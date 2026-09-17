import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def load_module(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load test module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    total = failed = 0
    results = []
    for path in sorted(Path(__file__).parent.glob("test_*.py")):
        module = load_module(path)
        for name in sorted(dir(module)):
            if not name.startswith("test_"):
                continue
            function = getattr(module, name)
            if not callable(function):
                continue
            total += 1
            try:
                function()
                results.append(f"PASS {path.name}:{name}")
            except Exception as exc:
                failed += 1
                results.append(f"FAIL {path.name}:{name}: {exc!r}")
    print("\n".join(results))
    print(f"TOTAL={total} FAILED={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
