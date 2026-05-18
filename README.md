# Cerilog

A modern hardware description language that transpiles to SystemVerilog. Cerilog brings C++-style syntax to FPGA development — curly braces, inline port declarations, and sane defaults — while targeting existing toolchains like Quartus Prime, Vivado, and Verilator unchanged.

---

## Motivation

Verilog was designed in 1984. If you've written C++ and then sat down with Verilog, you've felt the gap. Cerilog closes it — not by reinventing hardware semantics, but by giving you a syntax that gets out of your way.

```cerilog
// Cerilog
module Counter(input logic clk, input logic rst, output logic[7:0] count) {
    always_ff(posedge clk) {
        if (rst) {
            count = 0;
        } else {
            count = count + 1;
        }
    }
}
```

```systemverilog
// Generated SystemVerilog (fed directly into Quartus)
module Counter(input logic clk, input logic rst, output logic[7:0] count);
    always_ff @(posedge clk) begin
        if (rst) begin
            count = 0;
        end else begin
            count = count + 1;
        end
    end
endmodule
```

---

## Features

- **Curly braces** instead of `begin`/`end`/`endmodule`
- **Inline port declarations** in the module header
- **`logic` as the universal type** — no more choosing between `wire` and `reg`
- **C-style comments** (`//` and `/* */`)
- Transpiles to clean, readable SystemVerilog
- Drops straight into Quartus, Vivado, or Verilator — no changes to your toolchain

---

## Project Status

🚧 **Early development** — Stage 1 (syntax design) in progress.

- [ ] Stage 1 — Syntax design
- [ ] Stage 2 — Lexer
- [ ] Stage 3 — Parser
- [ ] Stage 4 — Code generator
- [ ] Stage 5 — Polish & tooling

---

## Toolchain

```
yourfile.cel
    │
    ▼
Cerilog transpiler     (this project)
    │
    ▼
yourfile.sv             (generated SystemVerilog)
    │
    ▼
Quartus / Vivado        (unchanged — programs your FPGA as normal)
```

---

## Getting Started

### Requirements

- Python 3.10+
- [Lark](https://github.com/lark-parser/lark) (`pip install lark`)

### Install

```bash
git clone https://github.com/yourname/cerilog.git
cd cerilog
pip install -e .
```

### Usage

```bash
# Transpile a single file
python -m cerilog counter.cel -o counter.sv

# Transpile and print to stdout
python -m cerilog counter.cel
```

### Run Tests

```bash
python -m pytest tests/
```

---

## Repository Structure

```
cerilog/
├── src/
│   ├── lexer/          # Tokenizer
│   ├── parser/         # Grammar + AST builder
│   ├── ast/            # AST node definitions
│   └── codegen/        # SystemVerilog emitter
├── tests/
│   ├── lexer/          # Lexer unit tests
│   ├── parser/         # Parser unit tests
│   └── codegen/        # Code gen unit tests
├── examples/           # Example .cel programs
├── docs/               # Language spec and notes
└── README.md
```

---

## Language Reference

See [`docs/language_spec.md`](docs/language_spec.md) for the full syntax reference.

---

## Contributing

This is a personal learning project for now. If you're interested in contributing, open an issue first to discuss.

---

## License

MIT
