"""Motor matemático de la calculadora de EDO (independiente de la interfaz)."""
from .classifier import AUTO_KEY, BY_KEY, METHODS, solve
from .report import EdoError, NotApplicable, ParseError, Solution, Unsupported

__all__ = ["solve", "METHODS", "BY_KEY", "AUTO_KEY", "Solution",
           "EdoError", "ParseError", "NotApplicable", "Unsupported"]
