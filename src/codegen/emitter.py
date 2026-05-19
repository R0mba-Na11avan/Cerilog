"""
Cerilog Code Generator (Stage 4)

Walks the AST and emits either SystemVerilog (.sv) or plain Verilog (.v).
Target is selected at construction time via the Target enum.

Verilog vs SystemVerilog differences handled here:
    ┌─────────────────────┬──────────────────────────┬─────────────────────────┐
    │ Cerilog             │ SystemVerilog             │ Verilog                 │
    ├─────────────────────┼──────────────────────────┼─────────────────────────┤
    │ logic               │ logic                     │ wire / reg (inferred)   │
    │ always()            │ always_comb               │ always @(*)             │
    │ always(posedge clk) │ always_ff @(posedge clk)  │ always @(posedge clk)   │
    │ int i               │ int i                     │ integer i               │
    │ #(WIDTH = 8)        │ #(WIDTH = 8)              │ #(parameter WIDTH = 8)  │
    └─────────────────────┴──────────────────────────┴─────────────────────────┘

wire/reg inference rule (Verilog target only):
    - input port            -> wire (inputs are never reg)
    - output/local signal   -> reg  if driven inside an always block
                            -> wire if driven by assign or module output

Design principles:
    - Emit readable output, not minified
    - Each emitted line gets a source comment (e.g. // source: counter.cel:14)
      so Quartus error messages can be traced back to your .cel file
    - Indentation is handled by the emitter, not the AST

TODO (Stage 4):
    - Implement Emitter.emit() and all emit_* methods
    - Add semantic analysis pass to set driven_in_always on Port/LocalSignal nodes
    - Test Verilog output against Quartus, SV output against Verilator
"""

from enum import Enum
from src.ast import nodes


INDENT = "    "   # 4 spaces per level


class Target(Enum):
    SYSTEMVERILOG = "systemverilog"
    VERILOG = "verilog"


class EmitError(Exception):
    """Raised when the emitter encounters an AST it can't handle."""
    pass


class Emitter:
    """
    Walks a Cerilog AST and produces a SystemVerilog or Verilog string.

    Usage:
        # SystemVerilog (default)
        sv_code = Emitter().emit(module_node)

        # Plain Verilog (for Quartus .v files, DE-10 Lite etc.)
        v_code = Emitter(target=Target.VERILOG).emit(module_node)
    """

    def __init__(self, target: Target = Target.SYSTEMVERILOG, source_maps: bool = True):
        self.target = target
        self.source_maps = source_maps  # include // source: file:line comments
        self._indent = 0
        self._lines: list[str] = []

    @property
    def is_verilog(self) -> bool:
        return self.target == Target.VERILOG

    @property
    def is_systemverilog(self) -> bool:
        return self.target == Target.SYSTEMVERILOG

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def emit(self, module: nodes.Module) -> str:
        """
        Entry point. Returns the full source as a string.
        Call with a Module node from the parser.
        """
        # TODO: implement in Stage 4
        raise NotImplementedError("Emitter not yet implemented — coming in Stage 4")

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _write(self, text: str, node: nodes.Node = None):
        """Write one line at the current indentation level."""
        indent = INDENT * self._indent
        source_comment = ""
        if self.source_maps and node and node.line:
            source_comment = f"  // source: line {node.line}"
        self._lines.append(f"{indent}{text}{source_comment}")

    def _indent_in(self):
        self._indent += 1

    def _indent_out(self):
        self._indent = max(0, self._indent - 1)

    def _signal_type(self, driven_in_always: bool, direction: str = "") -> str:
        """
        Returns the correct type keyword for a signal.

        SystemVerilog: always 'logic'
        Verilog:       'wire' or 'reg' depending on how the signal is driven.
                       Input ports are always wire in Verilog.
        """
        if self.is_systemverilog:
            return "logic"
        # Verilog target
        if direction == "input":
            return "wire"
        return "reg" if driven_in_always else "wire"

    # ------------------------------------------------------------------ #
    # Node emitters (implement in Stage 4)
    # ------------------------------------------------------------------ #

    def emit_module(self, node: nodes.Module): ...

    def emit_port(self, node: nodes.Port) -> str:
        """
        Emit a port declaration.

        SV:      input logic[7:0] count
        Verilog: input wire[7:0] count   (input)
                 output reg[7:0] count   (output driven in always)
                 output wire[7:0] count  (output driven by assign)
        """
        ...

    def emit_always(self, node: nodes.Always):
        """
        Smart emit based on target and sensitivity list.

        SV,   no args:   always_comb
        SV,   args:      always_ff @(posedge clk, ...)
        Verilog, no args: always @(*)
        Verilog, args:   always @(posedge clk, ...)
        """
        ...

    def emit_parameter(self, node: nodes.Parameter) -> str:
        """
        SV:      WIDTH = 8
        Verilog: parameter WIDTH = 8
        """
        ...

    def emit_for(self, node: nodes.For):
        """
        Loop variable type:
        SV:      int i
        Verilog: integer i
        """
        ...

    def emit_assign(self, node: nodes.Assign): ...
    def emit_if(self, node: nodes.If): ...
    def emit_case(self, node: nodes.Case): ...
    def emit_block(self, node: nodes.Block): ...
    def emit_binary_op(self, node: nodes.BinaryOp) -> str: ...
    def emit_unary_op(self, node: nodes.UnaryOp) -> str: ...
    def emit_subscript(self, node: nodes.Subscript) -> str: ...
    def emit_identifier(self, node: nodes.Identifier) -> str: ...
    def emit_number_lit(self, node: nodes.NumberLit) -> str: ...
