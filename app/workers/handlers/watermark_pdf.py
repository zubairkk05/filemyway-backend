"""Watermark PDF Handler"""

import io
import shutil
from pathlib import Path
from typing import Any, Dict, List
import pikepdf

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import HexColor
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


def _parse_color(color: Any):
    if isinstance(color, str):
        name = color.strip()
        if name.startswith("#") and len(name) == 7:
            try:
                return HexColor(name)
            except Exception:
                pass
        mapping = {
            "black": "#000000",
            "white": "#FFFFFF",
            "red": "#FF0000",
            "gray": "#808080",
            "grey": "#808080",
            "orange": "#FF4B14",
            "blue": "#0000FF",
            "green": "#008000",
        }
        return HexColor(mapping.get(name.lower(), "#000000"))
    return HexColor("#000000")


def handler(job_dir: Path, inputs: List[Dict], options: Dict[str, Any]) -> Dict:
    """Add a text watermark to every page of a PDF."""
    watermark_text = options.get("text", "Draft")
    font_size = float(options.get("font_size", options.get("size", 50)))
    opacity = float(options.get("opacity", 0.5))
    if opacity > 1:
        opacity = opacity / 100.0
    angle = float(options.get("angle", 0)) or 45.0
    color = options.get("color", options.get("colour", "black"))

    input_path = Path(inputs[0]["path"])
    output_path = job_dir / "out/watermarked.pdf"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with pikepdf.open(input_path) as pdf:
        total_pages = len(pdf.pages)

        if not REPORTLAB_AVAILABLE:
            shutil.copy2(input_path, output_path)
            return {
                "ok": True,
                "outputs": [
                    {"path": "out/watermarked.pdf", "name": "watermarked.pdf", "mime": "application/pdf"}
                ],
                "stats": {
                    "total_pages": total_pages,
                    "watermark_text": watermark_text,
                    "opacity": opacity,
                    "angle": angle,
                    "note": "watermark_engine_unavailable",
                },
                "progress": 100,
            }

        fill_color = _parse_color(color)

        for page in pdf.pages:
            page_w = float(page.mediabox[2]) - float(page.mediabox[0])
            page_h = float(page.mediabox[3]) - float(page.mediabox[1])

            buf = io.BytesIO()
            c = canvas.Canvas(buf, pagesize=(page_w, page_h))
            c.saveState()
            c.setFillColor(fill_color)
            c.setFillAlpha(max(0.0, min(1.0, opacity)))
            c.setFont("Helvetica-Bold", font_size)
            c.translate(page_w / 2.0, page_h / 2.0)
            c.rotate(angle)
            c.drawCentredString(0, 0, watermark_text)
            c.restoreState()
            c.save()
            buf.seek(0)

            with pikepdf.open(buf) as overlay:
                pikepdf.Page(page).add_overlay(pikepdf.Page(overlay.pages[0]))

        pdf.save(output_path)

    return {
        "ok": True,
        "outputs": [
            {"path": "out/watermarked.pdf", "name": "watermarked.pdf", "mime": "application/pdf"}
        ],
        "stats": {
            "total_pages": total_pages,
            "watermark_text": watermark_text,
            "opacity": opacity,
            "angle": angle,
        },
        "progress": 100,
    }
