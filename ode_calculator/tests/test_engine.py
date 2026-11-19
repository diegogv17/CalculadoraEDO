"""Pruebas del motor: cada solución se verifica sustituyéndola en la EDO original.

Ejecutar:  python -m tests.test_engine   (desde la carpeta ode_calculator)
"""
import random
import sys

sys.stdout.reconfigure(encoding="utf-8")

import sympy as sp

from ode_core import EdoError, solve
from ode_core.parser import D, parse, x, y

random.seed(1)


def _num_zero(expr, extra=()):
    """¿expr ≈ 0 en varios puntos aleatorios (las constantes se fijan)?"""
    free = [s for s in expr.free_symbols]
    for _ in range(4):
        vals = {s: sp.Rational(random.randint(5, 40), 10) for s in free}
        v = complex(sp.N(expr.subs(vals)))
        if abs(v) > 1e-6:
            return False
    return True


def verify(text, sol):
    p = parse(text)
    ok = False
    for e in sol.explicit:
        if p.order == 1:
            res = sp.diff(e, x) - p.f.subs(y, e)
        else:
            sub = {D[k]: sp.diff(e, x, k) for k in range(p.order + 1)}
            res = p.expr.subs(sub)
        ok = _num_zero(res)
        assert ok, f"{text}: la solución explícita {e} no satisface la EDO"
    if sol.implicit is not None and not sol.explicit:
        F = sol.implicit
        res = sp.diff(F, x) + sp.diff(F, y) * p.f
        assert _num_zero(res), f"{text}: F={F} no es integral primera"
        ok = True
    assert ok, f"{text}: sin solución verificable"


CASES = [
    # (ecuación, método esperado en modo automático, método manual a probar)
    ("dy/dx = x*y", "separable"),
    ("y' = exp(x+y)", "separable"),
    ("(1+x^2) dy - (1+y^2) dx = 0", "separable"),
    ("y' = (x+y)/x", "linear"),
    ("(x^2 + y^2) dx - x*y dy = 0", "homogeneous"),
    ("y' = (x^2+y^2)/(x*y)", "homogeneous"),
    ("(2*x*y + 3) dx + (x^2 - 1) dy = 0", "exact"),
    ("(x^2 + y^2 + x) dx + x*y dy = 0", "integrating_factor"),
    ("2*x*y dx + (y^2 - 3*x^2) dy = 0", "integrating_factor"),
    ("y' + y/x = x^2", "linear"),
    ("y' + 2*y = exp(-x)", "linear"),
    ("y' + y/x = x*y^2", "bernoulli"),
    ("y' + y = x*y^3", "bernoulli"),
    ("y'' - 3*y' + 2*y = 0", "cc_hom"),
    ("y'' + 4*y = 0", "cc_hom"),
    ("y'' - 2*y' + y = 0", "cc_hom"),
    ("y''' - y'' + y' - y = 0", "cc_hom"),
    ("y'' + 2*y' + 5*y = 0", "cc_hom"),
    ("y'' - 3*y' + 2*y = exp(x) + x", "cc_undetermined"),
    ("y'' + y = sin(x)", "cc_undetermined"),
    ("y'' + 4*y = x*cos(2*x) + 3", "cc_undetermined"),
    ("y'' - 2*y' + y = x*exp(x)", "cc_undetermined"),
    ("y'' + y = tan(x)", "cc_variation"),
    ("y'' - 2*y' + y = exp(x)/x", "cc_variation"),
    ("x^2*y'' - 2*x*y' + 2*y = 0", "cauchy_euler"),
    ("x^2*y'' - 2*x*y' + 2*y = x^3", "cauchy_euler"),
    ("x^2*y'' + x*y' + y = 0", "cauchy_euler"),
    ("x^2*y'' + 3*x*y' + y = ln(x)", "cauchy_euler"),
]

BAD = ["y'' + = 0", "dy/dx = ", "y' = x**", "hola mundo", "y' = z*y", "(x+y dx + dy = 0",
       "y'' = y^2", "y' = 1/0", "", "x + y = 3", "y'*y'' = 1"]


def main() -> int:
    fails = 0
    for text, key in CASES:
        try:
            sol = solve(text, "auto")
            if sol.method_key != key:
                print(f"     (auto eligió {sol.method_key}; se prueba {key} en manual)")
                verify(text, sol)
                sol = solve(text, key)
            verify(text, sol)
            print(f"OK   [{sol.method_key:18}] {text}")
        except Exception as exc:
            fails += 1
            print(f"FAIL [{key:18}] {text}\n       {type(exc).__name__}: {exc}")
    for text in BAD:
        try:
            solve(text, "auto")
            print(f"FAIL (debía dar error): {text!r}")
            fails += 1
        except EdoError as exc:
            print(f"OK   error controlado: {text!r} -> {str(exc)[:70]}")
        except Exception as exc:
            fails += 1
            print(f"FAIL excepción no controlada {text!r}: {type(exc).__name__}: {exc}")
    # validación en modo manual
    for text, key in [("y'' + y = 0", "separable"), ("dy/dx = x*y", "cc_hom"),
                      ("y' + y = x", "bernoulli"), ("y'' + y = x", "cc_hom")]:
        try:
            solve(text, key)
            print(f"FAIL (manual debía rechazar): {text!r} con {key}")
            fails += 1
        except EdoError as exc:
            print(f"OK   manual rechaza {key}: {str(exc)[:70]}")
    print("\nFallos:", fails)
    return fails


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
