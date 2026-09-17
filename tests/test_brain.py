from app.brain.brain import Brain
from app.knowledge.store import KnowledgeStore
from app.llm.base import BaseLLM
from app.memory import MemoryManager


class DummyLLM(BaseLLM):
    def chat(self, messages):
        assert messages[0]["role"] == "system"
        return "OK"


def test_brain_smoke():
    memory = MemoryManager()
    brain = Brain(DummyLLM(), KnowledgeStore(), memory)
    assert brain.think("hello") == "OK"
    assert len(brain.conversation.get_messages()) == 2
    memory.close()
