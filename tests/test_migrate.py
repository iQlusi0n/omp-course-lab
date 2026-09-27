import io
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from tests.support import ROOT, TempDB

from generated.schema_info import SCHEMA_VERSION

sys.path.insert(0, str(ROOT / "tools"))
import migrate  # noqa: E402

V1_SCHEMA = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL
);
CREATE TABLE schema_version (version INTEGER NOT NULL);
INSERT INTO schema_version (version) VALUES (1);
INSERT INTO users (name, email, created_at) VALUES ('Old User', 'old@example.com', '2025-01-01');
"""


def _columns(path: str) -> list[str]:
    with sqlite3.connect(path) as conn:
        return [r[1] for r in conn.execute("PRAGMA table_info(users)")]


def _version(path: str) -> int:
    with sqlite3.connect(path) as conn:
        return conn.execute("SELECT version FROM schema_version").fetchone()[0]


class MigrateTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory(prefix="lab-migrate-")
        self.addCleanup(self.dir.cleanup)
        self.v1 = Path(self.dir.name) / "v1.sqlite"
        with sqlite3.connect(self.v1) as conn:
            conn.executescript(V1_SCHEMA)

    def test_v1_database_gains_company_and_version_2(self):
        self.assertNotIn("company", _columns(self.v1))
        migrate.migrate(self.v1)
        self.assertIn("company", _columns(self.v1))
        self.assertEqual(_version(self.v1), 2)
        with sqlite3.connect(self.v1) as conn:
            row = conn.execute("SELECT company FROM users WHERE email = 'old@example.com'").fetchone()
        self.assertIsNone(row[0])

    def test_second_run_is_a_noop(self):
        migrate.migrate(self.v1)
        out = io.StringIO()
        with redirect_stdout(out):
            migrate.migrate(self.v1)
        self.assertEqual(out.getvalue().strip(), "already at version 2")
        self.assertEqual(_columns(self.v1).count("company"), 1)

    def test_cli_entry_point(self):
        result = subprocess.run(
            [sys.executable, "tools/migrate.py", "--db", str(self.v1)],
            cwd=ROOT, capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("to 2", result.stdout)

    def test_seeded_database_is_already_version_2(self):
        with TempDB() as tdb:
            self.assertEqual(_version(tdb.path), 2)
            self.assertIn("company", _columns(tdb.path))
        self.assertEqual(SCHEMA_VERSION, 2)


if __name__ == "__main__":
    unittest.main()
