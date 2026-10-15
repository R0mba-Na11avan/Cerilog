"""
Semantic analysis tests.

Run with: python -m pytest tests/analysis/
"""

from cerilog.analysis.checks import analyze
from cerilog.parser.parser import Parser

PORTS = "input logic clk, input logic a, input logic[7:0] b, output logic y, output logic[7:0] z"


def check(body: str, ports: str = PORTS, extra: str = ""):
    tree = Parser().parse(f"{extra}\nmodule M({ports}) {{\n{body}\n}}")
    diags = analyze(tree)
    return tree, diags


def errors(body, **kw):
    return [d.message for d in check(body, **kw)[1] if d.is_error]


def warnings(body, **kw):
    return [d.message for d in check(body, **kw)[1] if not d.is_error]


class TestDeclarations:
    def test_clean_module_has_no_diagnostics(self):
        _, diags = check("logic t; assign t = a; always(posedge clk) y <= t;")
        assert diags == []

    def test_undeclared_identifier(self):
        assert errors("assign y = nope;") == ["'nope' is not declared"]

    def test_undeclared_reported_once(self):
        assert errors("assign y = nope & nope;") == ["'nope' is not declared"]

    def test_duplicate_declaration(self):
        assert errors("logic a;") == ["'a' is already declared in module 'M'"]

    def test_duplicate_module(self):
        tree = Parser().parse("module A() { } module A() { }")
        assert [d.message for d in analyze(tree)] == ["module 'A' is defined twice"]

    def test_loop_variable_scoped_to_loop(self):
        assert errors("always() { for (int i = 0; i < 8; i++) z[i] = b[i]; y = i; }") == ["'i' is not declared"]

    def test_undeclared_loop_variable(self):
        assert errors("always() for (i = 0; i < 8; i++) z[i] = 1;") == ["loop variable 'i' is not declared"]

    def test_genvar_in_scope_inside_generate(self):
        assert errors("for (int i = 0; i < 8; i++) { assign z[i] = b[i]; }") == []


class TestDrivers:
    def test_assign_to_input(self):
        assert errors("assign a = 1;") == ["cannot assign to input port 'a'"]

    def test_assign_to_parameter(self):
        assert errors("localparam P = 1; assign P = 1;") == ["cannot assign to localparam 'P'"]

    def test_always_and_assign_conflict(self):
        assert errors("assign y = a; always(posedge clk) y <= a;") == [
            "'y' is driven by both an always block and an assign"]

    def test_init_and_assign_conflict(self):
        assert errors("logic t = 0; assign t = a; assign y = t;") == [
            "'t' has an initial value but is driven by an assign"]

    def test_bad_assignment_target(self):
        assert errors("assign $clog2(b) = 1;") == [
            "left side of an assignment must be a signal, a bit/part select of one, "
            "or a {concatenation} of those"]

    def test_driven_in_always_flags(self):
        tree, _ = check("logic t; logic u; always() t = a; assign u = a; assign y = t & u;")
        module = tree.modules[0]
        flags = {s.name: s.driven_in_always for s in module.body if hasattr(s, "driven_in_always")}
        assert flags == {"t": True, "u": False}

    def test_concat_target_marks_every_part(self):
        tree, diags = check("always() {y, z} = {a, b};")
        ports = {p.name: p.driven_in_always for p in tree.modules[0].ports}
        assert ports["y"] and ports["z"] and not ports["a"]

    def test_instance_output_counts_as_continuous_driver(self):
        extra = "module Sub(input logic i, output logic o) { assign o = i; }"
        assert errors("Sub u (.i(a), .o(y)); always(posedge clk) y <= a;", extra=extra) == [
            "'y' is driven by both an always block and an instance output"]

    def test_instance_unknown_port(self):
        extra = "module Sub(input logic i, output logic o) { assign o = i; }"
        assert errors("Sub u (.i(a), .nope(y));", extra=extra) == ["module 'Sub' has no port 'nope'"]

    def test_instance_of_external_module_is_accepted(self):
        assert errors("External u (.i(a), .o(y));") == []

    def test_mixed_named_and_positional(self):
        assert errors("External u (a, .o(y));") == [
            "instance 'u' mixes named and positional port connections"]


class TestWarnings:
    def test_blocking_in_clocked_block(self):
        assert warnings("always(posedge clk) y = a;") == ["blocking assignment '=' in a clocked always block"]

    def test_nonblocking_in_combinational_block(self):
        assert warnings("always() y <= a;") == ["non-blocking assignment '<=' in a combinational always block"]

    def test_loop_step_does_not_warn(self):
        assert warnings("always(posedge clk) for (int i = 0; i < 8; i++) z[i] <= b[i];") == []

    def test_written_in_two_always_blocks(self):
        assert warnings("always(posedge clk) y <= a; always(posedge clk) y <= 0;") == [
            "'y' is written in more than one always block"]
