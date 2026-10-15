"""
Parser tests (Stage 3)

Run with: python -m pytest tests/parser/
"""

import pytest

# from cerilog.parser.parser import Parser, ParseError
# from cerilog.ast.nodes import Module, Port, AlwaysFF


# Uncomment and fill in as you implement the parser in Stage 3.


# class TestModuleDeclaration:
#     def test_empty_module(self):
#         src = "module Foo() { }"
#         module = Parser().parse(src)
#         assert isinstance(module, Module)
#         assert module.name == "Foo"
#         assert module.ports == []
#         assert module.body == []
#
#     def test_module_with_ports(self):
#         src = "module Bar(input logic clk, output logic out) { }"
#         module = Parser().parse(src)
#         assert len(module.ports) == 2
#         assert module.ports[0].direction == "input"
#         assert module.ports[0].name == "clk"
#         assert module.ports[1].direction == "output"
#         assert module.ports[1].name == "out"


# class TestAlwaysFF:
#     def test_basic_always_ff(self):
#         src = """
#         module Foo(input logic clk) {
#             always_ff(posedge clk) { }
#         }
#         """
#         module = Parser().parse(src)
#         assert len(module.body) == 1
#         assert isinstance(module.body[0], AlwaysFF)
#         assert "posedge clk" in module.body[0].sensitivity


# class TestErrors:
#     def test_missing_closing_brace(self):
#         with pytest.raises(ParseError):
#             Parser().parse("module Foo() {")
#
#     def test_missing_module_name(self):
#         with pytest.raises(ParseError):
#             Parser().parse("module () { }")


def test_placeholder():
    """Placeholder so pytest doesn't complain about an empty test file."""
    pass
