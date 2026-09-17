from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievedContext:
    knowledge: str
    memory: str
    sources: list[str]


def _source_name(metadata, path):
    return metadata.get("title") or metadata.get("source") or path.name


def build_context(knowledge, memory, user_message, max_knowledge=3, max_memory=3):
    blocks = []
    sources = []
    for path, chunk, score in knowledge.search_chunks(
        user_message, limit=max_knowledge, max_chars=800, overlap=100
    ):
        metadata = knowledge.get_metadata(path)
        name = _source_name(metadata, path)
        blocks.append(
            f"Source: {name}\nDocument: {path.name}\n"
            f"Chunk: {chunk.index}\nRelevance: {score:.2f}\n{chunk.text}"
        )
        sources.append(name)

    rows = memory.recall(user_message, limit=max_memory)
    memory_blocks = [f"Memory ({row[1]}): {row[2]}" for row in rows]
    return RetrievedContext(
        knowledge="\n\n---\n\n".join(blocks),
        memory="\n".join(memory_blocks),
        sources=list(dict.fromkeys(sources)),
    )
