"""
Cerilog transpiler entry point.

Usage:
    python -m cerilog <input.cel>                          # emit SV to stdout
    python -m cerilog <input.cel> -o output.sv             # emit SystemVerilog
    python -m cerilog <input.cel> -o output.v              # emit plain Verilog
    python -m cerilog <input.cel> --target verilog         # force Verilog output
    python -m cerilog <input.cel> --target systemverilog   # force SV output (default)

Target is inferred from the output file extension if -o is provided:
    .sv  ->  SystemVerilog
    .v   ->  Verilog
Explicit --target always overrides extension inference.
"""

import sys
import argparse
from pathlib import Path


VALID_TARGETS = ("systemverilog", "verilog")


def infer_target(output_path: str | None) -> str:
    """Infer target from output file extension. Defaults to systemverilog."""
    if output_path:
        ext = Path(output_path).suffix
        if ext == ".v":
            return "verilog"
        if ext == ".sv":
            return "systemverilog"
    return "systemverilog"


def main():
    parser = argparse.ArgumentParser(
        prog="cerilog",
        description="Transpile Cerilog (.cel) to SystemVerilog (.sv) or Verilog (.v)"
    )
    parser.add_argument("input", help="Input .cel file")
    parser.add_argument("-o", "--output", help="Output file (.sv or .v). Defaults to stdout.")
    parser.add_argument(
        "--target",
        choices=VALID_TARGETS,
        default=None,
        help="Emit target: 'systemverilog' (default) or 'verilog'. "
             "Inferred from output extension if not set."
    )
    parser.add_argument("--tokens", action="store_true", help="Print token stream and exit (debug)")
    parser.add_argument("--ast",    action="store_true", help="Print AST and exit (debug)")
    args = parser.parse_args()

    # --- Resolve target ---
    target = args.target or infer_target(args.output)

    # --- Validate input ---
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
    # from src.codegen.emitter import Emitter, Target
    # code = Emitter(target=Target(target)).emit(tree)

    # --- Output ---
    # if args.output:
    #     Path(args.output).write_text(code)
    #     print(f"Written to {args.output} (target: {target})")
    # else:
    #     print(code)

    print(f"Cerilog transpiler: not yet implemented. Target would be: {target}")


if __name__ == "__main__":
    main()
