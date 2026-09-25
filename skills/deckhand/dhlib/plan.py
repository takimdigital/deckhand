"""The plan as an interaction graph (.deckhand/sitemap.json) — linted, rendered, split for parallel agents.

Every clickable thing is an edge with a typed target:
  route:/path · anchor:#id · modal:<id> · api:METHOD /path · external:https://… · state:<page>.<state>
  · mailto:… · tel:… · download:<file>
`lint` proves the map has no dead end, no orphan page, no form without success AND error, no API
without an owning feature, no protected page without a way in. `split` cuts it into work packages
(one bounded context per feature + a shell) that agents build in parallel, coordinating through an
append-only blackboard instead of each other's context windows.
"""
from __future__ import annotations

import re
from collections import deque
from pathlib import Path

from .util import DhError, append_jsonl, now, read_json, read_jsonl, write_json, SKILL

KINDS = ("route", "anchor", "modal", "api", "external", "state", "mailto", "tel", "download")


def sitemap_path(root: Path) -> Path:
    return Path(root) / ".deckhand" / "sitemap.json"


def init(root: Path, force: bool = False) -> dict:
    root = Path(root)
    made = []
    for name in ("sitemap.json", "research.json", "brief.json"):
        dst = root / ".deckhand" / name
        if dst.exists() and not force:
            continue
        src = SKILL / "templates" / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        made.append(str(dst.relative_to(root)))
    return {"created": made}


def _target(t: str):
    m = re.match(r"^(\w+):(.*)$", str(t or ""))
    return (m.group(1), m.group(2).strip()) if m else (None, None)


def _route_re(route: str):
    pat = re.sub(r"\[\.\.\.[^\]]+\]", ".+", route)
    pat = re.sub(r"\[[^\]]+\]", "[^/]+", pat)
    return re.compile("^" + pat.rstrip("/") + "/?$")


def _actions(page: dict):
    for a in page.get("actions", []) or []:
        yield a, None
    for sec in page.get("sections", []) or []:
        for a in sec.get("actions", []) or []:
            yield a, sec
    for m in page.get("modals", []) or []:
        for a in m.get("actions", []) or []:
            yield a, m


def lint(root: Path, sm: dict | None = None) -> dict:
    sm = sm if sm is not None else read_json(sitemap_path(root))
    errors, warnings = [], []
    E = lambda code, msg, **k: errors.append({"code": code, "msg": msg, **k})  # noqa: E731
    W = lambda code, msg, **k: warnings.append({"code": code, "msg": msg, **k})  # noqa: E731
    if not sm:
        E("E0", "no .deckhand/sitemap.json (dh plan init)")
        return {"ok": False, "errors": errors, "warnings": warnings}
    pages = sm.get("pages", []) or []
    features = {f.get("id"): f for f in sm.get("features", []) or []}
    ids, routes = {}, {}
    for p in pages:
        if not p.get("id") or not str(p.get("route", "")).startswith("/"):
            E("E1", f"page {p.get('id') or '?'}: needs an id and a route starting with /")
            continue
        if p["id"] in ids:
            E("E1", f"duplicate page id {p['id']}")
        if p["route"] in routes:
            E("E1", f"duplicate route {p['route']}")
        ids[p["id"]] = p
        routes[p["route"]] = p
    matchers = [(_route_re(r), p) for r, p in routes.items()]

    def resolve(route):
        route = route.split("#")[0].split("?")[0] or "/"
        if route in routes:
            return routes[route]
        for rx, p in matchers:
            if rx.match(route):
                return p
        return None

    nav = sm.get("nav", {}) or {}
    nav_edges = [t for grp in nav.values() for t in (grp or [])]
    edges = {p["id"]: set() for p in pages if p.get("id")}
    apis_used = set()
    for p in pages:
        if p.get("id") not in ids:
            continue
        sections = {s.get("id") for s in p.get("sections", []) or []}
        modals = {m.get("id") for m in p.get("modals", []) or []}
        out = 0
        for a, where in _actions(p):
            label = a.get("label") or a.get("id")
            if not a.get("label"):
                E("E11", f"{p['id']}: an action without a visible label ({a.get('id') or a.get('to')})", page=p["id"])
            kind, val = _target(a.get("to"))
            if kind not in KINDS:
                E("E2", f"{p['id']}: '{label}' has no valid target (got {a.get('to')!r}; use route:/x, api:POST /x, modal:x, anchor:#x …)", page=p["id"])
                continue
            if kind == "route":
                tgt = resolve(val)
                if not tgt:
                    E("E2", f"{p['id']}: '{label}' goes to {val} — no page has that route", page=p["id"])
                else:
                    edges[p["id"]].add(tgt["id"])
                    out += 1
            elif kind == "anchor":
                if val.lstrip("#") not in sections:
                    E("E9", f"{p['id']}: '{label}' scrolls to {val} — no section with that id on this page", page=p["id"])
            elif kind == "modal":
                if val not in modals:
                    E("E10", f"{p['id']}: '{label}' opens modal {val} — declare it in page.modals with its own actions", page=p["id"])
            elif kind == "api":
                apis_used.add(val)
                if not a.get("then"):
                    E("E5", f"{p['id']}: '{label}' calls {val} — say what the user sees after (then: route:/…|state:…)", page=p["id"])
                else:
                    tk, tv = _target(a["then"])
                    if tk == "route" and not resolve(tv):
                        E("E2", f"{p['id']}: after '{label}' the user goes to {tv} — no such page", page=p["id"])
                    elif tk == "route":
                        edges[p["id"]].add(resolve(tv)["id"])
                        out += 1
                if not a.get("error"):
                    E("E5", f"{p['id']}: '{label}' calls {val} — the error state is missing (error: state:… )", page=p["id"])
            elif kind in ("external", "mailto", "tel", "download"):
                out += 1
        for f in p.get("features", []) or []:
            if f not in features:
                E("E7", f"{p['id']}: feature '{f}' is not declared in features[]", page=p["id"])
        shows_nav = p.get("chrome", True) is not False
        if not p.get("terminal") and out == 0 and not (shows_nav and nav_edges):
            E("E4", f"{p['id']} ({p['route']}) is a dead end: no way forward and no navigation", page=p["id"])
        if not (p.get("sections") or p.get("components")):
            W("W1", f"{p['id']}: no sections listed (what is on this page?)", page=p["id"])
        if p.get("data") and not set(p.get("states") or []) >= {"empty", "loading", "error"}:
            W("W3", f"{p['id']}: shows data — list its empty, loading and error states", page=p["id"])
    for t in nav_edges:
        kind, val = _target(t)
        if kind == "route":
            tgt = resolve(val)
            if not tgt:
                E("E2", f"navigation links to {val} — no such page")
            else:
                for p in pages:
                    if p.get("id") in edges and p.get("chrome", True) is not False:
                        edges[p["id"]].add(tgt["id"])
    for form in sm.get("forms", []) or []:
        for k in ("submit", "success", "error"):
            if not form.get(k):
                E("E5", f"form {form.get('id')}: '{k}' missing (every form says where it posts, what success shows, what failure shows)")
        kind, val = _target(form.get("submit"))
        if kind == "api":
            apis_used.add(val)
    owned = {api for f in features.values() for api in (f.get("api") or [])}
    for api in sorted(apis_used - owned):
        E("E6", f"API {api} is called but no feature owns it (add it to a feature's api[])")
    for fid, f in features.items():
        fp = [x for x in f.get("pages", []) or [] if x not in ids]
        if fp:
            E("E7", f"feature {fid}: pages {fp} do not exist")
        if not f.get("pages"):
            E("E7", f"feature {fid}: lives on no page")
        if not f.get("done"):
            W("W4", f"feature {fid}: no acceptance line (done: …)")
    # reachability from /
    home = routes.get("/")
    if not home:
        E("E3", "no page at route /")
    else:
        seen, q = {home["id"]}, deque([home["id"]])
        while q:
            cur = q.popleft()
            for n in edges.get(cur, ()):
                if n not in seen:
                    seen.add(n)
                    q.append(n)
        for p in pages:
            if p.get("id") in ids and p["id"] not in seen and not p.get("entry"):
                E("E3", f"{p['id']} ({p['route']}) cannot be reached from / (link it, or mark entry: true for email/deep-link pages)", page=p["id"])
    # protected pages need a way in
    if any((p.get("auth") or "public") != "public" for p in pages):
        login = next((p for p in pages if re.search(r"(login|sign-?in)", p.get("route", "") + p.get("id", ""))), None)
        if not login:
            E("E8", "protected pages exist but there is no login page")
        else:
            ok = any(_target(a.get("then") or a.get("to"))[0] in ("route",) for a, _ in _actions(login)) or any(
                f.get("page") == login["id"] and f.get("success") for f in sm.get("forms", []) or [])
            if not ok:
                E("E8", f"login page {login['id']}: where does a successful sign-in land? (then: route:/dashboard)")
    return {"ok": not errors, "errors": errors, "warnings": warnings,
            "stats": {"pages": len(pages), "features": len(features), "edges": sum(len(v) for v in edges.values())}}


def render(root: Path) -> dict:
    sm = read_json(sitemap_path(root))
    if not sm:
        raise DhError("NO_SITEMAP", "no .deckhand/sitemap.json")
    brief = read_json(Path(root) / ".deckhand" / "brief.json", {}) or {}
    L = [f"# {brief.get('name') or sm.get('name') or 'Plan'} — site map", "",
         f"> {brief.get('business', '')}", ""]
    L += ["```mermaid", "flowchart LR"]
    pid = {p["id"]: p for p in sm.get("pages", []) if p.get("id")}
    for p in pid.values():
        L.append(f'  {p["id"]}["{p.get("title", p["id"])}<br/>{p["route"]}"]')
    for p in pid.values():
        for a, _ in _actions(p):
            for t in (a.get("to"), a.get("then")):
                k, v = _target(t)
                if k == "route":
                    tgt = next((q for q in pid.values() if _route_re(q["route"]).match(v.split("#")[0] or "/")), None)
                    if tgt:
                        L.append(f'  {p["id"]} -->|{(a.get("label") or "")[:24]}| {tgt["id"]}')
    L += ["```", ""]
    for p in pid.values():
        L += [f"## {p.get('title', p['id'])} — `{p['route']}` ({p.get('auth', 'public')})", ""]
        if p.get("purpose"):
            L += [p["purpose"], ""]
        for s in p.get("sections", []) or []:
            acts = ", ".join(f"{a.get('label')} → {a.get('to')}" for a in s.get("actions", []) or [])
            L.append(f"- **{s.get('slot') or s.get('id')}** {('— ' + acts) if acts else ''}")
        for a in p.get("actions", []) or []:
            L.append(f"- action: {a.get('label')} → {a.get('to')}" + (f" → then {a.get('then')}" if a.get("then") else "") + (f" · on error {a.get('error')}" if a.get("error") else ""))
        L.append("")
    if sm.get("features"):
        L += ["## Features", "", "| feature | pages | api | done when |", "|---|---|---|---|"]
        for f in sm["features"]:
            L.append(f"| {f.get('title', f['id'])} | {', '.join(f.get('pages', []))} | {', '.join(f.get('api', []) or [])} | {f.get('done', '')} |")
        L.append("")
    out = Path(root) / ".deckhand" / "PLAN.md"
    out.write_text("\n".join(L), encoding="utf-8")
    return {"written": str(out)}


def split(root: Path, agents: int = 3) -> dict:
    """Work packages: one per feature (its pages, APIs, entities) + a shell (layout, nav, marketing)."""
    sm = read_json(sitemap_path(root))
    lint_r = lint(root, sm)
    if not lint_r["ok"]:
        raise DhError("PLAN_NOT_CLEAN", "fix the plan first (dh plan lint)", errors=lint_r["errors"][:10])
    pages = {p["id"]: p for p in sm.get("pages", [])}
    owned = {}
    wps = []
    for f in sm.get("features", []) or []:
        mine = [pg for pg in f.get("pages", []) if pg not in owned]
        for pg in mine:
            owned[pg] = f["id"]
        wps.append({"id": f"WP-{len(wps) + 1:02d}", "context": f["id"], "title": f.get("title", f["id"]),
                    "pages": mine, "api": f.get("api", []) or [], "entities": f.get("entities", []) or [],
                    "emails": f.get("emails", []) or [], "done": f.get("done", "")})
    shell = [pid for pid in pages if pid not in owned]
    wps.insert(0, {"id": "WP-00", "context": "shell", "title": "Shell: layout, navigation, marketing pages, shared UI",
                   "pages": shell, "api": [], "entities": [], "emails": [], "done": "every nav/footer link resolves; marketing pages match the plan"})
    # contracts: links that leave a package are its interfaces
    for wp in wps:
        consumes = set()
        for pid in wp["pages"]:
            for a, _ in _actions(pages[pid]):
                for t in (a.get("to"), a.get("then")):
                    k, v = _target(t)
                    if k == "route":
                        tgt = next((q for q in pages.values() if _route_re(q["route"]).match(v.split("#")[0] or "/")), None)
                        if tgt and tgt["id"] not in wp["pages"]:
                            consumes.add(f"route {tgt['route']} (owned by {owned.get(tgt['id'], 'shell')})")
                    if k == "api" and v not in wp["api"]:
                        consumes.add(f"api {v}")
        wp["consumes"] = sorted(consumes)
    lanes = [[] for _ in range(max(1, agents))]
    for wp in sorted(wps, key=lambda w: -len(w["pages"]) - 2 * len(w["api"])):
        min(lanes, key=lambda l: sum(len(w["pages"]) + 2 * len(w["api"]) for w in l)).append(wp)
    wdir = Path(root) / ".deckhand" / "work"
    wdir.mkdir(parents=True, exist_ok=True)
    tpl = (SKILL / "templates" / "work-package.md").read_text(encoding="utf-8")
    for lane_i, lane in enumerate(lanes):
        for wp in lane:
            wp["agent"] = lane_i + 1
            body = tpl
            rep = {
                "{{ID}}": wp["id"], "{{TITLE}}": wp["title"], "{{CONTEXT}}": wp["context"], "{{AGENT}}": str(wp["agent"]),
                "{{PAGES}}": "\n".join(f"- `{pages[p]['route']}` — {pages[p].get('title', p)}: " + "; ".join(
                    f"{s.get('slot') or s.get('id')}" for s in pages[p].get("sections", []) or []) for p in wp["pages"]) or "- (none)",
                "{{ACTIONS}}": "\n".join(f"- `{pages[p]['route']}` · {a.get('label')} → {a.get('to')}" + (f" → {a.get('then')}" if a.get('then') else "") + (f" · error → {a.get('error')}" if a.get('error') else "")
                                         for p in wp["pages"] for a, _ in _actions(pages[p])) or "- (none)",
                "{{API}}": "\n".join(f"- `{x}`" for x in wp["api"]) or "- (none)",
                "{{ENTITIES}}": ", ".join(wp["entities"]) or "(none)",
                "{{CONSUMES}}": "\n".join(f"- {c}" for c in wp["consumes"]) or "- (none)",
                "{{DONE}}": wp["done"] or "the pages render, every action reaches its target, errors show their state",
            }
            for k, v in rep.items():
                body = body.replace(k, v)
            (wdir / f"{wp['id']}-{wp['context']}.md").write_text(body, encoding="utf-8")
    index = {"at": now(), "agents": len(lanes), "packages": [{k: wp[k] for k in ("id", "context", "title", "agent", "pages", "api", "consumes")} for lane in lanes for wp in lane]}
    write_json(wdir / "index.json", index)
    return index


# ------------------------------------------------------------------ blackboard (shared memory)
BB_KINDS = ("decision", "contract", "blocker", "question", "done", "note")


def bb_post(root: Path, wp: str, kind: str, msg: str, refs=None) -> dict:
    if kind not in BB_KINDS:
        raise DhError("BAD_KIND", f"kind must be one of {BB_KINDS}")
    entry = {"at": now(), "wp": wp, "kind": kind, "msg": msg, **({"refs": refs} if refs else {})}
    append_jsonl(Path(root) / ".deckhand" / "blackboard.jsonl", entry)
    return entry


def bb_read(root: Path, wp: str | None = None, kind: str | None = None, last: int = 40) -> list:
    rows = read_jsonl(Path(root) / ".deckhand" / "blackboard.jsonl")
    if wp:
        rows = [r for r in rows if r.get("wp") in (wp, "all") or r.get("kind") in ("contract", "decision")]
    if kind:
        rows = [r for r in rows if r.get("kind") == kind]
    return rows[-last:]
