"""
ui/dialogs/about.py
-------------------
Diálogo "Acerca de / Ayuda" para la app EarTrainer – Detección de Feedback.

¿Por qué un diálogo propio (Toplevel) y no messagebox?
- Podemos mostrar texto largo y formateado (con saltos de línea).
- Añadimos scroll si el contenido crece.
- No bloqueamos la expansión a futuro (links, botones extra, etc.).
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk

APP_TITLE = "HowlTrainer – Detección de Feedback"
APP_VERSION = "v0.1.0"   # puedes actualizar este número cuando hagas entregas

HELP_TEXT = f"""\
{APP_TITLE} ({APP_VERSION})

OBJETIVO
- Entrenar la identificación rápida de bandas de realimentación (feedback) en mezcla.
- Módulo base: tonos ocultos en bandas de 1/3 de octava (simulación de feedback).

FLUJO DE USO (Pestaña "Práctica")
1) Pulsa "🎯 Nuevo objetivo" para fijar internamente una banda (frecuencia) oculta.
2) Pulsa "▶ Reproducir" para escuchar el tono simulado.
3) Elige tu respuesta en el desplegable (Hz) y pulsa "✅ Responder".
4) Se muestra retroalimentación pedagógica y se registra el intento (CSV).
5) Automáticamente se prepara un nuevo objetivo (flujo continuo de práctica).

CONSEJOS
- Si estás empezando, activa "Mostrar objetivo (debug)" para entender las bandas.
- Piensa en regiones primero: graves (<500 Hz), medios (500–2k), agudos (≥2k).
- Concéntrate en identificar + o – “una banda” de desplazamiento respecto al objetivo.
- Practica series cortas (5–10 min) y revisa las estadísticas.

PESTAÑA "Stats"
- Lee el CSV (por defecto: data/session_log.csv).
- Si hay pocos errores, verás un Fallback: accuracy global, peores bandas,
  errores por región y barritas ASCII por banda.
- Si hay ≥8 errores, corre KMeans para detectar patrones de confusión y te sugiere
  una región de práctica prioritaria.

ARCHIVO DE DATOS
- Cada intento se registra en: data/session_log.csv
  columnas: timestamp, module, band_true, band_user, correct, rt_ms.

IDEAS DE MEJORA (futuras)
- Atajos de teclado (N: nuevo objetivo, Space: reproducir/detener, Enter: responder).
- Control de volumen por slider.
- Matriz de confusiones por desplazamiento de banda.
- Módulo de "ruido rosa + realce" como segundo ejercicio.

Créditos
- Síntesis/Audio: numpy + sounddevice
- Analítica: pandas + scikit-learn (KMeans)
- UI: Tkinter (ttk)
"""

class AboutDialog(tk.Toplevel):
    """
    Ventana modal simple (Toplevel) con un Text de solo lectura y scroll.
    La hacemos modal con grab_set() para "bloquear" la app principal hasta cerrar.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Acerca de / Ayuda")
        self.minsize(520, 420)

        # Ubicar la ventana relativa al parent (centrado simple)
        self.geometry("+%d+%d" % (parent.winfo_rootx() + 40, parent.winfo_rooty() + 40))

        # ---- Contenido principal: Text + Scrollbar ----
        frame = ttk.Frame(self, padding=12)
        frame.pack(fill="both", expand=True)

        txt = tk.Text(frame, wrap="word", height=20)
        txt.insert("1.0", HELP_TEXT)
        txt.configure(state="disabled")  # solo lectura
        txt.pack(side="left", fill="both", expand=True)

        scroll = ttk.Scrollbar(frame, command=txt.yview)
        scroll.pack(side="right", fill="y")
        txt.configure(yscrollcommand=scroll.set)

        # ---- Botonera inferior ----
        btnbar = ttk.Frame(self, padding=(0, 6, 0, 0))
        btnbar.pack(fill="x")

        btn_close = ttk.Button(btnbar, text="Cerrar", command=self.destroy)
        btn_close.pack(side="right")

        # Modal simple (captura el foco hasta cerrar)
        self.transient(parent)   # aparece como dependiente de la ventana principal
        self.grab_set()
        self.focus_set()
