"""
Cerilog AST Node Definitions (Stage 3)

These dataclasses represent the Abstract Syntax Tree produced by the parser.
Every node in the tree corresponds to a syntactic construct in Cerilog.

The code generator (Stage 4) walks this tree and emits SystemVerilog.

Node hierarchy:
    Node                    (base)
    ├── Module              module Foo(...) { }
    ├── Port                input logic[7:0] data
    ├── Always              always() { }  or  always(posedge clk) { }
    ├── Assign              assign out = a & b
    ├── If                  if (cond) { } else { }
    ├── Case                case (sel) { ... }
    ├── CaseItem            value: statement
    ├── For                 for (int i = 0; ...) { }
    ├── Block               { statement; statement; }
    ├── BinaryOp            a + b, a & b, etc.
    ├── UnaryOp             ~a, !a
    ├── Subscript           signal[3:0]
    ├── NumberLit           8'hFF, 4'b1010, 42
    ├── Identifier          signal_name
    └── Parameter           #(WIDTH=8)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Node:
    """Base class for all AST nodes. Stores source location for error reporting."""
    line: int = field(default=0, repr=False)
    col: int = field(default=0, repr=False)


@dataclass
class Identifier(Node):
    name: str = ""


@dataclass
class NumberLit(Node):
    """A numeric literal, e.g. 8'hFF or 42."""
    raw: str = ""       # original text as written


@dataclass
class BinaryOp(Node):
    op: str = ""        # "+", "-", "&", "|", "^", "==", etc.
    left: Optional[Node] = None
    right: Optional[Node] = None


@dataclass
class UnaryOp(Node):
    op: str = ""        # "~", "!", "-"
    operand: Optional[Node] = None


@dataclass
class Subscript(Node):
    """Signal bit select or part select: signal[3] or signal[7:0]"""
    target: Optional[Node] = None
    high: Optional[Node] = None     # signal[high:low] or signal[index]
    low: Optional[Node] = None      # None for single-bit select


@dataclass
class Port(Node):
    """A module port: input/output logic[N:0] name"""
    direction: str = ""             # "input" or "output"
    width_high: Optional[Node] = None   # None = single bit
    width_low: Optional[Node] = None
    name: str = ""


@dataclass
class Parameter(Node):
    """A module parameter: #(NAME = default_value)"""
    name: str = ""
    default: Optional[Node] = None


@dataclass
class Block(Node):
    """A sequence of statements inside { }"""
    statements: list[Node] = field(default_factory=list)


@dataclass
class Assign(Node):
    """Continuous assignment: assign lhs = rhs;"""
    lhs: Optional[Node] = None
    rhs: Optional[Node] = None


@dataclass
class NonBlockingAssign(Node):
    """Non-blocking assignment inside always_ff: lhs <= rhs;"""
    lhs: Optional[Node] = None
    rhs: Optional[Node] = None


@dataclass
class BlockingAssign(Node):
    """Blocking assignment: lhs = rhs;"""
    lhs: Optional[Node] = None
    rhs: Optional[Node] = None


@dataclass
class If(Node):
    condition: Optional[Node] = None
    then_block: Optional[Block] = None
    else_block: Optional[Node] = None   # Block or another If (else if)


@dataclass
class CaseItem(Node):
    value: Optional[Node] = None    # None = default
    body: Optional[Node] = None


@dataclass
class Case(Node):
    subject: Optional[Node] = None
    items: list[CaseItem] = field(default_factory=list)


@dataclass
class For(Node):
    init: Optional[Node] = None
    condition: Optional[Node] = None
    step: Optional[Node] = None
    body: Optional[Block] = None


@dataclass
class Always(Node):
    """
    Unified always block. Cerilog syntax: always(sensitivity_list) { }

    Emits differently based on sensitivity list:
        always()                ->  always_comb
        always(posedge clk)     ->  always_ff @(posedge clk)
        always(posedge clk,
               posedge rst)     ->  always_ff @(posedge clk, posedge rst)

    sensitivity is an empty list for combinational blocks.
    Each entry is a string like "posedge clk" or "negedge rst".
    """
    sensitivity: list[str] = field(default_factory=list)
    body: Optional[Block] = None

    @property
    def is_sequential(self) -> bool:
        """True if this block has a sensitivity list (flip-flop). False = combinational."""
        return len(self.sensitivity) > 0


@dataclass
class LocalSignal(Node):
    """A local signal declaration inside a module: logic[7:0] count;"""
    width_high: Optional[Node] = None
    width_low: Optional[Node] = None
    name: str = ""


@dataclass
class Module(Node):
    """Top-level module declaration."""
    name: str = ""
    parameters: list[Parameter] = field(default_factory=list)
    ports: list[Port] = field(default_factory=list)
    body: list[Node] = field(default_factory=list)
