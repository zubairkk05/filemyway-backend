"""Reorder PDF Pages Handler"""

import json
import pikepdf
from pathlib import Path
from typing import Any, Dict, List


def handler(job_dir: Path, inputs: List[Dict], options: Dict[str, Any]) -> Dict:
    """Reorder PDF pages handler."""
    # Get the new order from options
    order_str = options.get("order", "")  # e.g., "3,1,2" or "reverse"
    reverse = options.get("reverse", False)
    
    # Open the PDF
    input_path = Path(inputs[0]["path"])
    pdf = pikepdf.open(input_path)
    total_pages = len(pdf.pages)
    
    if reverse:
        # Reverse the order
        new_order = list(range(total_pages - 1, -1, -1))
    elif order_str:
        # Parse order string like "3,1,2"
        try:
            order_list = [int(x.strip()) for x in order_str.split(",")]
            # Convert to zero-based and clamp to valid range
            new_order = []
            for o in order_list:
                if 1 <= o <= total_pages:
                    new_order.append(o - 1)
            # Add any pages not in the order list at the end
            all_indices = set(range(total_pages))
            ordered_set = set(new_order)
            remaining = all_indices - ordered_set
            for i in sorted(remaining):
                new_order.append(i)
        except (ValueError, TypeError):
            new_order = list(range(total_pages))
    else:
        new_order = list(range(total_pages))
    
    # Create new PDF with reordered pages
    new_pdf = pikepdf.new()
    for idx in new_order:
        if 0 <= idx < total_pages:
            new_pdf.pages.append(pdf.pages[idx])
    
    # Save output
    output_path = job_dir / "out/reordered.pdf"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    new_pdf.save(output_path)
    pdf.close()
    
    return {
        "ok": True,
        "outputs": [
            {
                "path": "out/reordered.pdf",
                "name": "reordered.pdf",
                "mime": "application/pdf"
            }
        ],
        "stats": {
            "total_pages": total_pages,
            "new_order": new_order
        },
        "progress": 100
    }