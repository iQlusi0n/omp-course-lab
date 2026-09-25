"""Logger for the CLI.

``logger`` writes bare messages to stdout at DEBUG level, so it is a drop-in
replacement for ``print(msg)`` (Module 8 codemod fixture): swapping
``print(x)`` for ``logger.debug(x)`` keeps the CLI tests green.
"""

import logging
import sys

logger = logging.getLogger("lab.cli")
if not logger.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(_handler)
logger.setLevel(logging.DEBUG)
logger.propagate = False
