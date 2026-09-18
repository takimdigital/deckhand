# Eval Harness — proving the pack actually helps

Load when: changing the pack, tuning descriptors/triggers, or answering "is this working?".

Measured warning: static quality scores are near-useless predictors of runtime value (structural checks vs live lift correlation ≈ 0). **Only paired live runs count.** And identical skill content can HELP or HURT depending on project/model — a skill is a hypothesis about a skill × project × model triple.

## 1. Paired runs (the core loop)

For a fixed task, same harness, same model:

1. Run WITHOUT the pack → record pass/fail, time, tokens.
2. Run WITH the pack (same task, fresh session) → record the same.
3. `Skill Lift = with − without` per metric.

Repeat over a task suite (≥8 tasks); report mean ± spread, not one hero run. Preserve raw transcripts of both runs — they are the evidence, not this summary.

**Length-matched control:** also run with a long, irrelevant skill of similar size. If results drop equally, the loss is length-distraction; if the pack still loses, the content is misleading for that project/model (then gate it off for that context).

## 2. Trigger evals (per harness / per model)

- Use `trigger-eval.json` (~20 queries: should-trigger / should-not-trigger).
- Measure recall (caught) + precision (false fires) after ANY change to the description.
- Real numbers matter: auto-triggering is keyword-overlap-based and leaks; keep an explicit `/expert-build-pack` path as the reliable route.

## 3. Paraphrase robustness

For each critical instruction: test ≥5 meaning-preserving variants (single variants miss ~70% of wording-fragile items). Record which variation types (reordering, framing, entity substitution) flip behavior.

## 4. CI gates for the pack itself

- **Compaction survival:** simulate 5 compaction rounds; constraints must lose ZERO content (that's why constraints are pinned verbatim).
- **Tag survival:** pass a handoff chain (A→B→C) and check every truth tag is still attached to its claim.
- **Trigger gate:** trigger-eval must meet recall/precision thresholds before release.

## 5. KPIs

- Cost per successful task (not cost per call).
- Handoff debt: successor work (events/tokens) after a handoff vs from scratch.
- Loop control: strict success (finished AND verified) vs partial.

## 6. Reporting template

```
Suite: <name>  Harness/Model: <x>  Date: <y>
Task | without | with | lift | tokens delta
mean ± sd: <...>  Control (irrelevant skill): <...>
Trigger eval: recall <x>%  precision <y>%
Verdict: keep / gate (context=...) / drop
```
