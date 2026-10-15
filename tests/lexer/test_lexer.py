"""
Lexer tests (Stage 2)

Run with: python -m pytest tests/lexer/
"""

import pytest

# from cerilog.lexer.lexer import Lexer, Token, LexError


# Uncomment and fill in as you implement the lexer in Stage 2.


# class TestKeywords:
#     def test_module_keyword(self):
#         tokens = list(Lexer().tokenize("module"))
#         assert tokens[0].type == "MODULE"
#         assert tokens[0].value == "module"
#
#     def test_input_keyword(self):
#         tokens = list(Lexer().tokenize("input"))
#         assert tokens[0].type == "INPUT"
#
#     def test_logic_keyword(self):
#         tokens = list(Lexer().tokenize("logic"))
#         assert tokens[0].type == "LOGIC"


# class TestIdentifiers:
#     def test_simple_ident(self):
#         tokens = list(Lexer().tokenize("mySignal"))
#         assert tokens[0].type == "IDENT"
#         assert tokens[0].value == "mySignal"
#
#     def test_ident_with_underscore(self):
#         tokens = list(Lexer().tokenize("my_signal_2"))
#         assert tokens[0].type == "IDENT"


# class TestSymbols:
#     def test_lbrace(self):
#         tokens = list(Lexer().tokenize("{"))
#         assert tokens[0].type == "LBRACE"
#
#     def test_rbrace(self):
#         tokens = list(Lexer().tokenize("}"))
#         assert tokens[0].type == "RBRACE"


# class TestSourceLocations:
#     def test_line_number(self):
#         src = "module\nCounter"
#         tokens = list(Lexer().tokenize(src))
#         assert tokens[0].line == 1   # "module" is on line 1
#         assert tokens[1].line == 2   # "Counter" is on line 2


# class TestErrors:
#     def test_unexpected_character(self):
#         with pytest.raises(LexError):
#             list(Lexer().tokenize("@@@"))


def test_placeholder():
    """Placeholder so pytest doesn't complain about an empty test file."""
    pass
