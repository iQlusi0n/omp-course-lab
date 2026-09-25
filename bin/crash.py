#!/usr/bin/env python3
"""DAP fixture: crashes deterministically with an AttributeError.

    python3 bin/crash.py          # -> traceback, exit code 1

The bug: ``find_user`` returns ``None`` for an unknown id and ``display_name``
dereferences it. Fix the code so the script prints a report for every id and
exits 0.
"""

from dataclasses import dataclass


@dataclass
class User:
    id: int
    name: str
    email: str


USERS = [
    User(1, "Ada Lovelace", "ada@example.com"),
    User(2, "Grace Hopper", "grace@example.com"),
    User(3, "Linus Torvalds", "linus@example.com"),
]

WANTED_IDS = [1, 2, 99, 3]


def find_user(user_id: int):
    for user in USERS:
        if user.id == user_id:
            return user
    return None


def display_name(user) -> str:
    """Render 'Name <email>' for the report line."""
    return f"{user.name} <{user.email}>"


def main() -> int:
    for user_id in WANTED_IDS:
        user = find_user(user_id)
        print(f"{user_id:>3}: {display_name(user)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
