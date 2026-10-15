"""
Lint every example's output with Verilator, for both targets.

Skipped when `verilator` isn't on PATH. Verilator is the ground truth for
"is this legal SystemVerilog / Verilog": if it rejects the output, the
emitter is wrong.

Run with: python -m pytest tests/lint/
"""

import shutil
import subprocess
from pathlib import Path

import pytest

from cerilog.codegen.emitter import Target
from cerilog.compiler import compile_source

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = sorted((ROOT / "examples").glob("*.cel"))
VERILATOR = shutil.which("verilator")

pytestmark = pytest.mark.skipif(VERILATOR is None, reason="verilator not installed")

LANGUAGE = {Target.SYSTEMVERILOG: "1800-2017", Target.VERILOG: "1364-2005"}


@pytest.mark.parametrize("target", list(Target), ids=lambda t: t.extension)
@pytest.mark.parametrize("example", EXAMPLES, ids=lambda p: p.stem)
def test_verilator_accepts_output(example: Path, target: Target, tmp_path: Path):
    result = compile_source(example.read_text(encoding="utf-8"), target=target, filename=example.name)
    assert result.ok
    out = tmp_path / f"{example.stem}{target.extension}"
    out.write_text(result.code, encoding="utf-8")

    proc = subprocess.run(
        [VERILATOR, "--lint-only", "-Wno-fatal", "-Wno-MULTITOP", "--default-language", LANGUAGE[target], str(out)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
