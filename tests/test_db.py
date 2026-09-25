import sqlite3
import unittest

from tests.support import TempDB

from api import db, get_user


class SeedInvariants(unittest.TestCase):
    def test_seed_shape(self):
        with TempDB(), db.connect() as conn:
            users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
            months = conn.execute("SELECT COUNT(DISTINCT substr(created_at,1,7)) FROM orders").fetchone()[0]
            bad = conn.execute("SELECT COUNT(*) FROM orders WHERE status NOT IN ('pending','shipped','completed','cancelled')").fetchone()[0]
        self.assertGreaterEqual(users, 10)
        self.assertGreaterEqual(orders, 50)
        self.assertGreaterEqual(months, 6)
        self.assertEqual(bad, 0)


class Users(unittest.TestCase):
    def test_get_user_returns_record_with_count(self):
        with TempDB():
            user = get_user(1)
        self.assertEqual(user["email"], "ada@example.com")
        self.assertIsInstance(user["order_count"], int)
        self.assertGreaterEqual(user["order_count"], 0)

    def test_get_user_missing(self):
        with TempDB():
            self.assertIsNone(get_user(9999))

    def test_create_user_then_get(self):
        with TempDB():
            created = db.create_user("New Person", "new@example.com")
            fetched = get_user(created["id"])
        self.assertEqual(fetched["email"], "new@example.com")
        self.assertEqual(fetched["order_count"], 0)

    def test_create_user_duplicate_email_raises(self):
        with TempDB():
            with self.assertRaises(sqlite3.IntegrityError):
                db.create_user("Ada Again", "ada@example.com")


class Orders(unittest.TestCase):
    def test_month_filter(self):
        with TempDB():
            orders = db.list_orders(month="2026-03")
        self.assertTrue(orders)
        self.assertTrue(all(o["created_at"].startswith("2026-03") for o in orders))

    def test_newest_first(self):
        with TempDB():
            orders = db.list_orders()
        dates = [o["created_at"] for o in orders]
        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_count_matches_listing(self):
        with TempDB():
            self.assertEqual(db.count_orders_in_month("2026-03"), len(db.list_orders(month="2026-03")))
            self.assertEqual(db.count_orders_in_month(None), len(db.list_orders()))

    def test_orders_per_month_sums(self):
        with TempDB():
            rows = db.orders_per_month()
            total = db.count_orders_in_month(None)
        self.assertEqual(sum(r["count"] for r in rows), total)
        self.assertEqual([r["month"] for r in rows], sorted(r["month"] for r in rows))


class Config(unittest.TestCase):
    def test_missing_database_is_a_lab_error(self):
        with TempDB():
            import os
            os.environ["DATABASE_URL"] = "/nonexistent/dir/lab.sqlite"
            with self.assertRaises(db.LabError):
                db.connect()


if __name__ == "__main__":
    unittest.main()
