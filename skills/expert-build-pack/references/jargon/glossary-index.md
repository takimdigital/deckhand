# Glossary Index — how jargon files work

Load when: writing/reading specialist terms, or creating a new domain glossary file.

Jargon files exist so prompts and briefs can use exact, task-native vocabulary. Measured basis: domain terminology anchors semantic boundaries and cuts output variance; exact artifact identifiers dominate model behavior while obscure synonyms are largely ignored. So: **literal names and terms, not obscure flourish**.

## Entry format (every term)

```
**Term** — precise meaning in one line. Use when: <situation>. Example: <one usage>. Do NOT use for: <nearest confusable scope>.
```

Rules:
- One usage example per term (usage teaches better than definitions).
- Prefer the literal artifact name (library, API, command, pattern) over descriptions.
- Terms are for execution contexts; for teaching/explanation, switch to plain register (see register routing below).
- No undefined synonyms — if a term appears, it must be defined somewhere in `references/jargon/`.

## Register routing

- **Build/deploy/ops contexts →** expert register (precise jargon, exact commands, numbers).
- **Explanation/teaching/onboarding →** plain register (the measured tradeoff: role/expert register increases jargon density but reduces clarity; pick deliberately).
- **User-facing copy →** the user's language, never internal jargon.

## Domain files

| File | Domain | Status |
|---|---|---|
| `web-saas.md` | Web/SaaS business + engineering terms | active |

Add a new domain file only when a domain exceeds roughly one file of terms (avoid fragmenting); extend existing files with the update loop instead.

## Maintenance

Terms enter only through the update loop (verification + provenance). When a term is renamed upstream (API/lib), update the entry and note the old name as obsolete rather than deleting.
