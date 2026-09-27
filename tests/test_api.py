import unittest

from tests.support import LiveServer, TempDB


class ApiTests(unittest.TestCase):
    def setUp(self):
        self._db = TempDB().__enter__()
        self._srv = LiveServer().__enter__()
        self.addCleanup(self._srv.__exit__, None, None, None)
        self.addCleanup(self._db.__exit__, None, None, None)

    def test_health(self):
        status, body = self._srv.get("/health")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")

    def test_get_user(self):
        status, body = self._srv.get("/users/1")
        self.assertEqual(status, 200)
        self.assertEqual(body["name"], "Ada Lovelace")
        self.assertIn("order_count", body)

    def test_get_user_404(self):
        status, body = self._srv.get("/users/9999")
        self.assertEqual(status, 404)
        self.assertIn("error", body)

    def test_orders_month_count(self):
        status, body = self._srv.get("/orders?month=2026-03")
        self.assertEqual(status, 200)
        self.assertEqual(body["count"], 12)
        self.assertEqual(body["page"], 1)
        self.assertTrue(all(o["created_at"].startswith("2026-03") for o in body["orders"]))

    def test_orders_bad_month(self):
        status, body = self._srv.get("/orders?month=march")
        self.assertEqual(status, 400)
        self.assertIn("YYYY-MM", body["error"])

    def test_orders_bad_page(self):
        self.assertEqual(self._srv.get("/orders?page=0")[0], 400)
        self.assertEqual(self._srv.get("/orders?page=x")[0], 400)

    def test_signup_creates_user(self):
        status, body = self._srv.post("/signup", {"name": "Web User", "email": "web@example.com"})
        self.assertEqual(status, 201)
        self.assertEqual(body["email"], "web@example.com")
        status, user = self._srv.get(f"/users/{body['id']}")
        self.assertEqual(status, 200)
        self.assertEqual(user["name"], "Web User")

    def test_signup_stores_and_echoes_company(self):
        status, body = self._srv.post(
            "/signup", {"name": "Corp User", "email": "corp@example.com", "company": "ACME"}
        )
        self.assertEqual(status, 201)
        self.assertEqual(body["company"], "ACME")
        status, user = self._srv.get(f"/users/{body['id']}")
        self.assertEqual(status, 200)
        self.assertEqual(user["company"], "ACME")

    def test_signup_without_company_is_null(self):
        status, body = self._srv.post("/signup", {"name": "Solo", "email": "solo@example.com"})
        self.assertEqual(status, 201)
        self.assertIsNone(body["company"])
        self.assertIsNone(self._srv.get(f"/users/{body['id']}")[1]["company"])

    def test_signup_blank_company_is_null(self):
        status, body = self._srv.post("/signup", {"name": "Blank", "email": "blank@example.com", "company": "  "})
        self.assertEqual(status, 201)
        self.assertIsNone(body["company"])

    def test_static_form_has_company_field(self):
        status, html = self._srv.get("/")
        self.assertEqual(status, 200)
        self.assertIn(b'id="company"', html)
        self.assertLess(html.index(b'id="email"'), html.index(b'id="company"'))
        self.assertLess(html.index(b'id="company"'), html.index(b'id="submit"'))
        status, js = self._srv.get("/app.js")
        self.assertIn(b"company", js)

    def test_signup_rejects_non_json(self):
        status, body = self._srv.post("/signup", ["not", "an", "object"])
        self.assertEqual(status, 400)

    def test_unknown_route_404(self):
        self.assertEqual(self._srv.get("/nope")[0], 404)
        self.assertEqual(self._srv.post("/nope", {})[0], 404)

    def test_static_index_and_js(self):
        status, html = self._srv.get("/")
        self.assertEqual(status, 200)
        self.assertIn(b'id="signup-form"', html)
        status, js = self._srv.get("/app.js")
        self.assertEqual(status, 200)
        self.assertIn(b"Welcome aboard!", js)

    def test_static_blocks_traversal(self):
        self.assertEqual(self._srv.get("/../api/db.py")[0], 404)

    # ----- v2: GET /users/<id>/orders and company -------------------------

    def test_get_user_has_company_null_when_unset(self):
        status, body = self._srv.get("/users/1")
        self.assertEqual(status, 200)
        self.assertIn("company", body)
        self.assertIsNone(body["company"])

    def test_user_orders_newest_first_unpaginated(self):
        status, body = self._srv.get("/users/9/orders")
        self.assertEqual(status, 200)
        self.assertEqual(body["user_id"], 9)
        self.assertEqual(body["count"], len(body["orders"]))
        self.assertEqual(body["count"], 7)  # seed: user 9 has 7 orders incl. cancelled
        self.assertNotIn("page", body)
        self.assertTrue(all(o["user_id"] == 9 for o in body["orders"]))
        dates = [o["created_at"] for o in body["orders"]]
        self.assertEqual(dates, sorted(dates, reverse=True))
        self.assertEqual(set(body["orders"][0]), {"id", "user_id", "created_at", "status", "total_cents"})

    def test_user_orders_status_filter(self):
        status, body = self._srv.get("/users/9/orders?status=cancelled")
        self.assertEqual(status, 200)
        self.assertEqual(body["count"], 2)
        self.assertTrue(all(o["status"] == "cancelled" for o in body["orders"]))

    def test_user_orders_unknown_status_400_names_valid_values(self):
        status, body = self._srv.get("/users/9/orders?status=bogus")
        self.assertEqual(status, 400)
        for valid in ("pending", "shipped", "completed", "cancelled"):
            self.assertIn(valid, body["error"])

    def test_user_orders_missing_user_404(self):
        status, body = self._srv.get("/users/9999/orders")
        self.assertEqual(status, 404)
        self.assertIn("error", body)


if __name__ == "__main__":
    unittest.main()
