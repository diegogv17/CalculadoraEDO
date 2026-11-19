"""Analizador de la ecuación escrita por el usuario.

Sintaxis aceptada (ver README):  y'  y''  y'''  dy/dx  d2y/dx2  dx  dy
  ^ o ** para potencias, * explícito (la multiplicación implícita también
  funciona), exp, sin, cos, tan, ln, log, sqrt, pi, e ...

Resultado: un `ParsedODE` con la ecuación normalizada:
  * primer orden:  M dx + N dy = 0   y   dy/dx = f(x, y)
  * orden superior lineal:  a_n(x) y^(n) + ... + a_0(x) y = g(x)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor, implicit_multiplication_application, parse_expr,
    standard_transformations,
)

from .report import ParseError, Unsupported

x = sp.Symbol("x")
y = sp.Symbol("y")
MAX_ORDER = 6
# D[k] representa y^(k)
D = [y] + [sp.Symbol(f"y_{k}") for k in range(1, MAX_ORDER + 1)]
_DX = sp.Symbol("DXSYM")
_DY = sp.Symbol("DYSYM")

_LOCAL = {
    "x": x, "y": y, "DXSYM": _DX, "DYSYM": _DY,
    "e": sp.E, "E": sp.E, "pi": sp.pi,
    "exp": sp.exp, "ln": sp.log, "log": sp.log, "sqrt": sp.sqrt, "abs": sp.Abs,
    "sin": sp.sin, "cos": sp.cos, "tan": sp.tan, "cot": sp.cot,
    "sec": sp.sec, "csc": sp.csc, "sen": sp.sin, "tg": sp.tan,
    "sinh": sp.sinh, "cosh": sp.cosh, "tanh": sp.tanh,
    "asin": sp.asin, "acos": sp.acos, "atan": sp.atan,
    "arcsin": sp.asin, "arccos": sp.acos, "arctan": sp.atan,
}
_LOCAL.update({f"y_{k}": D[k] for k in range(1, MAX_ORDER + 1)})
_TRANS = standard_transformations + (implicit_multiplication_application, convert_xor)


@dataclass
class ParsedODE:
    text: str
    order: int
    expr: sp.Expr                 # lado izquierdo - lado derecho
    M: sp.Expr = None             # primer orden: M dx + N dy = 0
    N: sp.Expr = None
    f: sp.Expr = None             # dy/dx = f(x, y)
    coeffs: list = field(default_factory=list)   # a_0 .. a_n (orden superior)
    g: sp.Expr = None             # término independiente (orden superior)


def _normalize(text: str) -> str:
    s = text.strip()
    for a, b in (("′", "'"), ("’", "'"), ("−", "-"), ("×", "*"), ("·", "*"), ("²", "^2"), ("³", "^3")):
        s = s.replace(a, b)
    if not s:
        raise ParseError("Escriba una ecuación diferencial.")
    if re.search(r"[^0-9A-Za-z_+\-*/^().,'\s=]", s) or "__" in s:
        raise ParseError("La ecuación contiene caracteres no permitidos. "
                         "Use solo letras, números y + - * / ^ ( ) ' =")
    if re.search(r"dx\s*/\s*dy", s):
        raise ParseError("Escriba la ecuación como dy/dx o y' (la variable independiente es x).")
    s = re.sub(r"(y'*)\(\s*x\s*\)", r"\1", s)                        # y(x) -> y
    s = re.sub(r"d\^?\(?(\d)\)?y\s*/\s*dx\^?\(?\1\)?",
               lambda m: "y" + "'" * int(m.group(1)), s)            # d2y/dx2 -> y''
    s = re.sub(r"dy\s*/\s*dx", "y'", s)                              # dy/dx -> y'
    s = re.sub(r"(?<![A-Za-z_])y('+)",
               lambda m: f"y_{len(m.group(1))}", s)                  # y'' -> y_2
    s = re.sub(r"(?<![A-Za-z_])dx(?![A-Za-z_0-9])", " DXSYM ", s)
    s = re.sub(r"(?<![A-Za-z_])dy(?![A-Za-z_0-9])", " DYSYM ", s)
    return s


def _parse_side(s: str) -> sp.Expr:
    if not s.strip():
        raise ParseError("Falta una expresión a un lado del signo '='.")
    try:
        e = parse_expr(s, local_dict=_LOCAL, transformations=_TRANS, evaluate=True)
    except Exception as exc:  # sympy lanza muchos tipos distintos
        raise ParseError("Error de sintaxis: revise paréntesis, operadores y el uso de '*'. "
                         f"({type(exc).__name__})") from None
    if not isinstance(e, sp.Expr):
        raise ParseError("No se pudo interpretar la expresión como una fórmula matemática.")
    return e


def parse(text: str) -> ParsedODE:
    s = _normalize(text)
    if s.count("=") > 1:
        raise ParseError("Solo puede haber un signo '=' en la ecuación.")
    if "=" in s:
        left, right = s.split("=")
        expr = _parse_side(left) - _parse_side(right)
    else:
        expr = _parse_side(s)
    if expr.has(sp.Float):
        expr = sp.nsimplify(expr, rational=True)
    expr = sp.expand(expr) if expr.has(_DX, _DY) else expr

    if expr.has(sp.zoo, sp.nan, sp.oo, -sp.oo):
        raise ParseError("La ecuación contiene una división por cero o un valor indefinido.")
    allowed = {x, y, _DX, _DY, *D}
    extra = expr.free_symbols - allowed
    if extra:
        names = ", ".join(sorted(str(v) for v in extra))
        raise ParseError(f"Símbolo(s) no reconocido(s): {names}. "
                         "La variable independiente es x y la función es y.")

    orders = [k for k in range(1, MAX_ORDER + 1) if expr.has(D[k])]
    uses_diff = expr.has(_DX) or expr.has(_DY)
    if uses_diff and orders:
        raise ParseError("No mezcle la notación diferencial (dx, dy) con derivadas (y', y'').")
    if not uses_diff and not orders:
        raise ParseError("La ecuación no contiene derivadas: use y', y'' o dy/dx, o la forma M dx + N dy = 0.")

    p = ParsedODE(text=text, order=1, expr=expr)
    if uses_diff:
        poly = sp.Poly(expr, _DX, _DY)
        if poly.total_degree() != 1 or poly.coeff_monomial(1) != 0:
            raise ParseError("La forma diferencial debe ser M(x,y) dx + N(x,y) dy = 0.")
        p.M, p.N = poly.coeff_monomial(_DX), poly.coeff_monomial(_DY)
        if p.N == 0:
            raise ParseError("El coeficiente de dy es cero: no es una EDO en y(x).")
        p.f = sp.simplify(-p.M / p.N)
        return p

    p.order = orders[-1]
    if p.order == 1:
        sols = sp.solve(expr, D[1])
        if len(sols) != 1:
            raise Unsupported("No es posible despejar y' de forma única en esta ecuación.")
        p.f = sp.simplify(sols[0])
        num, den = sp.fraction(sp.together(p.f))
        p.M, p.N = sp.expand(-num), sp.expand(den)
        return p

    # Orden superior: debe ser lineal en y, y', ..., y^(n)
    p.coeffs = [sp.simplify(sp.diff(expr, D[k])) for k in range(p.order + 1)]
    p.g = sp.simplify(-expr.subs({D[k]: 0 for k in range(p.order + 1)}))
    rebuilt = sum(c * D[k] for k, c in enumerate(p.coeffs)) - p.g
    if any(c.has(*D) for c in p.coeffs) or p.g.has(*D) or sp.simplify(expr - rebuilt) != 0:
        raise Unsupported("La ecuación de orden superior debe ser LINEAL en y, y', y'', ...")
    if p.coeffs[-1] == 0:
        raise ParseError("Ecuación mal formada.")
    return p
