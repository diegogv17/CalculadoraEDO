"""Convierte LaTeX en imágenes PhotoImage de Tk usando el motor mathtext de matplotlib."""
from __future__ import annotations

import base64
import io
import re

import matplotlib

matplotlib.use("Agg")
from matplotlib.figure import Figure  # noqa: E402

matplotlib.rcParams["mathtext.fontset"] = "cm"

# Construcciones de LaTeX que mathtext no entiende -> equivalentes simples
_REPLACEMENTS = [
    (r"\left.", ""), (r"\right.", ""), (r"\displaystyle", ""),
    (r"\ldots", r"\dots"), (r"\Longrightarrow", r"\Rightarrow"), (r"\Longleftrightarrow", r"\Leftrightarrow"),
    (r"\mathrm", r"\mathrm"), (r"\log", r"\ln"),
]


def _sanitize(tex: str) -> str:
    for a, b in _REPLACEMENTS:
        tex = tex.replace(a, b)
    tex = re.sub(r"\\operatorname\{([^}]*)\}", r"\\mathrm{\1}", tex)
    tex = re.sub(r"\\mathbb\{([^}]*)\}", r"\1", tex)
    return tex


def _png(markup: str, size: float, color: str = "black") -> bytes:
    fig = Figure(figsize=(0.01, 0.01), dpi=130)
    fig.text(0, 0, markup, fontsize=size, color=color)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0.04, transparent=True)
    return buf.getvalue()


def latex_png(tex: str, size: float = 15, color: str = "black") -> bytes:
    """PNG de una fórmula. Si mathtext falla, devuelve el texto plano (nunca lanza)."""
    try:
        return _png(f"${_sanitize(tex)}$", size, color)
    except Exception:
        plain = tex.replace("$", "")
        try:
            return _png(plain.replace("\\", ""), size, color)
        except Exception:
            return _png("(no se pudo dibujar la fórmula)", size, color)


def latex_image(tk, tex: str, size: float = 15, color: str = "black"):
    """PhotoImage de Tk (el llamador debe conservar la referencia)."""
    return tk.PhotoImage(data=base64.b64encode(latex_png(tex, size, color)))
