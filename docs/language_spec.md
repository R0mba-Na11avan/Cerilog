# Cerilog Language Specification

> This document is a living draft. It evolves as the transpiler is built.

---

## File Extension

`.cel`

---

## Compilation Targets

Cerilog can transpile to either **SystemVerilog** (`.sv`) or **plain Verilog** (`.v`). The target is selected via the CLI:

```bash
# SystemVerilog (default)
python -m cerilog counter.cel -o counter.sv

# Plain Verilog — for toolchains that don't accept .sv (e.g. Quartus on DE-10 Lite)
python -m cerilog counter.cel -o counter.v

# Explicit flag (overrides extension inference)
python -m cerilog counter.cel -o out.v --target verilog
python -m cerilog counter.cel -o out.sv --target systemverilog
```

The output file extension (`.sv` vs `.v`) is enough — you don't need the flag in normal use.

### What Changes Between Targets

The Cerilog source is identical regardless of target. Only the emitted output differs:

| Cerilog | SystemVerilog | Verilog |
|---|---|---|
| `logic` (port or signal) | `logic` | `wire` or `reg` (inferred) |
| `always()` — no args | `always_comb` | `always @(*)` |
| `always(posedge clk)` | `always_ff @(posedge clk)` | `always @(posedge clk)` |
| `int i` (for loop) | `int i` | `integer i` |
| `#(WIDTH = 8)` | `#(WIDTH = 8)` | `#(parameter WIDTH = 8)` |
| `begin` / `end` / `endmodule` | same | same |

### wire vs reg Inference (Verilog target only)

In the Verilog target, the transpiler automatically infers `wire` vs `reg` so you never have to think about it:

| Signal | Driven by | Emits as |
|---|---|---|
| `input` port | — | `wire` (always) |
| `output` port or local signal | `assign` | `wire` |
| `output` port or local signal | `always()` block | `reg` |

---

## Module Declaration

Ports are declared inline in the module header. No separate `input`/`output` declarations needed.

```cerilog
module ModuleName(port_list) {
    // body
}
```

### Port List

```cerilog
module Adder(
    input  logic        clk,
    input  logic        rst,
    input  logic[7:0]   a,
    input  logic[7:0]   b,
    output logic[8:0]   sum
) {

}
```

**SystemVerilog output:**
```systemverilog
module Adder(
    input  logic       clk,
    input  logic       rst,
    input  logic[7:0]  a,
    input  logic[7:0]  b,
    output logic[8:0]  sum
);
endmodule
```

**Verilog output:**
```verilog
module Adder(
    input  wire       clk,
    input  wire       rst,
    input  wire[7:0]  a,
    input  wire[7:0]  b,
    output wire[8:0]  sum      // wire because driven by assign
);
endmodule
```

---

## Types

Cerilog uses `logic` as the universal signal type in source. You never write `wire` or `reg` — the transpiler handles that for the Verilog target automatically.

```cerilog
logic       single_bit;
logic[7:0]  byte_signal;
logic[31:0] word_signal;
```

---

## Always Blocks

Cerilog uses a single unified `always()` block for both sequential and combinational logic. The transpiler infers the correct construct based on the argument list.

### Combinational (no arguments)

```cerilog
always() {
    // ...
}
```

| Target | Emits |
|---|---|
| SystemVerilog | `always_comb` |
| Verilog | `always @(*)` |

### Sequential (clocked)

```cerilog
always(posedge clk) {
    // ...
}

always(posedge clk, posedge rst) {
    // async reset
}
```

| Target | Emits |
|---|---|
| SystemVerilog | `always_ff @(posedge clk)` |
| Verilog | `always @(posedge clk)` |

---

## Continuous Assignment

```cerilog
assign out = a & b;
```

Identical in both targets — no change needed.

---

## Parameters

```cerilog
module FIFO #(WIDTH = 8, DEPTH = 16) (
    input  logic            clk,
    input  logic[WIDTH-1:0] data_in,
    output logic[WIDTH-1:0] data_out
) {

}
```

**SystemVerilog output:** `#(WIDTH = 8, DEPTH = 16)`
**Verilog output:** `#(parameter WIDTH = 8, parameter DEPTH = 16)`

---

## Comments

```cerilog
// Single line comment

/* Multi-line
   comment */
```

Identical in both targets.

---

## If / Else

```cerilog
if (condition) {
    // ...
} else if (other) {
    // ...
} else {
    // ...
}
```

Emits `begin`/`end` blocks in both targets.

---

## Case

### Basic

```cerilog
case (sel) {
    2'b00: out = a;
    2'b01: out = b;
    default: out = 0;
}
```

### Fallthrough

Stack multiple case values with no body between them — the first one with a body executes for all of them. Same as C++ fallthrough.

```cerilog
case (opcode) {
    4'h0:
    4'h1:
    4'h2: result = a + b;   // 0, 1, and 2 all fall through to here

    4'h3:
    4'h4: result = a - b;   // 3 and 4 fall through to here

    default: result = 0;
}
```

Emits as comma-separated values in both targets:

```verilog
case (opcode)
    4'h0, 4'h1, 4'h2: result = a + b;
    4'h3, 4'h4:        result = a - b;
    default:           result = 0;
endcase
```

> **Note:** Neither Verilog nor SystemVerilog has true C++-style fallthrough — both use comma-separated values instead. Cerilog's stacked syntax is cleaner to write and compiles down to the correct form automatically in both targets.

---

## For Loop (generate)

```cerilog
for (int i = 0; i < 8; i++) {
    assign out[i] = in[i] ^ mask[i];
}
```

| Target | Loop variable emits as |
|---|---|
| SystemVerilog | `int i` |
| Verilog | `integer i` |

---

## Emitted Output Examples

### SystemVerilog target (`counter.sv`)

```systemverilog
module Counter(                        // source: counter.cel:1
    input  logic       clk,
    output logic[7:0]  count
);
    always_ff @(posedge clk) begin     // source: counter.cel:4
        count <= count + 1;            // source: counter.cel:5
    end
endmodule
```

### Verilog target (`counter.v`)

```verilog
module Counter(                        // source: counter.cel:1
    input  wire       clk,
    output reg[7:0]   count            // reg — driven inside always block
);
    always @(posedge clk) begin        // source: counter.cel:4
        count <= count + 1;            // source: counter.cel:5
    end
endmodule
```