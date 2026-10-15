"""
Lexer tests.

Run with: python -m pytest tests/lexer/
"""

import pytest

from cerilog.lexer.lexer import Lexer, LexError


def types(src):
    return [t.type for t in Lexer().tokenize(src)]


class TestKeywords:
    def test_module_keyword(self):
        tokens = list(Lexer().tokenize("module"))
        assert tokens[0].type == "MODULE"
        assert tokens[0].value == "module"

    def test_input_keyword(self):
        tokens = list(Lexer().tokenize("input"))
        assert tokens[0].type == "INPUT"

    def test_logic_keyword(self):
        tokens = list(Lexer().tokenize("logic"))
        assert tokens[0].type == "LOGIC"

    @pytest.mark.parametrize("word", ["always", "always_ff", "always_comb"])
    def test_always_spellings(self, word):
        assert types(word) == ["ALWAYS"]

    def test_keyword_prefix_is_identifier(self):
        assert types("always_x modules casez_1") == ["IDENT", "IDENT", "IDENT"]


class TestIdentifiers:
    def test_simple_ident(self):
        tokens = list(Lexer().tokenize("mySignal"))
        assert tokens[0].type == "IDENT"
        assert tokens[0].value == "mySignal"

    def test_ident_with_underscore(self):
        tokens = list(Lexer().tokenize("my_signal_2"))
        assert tokens[0].type == "IDENT"

    def test_system_function(self):
        assert types("$clog2") == ["SYSNAME"]


class TestNumbers:
    @pytest.mark.parametrize("text", ["42", "1_000", "8'hFF", "4'b10_10", "'d5", "4'sb1010", "'0", "'1", "'x"])
    def test_number_forms(self, text):
        tokens = list(Lexer().tokenize(text))
        assert [(t.type, t.value) for t in tokens] == [("NUMBER", text)]


class TestSymbols:
    def test_lbrace(self):
        tokens = list(Lexer().tokenize("{"))
        assert tokens[0].type == "LBRACE"

    def test_rbrace(self):
        tokens = list(Lexer().tokenize("}"))
        assert tokens[0].type == "RBRACE"

    def test_multi_char_operators_have_names(self):
        assert types("<= == <<< ++") == ["LESSEQUAL", "EQEQ", "ASHL", "INCREMENT"]


class TestComments:
    def test_comments_are_skipped(self):
        assert types("a // line comment\n/* block\ncomment */ b") == ["IDENT", "IDENT"]


class TestSourceLocations:
    def test_line_number(self):
        src = "module\nCounter"
        tokens = list(Lexer().tokenize(src))
        assert tokens[0].line == 1   # "module" is on line 1
        assert tokens[1].line == 2   # "Counter" is on line 2

    def test_column_number(self):
        tokens = list(Lexer().tokenize("  foo bar"))
        assert [t.col for t in tokens] == [3, 7]


class TestErrors:
    def test_unexpected_character(self):
        with pytest.raises(LexError):
            list(Lexer().tokenize("@@@"))

    def test_error_location(self):
        with pytest.raises(LexError) as info:
            list(Lexer().tokenize("a\n  @"))
        assert (info.value.diagnostic.line, info.value.diagnostic.col) == (2, 3)
