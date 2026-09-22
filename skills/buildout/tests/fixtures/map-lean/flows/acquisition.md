# FLOW_MAP: acquisition

entry_points: [google search, QR card, referral text message]
screens:
  1. homepage-services -> next_action: tap a walk option or the CTA
  2. booking-form -> next_action: confirmation screen after send; error + retry on failure
  3. faq -> next_action: link back to booking-form from every answer
decision_points: [homepage-services: branches to booking-form if ready, else faq if unsure]
exit_points: [any page via browser close — normal; mid-form via back button — typed values kept; confirmation screen — done]
dead_ends_found: []
edge_cases_ref: edges/acquisition.md
flow_overlap_check: no other flow shares these screens — single flow at lean depth.
