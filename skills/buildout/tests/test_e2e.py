"""End-to-end smoke: the whole try-on save loop, driven in a real headless Chrome over CDP.

The Node script it wraps (templates/tryon/test-e2e.mjs) builds its own static page + fake project
under a scratch dir, starts the helper and a static server, and drives Try → reply → Save → verify
→ library → reply, asserting the panel state at each step. It exits non-zero on any FAIL and prints
`N/N assertions passed` as its last line.

Skips cleanly when there is no Chrome to drive. No Python is spawned from here: the script picks its
own launcher (`py` on Windows, `python` elsewhere, `PYTHON` to override).
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parents[1]
SCRIPT = SKILL / "templates" / "tryon" / "test-e2e.mjs"
TIMEOUT_S = 300


def _chrome_candidates() -> list[str]:
    """The same set the Node script tries: --chrome/env first, then the platform defaults."""
    cands: list[str] = []
    if os.environ.get("CHROME_PATH"):
        cands.append(os.environ["CHROME_PATH"])
    if sys.platform == "win32":
        cands += [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                  r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"]
        local = os.environ.get("LOCALAPPDATA")
        if local:
            cands.append(os.path.join(local, "Google", "Chrome", "Application", "chrome.exe"))
    elif sys.platform == "darwin":
        cands.append("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    else:
        cands += ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"]
    return cands


def _find_chrome() -> str | None:
    for c in _chrome_candidates():
        if os.sep in c or "/" in c:
            if Path(c).is_file():
                return c
        else:
            found = shutil.which(c)
            if found:
                return found
    return None


def _tail(proc: subprocess.CompletedProcess) -> str:
    text = (proc.stdout or "") + (proc.stderr or "")
    if isinstance(text, bytes):
        text = text.decode("utf-8", "replace")
    return "\n".join(text.splitlines()[-15:])


def _run_smoke(node: str, chrome: str) -> subprocess.CompletedProcess:
    try:
        return subprocess.run([node, str(SCRIPT), "--chrome", chrome],
                              capture_output=True, text=True, cwd=str(SKILL), timeout=TIMEOUT_S)
    except subprocess.TimeoutExpired as exc:
        parts = []
        for chunk in (exc.stdout, exc.stderr):
            if chunk is None:
                continue
            parts.append(chunk.decode("utf-8", "replace") if isinstance(chunk, bytes) else chunk)
        text = "".join(parts)
        pytest.fail(f"e2e smoke did not finish within {TIMEOUT_S}s\n"
                    + "\n".join(text.splitlines()[-15:]))


def test_e2e_smoke():
    chrome = _find_chrome()
    if not chrome:
        pytest.skip("no Chrome found (set CHROME_PATH or install Chrome)")
    node = shutil.which("node")
    if not node:
        pytest.skip("no node on PATH")
    assert SCRIPT.is_file(), f"missing {SCRIPT}"

    out = _run_smoke(node, chrome)
    stdout = out.stdout or ""
    tail = _tail(out)
    if "SKIP: no chrome" in stdout:
        pytest.skip("the smoke found no Chrome to drive")

    assert out.returncode == 0, f"e2e smoke exited {out.returncode}\n{tail}"
    lines = [ln.strip() for ln in stdout.splitlines() if ln.strip()]
    assert lines, f"e2e smoke printed nothing\n{tail}"
    last = lines[-1]
    m = re.search(r"(\d+)/(\d+)\s+assertions passed", last)
    assert m, f"last line is not the 'N/N assertions passed' contract: {last!r}\n{tail}"
    passed, total = int(m.group(1)), int(m.group(2))
    assert passed == total, f"not every assertion passed: {last!r}\n{tail}"
    assert passed >= 21, f"fewer assertions than the smoke's floor (21): {last!r}\n{tail}"
