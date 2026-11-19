"""Catálogo de métodos, clasificación automática y punto de entrada `solve`.

Esta capa es la lógica de clasificación propia: decide qué método aplica
(modo automático) o valida que la ecuación cumpla el método elegido (modo manual).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from . import first_order as fo
from . import higher_order as ho
from .parser import ParsedODE, parse
from .report import EdoError, NotApplicable, Solution, Unsupported


@dataclass(frozen=True)
class Method:
    key: str
    label: str
    block: str           # "A" o "B"
    func: Callable[[ParsedODE], Solution]
    example: str
    hint: str


METHODS = [
    Method("separable", "A · Variables separables", "A", fo.separable,
           "dy/dx = x*y",
           "Forma dy/dx = f(x,y) con f = g(x)·h(y)  (o M dx + N dy = 0)."),
    Method("homogeneous", "A · Homogéneas (y = ux)", "A", fo.homogeneous,
           "(x^2 + y^2) dx - x*y dy = 0",
           "M dx + N dy = 0 con M y N homogéneas del mismo grado (o y' = f(y/x))."),
    Method("exact", "A · Exactas", "A", fo.exact,
           "(2*x*y + 3) dx + (x^2 - 1) dy = 0",
           "M dx + N dy = 0 con ∂M/∂y = ∂N/∂x."),
    Method("integrating_factor", "A · Reducibles a exactas (factor integrante)", "A", fo.integrating_factor,
           "(x^2 + y^2 + x) dx + x*y dy = 0",
           "M dx + N dy = 0 NO exacta, con μ(x) o μ(y)."),
    Method("linear", "A · Lineales de primer orden", "A", fo.linear,
           "y' + y/x = x^2",
           "Forma y' + P(x)·y = Q(x)."),
    Method("bernoulli", "A · Bernoulli (u = y^(1-n))", "A", fo.bernoulli,
           "y' + y/x = x*y^2",
           "Forma y' + P(x)·y = Q(x)·y^n, con n ≠ 0, 1."),
    Method("cc_hom", "B · Coef. constantes homogénea", "B", ho.cc_homogeneous,
           "y'' - 3*y' + 2*y = 0",
           "a_n y⁽ⁿ⁾ + ... + a_1 y' + a_0 y = 0 con a_k constantes (use y', y'', y''')."),
    Method("cc_undetermined", "B · No homogénea: coef. indeterminados", "B", ho.cc_undetermined,
           "y'' - 3*y' + 2*y = exp(x) + x",
           "Coeficientes constantes; g(x) con polinomios, exp, sin, cos."),
    Method("cc_variation", "B · No homogénea: variación de parámetros", "B", ho.cc_variation,
           "y'' + y = tan(x)",
           "Coeficientes constantes; g(x) cualquiera."),
    Method("cauchy_euler", "B · Cauchy-Euler (homog. y no homog.)", "B", ho.cauchy_euler,
           "x^2*y'' - 2*x*y' + 2*y = x^3",
           "x²y'' + a·x·y' + b·y = f(x)  (coeficiente de y⁽ᵏ⁾ es c·xᵏ)."),
]
BY_KEY = {m.key: m for m in METHODS}
AUTO_KEY = "auto"

# Orden de prueba en modo automático (de lo más simple a lo más general)
_AUTO_FIRST = ["separable", "linear", "bernoulli", "exact", "homogeneous", "integrating_factor"]
_AUTO_HIGHER = ["cauchy_euler", "cc_hom", "cc_undetermined", "cc_variation"]


def _run(method: Method, parsed: ParsedODE) -> Solution:
    try:
        sol = method.func(parsed)
    except EdoError:
        raise
    except Exception as exc:  # error inesperado de sympy: no tumbar la aplicación
        raise EdoError(f"No se pudo completar el método «{method.label}»: {type(exc).__name__}: {exc}") from None
    sol.method_key, sol.method_name = method.key, method.label
    return sol


def solve(text: str, method_key: str = AUTO_KEY) -> Solution:
    """Resuelve la EDO escrita en `text`.

    method_key == "auto": clasifica y resuelve. Si no, valida y aplica ese método.
    Lanza ParseError / NotApplicable / Unsupported con mensajes para el usuario.
    """
    parsed = parse(text)
    if method_key != AUTO_KEY:
        if method_key not in BY_KEY:
            raise EdoError(f"Método desconocido: {method_key}")
        return _run(BY_KEY[method_key], parsed)

    candidates = _AUTO_FIRST if parsed.order == 1 else _AUTO_HIGHER
    log = []
    for key in candidates:
        method = BY_KEY[key]
        try:
            sol = _run(method, parsed)
        except NotApplicable as exc:
            log.append((method.label, str(exc)))
            continue
        sol.classification = log + [(method.label, "Aplicable ✔")]
        return sol
    detail = "; ".join(f"{name}: {why}" for name, why in log)
    raise Unsupported("La ecuación no pertenece a ninguno de los métodos soportados.\n" + detail)
