"""Tool Registry - Central registry for all PDF tools"""

from typing import Dict, Optional, List
from pydantic import BaseModel

TOOL_REGISTRY: Dict[str, dict] = {}


class ToolInfo(BaseModel):
    name: str
    slug: str
    category: str
    description: str
    accepted_input: str
    min_files: int
    max_files: int
    max_file_mb: int
    max_total_mb: int
    max_pages: int = 100
    runs_on: str  # "server" or "browser"
    status: str  # "live", "beta", "hidden"


def register_tool(tool_info: ToolInfo):
    """Register a tool in the registry."""
    try:
        data = tool_info.model_dump()
    except AttributeError:  # pydantic v1 fallback
        data = tool_info.dict()
    TOOL_REGISTRY[tool_info.slug] = data


def get_available_tools() -> List[dict]:
    """Get all live and beta tools."""
    return [
        tool for tool in TOOL_REGISTRY.values()
        if tool["status"] in ("live", "beta")
    ]


def get_tool(slug: str) -> Optional[dict]:
    """Get tool info by slug."""
    return TOOL_REGISTRY.get(slug)


# Register all PDF tools
register_tool(ToolInfo(
    name="Merge PDF",
    slug="merge-pdf",
    category="organize",
    description="Merge multiple PDFs into one document",
    accepted_input=".pdf",
    min_files=2,
    max_files=20,
    max_file_mb=100,
    max_total_mb=500,
    max_pages=100,
    runs_on="server",
    status="live"
))

register_tool(ToolInfo(
    name="Split PDF",
    slug="split-pdf",
    category="organize",
    description="Split PDF into separate pages or ranges",
    accepted_input=".pdf",
    min_files=1,
    max_files=1,
    max_file_mb=100,
    max_total_mb=500,
    max_pages=100,
    runs_on="server",
    status="live"
))

register_tool(ToolInfo(
    name="Compress PDF",
    slug="compress-pdf",
    category="optimize",
    description="Reduce PDF file size",
    accepted_input=".pdf",
    min_files=1,
    max_files=1,
    max_file_mb=100,
    max_total_mb=500,
    max_pages=100,
    runs_on="server",
    status="live"
))

register_tool(ToolInfo(
    name="Rotate PDF",
    slug="rotate-pdf",
    category="fix-up",
    description="Rotate PDF pages",
    accepted_input=".pdf",
    min_files=1,
    max_files=1,
    max_file_mb=100,
    max_total_mb=500,
    max_pages=100,
    runs_on="server",
    status="live"
))

register_tool(ToolInfo(
    name="Delete PDF Pages",
    slug="delete-pdf-pages",
    category="fix-up",
    description="Remove pages from a PDF",
    accepted_input=".pdf",
    min_files=1,
    max_files=1,
    max_file_mb=100,
    max_total_mb=500,
    max_pages=100,
    runs_on="server",
    status="live"
))

register_tool(ToolInfo(
    name="Reorder PDF Pages",
    slug="reorder-pdf-pages",
    category="fix-up",
    description="Change the order of PDF pages",
    accepted_input=".pdf",
    min_files=1,
    max_files=1,
    max_file_mb=100,
    max_total_mb=500,
    max_pages=100,
    runs_on="server",
    status="live"
))

register_tool(ToolInfo(
    name="Add Page Numbers",
    slug="add-page-numbers",
    category="fix-up",
    description="Add page numbers to PDF",
    accepted_input=".pdf",
    min_files=1,
    max_files=1,
    max_file_mb=100,
    max_total_mb=500,
    max_pages=100,
    runs_on="server",
    status="live"
))

register_tool(ToolInfo(
    name="Watermark PDF",
    slug="watermark-pdf",
    category="fix-up",
    description="Add watermark to PDF",
    accepted_input=".pdf",
    min_files=1,
    max_files=1,
    max_file_mb=100,
    max_total_mb=500,
    max_pages=100,
    runs_on="server",
    status="live"
))

register_tool(ToolInfo(
    name="Protect PDF",
    slug="protect-pdf",
    category="secure",
    description="Lock PDF with password",
    accepted_input=".pdf",
    min_files=1,
    max_files=1,
    max_file_mb=100,
    max_total_mb=500,
    max_pages=100,
    runs_on="server",
    status="live"
))

register_tool(ToolInfo(
    name="Unlock PDF",
    slug="unlock-pdf",
    category="secure",
    description="Unlock password-protected PDF",
    accepted_input=".pdf",
    min_files=1,
    max_files=1,
    max_file_mb=100,
    max_total_mb=500,
    max_pages=100,
    runs_on="server",
    status="live"
))

register_tool(ToolInfo(
    name="PDF to JPG",
    slug="pdf-to-jpg",
    category="convert",
    description="Convert PDF to JPG images",
    accepted_input=".pdf",
    min_files=1,
    max_files=1,
    max_file_mb=100,
    max_total_mb=500,
    max_pages=100,
    runs_on="server",
    status="live"
))

register_tool(ToolInfo(
    name="PDF to PNG",
    slug="pdf-to-png",
    category="convert",
    description="Convert PDF to PNG images",
    accepted_input=".pdf",
    min_files=1,
    max_files=1,
    max_file_mb=100,
    max_total_mb=500,
    max_pages=100,
    runs_on="server",
    status="live"
))

register_tool(ToolInfo(
    name="PDF to Text",
    slug="pdf-to-text",
    category="convert",
    description="Extract text from PDF",
    accepted_input=".pdf",
    min_files=1,
    max_files=1,
    max_file_mb=100,
    max_total_mb=500,
    max_pages=100,
    runs_on="server",
    status="live"
))

register_tool(ToolInfo(
    name="JPG to PDF",
    slug="jpg-to-pdf",
    category="convert",
    description="Convert JPG images to PDF",
    accepted_input=".jpg,.jpeg,.png",
    min_files=1,
    max_files=50,
    max_file_mb=10,
    max_total_mb=50,
    max_pages=100,
    runs_on="server",
    status="live"
))

register_tool(ToolInfo(
    name="Excel to PDF",
    slug="excel-to-pdf",
    category="convert",
    description="Convert Excel/CSV to PDF",
    accepted_input=".xlsx,.csv",
    min_files=1,
    max_files=1,
    max_file_mb=100,
    max_total_mb=500,
    max_pages=100,
    runs_on="server",
    status="beta"
))

register_tool(ToolInfo(
    name="PDF to Excel",
    slug="pdf-to-excel",
    category="convert",
    description="Convert PDF to Excel/CSV",
    accepted_input=".pdf",
    min_files=1,
    max_files=1,
    max_file_mb=100,
    max_total_mb=500,
    max_pages=100,
    runs_on="server",
    status="beta"
))

register_tool(ToolInfo(
    name="PDF to PPT",
    slug="pdf-to-ppt",
    category="convert",
    description="Convert PDF to PowerPoint",
    accepted_input=".pdf",
    min_files=1,
    max_files=1,
    max_file_mb=100,
    max_total_mb=500,
    max_pages=100,
    runs_on="server",
    status="beta"
))

register_tool(ToolInfo(
    name="Image Converter",
    slug="image-converter",
    category="pictures",
    description="Change picture format (PNG to JPG, etc.)",
    accepted_input=".jpg,.jpeg,.png,.webp,.heic",
    min_files=1,
    max_files=20,
    max_file_mb=10,
    max_total_mb=50,
    runs_on="server",
    status="live"
))

register_tool(ToolInfo(
    name="HEIC to JPG",
    slug="heic-to-jpg",
    category="pictures",
    description="Convert HEIC (iPhone photos) to JPG",
    accepted_input=".heic",
    min_files=1,
    max_files=20,
    max_file_mb=10,
    max_total_mb=50,
    runs_on="server",
    status="beta"
))

register_tool(ToolInfo(
    name="PDF to PPTX",
    slug="pdf-to-pptx",
    category="convert",
    description="Convert PDF to PowerPoint (beta)",
    accepted_input=".pdf",
    min_files=1,
    max_files=1,
    max_file_mb=100,
    max_total_mb=500,
    runs_on="server",
    status="hidden"
))

register_tool(ToolInfo(
    name="Word to PDF",
    slug="word-to-pdf",
    category="convert",
    description="Convert Word to PDF",
    accepted_input=".docx",
    min_files=1,
    max_files=1,
    max_file_mb=100,
    max_total_mb=500,
    runs_on="server",
    status="hidden"
))

register_tool(ToolInfo(
    name="PPT to PDF",
    slug="ppt-to-pdf",
    category="convert",
    description="Convert PowerPoint to PDF (beta)",
    accepted_input=".pptx",
    min_files=1,
    max_files=1,
    max_file_mb=100,
    max_total_mb=500,
    runs_on="server",
    status="hidden"
))