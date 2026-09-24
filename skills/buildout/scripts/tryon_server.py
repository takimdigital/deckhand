#!/usr/bin/env python3
"""tryon_server — the local helper behind /buildout try-on (stdlib only, loopback + token).

The browser overlay talks to THIS process; the agent talks to files in <project>/.tryon/.
No daemon, no websocket, no vendor: plain HTTP on 127.0.0.1 plus two append-only JSONL files.

    py scripts/tryon_server.py serve  --project D:/app [--port 7799]
    py scripts/tryon_server.py wait   --project D:/app [--timeout 300] [--follow]
    py scripts/tryon_server.py reply  --project D:/app --id 3 --status ok --message "preview installed" [--force]
    py scripts/tryon_server.py status --project D:/app

Request/response shapes (one JSON object per line):
  request : {"id":N,"type":"preview|accept|revert|save|catalog","element":{file,line,tag,text,selector},
             "slot":"button","candidate":{registry,item,item_url,...},"request":N,"note":"...","received_at":"..."}
             ("save" asks the agent to store the staged candidate in the owner's component library;
              "request" points at the preview it refers to)
  response: {"id":N,"status":"ok|error","message":"...","at":"..."}

Hardening (audit-driven, 2026-09-24):
  * POST requires the token AND, when a browser sends one, a localhost Origin — a random page in the
    owner's browser cannot reach the helper even cross-origin.
  * CORS headers are echoed only for localhost/127.0.0.1 origins (never `*`): the overlay's own
    GETs (/slots, /catalog, /events) keep working; anything else gets no CORS grant.
  * A POST body may only carry the known request keys — unknown keys are counted, never merged
    (a forged key used to be able to overwrite server-managed fields).
  * Content-Length is capped (a local process could otherwise stream unbounded data into the log).
  * A per-request nonce is deliberately NOT implemented: the panel authenticates with the token and
    the origin pin above; a nonce with no delivery channel would be theater (recorded in tryon.md).
"""
from __future__ import annotations

import argparse
import json
import re
import secrets
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
OVERLAY = SKILL / "templates" / "tryon" / "overlay.js"

import templates_db as DB  # noqa: E402
import tryon_catalog as CAT  # noqa: E402

LOCAL_ORIGIN_RE = re.compile(r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$")
KNOWN_REQUEST_KEYS = {"type", "element", "slot", "elementSlot", "rescope", "candidate", "note", "request"}
MAX_BODY_BYTES = 256 * 1024

# A per-request nonce was considered and is DEFERRED by decision (2026-09-24): the panel holds the
# token and posts from a localhost origin, and a nonce would need a delivery channel the overlay
# does not have (its GETs are tokenless). Revisit only if the token model itself changes.
NONCE_DEFERRED = True


def state_dir(project: Path) -> Path:
    d = project / ".tryon"
    d.mkdir(parents=True, exist_ok=True)
    return d


def read_jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def append_jsonl(p: Path, rec: dict) -> None:
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def load_server_cfg(project: Path) -> dict:
    p = state_dir(project) / "server.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_server_cfg(project: Path, cfg: dict) -> None:
    (state_dir(project) / "server.json").write_text(json.dumps(cfg, indent=1), encoding="utf-8")


def pending_requests(project: Path) -> list[dict]:
    reqs = read_jsonl(state_dir(project) / "requests.jsonl")
    done = {r.get("id") for r in read_jsonl(state_dir(project) / "responses.jsonl")}
    return [r for r in reqs if r.get("id") not in done]


BASE_LABELS = {"radix": "Radix", "base-ui": "Base UI", "aria": "React Aria",
               "none": "no primitive base", "unknown": "unknown"}


def project_scope(project: Path) -> dict:
    """What the project is made of — read from ITS OWN files (never trusted from the client).

    Same source of truth as the CLI: CAT.project_profile. The catalog is then scoped so a project
    never gets candidates that need a different primitive base.
    """
    prof = CAT.project_profile(project)
    base = prof.get("base") or "unknown"
    return {"base": base, "base_label": BASE_LABELS.get(base, base),
            "style": prof.get("style"), "lineage": prof.get("lineage"),
            "registry_pref": "shadcn" if prof.get("lineage") == "shadcn-style" else None,
            "evidence": prof.get("evidence", [])}


# ------------------------------------------------------------------ http side
class Handler(BaseHTTPRequestHandler):
    project: Path
    token: str
    port: int
    db: str

    def log_message(self, fmt, *a):  # quiet by default; the agent reads files, not logs
        if self.server.verbose:  # type: ignore[attr-defined]
            sys.stderr.write("tryon: " + fmt % a + "\n")

    def _origin(self):
        """The request's Origin when it is a localhost one; None otherwise (incl. absent)."""
        origin = (self.headers.get("Origin") or "").strip()
        return origin if origin and LOCAL_ORIGIN_RE.match(origin) else None

    def _send(self, code: int, body: bytes, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        o = self._origin()
        if o:
            # Pin the grant to the asking localhost origin — never `*` (any visited page used to be
            # able to read this server). Absent/foreign origins get no CORS grant at all.
            self.send_header("Access-Control-Allow-Origin", o)
            self.send_header("Vary", "Origin")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode(), "application/json")

    def do_GET(self):  # noqa: N802
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == "/health":
            return self._json({"ok": True, "project": str(self.project),
                               "pending": len(pending_requests(self.project))})
        if u.path == "/overlay.js":
            try:
                js = OVERLAY.read_text(encoding="utf-8")
            except FileNotFoundError:
                return self._send(500, b"overlay.js missing from the skill", "text/plain")
            cfg = {"port": self.port, "token": self.token, "project": self.project.name}
            prelude = "window.__TRYON__ = " + json.dumps(cfg) + ";\n"
            return self._send(200, (prelude + js).encode(), "application/javascript")
        if u.path == "/slots":
            con = DB.connect(Path(self.db))
            return self._json(DB.reg_slots(con))
        if u.path == "/catalog":
            slot = (q.get("slot") or [""])[0]
            base_q = (q.get("base") or [None])[0]
            registry_q = (q.get("registry") or [None])[0]
            if not slot:
                return self._json({"error": "slot required"}, 400)
            scope = project_scope(self.project)
            base = base_q or scope["base"]
            con = DB.connect(Path(self.db))
            all_rows = [dict(r) for r in DB.reg_rows(con, slot=slot, registry=registry_q, free_only=True)]
            filt = base if base in ("radix", "base-ui", "aria", "none") else None
            rows = [dict(r) for r in DB.reg_rows(con, slot=slot, registry=registry_q,
                                                 base=filt, free_only=True)]
            shown = {(r["registry"], r["item"]) for r in rows}
            hidden_rows = [r for r in all_rows if (r["registry"], r["item"]) not in shown]
            pref = scope.get("registry_pref")
            ranked = []
            for r in rows:
                sc, why = CAT.score(r, slot, base if base != "unknown" else None)
                if sc > 0:
                    ranked.append({"score": sc, "why": why, "registry": r["registry"], "item": r["item"],
                                   "type": r["type"], "title": r["title"], "base": r["base"],
                                   "style": r.get("style") or "", "item_url": r["item_url"],
                                   "license": r.get("license") or "", "license_evidence": r.get("license_evidence") or "",
                                   "deps": r.get("deps") or "[]", "registry_deps": r.get("registry_deps") or "[]",
                                   "desc": (r["description"] or "")[:160],
                                   "slot": r["slot"], "slot_kind": r["slot_kind"],
                                   "compat": ("same setup" if r["base"] == base and base != "unknown" else
                                              ("no shared base" if r["base"] in (None, "none") else "different base"))})
            # Order: the owner's OWN saved components first (pre-vetted by him), then same lineage,
            # then score. Personal items are still under the same base filter above.
            ranked.sort(key=lambda r: (0 if r["registry"] == "mine" else 1,
                                       0 if (pref and r["registry"] == pref) else 1,
                                       -r["score"],
                                       r["registry"], r["item"]))
            scope_out = dict(scope)
            scope_out["hidden"] = len(hidden_rows)
            scope_out["hidden_bases"] = sorted({r["base"] for r in hidden_rows if r["base"]})
            return self._json({"scope": scope_out, "items": ranked[:12]})
        if u.path == "/events":
            return self._sse()
        return self._json({"error": "not found"}, 404)

    def _sse(self):
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "keep-alive")
            o = self._origin()
            if o:
                self.send_header("Access-Control-Allow-Origin", o)
                self.send_header("Vary", "Origin")
            self.end_headers()
        except Exception:
            return
        resp = state_dir(self.project) / "responses.jsonl"
        sent = 0
        deadline = time.time() + 20 * 60
        try:
            while time.time() < deadline:
                rows = read_jsonl(resp)
                for r in rows[sent:]:
                    self.wfile.write(("data: " + json.dumps(r, ensure_ascii=False) + "\n\n").encode())
                    self.wfile.flush()
                sent = len(rows)
                time.sleep(0.5)
                self.wfile.write(b": hb\n\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

    def do_POST(self):  # noqa: N802
        u = urlparse(self.path)
        q = parse_qs(u.query)
        # Origin pin: a browser cross-origin POST carries Origin; refuse anything not localhost.
        origin = (self.headers.get("Origin") or "").strip()
        if origin and not LOCAL_ORIGIN_RE.match(origin):
            return self._json({"error": "origin not allowed"}, 403)
        tok = (q.get("token") or [self.headers.get("x-tryon-token", "")])[0]
        if tok != self.token:
            return self._json({"error": "bad token"}, 403)
        if u.path != "/event":
            return self._json({"error": "not found"}, 404)
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_BODY_BYTES:
            return self._json({"error": "body too large"}, 413)
        try:
            body = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
        except Exception:
            return self._json({"error": "bad json"}, 400)
        if not isinstance(body, dict):
            return self._json({"error": "body must be an object"}, 400)
        reqs = read_jsonl(state_dir(self.project) / "requests.jsonl")
        rec = {"id": (max([r.get("id", 0) for r in reqs]) + 1) if reqs else 1}
        # Allowlist, not blind merge: unknown keys are COUNTED, never stored (server-managed fields
        # like id/received_at must not be forgeable, and a crafted key must not inject into the log).
        for k in KNOWN_REQUEST_KEYS:
            if k in body:
                rec[k] = body[k]
        dropped = [k for k in body if k not in KNOWN_REQUEST_KEYS]
        if dropped:
            rec["dropped_keys"] = len(dropped)
        rec["received_at"] = DB.now()
        append_jsonl(state_dir(self.project) / "requests.jsonl", rec)
        print(f"tryon: request #{rec['id']} {rec.get('type')} slot={rec.get('slot')} "
              f"item={(rec.get('candidate') or {}).get('item')}", flush=True)
        return self._json({"ok": True, "id": rec["id"]})

    def do_OPTIONS(self):  # noqa: N802
        o = self._origin()
        self.send_response(204)
        if o:
            self.send_header("Access-Control-Allow-Origin", o)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Headers", "content-type, x-tryon-token")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()


def cmd_serve(args) -> int:
    project = Path(args.project).resolve()
    cfg = load_server_cfg(project)
    token = args.token if args.token and args.token != "auto" else (cfg.get("token") or secrets.token_hex(12))
    port = args.port or int(cfg.get("port") or 7799)
    save_server_cfg(project, {"port": port, "token": token, "pid": None, "db": str(Path(args.db))})
    H = Handler
    H.project, H.token, H.port, H.db = project, token, port, args.db
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    srv.verbose = bool(args.verbose)  # type: ignore[attr-defined]
    save_server_cfg(project, {"port": port, "token": token, "pid": None, "db": str(Path(args.db)),
                              "started_at": DB.now()})
    print(json.dumps({"ok": True, "url": f"http://127.0.0.1:{port}/overlay.js?token={token}",
                      "project": str(project), "state": str(state_dir(project))}), flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


def cmd_wait(args) -> int:
    project = Path(args.project).resolve()
    deadline = time.time() + args.timeout
    seen = args.after
    while True:
        pend = pending_requests(project)
        if seen is not None:
            pend = [r for r in pend if r.get("id", 0) > seen]
        if pend:
            if not getattr(args, "follow", False):
                print(json.dumps(pend[0], ensure_ascii=False))
                return 0
            # --follow: a long-lived listener — print each new request once and keep going. One line
            # per request is what a background notify-pattern can hook, so the agent always hears
            # every click instead of dying after the first one (that cost a live test round).
            for r in pend:
                print(json.dumps(r, ensure_ascii=False), flush=True)
            seen = max(r.get("id", 0) for r in pend)
            deadline = time.time() + args.timeout
        if time.time() >= deadline:
            print(json.dumps({"ok": True, "timed_out": True, "pending": 0}))
            return 3
        time.sleep(args.every)


def cmd_reply(args) -> int:
    project = Path(args.project).resolve()
    done = {r.get("id") for r in read_jsonl(state_dir(project) / "responses.jsonl")}
    rec = {"id": args.id, "status": args.status, "message": args.message or "", "at": DB.now()}
    if args.id in done and not getattr(args, "force", False):
        # An answered request stays answered: a duplicate reply would overwrite the panel's record
        # of what actually happened. Correcting a wrong reply is explicit (--force).
        print(json.dumps({"ok": False, "reason": "ALREADY_ANSWERED", "id": args.id,
                          "hint": "pass --force to append a correction"}, ensure_ascii=False))
        return 1
    append_jsonl(state_dir(project) / "responses.jsonl", rec)
    print(json.dumps({"ok": True, **rec}))
    return 0


def cmd_status(args) -> int:
    project = Path(args.project).resolve()
    cfg = load_server_cfg(project)
    reqs = read_jsonl(state_dir(project) / "requests.jsonl")
    pend = pending_requests(project)
    out = {"project": str(project), "server": cfg or None, "requests": len(reqs),
           "pending": len(pend), "last_request": reqs[-1] if reqs else None}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="try-on local helper (overlay <-> agent bridge)")
    ap.add_argument("--db", default=str(DB.DEFAULT_DB))
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("serve")
    p.add_argument("--project", required=True)
    p.add_argument("--port", type=int, default=0)
    p.add_argument("--token", default="auto")
    p.add_argument("--verbose", action="store_true")
    p = sub.add_parser("wait")
    p.add_argument("--project", required=True)
    p.add_argument("--timeout", type=int, default=300)
    p.add_argument("--after", type=int)
    p.add_argument("--every", type=float, default=0.5)
    p.add_argument("--follow", action="store_true",
                   help="keep listening and print every new request as one line (for a background listener)")
    p = sub.add_parser("reply")
    p.add_argument("--project", required=True)
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--status", choices=["ok", "error"], default="ok")
    p.add_argument("--message", default="")
    p.add_argument("--force", action="store_true",
                   help="append a correction for an already-answered id")
    p = sub.add_parser("status")
    p.add_argument("--project", required=True)
    args = ap.parse_args(argv)
    return {"serve": cmd_serve, "wait": cmd_wait, "reply": cmd_reply, "status": cmd_status}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
