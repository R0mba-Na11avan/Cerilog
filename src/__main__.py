"""
Cerilog transpiler entry point.
Usage: python -m cerilog <input.cel> [-o output.sv]
"""

import sys
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        prog="cerilog",
        description="Transpile Cerilog (.cel) to SystemVerilog (.sv)"
    )
    parser.add_argument("input", help="Input .cel file")
    parser.add_argument("-o", "--output", help="Output .sv file (default: stdout)")
    parser.add_argument("--tokens", action="store_true", help="Print token stream and exit (debug)")
    parser.add_argument("--ast", action="store_true", help="Print AST and exit (debug)")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: file not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    if input_path.suffix != ".cel":
        print(f"Warning: expected .cel extension, got {input_path.suffix}", file=sys.stderr)

    source = input_path.read_text()

    # --- Stage 2: Lex ---
    # from src.lexer.lexer import Lexer
    # tokens = Lexer().tokenize(source)
    # if args.tokens:
    #     for tok in tokens: print(tok)
    #     return

    # --- Stage 3: Parse ---
    # from src.parser.parser import Parser
    # tree = Parser().parse(source)
    # if args.ast:
    #     print(tree.pretty())
    #     return

    # --- Stage 4: Code gen ---
    # from src.codegen.emitter import Emitter
    # sv_code = Emitter().emit(tree)

    # --- Output ---
    # if args.output:
    #     Path(args.output).write_text(sv_code)
    # else:
    #     print(sv_code)

    print("Cerilog transpiler: not yet implemented. Stay tuned!")


if __name__ == "__main__":
    main()
