# Web / SaaS Glossary — exact terms for precise briefs

Load when: writing briefs/prompts/copy that touch business, growth, or engineering vocabulary.

Format: **Term** — meaning · use when · example. Never use the fuzzy synonym.

## Business & validation

- **ICP** (Ideal Customer Profile) — the narrow persona + situation you serve. Use when: scoping marketing/product. Example: "ICP: solo travel agencies running 5–20 trips/year." Not: "small businesses".
- **JTBD** (Jobs To Be Done) — the outcome a customer is hiring the product for; frame in their words. Use when: positioning. Example: "JTBD: fill last-minute trip seats without phone calls."
- **Wedge** — the single entry point (one persona, one job, one channel) you attack first. Use when: sequencing. Not: "everything we could build".
- **PMF** (Product-Market Fit) — retention-driven pull, not launch spikes. Use when: deciding to scale spend. Signal: cohort retention curve flattens + organic pull. The "40% very disappointed" survey is ONE signal, not proof.
- **MVP** — smallest end-to-end thing that delivers the one job. Scope tool, not a quality bar. Not: "version we ship without tests".
- **Validation ladder** — problem interviews → fake door → concierge → paid pre-commitment. Each rung costs more, proves more. Use when: deciding next evidence step.
- **Kill criteria** — pre-agreed numeric conditions that stop the project. Use when: before starting validation, never after.
- **Willingness to pay** — behavioral evidence money moves (pre-orders, LOIs, paid pilots). Not: "they said they'd pay".
- **Vanity vs actionable metric** — signups/views (vanity) vs activated/retained/paid (actionable). Use when: choosing dashboards.
- **North-star metric** — one actionable metric that best proxies delivered value. Example: "trips booked with confirmed payment".

## Growth

- **Activation** — the first moment a user gets the core value (define it concretely; e.g. "created first trip + invited one traveler").
- **Onboarding** — the engineered path to activation. Not: "welcome email".
- **Retention (D1/D7/D30)** — share of a cohort still active N days later. Use when: judging PMF. Measured in cohorts, not averages.
- **Churn** — rate users/customers stop paying or being active (define which). Logo churn = customers; revenue churn = $. Never mix.
- **MRR / ARR** — monthly/yearly recurring revenue. Use when: SaaS pricing. Not for one-off sales.
- **CAC** — blended or paid acquisition cost per customer. State which. Example: "paid CAC €23, blended €9".
- **LTV** — expected gross-margin contribution per customer over life. Pairs with CAC; LTV/CAC < 1 = losing money per user.
- **Payback period** — months for CAC to be repaid by gross margin. Use when: deciding paid growth.
- **PLG** (product-led growth) — product itself drives acquisition/expansion. Not a synonym for "free tier".
- **Funnel / conversion rate** — defined steps; % moving between adjacent steps. Always state denominator.
- **A/B test / significance** — controlled split with a pre-registered primary metric and decision rule. A result without significance + power is noise. Not: "we changed it and numbers went up".

## Reliability & ops

- **SLI / SLO / SLA** — indicator (measured signal) / objective (internal target, e.g. 99.9%) / agreement (external promise with consequences). Use in that order.
- **Error budget** — allowed failure within the SLO; when burned, reliability work preempts features.
- **RTO / RPO** — max tolerable downtime (recovery time) / max tolerable data loss (recovery point). Drives backup design.
- **Idempotency key** — client-supplied unique key making a retried side effect happen once. Use when: payments, emails, webhooks.
- **Backpressure / rate limiting** — refusing or slowing load beyond capacity instead of silently dropping. Not: "it'll scale".
- **Webhook vs polling** — push callback vs timed pull; webhooks need signature verification + replay protection.
- **RBAC** — role-based access control; permissions attach to roles, never individuals' names.
- **SSO** — single sign-on via an identity provider; enterprise gate, not a feature badge.

## Engineering (core)

- **Walking skeleton** — thinnest end-to-end deployed slice (UI→API→DB), before features. Use when: new codebase.
- **Expand/contract migration** — add-compatible → deploy → clean-up as separate release. The only safe default for live schemas.
- **Canary / blue-green** — progressive traffic shift / parallel environment cutover. Use when: risky deploys.
- **Feature flag** — runtime toggle for incomplete or risky work. Not: "a branch".
- **Rollback vs revert** — rollback: restore previous deployed artifact; revert: undo in git. Know which you're saying.
- **N+1** — one query per item instead of a join/prefetch; the classic ORM performance bug.
- **Provenance** — where a fact/artifact came from (source + date). Required on pack entries and reported claims.
- **Truth tag** — pack-internal: VERIFIED / INFERRED / UNVERIFIED / OBSOLETE attached to a claim.
- **Verification ladder** — strongest-first evidence: system of record > operation id > durable artifact > transient UI.
