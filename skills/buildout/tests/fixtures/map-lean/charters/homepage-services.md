# FEATURE_CHARTER: homepage-services

job_to_be_done: "When my dog needs a midday walk, I want a walker I can trust fast, so I can get back to work." VERIFIED
job_dimension: FUNCTIONAL
who_for: local dog owners | awareness_stage: solution-aware VERIFIED
trigger: external — search or handed-out card INFERRED
entry_point: google search / qr card | scent_match: Y
step_sequence:
  1. Land on hero with the three walk options visible
  2. Compare options and prices
  3. Tap "Book a walk"
user_state_per_step: curious -> comparing -> ready
next_action: booking-form (every card and the header CTA link there)
return_needed: N
aarrr_stage: acquisition
success_metric: click-through to booking-form | instrumented: N
cost_to_user: time=~30s clicks/fields=2 cognitive=low money=none
friction_notes: UNVERIFIED
content_notes: UNVERIFIED
monetization_notes: UNVERIFIED
