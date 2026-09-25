"""Command implementations for ``python -m cli``.

Each command returns an exit code and prints its result with ``print``.
"""

from __future__ import annotations

from api import get_user
from api import db

from .format import money, table


def cmd_users(user_id: int) -> int:
    user = get_user(user_id)
    if user is None:
        print(f"user {user_id} not found")
        return 1
    # order_count may be missing when talking to an older API; default to 0.
    count = int(user.get("order_count") or 0)
    print(f"#{user['id']}  {user['name']} <{user['email']}>")
    print(f"since:  {user['created_at']}")
    print(f"orders: {count}")
    return 0


def cmd_orders(month: str | None) -> int:
    orders = db.list_orders(month=month)
    label = month or "all months"
    if not orders:
        print(f"no orders for {label}")
        return 0
    rows = [
        [str(o["id"]), o["created_at"], str(o["user_id"]), o["status"], money(o["total_cents"])]
        for o in orders
    ]
    for line in table(rows, ["id", "date", "user", "status", "total"]):
        print(line)
    total = sum(o["total_cents"] for o in orders)
    print(f"{len(orders)} orders for {label}, total {money(total)}")
    return 0


def cmd_health() -> int:
    with db.connect() as conn:
        users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    print(f"db: {db.db_path()}")
    print(f"users: {users}")
    print(f"orders: {orders}")
    return 0
