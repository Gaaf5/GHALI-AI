from app.brain.brain import Brain
from app.core.settings import APP_NAME, VERSION
from app.database.database import Database
from app.llm.factory import create_llm
from app.knowledge.store import KnowledgeStore
from app.knowledge.cli import KnowledgeCLI
from app.memory import MemoryManager
from app.memory.manager import MemoryCLI


def _configure_console():
    import sys

    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def _memory_mode(memory_cli):
    print("\nMemory Management")
    print("Type 'help' for commands or 'back' to return.")
    while True:
        command_line = input("Memory> ").strip()
        if not command_line:
            continue
        if command_line.lower() in {"back", "exit"}:
            return
        parts = command_line.split()
        command, args = parts[0], parts[1:]
        try:
            print(memory_cli.run_command(command, *args))
        except Exception as exc:
            print(f"Memory ERROR: {exc}")


def _knowledge_mode(knowledge_cli):
    print("\nKnowledge Management")
    print("Type 'help' for commands or 'back' to return.")
    while True:
        command_line = input("Knowledge> ").strip()
        if not command_line:
            continue
        if command_line.lower() in {"back", "exit"}:
            return
        parts = command_line.split()
        command, args = parts[0], parts[1:]
        try:
            print(knowledge_cli.run_command(command, *args))
        except Exception as exc:
            print(f"Knowledge ERROR: {exc}")


def main():
    _configure_console()
    db = Database()
    db.create_tables()

    llm = create_llm()
    knowledge = KnowledgeStore()
    knowledge_cli = KnowledgeCLI(knowledge)
    memory = MemoryManager()
    memory_cli = MemoryCLI(memory)
    brain = Brain(llm, knowledge, memory)

    print("=" * 40)
    print(APP_NAME)
    print(f"Version: {VERSION}")
    print("Local model: qwen2.5:3b")
    print("Type 'knowledge' for knowledge management.")
    print("Type 'memory' for memory management.")
    print("Type 'exit' or 'quit' to stop.")
    print("=" * 40)

    try:
        while True:
            user = input("\nYou: ").strip()

            if user.lower() in ["exit", "quit"]:
                print("Goodbye!")
                break

            if user.lower() == "knowledge":
                _knowledge_mode(knowledge_cli)
                continue

            if user.lower() == "memory":
                _memory_mode(memory_cli)
                continue

            if user.lower() in {"/clear", "clear chat", "clear"}:
                brain.conversation.clear()
                print("Conversation cleared.")
                continue

            if not user:
                continue

            try:
                answer = brain.think(user)
                print(f"\nGHALI AI: {answer}")
            except Exception as exc:
                print(f"\nGHALI AI ERROR: {exc}")
    finally:
        memory.close()
        db.close()


if __name__ == "__main__":
    main()
