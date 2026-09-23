# Pool detail contract (v1) — one JSON file per repo

You are measuring ONE GitHub repository to make the template pool smarter. Write exactly one file:

    C:/Users/Takim/AppData/Local/hermes/cache/scratch/pool-details/<slug>.json

WHERE `<slug>` is given to you in your task. Nothing else may be written anywhere.

## Hard rules

1. **Remote only — never clone, never run the repo's code.** Use the GitHub API (`gh api …`, which is
   authenticated on this host) and `raw.githubusercontent.com` for file contents.
2. **No secrets, ever.** Environment variables are listed by NAME only (`STRIPE_SECRET_KEY`), never by
   value. If you ever see a value that looks like a key/token/password, record only the name.
3. **Evidence or it is not a fact.** Every non-obvious field must be traceable: put the file path (or
   API endpoint) you read it from into `evidence`. Do not guess; write `null` when unmeasured and say
   why in `unmeasured`.
4. Valid UTF-8 JSON, no comments, no trailing commas. Keep it under ~40 KB.
5. Prefer `false`/`null` over an invented `true`. An honest gap is worth more than a guess.

## Endpoints that usually answer everything

```
gh api repos/<repo>
gh api repos/<repo>/languages
gh api "repos/<repo>/git/trees/<branch>?recursive=1" --jq '.tree[].path'
gh api repos/<repo>/contents/package.json --jq '.content' | base64 -d
gh api repos/<repo>/contributors --jq '.[].login' ; gh api repos/<repo>/commits?per_page=1
gh api repos/<repo>/releases ; gh api repos/<repo>/issues?state=open | wc -l
curl -s https://raw.githubusercontent.com/<repo>/<branch>/<path>
```

## The file

```json
{
  "repo": "owner/name",
  "slug": "<slug>",
  "measured_at": "2026-09-23T00:00:00Z",
  "upstream_commit": "<sha of the default branch HEAD>",
  "default_branch": "main",
  "archived": false,
  "size_kb": 1234,
  "languages": {"TypeScript": 90.1, "CSS": 9.9},

  "framework": {"name": "next", "version": "16.3.4", "router": "app|pages|none", "notes": ""},
  "package_manager": "pnpm|npm|yarn|bun|uv|pip|poetry|none",
  "node_or_python_requirement": ">=20",
  "monorepo": {"is_monorepo": false, "workspaces": [], "notes": ""},

  "stack": {
    "db": "postgres|sqlite|mysql|mongodb|none|unknown",
    "orm": "drizzle|prisma|sqlmodel|typeorm|none|unknown",
    "auth": {"provider": "better-auth|next-auth|clerk|auth0|custom|none", "methods": ["email-password", "oauth", "magic-link"], "roles": ["user", "admin"], "notes": ""},
    "ui": ["tailwind", "shadcn", "radix", "framer-motion"],
    "i18n": {"library": "next-intl|i18next|none", "default": "en", "locales": ["en", "fr", "ar"], "rtl_aware": true, "translation_files": 3},
    "payments": {"provider": "stripe|lemonsqueezy|none", "model": "subscription|one-time|none", "webhooks": true},
    "email": {"provider": "resend|sendgrid|smtp|none", "templates": 3, "transactional": true},
    "analytics": [], "jobs": [], "search": [], "storage": [], "realtime": [], "flags": [], "observability": []
  },

  "features": ["accounts", "admin", "dashboard", "teams", "billing", "i18n", "uploads", "search", "jobs", "notifications", "booking", "map", "blog", "api-keys", "audit-log"],
  "routes": {"pages": ["/", "/login"], "api": ["/api/auth/[...all]"], "protected": ["/dashboard"], "count": 15},

  "env": {"count": 24, "names": ["DATABASE_URL", "BETTER_AUTH_SECRET"], "required_at_build": [], "notes": ""},
  "deploy": {"docker": true, "dockerfile_port": 6767, "compose": false, "standalone_output": true,
             "build_cmd": "pnpm build", "start_cmd": "pnpm start", "migrations_cmd": "pnpm db:migrate",
             "paas_coupling": ["vercel"], "notes": ""},

  "tests": {"frameworks": ["vitest", "playwright"], "unit_files": 6, "e2e_files": 3, "ci_workflows": [".github/workflows/ci.yml"], "notes": ""},

  "vendor": [{"name": "clerk", "where": ["package.json", ".env.example", "src/middleware.ts"], "what_it_does": "auth + sessions", "swap_target_hint": "better-auth", "effort_guess": "1-2 days"}],
  "rebrand_surface": [{"path": "src/app/layout.tsx", "kind": "metadata|logo|copy|theme|domain|email", "note": "app name + description in metadata"}],
  "hardcoded_demo_content": ["marketing copy on /", "fake testimonials in src/components/testimonials.tsx"],

  "pitfalls": [{"kind": "native-deps|build-needs-env|postinstall|peer-conflicts|docs-lie|dead-demo", "detail": "better-sqlite3 needs node-gyp build tools", "evidence": "package.json"}],

  "blocking": [],
  "complexity": {"pages": 15, "components": 60, "db_models": 12, "migrations": 3, "loc_estimate": 12000},

  "health": {"stars": 13000, "forks": 2000, "open_issues": 42, "contributors": 90,
             "top_contributor_share": 0.31, "last_commit": "2026-09-09", "last_release": "v4.2.0",
             "commits_last_90d": 120, "issues_closed_last_90d": 30},

  "verdict": {"best_for": "one sentence — which business asks this repo fits",
              "weak_for": "one sentence — what it cannot do without real work",
              "swap_burden": "none|light|medium|heavy — one clause saying why"},

  "evidence": {"framework": "package.json dependencies", "auth": "src/lib/auth.ts", "vendor": ".env.example + package.json", "deploy": "Dockerfile", "health": "gh api repos/…"},
  "unmeasured": ["list of fields you could not measure and why"]
}
```

## Quality bar

- `blocking` is the ONLY channel for a claim that stops a template from being used: an array of
  `{"kind": "injected-payload" | "install-impossible", "why": "…", "evidence": "file/URL + how you
  checked"}`. Leave it `[]` when there is nothing of the sort — most repos have `[]`. Nothing is
  derived from `pitfalls` prose, so a pitfall that merely *mentions* obfuscation or a lockfile must
  NOT become a blocking entry: the condition has to be true, and your `evidence` must show the check
  you ran (a 404 from the registry, the character count of the blob, …).
- `routes.pages` / `routes.api`: real paths from the tree or the app directory, not guesses.
- `features`: only what the CODE shows (a route, a component, a dependency) — never README promises.
  Note the difference in `evidence` when the README claims something the code does not show.
- `health.top_contributor_share`: fraction of commits by the single most active contributor (0–1).
- `vendor`: every paid/SaaS dependency you can see in dependencies, env names or code imports.
- `pitfalls`: the things that would waste an hour of a fresh agent's time (build-time env validation,
  native modules, postinstall scripts, dead demo pages, docs that contradict the code).
