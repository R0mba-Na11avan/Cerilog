"""
Cerilog Code Generator (Stage 4)

Walks the AST and emits valid SystemVerilog source code.
Each emit method corresponds to one AST node type.

Design principles:
    - Emit readable SV, not minified output
    - Each emitted line gets a source comment (e.g. // source: counter.cel:14)
      so Quartus error messages can be traced back to your .cel file
    - Indentation is handled by the emitter, not the AST

TODO (Stage 4):
    - Implement Emitter.emit() and all emit_* methods
    - Add source map comments
    - Test against Verilator for correctness
"""

from src.ast import nodes


INDENT = "    "   # 4 spaces per level


class EmitError(Exception):
    """Raised when the emitter encounters an AST it can't handle."""
    pass


class Emitter:
    """
    Walks a Cerilog AST and produces a SystemVerilog string.

    Usage:
        sv_code = Emitter().emit(module_node)
    """

    def __init__(self, source_maps: bool = True):
        self.source_maps = source_maps  # include // source: file:line comments
        self._indent = 0
        self._lines: list[str] = []

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def emit(self, module: nodes.Module) -> str:
        """
        Entry point. Returns the full SystemVerilog source as a string.
        """
        # TODO: implement in Stage 4
        raise NotImplementedError("Emitter not yet implemented — coming in Stage 4")

    # ------------------------------------------------------------------ #
    # Helpers (implement these in Stage 4)
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

    # ------------------------------------------------------------------ #
    # Node emitters (one per AST node type — implement in Stage 4)
    # ------------------------------------------------------------------ #

    def emit_module(self, node: nodes.Module): ...
    def emit_port(self, node: nodes.Port) -> str: ...
    def emit_always(self, node: nodes.Always):
        """
        Smart emit: inspects node.is_sequential to decide which SV construct to use.

        node.is_sequential == False  ->  always_comb
        node.is_sequential == True   ->  always_ff @(posedge clk, ...)
        """
        ...
    def emit_assign(self, node: nodes.Assign): ...
    def emit_if(self, node: nodes.If): ...
    def emit_case(self, node: nodes.Case): ...
    def emit_for(self, node: nodes.For): ...
    def emit_block(self, node: nodes.Block): ...
    def emit_binary_op(self, node: nodes.BinaryOp) -> str: ...
    def emit_unary_op(self, node: nodes.UnaryOp) -> str: ...
    def emit_subscript(self, node: nodes.Subscript) -> str: ...
    def emit_identifier(self, node: nodes.Identifier) -> str: ...
    def emit_number_lit(self, node: nodes.NumberLit) -> str: ...
