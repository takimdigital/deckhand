"""HARVEST: a finished business becomes the owner's next head start.

The project's tracked files are copied (no .env, no .deckhand state, no logs), the owner's brand is
neutralised to the base's own name (so the NEXT project's rebrand replaces it and its leak check
catches leftovers), a manifest records what the base contains, and the base is registered in the
personal pool — ranked first whenever it fits. Optionally pushed to a PRIVATE GitHub repo.
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from .util import DhError, git_files, home, now, read_json, run, slugify, write_json, which
from . import pool as POOL

DROP = re.compile(r"(^|/)(\.env($|\.)|\.deckhand/|PENDING\.md$|HANDOFF\.md$|VERIFY\.md$|ops/bots/.*\.env$|\.bot-state/|node_modules/|\.next/)")


def harvest(root: Path, name: str, to: Path | None = None, repo: str | None = None, private: bool = True) -> dict:
    root = Path(root)
    name = slugify(name)
    dest = Path(to) if to else home() / "bases" / name
    if dest.exists() and any(dest.iterdir()):
        raise DhError("DEST_NOT_EMPTY", str(dest))
    brief = read_json(root / ".deckhand" / "brief.json", {}) or {}
    brand = (brief.get("brand") or {}).get("name") or brief.get("name")
    display = name.replace("-", " ").title()
    copied = 0
    owner_data = []
    for p in git_files(root):
        rel = str(p.relative_to(root)).replace("\\", "/")
        if DROP.search(rel) or not p.is_file():
            continue
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        try:
            text = p.read_text(encoding="utf-8")
            if brand and brand.lower() in text.lower() and not re.search(r"(LICENSE|NOTICE)", rel):
                text = re.sub(re.escape(brand), display, text, flags=re.I)
            out.write_text(text, encoding="utf-8")
        except UnicodeDecodeError:
            shutil.copy2(p, out)
        if re.search(r"(seed|fixtures?|/data/).*\.(ts|js|json|sql)$", rel) or re.search(r"^public/.*\.(jpe?g|png|webp)$", rel):
            owner_data.append(rel)
        copied += 1
    sm = read_json(root / ".deckhand" / "sitemap.json", {}) or {}
    if sm:
        write_json(dest / "deckhand.sitemap.json", sm)
    sections = sorted({p.parent.name for p in (dest / "components" / "sections").glob("*/*.tsx")}) if (dest / "components" / "sections").exists() else []
    pkg = read_json(dest / "package.json", {}) or {}
    stack = POOL.detect_stack(pkg, [str(p.relative_to(dest)).replace("\\", "/") for p in dest.rglob("*") if p.is_file()][:20000])
    manifest = {
        "name": name, "display_name": display, "created": now(), "from_project": root.name,
        "shape": brief.get("shape"), "features": brief.get("features") or [], "languages": brief.get("languages") or [],
        "stack": stack, "pages": [p.get("route") for p in sm.get("pages", [])], "sections": sections,
        "template_names": [display, name], "owner_data_to_review": owner_data[:100],
        "licences": {"notice": (dest / "NOTICE").read_text(encoding="utf-8") if (dest / "NOTICE").exists() else None,
                     "third_party": (dest / "THIRD_PARTY_NOTICES.md").exists()},
    }
    write_json(dest / "deckhand.template.json", manifest)
    run(["git", "init", "-q"], cwd=dest)
    run(["git", "add", "-A"], cwd=dest)
    run(["git", "-c", "user.name=deckhand", "-c", "user.email=deckhand@localhost", "commit", "-qm", f"base: {name} (harvested from {root.name})"], cwd=dest)
    pushed = None
    if repo:
        if not which("gh"):
            pushed = {"ok": False, "hint": f"install gh, then: gh repo create {repo} --private --source {dest} --push"}
        else:
            r = run(["gh", "repo", "create", repo, "--private" if private else "--public", "--source", str(dest), "--push"], cwd=dest, timeout=300)
            pushed = {"ok": r["code"] == 0, "repo": repo, "tail": (r["err"] or r["out"])[-300:]}
    row = {"name": name, "path": str(dest), **({"repo": repo} if repo and pushed and pushed.get("ok") else {}), "license": "owner",
           "lane": "web", "shape": brief.get("shape"), "stack": stack, "canonical": stack.get("framework") == "next",
           "features": brief.get("features") or [], "vendors": [], "stars": None, "pushed_at": now()[:10], "measured": "harvest", "measured_at": now()}
    POOL.add_local(dest, row)
    return {"base": name, "path": str(dest), "files": copied, "manifest": "deckhand.template.json", "pushed": pushed,
            "registered": "personal pool (ranked first when it fits)", "review": owner_data[:12]}
