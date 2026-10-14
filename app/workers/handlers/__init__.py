"""Tool Handlers Package - All PDF tool handlers"""

from .merge_pdf import handler as merge_handler
from .split_pdf import handler as split_handler
from .compress_pdf import handler as compress_handler
from .pdf_to_jpg import handler as pdf_to_jpg_handler
from .pdf_to_png import handler as pdf_to_png_handler
from .rotate.rotate_pdf import handler as rotate_handler
from .delete_pdf_pages import handler as delete_handler
from .reorder_pdf_pages import handler as reorder_handler
from .add_page_numbers import handler as add_numbers_handler
from .watermark_pdf import handler as watermark_handler
from .protect_pdf import handler as protect_handler
from .unlock_pdf import handler as unlock_handler
from .pdf_to_text import handler as pdf_to_text_handler
from .jpg_to_pdf import handler as jpg_to_pdf_handler
from .excel_to_pdf import handler as excel_to_pdf_handler
from .pdf_to_excel import handler as pdf_to_excel_handler
from .pdf_to_ppt import handler as pdf_to_ppt_handler
from .image_converter import handler as image_converter_handler
from .heic_to_jpg import handler as heic_to_jpg_handler

# Export all handlers
TOOL_HANDLERS = {
    "merge-pdf": merge_handler,
    "split-pdf": split_handler,
    "compress-pdf": compress_handler,
    "pdf-to-jpg": pdf_to_jpg_handler,
    "pdf-to-png": pdf_to_png_handler,
    "rotate-pdf": rotate_handler,
    "delete-pdf-pages": delete_handler,
    "reorder-pdf-pages": reorder_handler,
    "add-page-numbers": add_numbers_handler,
    "watermark-pdf": watermark_handler,
    "protect-pdf": protect_handler,
    "unlock-pdf": unlock_handler,
    "pdf-to-text": pdf_to_text_handler,
    "jpg-to-pdf": jpg_to_pdf_handler,
    "excel-to-pdf": excel_to_pdf_handler,
    "pdf-to-excel": pdf_to_excel_handler,
    "pdf-to-ppt": pdf_to_ppt_handler,
    "image-converter": image_converter_handler,
    "heic-to-jpg": heic_to_jpg_handler,
}