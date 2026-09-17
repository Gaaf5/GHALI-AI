import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from app.brain.brain import Brain
from app.knowledge.store import KnowledgeStore
from app.memory import MemoryManager
from app.llm.base import BaseLLM

class Dummy(BaseLLM):
    def chat(self, messages):
        print('LLM_MESSAGES=', repr(messages[0]))
        return 'OK'

m=MemoryManager()
b=Brain(Dummy(), KnowledgeStore(), m)
print('ANSWER=', repr(b.think('calculate mass percent 5 g in 100 g')))
m.close()
