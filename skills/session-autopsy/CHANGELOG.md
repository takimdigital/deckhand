# Changelog — session-autopsy

## 0.1.2 — 2026-09-20

- Fresh-eyes audit fixes: the token-discipline line said "≤ 2 refs" while the phase workflow needs three (10 → 20 → 30) — rephrased to "the ref the current phase names, one at a time, three max". Evidence ref now records the Hermes fallback store (`request_dump_*.json` under the Hermes data dir + its session DB; `session_search` stays primary).
- CHANGELOG created (the skill's own publishing rule requires one).

## 0.1.1 — 2026-09-20

- **The trigger, spoken plainly**: "run session-autopsy" said in the failing session = Option A (it greps its own transcript); cross-session via session ID = Option B. Deliverable stated as an edited, verified instruction.

## 0.1.0 — 2026-09-19

- Initial: failure → instruction fix. Phases (evidence → cause-chain → locate → fix ladder → write → verify → publish), token discipline, ≤40-line report template.
