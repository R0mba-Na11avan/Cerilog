"""
Cerilog command line.

    cerilog counter.cel                     SystemVerilog to stdout
    cerilog counter.cel -o counter.sv       SystemVerilog to a file
    cerilog counter.cel -o counter.v        Verilog-2005 (target from the extension)
    cerilog counter.cel --target v          Verilog-2005 to stdout
    cerilog counter.cel --check             check only, write nothing

Diagnostics go to stderr. Exit status is 1 if there were errors.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cerilog.codegen.emitter import Target
from cerilog.compiler import compile_source
from cerilog.errors import CerilogError, format_diagnostic


def _parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="cerilog",
        description="Transpile Cerilog (.cel) to SystemVerilog (.sv) or Verilog-2005 (.v).",
    )
    parser.add_argument("input", help="input .cel file")
    parser.add_argument("-o", "--output", help="output file; .sv or .v picks the target (default: stdout)")
    parser.add_argument("--target", metavar="{sv,v}",
                        help="output language: sv/systemverilog or v/verilog "
                             "(default: from the -o extension, else sv)")
    parser.add_argument("--check", action="store_true", help="report errors and warnings, write nothing")
    parser.add_argument("--no-source-maps", action="store_true",
                        help="leave out the // source: file.cel:N comments")
    parser.add_argument("--tokens", action="store_true", help="print the token stream and exit (debug)")
    parser.add_argument("--ast", action="store_true", help="print the AST and exit (debug)")
    return parser, parser.parse_args(argv)


def _resolve_target(parser, args) -> Target:
    if args.target:
        try:
            return Target.parse(args.target)
        except ValueError as e:
            parser.error(str(e))
    if args.output:
        from_ext = Target.from_extension(args.output)
        if from_ext is not None:
            return from_ext
    return Target.SYSTEMVERILOG


def main(argv=None) -> int:
    parser, args = _parse_args(argv)
    target = _resolve_target(parser, args)

    input_path = Path(args.input)
    if not input_path.is_file():
        print(f"cerilog: error: file not found: {args.input}", file=sys.stderr)
        return 1
    if input_path.suffix != ".cel":
        print(f"cerilog: warning: expected a .cel file, got '{input_path.suffix}'", file=sys.stderr)

    source = input_path.read_text(encoding="utf-8")
    display_name = args.input

    if args.tokens or args.ast:
        return _debug_dump(args, source, display_name)

    result = compile_source(source, target=target, filename=input_path.name,
                            source_maps=not args.no_source_maps)
    for diag in result.diagnostics:
        print(format_diagnostic(diag, source, display_name), file=sys.stderr)
    if not result.ok:
        return 1
    if args.check:
        return 0

    if args.output:
        Path(args.output).write_text(result.code, encoding="utf-8", newline="\n")
        print(f"cerilog: wrote {args.output} ({target.display_name})", file=sys.stderr)
    else:
        sys.stdout.write(result.code)
    return 0


def _debug_dump(args, source: str, display_name: str) -> int:
    from cerilog.ast.nodes import dump
    from cerilog.lexer.lexer import Lexer
    from cerilog.parser.parser import Parser

    try:
        if args.tokens:
            for token in Lexer().tokenize(source):
                print(token)
        else:
            print(dump(Parser().parse(source)))
    except CerilogError as e:
        print(format_diagnostic(e.diagnostic, source, display_name), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
