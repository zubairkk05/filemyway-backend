"""Delete PDF Pages Handler"""

import json
import pikepdf
from pathlib import Path
from typing import Any, Dict, List


def handler(job_dir: Path, inputs: List[Dict], options: Dict[str, Any]) -> Dict:
    """Delete pages from PDF handler."""
    mode = options.get("mode", "range")  # "range", "all_but", "every_n"
    page_range = options.get("pages", "")  # e.g., "1,3-5" or "every_n:2"
    
    # Open the PDF
    input_path = Path(inputs[0]["path"])
    pdf = pikepdf.open(input_path)
    total_pages = len(pdf.pages)
    
    pages_to_remove = set()
    
    if mode == "range" and page_range:
        # Parse range like "1,3-5"
        for part in page_range.split(","):
            part = part.strip()
            if "-" in part:
                start, end = part.split("-", 1)
                for p in range(int(start), int(end) + 1):
                    if 1 <= p <= total_pages:
                        pages_to_remove.add(p - 1)  # zero-based
            else:
                p = int(part)
                if 1 <= p <= total_pages:
                    pages_to_remove.add(p - 1)
    
    elif mode == "every_n" and page_range:
        # every_n:2 means keep every Nth page, remove others
        n = int(page_range.split(":")[1]) if ":" in page_range else int(page_range)
        for i in range(total_pages):
            if (i + 1) % n != 0:
                pages_to_remove.add(i)
    
    elif mode == "all_but":
        # Keep specified pages, remove all others
        keep_str = page_range if page_range else "1"
        keep_pages = set()
        for part in keep_str.split(","):
            part = part.strip()
            if "-" in part:
                start, end = part.split("-", 1)
                for p in range(int(start), int(end) + 1):
                    if 1 <= p <= total_pages:
                        keep_pages.add(p - 1)
            else:
                p = int(part)
                if 1 <= p <= total_pages:
                    keep_pages.add(p - 1)
        # Pages not in keep_pages are removed
        pages_to_remove = set(range(total_pages)) - keep_pages
    
    # Remove pages (pikepdf handles this by rebuilding)
    if pages_to_remove:
        # Create new PDF with only kept pages
        kept_pages = [p for i, p in enumerate(pdf.pages) if i not in pages_to_remove]
        pdf = pikepdf.new()
        for p in kept_pages:
            pdf.pages.append(p)
    
    # Save output
    output_path = job_dir / "out/delete.pdf"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.save(output_path)
    pdf.close()
    
    # Count removed pages
    removed_count = len(pages_to_remove)
    
    return {
        "ok": True,
        "outputs": [
            {
                "path": "out/delete.pdf",
                "name": "delete.pdf",
                "mime": "application/pdf"
            }
        ],
        "stats": {
            "total_pages": total_pages,
            "removed_pages": removed_count,
            "remaining_pages": total_pages - removed_count
        },
        "progress": 100
    }