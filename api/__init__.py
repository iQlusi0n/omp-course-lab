"""omp-course-lab API package.

``get_user`` is re-exported here so callers can ``from api import get_user``
(this re-export is the LSP-rename fixture for Module 8).
"""

from .db import LabError, get_user  # noqa: F401

__all__ = ["LabError", "get_user"]
