"""JPG to PDF Handler"""

from pathlib import Path
from typing import Any, Dict, List
from PIL import Image


_PAGE_SIZES = {
    "a4": (1240, 1754),      # ~150 dpi
    "letter": (1275, 1650),
}

_MARGINS = {"none": 0, "small": 40, "big": 90}


def _load_images(image_paths: List[str]) -> List[Image.Image]:
    images = []
    for path in image_paths:
        img = Image.open(path)
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGBA")
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")
        images.append(img)
    return images


def _fit_on_canvas(img: Image.Image, page_size, margin: int) -> Image.Image:
    page = Image.new("RGB", page_size, (255, 255, 255))
    max_w = page_size[0] - 2 * margin
    max_h = page_size[1] - 2 * margin
    ratio = min(max_w / img.width, max_h / img.height)
    new_size = (max(1, int(img.width * ratio)), max(1, int(img.height * ratio)))
    resized = img.resize(new_size, Image.LANCZOS)
    offset = ((page_size[0] - new_size[0]) // 2, (page_size[1] - new_size[1]) // 2)
    page.paste(resized, offset)
    return page


def handler(job_dir: Path, inputs: List[Dict], options: Dict[str, Any]) -> Dict:
    """Convert JPG/PNG/WEBP images into a single multi-page PDF."""
    page_size_key = options.get("pageSize", options.get("orientation", "a4"))
    margin_key = options.get("margin", "small")

    image_paths = [inp["path"] for inp in inputs if Path(inp["path"]).exists()]
    if not image_paths:
        return {
            "ok": False,
            "error": {"code": "NO_INPUTS", "message": "No valid input images found"},
        }

    try:
        images = _load_images(image_paths)
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": {"code": "INVALID_IMAGE", "message": f"Cannot open image: {exc}"},
        }

    target = _PAGE_SIZES.get(str(page_size_key).lower())
    if target is not None:
        margin = _MARGINS.get(str(margin_key).lower(), 40)
        images = [_fit_on_canvas(img, target, margin) for img in images]

    output_path = job_dir / "out/output.pdf"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    images[0].save(
        output_path,
        "PDF",
        save_all=True,
        append_images=images[1:],
        resolution=150.0,
    )

    return {
        "ok": True,
        "outputs": [
            {"path": "out/output.pdf", "name": "output.pdf", "mime": "application/pdf"}
        ],
        "stats": {
            "total_images": len(images),
            "page_size": page_size_key,
            "margin": margin_key,
        },
        "progress": 100,
    }
