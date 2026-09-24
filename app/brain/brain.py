from app.knowledge.store import KnowledgeStore
from app.memory import MemoryManager
from app.memory.auto_memory import AutoMemory
from app.memory.learning import ContinuousLearner
from app.tools.registry import load_defaults, run_tool
from .context import build_context
from .conversation import Conversation
from .prompts import SYSTEM_PROMPT
from .router import classify, tool_help


class Brain:
    def __init__(self, llm, knowledge=None, memory=None, max_history=12):
        self.llm = llm
        self.knowledge = knowledge or KnowledgeStore()
        self.memory = memory or MemoryManager()
        self.auto_memory = AutoMemory(self.memory)
        self.learner = ContinuousLearner(self.memory)
        self.conversation = Conversation(max_messages=max_history)
        load_defaults()

    def think(self, user_message, history=None):
        text = user_message.strip()
        if history is not None:
            self.conversation.clear()
            for item in history[-12:]:
                if item.get('role') == 'user': self.conversation.add_user(item.get('content',''))
                elif item.get('role') == 'assistant': self.conversation.add_assistant(item.get('content',''))
        if not text:
            return "Please enter a question or command."
        route = classify(text)
        if text.lower() in {"tools", "list tools", "tool help"}:
            return tool_help()
        if text.lower() in {"status", "system status"}:
            return self._status()
        self.conversation.add_user(text)
        learning = self.learner.learn(text)
        retrieved = build_context(self.knowledge, self.memory, text)
        if learning.candidate_id:
            prompt_note = (
                "\n\nLEARNING NOTE: This message was stored as a pending memory candidate "
                "because it may be durable but was not explicit enough to auto-confirm."
            )
        else:
            prompt_note = ""
        prompt = SYSTEM_PROMPT + prompt_note
        if retrieved.knowledge:
            prompt += "\n\nRetrieved project knowledge:\n" + retrieved.knowledge
        if retrieved.memory:
            prompt += "\n\nRelevant long-term memory:\n" + retrieved.memory
        tool_result = None
        if route.tool_name:
            prompt += (
                "\n\nThe router detected a calculation-related request. "
                "A deterministic tool is available, but it must be invoked by the application. "
                "Do not invent a numeric result if the application result is missing."
            )
            tool_result = self._try_tool(route.tool_name, text)
            if tool_result is not None:
                prompt += "\n\nDETERMINISTIC TOOL RESULT:\n" + tool_result
        messages = [{"role": "system", "content": prompt}, *self.conversation.get_messages()]
        try:
            reply = self.llm.chat(messages)
        except Exception as exc:
            # Deterministic tools remain usable when the LLM provider is unavailable,
            # including billing/quota exhaustion. Never hide a verified tool result.
            if tool_result is not None:
                reply = "LLM unavailable; returning the deterministic calculation result:\n\n" + tool_result
            else:
                reply = f"LLM request failed: {exc}"
        self.conversation.add_assistant(reply)
        if retrieved.sources:
            reply += "\n\nSources: " + ", ".join(retrieved.sources)
        return reply

    def _try_tool(self, tool_name, text):
        import re

        try:
            if tool_name == "molar_mass":
                match = re.search(r"(?:molar mass|molecular (?:weight|mass) of)\s+([A-Za-z0-9()]+)", text, re.I)
                if not match:
                    return None
                formula = match.group(1)
                value = run_tool(tool_name, formula=formula)
                return f"molar_mass({formula}) = {value:.6f} g/mol"

            if tool_name == "mass_percent":
                nums = re.findall(r"\d+(?:\.\d+)?", text)
                if len(nums) < 2:
                    return None
                part_mass, total_mass = map(float, nums[-2:])
                value = run_tool(tool_name, part_mass=part_mass, total_mass=total_mass)
                return f"mass_percent({part_mass}, {total_mass}) = {value:.6f}%"

            if tool_name == "formulation_solver":
                arabic_digits = "\u0660\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669"
                normalized = text.translate(str.maketrans(arabic_digits, "0123456789"))
                grade = re.search(r"(\d+(?:\.\d+)?)\s*[-–—/]\s*(\d+(?:\.\d+)?)\s*[-–—/]\s*(\d+(?:\.\d+)?)", normalized)
                batch = re.search(r"(\d+(?:\.\d+)?)\s*(kg|كيلو|كغ|طن|ton|tons)", normalized, re.I)
                if not grade or not batch:
                    return None
                batch_kg = float(batch.group(1)) * (1000.0 if batch.group(2).lower() in {"طن", "ton", "tons"} else 1.0)
                known = {
                    "urea": ("urea", "يوريا", "اليوريا"), "map": ("map", "ماب", "اماب"),
                    "mkp": ("mkp", "ام كي بي"), "sop": ("sop", "سوب", "كبريتات البوتاسيوم", "كبريتات بوتاسيوم"),
                    "nop": ("nop", "نوب"), "potassium nitrate": ("potassium nitrate", "نترات البوتاسيوم", "نترات بوتاسيوم"),
                    "ammonium nitrate": ("ammonium nitrate", "نترات الأمونيوم", "نترات الامونيوم"),
                    "ammonium sulfate": ("ammonium sulfate", "كبريتات الأمونيوم", "كبريتات الامونيوم"),
                    "urea phosphate": ("urea phosphate", "فوسفات اليوريا", "يوريا فوسفيت"),
                    "bentonite": ("bentonite", "بنتونايت", "بنتونيت"), "xanthan gum": ("xanthan gum", "زانثان", "صمغ الزانثان"),
                }
                lowered = normalized.lower()
                names = [canonical for canonical, aliases in known.items() if any(alias.lower() in lowered for alias in aliases)]
                if not names:
                    return None
                result = run_tool("formulation_solver", target="-".join(grade.groups()), batch_kg=batch_kg, material_names=names)
                return "FORMULATION RESULT: " + repr(result)

            if tool_name == "mass_to_moles":
                match = re.search(r"(\d+(?:\.\d+)?)\s*(?:g|grams?)\s+(?:of\s+)?([A-Za-z0-9()]+)", text, re.I)
                if not match:
                    return None
                mass_g = float(match.group(1))
                formula = match.group(2)
                value = run_tool(tool_name, mass_g=mass_g, formula=formula)
                return f"mass_to_moles({mass_g} g, {formula}) = {value:.8f} mol"

            return None
        except (ValueError, TypeError, KeyError):
            return None

    def _status(self):
        model = getattr(self.llm, "model", "unknown")
        knowledge_count = len(self.knowledge.list_documents())
        memory_count = self.memory.count()
        return (
            f"GHALI AI v0.1.0\n"
            f"LLM: {model}\n"
            f"Knowledge documents: {knowledge_count}\n"
            f"Memories: {memory_count}\n"
            f"Conversation messages: {len(self.conversation.get_messages())}"
        )
