import unittest

from tests.support import TempDB, run_cli


class CliTests(unittest.TestCase):
    def setUp(self):
        self._db = TempDB().__enter__()
        self.addCleanup(self._db.__exit__, None, None, None)

    def test_users_shows_name_and_email(self):
        result = run_cli("users", "1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Ada Lovelace <ada@example.com>", result.stdout)
        self.assertIn("orders:", result.stdout)

    def test_users_missing_exits_1(self):
        result = run_cli("users", "9999")
        self.assertEqual(result.returncode, 1)
        self.assertIn("not found", result.stdout)

    def test_orders_month_table(self):
        result = run_cli("orders", "--month", "2026-03")
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.splitlines()
        self.assertTrue(lines[0].startswith("id"))
        self.assertIn("12 orders for 2026-03, total $", lines[-1])

    def test_orders_empty_month(self):
        result = run_cli("orders", "--month", "2031-01")
        self.assertEqual(result.returncode, 0)
        self.assertIn("no orders for 2031-01", result.stdout)

    def test_health(self):
        result = run_cli("health")
        self.assertEqual(result.returncode, 0)
        self.assertIn("users: 12", result.stdout)

    def test_missing_db_exit_2(self):
        result = run_cli("users", "1", env={"DATABASE_URL": "/nonexistent/lab.sqlite"})
        self.assertEqual(result.returncode, 2)
        self.assertTrue(result.stderr.startswith("error:"))

    def test_usage_error(self):
        result = run_cli("users")
        self.assertEqual(result.returncode, 2)

    # ----- v2: orders --status --------------------------------------------

    def test_orders_status_filter_combines_with_month(self):
        result = run_cli("orders", "--month", "2026-03", "--status", "completed")
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.splitlines()
        rows = [ln.split() for ln in lines[1:-1]]
        self.assertTrue(rows, result.stdout)
        self.assertTrue(all(r[1].startswith("2026-03") and r[3] == "completed" for r in rows), result.stdout)
        self.assertIn(f"{len(rows)} orders for 2026-03 (completed), total $", lines[-1])

    def test_orders_status_alone(self):
        result = run_cli("orders", "--status", "cancelled")
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = [ln.split() for ln in result.stdout.splitlines()[1:-1]]
        self.assertTrue(all(r[3] == "cancelled" for r in rows), result.stdout)

    def test_orders_invalid_status_is_usage_error(self):
        result = run_cli("orders", "--status", "bogus")
        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid choice", result.stderr)

    def test_orders_table_unchanged_without_status(self):
        result = run_cli("orders", "--month", "2026-03")
        self.assertEqual(result.returncode, 0)
        self.assertIn("12 orders for 2026-03, total $", result.stdout.splitlines()[-1])


if __name__ == "__main__":
    unittest.main()
