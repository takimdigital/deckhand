#!/usr/bin/env python3
"""try-on guard — the agent's refusal check BEFORE any swap write.

The overlay can be fooled or bypassed; this cannot be skipped. Before repointing anything, run:

    py scripts/tryon_guard.py check --project DIR --file ABS_OR_REL --line N \
        --candidate-slot SLOT [--element-slot SLOT] [--rescope]

exit 0 = allowed (prints the local binding to repoint); exit 4 = refused (prints {ok:false, code, reason});
exit 2 = usage. Enforces references/tryon.md: like-for-like slots, single components only in v1
(whole sections render children and must not be replaced), and no silent no-ops.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import templates_db as DB  # noqa: E402

REFUSE = 4
DB_PATH = HERE.parent / "data" / "templates.db"


def refuse(code: str, reason: str) -> dict:
    return {"ok": False, "code": code, "reason": "refused: " + reason + " Nothing written."}


def slot_kind(slot: str) -> str | None:
    con = DB.connect(DB_PATH)
    try:
        row = con.execute("SELECT slot_kind FROM registry_items WHERE slot = ? LIMIT 1", (slot,)).fetchone()
        return row[0] if row else None
    finally:
        con.close()


def element_region(lines: list[str], line: int) -> tuple[list[str] | None, str | None]:
    """The balanced JSX region of the element that starts at/just after the stamped line."""
    start = max(0, line - 1)
    name = None
    for i in range(start, min(len(lines), start + 4)):
        m = re.search(r"<\s*([A-Za-z][A-Za-z0-9_.-]*)", lines[i])
        if m:
            name, start = m.group(1), i
            break
    if not name:
        return None, None
    if re.search(r"<\s*%s\b[^>]*/>" % re.escape(name), lines[start], re.I):
        return lines[start:start + 3], name
    depth, end = 0, start
    tag_open = re.compile(r"<\s*%s\b" % re.escape(name), re.I)
    tag_close = re.compile(r"</\s*%s\s*>" % re.escape(name), re.I)
    for i in range(start, min(len(lines), start + 120)):
        depth += len(tag_open.findall(lines[i])) - len(tag_close.findall(lines[i]))
        end = i
        if depth <= 0 and i > start:
            break
    return lines[start:end + 1], name


def enclosing_component(lines: list[str], line: int) -> str | None:
    """Innermost Capitalized JSX element open above the stamped line (bounded, heuristic)."""
    stack: list[str] = []
    for i in range(max(0, line - 40), line):
        s = lines[i]
        for m in re.finditer(r"<\s*([A-Z][A-Za-z0-9_.]*)", s):
            if "/>" in s[m.end():]:
                continue                       # self-closed on this line: never an encloser
            stack.append(m.group(1))
        for m in re.finditer(r"</\s*([A-Z][A-Za-z0-9_.]*)\s*>", s):
            if stack and stack[-1] == m.group(1):
                stack.pop()
            elif m.group(1) in stack:
                stack.remove(m.group(1))
    return stack[-1] if stack else None


def is_imported(text: str, name: str) -> bool:
    return bool(re.search(r"import\s+(?:type\s+)?(?:\{[^}]*\b%s\b[^}]*\}|%s\b|\*\s+as\s+%s\b)"
                          % (re.escape(name), re.escape(name), re.escape(name)), text))


def project_base(project: str) -> str | None:
    """The project's primitive base, read from its own files (same rules as the catalog/scoping)."""
    try:
        import tryon_catalog as CAT  # local import: keep guard start-up lean
        return CAT.project_profile(Path(project)).get("base")
    except Exception:
        return None


def check(project: str, file: str, line: int, cand_slot: str,
          elem_slot: str | None, rescope: bool, cand_base: str | None = None) -> dict:
    p = Path(file)
    if not p.is_absolute():
        p = Path(project) / file
    if not p.exists():
        return refuse("ELEMENT_NOT_FOUND", "no such file: %s." % file)
    text = p.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    if not (1 <= line <= len(lines)):
        return refuse("ELEMENT_NOT_FOUND", "%s:%s is outside the file." % (p.name, line))

    kind = slot_kind(cand_slot)
    if kind == "block":
        return refuse("BLOCK_SLOT",
                      "'%s' is a whole section; v1 swaps single components like-for-like, and a section "
                      "swap would throw away the content it renders." % cand_slot)
    if elem_slot and elem_slot != cand_slot and not rescope:
        return refuse("SLOT_MISMATCH",
                      "the element is '%s' and the candidate is '%s'; a swap must be like-for-like "
                      "(the owner can confirm a re-scope in the panel)." % (elem_slot, cand_slot))
    # base compatibility: never repoint a Radix project at a Base UI component (or the reverse)
    # unless the owner explicitly confirmed they understand it needs a different setup.
    if cand_base and cand_base not in ("none", None) and not rescope:
        pbase = project_base(project)
        if pbase and pbase not in ("none", "unknown") and cand_base != pbase:
            return refuse("BASE_MISMATCH",
                          "that candidate is built for %s and this project uses %s; picking it would add "
                          "a second primitive system. The owner can confirm this in the panel." % (cand_base, pbase))

    region, tag = element_region(lines, line)
    if region is None:
        return refuse("BAD_ELEMENT", "no JSX element found at %s:%s." % (p.name, line))
    body = "\n".join(region)
    if tag and tag[0].islower() and ".map(" in body:
        return refuse("CONTAINER",
                      "<%s> at %s:%s renders a list of children (a .map( in its markup) - that is a "
                      "section, not a single component." % (tag, p.name, line))

    if tag and tag[0].isupper():
        local, how = tag, "declared at the click"
    else:
        local, how = enclosing_component(lines, line), "enclosing component"
    if not local:
        return refuse("INLINE",
                      "the element at %s:%s is plain markup written inline - there is no import to "
                      "repoint, so an automatic swap would hand-edit your JSX." % (p.name, line))
    if not is_imported(text, local.split(".")[0]):
        return refuse("NO_IMPORT", "'%s' is not imported by %s - nothing to repoint." % (local, p.name))

    return {"ok": True, "code": "ALLOWED", "local": local,
            "reason": "like-for-like: %s -> %s (%s)" % (cand_slot, local, how),
            "slot": cand_slot, "element_slot": elem_slot, "rescope": bool(rescope),
            "file": str(p), "line": line}


def main() -> int:
    ap = argparse.ArgumentParser(description="try-on guard (agent-side refusal before any write)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--project", required=True)
    c.add_argument("--file", required=True)
    c.add_argument("--line", type=int, required=True)
    c.add_argument("--candidate-slot", required=True)
    c.add_argument("--element-slot", default=None)
    c.add_argument("--candidate-base", default=None,
                   help="the candidate item's base from the request payload (base-ui/radix/aria/none)")
    c.add_argument("--rescope", action="store_true")
    a = ap.parse_args()
    if a.cmd != "check":
        print(json.dumps({"ok": False, "code": "USAGE"}))
        return 2
    out = check(a.project, a.file, a.line, a.candidate_slot, a.element_slot, a.rescope, a.candidate_base)
    print(json.dumps(out, ensure_ascii=False))
    return 0 if out.get("ok") else REFUSE


if __name__ == "__main__":
    sys.exit(main())
