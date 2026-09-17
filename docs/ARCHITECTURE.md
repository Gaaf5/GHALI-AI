# GHALI AI Architecture

## Mission
GHALI AI is a local-first technical assistant focused on industrial chemistry,
fertilizers, manufacturing, calculations, and process troubleshooting.

## Layers

- `app/brain`: conversation orchestration and retrieval context.
- `app/knowledge`: source-backed document ingestion, chunking, and retrieval.
- `app/memory`: durable user/project memory with conservative auto-capture.
- `app/tools`: deterministic chemistry, NPK, unit, solution, and mass-balance tools.
- `app/llm`: provider abstraction with local Ollama and optional OpenAI.
- `app/database`: SQLite persistence primitives.
- `tests`: executable smoke coverage.

## Data flow

User -> Brain -> knowledge/memory retrieval -> system context -> LLM -> response.

Deterministic calculations should be handled by `app/tools` instead of asking the
language model to invent arithmetic.

## Knowledge policy

Technical facts should be source-backed where possible. User/project memory is
context, not authoritative technical evidence. Factory-specific information should
only be added when it is intentionally supplied and safe to store.

## Local-first operation

Ollama is the default provider. The application does not require internet access
for ordinary local inference or local knowledge retrieval.
