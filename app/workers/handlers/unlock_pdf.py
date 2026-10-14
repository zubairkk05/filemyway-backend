"""Unlock PDF Handler (Remove Password)"""

from pathlib import Path
from typing import Any, Dict, List
import pikepdf


def handler(job_dir: Path, inputs: List[Dict], options: Dict[str, Any]) -> Dict:
    """Remove password protection from a PDF."""
    password = options.get("password", "") or None
    input_path = Path(inputs[0]["path"])

    try:
        pdf = pikepdf.open(input_path, password=password)
    except pikepdf.PasswordError:
        return {
            "ok": False,
            "error": {
                "code": "WRONG_PASSWORD",
                "message": "Incorrect password or the file is not encrypted",
                "needsPassword": True,
            },
        }

    try:
        if not pdf.is_encrypted:
            return {
                "ok": False,
                "error": {
                    "code": "PDF_NOT_ENCRYPTED",
                    "message": "PDF is not password protected",
                },
            }

        total_pages = len(pdf.pages)

        # Saving without an encryption argument strips the security handler.
        output_path = job_dir / "out/unlocked.pdf"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        pdf.save(output_path)
    finally:
        pdf.close()

    return {
        "ok": True,
        "outputs": [
            {"path": "out/unlocked.pdf", "name": "unlocked.pdf", "mime": "application/pdf"}
        ],
        "stats": {
            "total_pages": total_pages,
            "password_removed": True,
        },
        "progress": 100,
    }
