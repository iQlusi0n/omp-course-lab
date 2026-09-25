#!/usr/bin/env python3
"""Create data/lab.sqlite deterministically and regenerate generated/schema_info.py.

    python3 tools/seed_db.py            # writes data/lab.sqlite (overwrites)
    python3 tools/seed_db.py --db /tmp/x.sqlite --no-generated
"""

from __future__ import annotations

import argparse
import random
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_VERSION = 1
STATUSES = ("pending", "shipped", "completed", "cancelled")
STATUS_WEIGHTS = (10, 15, 65, 10)

USERS = [
    ("Ada Lovelace", "ada@example.com", "2025-09-02"),
    ("Grace Hopper", "grace@example.com", "2025-09-14"),
    ("Linus Torvalds", "linus@example.com", "2025-09-30"),
    ("Margaret Hamilton", "margaret@example.com", "2025-10-03"),
    ("Dennis Ritchie", "dennis@example.com", "2025-10-19"),
    ("Barbara Liskov", "barbara@example.com", "2025-11-05"),
    ("Ken Thompson", "ken@example.com", "2025-11-21"),
    ("Radia Perlman", "radia@example.com", "2025-12-08"),
    ("Guido van Rossum", "guido@example.com", "2025-12-27"),
    ("Frances Allen", "frances@example.com", "2026-01-11"),
    ("Bjarne Stroustrup", "bjarne@example.com", "2026-01-29"),
    ("Katherine Johnson", "katherine@example.com", "2026-02-10"),
]

MONTHS = ["2025-10", "2025-11", "2025-12", "2026-01", "2026-02", "2026-03", "2026-04", "2026-05"]
ORDERS_PER_MONTH = [6, 8, 11, 9, 10, 12, 9, 7]  # 72 orders

SCHEMA = """
CREATE TABLE users (
    id         INTEGER PRIMARY KEY,
    name       TEXT NOT NULL,
    email      TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);
CREATE TABLE orders (
    id          INTEGER PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    created_at  TEXT NOT NULL,
    status      TEXT NOT NULL CHECK (status IN ('pending','shipped','completed','cancelled')),
    total_cents INTEGER NOT NULL
);
CREATE INDEX orders_user_idx ON orders(user_id);
CREATE INDEX orders_month_idx ON orders(substr(created_at, 1, 7));
CREATE TABLE schema_version (version INTEGER NOT NULL);
"""


def build(db_path: Path) -> None:
    rng = random.Random(42)
    if db_path.exists():
        db_path.unlink()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.executemany("INSERT INTO users (name, email, created_at) VALUES (?, ?, ?)", USERS)
    conn.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))

    rows = []
    for month, n in zip(MONTHS, ORDERS_PER_MONTH):
        days = sorted(rng.randint(1, 28) for _ in range(n))
        for day in days:
            user_id = rng.randint(1, len(USERS))
            status = rng.choices(STATUSES, STATUS_WEIGHTS)[0]
            total = rng.randint(5, 400) * 100 + rng.choice((0, 50, 99))
            rows.append((user_id, f"{month}-{day:02d}", status, total))
    conn.executemany(
        "INSERT INTO orders (user_id, created_at, status, total_cents) VALUES (?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()


def write_generated(out_dir: Path) -> None:
    out_dir.mkdir(exist_ok=True)
    (out_dir / "__init__.py").write_text(
        "# GENERATED — do not edit\n"
        "# Package marker for generated modules. Regenerate with tools/seed_db.py.\n"
    )
    (out_dir / "schema_info.py").write_text(
        "# GENERATED — do not edit\n"
        "# Produced by tools/seed_db.py from data/lab.sqlite. Re-run the seeder to change it.\n"
        "\n"
        f"SCHEMA_VERSION = {SCHEMA_VERSION}\n"
        "\n"
        f"STATUSES = {STATUSES!r}\n"
        "\n"
        'TABLES = ("users", "orders", "schema_version")\n'
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", type=Path, default=ROOT / "data" / "lab.sqlite")
    parser.add_argument("--no-generated", action="store_true", help="skip generated/ refresh")
    args = parser.parse_args(argv)
    build(args.db)
    if not args.no_generated:
        write_generated(ROOT / "generated")
    conn = sqlite3.connect(args.db)
    users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    months = conn.execute("SELECT COUNT(DISTINCT substr(created_at,1,7)) FROM orders").fetchone()[0]
    print(f"seeded {args.db}: {users} users, {orders} orders across {months} months")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
