# AGENTS.md

Guide for AI coding agents working on Cerilog.

## What this is

Cerilog transpiles `.cel` (a C-flavored HDL) to SystemVerilog (`.sv`) or
Verilog-2005 (`.v`). It is source-to-source only; the output goes to existing
FPGA tools unchanged. `docs/language_spec.md` is the user-facing reference for
the language and must match the code.

## Pipeline

```
source ─▶ parser (Lark LALR, grammar.lark) ─▶ AST ─▶ analysis ─▶ emitter(target) ─▶ .sv / .v
```

| Stage | File | Notes |
|---|---|---|
| Grammar | `cerilog/parser/grammar.lark` | Every token and syntax rule, defined once |
| Parser | `cerilog/parser/parser.py` | `_ToAst` turns the parse tree into nodes; Lark errors become `ParseError` / `LexError` |
| Lexer | `cerilog/lexer/lexer.py` | Runs Lark's lexer on the same grammar; used only for `--tokens` and tests |
| AST | `cerilog/ast/nodes.py` | Dataclasses; every node has `line`/`col` |
| Analysis | `cerilog/analysis/checks.py` | Symbols, undeclared/duplicate names, drivers, sets `driven_in_always`, warnings |
| Emitter | `cerilog/codegen/emitter.py` | One `Emitter` class; `Target` picks SystemVerilog or Verilog-2005 |
| Pipeline | `cerilog/compiler.py` | `compile_source()` returns code + diagnostics; never raises for bad source |
| CLI | `cerilog/__main__.py` | Target from `--target`, else the `-o` extension, else sv |
| Errors | `cerilog/errors.py` | `Diagnostic`, `CerilogError`, `format_diagnostic()` |

## Adding or changing a construct

Work through every stage, in this order:

1. **Node** in `nodes.py`.
2. **Grammar** rule in `grammar.lark`. Keep the grammar LALR: Lark logs
   shift/reduce conflicts at debug level and resolves them as shift. Exactly
   two are intended (dangling `else`, and `<=` at the start of a statement
   being an assignment). A reduce/reduce conflict is an error. Multi-word
   keyword terminals need a priority and `\b` (see `ALWAYS.2`).
3. **Transformer** method in `parser.py` that builds the node with its position.
4. **Analysis** in `checks.py`: declare names, walk expressions, record drivers.
5. **Emitter**: output for both targets. If a construct can't be expressed in
   Verilog-2005, lower it; if lowering is impossible, raise `EmitError` with a
   message naming the target and a hint.
6. **Tests**: parser, analysis and emitter unit tests, plus an example in
   `examples/` if it's user-visible (then regenerate the golden files).
7. **Docs**: `docs/language_spec.md`: syntax, output for both targets, any
   new diagnostic in the diagnostics tables.

## Rules

- Python 3.10+: `match` statements, dataclasses, `list[X]`.
- Lark is the parser. Runtime dependency: `lark` only. Dev dependency: `pytest`.
- SystemVerilog output: never `wire`/`reg`, never `always @(*)`. Use `logic`,
  `always_comb`, `always_ff`.
- Verilog output: never `logic`, `always_comb`, `always_ff`, `int`, or
  `'0`-style fills. Use `wire`/`reg` from `driven_in_always`, `always @(...)`,
  hoisted `integer`/`genvar` declarations, and `generate`/`endgenerate`.
- Diagnostics are target independent, except `EmitError`s raised while
  lowering for Verilog.
- The first line of every diagnostic is `file:line:col: severity: message`.
  The VS Code extension parses it, so keep that format.
- Keep output readable: 4-space indent, aligned ports, `begin`/`end` on every
  block, source comments controlled by `source_maps`.
- Source has a single type, `logic` (plus `int`/`genvar` loop counters). Don't
  add new types without updating the spec.

## Testing

```bash
python -m pytest                                    # everything
python -m pytest tests/parser                       # one area
CERILOG_UPDATE_GOLDEN=1 python -m pytest tests/golden   # regenerate expected output
```

- Golden files in `tests/golden/expected/` are the exact output for every
  example in both targets. Review their diff whenever you regenerate them.
- `tests/lint/test_verilator.py` lints every example with Verilator in both
  targets and is skipped when `verilator` isn't on PATH. Verilator acceptance
  is the ground truth for "legal SV/Verilog".
- `tests/test_cli.py` runs the real CLI, including the diagnostic format.

## VS Code extension

`editors/vscode/` is plain JavaScript with no build step and no npm
dependencies. It shells out to the CLI (`cerilog.command` setting) with
`--check` on save and `-o` for the ▶ button, and parses diagnostics from
stderr. If you change CLI flags or the diagnostic format, update
`extension.js` too.
