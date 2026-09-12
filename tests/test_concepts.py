"""Check the reviewed vocabulary and generated client contract."""

import re
import subprocess
import sys
from pathlib import Path

import pytest
from equity_schema.concepts import Concept

ROOT = Path(__file__).resolve().parents[1]


def test_reviewed_vocabulary_is_exactly_the_s1_forty():
    approved = re.findall(
        r"^\| \d+\. `([^`]+)`", (ROOT / "docs/research/s1/concept-map.md").read_text(), re.M
    )
    assert [member.value for member in Concept] == approved
    assert len(approved) == 40
    with pytest.raises(ValueError):
        Concept("invented_revenue")


def test_typescript_generation_is_current():
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/generate_concepts.py"), "--check"], check=True
    )
