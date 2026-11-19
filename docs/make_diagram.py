"""Genera docs/diagrama_bloques.png (arquitectura de la aplicación)."""
import os
from matplotlib.figure import Figure
from matplotlib.patches import FancyBboxPatch

fig = Figure(figsize=(12, 6.2), dpi=130, facecolor="white")
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 12); ax.set_ylim(0, 6.2); ax.axis("off")


def box(x, y, w, h, title, sub, color):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.15",
                                fc=color, ec="#222", lw=1.4))
    ax.text(x + w / 2, y + h - 0.28, title, ha="center", va="center", fontsize=11, weight="bold")
    ax.text(x + w / 2, y + h / 2 - 0.15, sub, ha="center", va="center", fontsize=8.5, linespacing=1.4)


def arrow(x1, y1, x2, y2, txt=""):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="-|>", lw=1.6, color="#333"))
    if txt:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.15, txt, ha="center", fontsize=8, style="italic")


ax.text(6, 5.95, "Arquitectura de la Calculadora de EDO", ha="center", fontsize=14, weight="bold")
box(0.2, 2.2, 2.3, 1.8, "INTERFAZ (GUI)", "gui/app.py\nTkinter · teclado\nmodo auto / manual\nmenú de métodos\nalertas de error", "#ffe2b8")
box(3.2, 2.2, 2.2, 1.8, "CLASIFICADOR", "ode_core/classifier.py\nsolve(texto, método)\nauto: prueba métodos\nmanual: valida", "#cfe3ff")
box(6.1, 4.1, 2.6, 1.4, "PARSER", "parser.py\nvalida sintaxis\nnormaliza: M dx+N dy=0,\ny'=f(x,y), a_k(x)y^(k)=g", "#d9f2d9")
box(6.1, 2.2, 2.6, 1.5, "BLOQUE A  (1.er orden)", "first_order.py\nseparable · homogénea · exacta\nfactor integrante · lineal\nBernoulli", "#e6d9f5")
box(6.1, 0.3, 2.6, 1.6, "BLOQUE B  (orden superior)", "higher_order.py\ncoef. constantes · indeterminados\nvariación de parámetros\nCauchy-Euler", "#e6d9f5")
box(9.3, 2.2, 2.5, 1.8, "RESULTADO", "report.py · Solution\npasos (head/text/math)\nrespuesta en LaTeX\nclasificación", "#ffd9d9")
box(9.3, 0.3, 2.5, 1.4, "RENDER LaTeX", "gui/latex_render.py\nmathtext → imagen\n(solución y trazabilidad)", "#ffe2b8")
box(3.2, 0.3, 2.2, 1.4, "sympy", "integrar · derivar\nsimplificar · raíces\n(nunca dsolve)", "#eeeeee")
arrow(2.5, 3.1, 3.2, 3.1, "texto + método")
arrow(5.4, 3.5, 6.1, 4.6, "")
arrow(5.4, 3.1, 6.1, 3.0, "")
arrow(5.4, 2.7, 6.1, 1.3, "")
arrow(8.7, 3.0, 9.3, 3.1, "")
arrow(8.7, 1.2, 9.3, 2.5, "")
arrow(10.55, 2.2, 10.55, 1.7, "")
ax.text(10.55, 0.05, "se dibuja en la ventana de la GUI", ha="center", fontsize=7.5, color="#555")
arrow(4.3, 1.7, 4.3, 2.2, "")
ax.text(6, 0.05, "La GUI no contiene lógica matemática; ode_core no importa nada de la GUI.", ha="center", fontsize=8.5, color="#555")
fig.savefig(os.path.join(os.path.dirname(__file__), "diagrama_bloques.png"))
