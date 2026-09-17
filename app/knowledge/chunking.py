from dataclasses import dataclass


@dataclass(frozen=True)
class KnowledgeChunk:
    chunk_id: str
    text: str
    index: int


def split_text(text: str, max_chars: int = 800, overlap: int = 100) -> list[KnowledgeChunk]:
    clean = " ".join(text.split())
    if not clean:
        return []
    if max_chars <= 0 or overlap < 0 or overlap >= max_chars:
        raise ValueError("Invalid chunk size or overlap")

    chunks = []
    start = 0
    index = 0
    while start < len(clean):
        end = min(start + max_chars, len(clean))
        chunk_text = clean[start:end].strip()
        chunks.append(KnowledgeChunk(f"chunk-{index}", chunk_text, index))
        if end == len(clean):
            break
        start = end - overlap
        index += 1
    return chunks
