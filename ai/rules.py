"""
ai/rules.py
------------
Reglas simbólicas (explicables) para el EarTrainer – Detección de Feedback.

Este módulo NO reproduce audio ni entrena modelos. Solo:
- Traduce frecuencias en descriptores "humanos" (cuerpo, presencia, brillo).
- Genera mensajes de retroalimentación pedagógicos (correcto / casi / no).
- Sugiere una acción técnica típica: un notch EQ en la banda del feedback.

Importante: no tiene prints ni código de ejecución directa para que el import sea limpio.
"""

from __future__ import annotations
from typing import Dict

# Importamos utilidades del módulo de bandas.
# Estas funciones son "la regla del juego" de las frecuencias.
from core.bands import (
    BANDS,         # Lista de bandas "oficiales" (1/3 de octava)
    nearest,       # Mapea una frecuencia real a la banda más cercana
    band_distance, # Mide "cuántas bandas" separan dos frecuencias
    region_of,     # Clasifica una frecuencia como graves / medios / agudos
    index_of       # Posición de una banda en BANDS (para saber si subir/bajar)
)

# ---------------------------------------------------------------------
# 1) Descriptores auditivos "humanos" para explicar qué se está oyendo
# ---------------------------------------------------------------------

def freq_to_descriptor(freq_hz: float) -> str:
    """
    Devuelve un texto corto y pedagógico que describe la sensación de la frecuencia.
    No pretende ser científico al 100%, sino útil para entrenar el oído.
    """
    f = float(freq_hz)
    if f < 120:
        return "subgraves / muy profundo"
    if f < 250:
        return "graves / cuerpo"
    if f < 500:
        return "medios-graves / calidez"
    if f < 1000:
        return "medios / claridad"
    if f < 2000:
        return "presencia baja (1–2 kHz)"
    if f < 4000:
        return "presencia / agudos medios (2–4 kHz)"
    if f < 8000:
        return "brillo / sibilancia (4–8 kHz)"
    return "aire / superagudos (8 kHz+)"

# ---------------------------------------------------------------
# 2) Sugerencia técnica típica para “matar” feedback con un notch
# ---------------------------------------------------------------

def notch_suggestion(freq_hz: float) -> Dict[str, float]:
    """
    Devuelve una configuración conservadora para aplicar un notch EQ:
      - Usamos la banda oficial más cercana (consistencia con el resto del sistema).
      - Q ≈ 8: lo bastante estrecho para no quitar demasiado del programa.
      - Ganancia ≈ –9 dB como punto de partida (ajustable en uso real).
    """
    band = float(nearest(freq_hz))
    return {"freq": band, "Q": 8.0, "gain_db": -9.0}

# -------------------------------------------------------------
# 3) Pista de escucha corta según la región (graves / medios...)
# -------------------------------------------------------------

def region_hint(freq_hz: float) -> str:
    """
    Devuelve un tip breve para orientar 'dónde escuchar' según la región.
    Esto guía al usuario hacia la textura correcta (gordo, voz, brillo).
    """
    r = region_of(freq_hz)
    if r == "graves":
        return "fíjate si el pitido suena más 'gordo' o 'profundo'."
    if r == "medios":
        return "nota si molesta en la zona de la voz o de la claridad."
    return "escucha un 'silbido' fino o brillo en la parte alta."

# ---------------------------------------------------------
# 4) Mensaje principal de feedback tras la respuesta del usuario
# ---------------------------------------------------------

def feedback_text(true_freq_hz: float, user_freq_hz: float) -> str:
    """
    Genera un mensaje pedagógico después de una respuesta.

    Entradas:
        true_freq_hz : frecuencia real del feedback (target del ejercicio)
        user_freq_hz : frecuencia que eligió la persona usuaria

    Reglas:
        - Si coincide la misma banda → “Correcto” + descriptor + sugerencia notch.
        - Si está a 1 banda → “Casi” + orientación (subir/bajar) + tip de escucha.
        - Si está más lejos → “No” + distancia, dirección y tip de escucha.
    """
    # Convertimos a bandas oficiales para "hablar el mismo idioma" en todo el sistema.
    b_true = nearest(true_freq_hz)
    b_user = nearest(user_freq_hz)
    d = band_distance(b_true, b_user)

    desc = freq_to_descriptor(b_true)   # cómo se siente esa banda
    tip  = region_hint(b_true)          # dónde poner la atención

    if d == 0:
        # Acierto exacto → felicitamos y damos acción técnica concreta
        notch = notch_suggestion(b_true)
        return (f"✔ Correcto: {b_true} Hz ({desc}). "
                f"Sugerencia técnica: notch en {int(notch['freq'])} Hz, "
                f"Q≈{notch['Q']}, {notch['gain_db']} dB.")

    # Si se equivocó, damos dirección (hacia más agudo o hacia más grave)
    dir_txt = _direction_text(b_true, b_user)

    if d == 1:
        # Error por una banda → casi acierta
        return (f"≈ Casi. Era {b_true} Hz ({desc}). "
                f"Te faltó {dir_txt}. Tip: {tip}")

    # Error grande → explicamos distancia y reforzamos el tip
    return (f"✖ No. Era {b_true} Hz ({desc}). Estabas a {d} bandas. "
            f"Intenta buscar un tono {dir_txt}. Tip: {tip}")

# ---------------------------------------------------------
# 5) Utilidad interna: texto de dirección del error (subir/bajar)
# ---------------------------------------------------------

def _direction_text(b_true: int, b_user: int) -> str:
    """
    Indica si hay que ir "hacia más agudo" (subir) o "hacia más grave" (bajar)
    para llegar desde la banda elegida a la verdadera en la escala BANDS.
    """
    i_true = index_of(b_true)
    i_user = index_of(b_user)
    if i_user < i_true:
        return "subir (hacia más agudo)"
    if i_user > i_true:
        return "bajar (hacia más grave)"
    return "ajustar mínimamente"

# Exportamos explícitamente los símbolos públicos de este módulo
__all__ = [
    "freq_to_descriptor",
    "notch_suggestion",
    "region_hint",
    "feedback_text",
]
