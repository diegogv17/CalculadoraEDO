"""Prueba de humo: renderiza TODAS las fórmulas de todos los casos y lanza la GUI."""
import sys
sys.stdout.reconfigure(encoding="utf-8")
from ode_core import solve
from gui.latex_render import _png, _sanitize
from tests.test_engine import CASES

bad = 0
for text, _ in CASES:
    sol = solve(text)
    for tex in sol.answer + [c for k, c in sol.steps if k == "math"]:
        try:
            _png(f"${_sanitize(tex)}$", 14)
        except Exception as e:
            bad += 1
            print("NO RENDER:", text, "|", tex[:90], "|", str(e)[:80].replace("\n", " "))
print("fórmulas con fallo:", bad)

from gui.app import App
app = App()
for text in ["y' + y/x = x*y^2", "y'' + y = tan(x)", "y'' + = 0"]:
    app.entry.delete(0, "end"); app.entry.insert(0, text); app.on_solve()
    for _ in range(300):
        app.update(); 
        if not app._busy: break
        import time; time.sleep(0.05)
    app.update()
    print(text, "->", app.method.get(), "| alerta:", app.alert.cget("text")[:60] if app.alert.winfo_ismapped() else "-")
app.after(100, app.destroy); app.mainloop()
