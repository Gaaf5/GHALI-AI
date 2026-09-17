from pathlib import Path

from app.knowledge.store import KnowledgeStore

from .ingestor import ingest_docx, ingest_pdf, ingest_text
from app.knowledge.json_loader import ingest_json


SUPPORTED_TYPES = {
    ".txt": "text",
    ".md": "text",
    ".pdf": "pdf",
    ".docx": "docx",
    ".json": "json",
}


def ingest_file(
    path: str | Path,
    store: KnowledgeStore,
    title: str | None = None,
    source: str = "file",
):
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    if suffix not in SUPPORTED_TYPES:
        raise ValueError(f"Unsupported knowledge file type: {suffix or '<none>'}")

    document_type = SUPPORTED_TYPES[suffix]
    if document_type == "pdf":
        return ingest_pdf(file_path, store, title=title, source=source)
    if document_type == "docx":
        return ingest_docx(file_path, store, title=title, source=source)
    if document_type == "json":
        return ingest_json(file_path, store, source=source)
    return ingest_text(
        file_path,
        store,
        title=title,
        source=source,
        document_type=document_type,
    )
