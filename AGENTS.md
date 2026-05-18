# AGENTS.md

Instructions for AI coding agents working on the Cerilog repository.

---

## What This Project Is

Cerilog is a transpiler that converts `.cel` source files into valid SystemVerilog (`.sv`).
The generated `.sv` is fed directly into existing FPGA toolchains (Quartus, Vivado, Verilator) unchanged.
Cerilog does NOT compile to hardware itself — it is purely source-to-source.

```
input.cel  →  [Cerilog transpiler]  →  output.sv  →  Quartus / Verilator
```

---

## Repository Structure

```
cerilog/
├── src/
│   ├── __main__.py         # CLI entry point: python -m cerilog <file.cel>
│   ├── lexer/
│   │   └── lexer.py        # Tokenizer — produces Token stream from source text
│   ├── parser/
│   │   ├── parser.py       # Builds AST from token stream using Lark
│   │   └── grammar.lark    # Lark grammar file (created in Stage 3)
│   ├── ast/
│   │   └── nodes.py        # ALL AST node dataclasses — the source of truth for the IR
│   └── codegen/
│       └── emitter.py      # Walks AST and emits SystemVerilog strings
├── tests/
│   ├── lexer/test_lexer.py
│   ├── parser/test_parser.py
│   └── codegen/test_emitter.py
├── examples/               # Example .cel programs — use these to test end-to-end
│   ├── counter.cel
│   └── adder.cel
└── docs/
    └── language_spec.md    # Source of truth for Cerilog syntax
```

---

## Language Reference

Always read `docs/language_spec.md` before making any changes to the lexer, parser, AST, or emitter.
It is the source of truth for what Cerilog syntax looks like and how it maps to SystemVerilog.

Key design decisions already made:
- **`logic`** is the universal signal type — no `wire` or `reg`
- **`always()`** is unified: no args emits `always_comb`, any args emit `always_ff @(...)`
- **`int`** is valid for loop counters (passes through to SV directly)
- **Case fallthrough** uses stacked cases with no body — emits as comma-separated SV values
- **Curly braces** map to `begin`/`end`/`endmodule` based on context

---

## AST Nodes

`src/ast/nodes.py` is the single source of truth for the intermediate representation.
Do not add new syntax to the lexer or parser without first adding the corresponding node to `nodes.py`.

The most important node is `Always`:
```python
# sensitivity == []       ->  emits always_comb
# sensitivity == [...]    ->  emits always_ff @(...)
Always(sensitivity=[], body=Block(...))
Always(sensitivity=["posedge clk"], body=Block(...))
```

---

## Development Stages

The project is built in order — do not skip stages:

| Stage | File(s) | Status |
|-------|---------|--------|
| 1 — Syntax design | `docs/language_spec.md` | ✅ Done |
| 2 — Lexer | `src/lexer/lexer.py` | 🚧 Todo |
| 3 — Parser | `src/parser/parser.py`, `grammar.lark` | 🚧 Todo |
| 4 — Code gen | `src/codegen/emitter.py` | 🚧 Todo |
| 5 — Polish | Error messages, VS Code extension | 🚧 Todo |

---

## Coding Rules

- **Python 3.10+** — use `match` statements where appropriate, use `dataclasses`, use `list[X]` not `List[X]`
- **Lark** is the parser library — do not swap it out for another library without discussion
- All AST nodes inherit from `Node` and store `line` and `col` for source map comments
- Emitted SV lines should include `// source: filename.cel:N` comments (controlled by `Emitter.source_maps` flag)
- Do not emit plain `always @(*)` — always use `always_comb` or `always_ff`
- Keep emitted SystemVerilog readable — indent properly, don't minify

---

## Testing

```bash
# Run all tests
python -m pytest tests/

# Run a specific stage
python -m pytest tests/lexer/
python -m pytest tests/parser/
python -m pytest tests/codegen/
```

Tests are pre-scaffolded with commented-out cases. Uncomment and implement as each stage is built.
Do not delete commented test cases — they are the spec for what each stage must handle.

---

## Verifying Emitted Output

Use **Verilator** to validate that emitted `.sv` files are legal SystemVerilog:

```bash
verilator --lint-only output.sv
```

This is the ground truth for correctness. If Verilator accepts it, the emitter is correct.

---

## What NOT to Do

- Do not change `always_comb` / `always_ff` emit behavior — it is intentional (see language spec)
- Do not introduce new top-level types besides `logic` and `int` without updating `language_spec.md` first
- Do not emit `wire` or `reg` — always emit `logic`
- Do not add dependencies beyond `lark` and `pytest` without a good reason