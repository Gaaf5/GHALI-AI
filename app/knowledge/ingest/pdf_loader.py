from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover
    PdfReader = None


def load_pdf(path: str | Path) -> str:
    """Extract text from a PDF using pypdf."""
    if PdfReader is None:
        raise RuntimeError("PDF support requires the 'pypdf' package")

    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(file_path)

    reader = PdfReader(str(file_path))
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        if text:
            pages.append(text)

    return "\n\n".join(pages).strip()
