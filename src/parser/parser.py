"""
Cerilog Parser (Stage 3)

Consumes the token stream from the Lexer and produces an AST.
Uses Lark's Earley or LALR parser with the grammar defined in grammar.lark.

TODO (Stage 3):
    - Write grammar.lark
    - Implement Parser.parse()
    - Implement the Transformer that converts Lark's parse tree into our AST nodes
"""

from pathlib import Path
from src.ast.nodes import Module


GRAMMAR_PATH = Path(__file__).parent / "grammar.lark"


class ParseError(Exception):
    """Raised when the parser encounters a syntax error."""
    pass


class Parser:
    """
    Parses Cerilog source into an AST.

    Usage:
        parser = Parser()
        module = parser.parse(source_code)
    """

    def __init__(self):
        # TODO Stage 3: load grammar and initialize Lark
        # from lark import Lark
        # self._parser = Lark(GRAMMAR_PATH.read_text(), parser="lalr")
        pass

    def parse(self, source: str) -> Module:
        """
        Parse Cerilog source and return the root AST node.
        Raises ParseError on invalid syntax.
        """
        # TODO: implement in Stage 3
        raise NotImplementedError("Parser not yet implemented — coming in Stage 3")
