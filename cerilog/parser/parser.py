"""
Cerilog parser: source text -> AST (cerilog.ast.nodes).

Lark parses with the LALR grammar in grammar.lark, then _ToAst turns Lark's
parse tree into AST nodes. Lark exceptions are translated into ParseError /
LexError with readable messages.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from lark import Lark, Token, Transformer, v_args
from lark.exceptions import UnexpectedCharacters, UnexpectedEOF, UnexpectedToken, VisitError

from cerilog.ast import nodes
from cerilog.errors import CerilogError

GRAMMAR_PATH = Path(__file__).parent / "grammar.lark"


class LexError(CerilogError):
    """Raised on a character that can't start any token."""


class ParseError(CerilogError):
    """Raised on a syntax error."""


@lru_cache(maxsize=None)
def build_lark(lexer: str = "contextual") -> Lark:
    return Lark(
        GRAMMAR_PATH.read_text(encoding="utf-8"),
        parser="lalr",
        lexer=lexer,
        propagate_positions=True,
    )


# --------------------------------------------------------------------------- #
# Error messages
# --------------------------------------------------------------------------- #

_TERMINAL_NAMES = {
    "IDENT": "an identifier",
    "NUMBER": "a number",
    "SYSNAME": "a system function like $clog2",
    "$END": "end of file",
}


def describe_terminal(name: str, lark: Lark) -> str:
    """Human name for a grammar terminal: SEMICOLON -> ';', IDENT -> an identifier."""
    if name in _TERMINAL_NAMES:
        return _TERMINAL_NAMES[name]
    try:
        pattern = lark.get_terminal(name).pattern
    except KeyError:
        return name
    if pattern.type == "str":
        return f"'{pattern.value}'"
    return name.lower().replace("_", " ")


def _describe_token(token: Token) -> str:
    if token.type == "$END":
        return "end of file"
    if token.type == "IDENT":
        return f"identifier '{token}'"
    if token.type == "NUMBER":
        return f"number '{token}'"
    return f"'{token}'"


def _expected_list(expected: set[str], lark: Lark) -> str:
    names = sorted({describe_terminal(e, lark) for e in expected})
    if len(names) > 6:
        names = names[:6] + ["..."]
    return ", ".join(names)


# --------------------------------------------------------------------------- #
# Parse tree -> AST
# --------------------------------------------------------------------------- #

def _at(meta, node: nodes.Node) -> nodes.Node:
    if not meta.empty:
        node.line, node.col = meta.line, meta.column
    return node


def _tok_at(tok: Token, node: nodes.Node) -> nodes.Node:
    node.line, node.col = tok.line, tok.column
    return node


class _Tagged:
    """Intermediate value passed between transformer callbacks."""

    def __init__(self, tag: str, *values, meta=None):
        self.tag = tag
        self.values = values
        self.meta = meta


def _tagged(children, tag):
    return [c for c in children if isinstance(c, _Tagged) and c.tag == tag]


def _tokens(children, type_):
    return [c for c in children if isinstance(c, Token) and c.type == type_]


@v_args(meta=True)
class _ToAst(Transformer):
    # ----------------------------------------------------------- modules

    def start(self, meta, children):
        return _at(meta, nodes.SourceFile(modules=list(children)))

    def module(self, meta, children):
        name = children[0]
        params = _tagged(children, "params")
        ports = _tagged(children, "ports")
        body = []
        for child in children[1:]:
            if isinstance(child, _Tagged):
                continue
            body.extend(child if isinstance(child, list) else [child])
        return _at(meta, nodes.Module(
            name=str(name),
            parameters=list(params[0].values[0]) if params else [],
            ports=list(ports[0].values[0]) if ports else [],
            body=body,
        ))

    def param_list(self, meta, children):
        return _Tagged("params", list(children))

    def param(self, meta, children):
        ident, value = children[-2], children[-1]
        return _tok_at(ident, nodes.Parameter(name=str(ident), default=value))

    def port_list(self, meta, children):
        return _Tagged("ports", list(children))

    def port(self, meta, children):
        direction = children[0]
        rng = _tagged(children, "range")
        name = children[-1]
        hi, lo = rng[0].values if rng else (None, None)
        return _at(meta, nodes.Port(
            direction=direction,
            signed=bool(_tokens(children, "SIGNED")),
            width_high=hi,
            width_low=lo,
            name=str(name),
        ))

    def direction(self, meta, children):
        return str(children[0])

    def range(self, meta, children):
        return _Tagged("range", children[0], children[1])

    def signal_decl(self, meta, children):
        signed = bool(_tokens(children, "SIGNED"))
        rng = _tagged(children, "range")
        hi, lo = rng[0].values if rng else (None, None)
        signals = []
        for item in _tagged(children, "decl_item"):
            ident, dims, init = item.values
            signals.append(_tok_at(ident, nodes.LocalSignal(
                signed=signed, width_high=hi, width_low=lo, name=str(ident),
                unpacked=dims, init=init,
            )))
        return signals

    def decl_item(self, meta, children):
        ident = children[0]
        dims = [c for c in children[1:] if isinstance(c, nodes.UnpackedDim)]
        init = next((c for c in children[1:] if isinstance(c, nodes.Node)
                     and not isinstance(c, nodes.UnpackedDim)), None)
        return _Tagged("decl_item", ident, dims, init)

    def unpacked_dim(self, meta, children):
        low = children[1] if len(children) > 1 else None
        return _at(meta, nodes.UnpackedDim(high=children[0], low=low))

    def localparam_decl(self, meta, children):
        return list(children)

    def localparam_item(self, meta, children):
        ident, value = children
        return _tok_at(ident, nodes.Localparam(name=str(ident), value=value))

    def assign(self, meta, children):
        return _at(meta, nodes.Assign(lhs=children[0], rhs=children[1]))

    def always(self, meta, children):
        keyword = children[0]
        sens = _tagged(children, "sensitivity")
        body = children[-1]
        items = sens[0].values[0] if sens else []

        if keyword == "always_ff" and not items:
            raise ParseError(
                "always_ff needs a sensitivity list", keyword.line, keyword.column,
                hint="write always_ff(posedge clk) { ... }, or always() { ... } for combinational logic",
            )
        if keyword == "always_comb" and items:
            raise ParseError(
                "always_comb takes no sensitivity list", keyword.line, keyword.column,
                hint="write always_comb() { ... }, or always(posedge clk) { ... } for flip-flops",
            )

        if not isinstance(body, nodes.Block):
            body = nodes.Block(statements=[body] if body is not None else [],
                               line=getattr(body, "line", 0), col=getattr(body, "col", 0))
        return _tok_at(keyword, nodes.Always(sensitivity=items, body=body))

    def sensitivity(self, meta, children):
        # "*" produces no children: same as an empty list (combinational).
        return _Tagged("sensitivity", list(children))

    def sens_item(self, meta, children):
        if len(children) == 1:
            signal = children[0]
            raise ParseError(
                "sensitivity list entries need posedge or negedge",
                signal.line, signal.col,
                hint="use always() { ... } for combinational logic; it emits always_comb / always @(*)",
            )
        edge, signal = children
        return _tok_at(edge, nodes.Sensitivity(edge=str(edge), signal=signal))

    def gen_for(self, meta, children):
        init, cond, step, body = children
        loop_type, var, value = init.values
        if loop_type is not None and loop_type == "integer":
            raise ParseError("module-level for loops need int or genvar, not integer",
                             loop_type.line, loop_type.column)
        _check_step_var(var, step)
        return _at(meta, nodes.GenerateFor(
            var_name=str(var),
            init=value,
            condition=cond,
            step=step,
            body=body,
        ))

    def gen_body(self, meta, children):
        body = []
        for child in children:
            body.extend(child if isinstance(child, list) else [child])
        return body

    def instance(self, meta, children):
        module_name = children[0]
        params = _tagged(children, "param_override")
        name = [c for c in children if isinstance(c, Token) and c.type == "IDENT"][1]
        conns = [c for c in children if isinstance(c, nodes.Connection)]
        return _tok_at(module_name, nodes.Instance(
            module_name=str(module_name),
            name=str(name),
            params=list(params[0].values[0]) if params else [],
            connections=conns,
        ))

    def param_override(self, meta, children):
        return _Tagged("param_override", list(children))

    def named_connection(self, meta, children):
        ident = children[0]
        expr = children[1] if len(children) > 1 else None
        return _tok_at(ident, nodes.Connection(name=str(ident), expr=expr))

    def positional_connection(self, meta, children):
        expr = children[0]
        return nodes.Connection(name=None, expr=expr, line=expr.line, col=expr.col)

    # ----------------------------------------------------------- statements

    def block(self, meta, children):
        return _at(meta, nodes.Block(statements=[c for c in children if c is not None]))

    def empty_stmt(self, meta, children):
        return None

    def if_stmt(self, meta, children):
        cond, then = children[0], children[1]
        other = children[2] if len(children) > 2 else None
        return _at(meta, nodes.If(condition=cond, then_branch=_stmt(then),
                                  else_branch=_stmt(other) if len(children) > 2 else None))

    def case_stmt(self, meta, children):
        kind, subject, *items = children
        flat = []
        for item in items:
            flat.extend(item)
        return _at(meta, nodes.Case(kind=str(kind), subject=subject, items=flat))

    def case_item(self, meta, children):
        *labels, body = children
        body = _stmt(body)
        values = []
        has_default = False
        for label in labels:
            if label.tag == "default":
                has_default = True
            else:
                values.extend(label.values)
        items = []
        if values:
            items.append(_at(meta, nodes.CaseItem(values=values, body=body)))
        if has_default:
            items.append(_at(meta, nodes.CaseItem(values=[], body=body)))
        return items

    def case_label(self, meta, children):
        return _Tagged("label", *children)

    def default_label(self, meta, children):
        return _Tagged("default")

    def for_stmt(self, meta, children):
        init, cond, step, body = children
        loop_type, var, value = init.values
        if loop_type is not None and loop_type == "genvar":
            raise ParseError("genvar is only valid in module-level for loops",
                             loop_type.line, loop_type.column,
                             hint="use int inside always blocks")
        _check_step_var(var, step)
        return _at(meta, nodes.For(
            var_name=str(var),
            declares_var=loop_type is not None,
            init=value,
            condition=cond,
            step=step,
            body=_stmt(body),
        ))

    def for_init(self, meta, children):
        loop_type = _tokens(children, "LOOP_TYPE")
        idents = _tokens(children, "IDENT")
        return _Tagged("for_init", loop_type[0] if loop_type else None, idents[0], children[-1])

    def for_step(self, meta, children):
        var = children[0]
        op = str(children[1])
        target = _tok_at(var, nodes.Identifier(name=str(var)))
        if op in ("++", "--"):
            one = _tok_at(var, nodes.NumberLit(raw="1"))
            rhs = nodes.BinaryOp(op=op[0], left=_tok_at(var, nodes.Identifier(name=str(var))),
                                 right=one, line=var.line, col=var.column)
        elif op == "=":
            rhs = children[2]
        else:
            rhs = nodes.BinaryOp(op=op[0], left=_tok_at(var, nodes.Identifier(name=str(var))),
                                 right=children[2], line=var.line, col=var.column)
        return _tok_at(var, nodes.BlockingAssign(lhs=target, rhs=rhs))

    def blocking_assign(self, meta, children):
        return _at(meta, nodes.BlockingAssign(lhs=children[0], rhs=children[1]))

    def nonblocking_assign(self, meta, children):
        return _at(meta, nodes.NonBlockingAssign(lhs=children[0], rhs=children[1]))

    # ----------------------------------------------------------- expressions

    def ident(self, meta, children):
        return _tok_at(children[0], nodes.Identifier(name=str(children[0])))

    def number(self, meta, children):
        return _tok_at(children[0], nodes.NumberLit(raw=str(children[0])))

    def paren(self, meta, children):
        return _at(meta, nodes.Paren(inner=children[0]))

    def binop(self, meta, children):
        left, op, right = children
        return _at(meta, nodes.BinaryOp(op=op, left=left, right=right))

    def unop(self, meta, children):
        op, operand = children
        return _at(meta, nodes.UnaryOp(op=op, operand=operand))

    def ternary(self, meta, children):
        cond, a, b = children
        return _at(meta, nodes.Ternary(condition=cond, if_true=a, if_false=b))

    def index(self, meta, children):
        return _at(meta, nodes.Subscript(target=children[0], high=children[1]))

    def part_select(self, meta, children):
        return _at(meta, nodes.Subscript(target=children[0], high=children[1],
                                         low=children[2], op=":"))

    def indexed_select(self, meta, children):
        target, base, op, width = children
        return _at(meta, nodes.Subscript(target=target, high=base, low=width, op=str(op)))

    def call(self, meta, children):
        name, *args = children
        return _tok_at(name, nodes.Call(name=str(name), args=list(args)))

    def concat(self, meta, children):
        return _at(meta, nodes.Concat(parts=list(children)))

    def replicate(self, meta, children):
        count, *parts = children
        return _at(meta, nodes.Replicate(count=count, parts=list(parts)))


def _make_op_callback(self, meta, children):
    return str(children[0])


for _op_rule in ("lor_op", "land_op", "bor_op", "bxor_op", "band_op", "eq_op", "rel_op",
                 "shift_op", "add_op", "mul_op", "pow_op", "unary_op"):
    setattr(_ToAst, _op_rule, v_args(meta=True)(_make_op_callback))


def _stmt(node):
    """Empty statements (';') parse to None; represent them as empty blocks."""
    return node if node is not None else nodes.Block()


def _check_step_var(var: Token, step: nodes.BlockingAssign):
    if step.lhs.name != str(var):
        raise ParseError(
            f"for loop step updates '{step.lhs.name}' but the loop variable is '{var}'",
            step.line, step.col,
        )


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

class Parser:
    """
    Parses Cerilog source into an AST.

        source_file = Parser().parse(text)
    """

    def __init__(self):
        self._lark = build_lark()

    def parse(self, source: str) -> nodes.SourceFile:
        try:
            tree = self._lark.parse(source)
        except UnexpectedCharacters as e:
            raise LexError(f"unexpected character {source[e.pos_in_stream]!r}", e.line, e.column) from None
        except UnexpectedEOF as e:
            raise ParseError("unexpected end of file", *_eof_position(source)) from None
        except UnexpectedToken as e:
            raise self._unexpected_token(e, source) from None

        try:
            return _ToAst().transform(tree)
        except VisitError as e:
            if isinstance(e.orig_exc, CerilogError):
                raise e.orig_exc from None
            raise

    def _unexpected_token(self, e: UnexpectedToken, source: str) -> ParseError:
        expected = set(e.expected or ())
        token = e.token

        if token.type == "$END":
            line, col = _eof_position(source)
            if "RBRACE" in expected:
                return ParseError("unexpected end of file, missing '}'", line, col)
            return ParseError(f"unexpected end of file, expected {_expected_list(expected, self._lark)}",
                              line, col)

        if "SEMICOLON" in expected:
            prev = _previous_token_end(source, token)
            if prev is not None:
                return ParseError(f"expected ';' before {_describe_token(token)}", *prev)

        return ParseError(
            f"unexpected {_describe_token(token)}, expected {_expected_list(expected, self._lark)}",
            token.line, token.column,
        )


def _eof_position(source: str) -> tuple[int, int]:
    lines = source.rstrip().splitlines() or [""]
    return len(lines), len(lines[-1]) + 1


def _previous_token_end(source: str, token: Token):
    """
    Position just after the last non-blank, non-comment text before `token`,
    when that text is on an earlier line. A missing ';' is reported there,
    at the end of the statement, rather than at the start of the next line.
    """
    before = source[: token.start_pos]
    lines = before.splitlines()
    for idx in range(len(lines) - 1, -1, -1):
        text = lines[idx].split("//")[0].rstrip()
        if text:
            line_no = idx + 1
            if line_no == token.line:
                return None
            return line_no, len(text) + 1
    return None
