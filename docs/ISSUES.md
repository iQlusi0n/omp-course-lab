# Seeded issues

Each issue below is deliberately present on `main`. Each has a test in
`tests/test_issues.py` that is **skipped unless `LAB_ISSUE=<n>`** is set, so the
normal suite stays green:

```
python3 -m unittest discover -s tests                 # always green on main
LAB_ISSUE=3 python3 -m unittest tests.test_issues     # fails until #3 is done
LAB_ISSUE=all python3 -m unittest tests.test_issues   # every seeded test
```

Run all commands from the repository root. `python3 -m api` must be running on
port 8080 for the `curl` repros.

---

## #1 — CLI shows money 10× too large

**Module:** 1 (quickstart: "inspect for one small bug, make the smallest safe fix, run the relevant check").

**Repro today**
```
python3 -m cli orders --month 2026-03
# last line: 12 orders for 2026-03, total $19439.40   (DB says 194394 cents)
LAB_ISSUE=1 python3 -m unittest tests.test_issues     # FAIL
```
**Expected:** `$1943.94`; `money(1234)` returns `$12.34`.

**Files:** `cli/format.py` (one line).

---

## #2 — `GET /orders` first page is missing orders

**Module:** 2 (a fix that touches two files).

**Repro today**
```
curl -s 'http://127.0.0.1:8080/orders?month=2026-03' | python3 -m json.tool
# "count": 12 but "orders" has only 2 entries; page=2 also returns 2
LAB_ISSUE=2 python3 -m unittest tests.test_issues     # FAIL
```
**Expected:** page 1 returns the 10 newest orders of the month, page 2 the
remaining 2 (`page_size` is 10; `count` stays 12). Fixing only one file makes
it worse or leaves it broken — both halves of the pagination path are wrong.

**Files:** `api/server.py` (`_list_orders` offset), `api/db.py` (`list_orders` LIMIT/OFFSET).

---

## #3 — CLI: `orders` has no `--format csv` (export for spreadsheets)

**Module:** 3 (same task with a vague prompt, then a structured prompt).

**Repro today**
```
python3 -m cli orders --month 2026-03 --format csv
# error: unrecognized arguments: --format csv   (exit 2)
LAB_ISSUE=3 python3 -m unittest tests.test_issues     # FAIL
```
**Expected:** `--format {table,csv}` (default `table`). CSV output is written by
the `csv` module with header `id,user_id,created_at,status,total_cents`, one row
per order, `total_cents` as an integer, no summary line. The table output is
unchanged.

**Files:** `cli/__main__.py` (argparse), `cli/commands.py` (rendering).

---

## #4 — Add a `stats` subcommand (orders per month)

**Module:** 4 (approval mode `always-ask`: the natural implementation edits
several files and runs commands, producing multiple approval prompts).

**Repro today**
```
python3 -m cli stats
# argument command: invalid choice: 'stats'   (exit 2)
LAB_ISSUE=4 python3 -m unittest tests.test_issues     # FAIL
```
**Expected:** one line per month in ascending order, formatted exactly
`YYYY-MM  <n> orders  <total>` where `<total>` comes from `cli.format.money`.
Use `api.db.orders_per_month()` (already implemented). Also: add a test for the
command in `tests/`, document it in `README.md`, and run the test suite.

**Files:** `cli/__main__.py`, `cli/commands.py`, `tests/`, `README.md`.

---

## #5 — Order cancellation (feature for plan mode)

**Module:** 4 (plan mode; annotate sub-item (c) as out of scope before accepting).

**Repro today**
```
curl -s -X DELETE http://127.0.0.1:8080/orders/1
# {"error": "no DELETE route for /orders/1"}   (404)
python3 -m cli cancel 1                                # invalid choice (exit 2)
LAB_ISSUE=5 python3 -m unittest tests.test_issues     # FAIL
```
**Feature request, as written by the product owner:**

- (a) `DELETE /orders/<id>` marks the order `cancelled` and returns `200` with
  `{"id": <id>, "status": "cancelled"}`. `404` when the order does not exist.
  `409` when the order is already `shipped` or `completed` (nothing changes).
- (b) `python3 -m cli cancel <id>` does the same through the database and prints
  `order <id> cancelled` (exit 0), or an error and exit 1.
- (c) Email the customer a cancellation confirmation. **Deliberately out of
  scope** — the lab has no mail infrastructure; the plan should drop this item.

**Files:** `api/server.py`, `api/db.py`, `cli/__main__.py`, `cli/commands.py`.

---

## #6 — "database is locked" when `DATABASE_URL` uses the `sqlite:///` form

**Module:** 9 (a misleading error to learn from, then `learn` the lesson).

**Repro today**
```
DATABASE_URL=sqlite:///data/lab.sqlite python3 -m cli users 1
# error: database is locked (is another process using data/lab.sqlite?)   (exit 2)
LAB_ISSUE=6 python3 -m unittest tests.test_issues     # FAIL
```
**Gotcha:** nothing is locked. `.env.example` documents the URL form
`sqlite:///data/lab.sqlite`, but `api/db.py::db_path()` hands the whole string
to `sqlite3.connect`, which treats `sqlite:` as a directory name and fails with
"unable to open database file". `connect()` then swallows that and raises a
*different*, invented message. Investigating locks, WAL files or a running
server is a dead end.

**Expected:** `sqlite:///<path>` is accepted (strip the prefix; relative paths
stay relative to the working directory), and a genuinely missing database
reports the real cause including the path — never "locked".

**Files:** `api/db.py` (`db_path`, `connect`).

---

## #7 — `order_count` includes cancelled orders

**Module:** 9 (checkpoint/rewind: an investigation with a red herring).

**Repro today**
```
python3 -m cli users 9
# orders: 7
python3 -c "import sqlite3; print(sqlite3.connect('data/lab.sqlite').execute(\"select count(*) from orders where user_id=9 and status!='cancelled'\").fetchone())"
# (5,)
LAB_ISSUE=7 python3 -m unittest tests.test_issues     # FAIL
```
**Expected:** `order_count` (API and CLI) excludes cancelled orders: user 9 → 5.

**Red herrings you will meet:** the CLI's "default to 0" comment in
`cli/commands.py`, the "check the seed" note in `api/server.py`, and
`tools/seed_db.py` itself. None of them is the cause; the seed is correct
(`generated/schema_info.py` lists the real status values).

**Files:** `api/db.py` (one function).

---

## #8 — `POST /signup` returns 500 on bad input

**Module:** 11 (advisor watchdog: it is tempting to wrap the handler in a
catch-all and return 400 for everything).

**Repro today**
```
curl -s -X POST http://127.0.0.1:8080/signup -H 'Content-Type: application/json' -d '{"name":"Ada Again","email":"ada@example.com"}'
# {"error": "internal error", "detail": "IntegrityError('UNIQUE constraint failed: users.email')", ...}   (500)
curl -s -X POST http://127.0.0.1:8080/signup -H 'Content-Type: application/json' -d '{"name":"X","email":"not-an-email"}'
# 201 Created — accepted a nonsense email
LAB_ISSUE=8 python3 -m unittest tests.test_issues     # FAIL
```
**Expected:**
- missing `name`/`email`, or an email without `@` → `400` with an error message naming the field
- duplicate email (`sqlite3.IntegrityError`) → `409`
- any *other* exception → still `500` (the gated test patches `create_user` to
  raise and expects a 500 — swallowing every exception fails it)

**Files:** `api/server.py` (`_signup`), optionally `api/db.py`.
