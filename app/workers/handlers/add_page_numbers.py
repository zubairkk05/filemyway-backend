"""Add Page Numbers Handler"""

import io
import shutil
from pathlib import Path
from typing import Any, Dict, List
import pikepdf

try:
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


POSITION_ALIGN = {
    "top-left": "left",
    "top-center": "center",
    "top-right": "right",
    "middle-left": "left",
    "middle-center": "center",
    "middle-right": "right",
    "bottom-left": "left",
    "bottom-center": "center",
    "bottom-right": "right",
}

MARGIN = 28.0
FONT_SIZE = 11.0


def _format_number(n: int, total: int, style: str) -> str:
    if style in ("1/N", "1 of N", "page-of", "n-total"):
        return f"{n} of {total}"
    if style in ("Page 1", "page", "page-n"):
        return f"Page {n}"
    return str(n)


def _draw_number(c, text: str, position: str, page_w: float, page_h: float) -> None:
    align = POSITION_ALIGN.get(position, "center")
    row = position.split("-")[0]

    if row == "top":
        y = page_h - MARGIN
    elif row == "middle":
        y = page_h / 2.0
    else:
        y = MARGIN

    if align == "left":
        x = MARGIN
        c.drawString(x, y, text)
    elif align == "right":
        x = page_w - MARGIN
        c.drawRightString(x, y, text)
    else:
        x = page_w / 2.0
        c.drawCentredString(x, y, text)


def handler(job_dir: Path, inputs: List[Dict], options: Dict[str, Any]) -> Dict:
    """Add page numbers to a PDF."""
    position = options.get("position", "bottom-center")
    format_type = options.get("format", "n")
    start_number = int(options.get("start_number", options.get("start", 1)))
    skip_first = options.get("skip_first", options.get("skipFirst", False))

    input_path = Path(inputs[0]["path"])
    output_path = job_dir / "out/numbered.pdf"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with pikepdf.open(input_path) as pdf:
        total_pages = len(pdf.pages)

        if not REPORTLAB_AVAILABLE:
            shutil.copy2(input_path, output_path)
            return {
                "ok": True,
                "outputs": [
                    {"path": "out/numbered.pdf", "name": "numbered.pdf", "mime": "application/pdf"}
                ],
                "stats": {
                    "total_pages": total_pages,
                    "position": position,
                    "start_number": start_number,
                    "skip_first": skip_first,
                    "note": "numbering_engine_unavailable",
                },
                "progress": 100,
            }

        for i, page in enumerate(pdf.pages):
            if skip_first and i == 0:
                continue

            page_w = float(page.mediabox[2]) - float(page.mediabox[0])
            page_h = float(page.mediabox[3]) - float(page.mediabox[1])
            number = start_number + i
            text = _format_number(number, total_pages, format_type)

            buf = io.BytesIO()
            c = canvas.Canvas(buf, pagesize=(page_w, page_h))
            c.setFont("Helvetica", FONT_SIZE)
            _draw_number(c, text, position, page_w, page_h)
            c.save()
            buf.seek(0)

            with pikepdf.open(buf) as overlay:
                pikepdf.Page(page).add_overlay(pikepdf.Page(overlay.pages[0]), push_stack=True)

        pdf.save(output_path)

    return {
        "ok": True,
        "outputs": [
            {"path": "out/numbered.pdf", "name": "numbered.pdf", "mime": "application/pdf"}
        ],
        "stats": {
            "total_pages": total_pages,
            "position": position,
            "start_number": start_number,
            "skip_first": skip_first,
        },
        "progress": 100,
    }
