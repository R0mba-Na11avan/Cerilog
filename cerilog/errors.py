"""
Diagnostics shared by every stage.

Each diagnostic prints as

    counter.cel:12:23: error: expected ';' after assignment
        count <= count + 1
                          ^
        hint: ...

The first line is stable and machine-parseable (the VS Code extension reads it).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Diagnostic:
    severity: str                   # "error" or "warning"
    message: str
    line: int = 0
    col: int = 0
    hint: Optional[str] = None

    @property
    def is_error(self) -> bool:
        return self.severity == "error"


class CerilogError(Exception):
    """Base class for errors that stop compilation. Carries one diagnostic."""

    def __init__(self, message: str, line: int = 0, col: int = 0, hint: Optional[str] = None):
        super().__init__(message)
        self.diagnostic = Diagnostic("error", message, line, col, hint)


class CompileFailed(Exception):
    """Raised when analysis reports one or more errors. Holds every diagnostic."""

    def __init__(self, diagnostics: list[Diagnostic]):
        super().__init__(f"{sum(d.is_error for d in diagnostics)} error(s)")
        self.diagnostics = diagnostics


def format_diagnostic(diag: Diagnostic, source: str = "", filename: str = "<input>") -> str:
    location = f"{filename}:{diag.line}:{diag.col}" if diag.line else filename
    out = [f"{location}: {diag.severity}: {diag.message}"]

    lines = source.splitlines()
    if diag.line and 0 < diag.line <= len(lines):
        raw = lines[diag.line - 1]
        out.append(f"    {raw.expandtabs(4)}")
        if diag.col:
            prefix = raw[: diag.col - 1].expandtabs(4)
            out.append("    " + " " * len(prefix) + "^")
    if diag.hint:
        out.append(f"    hint: {diag.hint}")
    return "\n".join(out)
