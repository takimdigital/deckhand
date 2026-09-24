"""Budget + wiring checks for the buildout skill (Template Factory).

Budgets are pack law: SKILL.md <=500 lines, each ref <=~150 lines.
Wiring: the factory refs and scripts exist, SKILL.md routes to them, and the
removed machinery may never quietly reappear.
"""
from __future__ import annotations

import json
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
FACTORY_REFS = ["00-intake.md", "10-match.md", "20-clone.md", "30-swap.md",
                "40-rebrand.md", "50-verify-deploy.md"]
FACTORY_SCRIPTS = ["templates_db.py", "template_intake.py", "factory_clone.py", "swap_check.py", "_tpl_lib.py"]
REMOVED = ["map_check.py", "registry_sync.py", "styles_fetch.py", "styles_pick.py", "assemble_pick.py",
           "45-map.md", "50-direction-competition.md", "10-design-assembly.md", "15-reference-library.md",
           "20-component-library.md", "30-design-audit.md", "01-start-from-boilerplate.md",
           "00-start-from-boilerplate.md", "design-audit", "registries.snapshot", "data/styles"]


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


def test_factory_refs_exist():
    for name in FACTORY_REFS:
        assert (SKILL / "references" / "factory" / name).is_file(), f"missing factory ref {name}"


def test_factory_scripts_exist():
    for name in FACTORY_SCRIPTS:
        assert (SKILL / "scripts" / name).is_file(), f"missing factory script {name}"


def test_skill_routes_to_factory():
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    for needle in FACTORY_REFS + ["templates_db.py", "template_intake.py", "factory_clone.py", "swap_check.py"]:
        assert needle in text, f"SKILL.md no longer routes to {needle}"


def test_removed_machinery_does_not_reappear():
    """The 0.8.0 deletions are permanent: SKILL.md must not reference them again
    (its history section may name them once, under 'What 0.8.0 removed')."""
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    routing = text.split("## What 0.8.0 removed")[0]
    for needle in REMOVED:
        assert needle not in routing, f"SKILL.md routes to removed machinery: {needle}"


def test_design_generation_inputs_are_gone():
    for rel in ("data/styles", "data/items", "data/registries.snapshot.json",
                "references/buildout", "templates/design-audit"):
        assert not (SKILL / rel).exists(), f"{rel} should have been deleted in 0.8.0"


def test_registry_seed_is_present_and_parsable():
    import json
    seed = json.loads((SKILL / "data" / "templates.seed.json").read_text(encoding="utf-8"))
    rows = seed["templates"]
    assert len(rows) >= 8
    assert all(r["url"].startswith("https://github.com/") for r in rows)


def test_tryon_is_wired():
    """The try-on tool ships wired or not at all: ref routed, scripts named, templates present."""
    assert (SKILL / "references" / "tryon.md").is_file()
    assert (SKILL / "references" / "library.md").is_file()
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    routing = text.split("## What 0.8.0 removed")[0]
    for needle in ("references/tryon.md", "references/library.md", "tryon_intake.py", "tryon_catalog.py",
                   "tryon_server.py", "tryon_install.py", "tryon_guard.py", "library_import.py",
                   "templates/tryon/swap.mjs"):
        assert needle in routing, f"SKILL.md no longer routes to {needle}"
    for f in ("loader.cjs", "overlay.js", "swap.mjs", "test-swap.mjs", "test-ladder.cjs", "tryon-dev.tsx"):
        assert (SKILL / "templates" / "tryon" / f).is_file(), f"missing templates/tryon/{f}"
    for s in ("tryon_intake.py", "tryon_catalog.py", "tryon_server.py", "tryon_install.py",
              "tryon_guard.py", "library_import.py"):
        assert (SKILL / "scripts" / s).is_file(), f"missing scripts/{s}"
    roster = json.loads((SKILL / "data" / "registries.json").read_text(encoding="utf-8"))
    usable = [r for r in roster["registries"] if r.get("status", "ok") == "ok"]
    assert usable, "the registry roster must carry usable registries"
    assert all(r["license"] in ("MIT", "Apache-2.0") for r in usable), "licence gate on usable registries"
    assert roster["refusals"], "the refused list is the licence gate's evidence"
