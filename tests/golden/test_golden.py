"""
Golden-file tests: every examples/*.cel is compiled to both targets and
compared with the checked-in output in tests/golden/expected/.

Run with: python -m pytest tests/golden/

After an intended change to the output, regenerate the expected files with
    CERILOG_UPDATE_GOLDEN=1 python -m pytest tests/golden/
and review the diff before committing.
"""

import os
from pathlib import Path

import pytest

from cerilog.codegen.emitter import Target
from cerilog.compiler import compile_source

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = sorted((ROOT / "examples").glob("*.cel"))
EXPECTED = Path(__file__).parent / "expected"
UPDATE = os.environ.get("CERILOG_UPDATE_GOLDEN") == "1"


@pytest.mark.parametrize("target", list(Target), ids=lambda t: t.extension)
@pytest.mark.parametrize("example", EXAMPLES, ids=lambda p: p.stem)
def test_example_matches_golden(example: Path, target: Target):
    source = example.read_text(encoding="utf-8")
    result = compile_source(source, target=target, filename=example.name)
    assert result.ok, [d.message for d in result.diagnostics]
    assert not result.diagnostics, [d.message for d in result.diagnostics]

    expected_path = EXPECTED / f"{example.stem}{target.extension}"
    if UPDATE:
        EXPECTED.mkdir(exist_ok=True)
        expected_path.write_text(result.code, encoding="utf-8", newline="\n")
    assert expected_path.exists(), f"missing {expected_path.name}; run with CERILOG_UPDATE_GOLDEN=1"
    assert result.code == expected_path.read_text(encoding="utf-8")
