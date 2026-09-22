"""Tests for scripts/map_check.py — the map completeness gate.

Every rule gets a known-bad input that MUST fail (the field-test lesson:
a gate that cannot fail is not a gate). The good fixture doubles as the
lean spec-mode toy map.
"""
from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("map_check", SKILL / "scripts" / "map_check.py")
map_check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(map_check)

FIX = SKILL / "tests" / "fixtures" / "map-lean"


def _copy(tmp_path: Path) -> Path:
    d = tmp_path / "map"
    shutil.copytree(FIX, d)
    return d


def _run(d: Path, capsys) -> tuple[int, str]:
    rc = map_check.main(["--map", str(d)])
    return rc, capsys.readouterr().out


def _edit(p: Path, old: str, new: str) -> None:
    text = p.read_text(encoding="utf-8")
    assert old in text, f"fixture drifted: {old!r} not in {p.name}"
    p.write_text(text.replace(old, new), encoding="utf-8")


# ---------------------------------------------------------------- happy paths

def test_good_lean_map_passes(tmp_path, capsys):
    rc, out = _run(_copy(tmp_path), capsys)
    assert rc == 0, out
    assert "PASS" in out


def test_no_map_dir_skips_not_errors(tmp_path, capsys):
    rc, out = _run(tmp_path / "nope", capsys)
    assert rc == 0
    assert "SKIP" in out


def test_json_output_shape(tmp_path, capsys):
    rc = map_check.main(["--map", str(_copy(tmp_path)), "--json"])
    out = capsys.readouterr().out
    assert rc == 0
    assert '"status": "pass"' in out


# ------------------------------------------------- known-bad: each MUST fail

def test_missing_charter_fails(tmp_path, capsys):
    d = _copy(tmp_path)
    (d / "charters" / "faq.md").unlink()
    rc, out = _run(d, capsys)
    assert rc == 1 and "R3" in out and "faq" in out


def test_extra_charter_not_in_inventory_fails(tmp_path, capsys):
    d = _copy(tmp_path)
    shutil.copy(d / "charters" / "faq.md", d / "charters" / "gallery.md")
    rc, out = _run(d, capsys)
    assert rc == 1 and "R3" in out and "gallery" in out


def test_inventory_item_without_source_fails(tmp_path, capsys):
    d = _copy(tmp_path)
    _edit(d / "inventory.md", " · source: brief", "")
    rc, out = _run(d, capsys)
    assert rc == 1 and "R2" in out and "source" in out


def test_missing_depth_declaration_fails(tmp_path, capsys):
    d = _copy(tmp_path)
    _edit(d / "summary.md", "depth: lean\n", "")
    rc, out = _run(d, capsys)
    assert rc == 1 and "R1" in out and "depth" in out


def test_silent_blank_in_charter_fails(tmp_path, capsys):
    d = _copy(tmp_path)
    with open(d / "charters" / "faq.md", "a", encoding="utf-8") as fh:
        fh.write("\naarrr_stage:\n")
    rc, out = _run(d, capsys)
    assert rc == 1 and "R4" in out and "silent blank" in out


def test_unfilled_placeholder_fails(tmp_path, capsys):
    d = _copy(tmp_path)
    with open(d / "charters" / "faq.md", "a", encoding="utf-8") as fh:
        fh.write("\nnote: <to be decided>\n")
    rc, out = _run(d, capsys)
    assert rc == 1 and "R7" in out


def test_flow_dead_end_fails(tmp_path, capsys):
    d = _copy(tmp_path)
    _edit(d / "flows" / "acquisition.md", "dead_ends_found: []",
          "dead_ends_found: [booking form silently loses the request]")
    rc, out = _run(d, capsys)
    assert rc == 1 and "R5" in out and "dead_ends_found" in out


def test_merged_flows_fail(tmp_path, capsys):
    d = _copy(tmp_path)
    with open(d / "flows" / "acquisition.md", "a", encoding="utf-8") as fh:
        fh.write("\n# FLOW_MAP: retention\nscreens: []\n")
    rc, out = _run(d, capsys)
    assert rc == 1 and "R5" in out and "merged" in out


def test_empty_next_action_fails(tmp_path, capsys):
    d = _copy(tmp_path)
    _edit(d / "flows" / "acquisition.md", "-> next_action: tap a walk option or the CTA",
          "-> next_action: ")
    rc, out = _run(d, capsys)
    assert rc == 1 and "R5" in out and "next_action" in out


def test_missing_core_category_fails(tmp_path, capsys):
    d = _copy(tmp_path)
    lines = (d / "edges" / "acquisition.md").read_text(encoding="utf-8").splitlines(True)
    kept = [ln for ln in lines if not ln.startswith("| error |")]
    assert len(kept) == len(lines) - 1
    (d / "edges" / "acquisition.md").write_text("".join(kept), encoding="utf-8")
    rc, out = _run(d, capsys)
    assert rc == 1 and "R6" in out and "error" in out


def test_dead_end_y_in_edges_fails(tmp_path, capsys):
    d = _copy(tmp_path)
    _edit(d / "edges" / "acquisition.md",
          "| error | Y | booking-form send failure | N | - |",
          "| error | Y | booking-form send failure | Y | - |")
    rc, out = _run(d, capsys)
    assert rc == 1 and "R6" in out and "dead-end" in out


def test_empty_edge_cell_fails(tmp_path, capsys):
    d = _copy(tmp_path)
    _edit(d / "edges" / "acquisition.md",
          "| interruption | Y | booking-form back button keeps values | N | - |",
          "| interruption | Y |  | N | - |")
    rc, out = _run(d, capsys)
    assert rc == 1 and "R6" in out and "empty cell" in out


def test_status_tag_leftover_fails(tmp_path, capsys):
    d = _copy(tmp_path)
    with open(d / "charters" / "booking-form.md", "a", encoding="utf-8") as fh:
        fh.write("\nnotes: [STATUS]\n")
    rc, out = _run(d, capsys)
    assert rc == 1 and "R7" in out and "STATUS" in out


def test_full_depth_accepts_parenthesized_category_names(tmp_path, capsys):
    """Template labels carry suffixes: `lifecycle(first/repeat/lapsed)`."""
    d = _copy(tmp_path)
    _edit(d / "summary.md", "depth: lean", "depth: full")
    e = d / "edges" / "acquisition.md"
    t = e.read_text(encoding="utf-8")
    t = t.replace("| lifecycle |", "| lifecycle(first/repeat/lapsed) |")
    t = t.replace("| ai_agent |", "| ai_agent(if DUAL_AUDIENCE!=no) |")
    e.write_text(t, encoding="utf-8")
    rc, out = _run(d, capsys)
    assert rc == 0, out


def test_flow_dead_ends_found_bare_key_with_block_still_ok(tmp_path, capsys):
    """Block keys (step_sequence:, screens:) must NOT read as silent blanks."""
    rc, out = _run(_copy(tmp_path), capsys)
    assert rc == 0, out
    assert "R4" not in out


def test_missing_map_version_fails(tmp_path, capsys):
    d = _copy(tmp_path)
    _edit(d / "summary.md", "map_version: 1\n", "")
    rc, out = _run(d, capsys)
    assert rc == 1 and "map_version" in out


def test_tbd_marker_fails(tmp_path, capsys):
    d = _copy(tmp_path)
    with open(d / "charters" / "faq.md", "a", encoding="utf-8") as fh:
        fh.write("\ncontent_notes: TBD after client call\n")
    rc, out = _run(d, capsys)
    assert rc == 1 and "R7" in out and "unresolved marker" in out


# ------------------------------------------------- direction arm (ref 50 gate)

FIXD = SKILL / "tests" / "fixtures" / "freeze-project"


def _proj(tmp_path: Path) -> Path:
    d = tmp_path / "proj"
    shutil.copytree(FIXD, d)
    return d


def _run_dir(d: Path, capsys, extra=None) -> tuple[int, str]:
    rc = map_check.main(["--direction", str(d / "direction")] + (extra or []))
    return rc, capsys.readouterr().out


def test_direction_good_passes(tmp_path, capsys):
    rc, out = _run_dir(_proj(tmp_path), capsys)
    assert rc == 0, out
    assert "PASS" in out


def test_direction_missing_skips(tmp_path, capsys):
    rc, out = _run_dir(tmp_path / "nope", capsys)
    assert rc == 0
    assert "SKIP" in out and "single-designer" in out


def test_direction_missing_draft_fails(tmp_path, capsys):
    d = _proj(tmp_path)
    (d / "direction" / "A.md").unlink()
    rc, out = _run_dir(d, capsys)
    assert rc == 1 and "D1" in out and "A.md" in out


def test_direction_forks_header_lacks_criterion_fails(tmp_path, capsys):
    d = _proj(tmp_path)
    _edit(d / "direction" / "forks.md",
          "| # | fork | criterion (pre-committed) | position A |",
          "| # | fork | position A |")
    rc, out = _run_dir(d, capsys)
    assert rc == 1 and "criterion" in out


def test_direction_forks_empty_resolution_fails(tmp_path, capsys):
    d = _proj(tmp_path)
    _edit(d / "direction" / "forks.md", "resolved — cool stone (acceptance delta)", "")
    rc, out = _run_dir(d, capsys)
    assert rc == 1 and "resolution" in out


def test_direction_forks_over_cap_fails(tmp_path, capsys):
    d = _proj(tmp_path)
    with open(d / "direction" / "forks.md", "a", encoding="utf-8") as fh:
        for n in (3, 4, 5, 6):
            fh.write(f"| {n} | fork {n} | criterion | A | B | ev | 1 file | resolved |\n")
    rc, out = _run_dir(d, capsys)
    assert rc == 1 and "over the ~5 cap" in out


def test_direction_missing_winner_fails(tmp_path, capsys):
    d = _proj(tmp_path)
    _edit(d / "direction" / "final.md", "winner: MANDATE A (trust-first)", "the chosen mandate")
    rc, out = _run_dir(d, capsys)
    assert rc == 1 and "D3" in out


def test_direction_missing_minority_fails(tmp_path, capsys):
    d = _proj(tmp_path)
    _edit(d / "direction" / "decision.md", "## Minority report", "## Runner-up notes")
    rc, out = _run_dir(d, capsys)
    assert rc == 1 and "D4" in out


def test_direction_log_missing_vindication_fails(tmp_path, capsys):
    d = _proj(tmp_path)
    _edit(d / "direction" / "log.md", "vindication:", "later:")
    rc, out = _run_dir(d, capsys)
    assert rc == 1 and "vindication" in out


def test_direction_lock_missing_key_fails(tmp_path, capsys):
    d = _proj(tmp_path)
    _edit(d / ".design" / "design.lock.json", '  "density": "comfortable",\n', "")
    rc, out = _run_dir(d, capsys)
    assert rc == 1 and "density" in out


def test_direction_lock_bad_hex_fails(tmp_path, capsys):
    d = _proj(tmp_path)
    _edit(d / ".design" / "design.lock.json", '"ink": "#1b1b1b"', '"ink": "near-black"')
    rc, out = _run_dir(d, capsys)
    assert rc == 1 and "colors.ink" in out


def test_map_and_direction_combined_passes(tmp_path, capsys):
    d = _proj(tmp_path)
    momap = tmp_path / "map"
    shutil.copytree(FIX, momap)
    rc = map_check.main(["--map", str(momap), "--direction", str(d / "direction")])
    out = capsys.readouterr().out
    assert rc == 0
    assert "GATE: PASS" in out


def test_direction_second_live_direction_fails(tmp_path, capsys):
    d = _proj(tmp_path)
    shutil.copy(d / "direction" / "final.md", d / "direction" / "final2.md")
    rc, out = _run_dir(d, capsys)
    assert rc == 1 and "D3" in out and "second live direction" in out


def test_direction_second_direction_retired_passes(tmp_path, capsys):
    d = _proj(tmp_path)
    text = (d / "direction" / "final.md").read_text(encoding="utf-8")
    (d / "direction" / "final2.md").write_text(text + "\nretired — superseded by final.md.\n", encoding="utf-8")
    rc, out = _run_dir(d, capsys)
    assert rc == 0, out


def test_direction_lock_enum_fails(tmp_path, capsys):
    d = _proj(tmp_path)
    _edit(d / ".design" / "design.lock.json", '"motion": "subtle"', '"motion": "medium-high"')
    rc, out = _run_dir(d, capsys)
    assert rc == 1 and "motion" in out and "vocabulary" in out


def test_direction_pass2_without_citations_fails(tmp_path, capsys):
    d = _proj(tmp_path)
    _edit(d / "direction" / "pass2.md",
          "flagged (conversion-audit10:7) → revised to cool stone (design.lock.json:10).",
          "flagged then revised.")
    rc, out = _run_dir(d, capsys)
    assert rc == 1 and "D5" in out and "citations" in out


# ------------------------------------- field-test №2 fix batch (F-22+ regressions)

def test_fill_me_marker_fails(tmp_path, capsys):
    """F-24: the kits' single fill marker is gate-detectable (template ↔ gate agree)."""
    d = _copy(tmp_path)
    with open(d / "charters" / "faq.md", "a", encoding="utf-8") as fh:
        fh.write("\ncontent_notes: FILL_ME\n")
    rc, out = _run(d, capsys)
    assert rc == 1 and "R7" in out and "FILL_ME" in out


def test_not_applicable_exists_cell_passes(tmp_path, capsys):
    """F-23: the documented `not_applicable: reason` convention PASSES the gate."""
    d = _copy(tmp_path)
    _edit(d / "edges" / "acquisition.md",
          "| boundary | N | not_applicable: no quotas or limits | N | - |",
          "| boundary | not_applicable: no quotas or limits | - | not_applicable | - |")
    rc, out = _run(d, capsys)
    assert rc == 0, out


def test_add_rows_counted_in_gate_output(tmp_path, capsys):
    """F-59: ADD rows (checks the map adds beyond the brief) are enumerated for verify."""
    d = _copy(tmp_path)
    with open(d / "charters" / "booking-form.md", "a", encoding="utf-8") as fh:
        fh.write("\nADD: validate phone + email format before send\n")
    rc, out = _run(d, capsys)
    assert rc == 0 and "ADD rows: 1" in out


def test_direction_forks_escaped_pipe_cell_passes(tmp_path, capsys):
    """F-43: `\\|` inside a cell is an escape, not a column break."""
    d = _proj(tmp_path)
    with open(d / "direction" / "forks.md", "a", encoding="utf-8") as fh:
        fh.write("| 3 | escaped pipe | cell contains \\| pipe | A | B | ev | 1 file | resolved |\n")
    rc, out = _run_dir(d, capsys)
    assert rc == 0, out


def test_direction_log_missing_witness_fails(tmp_path, capsys):
    """F-31: two draft sha256 hashes (or DEGRADED) are the blinding witness."""
    d = _proj(tmp_path)
    _edit(d / "direction" / "log.md", "- A.md sha256: " + "a" * 64, "- A.md sha256: recorded at write")
    _edit(d / "direction" / "log.md", "- B.md sha256: " + "b" * 64, "- B.md sha256: recorded at write")
    rc, out = _run_dir(d, capsys)
    assert rc == 1 and "D8" in out


def test_direction_degraded_witness_passes(tmp_path, capsys):
    """A single-writer run may say DEGRADED instead of carrying two hashes."""
    d = _proj(tmp_path)
    _edit(d / "direction" / "log.md", "- A.md sha256: " + "a" * 64, "- witness: DEGRADED MODE - single writer")
    _edit(d / "direction" / "log.md", "- B.md sha256: " + "b" * 64, "- hashes not recorded")
    rc, out = _run_dir(d, capsys)
    assert rc == 0, out


def test_direction_winner_prose_mention_ok(tmp_path, capsys):
    """F-41: `winner:` mid-sentence in honest reporting must not trip D3."""
    d = _proj(tmp_path)
    with open(d / "direction" / "pass2.md", "a", encoding="utf-8") as fh:
        fh.write("\nNote: the winner: token inside prose no longer counts as a declaration.\n")
    rc, out = _run_dir(d, capsys)
    assert rc == 0, out


def test_direction_pass2_allow_missing_then_strict(tmp_path, capsys):
    """F-40: merge-time self-check with `--allow-missing pass2` passes; strict still fails."""
    d = _proj(tmp_path)
    (d / "direction" / "pass2.md").unlink()
    rc, out = _run_dir(d, capsys)
    assert rc == 1 and "pass2" in out
    rc, out = _run_dir(d, capsys, extra=["--allow-missing", "pass2"])
    assert rc == 0, out


def test_direction_lock_base_vocabulary_fails(tmp_path, capsys):
    """F-44: `base` has a defined vocabulary."""
    d = _proj(tmp_path)
    _edit(d / ".design" / "design.lock.json", '"base": "radix"', '"base": "bootstrap"')
    rc, out = _run_dir(d, capsys)
    assert rc == 1 and "base" in out and "vocabulary" in out


def test_direction_lock_optional_dark_and_focus_ring_pass(tmp_path, capsys):
    """F-35/F-47: optional `dark` + `focus_ring` keys validate when present."""
    d = _proj(tmp_path)
    _edit(d / ".design" / "design.lock.json", '  "sections": {}',
          '  "focus_ring": "#3f5d52",\n'
          '  "dark": {"background": "#101210", "surface": "#161816", "ink": "#eceee9", "muted": "#9aa39c", "accent": "#8fb8a6", "border": "#2a2e2a"},\n'
          '  "sections": {}')
    rc, out = _run_dir(d, capsys)
    assert rc == 0, out


def test_direction_lock_dark_incomplete_fails(tmp_path, capsys):
    """F-35: a `dark` block must carry all six color keys as 6-hex."""
    d = _proj(tmp_path)
    _edit(d / ".design" / "design.lock.json", '  "sections": {}',
          '  "dark": {"background": "#101210"},\n  "sections": {}')
    rc, out = _run_dir(d, capsys)
    assert rc == 1 and "dark.surface" in out


def test_direction_lock_focus_ring_bad_hex_fails(tmp_path, capsys):
    d = _proj(tmp_path)
    _edit(d / ".design" / "design.lock.json", '  "sections": {}',
          '  "focus_ring": "#fff",\n  "sections": {}')
    rc, out = _run_dir(d, capsys)
    assert rc == 1 and "focus_ring" in out


# ------------------------------------- cold-read audit batch (pre-release, 2026-09)

def test_direction_multi_winner_without_final_fails(tmp_path, capsys):
    """Audit: drafts may each declare `winner:` AND carry `retired` and still leave
    ZERO live directions — final.md must be among the `winner:` docs."""
    d = _proj(tmp_path)
    _edit(d / "direction" / "final.md", "winner: MANDATE A (trust-first)", "the chosen mandate")
    for name in ("A.md", "B.md"):
        with open(d / "direction" / name, "a", encoding="utf-8") as fh:
            fh.write("\nwinner: MANDATE (retired — superseded in final.md)\n")
    rc, out = _run_dir(d, capsys)
    assert rc == 1 and "D3" in out and "not in final.md" in out


def test_direction_forks_empty_cost_fails(tmp_path, capsys):
    """Audit: the `cost` column was header-text-only — an empty cost cell must fail."""
    d = _proj(tmp_path)
    with open(d / "direction" / "forks.md", "a", encoding="utf-8") as fh:
        fh.write("| 3 | costless | criterion | A | B | ev |  | resolved |\n")
    rc, out = _run_dir(d, capsys)
    assert rc == 1 and "empty cost cell" in out


def test_q_number_placeholder_fails(tmp_path, capsys):
    """Audit: `<Q1>`-style placeholders (uppercase/digits) are still placeholders."""
    d = _copy(tmp_path)
    with open(d / "charters" / "faq.md", "a", encoding="utf-8") as fh:
        fh.write("\nopen_item: <Q1>\n")
    rc, out = _run(d, capsys)
    assert rc == 1 and "R7" in out


def test_marker_in_summary_fails(tmp_path, capsys):
    """Audit: summary.md was the one map file the marker scan skipped."""
    d = _copy(tmp_path)
    with open(d / "summary.md", "a", encoding="utf-8") as fh:
        fh.write("\nopen question: needs a decision\nTBD owner\n")
    rc, out = _run(d, capsys)
    assert rc == 1 and "R7" in out and "summary.md" in out
