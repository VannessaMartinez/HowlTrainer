"""
ui/pages/tones_page.py
----------------------
Página de práctica (Práctica: Detección de Feedback).

Novedad en esta versión:
- Recibimos un callback opcional `go_to_stats` desde main.py.
- Añadimos un botón “📈 Ver Stats” que, al pulsarse, invoca ese callback:
  cambia a la pestaña de Stats y refresca el reporte.

Ventaja pedagógica:
- Mantiene el acoplamiento bajo: TonesPage no “sabe” cómo está implementada
  la pestaña de Stats; solo llama a una función que le inyectan.
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox
import time

from core.bands import BANDS, nearest, band_distance
from core.synth import make_feedback
from core.audio_io import play_async, stop_all
from ai.rules import feedback_text
from ai.policy import next_band, update as policy_update
from data_logger import log_attempt
from config import FS


class TonesPage(ttk.Frame):
    def __init__(self, parent, go_to_stats=None):

        super().__init__(parent)
        self.go_to_stats = go_to_stats  # guardamos el callback para usarlo cuando haga falta

         # Estado interno
        self.target_band: int | None = None   # banda objetivo actual (en Hz)
        self.stream = None                    # stream de audio activo (si está sonando)
        self.t0 = None                        # timestamp para medir tiempo de respuesta

        """
        go_to_stats: función opcional (inyectada por main.py) que, cuando se llama,
        cambia a la pestaña de Stats y refresca su reporte. Esto nos permite, desde
        la página de práctica, saltar a “ver resultados” sin duplicar lógica aquí.
        """
                # === Preferencia de depuración: mostrar u ocultar el objetivo ===
        # BooleanVar guarda el estado del Checkbutton (True/False).
        self.show_target_var = tk.BooleanVar(value=False)

        # Colocamos el Checkbutton debajo del panel superior, para fácil acceso.
        dbg = ttk.Frame(self)
        dbg.pack(fill="x", pady=(2, 6))

        chk = ttk.Checkbutton(
            dbg,
            text="Mostrar objetivo (debug)",
            variable=self.show_target_var,
            command=self.update_target_label  # cuando cambie, actualiza el texto
        )
        
        chk.pack(side="left")


        # === Título ===
        title = ttk.Label(self, text="Práctica: Detección de Feedback", font=("Helvetica", 16, "bold"))
        title.pack(pady=(0, 10), anchor="w")

        # === Panel superior: control de objetivo y reproducción ===
        top = ttk.Frame(self)
        top.pack(fill="x", pady=6)

        self.lbl_target = ttk.Label(top, text="Objetivo: — Hz (oculto)")
        self.btn_new = ttk.Button(top, text="🎯 Nuevo objetivo", command=self.on_new_target)
        self.btn_play = ttk.Button(top, text="▶ Reproducir", command=self.on_play)
        self.btn_stop = ttk.Button(top, text="⏹ Detener", command=self.on_stop)

        self.lbl_target.pack(side="left")
        self.btn_new.pack(side="right", padx=(6, 0))
        self.btn_play.pack(side="right", padx=(6, 0))
        self.btn_stop.pack(side="right")

        # === Selector de respuesta + acciones ===
        sel_box = ttk.Frame(self)
        sel_box.pack(fill="x", pady=10)

        ttk.Label(sel_box, text="Tu respuesta (Hz):").pack(side="left")

        # Desplegable con las bandas de 1/3 de octava
        self.answer_var = tk.StringVar(value=str(BANDS[7]))  # valor por defecto
        self.cbo_bands = ttk.Combobox(sel_box, textvariable=self.answer_var, width=10, state="readonly")
        self.cbo_bands["values"] = [str(b) for b in BANDS]
        self.cbo_bands.current(BANDS.index(int(self.answer_var.get())))
        self.cbo_bands.pack(side="left", padx=8)

        self.btn_answer = ttk.Button(sel_box, text="✅ Responder", command=self.on_answer)
        self.btn_answer.pack(side="left", padx=8)

        # 🔥 NUEVO: botón para abrir la pestaña de Stats y refrescar reporte
        self.btn_stats = ttk.Button(sel_box, text="📈 Ver Stats", command=self.on_open_stats)
        self.btn_stats.pack(side="left", padx=(8, 0))

        # === Área de feedback pedagógico ===
        self.msg = tk.Text(self, height=6, wrap="word")
        self.msg.configure(state="disabled")
        self.msg.pack(fill="both", expand=True, pady=(8, 0))

        # === Barra de estado (abajo) ===
        self.status = ttk.Label(self, text="Listo.", relief="sunken", anchor="w")
        self.status.pack(fill="x", pady=(8, 0))

        # Estado inicial
        self.on_new_target(first_time=True)

    # ---------------- Utilidades UI ----------------

    def set_status(self, text: str):
        self.status.config(text=text)

    def set_message(self, text: str):
        self.msg.configure(state="normal")
        self.msg.delete("1.0", "end")
        self.msg.insert("1.0", text)
        self.msg.configure(state="disabled")

    def safe_stop_audio(self):
        """Detiene audio activo y limpia el stream sin romper la UI."""
        try:
            stop_all()
        except Exception:
            pass
        self.stream = None

    
    def update_target_label(self):
        """
    Actualiza la etiqueta del objetivo según el estado del checkbox.
    NO se llama a sí misma (evitamos recursión).
    """
        # La etiqueta aún no existe (muy temprano)
        if not hasattr(self, "lbl_target") or self.lbl_target is None:
            return

        # Lee el estado del checkbox de forma segura
        try:
            show = bool(self.show_target_var.get())
        except Exception:
            show = False

        # Si no hay objetivo aún, muestra oculto
        if self.target_band is None:
            self.lbl_target.config(text="Objetivo: — Hz (oculto)")
            return

        # Decide el texto sin auto-llamados
        if show:
            self.lbl_target.config(text=f"Objetivo: {self.target_band} Hz  (DEBUG)")
        else:
            self.lbl_target.config(text="Objetivo: — Hz (oculto)")



    # ---------------- Callbacks ----------------

    def on_open_stats(self):
        """
        Handler del botón “📈 Ver Stats”.
        Si existe el callback `go_to_stats`, lo invoca para cambiar de pestaña
        y refrescar el reporte. Si no, informa al usuario.
        """
        if callable(self.go_to_stats):
            self.go_to_stats()
        else:
            messagebox.showinfo("Stats", "La página de Stats no está disponible en esta configuración.")

    def on_new_target(self, first_time: bool = False):
        """
        Elige una nueva banda objetivo usando la política simple.
        Mantenemos el objetivo oculto para un entrenamiento más “ciego”.
        """
        # Si había objetivo previo, pasamos su índice para rotación más natural.
        last_idx = None
        if self.target_band in BANDS:
            last_idx = BANDS.index(self.target_band)

        self.target_band = next_band(last_idx)  # política simple de siguiente objetivo
        self.lbl_target.config(text=f"Objetivo: — Hz (oculto)")  # para depuración, puedes mostrar self.target_band
        self.set_status("Nuevo objetivo listo. Presiona ▶ Reproducir para escucharlo.")
        self.set_message("Consejo: ubica si el tono está en región grave, media o aguda.")

        # Reset de cronómetro y audio
        self.t0 = None
        self.safe_stop_audio()

        if not first_time:
            self.focus_set()

    def on_play(self):
        """
        Genera un feedback simulado en la banda objetivo y lo reproduce en modo asíncrono,
        para que la UI no se congele durante la reproducción.
        """
        if not self.target_band:
            messagebox.showinfo("Info", "Primero crea un objetivo con 'Nuevo objetivo'.")
            return

        sig = make_feedback(self.target_band, dur=1.8, fs=FS, mode="pure") # modo puro
        #sig = make_feedback(self.target_band, dur=1.8, fs=FS, mode="mixed", mix=0.15, q=35.0) #ensuciar un poquito
        #sig = make_feedback(self.target_band, dur=1.8, fs=FS, mode="narrowband", q=30.0) # realismo fuerte


        # Reproduce con un margen de seguridad en nivel
        self.safe_stop_audio()
        self.stream = play_async(sig, fs=FS, gain_db=-9.0)

        # Marca tiempo de inicio para medir RT
        self.t0 = time.perf_counter()
        self.set_status(f"Reproduciendo objetivo oculto… ({self.target_band} Hz)")

    def on_stop(self):
        """Detiene la reproducción actual (si la hay)."""
        self.safe_stop_audio()
        self.set_status("Audio detenido.")

    def on_answer(self):
        """
        Lee la banda seleccionada por el usuario, calcula feedback pedagógico,
        registra el intento (CSV) y actualiza la política para el siguiente objetivo.
        """
        if self.target_band is None:
            messagebox.showinfo("Info", "No hay objetivo activo. Haz clic en 'Nuevo objetivo'.")
            return

        self.safe_stop_audio()

        try:
            user_val = int(self.answer_var.get())
        except ValueError:
            messagebox.showerror("Error", "Selecciona una banda válida en Hz.")
            return

        user_band = nearest(user_val)
        rt_ms = 0
        if self.t0 is not None:
            rt_ms = int((time.perf_counter() - self.t0) * 1000)

        # Feedback pedagógico basado en reglas simbólicas
        msg = feedback_text(self.target_band, user_band)
        self.set_message(msg)

        correct = int(user_band == self.target_band)
        dist = band_distance(self.target_band, user_band)

        # Log de intento
        try:
            log_attempt("tk_ui", self.target_band, user_band, correct, rt_ms)
        except Exception as e:
            messagebox.showwarning("Logger", f"No se pudo registrar el intento: {e}")

        # Actualizar política (para que próximo objetivo tenga en cuenta el desempeño)
        try:
            policy_update(self.target_band, correct)
        except Exception:
            pass

        self.set_status(
            f"Respuesta: {user_band} Hz  |  {'✔ Correcto' if correct else f'✖ Dist={dist} bandas'}  |  RT={rt_ms} ms"
        )

        # Prepara siguiente objetivo (flujo continuo de práctica)
        self.on_new_target()

        # (Opcional) abrir stats automáticamente después de responder:
        # if callable(self.go_to_stats): self.go_to_stats()
