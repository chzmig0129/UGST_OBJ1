"""
conftest.py — pytest configuration for the UGST_OBJ1 test suite.

Adds the project root to sys.path so that ``from utils.geometry import ...``
works regardless of where pytest is invoked from.
"""

import sys
import os

# Insert the project root (one level above this file's directory) at the
# front of sys.path so that top-level packages like ``utils`` are importable.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
