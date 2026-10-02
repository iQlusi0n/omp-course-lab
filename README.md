# omp-course-lab

The practice repository for the *Working with omp* course
(`omp-course`, which includes this repo as a git submodule). Python 3 standard
library only — nothing to install.

```
python3 -m api                        # JSON API + web form on http://127.0.0.1:8080
python3 -m cli users 1                # CLI client (reads data/lab.sqlite directly)
python3 -m cli orders --month 2026-03
python3 -m cli health
python3 -m unittest discover -s tests # test suite (< 10 s)
```

Run everything from the repository root. Set `DATABASE_URL=/path/to.sqlite` to
point at another database (see `.env.example`).

## Layout

| path | what it is |
|---|---|
| `api/` | `http.server` JSON service: `GET /health`, `GET /users/<id>`, `GET /orders?month=&page=`, `POST /signup`; serves `web/` at `/`. `api/__init__.py` re-exports `get_user`. |
| `cli/` | argparse client (`users`, `orders`, `health`); `cli/log.py` provides `logger` (stdout, message-only). |
| `web/` | signup form (`#signup-form`, `#name`, `#email`, button "Sign up"); success banner `#banner` reads `Welcome aboard!`. |
| `generated/` | machine-written constants (`# GENERATED — do not edit`), refreshed by `tools/seed_db.py`. |
| `data/lab.sqlite` | seeded DB: 12 users, 72 orders across 8 months (2025-10 … 2026-05); tables `users`, `orders`, `schema_version`. |
| `docs/spec.md`, `docs/spec.pdf` | service spec; PDF built by `tools/make_pdf.py` (3 pages). |
| `docs/ISSUES.md` | seeded issues #1–#8 with repro commands. |
| `docs/V2-SPEC.md` | capstone feature set. |
| `fixtures/bundle.zip` | `README.md`, `data/sample.csv`, `config.json` (built by `tools/make_bundle.py`). |
| `bin/crash.py` | crashes with `AttributeError: 'NoneType' object has no attribute 'name'` (debugger fixture). |
| `bin/crash.c` | NULL-pointer crash; compile: `cc -g -O0 -o bin/crash bin/crash.c`. |
| `bin/gui-demo.py` | Tk window "Lab GUI Demo": label "Ready", button "Click me" → "Clicked!" (needs `python3-tk`). |
| `tools/mock-provider.py` | OpenAI-compatible mock (`/v1/models`, `/v1/chat/completions`, model `mock-1`, port 8765, `--fail` → 429). |
| `tools/seed_db.py` | rebuilds `data/lab.sqlite` + `generated/` deterministically. |
| `tests/` | unittest suite; `tests/test_issues.py` holds the gated issue tests. |
| `ci/` | empty; learners add `review.sh` here. |
| `notes/` | learner scratch output; gitignored (only `.gitkeep` is tracked). |
| `.omp/` | empty at `module-1-start`; learners populate it. |
| `.env.example` | `LAB_TOKEN` (fake secret, `labtok_` + 16 hex) and `DATABASE_URL`. |

## Seeded issues and the `LAB_ISSUE` gate

`docs/ISSUES.md` describes eight deliberate problems. Each has a test in
`tests/test_issues.py` that only runs when `LAB_ISSUE=<n>` (or `all`) is set,
so `main` stays green:

```
LAB_ISSUE=1 python3 -m unittest tests.test_issues   # fails on main; passes once #1 is fixed
```

## Git fixtures

- Tags `module-1-start` … `module-15-start` all point at the same `main` commit
  (the course starts every module from a clean tree).
- Branch `conflict-lab` conflicts with `main` in `api/server.py` and
  `cli/__main__.py` (both sides changed the service/CLI description). Merge it
  from a scratch branch to practise conflict resolution:
  `git switch -c scratch main && git merge conflict-lab`.
- Branch `capstone-solution` (instructor reference): the Module 15 v2 feature
  set implemented on top of `module-15-start`; 65 tests green.

## Regenerating fixtures

```
python3 tools/seed_db.py      # data/lab.sqlite + generated/
python3 tools/make_pdf.py     # docs/spec.pdf from docs/spec.md
python3 tools/make_bundle.py  # fixtures/bundle.zip
```
