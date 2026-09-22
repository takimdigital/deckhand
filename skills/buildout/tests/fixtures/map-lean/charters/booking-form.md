# FEATURE_CHARTER: booking-form

job_to_be_done: "When I've picked a walk, I want to request it in under a minute, so I don't lose the thread of my day." VERIFIED
job_dimension: FUNCTIONAL
who_for: local dog owners | awareness_stage: solution-aware VERIFIED
trigger: internal — "I need this sorted today" INFERRED
entry_point: homepage CTA | scent_match: Y
step_sequence:
  1. Pick service from the three options
  2. Enter phone number
  3. Send
user_state_per_step: focused -> relieved after confirm
next_action: confirmation screen; on failure an error state with retry
return_needed: Y — trigger_if_yes: back button or session timeout keeps the typed values
aarrr_stage: acquisition
success_metric: submitted requests per week | instrumented: N
cost_to_user: time=~45s clicks/fields=3 cognitive=low money=none
friction_notes: UNVERIFIED
content_notes: UNVERIFIED
monetization_notes: UNVERIFIED
