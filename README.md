# Cerilog

Cerilog is a C-flavored hardware description language that transpiles to
**SystemVerilog** (`.sv`) or **Verilog-2005** (`.v`). Curly braces instead of
`begin`/`end`, ports declared in the module header, one `logic` type, one
`always` keyword. The output is plain, readable HDL that goes into Quartus,
Vivado, Verilator or Icarus unchanged.

```
counter.cel  ──cerilog──▶  counter.sv / counter.v  ──▶  Quartus / Vivado / Verilator
```

## Example

```cerilog
// counter.cel
module Counter(
    input  logic       clk,
    input  logic       rst,
    output logic[7:0]  count
) {
    always(posedge clk) {
        if (rst) count <= 0;
        else     count <= count + 1;
    }
}
```

`cerilog counter.cel -o counter.sv`:

```systemverilog
module Counter (
    input  logic       clk,
    input  logic       rst,
    output logic [7:0] count
);
    always_ff @(posedge clk) begin
        if (rst) begin
            count <= 0;
        end else begin
            count <= count + 1;
        end
    end
endmodule
```

`cerilog counter.cel -o counter.v`, for tools without SystemVerilog support:

```verilog
module Counter (
    input  wire       clk,
    input  wire       rst,
    output reg  [7:0] count
);
    always @(posedge clk) begin
        if (rst) begin
            count <= 0;
        end else begin
            count <= count + 1;
        end
    end
endmodule
```

(Real output also has a header line and `// source: counter.cel:N` comments,
which tie tool errors back to your source.)

## Features

- `{ }` blocks; braces are optional around single statements, as in C
- Ports and parameters declared in the module header
- `logic` everywhere. For Verilog output, `wire` vs `reg` is worked out for you
- `always()` for combinational logic, `always(posedge clk)` for flip-flops
- C-style stacked `case` labels (fallthrough)
- `for` loops: inside `always` they're procedural, at module level they
  become generate loops
- Multiple modules per file and SystemVerilog-style instances
- Memories, `localparam`, initial values, the full SystemVerilog operator set,
  `$clog2` and friends
- Errors and warnings with `file:line:col`, the source line and a caret
- VS Code extension: highlighting, error squiggles on save, a ▶ compile
  button and an `.sv`/`.v` target picker

The full language is described in [`docs/language_spec.md`](https://github.com/R0mba-Na11avan/Cerilog/blob/main/docs/language_spec.md).

## Install

Requires Python 3.10+.

```bash
pip install cerilog
```

This installs the `cerilog` command and its one dependency, the `lark`
parser library.

To work on Cerilog itself:

```bash
git clone https://github.com/R0mba-Na11avan/Cerilog.git
cd Cerilog
pip install -e ".[dev]"
```

## Usage

```bash
cerilog counter.cel                  # SystemVerilog to stdout
cerilog counter.cel -o counter.sv    # SystemVerilog to a file
cerilog counter.cel -o counter.v     # Verilog-2005 (target taken from the extension)
cerilog counter.cel --target v       # Verilog-2005 to stdout
cerilog counter.cel --check          # only report errors and warnings
```

| Flag | Meaning |
|---|---|
| `-o FILE` | write to `FILE`; a `.sv` or `.v` extension picks the target |
| `--target sv\|v` | choose the output language (also `systemverilog` / `verilog`); overrides the extension |
| `--check` | parse and check only; write nothing |
| `--no-source-maps` | leave out the `// source: file.cel:N` comments |
| `--tokens`, `--ast` | print the token stream or the syntax tree (debugging) |

Errors and warnings go to stderr. The exit status is 1 if there were errors.

```
counter.cel:8:28: error: expected ';' before 'else'
            if (rst) count <= 0
                               ^
```

## VS Code

The extension in [`editors/vscode`](https://github.com/R0mba-Na11avan/Cerilog/blob/main/editors/vscode) adds syntax highlighting,
error checking on save, a ▶ compile button, and a status-bar switch between
`.sv` and `.v` output. See its [README](https://github.com/R0mba-Na11avan/Cerilog/blob/main/editors/vscode/README.md) to install it.

## Project layout

```
cerilog/
├── __main__.py          command line
├── compiler.py          compile_source(): parse → analyse → emit
├── errors.py            diagnostics and their formatting
├── lexer/lexer.py       token stream (debugging, --tokens)
├── parser/grammar.lark  the grammar: every token and syntax rule
├── parser/parser.py     Lark parse tree → AST, syntax error messages
├── ast/nodes.py         AST node dataclasses
├── analysis/checks.py   symbol checks, drivers, wire/reg inference, warnings
└── codegen/emitter.py   SystemVerilog and Verilog output
examples/                example .cel programs
tests/                   pytest suite, golden outputs, Verilator lint
editors/vscode/          VS Code extension
docs/language_spec.md    language reference
```

## Tests

```bash
python -m pytest
```

- `tests/golden/` compiles every file in `examples/` to both targets and
  compares the result with `tests/golden/expected/`. After an intended output
  change, regenerate with `CERILOG_UPDATE_GOLDEN=1 python -m pytest tests/golden`
  and review the diff.
- `tests/lint/` runs `verilator --lint-only` on every example in both
  targets. It is skipped when Verilator isn't installed.

## License

MIT
