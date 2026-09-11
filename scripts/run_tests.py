"""Allow intentionally empty S0 suites without hiding failures or deselection."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    args = sys.argv[1:] or ["tests"]
    status = pytest.main(args.copy())
    if status != pytest.ExitCode.NO_TESTS_COLLECTED:
        return int(status)
    # A narrowly scoped bootstrap exception, removed when these suites gain tests.
    allowed = {"tests", "tests/core", "tests/golden"}
    if len(args) == 1 and args[0] in allowed:
        suite = ROOT / args[0]
        test_files = list(suite.rglob("test_*.py")) + list(suite.rglob("*_test.py"))
        if (suite / ".allow-empty-s0").is_file() and not test_files:
            print(f"S0: {args[0]} is intentionally empty; no behavioral tests have run.")
            return 0
    return int(status)


if __name__ == "__main__":
    raise SystemExit(main())
