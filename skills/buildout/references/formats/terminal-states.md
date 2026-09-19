# Terminal States — how work ends, explicitly

Load when: closing a task, reporting status, or designing loop/stop conditions.

Every unit of work ends in exactly one named terminal state. Unnamed endings ("stopped") hide failures and inflate success claims.

| State | Meaning | Success? |
|---|---|---|
| `success` | Completion condition met AND verified (step-record + evidence) | yes |
| `no-op` | Correctly determined there was nothing to do (state already as desired) | yes (with evidence) |
| `blocked` | External dependency prevents progress (access, upstream, decision needed) | no — escalate with the exact blocker |
| `stalled` | No measurable progress across iterations (stagnation detected) | no — change approach or escalate; do not loop |
| `exhausted` | Budget (iterations/tokens/time) spent before completion | no — report partial state + next action |

## Rules

- **Error or exhausted budget never counts as success.** Report partial artifacts + envelope so a successor can continue.
- **Name the state in every status and handoff.** "Almost done" is not a state.
- **Stopping rule required up front.** Every prompt/loop declares its stop condition: goal met, stagnation detected, or budget ceiling — plus the ambiguity clause ("inspect evidence when the spec is ambiguous") so efficiency wording doesn't cause under-action.
- **Escalation is a valid terminal move:** transferring to a stronger model/human with the envelope attached beats grinding. Mid-run escalation beats post-hoc retry when the competence signal is available.
