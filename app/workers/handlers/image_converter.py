"""Image Converter Handler (format conversion)"""

import json
from pathlib import Path
from typing import Any, Dict, List
from PIL import Image


def handler(job_dir: Path, inputs: List[Dict], options: Dict[str, Any]) -> Dict:
    """Convert image format handler."""
    output_format = options.get("output_format", options.get("format", "jpg"))  # "jpg", "png", "webp"
    quality = int(options.get("quality", "80"))
    background = options.get("background", "white")  # "white", "transparent"
    
    # Get all input image paths
    image_paths = []
    for inp in inputs:
        img_path = Path(inp["path"])
        if img_path.exists():
            image_paths.append(str(img_path))
    
    if not image_paths:
        return {
            "ok": False,
            "error": {
                "code": "NO_INPUTS",
                "message": "No valid input images found"
            }
        }
    
    output_paths = []
    
    for img_path in image_paths:
        try:
            img = Image.open(img_path)
            
            # Handle background/transparency
            if output_format in ["jpg", "jpeg"] and img.mode == "RGBA" and background == "white":
                # Create white background
                background_img = Image.new("RGB", img.size, (255, 255, 255))
                background_img.paste(img, mask=img.split()[3])  # Use alpha mask
                img = background_img
            elif output_format in ["png"] and img.mode != "RGBA" and background == "transparent":
                # Ensure RGBA for transparency
                img = img.convert("RGBA")
            
            # Convert format
            if img.mode != "RGB" and output_format in ["jpg", "jpeg"]:
                if img.mode in ("RGBA", "LA", "PA"):
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1])
                    img = background
                else:
                    img = img.convert("RGB")
            
            # Determine output path
            stem = Path(img_path).stem
            out_path = job_dir / f"{stem}.{output_format}"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save with quality
            save_kwargs = {}
            if output_format in ["jpg", "jpeg"]:
                save_kwargs["quality"] = quality
            elif output_format == "webp":
                save_kwargs["quality"] = quality
            
            img.save(out_path, **save_kwargs)
            output_paths.append(str(out_path))
            
        except Exception as e:
            return {
                "ok": False,
                "error": {
                    "code": "CONVERSION_FAILED",
                    "message": f"Failed to convert {img_path}: {str(e)}"
                }
            }
    
    # If single input, return single output; otherwise ZIP
    if len(output_paths) == 1:
        result_outputs = [
            {
                "path": output_paths[0],
                "name": Path(output_paths[0]).name,
                "mime": _get_mime_type(output_paths[0])
            }
        ]
    else:
        # Create ZIP
        import zipfile
        zip_path = job_dir / "out/converted.zip"
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "w") as zf:
            for op in output_paths:
                zf.write(op, arcname=Path(op).name)
        
        result_outputs = [
            {
                "path": "out/converted.zip",
                "name": "converted.zip",
                "mime": "application/zip"
            }
        ]
    
    return {
        "ok": True,
        "outputs": result_outputs,
        "stats": {
            "total_images": len(image_paths),
            "output_format": output_format,
            "quality": quality
        },
        "progress": 100
    }


def _get_mime_type(filepath: str) -> str:
    """Get MIME type based on file extension."""
    ext = Path(filepath).suffix.lower()
    mime_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }
    return mime_types.get(ext, "application/octet-stream")