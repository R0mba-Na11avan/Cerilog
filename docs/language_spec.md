# Cerilog Language Specification

> This document is a living draft. It evolves as the transpiler is built.

---

## File Extension

`.cel`

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

---

## Types

Cerilog uses `logic` as the universal signal type. The transpiler emits `logic` in SystemVerilog, which handles both combinational and sequential contexts. You don't choose between `wire` and `reg`.

```cerilog
logic       single_bit;
logic[7:0]  byte_signal;
logic[31:0] word_signal;
```

---

## Always Blocks

### Sequential (clocked)

```cerilog
always(posedge clk) {
    // ...
}

always_ff(posedge clk, posedge rst) {
    // async reset
}
```

### Combinational

```cerilog
always() {
    // ...
}
```

---

## Continuous Assignment

```cerilog
assign out = a & b;
```

Identical to Verilog — no change needed here.

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

---

## Comments

```cerilog
// Single line comment

/* Multi-line
   comment */
```

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

---

## Case

```cerilog
case (sel) {
    2'b00: out = a;
    2'b01: out = b;
    default: out = 0;
}
```

---

## For Loop (generate)

```cerilog
for (int i = 0; i < 8; i++) {
    assign out[i] = in[i] ^ mask[i];
}
```

---

## Emitted SystemVerilog

Cerilog emits clean, readable SystemVerilog. Each emitted line includes a source comment for debugging:

```systemverilog
module Counter( // source: counter.cel:1
    input logic clk,
    output logic[7:0] count
);
    always_ff @(posedge clk) begin // source: counter.cel:4
        count <= count + 1; // source: counter.cel:5
    end
endmodule
