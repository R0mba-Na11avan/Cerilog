"""
Semantic analysis: runs between parsing and code generation.

For every module it
    - builds a symbol table (ports, signals, parameters, localparams, genvars,
      loop variables, instances) and reports duplicates and undeclared names
    - records what drives each signal (assign, always block, instance output,
      declaration initial value) and reports illegal mixes
    - sets driven_in_always on Port and LocalSignal nodes, which the Verilog
      emitter uses to choose reg over wire
    - warns about '=' in clocked blocks and '<=' in combinational blocks

Diagnostics are target independent: the same file gets the same errors and
warnings whether it is compiled to .sv or .v.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, Optional

from cerilog.ast import nodes
from cerilog.errors import Diagnostic


@dataclass
class _Symbol:
    name: str
    kind: str                       # port, signal, parameter, localparam, instance
    node: nodes.Node


@dataclass
class _Drivers:
    kinds: set[str] = field(default_factory=set)        # assign, always, instance, init
    always_blocks: set[int] = field(default_factory=set)
    first: dict[str, nodes.Node] = field(default_factory=dict)


ASSIGNABLE = ("port", "signal")


def analyze(source: nodes.SourceFile) -> list[Diagnostic]:
    """Check a parsed file and annotate it in place. Returns all diagnostics."""
    diags: list[Diagnostic] = []
    modules: dict[str, nodes.Module] = {}
    for module in source.modules:
        if module.name in modules:
            diags.append(_error(module, f"module '{module.name}' is defined twice"))
        modules[module.name] = module
    for module in source.modules:
        _ModuleChecker(module, modules, diags).run()
    return diags


def _error(node: nodes.Node, message: str, hint: Optional[str] = None) -> Diagnostic:
    return Diagnostic("error", message, node.line, node.col, hint)


def _warning(node: nodes.Node, message: str, hint: Optional[str] = None) -> Diagnostic:
    return Diagnostic("warning", message, node.line, node.col, hint)


def assign_targets(lhs: nodes.Node) -> Iterator[nodes.Identifier]:
    """The identifiers an assignment writes: x, x[3], {a, b[1:0]} -> x / x / a, b."""
    if isinstance(lhs, nodes.Identifier):
        yield lhs
    elif isinstance(lhs, nodes.Subscript):
        yield from assign_targets(lhs.target)
    elif isinstance(lhs, nodes.Paren):
        yield from assign_targets(lhs.inner)
    elif isinstance(lhs, nodes.Concat):
        for part in lhs.parts:
            yield from assign_targets(part)


def _is_assignable_shape(lhs: nodes.Node) -> bool:
    if isinstance(lhs, nodes.Identifier):
        return True
    if isinstance(lhs, nodes.Subscript):
        return _is_assignable_shape(lhs.target)
    if isinstance(lhs, nodes.Paren):
        return _is_assignable_shape(lhs.inner)
    if isinstance(lhs, nodes.Concat):
        return all(_is_assignable_shape(p) for p in lhs.parts)
    return False


class _ModuleChecker:
    def __init__(self, module: nodes.Module, modules: dict[str, nodes.Module], diags: list[Diagnostic]):
        self.module = module
        self.modules = modules
        self.diags = diags
        self.symbols: dict[str, _Symbol] = {}
        self.drivers: dict[str, _Drivers] = {}
        self.reported_undeclared: set[str] = set()
        self.scopes: list[set[str]] = []       # genvars and loop variables
        self.always_id = 0

    # ------------------------------------------------------------------ #

    def run(self):
        self._declare_all()
        for item in self.module.body:
            self._item(item)
        self._resolve_drivers()

    def _declare(self, name: str, kind: str, node: nodes.Node):
        if name in self.symbols:
            previous = self.symbols[name]
            self.diags.append(_error(
                node, f"'{name}' is already declared in module '{self.module.name}'",
                hint=f"first declared as a {previous.kind} on line {previous.node.line}",
            ))
            return
        self.symbols[name] = _Symbol(name, kind, node)

    def _declare_all(self):
        for p in self.module.parameters:
            self._declare(p.name, "parameter", p)
        for p in self.module.ports:
            self._declare(p.name, "port", p)
        self._declare_items(self.module.body)

    def _declare_items(self, items: list[nodes.Node]):
        for item in items:
            match item:
                case nodes.LocalSignal():
                    self._declare(item.name, "signal", item)
                case nodes.Localparam():
                    self._declare(item.name, "localparam", item)
                case nodes.Instance():
                    self._declare(item.name, "instance", item)
                case nodes.GenerateFor():
                    self._declare_items(item.body)

    # ------------------------------------------------------------------ #
    # Module items
    # ------------------------------------------------------------------ #

    def _item(self, item: nodes.Node):
        match item:
            case nodes.LocalSignal():
                for dim in item.unpacked:
                    self._expr(dim.high)
                    self._expr(dim.low)
                self._expr(item.width_high)
                self._expr(item.width_low)
                if item.init is not None:
                    self._expr(item.init)
                    self._drive(nodes.Identifier(name=item.name, line=item.line, col=item.col), "init")
            case nodes.Localparam():
                self._expr(item.value)
            case nodes.Assign():
                self._expr(item.rhs)
                self._assign_target(item.lhs, "assign")
            case nodes.Always():
                self.always_id += 1
                for sens in item.sensitivity:
                    self._expr(sens.signal)
                self._stmt(item.body, item)
            case nodes.GenerateFor():
                self._expr(item.init)
                self.scopes.append({item.var_name})
                self._expr(item.condition)
                self._expr(item.step.rhs)
                for child in item.body:
                    self._item(child)
                self.scopes.pop()
            case nodes.Instance():
                self._instance(item)

    def _instance(self, inst: nodes.Instance):
        for conn in inst.params + inst.connections:
            self._expr(conn.expr)

        for group, label in ((inst.params, "parameter"), (inst.connections, "port")):
            named = [c for c in group if c.name is not None]
            if named and len(named) != len(group):
                self.diags.append(_error(
                    inst, f"instance '{inst.name}' mixes named and positional {label} connections",
                ))

        target = self.modules.get(inst.module_name)
        if target is None:
            return  # defined in another file; nothing more to check

        param_names = {p.name for p in target.parameters}
        for conn in inst.params:
            if conn.name is not None and conn.name not in param_names:
                self.diags.append(_error(conn, f"module '{target.name}' has no parameter '{conn.name}'"))

        ports_by_name = {p.name: p for p in target.ports}
        if any(c.name is None for c in inst.connections) and len(inst.connections) > len(target.ports):
            self.diags.append(_error(
                inst, f"instance '{inst.name}' has {len(inst.connections)} connections "
                      f"but module '{target.name}' has {len(target.ports)} ports",
            ))
        for index, conn in enumerate(inst.connections):
            if conn.name is not None:
                port = ports_by_name.get(conn.name)
                if port is None:
                    self.diags.append(_error(conn, f"module '{target.name}' has no port '{conn.name}'"))
                    continue
            elif index < len(target.ports):
                port = target.ports[index]
            else:
                continue
            if port.direction == "output" and conn.expr is not None:
                self._assign_target(conn.expr, "instance")

    # ------------------------------------------------------------------ #
    # Statements
    # ------------------------------------------------------------------ #

    def _stmt(self, stmt: Optional[nodes.Node], always: nodes.Always):
        match stmt:
            case None:
                return
            case nodes.Block():
                for s in stmt.statements:
                    self._stmt(s, always)
            case nodes.If():
                self._expr(stmt.condition)
                self._stmt(stmt.then_branch, always)
                self._stmt(stmt.else_branch, always)
            case nodes.Case():
                self._expr(stmt.subject)
                for item in stmt.items:
                    for value in item.values:
                        self._expr(value)
                    self._stmt(item.body, always)
            case nodes.For():
                self._expr(stmt.init)
                if stmt.declares_var:
                    self.scopes.append({stmt.var_name})
                elif not self._is_declared(stmt.var_name):
                    self.diags.append(_error(
                        stmt, f"loop variable '{stmt.var_name}' is not declared",
                        hint=f"declare it in the loop: for (int {stmt.var_name} = ...; ...)",
                    ))
                    self.reported_undeclared.add(stmt.var_name)
                self._expr(stmt.condition)
                self._expr(stmt.step.rhs)
                self._stmt(stmt.body, always)
                if stmt.declares_var:
                    self.scopes.pop()
            case nodes.BlockingAssign():
                self._expr(stmt.rhs)
                if always.is_sequential and not self._is_loop_var(stmt.lhs):
                    self.diags.append(_warning(
                        stmt, "blocking assignment '=' in a clocked always block",
                        hint="flip-flops are normally written with '<='",
                    ))
                self._assign_target(stmt.lhs, "always")
            case nodes.NonBlockingAssign():
                self._expr(stmt.rhs)
                if not always.is_sequential:
                    self.diags.append(_warning(
                        stmt, "non-blocking assignment '<=' in a combinational always block",
                        hint="combinational logic is normally written with '='",
                    ))
                self._assign_target(stmt.lhs, "always")

    def _is_loop_var(self, lhs: nodes.Node) -> bool:
        return isinstance(lhs, nodes.Identifier) and any(lhs.name in s for s in self.scopes)

    # ------------------------------------------------------------------ #
    # Expressions and drivers
    # ------------------------------------------------------------------ #

    def _is_declared(self, name: str) -> bool:
        return name in self.symbols or any(name in s for s in self.scopes)

    def _expr(self, expr: Optional[nodes.Node]):
        match expr:
            case None | nodes.NumberLit():
                return
            case nodes.Identifier():
                if not self._is_declared(expr.name) and expr.name not in self.reported_undeclared:
                    self.reported_undeclared.add(expr.name)
                    self.diags.append(_error(expr, f"'{expr.name}' is not declared"))
                elif expr.name in self.symbols and self.symbols[expr.name].kind == "instance":
                    self.diags.append(_error(expr, f"'{expr.name}' is an instance name, not a signal"))
            case nodes.BinaryOp():
                self._expr(expr.left)
                self._expr(expr.right)
            case nodes.UnaryOp():
                self._expr(expr.operand)
            case nodes.Ternary():
                self._expr(expr.condition)
                self._expr(expr.if_true)
                self._expr(expr.if_false)
            case nodes.Paren():
                self._expr(expr.inner)
            case nodes.Subscript():
                self._expr(expr.target)
                self._expr(expr.high)
                self._expr(expr.low)
            case nodes.Concat():
                for part in expr.parts:
                    self._expr(part)
            case nodes.Replicate():
                self._expr(expr.count)
                for part in expr.parts:
                    self._expr(part)
            case nodes.Call():
                for arg in expr.args:
                    self._expr(arg)

    def _assign_target(self, lhs: nodes.Node, kind: str):
        if not _is_assignable_shape(lhs):
            self.diags.append(_error(lhs, "left side of an assignment must be a signal, "
                                          "a bit/part select of one, or a {concatenation} of those"))
            return
        # Subscript indexes are reads.
        self._expr_reads_in_target(lhs)
        for ident in assign_targets(lhs):
            self._drive(ident, kind)

    def _expr_reads_in_target(self, lhs: nodes.Node):
        if isinstance(lhs, nodes.Subscript):
            self._expr_reads_in_target(lhs.target)
            self._expr(lhs.high)
            self._expr(lhs.low)
        elif isinstance(lhs, nodes.Paren):
            self._expr_reads_in_target(lhs.inner)
        elif isinstance(lhs, nodes.Concat):
            for part in lhs.parts:
                self._expr_reads_in_target(part)

    def _drive(self, ident: nodes.Identifier, kind: str):
        name = ident.name
        if any(name in s for s in self.scopes):
            if kind != "always":
                self.diags.append(_error(ident, f"cannot assign to loop variable '{name}'"))
            return
        symbol = self.symbols.get(name)
        if symbol is None:
            if name not in self.reported_undeclared:
                self.reported_undeclared.add(name)
                self.diags.append(_error(ident, f"'{name}' is not declared"))
            return
        if symbol.kind not in ASSIGNABLE:
            self.diags.append(_error(ident, f"cannot assign to {symbol.kind} '{name}'"))
            return
        if symbol.kind == "port" and symbol.node.direction == "input":
            self.diags.append(_error(ident, f"cannot assign to input port '{name}'"))
            return

        drivers = self.drivers.setdefault(name, _Drivers())
        drivers.kinds.add(kind)
        drivers.first.setdefault(kind, ident)
        if kind == "always":
            drivers.always_blocks.add(self.always_id)

    def _resolve_drivers(self):
        for name, drivers in self.drivers.items():
            symbol = self.symbols[name]
            kinds = drivers.kinds
            continuous = kinds & {"assign", "instance"}

            if "always" in kinds and continuous:
                other = "an assign" if "assign" in kinds else "an instance output"
                self.diags.append(_error(
                    drivers.first["always"],
                    f"'{name}' is driven by both an always block and {other}",
                    hint="drive each signal from one place: either always blocks or assign/instance outputs",
                ))
            if "init" in kinds and continuous:
                self.diags.append(_error(
                    symbol.node, f"'{name}' has an initial value but is driven by "
                                 f"{'an assign' if 'assign' in kinds else 'an instance output'}",
                    hint="initial values only make sense for signals written in always blocks",
                ))
            if len(drivers.always_blocks) > 1:
                self.diags.append(_warning(
                    drivers.first["always"], f"'{name}' is written in more than one always block",
                    hint="most synthesis tools reject this unless each block writes different bits",
                ))
            if "always" in kinds:
                symbol.node.driven_in_always = True
