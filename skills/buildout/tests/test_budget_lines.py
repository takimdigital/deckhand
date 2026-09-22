"""Budget + wiring checks for the buildout skill.

Budgets are pack law: SKILL.md <=500 lines, each ref <=~150 lines.
Wiring: the new map/direction refs exist and SKILL.md routes to them
(so the pieces can never be silently dropped).
"""
from __future__ import annotations

from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
REFS = SKILL / "references" / "buildout"


def test_skill_md_under_500_lines():
    lines = (SKILL / "SKILL.md").read_text(encoding="utf-8").splitlines()
    assert len(lines) <= 500, f"SKILL.md is {len(lines)} lines"


def test_every_ref_under_150_lines():
    over = {}
    for f in sorted((SKILL / "references").rglob("*.md")):
        n = len(f.read_text(encoding="utf-8").splitlines())
        if n > 150:
            over[str(f.relative_to(SKILL))] = n
    assert not over, f"refs over budget: {over}"


def test_new_refs_exist():
    assert (REFS / "45-map.md").is_file()
    assert (REFS / "50-direction-competition.md").is_file()


def test_skill_routes_to_map_and_direction():
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    for needle in ("45-map.md", "50-direction-competition.md", "map_check.py"):
        assert needle in text, f"SKILL.md no longer routes to {needle}"


def test_map_gate_script_exists():
    assert (SKILL / "scripts" / "map_check.py").is_file()
