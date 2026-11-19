"""Estructuras compartidas: excepciones y el objeto `Solution` (traza paso a paso).

El motor matemático NO conoce la interfaz gráfica: solo produce objetos
`Solution` cuyos pasos están en LaTeX, que cualquier GUI puede dibujar.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class EdoError(Exception):
    """Error base: siempre trae un mensaje legible para el usuario."""


class ParseError(EdoError):
    """La ecuación está mal escrita (sintaxis)."""


class NotApplicable(EdoError):
    """La ecuación no cumple las condiciones del método elegido."""


class Unsupported(EdoError):
    """La ecuación es válida pero no pertenece a ningún método soportado."""


@dataclass
class Solution:
    method_key: str = ""
    method_name: str = ""
    # Cada paso es (tipo, contenido); tipo ∈ {"head", "text", "math"}
    steps: list = field(default_factory=list)
    answer: list = field(default_factory=list)        # líneas LaTeX de la respuesta
    explicit: list = field(default_factory=list)      # y(x) explícitas (sympy)
    implicit: Any = None                              # F(x, y) con F = C (sympy)
    classification: list = field(default_factory=list)  # [(método, motivo/OK)]

    def head(self, s: str) -> None:
        self.steps.append(("head", s))

    def text(self, s: str) -> None:
        self.steps.append(("text", s))

    def math(self, s: str) -> None:
        self.steps.append(("math", s))
