"""
Cerilog AST node definitions.

The parser produces these nodes, the analysis pass annotates them, and each
target emitter walks them to print SystemVerilog or Verilog.

Every node stores the 1-indexed source line and column it came from. Emitters
use the line for `// source: file.cel:N` comments; diagnostics use both.

Tree shape:
    SourceFile
    └── Module
        ├── Parameter              #(WIDTH = 8)
        ├── Port                   input logic [7:0] data
        └── body items
            ├── LocalSignal        logic [7:0] mem [0:255] = ...;
            ├── Localparam         localparam DEPTH = 16;
            ├── Assign             assign out = a & b;
            ├── Always             always(posedge clk) { ... }
            ├── GenerateFor        for (int i = 0; ...) { module items }
            └── Instance           Adder #(.W(8)) u_add (.a(x));

    Statements (inside always):
        Block, If, Case/CaseItem, For, BlockingAssign, NonBlockingAssign

    Expressions:
        Identifier, NumberLit, BinaryOp, UnaryOp, Ternary, Paren,
        Subscript, Concat, Replicate, Call
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Node:
    """Base class for all AST nodes. Stores source location."""
    line: int = field(default=0, repr=False, compare=False)
    col: int = field(default=0, repr=False, compare=False)


# --------------------------------------------------------------------------- #
# Expressions
# --------------------------------------------------------------------------- #

@dataclass
class Identifier(Node):
    name: str = ""


@dataclass
class NumberLit(Node):
    """A numeric literal kept exactly as written: 42, 8'hFF, 4'b10_10, '0, '1."""
    raw: str = ""

    @property
    def is_fill(self) -> bool:
        """True for the SystemVerilog fill literals '0, '1, 'x, 'z."""
        return len(self.raw) == 2 and self.raw[0] == "'" and self.raw[1] in "01xXzZ"


@dataclass
class BinaryOp(Node):
    op: str = ""                    # "+", "&", "==", "<<", ...
    left: Optional[Node] = None
    right: Optional[Node] = None


@dataclass
class UnaryOp(Node):
    op: str = ""                    # "~", "!", "-", and reductions "&", "|", "^", "~&", ...
    operand: Optional[Node] = None


@dataclass
class Ternary(Node):
    condition: Optional[Node] = None
    if_true: Optional[Node] = None
    if_false: Optional[Node] = None


@dataclass
class Paren(Node):
    """Parentheses written in the source. Kept so output grouping matches the input."""
    inner: Optional[Node] = None


@dataclass
class Subscript(Node):
    """
    Bit select, part select, indexed part select or memory index.

        sig[i]          op=None   high=i     low=None
        sig[7:0]        op=":"    high=7     low=0
        sig[base +: 4]  op="+:"   high=base  low=4
        sig[base -: 4]  op="-:"   high=base  low=4
    """
    target: Optional[Node] = None
    high: Optional[Node] = None
    low: Optional[Node] = None
    op: Optional[str] = None


@dataclass
class Concat(Node):
    """{a, b, c}"""
    parts: list[Node] = field(default_factory=list)


@dataclass
class Replicate(Node):
    """{count{a, b}}"""
    count: Optional[Node] = None
    parts: list[Node] = field(default_factory=list)


@dataclass
class Call(Node):
    """System function call: $clog2(DEPTH), $signed(x). Passed through unchanged."""
    name: str = ""                  # includes the leading '$'
    args: list[Node] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Declarations
# --------------------------------------------------------------------------- #

@dataclass
class Port(Node):
    """
    A module port: input logic signed [7:0] data

    driven_in_always is set by the analysis pass. The Verilog emitter uses it
    to pick 'output reg' over 'output wire'.
    """
    direction: str = ""             # "input", "output" or "inout"
    signed: bool = False
    width_high: Optional[Node] = None   # None = single bit
    width_low: Optional[Node] = None
    name: str = ""
    driven_in_always: bool = False


@dataclass
class Parameter(Node):
    """A module parameter: #(NAME = default)"""
    name: str = ""
    default: Optional[Node] = None


@dataclass
class Localparam(Node):
    """localparam NAME = value;"""
    name: str = ""
    value: Optional[Node] = None


@dataclass
class UnpackedDim(Node):
    """One memory dimension: [0:255] (high=0, low=255) or [256] (high=256, low=None)."""
    high: Optional[Node] = None
    low: Optional[Node] = None


@dataclass
class LocalSignal(Node):
    """
    A signal declared inside a module: logic signed [7:0] mem [0:255] = init;

    driven_in_always is set by the analysis pass. The Verilog emitter uses it
    to pick 'reg' over 'wire'.
    """
    signed: bool = False
    width_high: Optional[Node] = None
    width_low: Optional[Node] = None
    name: str = ""
    unpacked: list[UnpackedDim] = field(default_factory=list)
    init: Optional[Node] = None
    driven_in_always: bool = False


# --------------------------------------------------------------------------- #
# Statements
# --------------------------------------------------------------------------- #

@dataclass
class Block(Node):
    """A sequence of statements inside { }."""
    statements: list[Node] = field(default_factory=list)


@dataclass
class BlockingAssign(Node):
    """lhs = rhs;"""
    lhs: Optional[Node] = None
    rhs: Optional[Node] = None


@dataclass
class NonBlockingAssign(Node):
    """lhs <= rhs;"""
    lhs: Optional[Node] = None
    rhs: Optional[Node] = None


@dataclass
class If(Node):
    condition: Optional[Node] = None
    then_branch: Optional[Node] = None   # any statement
    else_branch: Optional[Node] = None   # any statement (an If for else-if), or None


@dataclass
class CaseItem(Node):
    """
    One case arm. Stacked labels (C-style fallthrough) are merged into values:

        4'h0:
        4'h1: result = a;    ->  CaseItem(values=[4'h0, 4'h1], body=...)

    values == [] means the default arm.
    """
    values: list[Node] = field(default_factory=list)
    body: Optional[Node] = None

    @property
    def is_default(self) -> bool:
        return not self.values


@dataclass
class Case(Node):
    kind: str = "case"              # "case" or "casez"
    subject: Optional[Node] = None
    items: list[CaseItem] = field(default_factory=list)


@dataclass
class For(Node):
    """
    Procedural for loop inside an always block.

    declares_var is True when the loop declares its own counter: for (int i = 0; ...).
    step is normalised to an assignment: i++ becomes i = i + 1.
    """
    var_name: str = ""
    declares_var: bool = False
    init: Optional[Node] = None
    condition: Optional[Node] = None
    step: Optional[BlockingAssign] = None
    body: Optional[Node] = None


# --------------------------------------------------------------------------- #
# Module items
# --------------------------------------------------------------------------- #

@dataclass
class Assign(Node):
    """Continuous assignment: assign lhs = rhs;"""
    lhs: Optional[Node] = None
    rhs: Optional[Node] = None


@dataclass
class Sensitivity(Node):
    """One entry of an always sensitivity list: posedge clk"""
    edge: str = ""                  # "posedge" or "negedge"
    signal: Optional[Node] = None


@dataclass
class Always(Node):
    """
    Unified always block.

        always() { }                  ->  always_comb         /  always @(*)
        always(posedge clk) { }       ->  always_ff @(...)    /  always @(...)

    sensitivity is empty for combinational blocks.
    """
    sensitivity: list[Sensitivity] = field(default_factory=list)
    body: Optional[Block] = None

    @property
    def is_sequential(self) -> bool:
        """True if this block has a sensitivity list (flip-flops)."""
        return len(self.sensitivity) > 0


@dataclass
class GenerateFor(Node):
    """
    Module-level for loop: stamps out copies of the module items in its body.
    The loop variable becomes a genvar in both targets.
    """
    var_name: str = ""
    init: Optional[Node] = None
    condition: Optional[Node] = None
    step: Optional[BlockingAssign] = None
    body: list[Node] = field(default_factory=list)


@dataclass
class Connection(Node):
    """Instance port or parameter connection: .name(expr), or positional when name is None."""
    name: Optional[str] = None
    expr: Optional[Node] = None     # None for an explicitly unconnected port: .b()


@dataclass
class Instance(Node):
    """Module instantiation: Adder #(.WIDTH(8)) u_add (.a(x), .sum(s));"""
    module_name: str = ""
    name: str = ""
    params: list[Connection] = field(default_factory=list)
    connections: list[Connection] = field(default_factory=list)


@dataclass
class Module(Node):
    name: str = ""
    parameters: list[Parameter] = field(default_factory=list)
    ports: list[Port] = field(default_factory=list)
    body: list[Node] = field(default_factory=list)


@dataclass
class SourceFile(Node):
    """Root node: every module in one .cel file."""
    modules: list[Module] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Debug output
# --------------------------------------------------------------------------- #

def dump(node, indent: int = 0) -> str:
    """Readable multi-line dump of an AST, used by `cerilog --ast`."""
    pad = "  " * indent
    if isinstance(node, list):
        if not node:
            return "[]"
        inner = "\n".join(f"{pad}  - {dump(item, indent + 2).lstrip()}" for item in node)
        return "\n" + inner
    if not isinstance(node, Node):
        return repr(node)

    fields = [
        (name, value)
        for name, value in vars(node).items()
        if name not in ("line", "col") and value not in (None, [], False, "")
    ]
    header = f"{pad}{type(node).__name__} @{node.line}:{node.col}"
    if not fields:
        return header
    lines = [header]
    for name, value in fields:
        lines.append(f"{pad}  {name}: {dump(value, indent + 2).lstrip(' ')}")
    return "\n".join(lines)
