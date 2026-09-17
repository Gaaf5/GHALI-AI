import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.brain.brain import Brain
from app.knowledge.store import KnowledgeStore
from app.memory import MemoryManager
from app.llm.base import BaseLLM


class DummyLLM(BaseLLM):
    def chat(self, messages):
        print("SYSTEM:", repr(messages[0]["content"]))
        return "TOOL_OK"


memory = MemoryManager()
brain = Brain(DummyLLM(), KnowledgeStore(), memory)
print("ANSWER:", brain.think("calculate mass percent 5 g in 100 g"))
memory.close()
