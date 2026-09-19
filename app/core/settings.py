import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

APP_NAME = "GHALI AI"
VERSION = "0.1.0"
LLM_PROVIDER = os.getenv("GHALI_LLM_PROVIDER", "ollama")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.2"))
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "256"))
KNOWLEDGE_PATH = Path(os.getenv("GHALI_KNOWLEDGE_PATH", "data/knowledge"))
DATABASE_PATH = Path(os.getenv("GHALI_DATABASE_PATH", "data/ghali.db"))

PORT = int(os.getenv("PORT", "8765"))
