"""PDF to JPG Handler"""

import json
import asyncio
from pathlib import Path
from typing import Any, Dict, List

# Try to import pypdfium2 for rendering
try:
    import pypdfium2
    PYPDFIUM2_AVAILABLE = True
except ImportError:
    PYPDFIUM2_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def handler(job_dir: Path, inputs: List[Dict], options: Dict[str, Any]) -> Dict:
    """Convert PDF to JPG handler."""
    if not PYPDFIUM2_AVAILABLE:
        return {
            "ok": False,
            "error": {
                "code": "MISSING_LIBRARY",
                "message": "pypdfium2 is required to convert PDF to JPG"
            }
        }

    quality = options.get("quality", "good")  # "small", "good", "best"
    pages = options.get("pages", "all")  # "all" or range

    # Open the PDF
    input_path = Path(inputs[0]["path"])
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(str(input_path))
    total_pages = len(doc)

    # Determine which pages to render
    pages_to_render = []
    if pages == "all":
        pages_to_render = list(range(total_pages))
    else:
        # Parse page range
        page_str = str(pages)
        if "-" in page_str:
            start, end = page_str.split("-", 1)
            start_page = int(start) - 1
            end_page = int(end)
            pages_to_render = list(range(max(0, start_page), min(end_page, total_pages)))
        else:
            single_page = int(page_str) - 1
            pages_to_render = [single_page]

    # Render pages to JPG
    image_paths = []
    quality_map = {"small": 50, "good": 80, "best": 95}
    jpeg_quality = quality_map.get(quality, 80)

    for i, page_num in enumerate(pages_to_render):
        page = doc[page_num]
        # Render at 2x for better quality
        render_obj = page.render(scale=2.0)
        pil_image = render_obj.to_pil()

        output_path = job_dir / f"out/page_{i+1}.jpg"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        pil_image.save(output_path, "JPEG", quality=jpeg_quality)
        image_paths.append(str(output_path))

    doc.close()
    
    # If single page, return single image; otherwise return ZIP
    if len(image_paths) == 1:
        result_outputs = [
            {
                "path": image_paths[0],
                "name": Path(image_paths[0]).name,
                "mime": "image/jpeg"
            }
        ]
    else:
        # Create ZIP
        zip_path = job_dir / "out/images.zip"
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        import zipfile
        with zipfile.ZipFile(zip_path, "w") as zf:
            for img_path in image_paths:
                zf.write(img_path, arcname=Path(img_path).name)
        
        result_outputs = [
            {
                "path": "out/images.zip",
                "name": "images.zip",
                "mime": "application/zip"
            }
        ]
    
    return {
        "ok": True,
        "outputs": result_outputs,
        "stats": {
            "pages_rendered": len(pages_to_render),
            "quality": quality
        },
        "progress": 100
    }