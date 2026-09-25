# 60 — REVIEW (one command, evidence rows)

**Objective:** nothing reaches production that would embarrass, leak or break. **Output:** `dh verify`
green on every blocking row; `.deckhand/VERIFY.md`. **Gate G4:** the owner says go live.

## Rows
| row | blocking | fails when |
|---|---|---|
| typecheck | yes | `tsc --noEmit` reports errors |
| lint | no | the project's lint script fails |
| build | yes | the production build fails |
| prod-clean | yes | a try-on stamp is in the build output |
| tryon-closed | yes | a session is still open |
| secrets | yes | a credential-shaped value or a committed `.env` exists in the repo |
| env-ignored | yes | `.env` is not gitignored |
| swaps | yes | a vendor SDK marked for replacement is still installed/imported |
| honesty | yes | template names, demo companies/people, lorem ipsum, fake logos, try-on leftovers |
| routes | yes (when a URL is given) | a planned public route or a home-page link answers ≥ 400 |
| a11y-basics | no | `<img>` without alt, `<html>` without lang |
| deps-audit | no | high/critical npm advisories |

## Procedure
`$T clean` (try-on) → `dh dev start` → `dh verify --url <dev url>` → fix every red blocking row at its root
(never by weakening the check) → re-run → `dh phase done review` → show VERIFY.md → G4.
Security floor before G4: auth routes rate-limited or provider-protected; admin routes server-checked;
uploads size/type-limited; CSP/headers from the framework defaults at least; no debug endpoints.
