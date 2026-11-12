"""只读抓帧封装：调用 scripts/capture-lol.ps1。

边界：只起子进程跑只读抓帧脚本，不点击、不注入、不读游戏进程内存。
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PS1 = REPO_ROOT / "scripts" / "capture-lol.ps1"


def _powershell_exe() -> str:
    """定位 Windows PowerShell 可执行文件（System32 优先，避免 PATH 缺失）。"""
    system_ps = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
    if os.path.exists(system_ps):
        return system_ps
    return shutil.which("powershell.exe") or "powershell.exe"


def capture_frame(width: int = 1600, out: str | None = None, timeout: int = 30) -> dict:
    """抓一帧，返回结果字典。

    返回字段：ok / frame_path / mode / elapsed_ms / raw / error。
    """
    out = out or str(Path(tempfile.gettempdir()) / "lol_frame.jpg")

    if not PS1.exists():
        return {"ok": False, "frame_path": None, "mode": None,
                "elapsed_ms": None, "raw": "", "error": f"抓帧脚本不存在: {PS1}"}

    cmd = [
        _powershell_exe(),
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(PS1),
        "-Width",
        str(width),
        "-Out",
        out,
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "frame_path": None, "mode": None,
                "elapsed_ms": None, "raw": "", "error": "抓帧超时（30s）"}

    raw = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
    result: dict = {
        "ok": proc.returncode == 0,
        "frame_path": out if proc.returncode == 0 else None,
        "mode": None,
        "elapsed_ms": None,
        "raw": raw,
        "error": None,
    }

    if proc.returncode != 0:
        result["error"] = (proc.stderr or proc.stdout or "脚本退出码非零").strip()
        return result

    m_mode = re.search(r"mode=(\w+)", raw)
    if m_mode:
        result["mode"] = m_mode.group(1)

    m_ms = re.search(r"(\d+)\s*ms", raw)
    if m_ms:
        result["elapsed_ms"] = int(m_ms.group(1))

    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    if lines:
        result["frame_path"] = lines[-1]

    return result
