# GHALI AI

GHALI AI is a local-first chemistry and fertilizer assistant with a raw-material database, NPK formulation solver, liquid-formulation screening, knowledge storage, and persistent memory. The repository also contains a browser-based manufacturing/lab interface.

## Requirements

- Windows 10/11 or a compatible Python environment
- Python 3.11+ recommended
- Dependencies from `requirements.txt`
- Optional: Ollama and a locally pulled model for offline/local chat
- Optional: provider API key if using a cloud LLM

## Setup (Windows PowerShell)

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and select a configured LLM provider. For local Ollama, install Ollama separately, pull the configured model, and make sure its service is running. Cloud providers require a valid API key; never commit secrets into Git.

## Run

Interactive terminal assistant:

```powershell
.\.venv\Scripts\python.exe main.py
```

Browser interface:

```powershell
.\.venv\Scripts\python.exe run_ui.py
```

Open `http://127.0.0.1:8765` on the same computer. Keep the interface bound to localhost for personal use unless authentication, strong credentials, network exposure, and deployment settings have been reviewed. Do not expose a development instance directly to the public internet.

## Configuration

Common environment variables:

- `GHALI_LLM_PROVIDER`: configured provider, default `ollama`
- `OLLAMA_MODEL`, `OLLAMA_URL`: local model configuration
- `OPENAI_API_KEY`, `GEMINI_API_KEY`, `MISTRAL_API_KEY`, `GROQ_API_KEY`, `OPENROUTER_API_KEY`: optional provider credentials
- `GHALI_DATABASE_PATH`: SQLite database path, default `data/ghali.db`
- `GHALI_KNOWLEDGE_PATH`: knowledge store path, default `data/knowledge`
- `HOST`, `PORT`: browser server bind address and port

Use `.env.example` as a template only. Replace placeholder values with valid settings. Do not share the real `.env` file.

## Tests and checks

Run the repository's lightweight test runner:

```powershell
.\.venv\Scripts\python.exe tests\run_all.py
.\.venv\Scripts\python.exe tests\smoke_test.py
.\.venv\Scripts\python.exe -m compileall -q app tests
git diff --check
```

The test runner invokes `test_*` functions from `tests/test_*.py`. It is intentionally lightweight; it does not replace integration tests with real provider credentials or independent chemical validation.

## Chemistry and manufacturing safety

- NPK grades are mass percentages of N, P2O5, and K2O unless an API explicitly says otherwise.
- Confirm each raw material's assay, moisture, hydrate form, and nutrient analysis against the supplier's current certificate of analysis before production.
- Solubility and compatibility screening are estimates. Mixed-electrolyte systems, temperature effects, pH, order of addition, and aging can change outcomes.
- Verify laboratory predictions with controlled bench tests, mass balance, measured density/final volume, and relevant QC tests before scaling up.
- Production orders and theoretical nutrient balances are planning aids, not a substitute for approved SOPs, EHS controls, or release testing.

## Current limitations

A passing automated suite proves only that covered software behaviors pass. It does not establish chemical accuracy for every formulation, cloud-provider connectivity, production readiness, or Android APK availability. Those require separate validation and packaging work.
