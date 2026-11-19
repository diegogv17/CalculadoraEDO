"""Interfaz gráfica (Tkinter), estilo calculadora oscura. Sin lógica matemática:
solo llama a `ode_core.solve`."""
from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import ttk

from ode_core import AUTO_KEY, BY_KEY, METHODS, EdoError, ParseError, Solution, solve

from .latex_render import latex_image

# Paleta (inspirada en una calculadora móvil oscura)
BG = "#000000"
PANEL = "#1c1c1e"
NUM = "#333336"
FUNC = "#a5a5a8"
ORANGE = "#ff9f0a"
ORANGE_DK = "#c77d08"
TXT = "#ffffff"
MUTED = "#98989f"
GREEN = "#32d74b"
RED = "#ff453a"
TEAM = [("Karla Betzabé Osorio Dávila", "2500194"), ("Dallin Eleazar Osorio Cruz", "2500492"),
        ("Jennifer Gabriela Duque Ventura", "2500103"), ("Diego Alejandro Gómez Vasquez", "2500028")]
NL = chr(10)
AUTO_LABEL = "Automático (el sistema identifica el método)"

# (texto, inserta, tipo)   tipo: num | func | op | act
KEYS = [
    [("AC", "AC", "func"), ("⌫", "BS", "func"), ("(", "(", "func"), (")", ")", "func"), ("÷", "/", "op")],
    [("7", "7", "num"), ("8", "8", "num"), ("9", "9", "num"), ("x", "x", "num"), ("×", "*", "op")],
    [("4", "4", "num"), ("5", "5", "num"), ("6", "6", "num"), ("y", "y", "num"), ("−", "-", "op")],
    [("1", "1", "num"), ("2", "2", "num"), ("3", "3", "num"), ("y'", "y'", "func"), ("+", "+", "op")],
    [("0", "0", "num"), (".", ".", "num"), ("xⁿ", "^", "func"), ("y''", "y''", "func"), ("=", "GO", "act")],
]
EXTRA = [[("dx", " dx ", "func"), ("dy", " dy ", "func"), ("dy/dx", "dy/dx", "func"), ("eˣ", "exp()", "func"), ("ln", "ln()", "func")],
         [("sin", "sin()", "func"), ("cos", "cos()", "func"), ("tan", "tan()", "func"), ("√", "sqrt()", "func"), ("π", "pi", "func")]]
SIZE = 58
GAP = 9


class Key(tk.Canvas):
    """Botón circular/ovalado dibujado en un Canvas, con efecto al pulsar."""

    COLORS = {"num": (NUM, "#505054", TXT), "func": (FUNC, "#d4d4d8", "#000000"),
              "op": (ORANGE, "#ffc766", TXT), "act": (ORANGE, "#ffc766", TXT)}

    def __init__(self, master, text, kind, command, w=SIZE, h=SIZE, font=("Segoe UI", 17)):
        super().__init__(master, width=w, height=h, bg=BG, highlightthickness=0, cursor="hand2")
        self.base, self.press, fg = self.COLORS[kind]
        self.shape = self._pill(2, 2, w - 2, h - 2, self.base)
        self.label = self.create_text(w / 2, h / 2, text=text, fill=fg, font=font)
        self.command = command
        self.bind("<ButtonPress-1>", lambda e: self.itemconfigure(self.shape, fill=self.press))
        self.bind("<ButtonRelease-1>", self._release)

    def _pill(self, x1, y1, x2, y2, fill):
        r = (y2 - y1) / 2
        if x2 - x1 == y2 - y1:                      # cuadrado -> círculo
            return self.create_oval(x1, y1, x2, y2, fill=fill, outline="")
        return self.create_polygon(
            x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
            x1, y2, x1, y2 - r, x1, y1 + r, x1, y1, smooth=True, fill=fill, outline="")

    def _release(self, e):
        self.itemconfigure(self.shape, fill=self.base)
        if 0 <= e.x <= self.winfo_width() and 0 <= e.y <= self.winfo_height():
            self.command()


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Calculadora de Ecuaciones Diferenciales")
        self.geometry("1240x860")
        self.minsize(980, 640)
        self.configure(bg=BG)
        self._images: list = []
        self._queue: queue.Queue = queue.Queue()
        self._busy = False
        self._labels = [AUTO_LABEL] + [m.label for m in METHODS]
        self._key_by_label = {m.label: m.key for m in METHODS}
        self.mode = tk.StringVar(value="auto")
        self._style()
        self._build_left()
        self._build_output()
        self.bind("<Return>", lambda e: self.on_solve())
        self.entry.focus_set()
        self._on_mode()

    # ------------------------------------------------------------------ UI
    def _style(self) -> None:
        st = ttk.Style(self)
        st.theme_use("clam")
        st.configure("TCombobox", fieldbackground=PANEL, background=NUM, foreground=TXT,
                     arrowcolor=ORANGE, bordercolor=PANEL, lightcolor=PANEL, darkcolor=PANEL,
                     selectbackground=PANEL, selectforeground=TXT, padding=6)
        st.map("TCombobox", fieldbackground=[("readonly", PANEL), ("disabled", "#111113")],
               foreground=[("disabled", MUTED)], selectbackground=[("readonly", PANEL)])
        st.configure("Vertical.TScrollbar", background=NUM, troughcolor=BG, bordercolor=BG, arrowcolor=MUTED)
        st.configure("Horizontal.TScrollbar", background=NUM, troughcolor=BG, bordercolor=BG, arrowcolor=MUTED)
        self.option_add("*TCombobox*Listbox.background", PANEL)
        self.option_add("*TCombobox*Listbox.foreground", TXT)
        self.option_add("*TCombobox*Listbox.selectBackground", ORANGE)
        self.option_add("*TCombobox*Listbox.font", ("Segoe UI", 10))

    def _build_left(self) -> None:
        left = tk.Frame(self, bg=BG, padx=16, pady=14)
        left.pack(side="left", fill="y")
        title = tk.Frame(left, bg=BG)
        title.pack(fill="x")
        tk.Label(title, text="Calculadora de EDO", bg=BG, fg=TXT, font=("Segoe UI", 18, "bold")).pack(side="left")
        tk.Button(title, text="?  Manual", command=self.open_manual, bg=PANEL, fg=ORANGE, relief="flat", bd=0,
                  activebackground=NUM, activeforeground=ORANGE, cursor="hand2", padx=10, pady=4,
                  font=("Segoe UI", 10, "bold")).pack(side="right")
        tk.Label(left, text="Escribe o usa el teclado y pulsa  =", bg=BG, fg=MUTED,
                 font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 10))

        # Selector de modo (segmentado)
        seg = tk.Frame(left, bg=PANEL)
        seg.pack(fill="x")
        self.seg_btns = {}
        for val, txt in (("auto", "Automático"), ("manual", "Manual")):
            b = tk.Label(seg, text=txt, font=("Segoe UI", 11, "bold"), pady=7, cursor="hand2")
            b.pack(side="left", expand=True, fill="x", padx=2, pady=2)
            b.bind("<Button-1>", lambda e, v=val: self._set_mode(v))
            self.seg_btns[val] = b

        self.method = tk.StringVar(value=AUTO_LABEL)
        self.combo = ttk.Combobox(left, textvariable=self.method, values=self._labels, state="readonly",
                                  font=("Segoe UI", 10))
        self.combo.pack(fill="x", pady=(8, 4))
        self.combo.bind("<<ComboboxSelected>>", lambda e: self._on_method())
        self.hint = tk.Label(left, text="", bg=BG, fg=MUTED, font=("Segoe UI", 9), wraplength=380, justify="left")
        self.hint.pack(anchor="w", pady=(0, 6))

        # Pantalla
        disp = tk.Frame(left, bg=PANEL, padx=12, pady=10)
        disp.pack(fill="x")
        self.entry = tk.Entry(disp, font=("Consolas", 18), bg=PANEL, fg=TXT, insertbackground=ORANGE,
                              relief="flat", justify="right", highlightthickness=0)
        self.entry.pack(fill="x", ipady=8)
        tk.Button(disp, text="Cargar ejemplo", command=self.on_example, bg=PANEL, fg=ORANGE, relief="flat",
                  activebackground=PANEL, activeforeground=ORANGE_DK, cursor="hand2", bd=0,
                  font=("Segoe UI", 9, "underline")).pack(anchor="e", pady=(4, 0))

        self.alert_slot = tk.Frame(left, bg=BG)
        self.alert_slot.pack(fill="x", pady=4)
        self.alert = tk.Label(self.alert_slot, text="", bg="#3a1412", fg=RED, font=("Segoe UI", 10, "bold"),
                              wraplength=380, justify="left", anchor="w", padx=10, pady=8)

        # Teclado principal
        pad = tk.Frame(left, bg=BG)
        pad.pack(pady=(4, 0))
        for r, row in enumerate(KEYS):
            for c, (txt, ins, kind) in enumerate(row):
                k = Key(pad, txt, kind, lambda s=ins: self._press(s))
                if ins == "GO":
                    self.go_key = k
                k.grid(row=r, column=c, padx=GAP // 2, pady=GAP // 2)
        tk.Label(left, text=NL.join(f"{n} — {c}" for n, c in TEAM), bg=BG, fg=MUTED, justify="left",
                 font=("Segoe UI", 8)).pack(side="bottom", anchor="w")
        tk.Label(left, text="Integrantes", bg=BG, fg=ORANGE, font=("Segoe UI", 8, "bold")).pack(
            side="bottom", anchor="w", pady=(0, 0))
        # Teclas de funciones (más pequeñas)
        ext = tk.Frame(left, bg=BG)
        ext.pack(pady=(6, 0))
        for r, row in enumerate(EXTRA):
            for c, (txt, ins, kind) in enumerate(row):
                Key(ext, txt, kind, lambda s=ins: self._press(s), w=SIZE, h=38, font=("Segoe UI", 12)
                    ).grid(row=r, column=c, padx=GAP // 2, pady=3)

    def _build_output(self) -> None:
        wrap = tk.Frame(self, bg=BG)
        wrap.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=10)
        self.canvas = tk.Canvas(wrap, bg=BG, highlightthickness=0)
        vs = ttk.Scrollbar(wrap, orient="vertical", command=self.canvas.yview)
        hs = ttk.Scrollbar(wrap, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
        vs.pack(side="right", fill="y")
        hs.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.out = tk.Frame(self.canvas, bg=BG)
        self._win = self.canvas.create_window((0, 0), window=self.out, anchor="nw")
        self.out.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self._win, width=max(e.width, 600)))
        self.canvas.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(-1 * (e.delta // 120), "units"))
        self._welcome()

    # ------------------------------------------------------------ comportamiento
    def _set_mode(self, val: str) -> None:
        self.mode.set(val)
        self._on_mode()

    def _on_mode(self) -> None:
        for v, b in self.seg_btns.items():
            on = self.mode.get() == v
            b.configure(bg=ORANGE if on else PANEL, fg=TXT if on else MUTED)
        if self.mode.get() == "auto":
            self.combo.configure(state="disabled")
            self.method.set(AUTO_LABEL)
        else:
            self.combo.configure(state="readonly")
            if self.method.get() == AUTO_LABEL:
                self.method.set(METHODS[0].label)
        self._on_method()

    def _on_method(self) -> None:
        key = self._key_by_label.get(self.method.get())
        if key is None:
            self.hint.configure(text="El sistema identificará el método.\nEj.: y' + 2*y = exp(-x)   ·   "
                                     "(x+y) dx + x dy = 0   ·   y'' + 4*y = 0")
        else:
            m = BY_KEY[key]
            self.hint.configure(text=f"Formato: {m.hint}\nEj.: {m.example}")

    def open_manual(self) -> None:
        """Manual interactivo: cada método trae su formato y un botón que carga el ejemplo."""
        win = tk.Toplevel(self)
        win.title("Manual de usuario")
        win.configure(bg=BG)
        win.geometry("760x640")
        tk.Label(win, text="Manual interactivo", bg=BG, fg=TXT, font=("Segoe UI", 16, "bold")).pack(
            anchor="w", padx=16, pady=(12, 0))
        intro = ("Escribe con el teclado o las teclas de la calculadora:  y' · y'' · dy/dx · dx · dy.\n"
                 "Usa * para multiplicar y ^ para potencias. Funciones: exp, sin, cos, tan, ln, sqrt.\n"
                 "Pulsa «Probar» en un método: se activa el modo manual, se elige el método y se carga el ejemplo; "
                 "luego pulsa  =  para ver la solución y los pasos.")
        tk.Label(win, text=intro, bg=BG, fg=MUTED, justify="left", wraplength=720, font=("Segoe UI", 10)).pack(
            anchor="w", padx=16, pady=6)
        body = tk.Frame(win, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        cv = tk.Canvas(body, bg=BG, highlightthickness=0)
        sb = ttk.Scrollbar(body, orient="vertical", command=cv.yview)
        cv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        cv.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(cv, bg=BG)
        cv.create_window((0, 0), window=inner, anchor="nw", width=700)
        inner.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.bind("<Enter>", lambda e: cv.bind_all("<MouseWheel>", lambda ev: cv.yview_scroll(-(ev.delta // 120), "units")))
        cv.bind("<Leave>", lambda e: self.canvas.bind_all(
            "<MouseWheel>", lambda ev: self.canvas.yview_scroll(-(ev.delta // 120), "units")))
        for m in METHODS:
            card = tk.Frame(inner, bg=PANEL, padx=12, pady=8)
            card.pack(fill="x", pady=4)
            tk.Label(card, text=m.label, bg=PANEL, fg=ORANGE, font=("Segoe UI", 10, "bold")).pack(anchor="w")
            tk.Label(card, text=m.hint, bg=PANEL, fg=TXT, wraplength=520, justify="left").pack(anchor="w")
            tk.Label(card, text=m.example, bg=PANEL, fg=GREEN, font=("Consolas", 11)).pack(anchor="w", pady=(2, 0))
            tk.Button(card, text="Probar", command=lambda mm=m: self._try(mm, win), bg=ORANGE, fg=TXT, relief="flat",
                      bd=0, cursor="hand2", padx=12, pady=3, font=("Segoe UI", 9, "bold")).place(relx=1, x=-6, y=6, anchor="ne")

    def _try(self, m, win) -> None:
        self.mode.set("manual")
        self._on_mode()
        self.method.set(m.label)
        self._on_method()
        self.entry.delete(0, "end")
        self.entry.insert(0, m.example)
        win.destroy()
        self.on_solve()

    def _press(self, s: str) -> None:
        if s == "AC":
            return self.on_clear()
        if s == "GO":
            return self.on_solve()
        self.entry.focus_set()
        if s == "BS":
            i = self.entry.index("insert")
            if i > 0:
                self.entry.delete(i - 1)
            return
        self.entry.insert("insert", s)
        if s.endswith("()"):
            self.entry.icursor(self.entry.index("insert") - 1)

    def on_clear(self) -> None:
        self.entry.delete(0, "end")
        self._alert("")
        self._welcome()
        self.entry.focus_set()

    def on_example(self) -> None:
        key = self._key_by_label.get(self.method.get())
        text = BY_KEY[key].example if key else "y' + y/x = x*y^2"
        self.entry.delete(0, "end")
        self.entry.insert(0, text)

    def _alert(self, msg: str) -> None:
        if msg:
            self.alert.configure(text=msg)
            self.alert.pack(fill="x")
        else:
            self.alert.pack_forget()

    def on_solve(self) -> None:
        if self._busy:
            return
        text = self.entry.get()
        key = AUTO_KEY if self.mode.get() == "auto" else self._key_by_label[self.method.get()]
        self._busy = True
        self._alert("")
        self.hint.configure(text="Calculando…")
        threading.Thread(target=self._work, args=(text, key), daemon=True).start()
        self.after(80, self._poll)

    def _work(self, text: str, key: str) -> None:
        try:
            self._queue.put(("ok", solve(text, key)))
        except EdoError as exc:
            self._queue.put(("err", exc))
        except Exception as exc:  # nunca dejar caer la aplicación
            self._queue.put(("err", EdoError(f"Error inesperado: {type(exc).__name__}: {exc}")))

    def _poll(self) -> None:
        try:
            kind, payload = self._queue.get_nowait()
        except queue.Empty:
            self.after(80, self._poll)
            return
        self._busy = False
        if kind == "ok":
            self._show(payload)
        else:
            self._on_method()
            self._error(payload)

    # ---------------------------------------------------------------- salida
    def _clear_out(self) -> None:
        for w in self.out.winfo_children():
            w.destroy()
        self._images.clear()
        self.canvas.yview_moveto(0)

    def _math(self, parent, tex: str, size: float = 15, pad=(10, 3)) -> None:
        img = latex_image(tk, tex, size, color="white")
        self._images.append(img)
        tk.Label(parent, image=img, bg=PANEL).pack(anchor="w", padx=pad[0], pady=pad[1])

    def _card(self, title: str, color: str = ORANGE) -> tk.Frame:
        outer = tk.Frame(self.out, bg=PANEL, padx=14, pady=10)
        outer.pack(fill="x", pady=6, padx=2)
        tk.Label(outer, text=title, bg=PANEL, fg=color, font=("Segoe UI", 11, "bold")).pack(anchor="w")
        return outer

    def _welcome(self) -> None:
        self._clear_out()
        c = self._card("Cómo usar")
        msg = ("1. Elige Automático o Manual (con el método en el menú).\n"
               "2. Escribe la ecuación con el teclado o con las teclas: y', y'', dy/dx;\n"
               "   usa * para multiplicar y ^ para potencias. Forma diferencial: M dx + N dy = 0.\n"
               "3. Pulsa  =  (o Enter): verás la solución y cada paso intermedio.")
        tk.Label(c, text=msg, bg=PANEL, fg=TXT, justify="left", font=("Segoe UI", 10)).pack(anchor="w", pady=(6, 0))

    def _error(self, exc: EdoError) -> None:
        prefix = "" if isinstance(exc, ParseError) else "No se puede resolver: "
        self._alert(f"⚠ {prefix}{exc}")

    def _show(self, sol: Solution) -> None:
        self._clear_out()
        if self.mode.get() == "auto":
            self.method.set(sol.method_name)        # activa en el menú el método detectado
        self.hint.configure(text=f"Método: {sol.method_name}")
        head = self._card(f"Solución  ·  {sol.method_name}")
        for line in sol.answer:
            self._math(head, line, size=18, pad=(4, 5))
        if sol.classification:
            c = self._card("Clasificación automática")
            for name, why in sol.classification:
                ok = why.startswith("Aplicable")
                tk.Label(c, text=f"{'✔' if ok else '✘'} {name}: {why}", bg=PANEL, anchor="w", justify="left",
                         wraplength=760, fg=GREEN if ok else MUTED).pack(anchor="w")
        steps = self._card("Trazabilidad — paso a paso")
        for kind, content in sol.steps:
            if kind == "head":
                tk.Label(steps, text=content, bg=PANEL, fg=ORANGE, font=("Segoe UI", 10, "bold")).pack(
                    anchor="w", pady=(10, 0))
            elif kind == "text":
                tk.Label(steps, text=content, bg=PANEL, fg=TXT, justify="left", wraplength=760).pack(
                    anchor="w", padx=6)
            else:
                self._math(steps, content, size=14)


def run() -> None:
    App().mainloop()
