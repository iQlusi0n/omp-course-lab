#!/usr/bin/env python3
"""Migrate a lab database to schema version 2 (adds ``users.company``).

    python3 tools/migrate.py               # migrates data/lab.sqlite
    python3 tools/migrate.py --db PATH     # migrates another database

Idempotent: a database that is already at version 2 is left untouched and the
tool prints ``already at version 2``.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET_VERSION = 2


def current_version(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT version FROM schema_version").fetchone()
    if row is None:
        raise SystemExit("schema_version table is empty; not a lab database")
    return int(row[0])


def has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    return any(r[1] == column for r in conn.execute(f"PRAGMA table_info({table})"))


def migrate(db_path: Path) -> int:
    """Return the schema version the database is at after the call."""
    if not db_path.exists():
        raise SystemExit(f"no database at {db_path}")
    conn = sqlite3.connect(db_path)
    try:
        version = current_version(conn)
        if version >= TARGET_VERSION:
            print(f"already at version {version}")
            return version
        if not has_column(conn, "users", "company"):
            conn.execute("ALTER TABLE users ADD COLUMN company TEXT")
        conn.execute("UPDATE schema_version SET version = ?", (TARGET_VERSION,))
        conn.commit()
        print(f"migrated {db_path} from version {version} to {TARGET_VERSION}")
        return TARGET_VERSION
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", type=Path, default=ROOT / "data" / "lab.sqlite")
    args = parser.parse_args(argv)
    migrate(args.db)
    return 0


if __name__ == "__main__":
    sys.exit(main())
