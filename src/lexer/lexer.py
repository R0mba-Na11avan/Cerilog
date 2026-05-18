"""
Cerilog Lexer (Stage 2)

Converts raw Cerilog source text into a stream of tokens.
Uses the Lark library with a custom grammar.

TODO (Stage 2):
    - Define the grammar in grammar.lark
    - Implement Lexer.tokenize()
    - Handle comments (strip or preserve for source maps)
"""

from dataclasses import dataclass
from typing import Iterator


@dataclass
class Token:
    """A single token produced by the lexer."""
    type: str       # e.g. "MODULE", "IDENT", "LBRACE"
    value: str      # raw text
    line: int       # 1-indexed line number in source
    col: int        # 1-indexed column number in source

    def __repr__(self):
        return f"Token({self.type}, {self.value!r}, line={self.line}, col={self.col})"


class LexError(Exception):
    """Raised when the lexer encounters an unexpected character."""
    pass


class Lexer:
    """
    Tokenizes Cerilog source code.

    Usage:
        lexer = Lexer()
        for token in lexer.tokenize(source_code):
            print(token)
    """

    def tokenize(self, source: str) -> Iterator[Token]:
        """
        Tokenize the given source string.
        Yields Token objects in order.
        Raises LexError on unrecognized input.
        """
        # TODO: implement in Stage 2
        raise NotImplementedError("Lexer not yet implemented — coming in Stage 2")
