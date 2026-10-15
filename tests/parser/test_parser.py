"""
Parser tests.

Run with: python -m pytest tests/parser/
"""

import pytest

from cerilog.ast.nodes import (
    Always, Assign, BinaryOp, Block, BlockingAssign, Case, Concat, For, GenerateFor,
    Identifier, If, Instance, LocalSignal, Localparam, Module, NonBlockingAssign, NumberLit,
    Paren, SourceFile, Subscript,
)
from cerilog.parser.parser import LexError, ParseError, Parser


def parse_module(src) -> Module:
    tree = Parser().parse(src)
    assert isinstance(tree, SourceFile)
    return tree.modules[0]


def parse_body(body: str) -> list:
    return parse_module(f"module M(input logic clk, input logic a, output logic y) {{ {body} }}").body


class TestModuleDeclaration:
    def test_empty_module(self):
        module = parse_module("module Foo() { }")
        assert isinstance(module, Module)
        assert module.name == "Foo"
        assert module.ports == []
        assert module.body == []

    def test_module_with_ports(self):
        module = parse_module("module Bar(input logic clk, output logic out) { }")
        assert len(module.ports) == 2
        assert module.ports[0].direction == "input"
        assert module.ports[0].name == "clk"
        assert module.ports[1].direction == "output"
        assert module.ports[1].name == "out"

    def test_port_width_signed_and_optional_logic(self):
        module = parse_module("module M(input [7:0] a, output logic signed [3:0] b, inout c,) { }")
        a, b, c = module.ports
        assert (a.width_high, a.width_low) == (NumberLit(raw="7"), NumberLit(raw="0"))
        assert b.signed and b.direction == "output"
        assert c.direction == "inout" and c.width_high is None

    def test_parameters(self):
        module = parse_module("module M #(WIDTH = 8, parameter DEPTH = 16) (input logic[WIDTH-1:0] d) { }")
        assert [p.name for p in module.parameters] == ["WIDTH", "DEPTH"]
        assert module.ports[0].width_high == BinaryOp(op="-", left=Identifier(name="WIDTH"),
                                                      right=NumberLit(raw="1"))

    def test_multiple_modules(self):
        tree = Parser().parse("module A() { } module B() { }")
        assert [m.name for m in tree.modules] == ["A", "B"]

    def test_positions(self):
        module = parse_module("\n  module Foo() { }")
        assert (module.line, module.col) == (2, 3)


class TestDeclarations:
    def test_signals_split_per_name(self):
        x, y = parse_body("logic signed [7:0] x = 0, y;")
        assert isinstance(x, LocalSignal) and x.name == "x" and x.signed and x.init == NumberLit(raw="0")
        assert y.name == "y" and y.init is None and y.width_high == NumberLit(raw="7")

    def test_memory(self):
        (mem,) = parse_body("logic [7:0] mem [0:255];")
        assert len(mem.unpacked) == 1
        assert mem.unpacked[0].low == NumberLit(raw="255")

    def test_localparam(self):
        (lp,) = parse_body("localparam AW = $clog2(16);")
        assert isinstance(lp, Localparam) and lp.name == "AW"


class TestAlways:
    def test_basic_always_ff(self):
        src = """
        module Foo(input logic clk) {
            always_ff(posedge clk) { }
        }
        """
        module = parse_module(src)
        assert len(module.body) == 1
        assert isinstance(module.body[0], Always)
        sens = module.body[0].sensitivity[0]
        assert (sens.edge, sens.signal) == ("posedge", Identifier(name="clk"))

    @pytest.mark.parametrize("header", ["always()", "always(*)", "always_comb()"])
    def test_combinational_spellings(self, header):
        (always,) = parse_body(f"{header} {{ y = a; }}")
        assert not always.is_sequential

    def test_or_separated_sensitivity(self):
        (always,) = parse_body("always(posedge clk or negedge a) y <= a;")
        assert [s.edge for s in always.sensitivity] == ["posedge", "negedge"]

    def test_braceless_body_is_wrapped_in_block(self):
        (always,) = parse_body("always(posedge clk) y <= a;")
        assert isinstance(always.body, Block)
        assert isinstance(always.body.statements[0], NonBlockingAssign)

    def test_always_ff_without_sensitivity_is_error(self):
        with pytest.raises(ParseError, match="always_ff needs a sensitivity list"):
            parse_body("always_ff() { }")

    def test_always_comb_with_sensitivity_is_error(self):
        with pytest.raises(ParseError, match="always_comb takes no sensitivity list"):
            parse_body("always_comb(posedge clk) { }")

    def test_level_sensitive_list_is_error(self):
        with pytest.raises(ParseError, match="posedge or negedge"):
            parse_body("always(a) { }")


class TestStatements:
    def test_else_if_chain(self):
        (always,) = parse_body("always() if (a) y = 1; else if (clk) y = 0; else y = a;")
        stmt = always.body.statements[0]
        assert isinstance(stmt, If)
        assert isinstance(stmt.else_branch, If)
        assert isinstance(stmt.else_branch.else_branch, BlockingAssign)

    def test_dangling_else_binds_to_nearest_if(self):
        (always,) = parse_body("always() if (a) if (clk) y = 1; else y = 0;")
        outer = always.body.statements[0]
        assert outer.else_branch is None
        assert outer.then_branch.else_branch is not None

    def test_nonblocking_vs_comparison(self):
        (always,) = parse_body("always(posedge clk) y <= a <= clk;")
        stmt = always.body.statements[0]
        assert isinstance(stmt, NonBlockingAssign)
        assert stmt.rhs.op == "<="

    def test_case_fallthrough_merges_labels(self):
        (always,) = parse_body("""
            always() case (a) {
                0:
                1, 2: y = 1;
                3: y = 0;
                default: y = a;
            }
        """)
        case = always.body.statements[0]
        assert isinstance(case, Case) and case.kind == "case"
        assert [len(i.values) for i in case.items] == [3, 1, 0]
        assert case.items[2].is_default

    def test_casez(self):
        (always,) = parse_body("always() casez (a) { 1'b?: y = 1; }")
        assert always.body.statements[0].kind == "casez"

    def test_concat_assignment_in_block(self):
        (always,) = parse_body("always() { {y, y} = a; }")
        assert isinstance(always.body.statements[0].lhs, Concat)

    @pytest.mark.parametrize("step, op, amount", [("i++", "+", "1"), ("i--", "-", "1"), ("i += 2", "+", "2")])
    def test_for_step_is_normalised(self, step, op, amount):
        (always,) = parse_body(f"always() for (int i = 0; i < 4; {step}) y = a;")
        loop = always.body.statements[0]
        assert isinstance(loop, For) and loop.declares_var and loop.var_name == "i"
        assert loop.step.lhs == Identifier(name="i")
        assert loop.step.rhs == BinaryOp(op=op, left=Identifier(name="i"), right=NumberLit(raw=amount))

    def test_for_step_must_update_loop_variable(self):
        with pytest.raises(ParseError, match="loop variable is 'i'"):
            parse_body("always() for (int i = 0; i < 4; j++) y = a;")


class TestModuleItems:
    def test_generate_for(self):
        (loop,) = parse_body("for (int i = 0; i < 8; i++) { assign y = a; }")
        assert isinstance(loop, GenerateFor) and loop.var_name == "i"
        assert isinstance(loop.body[0], Assign)

    def test_instance(self):
        (inst,) = parse_body("Adder #(.WIDTH(8)) u_add (.a(a), .b(), .sum(y));")
        assert isinstance(inst, Instance)
        assert (inst.module_name, inst.name) == ("Adder", "u_add")
        assert [(c.name, c.expr) for c in inst.params] == [("WIDTH", NumberLit(raw="8"))]
        assert [c.name for c in inst.connections] == ["a", "b", "sum"]
        assert inst.connections[1].expr is None

    def test_positional_instance(self):
        (inst,) = parse_body("Foo u (a, y);")
        assert [c.name for c in inst.connections] == [None, None]


class TestExpressions:
    def expr(self, text):
        (assign,) = parse_body(f"assign y = {text};")
        return assign.rhs

    def test_precedence(self):
        e = self.expr("a + clk * 2")
        assert e.op == "+" and e.right.op == "*"

    def test_parentheses_are_kept(self):
        e = self.expr("(a + clk) * 2")
        assert isinstance(e.left, Paren)

    def test_ternary_and_reduction(self):
        e = self.expr("&a ? ~a : a")
        assert e.condition.op == "&" and e.if_true.op == "~"

    def test_selects(self):
        assert self.expr("a[3]") == Subscript(target=Identifier(name="a"), high=NumberLit(raw="3"))
        assert self.expr("a[7:0]").op == ":"
        assert self.expr("a[clk +: 4]").op == "+:"

    def test_replication(self):
        e = self.expr("{4{a}}")
        assert e.count == NumberLit(raw="4")


class TestErrors:
    def test_missing_closing_brace(self):
        with pytest.raises(ParseError):
            Parser().parse("module Foo() {")

    def test_missing_module_name(self):
        with pytest.raises(ParseError):
            Parser().parse("module () { }")

    def test_missing_semicolon_points_at_end_of_statement(self):
        src = "module M(input logic a, output logic y) {\n    assign y = a\n    assign y = a;\n}"
        with pytest.raises(ParseError) as info:
            Parser().parse(src)
        d = info.value.diagnostic
        assert "expected ';'" in d.message
        assert (d.line, d.col) == (2, 17)

    def test_bad_character(self):
        with pytest.raises(LexError):
            Parser().parse("module M() { @ }")
