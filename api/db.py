"""SQLite access layer for the lab API.

All functions open a fresh connection per call (the DB is tiny) and return
plain dicts so callers can JSON-encode them directly.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from generated.schema_info import STATUSES

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = REPO_ROOT / "data" / "lab.sqlite"
PAGE_SIZE = 10


class LabError(Exception):
    """Raised for user-facing failures (bad input, missing DB, ...)."""


def db_path() -> str:
    """Resolve the database location.

    ``DATABASE_URL`` wins when set (see .env.example), otherwise data/lab.sqlite.
    """
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    return str(DEFAULT_DB)


def connect() -> sqlite3.Connection:
    path = db_path()
    try:
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        conn.execute("SELECT 1 FROM users LIMIT 1")
    except sqlite3.OperationalError:
        raise LabError(
            "database is locked (is another process using data/lab.sqlite?)"
        ) from None
    return conn


def get_user(user_id: int) -> dict | None:
    """Return one user with their ``order_count`` (non-cancelled orders)."""
    with connect() as conn:
        row = conn.execute(
            "SELECT id, name, email, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            return None
        user = dict(row)
        user["order_count"] = count_orders(conn, user_id)
        return user


def count_orders(conn: sqlite3.Connection, user_id: int) -> int:
    """Number of orders that are still 'live' for a user (cancelled ones excluded)."""
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM orders WHERE user_id = ? AND status != 'canceled'",
        (user_id,),
    ).fetchone()
    return int(row["n"])


def list_orders(
    month: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict]:
    """Orders, newest first. ``month`` is ``YYYY-MM``. ``limit=None`` disables paging."""
    sql = "SELECT id, user_id, created_at, status, total_cents FROM orders"
    args: list = []
    if month:
        sql += " WHERE substr(created_at, 1, 7) = ?"
        args.append(month)
    sql += " ORDER BY created_at DESC, id DESC"
    if limit is not None:
        sql += " LIMIT ? OFFSET ?"
        args += [offset, limit]
    with connect() as conn:
        return [dict(r) for r in conn.execute(sql, args)]


def count_orders_in_month(month: str | None) -> int:
    sql = "SELECT COUNT(*) AS n FROM orders"
    args: list = []
    if month:
        sql += " WHERE substr(created_at, 1, 7) = ?"
        args.append(month)
    with connect() as conn:
        return int(conn.execute(sql, args).fetchone()["n"])


def get_order(order_id: int) -> dict | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT id, user_id, created_at, status, total_cents FROM orders WHERE id = ?",
            (order_id,),
        ).fetchone()
        return dict(row) if row else None


def create_user(name: str, email: str) -> dict:
    """Insert a user. Raises sqlite3.IntegrityError on a duplicate email."""
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO users (name, email, created_at) VALUES (?, ?, date('now'))",
            (name, email),
        )
        return {"id": cur.lastrowid, "name": name, "email": email}


def orders_per_month() -> list[dict]:
    """[{month, count, total_cents}] ascending by month."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT substr(created_at, 1, 7) AS month, COUNT(*) AS count,"
            " SUM(total_cents) AS total_cents FROM orders GROUP BY month ORDER BY month"
        )
        return [dict(r) for r in rows]


def valid_status(status: str) -> bool:
    return status in STATUSES
