# Cerilog Language Reference

Cerilog is a C-flavored hardware description language. A `.cel` file is
transpiled to either **SystemVerilog** (`.sv`) or **Verilog-2005** (`.v`); the
output goes straight into Quartus, Vivado, Verilator or Icarus unchanged.

This document describes every construct, what it emits for each target, and
every error and warning the compiler can report. Output snippets are shown
without the `// source:` comments (`--no-source-maps`).

- [Files and modules](#files-and-modules)
- [Ports and parameters](#ports-and-parameters)
- [Declarations](#declarations)
- [Continuous assignment](#continuous-assignment)
- [Always blocks](#always-blocks)
- [Statements](#statements)
- [For loops](#for-loops)
- [Module instances](#module-instances)
- [Expressions](#expressions)
- [Targets](#targets)
- [Diagnostics](#diagnostics)

---

## Files and modules

A file holds any number of modules. Module bodies use curly braces; ports and
parameters are declared in the header.

```cerilog
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

| | SystemVerilog | Verilog-2005 |
|---|---|---|
| header | `module Counter (` ... `);` | same |
| port | `output logic [7:0] count` | `output reg  [7:0] count` |
| body | `always_ff @(posedge clk) begin` ... `end` | `always @(posedge clk) begin` ... `end` |
| end | `endmodule` | `endmodule` |

Comments are `// line` and `/* block */`. Statements end with `;`.
Identifiers are letters, digits, `_` and `$`, not starting with a digit.

Reserved words: `module input output inout logic signed parameter localparam
assign always always_ff always_comb posedge negedge or if else case casez
default for int genvar integer`.

---

## Ports and parameters

```cerilog
module Fifo #(WIDTH = 8, DEPTH = 16) (
    input  logic                 clk,
    input  logic signed [7:0]    offset,
    input        [WIDTH-1:0]     data_in,     // 'logic' is optional
    inout  logic                 sda,
    output logic[WIDTH-1:0]      data_out,    // a trailing comma is allowed
) { ... }
```

- Directions: `input`, `output`, `inout`.
- Type: `logic`, which you may leave out. `signed` is optional.
- Width: `[high:low]`, any constant expression.
- Parameters: `#(NAME = default, ...)`. The `parameter` keyword is optional.
  Both targets emit `#(parameter NAME = default, ...)`.

---

## Declarations

### Signals

```cerilog
logic          done;
logic[7:0]     a, b;               // one line per name in the output
logic signed [15:0] acc = 0;       // initial value (power-on value on FPGAs)
logic[7:0]     mem[0:255];         // memory: 256 bytes
logic[7:0]     rom[16];            // memory with a size instead of a range
```

| Cerilog | SystemVerilog | Verilog-2005 |
|---|---|---|
| `logic[7:0] a;` | `logic [7:0] a;` | `wire [7:0] a;` or `reg [7:0] a;` |
| `logic[7:0] mem[0:255];` | `logic [7:0] mem [0:255];` | `reg [7:0] mem [0:255];` |
| `logic[7:0] rom[16];` | `logic [7:0] rom [16];` | `reg [7:0] rom [0:15];` |

In Verilog, a signal is `reg` when any always block writes it and `wire`
otherwise (see [wire vs reg](#wire-vs-reg)). You only ever write `logic`.

### Constants

```cerilog
localparam AW = $clog2(DEPTH);
localparam IDLE = 2'd0, RUN = 2'd1;
```

Emitted unchanged, one `localparam` per line.

---

## Continuous assignment

```cerilog
assign sum = a + b;
assign {carry, sum} = a + b;      // concatenation on the left
assign bits[3:0] = nibble;
```

Emitted unchanged in both targets.

---

## Always blocks

One keyword covers flip-flops and combinational logic. The sensitivity list
decides which one you get.

| Cerilog | SystemVerilog | Verilog-2005 |
|---|---|---|
| `always() { }` | `always_comb begin ... end` | `always @(*) begin ... end` |
| `always(*) { }` | `always_comb` | `always @(*)` |
| `always(posedge clk) { }` | `always_ff @(posedge clk)` | `always @(posedge clk)` |
| `always(posedge clk, negedge rst_n) { }` | `always_ff @(posedge clk, negedge rst_n)` | `always @(posedge clk, negedge rst_n)` |

- Entries can be separated with `,` or `or`.
- Every entry needs `posedge` or `negedge`. A level-sensitive list like
  `always(a, b)` is an error: write `always()` for combinational logic.
- `always_ff(...)` and `always_comb()` are accepted as aliases. `always_ff()`
  with no edges and `always_comb(...)` with edges are errors.
- The body can be a `{ block }` or a single statement:
  `always(posedge clk) q <= d;`

Use `<=` in clocked blocks and `=` in combinational blocks. The compiler emits
what you write, and warns when the two are swapped.

---

## Statements

Statements appear inside always blocks. Any statement body can be a
`{ block }` or a single statement, as in C.

### Assignment

```cerilog
y = a & b;         // blocking
q <= d;            // non-blocking
{hi, lo} = word;   // concatenation target
mem[addr] <= data;
```

At the start of a statement, `<=` is always an assignment. `<=` inside an
expression is less-or-equal: `flag <= a <= b;` assigns `a <= b` to `flag`.

### If / else

```cerilog
if (a) {
    y = 1;
} else if (b) {
    y = 2;
} else y = 3;
```

Emits `if (a) begin ... end else if (b) begin ... end else begin ... end`.
An `else` belongs to the nearest `if`, as in C.

### Case

```cerilog
case (opcode) {
    4'h0:
    4'h1:
    4'h2: result = a + b;   // 0, 1 and 2 all land here
    4'h3, 4'h4: result = a - b;
    4'h5: { result = a & b; done = 1; }
    default: result = '0;
}
```

Stacked labels with no statement between them share the next statement, like
C fallthrough. Verilog has no fallthrough, so they are merged into one
comma-separated item:

```systemverilog
case (opcode)
    4'h0, 4'h1, 4'h2: result = a + b;
    4'h3, 4'h4:       result = a - b;
    4'h5: begin
        result = a & b;
        done = 1;
    end
    default:          result = '0;
endcase
```

`casez` works the same way and allows `?` don't-care bits: `4'b1???`.
An arm with no work is written `default: ;`.

---

## For loops

The same `for` syntax means two different things depending on where it is.

### Inside an always block: procedural loop

The synthesis tool unrolls it.

```cerilog
always() {
    ones = 0;
    for (int i = 0; i < 8; i++) ones = ones + data[i];
}
```

| SystemVerilog | Verilog-2005 |
|---|---|
| `for (int i = 0; i < 8; i = i + 1) begin` | `integer i;` at the top of the module, then `for (i = 0; i < 8; i = i + 1) begin` |

### At module level: generate loop

It stamps out a copy of its body for each value: here, 8 `assign`s.

```cerilog
for (int i = 0; i < WIDTH; i++) {
    assign out[i] = data[i] ^ mask[i];
}
```

SystemVerilog:

```systemverilog
for (genvar i = 0; i < WIDTH; i = i + 1) begin : gen_i
    assign out[i] = data[i] ^ mask[i];
end
```

Verilog-2005:

```verilog
genvar i;

generate
    for (i = 0; i < WIDTH; i = i + 1) begin : gen_i
        assign out[i] = data[i] ^ mask[i];
    end
endgenerate
```

Rules for both kinds:

- Declare the counter in the loop with `int` (module-level loops also accept
  `genvar`). It is only visible inside the loop.
- The step can be `i++`, `i--`, `i += n`, `i -= n` or `i = expr`; it is
  always emitted as `i = ...`.
- Generate blocks are labelled `gen_<var>`, with `_1`, `_2`, ... added when
  a module has more than one loop over the same name.
- A generate body may contain any module item: signals, assigns, always
  blocks, instances, nested loops.

---

## Module instances

SystemVerilog syntax, passed through unchanged:

```cerilog
Adder #(.WIDTH(8)) u_add (
    .a(count),
    .b(8'd1),
    .sum(next),
    .carry()          // explicitly unconnected
);

Register u_reg (clk, rst, next, count);   // positional connections
```

- Connections are all named or all positional, not mixed.
- When the instantiated module is in the same file, port and parameter names
  are checked, and signals connected to its outputs count as driven by the
  instance.
- Modules defined in other files are accepted without checks.

---

## Expressions

Operators, highest precedence first (the same as SystemVerilog):

| Operators | Meaning |
|---|---|
| `x[i]` `x[h:l]` `x[b +: w]` `x[b -: w]` | bit, part and indexed part select |
| `! ~ - + & \| ^ ~& ~\| ~^` (unary) | not, invert, negate, reductions |
| `**` | power |
| `* / %` | multiply, divide, modulo |
| `+ -` | add, subtract |
| `<< >> <<< >>>` | logical and arithmetic shifts |
| `< <= > >=` | compare |
| `== != === !==` | equality, case equality |
| `&` | bitwise and |
| `^ ~^ ^~` | xor, xnor |
| `\|` | bitwise or |
| `&&` | logical and |
| `\|\|` | logical or |
| `c ? a : b` | conditional |

Also:

- Concatenation `{a, b, 4'b0}` and replication `{4{a}}`.
- System functions such as `$clog2(DEPTH)`, `$signed(x)` and `$unsigned(x)`,
  emitted unchanged.
- Parentheses are kept exactly as written.

Numbers:

| Form | Example |
|---|---|
| decimal | `42`, `1_000` |
| sized / based | `8'hFF`, `4'b1010`, `12'o777`, `'d5`, `4'sb1010`, `4'b1x0z` |
| fill (all bits) | `'0`, `'1`, `'x`, `'z` |

---

## Targets

The source is the same for both targets. Pick one with the output extension
or `--target`:

```bash
cerilog counter.cel -o counter.sv        # SystemVerilog
cerilog counter.cel -o counter.v         # Verilog-2005 (e.g. Quartus Lite on a DE-10 Lite)
cerilog counter.cel --target v           # Verilog-2005 to stdout
```

### What changes

| Cerilog | SystemVerilog | Verilog-2005 |
|---|---|---|
| `logic` | `logic` | `wire` or `reg` (inferred) |
| `always()` | `always_comb` | `always @(*)` |
| `always(posedge clk)` | `always_ff @(posedge clk)` | `always @(posedge clk)` |
| `for (int i ...)` in always | `for (int i = ...)` | `integer i;` + `for (i = ...)` |
| `for (int i ...)` at module level | `for (genvar i = ...) begin : gen_i` | `genvar i;` + `generate ... endgenerate` |
| `'0` | `'0` | `0` |
| `'x` / `'z` | `'x` / `'z` | `'bx` / `'bz` |
| `y = '1` | `y = '1` | `y = {8{1'b1}}` (width taken from `y`) |

### wire vs reg

Verilog target only:

| Signal | Written by | Emits |
|---|---|---|
| `input` / `inout` port | (nothing) | `wire` |
| `output` port or signal | `assign`, an instance output, or nothing | `wire` |
| `output` port or signal | an always block | `reg` |

A signal written by both an always block and an assign/instance output is an
error in both targets.

### Target-specific errors

Almost everything is translated for Verilog. The one construct that can fail
is `'1`, because Verilog needs to know how wide "all ones" is:

```
fill.cel:2:20: error: '1 is not available when targeting Verilog-2005 (.v) here: its width can't be worked out
    assign y = a & '1;
                   ^
    hint: use '1 only as the whole right-hand side of an assignment to a declared signal, write the width explicitly (e.g. {8{1'b1}}), or use --target sv
```

`'1` works in Verilog when it is the whole right-hand side of an assignment
to a declared, non-memory signal (`y = '1;`, `assign y = '1;`,
`logic[3:0] m = '1;`).

A name used both as a generate loop variable and as an always-block loop
variable in the same module is also a Verilog-only error, since Verilog
declares both at module level.

### Source comments

Each output line that comes from a source line ends with
`// source: file.cel:N`, so tool errors in the `.sv`/`.v` lead back to the
`.cel` line. Turn them off with `--no-source-maps`.

---

## Diagnostics

Every message starts with `file:line:col: error|warning: message`, followed by
the source line, a caret, and sometimes a hint. Errors stop compilation;
warnings don't.

### Syntax errors

| Message | Cause |
|---|---|
| `expected ';' before ...` | missing semicolon (reported at the end of the statement) |
| `unexpected X, expected ...` | anything else the grammar doesn't allow |
| `unexpected end of file, missing '}'` | unclosed brace |
| `unexpected character '@'` | a character no token starts with |
| `always_ff needs a sensitivity list` | `always_ff()` |
| `always_comb takes no sensitivity list` | `always_comb(posedge clk)` |
| `sensitivity list entries need posedge or negedge` | `always(a, b)` |
| `genvar is only valid in module-level for loops` | `for (genvar i ...)` in an always block |
| `module-level for loops need int or genvar, not integer` | `for (integer i ...)` at module level |
| `for loop step updates 'j' but the loop variable is 'i'` | mismatched step |

### Semantic errors

| Message | Cause |
|---|---|
| `'x' is not declared` | unknown name (reported once per name per module) |
| `'x' is already declared in module 'M'` | duplicate port/signal/parameter/instance name |
| `module 'M' is defined twice` | two modules with one name |
| `loop variable 'i' is not declared` | `for (i = 0; ...)` without `int` |
| `cannot assign to input port 'a'` | writing an input |
| `cannot assign to parameter/localparam 'P'` | writing a constant |
| `cannot assign to loop variable 'i'` | assigning a loop counter outside its loop step |
| `left side of an assignment must be a signal, ...` | e.g. `assign $clog2(x) = 1;` |
| `'x' is driven by both an always block and an assign` | mixed drivers (also "an instance output") |
| `'x' has an initial value but is driven by an assign` | initial value on a continuously driven signal |
| `'u' is an instance name, not a signal` | instance name used in an expression |
| `module 'M' has no port 'p'` / `no parameter 'P'` | bad named connection to a module in the same file |
| `instance 'u' mixes named and positional port connections` | `M u (a, .b(c));` |
| `instance 'u' has N connections but module 'M' has K ports` | too many positional connections |

### Warnings

| Message | Cause |
|---|---|
| `blocking assignment '=' in a clocked always block` | `=` inside `always(posedge clk)` |
| `non-blocking assignment '<=' in a combinational always block` | `<=` inside `always()` |
| `'x' is written in more than one always block` | usually a bug; allowed if each block writes different bits |
