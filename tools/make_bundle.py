#!/usr/bin/env python3
"""Build fixtures/bundle.zip (archive-read exercise) with the stdlib zipfile module."""

from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "fixtures" / "bundle.zip"

README = """# bundle.zip

A tiny archive used by the omp-course archive-reading exercise.

Members:
- README.md        this file
- data/sample.csv  five order rows in the same shape as data/lab.sqlite
- config.json      example client configuration

The bundle is rebuilt by `python3 tools/make_bundle.py`; it is committed so the
exercise works without running anything first.
"""

SAMPLE_CSV = """id,user_id,created_at,status,total_cents
1,4,2025-10-02,completed,12900
2,2,2025-10-05,shipped,4550
3,9,2025-10-09,completed,21099
4,4,2025-10-14,cancelled,8000
5,11,2025-10-27,pending,15000
"""

CONFIG_JSON = """{
  "base_url": "http://127.0.0.1:8080",
  "page_size": 10,
  "default_month": "2026-03",
  "retry": {"attempts": 3, "backoff_seconds": 0.5}
}
"""


def main() -> int:
    OUT.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, text in (("README.md", README), ("data/sample.csv", SAMPLE_CSV), ("config.json", CONFIG_JSON)):
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))  # deterministic bytes
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, text)
    print(f"wrote {OUT}: {zipfile.ZipFile(OUT).namelist()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
