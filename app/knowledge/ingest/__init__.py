from .dispatcher import ingest_file
from .docx_loader import load_docx
from .ingestor import ingest_docx, ingest_pdf, ingest_text
from .pdf_loader import load_pdf
from .text_loader import load_text

__all__ = [
    "ingest_file",
    "ingest_docx",
    "ingest_pdf",
    "ingest_text",
    "load_docx",
    "load_pdf",
    "load_text",
]
