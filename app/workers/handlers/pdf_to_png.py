"""PDF to PNG Handler"""

import zipfile
from pathlib import Path
from typing import Any, Dict, List

try:
    import pypdfium2 as pdfium
    PYPDFIUM2_AVAILABLE = True
except ImportError:
    PYPDFIUM2_AVAILABLE = False


_QUALITY_SCALE = {"small": 1.5, "good": 2.0, "best": 3.0}


def _parse_pages(value: str, total: int) -> List[int]:
    if not value or value == "all":
        return list(range(total))
    pages: List[int] = []
    for part in str(value).split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-", 1)
            pages.extend(range(max(0, int(start) - 1), min(int(end), total)))
        else:
            index = int(part) - 1
            if 0 <= index < total:
                pages.append(index)
    return sorted(set(pages))


def handler(job_dir: Path, inputs: List[Dict], options: Dict[str, Any]) -> Dict:
    """Render PDF pages to PNG images."""
    if not PYPDFIUM2_AVAILABLE:
        return {
            "ok": False,
            "error": {"code": "MISSING_LIBRARY", "message": "pypdfium2 is required"},
        }

    quality = options.get("quality", "good")
    transparent = bool(options.get("transparent", False))

    input_path = Path(inputs[0]["path"])
    doc = pdfium.PdfDocument(str(input_path))
    total_pages = len(doc)
    pages = _parse_pages(options.get("pages", "all"), total_pages)
    scale = _QUALITY_SCALE.get(quality, 2.0)

    out_dir = job_dir / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    image_paths = []
    for i, page_num in enumerate(pages):
        pil_image = doc[page_num].render(scale=scale).to_pil()
        if transparent:
            pil_image = pil_image.convert("RGBA")
        output_path = out_dir / f"page_{i + 1}.png"
        pil_image.save(output_path, "PNG")
        image_paths.append(output_path)

    doc.close()

    if len(image_paths) == 1:
        outputs = [
            {"path": f"out/{image_paths[0].name}", "name": image_paths[0].name, "mime": "image/png"}
        ]
    else:
        zip_path = out_dir / "images.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            for img in image_paths:
                zf.write(img, arcname=img.name)
        outputs = [{"path": "out/images.zip", "name": "images.zip", "mime": "application/zip"}]

    return {
        "ok": True,
        "outputs": outputs,
        "stats": {"pages_rendered": len(pages), "quality": quality, "transparent": transparent},
        "progress": 100,
    }
