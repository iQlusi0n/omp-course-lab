"""One failing test per seeded issue in docs/ISSUES.md.

Every test here is skipped unless ``LAB_ISSUE=<n>`` (or ``LAB_ISSUE=all``) is
set, so the main suite stays green while the bugs are still in the tree:

    LAB_ISSUE=1 python3 -m unittest tests.test_issues     # fails on main, passes when fixed
"""

import csv
import io
import os
import re
import sqlite3
import unittest
from unittest import mock

from tests.support import ROOT, LiveServer, TempDB, run_cli

from api import db, get_user

LAB_ISSUE = os.environ.get("LAB_ISSUE", "")


def issue(n: int):
    return unittest.skipUnless(LAB_ISSUE in (str(n), "all"), f"set LAB_ISSUE={n} to run")


class WithDb(unittest.TestCase):
    def setUp(self):
        self._db = TempDB().__enter__()
        self.addCleanup(self._db.__exit__, None, None, None)


class WithServer(WithDb):
    def setUp(self):
        super().setUp()
        self.srv = LiveServer().__enter__()
        self.addCleanup(self.srv.__exit__, None, None, None)


@issue(1)
class Issue1MoneyFormatting(WithDb):
    def test_money_is_cents_over_100(self):
        from cli.format import money
        self.assertEqual(money(1234), "$12.34")
        self.assertEqual(money(100), "$1.00")
        self.assertEqual(money(5), "$0.05")

    def test_cli_month_total(self):
        result = run_cli("orders", "--month", "2026-03")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.rstrip().endswith("total $1943.94"), result.stdout.splitlines()[-1])


@issue(2)
class Issue2OrdersPagination(WithServer):
    def test_first_page_has_ten_newest(self):
        status, body = self.srv.get("/orders?month=2026-03")
        self.assertEqual(status, 200)
        self.assertEqual(body["count"], 12)
        expected = [o["id"] for o in db.list_orders(month="2026-03")[:10]]
        self.assertEqual([o["id"] for o in body["orders"]], expected)

    def test_second_page_has_remainder(self):
        status, body = self.srv.get("/orders?month=2026-03&page=2")
        self.assertEqual(status, 200)
        expected = [o["id"] for o in db.list_orders(month="2026-03")[10:]]
        self.assertEqual([o["id"] for o in body["orders"]], expected)
        self.assertEqual(len(body["orders"]), 2)


@issue(3)
class Issue3CsvExport(WithDb):
    def test_csv_format(self):
        result = run_cli("orders", "--month", "2026-03", "--format", "csv")
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = list(csv.reader(io.StringIO(result.stdout)))
        self.assertEqual(rows[0], ["id", "user_id", "created_at", "status", "total_cents"])
        self.assertEqual(len(rows), 1 + 12)
        self.assertTrue(all(r[2].startswith("2026-03") for r in rows[1:]))
        self.assertTrue(all(r[4].isdigit() for r in rows[1:]))

    def test_table_is_still_default(self):
        result = run_cli("orders", "--month", "2026-03")
        self.assertEqual(result.returncode, 0)
        self.assertTrue(result.stdout.startswith("id "))


@issue(4)
class Issue4StatsCommand(WithDb):
    def test_stats_one_line_per_month(self):
        from cli.format import money
        result = run_cli("stats")
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.strip().splitlines()
        expected = db.orders_per_month()
        self.assertEqual(len(lines), len(expected))
        pattern = re.compile(r"^(\d{4}-\d{2})\s+(\d+) orders\s+(\$[\d,]+\.\d{2})$")
        for line, row in zip(lines, expected):
            m = pattern.match(line)
            self.assertIsNotNone(m, line)
            self.assertEqual(m.group(1), row["month"])
            self.assertEqual(int(m.group(2)), row["count"])
            self.assertEqual(m.group(3), money(row["total_cents"]))


@issue(5)
class Issue5OrderCancellation(WithServer):
    def _order_with_status(self, status):
        with db.connect() as conn:
            return conn.execute("SELECT id FROM orders WHERE status = ? ORDER BY id LIMIT 1", (status,)).fetchone()["id"]

    def test_delete_pending_order_cancels_it(self):
        oid = self._order_with_status("pending")
        status, body = self.srv.request("DELETE", f"/orders/{oid}")
        self.assertEqual(status, 200)
        self.assertEqual(body["id"], oid)
        self.assertEqual(body["status"], "cancelled")
        self.assertEqual(db.get_order(oid)["status"], "cancelled")

    def test_delete_missing_order_404(self):
        self.assertEqual(self.srv.request("DELETE", "/orders/999999")[0], 404)

    def test_delete_completed_order_409(self):
        oid = self._order_with_status("completed")
        status, body = self.srv.request("DELETE", f"/orders/{oid}")
        self.assertEqual(status, 409)
        self.assertEqual(db.get_order(oid)["status"], "completed")

    def test_cli_cancel(self):
        oid = self._order_with_status("shipped")
        result = run_cli("cancel", str(oid))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"order {oid} cancelled", result.stdout)
        self.assertEqual(db.get_order(oid)["status"], "cancelled")


@issue(6)
class Issue6DatabaseUrlPrefix(unittest.TestCase):
    def test_sqlite_url_prefix_is_accepted(self):
        result = run_cli("users", "1", env={"DATABASE_URL": "sqlite:///data/lab.sqlite"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Ada Lovelace", result.stdout)

    def test_absolute_sqlite_url(self):
        with TempDB() as tdb:
            result = run_cli("users", "1", env={"DATABASE_URL": f"sqlite:///{tdb.path}"})
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_file_error_names_the_real_cause(self):
        result = run_cli("users", "1", env={"DATABASE_URL": "/nonexistent/lab.sqlite"})
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("locked", result.stderr)
        self.assertIn("/nonexistent/lab.sqlite", result.stderr)


@issue(7)
class Issue7OrderCountExcludesCancelled(WithDb):
    def test_every_user_count_matches_sql(self):
        with db.connect() as conn:
            expected = {
                r["user_id"]: r["n"]
                for r in conn.execute(
                    "SELECT user_id, COUNT(*) AS n FROM orders WHERE status != 'cancelled' GROUP BY user_id"
                )
            }
        for user_id, n in expected.items():
            self.assertEqual(get_user(user_id)["order_count"], n, f"user {user_id}")

    def test_user_9_has_five_live_orders(self):
        self.assertEqual(get_user(9)["order_count"], 5)


@issue(8)
class Issue8SignupValidation(WithServer):
    def test_missing_field_400(self):
        status, body = self.srv.post("/signup", {"email": "x@example.com"})
        self.assertEqual(status, 400)
        self.assertIn("name", body["error"])

    def test_malformed_email_400(self):
        status, body = self.srv.post("/signup", {"name": "X", "email": "not-an-email"})
        self.assertEqual(status, 400)
        self.assertIn("email", body["error"])

    def test_duplicate_email_409(self):
        status, body = self.srv.post("/signup", {"name": "Ada Again", "email": "ada@example.com"})
        self.assertEqual(status, 409)
        self.assertIn("error", body)

    def test_unexpected_failure_is_still_500(self):
        with mock.patch("api.server.db.create_user", side_effect=RuntimeError("disk on fire")):
            status, body = self.srv.post("/signup", {"name": "X", "email": "x@example.com"})
        self.assertEqual(status, 500)
        self.assertIn("error", body)


if __name__ == "__main__":
    unittest.main()
