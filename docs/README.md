# GHALI AI

Local-first industrial chemistry and fertilizer assistant.

## Release

Current release: `0.1.0`.

The application combines local LLM inference, source-backed knowledge,
long-term memory, and deterministic chemistry/engineering tools.

## Requirements

- Windows with Python 3.14 or compatible Python 3.x.
- Ollama installed and running locally.
- `qwen2.5:3b` pulled for the default model.

## Start

```powershell
Set-Location 'C:\Users\ghaly\OneDrive\Desktop\GHALI-AI'
& '.\.venv\Scripts\python.exe' main.py
```

## Commands

- `knowledge` opens knowledge management.
- `memory` opens persistent-memory management.
- `clear` clears the current conversation.
- `exit` closes the application.

## Knowledge ingestion

TXT, MD, PDF, and DOCX are supported:

```text
Knowledge> ingest <path> [source]
Knowledge> search <query>
Knowledge> validate
Knowledge> list
```

## Deterministic tools

The tool layer includes formula parsing and molar mass, mole/mass conversion,
mass percentage, solution calculations, NPK grade conversion, unit conversion,
and basic mass-balance composition.

## Quality gates

Before release, run:

```powershell
& '.\.venv\Scripts\python.exe' -m compileall -q app main.py
& '.\.venv\Scripts\python.exe' tests\run_all.py
& '.\.venv\Scripts\python.exe' tests\smoke_test.py
& '.\.venv\Scripts\python.exe' -m pip check
```

The project is local-first. Factory-specific knowledge should be deliberately
supplied and validated before it is treated as authoritative.
