"""Merge PDF Handler"""

import json
import pikepdf
from pathlib import Path
from typing import Any, Dict, List


def handler(job_dir: Path, inputs: List[Dict], options: Dict[str, Any]) -> Dict:
    """Merge PDF files handler."""
    order = options.get("order", None)
    
    # Open all PDFs
    pdfs = []
    for i, inp in enumerate(inputs):
        pdf = pikepdf.open(inp["path"])
        pdfs.append(pdf)
    
    # Apply custom order if specified
    if order:
        # order is list of file indices (1-based)
        ordered_pdfs = []
        for idx in order:
            idx_zero = idx - 1
            if 0 <= idx_zero < len(pdfs):
                ordered_pdfs.append(pdfs[idx_zero])
        # Add any remaining PDFs
        for i, pdf in enumerate(pdfs):
            if i + 1 not in order:
                ordered_pdfs.append(pdf)
        pdfs = ordered_pdfs
    
    # Create merged PDF
    merged = pikepdf.new()
    for pdf in pdfs:
        for page in pdf.pages:
            merged.pages.append(page)
    
    # Save output
    output_path = job_dir / "out" / "filemyway-merged.pdf"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    merged.save(output_path)
    
    # Close all input PDFs
    for pdf in pdfs:
        pdf.close()
    
    return {
        "ok": True,
        "outputs": [
            {
                "path": "out/filemyway-merged.pdf",
                "name": "filemyway-merged.pdf",
                "mime": "application/pdf"
            }
        ],
        "stats": {
            "input_count": len(inputs),
            "output_count": 1
        },
        "progress": 100
    }