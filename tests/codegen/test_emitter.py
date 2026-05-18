"""
Code generator tests (Stage 4)

Run with: python -m pytest tests/codegen/

Strategy: build AST nodes by hand and assert the emitted SV is correct.
Don't rely on the parser here — test the emitter in isolation.
"""

import pytest

# from src.ast.nodes import Module, Port, AlwaysFF, Block, If, NonBlockingAssign, Identifier, NumberLit
# from src.codegen.emitter import Emitter


# Uncomment and fill in as you implement the emitter in Stage 4.


# class TestModuleEmit:
#     def test_empty_module(self):
#         module = Module(name="Foo", ports=[], body=[])
#         sv = Emitter().emit(module)
#         assert "module Foo" in sv
#         assert "endmodule" in sv
#
#     def test_module_with_ports(self):
#         module = Module(
#             name="Counter",
#             ports=[
#                 Port(direction="input", name="clk"),
#                 Port(direction="output", width_high=NumberLit(raw="7"),
#                      width_low=NumberLit(raw="0"), name="count"),
#             ],
#             body=[]
#         )
#         sv = Emitter().emit(module)
#         assert "input logic clk" in sv
#         assert "output logic[7:0] count" in sv


# class TestAlwaysFFEmit:
#     def test_basic(self):
#         node = AlwaysFF(
#             sensitivity=["posedge clk"],
#             body=Block(statements=[])
#         )
#         module = Module(name="Foo", ports=[], body=[node])
#         sv = Emitter().emit(module)
#         assert "always_ff @(posedge clk)" in sv
#         assert "begin" in sv
#         assert "end" in sv


def test_placeholder():
    """Placeholder so pytest doesn't complain about an empty test file."""
    pass
