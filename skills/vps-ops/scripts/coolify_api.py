#!/usr/bin/env python3
"""vps-ops — thin Coolify REST client (stdlib only).

Config precedence: --url/--token flags > COOLIFY_URL/COOLIFY_TOKEN env
> ~/.vps-ops/config.json > token fallback in ~/.vps-ops/secrets/env.sh.
See references/10-bootstrap-vps.md for setup, references/40-change-pipeline.md for usage.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HOME = Path(os.environ.get("VPS_OPS_HOME", str(Path.home() / ".vps-ops")))

# Tolerated deployment status sets (live-confirmed 2026-09-17 on Coolify 4.3.21: terminal OK = "finished").
OK_STATUS = {"success", "finished"}
FAIL_STATUS = {"failed", "cancelled"}


def resolve(url_override=None, token_override=None, env=None, home=None):
    """Resolve Coolify URL + token, or raise SystemExit('config error: ...')."""
    env = os.environ if env is None else env
    home = Path(home) if home is not None else HOME
    url = url_override or env.get("COOLIFY_URL")
    token = token_override or env.get("COOLIFY_TOKEN")
    cfg_path = home / "config.json"
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise SystemExit(f"config error: cannot parse {cfg_path}: {exc}")
        url = url or cfg.get("coolify_url")
        token = token or cfg.get("coolify_token")
    if not token:
        secrets = home / "secrets" / "env.sh"
        if secrets.exists():
            for line in secrets.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("export COOLIFY_TOKEN="):
                    token = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if not url or not token:
        raise SystemExit(
            "config error: need both Coolify URL and token — set COOLIFY_URL/COOLIFY_TOKEN, "
            f"or create {cfg_path} / {home / 'secrets' / 'env.sh'} (see references/10-bootstrap-vps.md)"
        )
    return url.rstrip("/"), token


def build_request(url, token, method, path, params=None, body=None):
    full = url.rstrip("/") + "/api/v1" + path
    if params:
        full += "?" + urllib.parse.urlencode({k: str(v) for k, v in params.items() if v is not None})
    data = None
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json",
               "User-Agent": "vps-ops/1.0"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    return urllib.request.Request(full, data=data, method=method, headers=headers)


def _http_req(req, timeout):
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "ignore")


def api(url, token, method, path, params=None, body=None, timeout=60, http=None):
    http = http or _http_req
    req = build_request(url, token, method, path, params=params, body=body)
    status, raw = http(req, timeout)
    try:
        return status, (json.loads(raw) if raw.strip() else None)
    except ValueError:
        return status, raw


def _deployment_rows(body):
    """Normalize GET /deployments/applications/{uuid}.

    Live shape (Coolify 4.3.21): {"count": N, "deployments": [ {...}, ... ]}.
    Tolerates a plain list and {"data": [...]} wrappers too. Returns newest-first.
    """
    rows = []
    if isinstance(body, list):
        rows = body
    elif isinstance(body, dict):
        for key in ("deployments", "data"):
            if isinstance(body.get(key), list):
                rows = body[key]
                break
    rows = [r for r in rows if isinstance(r, dict)]
    rows.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)
    return rows


def wait_for_deploy(url, token, uuid, timeout=900, interval=10, api_fn=None,
                    sleep=time.sleep, now=time.time, log=print):
    """Poll the newest deployment for <uuid> until terminal status. Returns 0/3/5."""
    api_fn = api_fn or api
    t0 = now()
    while True:
        if now() - t0 > timeout:
            log(f"TIMEOUT after {timeout}s")
            return 5
        status, body = api_fn(url, token, "GET", f"/deployments/applications/{uuid}")
        rows = _deployment_rows(body)
        latest = rows[0] if rows else None
        if latest:
            st = str(latest.get("status", "")).lower()
            dep = latest.get("deployment_uuid") or latest.get("uuid") or "?"
            log(f"  [{int(now() - t0):>4}s] {st}")
            if st in OK_STATUS:
                log(f"SUCCESS ({int(now() - t0)}s, deployment {dep})")
                return 0
            if st in FAIL_STATUS:
                log(f"DEPLOY FAILED ({st}, deployment {dep})")
                return 3
        sleep(interval)


def _http_url(url, timeout):
    req = urllib.request.Request(url, headers={"User-Agent": "vps-ops/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(200000).decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, e.read(200000).decode("utf-8", "ignore")


def smoke(target, expect=200, contains=None, timeout=30, http=None):
    http = http or _http_url
    try:
        status, text = http(target, timeout)
    except Exception as exc:
        print(f"FAIL {type(exc).__name__} {target} ({exc})")
        return 4
    ok = status == expect and (not contains or contains in text)
    print(f"{'OK' if ok else 'FAIL'} {status} {target}")
    return 0 if ok else 4


# ----------------------------- subcommands -------------------------------

def cmd_health(a, url, token):
    st, body = api(url, token, "GET", "/health", timeout=15)
    tail = "" if st == 200 else f" — {str(body)[:200]}"
    print(f"coolify health: {st}{tail}")
    return 0 if st == 200 else 4


def cmd_apps(a, url, token):
    st, body = api(url, token, "GET", "/applications")
    if st != 200:
        print(f"error {st}: {str(body)[:300]}")
        return 4
    for app in body or []:
        print(f"{app.get('uuid', '?'):<28} {str(app.get('name', '?')):<28} {app.get('status', '?')}")
    return 0


def cmd_app(a, url, token):
    st, body = api(url, token, "GET", f"/applications/{a.uuid}")
    if st != 200:
        print(f"error {st}: {str(body)[:300]}")
        return 4
    print(json.dumps(body, indent=1)[:4000])
    return 0


def cmd_deploy(a, url, token):
    params = {"uuid": a.uuid}
    if a.force:
        params["force"] = "true"
    st, body = api(url, token, "POST", "/deploy", params=params)
    print(f"deploy {a.uuid}: HTTP {st} {str(body)[:300] if body else ''}")
    return 0 if st in (200, 201) else 4


def cmd_deployments(a, url, token):
    st, body = api(url, token, "GET", f"/deployments/applications/{a.uuid}")
    if st != 200:
        print(f"error {st}: {str(body)[:300]}")
        return 4
    rows = _deployment_rows(body)
    for d in rows[: a.limit]:
        dep = d.get("deployment_uuid") or d.get("uuid") or "?"
        print(f"{str(d.get('status', '?')):<12} {str(d.get('created_at', ''))[:19]:<20} {dep}")
    if not rows:
        print("(no deployments yet)")
    return 0


def cmd_wait(a, url, token):
    return wait_for_deploy(url, token, a.uuid, timeout=a.timeout, interval=a.interval)


def cmd_logs(a, url, token):
    st, body = api(url, token, "GET", f"/applications/{a.uuid}/logs",
                   params={"lines": a.lines, "show_timestamps": "true" if a.timestamps else None})
    if st != 200:
        print(f"error {st}: {str(body)[:300]}")
        return 4
    if isinstance(body, dict):
        body = body.get("logs", body)
    print(str(body)[:8000])
    return 0


def cmd_envs(a, url, token):
    st, body = api(url, token, "GET", f"/applications/{a.uuid}/envs")
    if st != 200:
        print(f"error {st}: {str(body)[:300]}")
        return 4
    for e in body or []:
        print(e.get("key"))
    return 0


def cmd_envset(a, url, token):
    data = []
    for pair in a.pairs:
        if "=" not in pair:
            print(f"bad pair (need KEY=VALUE): {pair}")
            return 4
        k, v = pair.split("=", 1)
        data.append({"key": k, "value": v})
    st, body = api(url, token, "PATCH", f"/applications/{a.uuid}/envs/bulk", body={"data": data})
    print(f"envset {a.uuid}: HTTP {st} {str(body)[:200]}")
    return 0 if 200 <= st < 300 else 4


def cmd_status(a, url, token):
    st, apps = api(url, token, "GET", "/applications")
    if st != 200:
        print(f"error {st}: {str(apps)[:300]}")
        return 4
    for app in apps or []:
        s2, deps = api(url, token, "GET", f"/deployments/applications/{app['uuid']}")
        rows = _deployment_rows(deps)
        last = rows[0] if rows else {}
        print(f"{str(app.get('name', '?')):<28} {str(app.get('status', '?')):<10} "
              f"last:{str(last.get('status', '-')):<10} {str(last.get('created_at', ''))[:19]}")
    return 0


def cmd_smoke(a):
    return smoke(a.target, expect=a.expect, contains=a.contains)


def main(argv=None):
    p = argparse.ArgumentParser(prog="coolify_api.py", description="vps-ops Coolify client")
    p.add_argument("--url")
    p.add_argument("--token")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add(name, fn, cfg=True):
        sp = sub.add_parser(name)
        sp.set_defaults(fn=fn, needs_cfg=cfg)
        return sp

    add("health", cmd_health)
    add("apps", cmd_apps)
    sp = add("app", cmd_app); sp.add_argument("uuid")
    sp = add("deploy", cmd_deploy); sp.add_argument("uuid"); sp.add_argument("--force", action="store_true")
    sp = add("deployments", cmd_deployments); sp.add_argument("uuid"); sp.add_argument("--limit", type=int, default=10)
    sp = add("wait", cmd_wait); sp.add_argument("uuid")
    sp.add_argument("--timeout", type=int, default=900); sp.add_argument("--interval", type=int, default=10)
    sp = add("logs", cmd_logs); sp.add_argument("uuid")
    sp.add_argument("--lines", type=int, default=200); sp.add_argument("--timestamps", action="store_true")
    sp = add("envs", cmd_envs); sp.add_argument("uuid")
    sp = add("envset", cmd_envset); sp.add_argument("uuid"); sp.add_argument("pairs", nargs="+")
    add("status", cmd_status)
    sp = add("smoke", cmd_smoke, cfg=False); sp.add_argument("target")
    sp.add_argument("--expect", type=int, default=200); sp.add_argument("--contains")

    a = p.parse_args(argv)
    try:
        if getattr(a, "needs_cfg", False):
            url, token = resolve(a.url, a.token)
            return a.fn(a, url, token)
        return a.fn(a)
    except SystemExit:
        raise
    except Exception as e:
        print(f"unexpected error: {type(e).__name__}: {e}")
        return 6


if __name__ == "__main__":
    sys.exit(main())
