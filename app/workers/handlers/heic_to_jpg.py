"""HEIC to JPG Handler (iPhone photo conversion)"""

import json
import asyncio
from pathlib import Path
from typing import Any, Dict, List
from PIL import Image


def handler(job_dir: Path, inputs: List[Dict], options: Dict[str, Any]) -> Dict:
    """Convert HEIC to JPG handler."""
    quality = int(options.get("quality", "80"))
    
    # Get input file paths
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
                "message": "No valid input HEIC files found"
            }
        }
    
    # HEIC support - try using pillow-heif or fallback
    output_paths = []
    
    for img_path in image_paths:
        try:
            # Try to open with PIL (may need pillow-heif plugin)
            img = Image.open(img_path)
            
            # If image is already in a supported format, just convert
            if img.mode != "RGB":
                img = img.convert("RGB")
            
            # Determine output path
            stem = Path(img_path).stem
            out_path = job_dir / f"{stem}.jpg"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save as JPG
            img.save(out_path, "JPEG", quality=quality)
            output_paths.append(str(out_path))
            
        except Exception as e:
            # If direct opening fails, try with heif support
            try:
                import pillow_heif
                img = Image.open(img_path)
                if img.mode != "RGB":
                    img = img.convert("RGB")
                
                stem = Path(img_path).stem
                out_path = job_dir / f"{stem}.jpg"
                out_path.parent.mkdir(parents=True, exist_ok=True)
                img.save(out_path, "JPEG", quality=quality)
                output_paths.append(str(out_path))
            except ImportError:
                return {
                    "ok": False,
                    "error": {
                        "code": "HEIC_NOT_SUPPORTED",
                        "message": "HEIC format requires pillow-heif plugin. Try JPG input instead."
                    }
                }
    
    # If single input, return single output
    if len(output_paths) == 1:
        result_outputs = [
            {
                "path": output_paths[0],
                "name": Path(output_paths[0]).name,
                "mime": "image/jpeg"
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
            "total_files": len(image_paths),
            "output_format": "jpg",
            "quality": quality
        },
        "progress": 100,
        "note": "BETA: May run in browser for supported formats"
    }