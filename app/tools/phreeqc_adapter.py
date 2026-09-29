"""PHREEQC/IPhreeqc adapter for GHALI-AI.

The adapter is optional: GHALI remains functional with its deterministic
screening engine when PHREEQC is unavailable. No silent fake PHREEQC results.
"""
from __future__ import annotations
import os, shutil, subprocess, tempfile
from pathlib import Path
from typing import Any

PHREEQC_NAMES = ("phreeqc.exe", "phreeqci.exe")

def discover_phreeqc() -> dict[str, Any]:
    candidates=[]
    for name in PHREEQC_NAMES:
        p=shutil.which(name)
        if p: candidates.append(p)
    roots=[Path(os.environ.get("PROGRAMFILES","C:\\Program Files")),
           Path(os.environ.get("PROGRAMFILES(X86)","C:\\Program Files (x86)"))]
    for root in roots:
        if root.exists():
            try:
                candidates.extend(str(p) for p in root.rglob("phreeqc.exe"))
            except OSError: pass
    unique=[]
    for p in candidates:
        if p not in unique: unique.append(p)
    return {"available":bool(unique), "executables":unique,
            "recommended_backend":"PHREEQC batch executable" if unique else None}

def _database_path(executable: str, requested: str | None) -> str | None:
    if requested and Path(requested).exists(): return str(Path(requested))
    exe=Path(executable).resolve()
    roots=[exe.parent, exe.parent/"database", exe.parent/"database_files"]
    for root in roots:
        for name in ("phreeqc.dat","pitzer.dat","sit.dat") if not requested else (requested,):
            p=root/name
            if p.exists(): return str(p)
    return None

def run_phreeqc(input_text: str, database: str | None = None, timeout_s: float = 30) -> dict[str, Any]:
    found=discover_phreeqc()
    if not found["available"]:
        return {"status":"unavailable","engine":"PHREEQC",
                "reason":"PHREEQC executable was not found on this machine.",
                "discovery":found}
    exe=found["executables"][0]
    with tempfile.TemporaryDirectory(prefix="ghali_phreeqc_") as td:
        td=Path(td); inp=td/"input.pqi"; out=td/"output.pqo"
        inp.write_text(input_text,encoding="utf-8")
        db=_database_path(exe,database)
        cmd=[exe,str(inp),str(out)]
        if db: cmd += ["-db",db]
        try:
            proc=subprocess.run(cmd,cwd=str(td),capture_output=True,text=True,timeout=timeout_s)
        except (OSError,subprocess.TimeoutExpired) as e:
            return {"status":"error","engine":"PHREEQC","error":str(e),"executable":exe}
        output=out.read_text(encoding="utf-8",errors="replace") if out.exists() else ""
        return {"status":"ok" if proc.returncode==0 else "error","engine":"PHREEQC",
                "returncode":proc.returncode,"executable":exe,"database":db,
                "stdout":proc.stdout[-8000:],"stderr":proc.stderr[-8000:],"output":output[-20000:]}
