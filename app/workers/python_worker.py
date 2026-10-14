"""Python worker.

Runs a single tool handler and records ``progress.json`` / ``result.json`` in the
job directory. Jobs are scheduled on an in-process thread pool by default; the
module can also be used as a CLI (``python -m app.workers.python_worker ...``).
"""

import json
import os
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# ``resource`` is POSIX-only. Guard it so the worker imports on Windows too.
try:
    import resource  # type: ignore

    _HAS_RESOURCE = True
except ImportError:  # pragma: no cover - platform dependent
    _HAS_RESOURCE = False


def _apply_memory_limit() -> None:
    if not _HAS_RESOURCE:
        return
    try:
        mem_mb = int(os.environ.get("PY_WORKER_MEM_MB", "1024"))
        limit = mem_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    except (ValueError, OSError):
        pass


_apply_memory_limit()

_EXECUTOR = ThreadPoolExecutor(max_workers=int(os.environ.get("CONCURRENCY", "2")))


def _write_json(path, data) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(data, handle, default=str)
    os.replace(tmp, target)


def _normalize_inputs(inputs) -> list:
    normalized = []
    for item in inputs or []:
        if isinstance(item, str):
            normalized.append({"path": item, "name": Path(item).name})
        elif isinstance(item, dict):
            normalized.append(item)
    return normalized


def run_job(tool, job_dir, inputs, options, progress_file=None, result_file=None):
    """Execute one job synchronously and return the result dict."""
    job_dir = Path(job_dir)
    progress_path = Path(progress_file) if progress_file else job_dir / "progress.json"
    result_path = Path(result_file) if result_file else job_dir / "result.json"

    for stale in (progress_path, result_path):
        if stale.exists():
            stale.unlink()

    inputs = _normalize_inputs(inputs)
    _write_json(progress_path, {"percent": 5, "message": "starting"})

    try:
        from app.workers.handlers import TOOL_HANDLERS

        handler = TOOL_HANDLERS.get(tool)
        if handler is None:
            raise ValueError(f"Tool '{tool}' not found")
        _write_json(progress_path, {"percent": 30, "message": "working"})
        result = handler(job_dir, inputs, options)
        _write_json(progress_path, {"percent": 100, "message": "finished"})
    except Exception as exc:  # noqa: BLE001 - surface any handler failure
        result = {
            "ok": False,
            "error": {
                "code": "ENGINE_FAILED",
                "message": str(exc),
                "detail": traceback.format_exc(),
            },
        }
        _write_json(progress_path, {"percent": 100, "message": "failed"})

    _write_json(result_path, result)
    return result


def submit_job(*, tool, job_dir, inputs, options, progress_file=None, result_file=None):
    """Schedule a job on the worker pool and return the Future."""
    return _EXECUTOR.submit(
        run_job, tool, job_dir, inputs, options, progress_file, result_file
    )


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="FileMyWay PDF Tools Worker")
    parser.add_argument("--tool", required=True, help="Tool slug")
    parser.add_argument("--job-dir", required=True, help="Absolute job directory")
    parser.add_argument("--inputs", required=True, help="JSON list of input paths")
    parser.add_argument("--options", default="{}", help="JSON options object")
    args = parser.parse_args()

    inputs = json.loads(args.inputs)
    options = json.loads(args.options) if args.options else {}
    result = run_job(args.tool, args.job_dir, inputs, options)
    if not result.get("ok"):
        sys.exit(1)


if __name__ == "__main__":
    main()
