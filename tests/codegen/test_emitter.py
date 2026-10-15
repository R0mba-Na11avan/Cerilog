"""
Code generator tests.

Run with: python -m pytest tests/codegen/

Most tests build AST nodes by hand so the emitter is tested on its own,
without the parser. Whitespace is normalised where only content matters.
"""

import pytest

from cerilog.ast.nodes import (
    Always, Assign, Block, BlockingAssign, Case, CaseItem, For, GenerateFor, Identifier,
    If, Instance, Connection, LocalSignal, Module, NonBlockingAssign, NumberLit, Port,
    Sensitivity, BinaryOp, UnaryOp,
)
from cerilog.codegen.emitter import EmitError, Emitter, Target


def flat(text: str) -> str:
    """Collapse all whitespace runs to single spaces."""
    return " ".join(text.split())


def emit(module, target=Target.SYSTEMVERILOG) -> str:
    return Emitter(target=target, source_maps=False).emit(module)


def ident(name):
    return Identifier(name=name)


def num(raw):
    return NumberLit(raw=raw)


CLK = Sensitivity(edge="posedge", signal=ident("clk"))


class TestModuleEmit:
    def test_empty_module(self):
        module = Module(name="Foo", ports=[], body=[])
        sv = emit(module)
        assert "module Foo" in sv
        assert "endmodule" in sv

    def test_module_with_ports(self):
        module = Module(
            name="Counter",
            ports=[
                Port(direction="input", name="clk"),
                Port(direction="output", width_high=num("7"), width_low=num("0"), name="count"),
            ],
            body=[],
        )
        sv = flat(emit(module))
        assert "input logic clk" in sv
        assert "output logic [7:0] count" in sv

    def test_parameters(self):
        module = Module(name="M", parameters=[], ports=[], body=[])
        from cerilog.ast.nodes import Parameter
        module.parameters = [Parameter(name="WIDTH", default=num("8"))]
        assert "module M #( parameter WIDTH = 8 ) ();" in flat(emit(module))


class TestAlwaysEmit:
    def test_sequential_sv(self):
        node = Always(sensitivity=[CLK], body=Block(statements=[]))
        module = Module(name="Foo", ports=[], body=[node])
        sv = emit(module)
        assert "always_ff @(posedge clk)" in sv
        assert "begin" in sv
        assert "end" in sv

    def test_combinational_sv(self):
        sv = emit(Module(name="Foo", body=[Always(body=Block())]))
        assert "always_comb begin" in sv

    def test_verilog_forms(self):
        module = Module(name="Foo", body=[
            Always(body=Block()),
            Always(sensitivity=[CLK, Sensitivity(edge="negedge", signal=ident("rst"))], body=Block()),
        ])
        v = emit(module, Target.VERILOG)
        assert "always @(*) begin" in v
        assert "always @(posedge clk, negedge rst) begin" in v
        assert "always_comb" not in v and "always_ff" not in v

    def test_sv_never_emits_plain_always(self):
        sv = emit(Module(name="Foo", body=[Always(body=Block())]))
        assert "always @" not in sv


class TestWireRegInference:
    def make(self, driven):
        out = Port(direction="output", name="q", driven_in_always=driven)
        sig = LocalSignal(name="s", driven_in_always=driven)
        return Module(name="M", ports=[Port(direction="input", name="d"), out], body=[sig])

    def test_verilog_reg_when_driven_in_always(self):
        v = flat(emit(self.make(True), Target.VERILOG))
        assert "input wire d" in v and "output reg q" in v and "reg s;" in v

    def test_verilog_wire_otherwise(self):
        v = flat(emit(self.make(False), Target.VERILOG))
        assert "output wire q" in v and "wire s;" in v

    def test_sv_always_logic(self):
        sv = emit(self.make(True))
        assert "wire" not in sv and "reg" not in sv


class TestStatements:
    def body(self, *stmts, sequential=False, target=Target.SYSTEMVERILOG):
        always = Always(sensitivity=[CLK] if sequential else [], body=Block(statements=list(stmts)))
        return emit(Module(name="M", body=[always]), target)

    def test_if_else_if_else(self):
        stmt = If(condition=ident("a"), then_branch=BlockingAssign(lhs=ident("y"), rhs=num("1")),
                  else_branch=If(condition=ident("b"), then_branch=BlockingAssign(lhs=ident("y"), rhs=num("2")),
                                 else_branch=BlockingAssign(lhs=ident("y"), rhs=num("3"))))
        out = flat(self.body(stmt))
        assert "if (a) begin y = 1; end else if (b) begin y = 2; end else begin y = 3; end" in out

    def test_case_fallthrough_is_comma_separated(self):
        case = Case(subject=ident("op"), items=[
            CaseItem(values=[num("0"), num("1")], body=BlockingAssign(lhs=ident("y"), rhs=ident("a"))),
            CaseItem(values=[], body=BlockingAssign(lhs=ident("y"), rhs=num("0"))),
        ])
        out = self.body(case)
        assert "0, 1:    y = a;" in out
        assert "default: y = 0;" in out
        assert "endcase" in out

    def test_nonblocking(self):
        out = self.body(NonBlockingAssign(lhs=ident("q"), rhs=ident("d")), sequential=True)
        assert "q <= d;" in out

    def test_procedural_for(self):
        loop = For(var_name="i", declares_var=True, init=num("0"),
                   condition=BinaryOp(op="<", left=ident("i"), right=num("8")),
                   step=BlockingAssign(lhs=ident("i"), rhs=BinaryOp(op="+", left=ident("i"), right=num("1"))),
                   body=Block())
        assert "for (int i = 0; i < 8; i = i + 1) begin" in self.body(loop)
        v = self.body(loop, target=Target.VERILOG)
        assert "integer i;" in v
        assert "for (i = 0; i < 8; i = i + 1) begin" in v


class TestGenerateFor:
    def loop(self, var="i"):
        return GenerateFor(var_name=var, init=num("0"),
                           condition=BinaryOp(op="<", left=ident(var), right=num("4")),
                           step=BlockingAssign(lhs=ident(var), rhs=BinaryOp(op="+", left=ident(var), right=num("1"))),
                           body=[Assign(lhs=ident("y"), rhs=ident("a"))])

    def test_sv_uses_genvar_and_label(self):
        sv = emit(Module(name="M", body=[self.loop()]))
        assert "for (genvar i = 0; i < 4; i = i + 1) begin : gen_i" in sv

    def test_verilog_wraps_in_generate(self):
        v = flat(emit(Module(name="M", body=[self.loop()]), Target.VERILOG))
        assert "genvar i; generate for (i = 0; i < 4; i = i + 1) begin : gen_i" in v
        assert "end endgenerate" in v

    def test_labels_are_unique(self):
        sv = emit(Module(name="M", body=[self.loop(), self.loop()]))
        assert "begin : gen_i\n" in sv and "begin : gen_i_1\n" in sv


class TestMemories:
    def test_size_only_dimension(self):
        from cerilog.ast.nodes import UnpackedDim
        mem = LocalSignal(name="rom", width_high=num("7"), width_low=num("0"),
                          unpacked=[UnpackedDim(high=num("16"))])
        assert "logic [7:0] rom [16];" in emit(Module(name="M", body=[mem]))
        assert "wire [7:0] rom [0:15];" in emit(Module(name="M", body=[mem]), Target.VERILOG)
        mem.unpacked = [UnpackedDim(high=ident("DEPTH"))]
        assert "rom [0:DEPTH-1];" in emit(Module(name="M", body=[mem]), Target.VERILOG)


class TestInstances:
    def test_named_connections(self):
        inst = Instance(module_name="Adder", name="u_add",
                        params=[Connection(name="WIDTH", expr=num("8"))],
                        connections=[Connection(name="a", expr=ident("x")), Connection(name="b")])
        out = flat(emit(Module(name="M", body=[inst])))
        assert "Adder #( .WIDTH(8) ) u_add ( .a(x), .b() );" in out


class TestExpressions:
    def expr(self, node, target=Target.SYSTEMVERILOG):
        return Emitter(target=target).emit_expr(node)

    def test_nested_unary_keeps_operators_apart(self):
        assert self.expr(UnaryOp(op="-", operand=UnaryOp(op="-", operand=ident("a")))) == "-(-a)"

    @pytest.mark.parametrize("raw, sv, v", [("'0", "'0", "0"), ("'x", "'x", "'bx"), ("'z", "'z", "'bz")])
    def test_fill_literals(self, raw, sv, v):
        assert self.expr(num(raw)) == sv
        assert self.expr(num(raw), Target.VERILOG) == v

    def test_all_ones_needs_width_in_verilog(self):
        with pytest.raises(EmitError, match="Verilog-2005"):
            self.expr(BinaryOp(op="&", left=ident("a"), right=num("'1")), Target.VERILOG)

    def test_all_ones_lowered_from_declared_width(self):
        module = Module(name="M", ports=[
            Port(direction="output", width_high=num("7"), width_low=num("0"), name="y"),
        ], body=[Assign(lhs=ident("y"), rhs=num("'1"))])
        assert "assign y = {8{1'b1}};" in emit(module, Target.VERILOG)
        assert "assign y = '1;" in emit(module)


class TestSourceMaps:
    def test_comment_has_file_and_line(self):
        module = Module(name="M", line=3, body=[Assign(lhs=ident("y"), rhs=ident("a"), line=5)])
        out = Emitter(filename="m.cel").emit(module)
        assert "assign y = a;  // source: m.cel:5" in out
        assert "// source: m.cel:3" in out

    def test_disabled(self):
        module = Module(name="M", line=3, body=[Assign(lhs=ident("y"), rhs=ident("a"), line=5)])
        assert "// source" not in Emitter(source_maps=False, filename="m.cel").emit(module)


class TestTarget:
    @pytest.mark.parametrize("text, target", [("sv", Target.SYSTEMVERILOG), ("SystemVerilog", Target.SYSTEMVERILOG),
                                              ("v", Target.VERILOG), ("verilog", Target.VERILOG)])
    def test_parse(self, text, target):
        assert Target.parse(text) is target

    def test_from_extension(self):
        assert Target.from_extension("out.v") is Target.VERILOG
        assert Target.from_extension("out.SV") is Target.SYSTEMVERILOG
        assert Target.from_extension("out.txt") is None
