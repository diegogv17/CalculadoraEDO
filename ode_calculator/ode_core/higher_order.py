"""Bloque B: EDO lineales de orden superior.

  * Coeficientes constantes homogéneas (ecuación característica)
  * No homogéneas: coeficientes indeterminados (aniquiladores) o variación de parámetros
  * Cauchy-Euler (homogénea y no homogénea)
"""
from __future__ import annotations

import sympy as sp

from .parser import ParsedODE, x
from .report import EdoError, NotApplicable, Solution

L = sp.latex
m = sp.Symbol("m")
xp = sp.Symbol("x", positive=True)   # Cauchy-Euler se resuelve para x > 0


def _need_higher(p: ParsedODE) -> None:
    if p.order < 2:
        raise NotApplicable("La ecuación es de primer orden; este método es para orden ≥ 2.")


def _const_coeffs(p: ParsedODE) -> bool:
    return all(not c.has(x) for c in p.coeffs)


def _need_const(p: ParsedODE) -> None:
    _need_higher(p)
    if not _const_coeffs(p):
        raise NotApplicable("Los coeficientes no son constantes (a_k depende de x).")


def _cs(n: int):
    return sp.symbols(f"C_1:{n + 1}")


def _lhs_latex(coeffs, g=None) -> str:
    terms = []
    for k in range(len(coeffs) - 1, -1, -1):
        c = coeffs[k]
        if c == 0:
            continue
        yk = "y" + "'" * k
        terms.append(rf"\left({L(c)}\right){yk}")
    s = " + ".join(terms)
    return s + (rf" = {L(g)}" if g is not None else " = 0")


# ------------------------------------------------------- raíces y bases de soluciones
def _roots(poly_expr):
    """Raíces con multiplicidad {raíz: mult}. Exactas si es posible; si no, numéricas."""
    poly = sp.Poly(poly_expr, m)
    r = sp.roots(poly, multiple=False)
    if sum(r.values()) == poly.degree():
        return r, True
    approx = {}
    for z in poly.nroots(n=15, maxsteps=200):
        z = sp.N(z, 10)
        key = next((k for k in approx if abs(complex(k - z)) < 1e-6), None)
        if key is None:
            approx[z] = 1
        else:
            approx[key] += 1
    return approx, False


def _basis(roots, euler: bool = False):
    """Base de soluciones de la homogénea. euler=True usa x^r y ln(x) (Cauchy-Euler)."""
    t = sp.log(xp) if euler else x
    basis = []
    for r, mult in sorted(roots.items(), key=lambda kv: (complex(sp.N(kv[0])).real, complex(sp.N(kv[0])).imag)):
        a, b = sp.re(r), sp.im(r)
        if abs(complex(sp.N(b))) < 1e-9:
            a = sp.simplify(r)
            core = xp ** a if euler else sp.exp(a * x)
            basis += [t ** j * core for j in range(mult)]
        elif complex(sp.N(b)).real > 0:
            core = xp ** a if euler else sp.exp(a * x)
            for j in range(mult):
                basis += [t ** j * core * sp.cos(b * t), t ** j * core * sp.sin(b * t)]
    return basis


def _roots_report(sol: Solution, roots, exact: bool, var: str = "m") -> None:
    parts = []
    for r, mult in roots.items():
        r = sp.simplify(r) if exact else r
        a, b = sp.re(r), sp.im(r)
        if abs(complex(sp.N(b))) < 1e-9:
            txt = rf"{var} = {L(a)}"
        elif complex(sp.N(b)).real > 0:
            txt = rf"{var} = {L(a)} \pm {L(b)}\,i"
        else:
            continue
        parts.append(txt + (rf"\ \text{{(multiplicidad {mult})}}" if mult > 1 else ""))
    sol.math(r",\qquad ".join(parts))
    if not exact:
        sol.text("Aviso: las raíces se calcularon de forma numérica (aproximada).")


def _yc(basis):
    cs = _cs(len(basis))
    return sum(c * f for c, f in zip(cs, basis)), cs


def _classify_text(roots) -> str:
    kinds = []
    if any(mu > 1 for mu in roots.values()):
        kinds.append("repetidas")
    if any(abs(complex(sp.N(sp.im(r)))) > 1e-9 for r in roots):
        kinds.append("complejas conjugadas")
    if any(abs(complex(sp.N(sp.im(r)))) <= 1e-9 for r in roots):
        kinds.append("reales")
    return "Raíces " + ", ".join(kinds) + "."


# ---------------------------------------- coeficientes constantes: homogénea
def _homog_solution(sol: Solution, p: ParsedODE):
    sol.head("1. Ecuación característica (y = e^(mx))")
    sol.math(_lhs_latex(p.coeffs))
    poly = sum(c * m ** k for k, c in enumerate(p.coeffs))
    sol.math(rf"{L(sp.expand(poly))} = 0")
    if sp.factor(poly) != sp.expand(poly):
        sol.math(rf"{L(sp.factor(poly))} = 0")
    roots, ex = _roots(poly)
    sol.head("2. Raíces de la ecuación auxiliar")
    _roots_report(sol, roots, ex)
    sol.text(_classify_text(roots))
    basis = _basis(roots)
    yc, cs = _yc(basis)
    sol.head("3. Solución complementaria  y_c")
    sol.math(rf"y_c = {L(yc)}")
    return roots, basis, yc


def cc_homogeneous(p: ParsedODE) -> Solution:
    _need_const(p)
    if p.g != 0:
        raise NotApplicable("La ecuación es NO homogénea (g(x) ≠ 0); use coeficientes indeterminados o variación de parámetros.")
    sol = Solution("cc_hom", "Homogénea, coeficientes constantes")
    _, _, yc = _homog_solution(sol, p)
    sol.head("Solución general")
    sol.explicit.append(yc)
    sol.answer.append(rf"y = {L(yc)}")
    return sol


# ------------------------------------------ coeficientes indeterminados
def _term_form(t):
    """t = c·x^d·e^{ax}·(cos|sin)(bx)  ->  (a, b, d) o None."""
    a = sp.Integer(0)
    b = sp.Integer(0)
    d = 0
    trig = 0
    for fac in sp.Mul.make_args(t):
        if not fac.has(x):
            continue
        if fac == x:
            d += 1
        elif fac.is_Pow and fac.base == x and fac.exp.is_Integer and fac.exp > 0:
            d += int(fac.exp)
        elif fac.func == sp.exp:
            arg = fac.args[0]
            k = sp.diff(arg, x)
            if k.has(x) or sp.simplify(arg - k * x).has(x):
                return None
            a += k
        elif fac.func in (sp.sin, sp.cos):
            arg = fac.args[0]
            k = sp.diff(arg, x)
            if k.has(x) or sp.simplify(arg - k * x) != 0 or trig:
                return None
            trig += 1
            b = abs(k)
        else:
            return None
    return a, b, d


def _families(g):
    """Agrupa los términos de g por familia (a, b): {(a,b): (grado_max, [términos])}."""
    if g.has(sp.sinh, sp.cosh):
        g = g.rewrite(sp.exp)
    g = sp.expand(sp.expand_power_exp(g))
    fams = {}
    for t in sp.Add.make_args(g):
        f = _term_form(t)
        if f is None:
            return None
        a, b, d = f
        deg, terms = fams.get((a, b), (0, []))
        fams[(a, b)] = (max(deg, d), terms + [t])
    return fams


def _annihilator(a, b, d) -> str:
    if b == 0:
        return rf"(D - {L(a)})^{{{d + 1}}}" if a != 0 else rf"D^{{{d + 1}}}"
    return rf"\left[(D - {L(a)})^2 + {L(b ** 2)}\right]^{{{d + 1}}}"


def cc_undetermined(p: ParsedODE) -> Solution:
    _need_const(p)
    if p.g == 0:
        raise NotApplicable("La ecuación es homogénea (g(x) = 0); use el método homogéneo.")
    fams = _families(p.g)
    if fams is None:
        raise NotApplicable("g(x) no es combinación de polinomios, exponenciales, senos y cosenos "
                            "(coeficientes indeterminados no aplica; use variación de parámetros).")
    sol = Solution("cc_undetermined", "No homogénea: coeficientes indeterminados")
    sol.head("A. Solución complementaria y_c")
    roots, basis, yc = _homog_solution(sol, p)

    sol.head("B. Solución particular y_p (aniquiladores)")
    sol.math(rf"g(x) = {L(p.g)}")
    poly = sum(c * m ** k for k, c in enumerate(p.coeffs))
    counter = 0
    yp_total, unknowns_all, eq_log = 0, [], []
    for (a, b), (d, terms) in fams.items():
        sol.math(rf"\text{{Término(s): }} {L(sum(terms))} \;\Rightarrow\; \text{{aniquilador }}\; {_annihilator(a, b, d)}")
        target = a + sp.I * b
        s = sum(mu for r, mu in roots.items() if sp.simplify(r - target) == 0)
        shape = []
        unknowns = []
        for j in range(d + 1):
            A = sp.Symbol(f"A_{counter}")
            counter += 1
            unknowns.append(A)
            if b == 0:
                shape.append(A * x ** j * sp.exp(a * x))
            else:
                B = sp.Symbol(f"A_{counter}")
                counter += 1
                unknowns.append(B)
                shape.append(x ** j * sp.exp(a * x) * (A * sp.cos(b * x) + B * sp.sin(b * x)))
        trial = x ** s * sum(shape)
        if s:
            sol.text(f"Resonancia: {a + sp.I * b if b else a} es raíz de la ecuación auxiliar con multiplicidad {s}; "
                     f"se multiplica la propuesta por x^{s}.")
        sol.math(rf"y_{{p}} \text{{ propuesta}} = {L(trial)}")
        gf = sum(terms)
        res = sp.expand(sum(c * sp.diff(trial, x, k) for k, c in enumerate(p.coeffs)) * sp.exp(-a * x)
                        - gf * sp.exp(-a * x))
        try:
            gens = [x] if b == 0 else [x, sp.cos(b * x), sp.sin(b * x)]
            eqs = sp.Poly(res, *gens).coeffs()
        except sp.PolynomialError:
            raise NotApplicable("No se pudieron igualar coeficientes (use variación de parámetros).")
        sol_dict = sp.solve(eqs, unknowns, dict=True)
        if not sol_dict:
            raise EdoError("El sistema de coeficientes indeterminados no tiene solución.")
        sol_dict = sol_dict[0]
        eq_log.append((eqs, sol_dict))
        yp_total += trial.subs(sol_dict)
        unknowns_all += unknowns
    sol.head("C. Sustituir en la EDO e igualar coeficientes")
    for eqs, sd in eq_log:
        sol.math(r"\ ,\quad ".join(L(sp.Eq(e, 0)) for e in eqs[:6]) + (r"\ ,\ \ldots" if len(eqs) > 6 else ""))
        sol.math(r",\quad ".join(L(sp.Eq(k, v)) for k, v in sd.items()))
    yp = sp.simplify(yp_total)
    sol.math(rf"y_p = {L(yp)}")
    sol.head("D. Solución general  y = y_c + y_p")
    full = yc + yp
    sol.explicit.append(full)
    sol.answer += [rf"y_c = {L(yc)}", rf"y_p = {L(yp)}", rf"y = {L(full)}"]
    return sol


# ---------------------------------------------- variación de parámetros
def _variation(sol: Solution, basis, g_std, var=x):
    n = len(basis)
    W = sp.Matrix(n, n, lambda i, j: sp.diff(basis[j], var, i))
    Wd = sp.simplify(W.det())
    sol.head("Wronskiano")
    sol.math(rf"W = {L(Wd)}")
    if Wd == 0:
        raise EdoError("El Wronskiano es cero: las soluciones no son linealmente independientes.")
    yp = 0
    sol.head("Funciones u_k' = W_k / W · g(x)/a_n(x)")
    for k in range(n):
        Wk = W.copy()
        for i in range(n):
            Wk[i, k] = 1 if i == n - 1 else 0
        uk_p = sp.simplify(Wk.det() / Wd * g_std)
        uk = sp.integrate(uk_p, var)
        sol.math(rf"u_{{{k + 1}}}' = {L(uk_p)} \;\Longrightarrow\; u_{{{k + 1}}} = {L(uk)}")
        yp += basis[k] * uk
    return sp.simplify(yp)


def cc_variation(p: ParsedODE) -> Solution:
    _need_const(p)
    if p.g == 0:
        raise NotApplicable("La ecuación es homogénea (g(x) = 0); use el método homogéneo.")
    sol = Solution("cc_variation", "No homogénea: variación de parámetros")
    sol.head("A. Solución complementaria y_c")
    _, basis, yc = _homog_solution(sol, p)
    sol.head("B. Variación de parámetros")
    sol.text("Forma estándar: dividir entre a_n para obtener y^(n) + ... = g(x)/a_n")
    g_std = sp.simplify(p.g / p.coeffs[-1])
    sol.math(rf"y_p = \sum y_k\,u_k, \qquad \frac{{g}}{{a_n}} = {L(g_std)}")
    sol.math(r"y_1,\dots,y_n:\ " + r",\ ".join(L(b) for b in basis))
    yp = _variation(sol, basis, g_std)
    sol.math(rf"y_p = {L(yp)}")
    sol.head("C. Solución general  y = y_c + y_p")
    full = yc + yp
    sol.explicit.append(full)
    sol.answer += [rf"y_c = {L(yc)}", rf"y_p = {L(yp)}", rf"y = {L(full)}"]
    return sol


# --------------------------------------------------------------- Cauchy-Euler
def _euler_coeffs(p: ParsedODE):
    cs = []
    for k, a in enumerate(p.coeffs):
        c = sp.simplify(a.subs(x, xp) / xp ** k)
        if c.has(xp):
            return None
        cs.append(c)
    return cs if cs[-1] != 0 else None


def cauchy_euler(p: ParsedODE) -> Solution:
    _need_higher(p)
    cs = _euler_coeffs(p)
    if cs is None:
        raise NotApplicable("No tiene la forma c_n xⁿ y⁽ⁿ⁾ + ... + c_1 x y' + c_0 y = g(x) con c_k constantes.")
    g = p.g.subs(x, xp)
    sol = Solution("cauchy_euler", "Cauchy-Euler")
    sol.head("1. Identificar la estructura de Cauchy-Euler (se trabaja con x > 0)")
    sol.math(" + ".join(rf"{L(c)}\,x^{{{k}}}y^{{({k})}}" for k, c in reversed(list(enumerate(cs))) if c != 0)
             + rf" = {L(g)}")
    sol.head("2. Sustitución  y = x^m  en la parte homogénea")
    sol.text("Como (x^m)^(k) = m(m−1)…(m−k+1) x^(m−k), cada término queda proporcional a x^m:")
    poly = sp.expand(sum(c * sp.ff(m, k) for k, c in enumerate(cs)))
    sol.math(rf"{L(poly)} = 0 \quad\Longleftrightarrow\quad {L(sp.factor(poly))} = 0")
    roots, ex = _roots(poly)
    sol.head("3. Raíces de la ecuación auxiliar")
    _roots_report(sol, roots, ex)
    sol.text(_classify_text(roots) + " (se usa ln x en lugar de x en repetidas / complejas)")
    basis = _basis(roots, euler=True)
    yc, _ = _yc(basis)
    sol.head("4. Solución complementaria  y_c")
    sol.math(rf"y_c = {L(yc)}")
    if g == 0:
        sol.head("Solución general")
        sol.explicit.append(yc.subs(xp, x))
        sol.answer.append(rf"y = {L(yc)}")
        return sol
    sol.head("5. Solución particular por variación de parámetros")
    g_std = sp.simplify(g / (cs[-1] * xp ** p.order))
    sol.text("Forma estándar: se divide entre c_n xⁿ.")
    sol.math(rf"f(x) = \frac{{g(x)}}{{c_n x^n}} = {L(g_std)}")
    sol.math(r"y_1,\dots,y_n:\ " + r",\ ".join(L(b) for b in basis))
    yp = _variation(sol, basis, g_std, var=xp)
    sol.math(rf"y_p = {L(yp)}")
    sol.head("6. Solución general  y = y_c + y_p")
    full = yc + yp
    sol.explicit.append(full.subs(xp, x))
    sol.answer += [rf"y_c = {L(yc)}", rf"y_p = {L(yp)}", rf"y = {L(full)}"]
    return sol
