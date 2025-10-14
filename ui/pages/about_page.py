"""
ui/pages/about_page.py
----------------------
Pestaña "About / Help" con logo + texto desplazable.
- Usa grid para que el texto siempre sea visible y expansible.
- Reduce automáticamente el logo si es muy grande (subsample de Tk).
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk

APP_TITLE = "Howl Trainer – Detección de Feedback"
APP_VERSION = "v0.1.0"

HELP_TEXT = f"""\
{APP_TITLE} ({APP_VERSION})

OBJETIVO
- Entrenar la identificación rápida de bandas de realimentación (feedback) en mezcla.
- Módulo base: tonos ocultos en bandas de 1/3 de octava (simulación de feedback).

FLUJO DE USO (Pestaña "Práctica")
1) "🎯 Nuevo objetivo" fija internamente una banda (frecuencia) oculta.
2) "▶ Reproducir" para oír el objetivo.
3) Selecciona tu respuesta (Hz) y pulsa "✅ Responder".
4) Verás retroalimentación pedagógica y se registra el intento (CSV).
5) Se prepara automáticamente un nuevo objetivo.

CONSEJOS
- Si empiezas, activa "Mostrar objetivo (debug)" para familiarizarte con bandas.
- Piensa en regiones: graves (<500 Hz), medios (500–2000 Hz), agudos (≥2000 Hz).
- Trabaja series cortas (5–10 min) y revisa la pestaña "Stats".

PESTAÑA "Stats"
- Pocos errores: Fallback (accuracy global, peores bandas y barritas ASCII).
- Con ≥8 errores: KMeans detecta patrones de confusión y sugiere región de práctica.

ARCHIVO DE DATOS
- CSV: data/session_log.csv
  columnas: timestamp, module, band_true, band_user, correct, rt_ms.

IDEAS DE MEJORA
- Atajos (N: nuevo, Space: reproducir/detener, Enter: responder)
- Slider de volumen
- Matriz de confusiones (desplazamiento por bandas)
- Módulo "ruido rosa + realce"

Créditos
- Audio: numpy + sounddevice
- Analítica: pandas + scikit-learn (KMeans)
- UI: Tkinter (ttk)
"""

class AboutPage(ttk.Frame):
    """Pestaña con logo (ajustado) y texto con scrollbar."""
    def __init__(self, parent):
        super().__init__(parent)

        # --- Layout base con grid ---
        self.columnconfigure(0, weight=1)   # única columna expansible
        self.rowconfigure(1, weight=1)      # fila del texto es la que se expande

        # ===== Encabezado (logo + título) =====
        header = ttk.Frame(self, padding=(12, 12, 12, 6))
        header.grid(row=0, column=0, sticky="ew")  # no expandimos en Y

        # Intentamos cargar el logo y reducirlo si es grande
        self._logo_img = None
        try:
            img = tk.PhotoImage(file="assets/howl_logo.png")
            # Si el logo es muy grande, lo reducimos (target ~128–160 px de alto)
            max_h = 128
            if img.height() > max_h:
                factor = max(2, int(round(img.height() / max_h)))
                img = img.subsample(factor, factor)
            self._logo_img = img
            ttk.Label(header, image=self._logo_img).pack(side="left", padx=(0, 8))
        except Exception as e:
            # Si no hay logo o falla, seguimos sin imagen
            print(f"[About] Logo no disponible: {e}")

        ttk.Label(
            header,
            text="Acerca de / Ayuda",
            font=("Helvetica", 16, "bold")
        ).pack(side="left", anchor="w")

        # ===== Cuerpo (texto + scrollbar) =====
        body = ttk.Frame(self, padding=(12, 0, 12, 12))
        body.grid(row=1, column=0, sticky="nsew")  # esta sección se expande

        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        txt = tk.Text(body, wrap="word")
        txt.insert("1.0", HELP_TEXT)
        txt.configure(state="disabled")
        txt.grid(row=0, column=0, sticky="nsew")

        scroll = ttk.Scrollbar(body, command=txt.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        txt.configure(yscrollcommand=scroll.set)
