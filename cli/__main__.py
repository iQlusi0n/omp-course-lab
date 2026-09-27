"""``python -m cli`` — command-line client for the lab database.

    python -m cli users 1
    python -m cli orders --month 2026-03
    python -m cli health
"""

from __future__ import annotations

import argparse
import sys

from api import LabError
from generated.schema_info import STATUSES

from . import commands

DESCRIPTION = "omp-course-lab CLI v1"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m cli", description=DESCRIPTION)
    sub = parser.add_subparsers(dest="command", required=True)

    p_users = sub.add_parser("users", help="show one user")
    p_users.add_argument("user_id", type=int)

    p_orders = sub.add_parser("orders", help="list orders")
    p_orders.add_argument("--month", help="filter by month, YYYY-MM")
    p_orders.add_argument("--status", choices=STATUSES, help="filter by order status")

    sub.add_parser("health", help="show database summary")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "users":
            return commands.cmd_users(args.user_id)
        if args.command == "orders":
            return commands.cmd_orders(args.month, args.status)
        if args.command == "health":
            return commands.cmd_health()
    except LabError as e:
        sys.stderr.write(f"error: {e}\n")
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
