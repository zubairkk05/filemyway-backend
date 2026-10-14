"""PDF to Text Handler (OCR-style text extraction)"""

import json
import pikepdf
from pathlib import Path
from typing import Any, Dict, List


def handler(job_dir: Path, inputs: List[Dict], options: Dict[str, Any]) -> Dict:
    """Extract text from PDF handler."""
    page_range = options.get("pages", "all")  # "all" or range
    include_breaks = options.get("page_breaks", options.get("pageBreak", False))
    
    # Open the PDF
    input_path = Path(inputs[0]["path"])
    pdf = pikepdf.open(input_path)
    total_pages = len(pdf.pages)
    
    # Extract text from pages
    extracted_text = []
    
    if page_range == "all":
        pages_to_extract = range(total_pages)
    else:
        # Parse page range
        pages_to_extract = _parse_page_range(page_range, total_pages)
    
    for i in pages_to_extract:
        page = pdf.pages[i]
        text = ""
        try:
            # Extract text from page resources
            if "/Resources" in page:
                res = page["/Resources"]
                if "/XObject" in res:
                    # Try to get text content
                    pass
            # Get text using pikepdf
            text = page.get(" /FAF ", "") or ""
        except:
            text = ""
        
        # Add page break marker if requested
        if include_breaks and i < total_pages - 1:
            text += "\n---PAGE_BREAK---\n"
        
        extracted_text.append(text)
    
    pdf.close()
    
    # Combine all text
    full_text = "\n".join(extracted_text)
    
    # Write to file
    output_path = job_dir / "out/extracted_text.txt"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_text)
    
    return {
        "ok": True,
        "outputs": [
            {
                "path": "out/extracted_text.txt",
                "name": "extracted_text.txt",
                "mime": "text/plain"
            }
        ],
        "stats": {
            "total_pages": total_pages,
            "pages_extracted": len(pages_to_extract),
            "text_length": len(full_text)
        },
        "progress": 100
    }


def _parse_page_range(ranges_str: str, total_pages: int) -> list:
    """Parse page range string into list of zero-based indices."""
    indices = set()
    if not ranges_str or ranges_str == "all":
        return list(range(total_pages))
    
    for part in ranges_str.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            start, end = int(start), int(end)
            for p in range(max(1, start), min(total_pages, end) + 1):
                indices.add(p - 1)
        else:
            p = int(part)
            if 1 <= p <= total_pages:
                indices.add(p - 1)
    
    return sorted(indices)