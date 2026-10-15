"""API v1 router.

Endpoints (mounted under ``/api/v1``):

* ``GET    /tools``                       -> list of live/beta tools
* ``POST   /jobs/{tool_name}``            -> multipart upload, returns a job id
* ``GET    /jobs/{job_id}``               -> queued | processing | completed | failed
* ``GET    /jobs/{job_id}/download``      -> the first output file
* ``DELETE /jobs/{job_id}``               -> remove a job (token protected)
"""

import hmac
import json
import os
import shutil
import stat
import threading
import time
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, Form, Header, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from app.core.config import settings
from app.core.tool_registry import get_available_tools, get_tool
from app.workers.python_worker import submit_job

router = APIRouter(tags=["tools"])


def _job_dir(job_id: str) -> Path:
    return Path(settings.STORAGE_DIR) / job_id


def _read_json(path) -> Optional[dict]:
    target = Path(path)
    if not target.exists():
        return None
    try:
        with open(target, encoding="utf-8") as handle:
            return json.load(handle)
    except (json.JSONDecodeError, OSError):
        return None


def _force_remove_tree(path) -> None:
    """Remove a directory tree even if a file is read-only (common on Windows)."""

    def _on_error(func, item, exc_info):  # noqa: ANN001
        os.chmod(item, stat.S_IWRITE)
        func(item)

    try:
        shutil.rmtree(path, onerror=_on_error)
    except Exception as exc:  # noqa: BLE001
        print(f"[delete] rmtree failed: {exc!r}", flush=True)
    print(f"[delete] removed={not path.exists()} path={path}", flush=True)


_CLEANUP_INTERVAL_SEC = 600
_DELETE_MARKER = ".delete-after"
# Never erase a job whose tree was touched within this window: a worker may
# still be writing progress.json/result.json into it.
_DELETE_MIN_AGE_SEC = 60.0
# Fallback for jobs that never produced a result.json (stuck/crashed workers).
_ORPHAN_MAX_AGE_SEC = 6 * 3600.0
_last_cleanup = 0.0


def _tree_age_seconds(path: Path) -> float:
    """Seconds since the newest file change in the tree (its "last used" time)."""
    try:
        newest = path.stat().st_mtime
    except OSError:
        return 0.0
    for root, _dirs, files in os.walk(path):
        for name in files:
            try:
                newest = max(newest, (Path(root) / name).stat().st_mtime)
            except OSError:
                continue
    return time.time() - newest


def _delete_deadline(job_dir: Path) -> Optional[float]:
    """Epoch seconds at which a downloaded job must be erased, if scheduled."""
    marker = job_dir / _DELETE_MARKER
    if not marker.exists():
        return None
    try:
        return float(marker.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return time.time()


def _job_finalized(job_dir: Path) -> bool:
    """True once the worker has written a final ``result.json`` (ok or error)."""
    result = _read_json(job_dir / "result.json")
    return isinstance(result, dict) and "ok" in result


def _safe_to_delete(job_dir: Path) -> bool:
    """Guard against erasing a job whose worker is still writing files.

    Requires a real job (``meta.json`` is written by the API before the worker
    starts) and a minimum idle age, so a folder that was just created or is
    being updated right now is skipped. Without this, a sweep could delete a
    job mid-run and the worker would recreate the folder with only
    ``progress.json`` / ``result.json`` and no inputs.
    """
    if not job_dir.is_dir():
        return False
    if not (job_dir / "meta.json").exists():
        return False
    return _tree_age_seconds(job_dir) >= _DELETE_MIN_AGE_SEC


def _guarded_delete(job_dir: Path) -> None:
    """Remove a job only if it is finished and idle (timer/download path)."""
    if _safe_to_delete(job_dir) and _job_finalized(job_dir):
        _force_remove_tree(job_dir)


def cleanup_expired_jobs() -> int:
    """Erase jobs whose post-download grace has passed, or that were never
    downloaded and are older than JOB_TTL_MIN minutes.

    Only finished, idle jobs are ever removed (see ``_safe_to_delete``), so an
    in-progress job is never deleted while its worker is still writing.
    """
    root = Path(settings.STORAGE_DIR)
    if not root.exists():
        return 0
    ttl_seconds = settings.JOB_TTL_MIN * 60
    removed = 0
    for entry in root.iterdir():
        if not entry.is_dir():
            continue
        if not _safe_to_delete(entry):
            continue
        deadline = _delete_deadline(entry)
        age = _tree_age_seconds(entry)
        if deadline is not None:
            expired = time.time() >= deadline
        elif _job_finalized(entry):
            expired = age > ttl_seconds
        else:
            # Never finished (crashed/stuck worker): reclaim only after a long
            # grace period so an in-progress job stays safe.
            expired = age > max(ttl_seconds, _ORPHAN_MAX_AGE_SEC)
        if expired:
            _force_remove_tree(entry)
            removed += 1
    return removed


def _schedule_job_deletion(job_dir: Path) -> None:
    """Erase a job a few minutes after it was first downloaded.

    Records the deadline in a marker file (so a restart still erases it on the
    next sweep) and starts a precise timer for the common case. Deletion is
    guarded so it can never remove a folder a worker is still writing.
    """
    if (job_dir / _DELETE_MARKER).exists():
        return
    deadline = time.time() + settings.POST_DOWNLOAD_GRACE_MIN * 60
    try:
        (job_dir / _DELETE_MARKER).write_text(str(deadline), encoding="utf-8")
    except OSError:
        pass
    timer = threading.Timer(
        max(1.0, deadline - time.time()), _guarded_delete, args=(job_dir,)
    )
    timer.daemon = True
    timer.start()


def _opportunistic_cleanup() -> None:
    """Throttled sweep so files expire even without an external cron."""
    global _last_cleanup
    now = time.time()
    if now - _last_cleanup < _CLEANUP_INTERVAL_SEC:
        return
    _last_cleanup = now
    try:
        cleanup_expired_jobs()
    except Exception:  # noqa: BLE001 - cleanup must never break a request
        pass


def _resolve_output(job_dir: Path, output: dict) -> Path:
    path = Path(output.get("path", ""))
    if not path.is_absolute():
        path = job_dir / path
    return path


def _enrich_result(job_id: str, job_dir: Path, token: Optional[str], result: dict) -> dict:
    outputs = []
    for output in result.get("outputs", []):
        path = _resolve_output(job_dir, output)
        size = path.stat().st_size if path.exists() else None
        outputs.append(
            {
                "name": output.get("name") or path.name,
                "mime": output.get("mime"),
                "size": size,
                "downloadUrl": (
                    f"/api/v1/jobs/{job_id}/download?token={token}" if token else None
                ),
            }
        )

    stats = dict(result.get("stats") or {})
    before = stats.get("beforeBytes", stats.get("inputBytes"))
    after = stats.get("afterBytes", stats.get("outputBytes"))
    if before is not None:
        stats["beforeBytes"] = before
    if after is not None:
        stats["afterBytes"] = after

    payload = {"ok": True, "outputs": outputs, "stats": stats}
    if result.get("note"):
        payload["note"] = result["note"]
    return payload


@router.get("/tools")
async def list_tools():
    """List tools that are visible to users (live/beta only)."""
    return get_available_tools()


@router.post("/maintenance/cleanup")
async def maintenance_cleanup(
    secret: Optional[str] = None,
    x_cron_secret: Optional[str] = Header(default=None),
):
    """Erase jobs older than JOB_TTL_MIN. Called by a cPanel cron job.

    Protect it with ``CRON_SECRET`` passed as ``?secret=`` or the
    ``X-Cron-Secret`` header.
    """
    provided = x_cron_secret or secret or ""
    expected = settings.CRON_SECRET
    if not expected or not hmac.compare_digest(provided, expected):
        return JSONResponse(
            status_code=403,
            content={"error": {"code": "FORBIDDEN", "message": "Invalid cron secret"}},
        )
    removed = cleanup_expired_jobs()
    return {
        "ok": True,
        "removed": removed,
        "ttlMinutes": settings.JOB_TTL_MIN,
        "postDownloadGraceMinutes": settings.POST_DOWNLOAD_GRACE_MIN,
    }


@router.post("/jobs/{tool_name}", status_code=202)
async def create_job(
    tool_name: str,
    files: List[UploadFile] = File(...),
    options: str = Form("{}"),
):
    """Create a conversion job from one or more uploaded files."""
    _opportunistic_cleanup()
    tool_info = get_tool(tool_name)
    if not tool_info or tool_info.get("status") == "hidden":
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "TOOL_NOT_FOUND", "message": f"Tool '{tool_name}' not found"}},
        )

    try:
        options_dict = json.loads(options) if options else {}
        if not isinstance(options_dict, dict):
            raise ValueError
    except (json.JSONDecodeError, ValueError):
        return JSONResponse(
            status_code=400,
            content={"error": {"code": "INVALID_OPTIONS", "message": "Options must be a JSON object"}},
        )

    job_id = str(uuid.uuid4())
    job_dir = _job_dir(job_id)
    in_dir = job_dir / "in"
    in_dir.mkdir(parents=True, exist_ok=True)

    max_file_bytes = tool_info["max_file_mb"] * 1024 * 1024
    max_total_bytes = tool_info["max_total_mb"] * 1024 * 1024

    inputs = []
    total_size = 0

    for index, upload in enumerate(files, start=1):
        ext = Path(upload.filename).suffix.lower() if upload.filename else ""
        if not ext:
            ext = ".bin"
        dest = in_dir / f"{index}{ext}"

        size = 0
        with open(dest, "wb") as handle:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
                size += len(chunk)

        if size > max_file_bytes:
            _force_remove_tree(job_dir)
            return JSONResponse(
                status_code=413,
                content={
                    "error": {
                        "code": "FILE_TOO_LARGE",
                        "message": f"Each file must be under {tool_info['max_file_mb']} MB",
                    }
                },
            )

        total_size += size
        inputs.append(
            {"path": str(dest.resolve()), "name": upload.filename or dest.name, "size": size}
        )

    if len(inputs) < tool_info["min_files"]:
        _force_remove_tree(job_dir)
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "TOO_FEW_FILES",
                    "message": f"Need at least {tool_info['min_files']} file(s)",
                }
            },
        )
    if len(inputs) > tool_info["max_files"]:
        _force_remove_tree(job_dir)
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "TOO_MANY_FILES",
                    "message": f"Maximum {tool_info['max_files']} files allowed",
                }
            },
        )
    if total_size > max_total_bytes:
        _force_remove_tree(job_dir)
        return JSONResponse(
            status_code=413,
            content={
                "error": {
                    "code": "TOTAL_TOO_LARGE",
                    "message": f"Total upload must be under {tool_info['max_total_mb']} MB",
                }
            },
        )

    delete_token = uuid.uuid4().hex
    meta = {
        "jobId": job_id,
        "tool": tool_name,
        "deleteToken": delete_token,
        "inputs": inputs,
        "options": options_dict,
    }
    (job_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")

    submit_job(
        tool=tool_name,
        job_dir=job_dir,
        inputs=inputs,
        options=options_dict,
        progress_file=job_dir / "progress.json",
        result_file=job_dir / "result.json",
    )

    return {"jobId": job_id, "status": "queued", "deleteToken": delete_token}


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Return the state of a job for the frontend to poll."""
    job_dir = _job_dir(job_id)
    if not job_dir.exists():
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "JOB_NOT_FOUND", "message": "Job not found"}},
        )

    meta = _read_json(job_dir / "meta.json") or {}
    token = meta.get("deleteToken")

    result = _read_json(job_dir / "result.json")
    if result is not None:
        if not result.get("ok", False):
            return {
                "status": "failed",
                "error": result.get("error") or {"code": "ENGINE_FAILED"},
            }
        return {
            "status": "completed",
            "result": _enrich_result(job_id, job_dir, token, result),
        }

    progress = _read_json(job_dir / "progress.json")
    if progress is not None:
        return {"status": "processing", "progress": progress}

    return {"status": "queued"}


@router.get("/jobs/{job_id}/download")
async def download_job(job_id: str, token: Optional[str] = None):
    """Stream the first output of a completed job."""
    job_dir = _job_dir(job_id)
    meta = _read_json(job_dir / "meta.json") or {}
    expected = meta.get("deleteToken")
    if expected and token and token != expected:
        return JSONResponse(
            status_code=403,
            content={"error": {"code": "FORBIDDEN", "message": "Invalid download token"}},
        )

    result = _read_json(job_dir / "result.json")
    if not result or not result.get("ok"):
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "JOB_NOT_FOUND", "message": "Job not found or not complete"}},
        )

    outputs = result.get("outputs") or []
    if not outputs:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "NO_OUTPUT", "message": "This job produced no output"}},
        )

    output = outputs[0]
    path = _resolve_output(job_dir, output)
    if not path.exists():
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "OUTPUT_MISSING", "message": "Output file is missing"}},
        )

    _schedule_job_deletion(job_dir)
    return FileResponse(
        path=str(path),
        media_type=output.get("mime") or "application/octet-stream",
        filename=output.get("name") or path.name,
    )


@router.delete("/jobs/{job_id}", status_code=204)
async def delete_job(job_id: str, token: Optional[str] = None):
    """Delete a job and its files. Protected by the per-job delete token."""
    job_dir = _job_dir(job_id)
    if not job_dir.exists():
        return Response(status_code=204)

    meta = _read_json(job_dir / "meta.json") or {}
    expected = meta.get("deleteToken")
    if expected and token and token != expected:
        return JSONResponse(
            status_code=403,
            content={"error": {"code": "FORBIDDEN", "message": "Invalid delete token"}},
        )

    _force_remove_tree(job_dir)
    return Response(status_code=204)
