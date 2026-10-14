"""Split PDF Handler"""

import json
import pikepdf
import zipfile
from pathlib import Path
from typing import Any, Dict, List


def handler(job_dir: Path, inputs: List[Dict], options: Dict[str, Any]) -> Dict:
    """Split PDF files handler."""
    mode = options.get("mode", "range")
    mode = {"range": "ranges", "every": "every_n", "pick": "extract"}.get(mode, mode)

    # Open the PDF
    input_path = Path(inputs[0]["path"])
    pdf = pikepdf.open(input_path)
    total_pages = len(pdf.pages)
    
    outputs = []
    
    if mode == "extract":
        # Extract specific pages
        pages_str = options.get("pages", "1-{}".format(total_pages))
        page_indices = parse_page_range(pages_str, total_pages)
        
        if len(page_indices) == 1:
            # Single page - save as individual PDF
            selected_pages = [pdf.pages[i] for i in page_indices]
            out_pdf = pikepdf.new()
            for p in selected_pages:
                out_pdf.pages.append(p)
            
            output_path = job_dir / f"out/page_{page_indices[0]+1}.pdf"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            out_pdf.save(output_path)
            outputs.append({
                "path": f"out/page_{page_indices[0]+1}.pdf",
                "name": f"page_{page_indices[0]+1}.pdf",
                "mime": "application/pdf"
            })
        else:
            # Multiple pages - save as single PDF
            out_pdf = pikepdf.new()
            for i in page_indices:
                out_pdf.pages.append(pdf.pages[i])
            
            output_path = job_dir / "out/extracted.pdf"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            out_pdf.save(output_path)
            outputs.append({
                "path": "out/extracted.pdf",
                "name": "extracted.pdf",
                "mime": "application/pdf"
            })
    
    elif mode == "every_n":
        n = int(options.get("everyN", options.get("every", 1)) or 1)
        chunks = []
        for i in range(0, total_pages, n):
            chunk = pdf.pages[i:i+n]
            chunks.append(chunk)
        
        for i, chunk in enumerate(chunks):
            out_pdf = pikepdf.new()
            for p in chunk:
                out_pdf.pages.append(p)
            
            output_path = job_dir / f"out/part_{i+1}.pdf"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            out_pdf.save(output_path)
            outputs.append({
                "path": f"out/part_{i+1}.pdf",
                "name": f"part_{i+1}.pdf",
                "mime": "application/pdf"
            })
    
    elif mode == "ranges":
        ranges_str = options.get("ranges") or options.get("range", "")
        range_sets = parse_ranges(ranges_str, total_pages)
        
        for i, range_set in enumerate(range_sets):
            out_pdf = pikepdf.new()
            for page_num in range_set:
                if 1 <= page_num <= total_pages:
                    out_pdf.pages.append(pdf.pages[page_num - 1])
            
            output_path = job_dir / f"out/range_{i+1}.pdf"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            out_pdf.save(output_path)
            outputs.append({
                "path": f"out/range_{i+1}.pdf",
                "name": f"range_{i+1}.pdf",
                "mime": "application/pdf"
            })
    
    # Close input PDF
    pdf.close()
    
    # If multiple outputs, create a ZIP
    if len(outputs) > 1:
        zip_path = job_dir / "out/split.zip"
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "w") as zf:
            for out in outputs:
                zf.write(job_dir / out["path"], arcname=Path(out["path"]).name)
        
        # Clear individual PDF outputs since they're in the ZIP
        outputs = [
            {
                "path": "out/split.zip",
                "name": "split.zip",
                "mime": "application/zip"
            }
        ]
    
    return {
        "ok": True,
        "outputs": outputs,
        "stats": {
            "input_pages": total_pages,
            "output_count": len(outputs)
        },
        "progress": 100
    }


def parse_page_range(ranges_str: str, total_pages: int) -> List[int]:
    """Parse page range string like '1-3,5,8-10' into zero-based indices."""
    indices = set()
    if not ranges_str:
        return list(range(total_pages))
    
    for part in ranges_str.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            start, end = int(start), int(end)
            for i in range(max(1, start), min(total_pages, end) + 1):
                indices.add(i - 1)
        else:
            page = int(part)
            if 1 <= page <= total_pages:
                indices.add(page - 1)
    
    return sorted(indices)


def parse_ranges(ranges_str: str, total_pages: int) -> List[List[int]]:
    """Parse ranges string into list of page number lists."""
    ranges = []
    if not ranges_str:
        return [[i+1 for i in range(total_pages)]]
    
    for part in ranges_str.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            start, end = int(start), int(end)
            # Clamp to valid range
            start = max(1, start)
            end = min(total_pages, end)
            if start <= end:
                ranges.append(list(range(start, end + 1)))
        else:
            page = int(part)
            if 1 <= page <= total_pages:
                ranges.append([page])
    
    # If no valid ranges found, return all pages
    if not ranges:
        ranges = [[i+1 for i in range(total_pages)]]
    
    return ranges