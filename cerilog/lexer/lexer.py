"""
Cerilog lexer: source text -> Token stream.

Token rules live in cerilog/parser/grammar.lark; this module runs Lark's lexer
over them so tokens are defined in exactly one place. The parser does not use
this stream (Lark lexes internally while parsing); it exists for debugging
(`cerilog --tokens`) and for testing the token rules on their own.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from lark.exceptions import UnexpectedCharacters

from cerilog.parser.parser import LexError, build_lark

__all__ = ["Lexer", "Token", "LexError"]


# Lark auto-names multi-character operators __ANON_n; give them stable names.
_OPERATOR_NAMES = {
    "<=": "LESSEQUAL", ">=": "MOREEQUAL", "==": "EQEQ", "!=": "NOTEQ",
    "===": "CASEEQ", "!==": "CASENOTEQ", "&&": "ANDAND", "||": "OROR",
    "<<": "SHL", ">>": "SHR", "<<<": "ASHL", ">>>": "ASHR", "**": "POW",
    "~&": "NAND", "~|": "NOR", "~^": "XNOR", "^~": "XNOR",
    "++": "INCREMENT", "--": "DECREMENT", "+=": "PLUSEQUAL", "-=": "MINUSEQUAL",
}


@dataclass
class Token:
    """A single token."""
    type: str       # e.g. "MODULE", "IDENT", "LBRACE"
    value: str      # raw text
    line: int       # 1-indexed
    col: int        # 1-indexed

    def __repr__(self):
        return f"Token({self.type}, {self.value!r}, line={self.line}, col={self.col})"


class Lexer:
    """
    Tokenizes Cerilog source code.

        for token in Lexer().tokenize(source):
            print(token)
    """

    def tokenize(self, source: str) -> Iterator[Token]:
        """Yield tokens in order. Raises LexError on unrecognized input."""
        lark = build_lark("basic")
        try:
            for tok in lark.lex(source):
                type_ = tok.type
                if type_.startswith("__ANON"):
                    type_ = _OPERATOR_NAMES.get(str(tok), "OPERATOR")
                yield Token(type_, str(tok), tok.line, tok.column)
        except UnexpectedCharacters as e:
            raise LexError(f"unexpected character {source[e.pos_in_stream]!r}", e.line, e.column) from None
