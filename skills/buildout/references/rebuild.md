# Rebuild an existing project (keep the design, replace the foundation)

The most common real second job: the owner already has a site or a vibe-coded app ("built with another
AI") and wants it rebuilt properly — same look, real foundation. The pool supplies the foundation; the
old project supplies the design, the copy and the data model. Read this **before** the interview.

## 1. Recon — bounded, and before any decision

Bounded means: never `du -sh` or a recursive listing over the whole tree (one real run sat on a 1.7 GB
folder until the command timed out). Read small files and structure instead:

```
ls <root>                                  # top level only — not -R
git -C <root> log --oneline -5             # is there any history at all?
<read> package.json · config · globals.css/theme · lib/db/* · route files
```

Then answer three questions in plain words the owner can check:

- **Foundation** — is there a real server, database and auth, or a browser-only fake (Dexie/IndexedDB,
  localStorage, seed data committed in the repo, hardcoded demo passwords)? A fake foundation cannot
  go live; that is the whole reason for the rebuild, and saying it out loud is what convinces the
  owner to let the old code go.
- **What is worth keeping** — think in buckets, not files: design tokens (colours, fonts, radii,
  spacing), the component set, the real copy, the data model, the route/screen map.
- **Scale** — screens, lines, languages. It tells you what is a port versus a rewrite.

Deliver a verdict: keep / port / rebuild per bucket, plus what the owner will actually notice.

## 2. Intake still happens — it just shrinks

The old project already answers part of it (shape, features, languages, brand). Ask only what it
cannot: the business intent, the audience, the money model, what is wrong with today's version, and
which kept items are non-negotiable. Mark everything inferred from code as `from: existing-project`
in `intake.json` so the owner can correct it. Mode and research questions still apply (`05-plan.md`).

## 3. The design port (where it actually breaks)

- **Snapshot first.** The old tree stays untouched and unmoved until the new build is verified — it is
  the design reference and the fallback. Build at a sibling path (`<name>-v2`); swap folder names only
  at the end, with the old one renamed, never deleted.
- **Tokens in, values out.** Port the design tokens the way the template wants them and keep every
  hardcoded hex out of components — otherwise dark mode and RTL rot the moment they are switched on.
- **Component library boundaries** — two errors seen in a real port, both cheap to fix at the port and
  expensive later: `Attempted to call X() from the server but X is on the client` (mark the boundary —
  `'use client'`, or pass the variant as data) and a11y runtime complaints such as
  `Base UI: A component that acts as a button expected a native <button>`. A port that only *looks*
  right while throwing in console is not done.
- **Data model**: keep the **template's** column convention (usually camelCase) and map old names onto
  it. Porting snake_case into a camelCase schema fails at the first real query —
  `column "createdAt" does not exist`. The write+read smoke row catches it.
- **Copy**: port the owner's real text; never leave placeholder copy. Missing content is a
  `PENDING.md` item, not lorem ipsum.

## 4. Hand over running, not described

A rebuild's first phase ends with a **local URL the owner can click**, showing the rebuilt app with
their design — not a report. In phased mode that is gate `G2` and a hard stop: the owner tests before
any rebrand, extra feature or deploy work begins. State plainly what is still template-flavoured at
that moment (auth screens, emails, admin chrome) so the owner is not surprised later.
