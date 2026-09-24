"""Pack-wide line budgets for every skill in skills/ (the pack law).

SKILL.md <=500 lines, every reference under a skill's references/ <=150 lines.
The law used to be enforced for buildout only (test_budget_lines.py, which keeps
buildout's wiring checks); this file holds the whole pack to it.

Over-budget files frozen in ALLOW are a ratchet: the recorded number is their
current size and can only go down. A file that grows past its recorded number
fails; a file that shrinks below the normal limit can be deleted from ALLOW
entirely and falls back under the standard rule.
"""
from __future__ import annotations

from pathlib import Path

SKILLS = Path(__file__).resolve().parents[2]  # the skills/ dir
SKILL_LIMIT = 500
REF_LIMIT = 150

# Frozen at today's size (2026-09-24). Shrink-only: never raise a number here,
# delete entries instead. vps-ops refs were knowingly over 150 before the
# ratchet existed.
ALLOW = {
    "vps-ops/references/00-user-checklist.md": 169,
    "vps-ops/references/10-bootstrap-vps.md": 273,
    "vps-ops/references/20-domain-dns-ssl.md": 162,
    "vps-ops/references/30-deploy-app.md": 253,
    "vps-ops/references/40-change-pipeline.md": 206,
}


def limit_for(name: str) -> int:
    return SKILL_LIMIT if name.rsplit("/", 1)[-1] == "SKILL.md" else REF_LIMIT


def pack_files(root: Path = SKILLS) -> list[str]:
    """Every file the law covers, as names relative to skills/: each skill's
    SKILL.md and every .md under any skill's references/."""
    root = Path(root)
    out = []
    for md in sorted(root.rglob("*.md")):
        rel = md.relative_to(root).as_posix()
        if rel.endswith("SKILL.md") or "/references/" in rel:
            out.append(rel)
    return out


def over_budget(paths, allow=ALLOW, root: Path = SKILLS) -> list[list]:
    """Pure checker -> [[name, lines, limit], ...] for every file over budget.

    ``paths`` are names relative to ``root`` (as in ALLOW) or absolute paths.
    An allowlisted name is capped at its frozen number; everything else at the
    standard limit (SKILL.md 500, references 150)."""
    over = []
    for raw in paths:
        name = Path(raw).as_posix()
        p = Path(raw)
        if not p.is_absolute():
            p = Path(root) / p
        lines = len(p.read_text(encoding="utf-8").splitlines())
        frozen = allow.get(name)
        if frozen is not None:
            if lines > frozen:
                over.append([name, lines, frozen])
            continue
        limit = limit_for(name)
        if lines > limit:
            over.append([name, lines, limit])
    return over


def test_pack_budgets_hold():
    over = over_budget(pack_files())
    assert not over, f"over budget (name, lines, limit): {over}"


def test_over_budget_flags_an_oversized_copy(tmp_path):
    """Known-bad input: a ref copy with 200 lines appended must be flagged."""
    src = SKILLS / "vps-ops" / "references" / "00-user-checklist.md"
    assert src.is_file()
    base = len(src.read_text(encoding="utf-8").splitlines())
    big = tmp_path / "00-user-checklist.md"
    big.write_text(src.read_text(encoding="utf-8").rstrip("\n") + "\n" + "pad\n" * 200,
                   encoding="utf-8")
    over = over_budget([big], allow={})
    assert over == [[big.as_posix(), base + 200, REF_LIMIT]], over


def test_allowlist_is_a_ratchet_shrink_only(tmp_path):
    """An allowlisted file may shrink but may never grow past its frozen size."""
    here = "some-skill/references/x.md"
    root = tmp_path / "skills"
    f = root / "some-skill" / "references" / "x.md"
    f.parent.mkdir(parents=True)
    f.write_text("x\n" * 160, encoding="utf-8")
    assert over_budget([here], allow={here: 170}, root=root) == []
    f.write_text("x\n" * 171, encoding="utf-8")          # grew past the freeze
    assert over_budget([here], allow={here: 170}, root=root) == [[here, 171, 170]]
    f.write_text("x\n" * 100, encoding="utf-8")          # shrunk: fine
    assert over_budget([here], allow={here: 170}, root=root) == []
