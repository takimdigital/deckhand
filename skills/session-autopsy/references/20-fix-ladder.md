# 20 — The fix ladder (strongest → weakest) + live cases

**Rule:** always take the highest reachable rung. Every pitfall is an instruction not yet fixed.

| Rung | Move | Must hold |
|---|---|---|
| 1 Eliminate | script/template/default renders the wrong path impossible | "can the agent still choose wrong?" → no |
| 2 Pre-flight | check at the last cheap moment before the point of no return | check sits BEFORE the expensive step |
| 3 Reorder/rewrite | canonical order/words make the right path the path | a first-time reader lands right |
| 4 Gate | loud verified failure exactly at the mistake (smoke, exit code) | fails fast with a readable reason |
| 5 Pitfall | non-designable quirk; entry says where the net is | rungs 1–4 really didn't apply |

## Live cases (red → green, 2026-09-19)

- Docker-29 bypasses host firewalls → **1**: loopback-bind in the compose (rung-4 firewall didn't hold).
- pnpm `packageManager` pin vs CI double-pin → **2**: pre-flight greps workflows before the first deploy.
- `setup-node@v5` needs `pnpm` on PATH first → **3**: canonical order checkout → action-setup → setup-node.
- Dev seed ships a known-password owner → **2+4**: first-run step + owner re-key; never a pitfall.
- Windows folder rename EBUSY → **5**: retry note (environment; not designable away).

## Anti-patterns

- Vague prose ("be careful with X") — not a fix. Exact strings, order, commands only.
- Duplicating an existing rule — cross-link with one line instead.
- Fixing a symptom in the wrong file — the edit goes where the agent ACTS, not where the problem was found.
- Skipping verify because the edit "looks right".
