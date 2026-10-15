"""
The full pipeline in one call: parse -> analyse -> emit.

    result = compile_source(text, target=Target.VERILOG, filename="counter.cel")
    if result.ok:
        print(result.code)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from cerilog.analysis.checks import analyze
from cerilog.codegen.emitter import Emitter, Target
from cerilog.errors import CerilogError, Diagnostic
from cerilog.parser.parser import Parser


@dataclass
class CompileResult:
    code: Optional[str]
    diagnostics: list[Diagnostic] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.code is not None


def compile_source(source: str, *, target: Target = Target.SYSTEMVERILOG,
                   filename: Optional[str] = None, source_maps: bool = True) -> CompileResult:
    """Compile Cerilog source. Never raises for problems in the source; check result.ok."""
    try:
        tree = Parser().parse(source)
    except CerilogError as e:
        return CompileResult(None, [e.diagnostic])

    diagnostics = analyze(tree)
    if any(d.is_error for d in diagnostics):
        return CompileResult(None, diagnostics)

    try:
        code = Emitter(target=target, source_maps=source_maps, filename=filename).emit(tree)
    except CerilogError as e:
        return CompileResult(None, diagnostics + [e.diagnostic])
    return CompileResult(code, diagnostics)
