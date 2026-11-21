"""Run every test suite.  python webapp/run_tests.py [unit|api|e2e]"""
import sys
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent / "tests"
sys.path.insert(0, str(TESTS))

suites = {"unit": "test_units", "api": "test_api", "e2e": "test_e2e"}
chosen = [suites[a] for a in sys.argv[1:] if a in suites] or list(suites.values())
result = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromNames(chosen))
sys.exit(0 if result.wasSuccessful() else 1)
