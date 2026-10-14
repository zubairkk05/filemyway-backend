"""Protect PDF Handler (Add Password Lock)"""

import shutil
from pathlib import Path
from typing import Any, Dict, List
import pikepdf


def handler(job_dir: Path, inputs: List[Dict], options: Dict[str, Any]) -> Dict:
    """Protect/lock a PDF with a password."""
    user_password = options.get("user_password") or options.get("password") or ""
    owner_password = options.get("owner_password") or user_password

    if not user_password:
        return {
            "ok": False,
            "error": {
                "code": "PASSWORD_REQUIRED",
                "message": "A password is required to protect the PDF",
            },
        }

    input_path = Path(inputs[0]["path"])
    output_path = job_dir / "out/protected.pdf"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with pikepdf.open(input_path) as pdf:
        if pdf.is_encrypted:
            return {
                "ok": False,
                "error": {
                    "code": "PDF_ENCRYPTED",
                    "message": "PDF is already password protected",
                    "needsPassword": True,
                },
            }

        total_pages = len(pdf.pages)
        pdf.save(
            output_path,
            encryption=pikepdf.Encryption(
                owner=owner_password, user=user_password, R=6
            ),
        )

    # Verify the produced file can be opened with the password.
    try:
        with pikepdf.open(output_path, password=user_password) as check:
            len(check.pages)
    except Exception as exc:  # noqa: BLE001
        shutil.rmtree(output_path.parent, ignore_errors=True)
        return {
            "ok": False,
            "error": {"code": "ENGINE_FAILED", "message": f"Failed to protect PDF: {exc}"},
        }

    return {
        "ok": True,
        "outputs": [
            {"path": "out/protected.pdf", "name": "protected.pdf", "mime": "application/pdf"}
        ],
        "stats": {"total_pages": total_pages, "password_protected": True},
        "progress": 100,
    }
