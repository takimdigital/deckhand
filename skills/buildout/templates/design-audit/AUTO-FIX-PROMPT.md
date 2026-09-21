# design-audit — AI fix-loop prompt

Use this prompt to hand audit failures to an agent. It reads ONLY the filtered failure JSON —
never raw logs or screenshots (unless a diff is ambiguous).

---

```
You are fixing DESIGN AUDIT failures in <repo> (stack: <e.g. Next.js + Tailwind>).
Input: run `pnpm design:fails` (reads design-audit/ctrf/ctrf-report.json). Work ONLY from the failures.

For each failed test:
1. Classify: visual | a11y (axe rule id) | layout/overflow | perf | link | html | console/page-error | network.
2. Locate the source:
   - everything: use `filePath` + `message`;
   - a11y: the failing node's `target` + `html` from the attached audit-<route>.json;
   - layout: viewport width + the overflow flag from the same file;
   - perf: open the attached lighthouse-<route>.json ONLY if the category score is the blocker;
   - visual: open the referenced *-diff.png ONLY if the change is genuinely ambiguous.
3. Fix the SOURCE with a minimal patch (component / CSS / markup).
   NEVER: edit snapshots to pass, loosen maxDiffPixelRatio/threshold, delete or skip an assertion,
   or add noise to allow.console/allow.network to silence a real finding.
   The ONE exception: an INTENTIONAL design change → regenerate baselines with
   `pnpm design:audit:update`, commit them, and state the change explicitly in the summary.
4. Re-run ONLY the failed scope: `pnpm exec playwright test --grep "<test name>"`
   (max 3 iterations per failure).
5. Budgets: Lighthouse perf >= 0.9 · zero WCAG A/AA violations · zero console/page errors ·
   zero failed/4xx requests (minus allow-lists) · no horizontal overflow at 320 / project widths ·
   zero broken links · html/lint clean.

Output per failure: {check, root cause (file:line), patch summary, re-run result}.
End with a pass/fail table + a suggested commit message.
Escalate instead of guessing when the fix requires a design-intent decision (ask the user, don't pick).
```

---

Tips:
- Run `pnpm design:audit:fast` once before fixing so the re-run scope (`--grep`) is fast.
- One failure often explains several: start from the first entry that names a file:line.
- After the loop is green: `pnpm design:audit` (full) once, then the app's own test/build gates.
