from pathlib import Path

from app.knowledge.store import KnowledgeDocument, KnowledgeStore

from .text_loader import load_text


def ingest_text(
    path: str | Path,
    store: KnowledgeStore,
    title: str | None = None,
    source: str = "file",
    document_type: str = "text",
) -> Path:
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(file_path)

    document_title = title or file_path.stem.replace("_", " ").title()
    content = load_text(file_path)
    if not content:
        raise ValueError(f"Empty knowledge document: {file_path}")

    duplicates = store.find_duplicate_content(content)
    if duplicates:
        return duplicates[0]

    document = KnowledgeDocument(
        title=document_title,
        content=content,
        source=source,
        document_type=document_type,
    )
    return store.add(document)


def ingest_pdf(
    path: str | Path,
    store: KnowledgeStore,
    title: str | None = None,
    source: str = "file",
    document_type: str = "pdf",
) -> Path:
    from .pdf_loader import load_pdf

    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(file_path)

    document_title = title or file_path.stem.replace("_", " ").title()
    content = load_pdf(file_path)
    if not content:
        raise ValueError(f"Empty PDF knowledge document: {file_path}")

    duplicates = store.find_duplicate_content(content)
    if duplicates:
        return duplicates[0]

    document = KnowledgeDocument(
        title=document_title,
        content=content,
        source=source,
        document_type=document_type,
    )
    return store.add(document)


def ingest_docx(
    path: str | Path,
    store: KnowledgeStore,
    title: str | None = None,
    source: str = "file",
    document_type: str = "docx",
) -> Path:
    from .docx_loader import load_docx

    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(file_path)

    document_title = title or file_path.stem.replace("_", " ").title()
    content = load_docx(file_path)
    if not content:
        raise ValueError(f"Empty DOCX knowledge document: {file_path}")

    duplicates = store.find_duplicate_content(content)
    if duplicates:
        return duplicates[0]

    document = KnowledgeDocument(
        title=document_title,
        content=content,
        source=source,
        document_type=document_type,
    )
    return store.add(document)
