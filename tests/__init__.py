"""Test package bootstrap.

This project uses a ``src/`` layout, so ``llm_prompt_compress`` is only
importable after an editable install (``pip install -e .``) or when
``src/`` is on ``sys.path``. pytest with the default ``rootdir`` import
mode handles this, but the standard-library test runner does not.

To keep the suite runnable with no third-party dependencies via::

    python3 -m unittest discover -s tests

we add the project's ``src/`` directory to ``sys.path`` here. This module
is imported by the ``unittest`` discovery loader before any test module in
this package, so the import path is ready in time. The insertion is a
no-op when the package is already importable (e.g. after an install).
"""

from __future__ import annotations

import os
import sys

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
