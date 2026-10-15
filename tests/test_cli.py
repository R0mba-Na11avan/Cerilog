"""
Command-line tests: run `python -m cerilog` the way a user (or the VS Code
extension) would.

Run with: python -m pytest tests/test_cli.py
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
COUNTER = ROOT / "examples" / "counter.cel"


def run(*args, cwd=ROOT):
    return subprocess.run([sys.executable, "-m", "cerilog", *map(str, args)],
                          capture_output=True, text=True, cwd=cwd)


def test_stdout_defaults_to_systemverilog():
    proc = run(COUNTER)
    assert proc.returncode == 0
    assert "always_ff @(posedge clk)" in proc.stdout


@pytest.mark.parametrize("name, marker", [("out.sv", "always_ff"), ("out.v", "output reg  [7:0] count")])
def test_target_from_output_extension(tmp_path, name, marker):
    out = tmp_path / name
    proc = run(COUNTER, "-o", out)
    assert proc.returncode == 0, proc.stderr
    assert marker in out.read_text(encoding="utf-8")


def test_target_flag_overrides_extension(tmp_path):
    out = tmp_path / "out.sv"
    assert run(COUNTER, "-o", out, "--target", "v").returncode == 0
    assert "always @(posedge clk)" in out.read_text(encoding="utf-8")


def test_unknown_target_is_rejected():
    proc = run(COUNTER, "--target", "vhdl")
    assert proc.returncode != 0
    assert "unknown target" in proc.stderr


def test_no_source_maps():
    assert "// source:" in run(COUNTER).stdout
    assert "// source:" not in run(COUNTER, "--no-source-maps").stdout


def test_check_writes_nothing():
    proc = run(COUNTER, "--check")
    assert proc.returncode == 0
    assert proc.stdout == ""


def test_error_format_is_machine_readable(tmp_path):
    bad = tmp_path / "bad.cel"
    bad.write_text("module M(input logic a, output logic y) {\n    assign y = a\n}\n", encoding="utf-8")
    proc = run(bad, "--check")
    assert proc.returncode == 1
    first = proc.stderr.splitlines()[0]
    assert re.fullmatch(r".*bad\.cel:2:17: error: expected ';' before '\}'", first), first
    assert "^" in proc.stderr


def test_warnings_do_not_fail(tmp_path):
    src = tmp_path / "warn.cel"
    src.write_text("module M(input logic clk, input logic a, output logic y) {\n"
                   "    always(posedge clk) y = a;\n}\n", encoding="utf-8")
    proc = run(src)
    assert proc.returncode == 0
    assert "warn.cel:2:25: warning: blocking assignment" in proc.stderr


def test_verilog_only_error_has_hint(tmp_path):
    src = tmp_path / "fill.cel"
    src.write_text("module M(input logic[7:0] a, output logic[7:0] y) {\n"
                   "    assign y = a & '1;\n}\n", encoding="utf-8")
    assert run(src, "--check", "--target", "sv").returncode == 0
    proc = run(src, "--check", "--target", "v")
    assert proc.returncode == 1
    assert "Verilog-2005 (.v)" in proc.stderr and "hint:" in proc.stderr


def test_missing_file():
    proc = run("does_not_exist.cel")
    assert proc.returncode == 1
    assert "file not found" in proc.stderr


def test_tokens_and_ast_debug_output():
    assert "Token(MODULE, 'module'" in run(COUNTER, "--tokens").stdout
    assert "Module @" in run(COUNTER, "--ast").stdout
