"""Bloque A: métodos analíticos para EDO de primer orden.

Cada método recibe un `ParsedODE`, verifica sus condiciones (si no se cumplen
lanza `NotApplicable` con el motivo) y devuelve una `Solution` con los pasos.
Solo se usa sympy para integrar/derivar/simplificar; la lógica del método
(sustituciones, factores integrantes, etc.) está programada aquí.
"""
from __future__ import annotations

import sympy as sp

from .parser import ParsedODE, x, y
from .report import NotApplicable, Solution

C = sp.Symbol("C")
L = sp.latex


def _need_first_order(p: ParsedODE) -> None:
    if p.order != 1:
        raise NotApplicable(f"La ecuación es de orden {p.order}; este método es para primer orden.")


def _form(M, N) -> str:
    return rf"\left({L(M)}\right)dx + \left({L(N)}\right)dy = 0"


def _explicit(expr, limit: int = 3):
    """Intenta despejar y de expr = 0. Devuelve [] si no es práctico."""
    try:
        sols = sp.solve(expr, y)
    except Exception:
        return []
    sols = [s for s in sols if not s.has(sp.CRootOf) and sp.count_ops(s) < 250]
    return sols if 0 < len(sols) <= limit else []


def _absorb(e):
    """exp(C)*A -> C*A (la constante arbitraria absorbe el factor)."""
    e = sp.expand_power_exp(e)
    return e.subs(sp.exp(C), C)


def _unevaluated(e) -> bool:
    return e.has(sp.Integral)


def _answer_implicit(sol: Solution, F, rhs=C) -> None:
    sol.implicit = F
    sol.answer.append(rf"{L(F)} = {L(rhs)}")
    exp = _explicit(F - C)
    for s in exp:
        s = _absorb(s)
        sol.explicit.append(s)
        sol.answer.append(rf"y = {L(s)}")


# ---------------------------------------------------------------- separables
def _separate(f):
    """f(x,y) = g(x) h(y)  ->  (g, h)  o None."""
    f = sp.expand_power_exp(f)
    for c in (f, sp.factor(f), sp.powsimp(sp.expand(f)), sp.factor(sp.expand_power_exp(sp.expand(f)))):
        g, h = c.as_independent(y, as_Add=False)
        if not h.has(x) and not g.has(y):
            return g, h
    return None


def separable(p: ParsedODE) -> Solution:
    _need_first_order(p)
    sep = _separate(p.f)
    if sep is None:
        raise NotApplicable("No se puede escribir f(x,y) como g(x)·h(y).")
    g, h = sep
    sol = Solution("separable", "Variables separables")
    sol.head("1. Identificar g(x) y h(y)")
    sol.math(rf"\frac{{dy}}{{dx}} = {L(p.f)} = g(x)\,h(y)")
    sol.math(rf"g(x) = {L(g)}, \qquad h(y) = {L(h)}")
    sol.head("2. Separar variables e integrar")
    sol.math(rf"\frac{{dy}}{{h(y)}} = g(x)\,dx \;\Longrightarrow\; \int \frac{{dy}}{{{L(h)}}} = \int {L(g)}\,dx")
    H = sp.integrate(1 / h, y)
    G = sp.integrate(g, x)
    sol.math(rf"{L(H)} = {L(G)} + C")
    if h.has(y):
        zeros = [s for s in sp.solve(h, y) if not s.has(x)]
        if zeros:
            sol.text("Soluciones constantes (h(y) = 0), que pudieron perderse al dividir:")
            sol.math(", \\quad ".join(rf"y = {L(z)}" for z in zeros))
    sol.head("3. Solución general")
    _answer_implicit(sol, H - G)
    return sol


# --------------------------------------------------------------- homogéneas
def _is_degree_zero(f) -> bool:
    t = sp.Symbol("t", positive=True)
    ft = f.subs({x: t * x, y: t * y}, simultaneous=True)
    return sp.simplify(ft - f) == 0


def homogeneous(p: ParsedODE) -> Solution:
    _need_first_order(p)
    if not _is_degree_zero(p.f):
        raise NotApplicable("f(tx, ty) ≠ f(x, y): la ecuación no es homogénea de grado 0.")
    sol = Solution("homogeneous", "Ecuaciones homogéneas")
    sol.head("1. Verificar homogeneidad")
    sol.math(rf"f(tx,ty) = f(x,y) = {L(p.f)}")
    xp = sp.Symbol("x", positive=True)
    yp = sp.Symbol("y", positive=True)
    u = sp.Symbol("u")

    attempts = [
        ("y = ux", "dy = u\\,dx + x\\,du", u, "x", p.f),
        ("x = vy", "dx = v\\,dy + y\\,dv", sp.Symbol("v"), "y", 1 / p.f),
    ]
    for k, (name, diff_txt, w, base, g_expr) in enumerate(attempts):
        # f en términos de la nueva variable (las funciones de grado 0 pierden x o y)
        if base == "x":
            phi = sp.simplify(g_expr.subs({x: xp, y: w * xp}))
            phi = phi.subs(xp, x)
            indep = x
        else:
            phi = sp.simplify(g_expr.subs({y: yp, x: w * yp}))
            phi = phi.subs(yp, y)
            indep = y
        if phi.has(indep):
            continue
        psi = sp.simplify(phi - w)
        if psi == 0:
            sol.head("2. Sustitución")
            sol.text("Con la sustitución resulta u' = 0, es decir, la solución son rectas por el origen.")
            sol.answer.append("y = C\\,x" if base == "x" else "x = C\\,y")
            if base == "x":
                sol.explicit.append(C * x)
            return sol
        W = sp.integrate(1 / psi, w)
        if _unevaluated(W) and k == 0:
            continue                      # probar la otra sustitución
        sol.head(f"2. Sustitución {name}")
        sol.math(rf"{name},\qquad {diff_txt}")
        if base == "x":
            sol.math(rf"u + x\frac{{du}}{{dx}} = {L(phi)} \;\Longrightarrow\; x\frac{{du}}{{dx}} = {L(psi)}")
            sol.head("3. Ecuación separable en u y x")
            sol.math(rf"\int \frac{{du}}{{{L(psi)}}} = \int \frac{{dx}}{{x}}")
            sol.math(rf"{L(W)} = \ln|x| + C")
            sol.head("4. Regresar a las variables originales (u = y/x)")
            F = W.subs(w, y / x) - sp.log(x)
        else:
            sol.math(rf"v + y\frac{{dv}}{{dy}} = {L(phi)} \;\Longrightarrow\; y\frac{{dv}}{{dy}} = {L(psi)}")
            sol.head("3. Ecuación separable en v e y")
            sol.math(rf"\int \frac{{dv}}{{{L(psi)}}} = \int \frac{{dy}}{{y}}")
            sol.math(rf"{L(W)} = \ln|y| + C")
            sol.head("4. Regresar a las variables originales (v = x/y)")
            F = W.subs(w, x / y) - sp.log(y)
        _answer_implicit(sol, F)
        return sol
    raise NotApplicable("No se pudo reducir a una ecuación separable con y=ux ni con x=vy.")


# ------------------------------------------------------------------ exactas
def _exact_core(sol: Solution, M, N) -> None:
    """Pasos del método de ecuaciones exactas (asume M_y = N_x ya verificado)."""
    sol.head("Obtención de la función potencial f(x, y)")
    F1 = sp.integrate(M, x)
    sol.math(rf"f(x,y) = \int M\,dx = {L(F1)} + g(y)")
    gp = sp.simplify(N - sp.diff(F1, y))
    sol.math(rf"\frac{{\partial f}}{{\partial y}} = {L(sp.diff(F1, y))} + g'(y) = N \;\Longrightarrow\; g'(y) = {L(gp)}")
    if gp.has(x):
        raise NotApplicable("g'(y) depende de x: la ecuación no es exacta.")
    g = sp.integrate(gp, y)
    sol.math(rf"g(y) = {L(g)}")
    sol.head("Solución general  f(x, y) = C")
    _answer_implicit(sol, F1 + g)


def exact(p: ParsedODE) -> Solution:
    _need_first_order(p)
    M, N = p.M, p.N
    My, Nx = sp.diff(M, y), sp.diff(N, x)
    if sp.simplify(My - Nx) != 0:
        raise NotApplicable(f"No es exacta: ∂M/∂y = {My} pero ∂N/∂x = {Nx}.")
    sol = Solution("exact", "Ecuaciones exactas")
    sol.head("1. Forma M dx + N dy = 0 y criterio de exactitud")
    sol.math(_form(M, N))
    sol.math(rf"\frac{{\partial M}}{{\partial y}} = {L(My)}, \qquad \frac{{\partial N}}{{\partial x}} = {L(Nx)}")
    sol.text("Las derivadas parciales coinciden: la ecuación es exacta.")
    _exact_core(sol, M, N)
    return sol


# --------------------------------------------- reducibles a exactas (μ(x), μ(y))
def integrating_factor(p: ParsedODE) -> Solution:
    _need_first_order(p)
    M, N = p.M, p.N
    My, Nx = sp.diff(M, y), sp.diff(N, x)
    if sp.simplify(My - Nx) == 0:
        raise NotApplicable("La ecuación ya es exacta (μ = 1); use el método de ecuaciones exactas.")
    sol = Solution("integrating_factor", "Reducible a exacta (factor integrante)")
    sol.head("1. La ecuación NO es exacta")
    sol.math(_form(M, N))
    sol.math(rf"\frac{{\partial M}}{{\partial y}} = {L(My)} \neq {L(Nx)} = \frac{{\partial N}}{{\partial x}}")

    mu = None
    sol.head("2. Buscar factor integrante")
    qx = sp.simplify((My - Nx) / N)
    sol.math(rf"\frac{{M_y - N_x}}{{N}} = {L(qx)}")
    if not qx.has(y):
        sol.text("Depende solo de x  →  μ(x) = exp(∫ (M_y − N_x)/N dx)")
        mu = sp.simplify(sp.exp(sp.integrate(qx, x)))
    elif M != 0:
        qy = sp.simplify((Nx - My) / M)
        sol.math(rf"\frac{{N_x - M_y}}{{M}} = {L(qy)}")
        if not qy.has(x):
            sol.text("Depende solo de y  →  μ(y) = exp(∫ (N_x − M_y)/M dy)")
            mu = sp.simplify(sp.exp(sp.integrate(qy, y)))
    if mu is None:
        raise NotApplicable("No existe factor integrante que dependa solo de x o solo de y.")
    sol.math(rf"\mu = {L(mu)}")
    M2, N2 = sp.simplify(mu * M), sp.simplify(mu * N)
    sol.head("3. Multiplicar por μ y comprobar exactitud")
    sol.math(_form(M2, N2))
    My2, Nx2 = sp.diff(M2, y), sp.diff(N2, x)
    if sp.simplify(My2 - Nx2) != 0:
        raise NotApplicable("Tras multiplicar por μ la ecuación sigue sin ser exacta.")
    sol.math(rf"\frac{{\partial (\mu M)}}{{\partial y}} = {L(sp.simplify(My2))} = \frac{{\partial (\mu N)}}{{\partial x}}")
    _exact_core(sol, M2, N2)
    sol.text("Nota: multiplicar por μ puede añadir o quitar soluciones constantes; verifíquelo si es necesario.")
    return sol


# ----------------------------------------------------------------- lineales
def _linear_parts(f):
    """dy/dx = Q - P y  ->  (P, Q)  o None."""
    try:
        Q = f.subs(y, 0)
        a = sp.diff(f, y)
    except Exception:
        return None
    if Q.has(sp.zoo, sp.nan, sp.oo) or a.has(y):
        return None
    if sp.simplify(f - (a * y + Q)) != 0:
        return None
    return sp.simplify(-a), sp.simplify(Q)


def _solve_linear(sol: Solution, P, Q, dep: str = "y"):
    """Pasos del factor integrante para dep' + P dep = Q. Devuelve dep(x)."""
    sol.math(rf"{dep}' + \left({L(P)}\right){dep} = {L(Q)}")
    sol.head("Factor integrante  μ(x) = exp(∫P dx)")
    IP = sp.integrate(P, x)
    mu = sp.simplify(sp.exp(IP))
    sol.math(rf"\int P\,dx = {L(IP)} \;\Longrightarrow\; \mu(x) = {L(mu)}")
    sol.head(f"Multiplicar por μ:  (μ·{dep})' = μ·Q")
    muQ = sp.simplify(mu * Q)
    sol.math(rf"\frac{{d}}{{dx}}\left[{L(mu)}\,{dep}\right] = {L(muQ)}")
    I = sp.integrate(muQ, x)
    sol.math(rf"{L(mu)}\,{dep} = {L(I)} + C")
    return sp.simplify(I / mu) + sp.simplify(C / mu)


def linear(p: ParsedODE) -> Solution:
    _need_first_order(p)
    parts = _linear_parts(p.f)
    if parts is None:
        raise NotApplicable("No es de la forma y' + P(x)y = Q(x).")
    P, Q = parts
    sol = Solution("linear", "Lineal de primer orden")
    sol.head("1. Forma estándar  y' + P(x) y = Q(x)")
    ysol = _solve_linear(sol, P, Q)
    sol.head("Solución general")
    sol.explicit.append(ysol)
    sol.answer.append(rf"y = {L(ysol)}")
    return sol


# ---------------------------------------------------------------- Bernoulli
def _bernoulli_parts(f):
    """dy/dx = -P y + Q y^n -> (P, Q, n) o None."""
    by_power = {}
    for term in sp.Add.make_args(sp.expand(f)):
        c, rest = term.as_independent(y)
        if rest == 1:
            k = sp.Integer(0)
        elif rest == y:
            k = sp.Integer(1)
        else:
            b, e = rest.as_base_exp()
            if b != y or e.free_symbols:
                return None
            k = e
        by_power[k] = by_power.get(k, 0) + c
    others = [k for k in by_power if k not in (0, 1)]
    if len(others) != 1 or 0 in by_power:
        return None
    n = others[0]
    P = sp.simplify(-by_power.get(sp.Integer(1), 0))
    return P, sp.simplify(by_power[n]), n


def bernoulli(p: ParsedODE) -> Solution:
    _need_first_order(p)
    parts = _bernoulli_parts(p.f)
    if parts is None:
        raise NotApplicable("No es de la forma y' + P(x)y = Q(x)yⁿ con n ≠ 0, 1.")
    P, Q, n = parts
    sol = Solution("bernoulli", "Ecuación de Bernoulli")
    sol.head("1. Identificar la forma  y' + P(x)y = Q(x)yⁿ")
    sol.math(rf"y' + \left({L(P)}\right)y = \left({L(Q)}\right)y^{{{L(n)}}}, \qquad n = {L(n)}")
    sol.head("2. Sustitución  u = y^(1−n)")
    k = 1 - n
    sol.math(rf"u = y^{{{L(k)}}}, \qquad u' = {L(k)}\,y^{{{L(-n)}}}\,y'")
    sol.text("Dividiendo la ecuación entre yⁿ y sustituyendo se obtiene una ecuación LINEAL en u:")
    sol.math(rf"u' + (1-n)P(x)\,u = (1-n)Q(x)")
    P2, Q2 = sp.simplify(k * P), sp.simplify(k * Q)
    sol.head("3. Resolver la ecuación lineal en u")
    u = _solve_linear(sol, P2, Q2, dep="u")
    sol.math(rf"u = {L(u)}")
    sol.head("4. Regresar a y  (y = u^(1/(1−n)))")
    root = sp.simplify(u ** (1 / k))
    sols = [root]
    if k.is_integer and k % 2 == 0:
        sols = [root, -root]
        sol.text("Como 1−n es par, aparecen ambos signos de la raíz.")
    for s in sols:
        sol.explicit.append(s)
        sol.answer.append(rf"y = {L(s)}")
    if n > 0:
        sol.text("Además y = 0 es solución constante (para n > 0).")
    return sol
