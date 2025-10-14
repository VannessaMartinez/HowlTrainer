"""
core/synth.py
--------------
Genera sonidos para el EarTrainer (det. feedback).

Incluye:
- Tono puro (seno) con fades para evitar clicks.
- Ruido rosa (1/f) simple (filtrado de blanco) con normalización + fades.
- "Feedback" en tres modos:
    * pure        → seno puro (entrenamiento básico, limpio)
    * narrowband  → ruido estrecho centrado en f0 (más realista/“sucio”)
    * mixed       → mezcla seno + narrowband (control de mix)

Diseño:
- Devolvemos float32 en rango [-1, 1].
- El control de volumen final puede aplicarse en audio_io (gain_db), pero aquí
  dejamos señales ya “limpias” y sin clicks.
"""

from __future__ import annotations
import numpy as np
from scipy import signal
from config import FS, DUR_SEC


# =======================
# Utilidades de amplitud
# =======================

def _db_to_lin(db: float) -> float:
    """Convierte dBFS a lineal (amplitud)."""
    return float(10.0 ** (db / 20.0))

def _safe_float32(x: np.ndarray) -> np.ndarray:
    """Clip a [-1, 1] y devuelve float32 (para sounddevice)."""
    return np.clip(x, -1.0, 1.0).astype(np.float32)

def _apply_fades(x: np.ndarray, fs: int, fade_ms: float = 10.0) -> np.ndarray:
    """Aplica fade in/out lineales cortos para evitar clicks."""
    n = len(x)
    nfade = max(1, int(fs * fade_ms / 1000.0))
    nfade = min(n // 2, nfade)
    if nfade > 1:
        ramp_in = np.linspace(0.0, 1.0, nfade, dtype=np.float64)
        ramp_out = np.linspace(1.0, 0.0, nfade, dtype=np.float64)
        x[:nfade] *= ramp_in
        x[-nfade:] *= ramp_out
    return x


# ==================
# Generadores básicos
# ==================

def make_tone(freq_hz: float, dur: float = DUR_SEC, fs: int = FS, fade_ms: float = 10.0) -> np.ndarray:
    """
    Seno puro a freq_hz con fades. Devuelve [-1, 1] float32.
    (El volumen final lo puedes manejar en audio_io con gain_db).
    """
    t = np.arange(int(dur * fs), dtype=np.float64) / fs
    x = np.sin(2.0 * np.pi * float(freq_hz) * t)  # seno limpio
    x = _apply_fades(x, fs, fade_ms=fade_ms)
    return _safe_float32(x)


def make_pink_noise(dur: float = DUR_SEC, fs: int = FS, fade_ms: float = 10.0) -> np.ndarray:
    """
    Ruido rosa (aprox) filtrando ruido blanco con un pasa-bajos suave.
    Normalizamos pico y aplicamos fades para evitar clicks.
    """
    n = int(fs * dur)
    rng = np.random.default_rng()
    white = rng.standard_normal(n).astype(np.float64)

    # Filtro simple (no es 1/f exacto, pero suficiente para “ambiente”)
    b, a = signal.butter(1, 0.01, btype="low")  # 0.01 * Nyquist
    pink = signal.lfilter(b, a, white)

    # Normaliza a 0.999 (pico) + fades
    m = max(1e-9, float(np.max(np.abs(pink))))
    pink = (pink / m) * 0.999
    pink = _apply_fades(pink, fs, fade_ms=fade_ms)
    return _safe_float32(pink)


# ==========================
# Simulación de "feedback"
# ==========================

def _narrowband_noise(freq_hz: float, dur: float, fs: int, q: float = 30.0, fade_ms: float = 10.0) -> np.ndarray:
    """
    Ruido estrecho centrado en freq_hz: ruido rosa pasado por un pico resonante.
    q alto = banda estrecha. Útil para ensuciar de manera realista.
    """
    noise = make_pink_noise(dur=dur, fs=fs, fade_ms=fade_ms).astype(np.float64)

    # Pico resonante (RBJ iirpeak a partir de w0 normalizado a Nyquist)
    w0 = float(freq_hz) / (fs / 2.0)  # 0..1 (1 = Nyquist)
    w0 = max(1e-6, min(0.999999, w0))  # evitar extremos
    b, a = signal.iirpeak(w0, Q=q)

    y = signal.lfilter(b, a, noise)

    # Normaliza (pico) y aplica fades de nuevo por si el filtrado genera transitorios
    m = max(1e-9, float(np.max(np.abs(y))))
    y = (y / m) * 0.999
    y = _apply_fades(y, fs, fade_ms=fade_ms)
    return _safe_float32(y)


def make_feedback(
    freq_hz: float,
    dur: float = DUR_SEC,
    fs: int = FS,
    *,
    mode: str = "pure",          # "pure" | "narrowband" | "mixed"
    q: float = 30.0,             # ancho de banda del pico (solo para narrow/mixed)
    mix: float = 0.2,            # proporción de ruido en "mixed" (0..1)
    fade_ms: float = 10.0
) -> np.ndarray:
    """
    Genera el estímulo “feedback” con distintos modos:
      - pure:       seno puro (limpio) → entrenamiento básico
      - narrowband: ruido estrecho alrededor de f0 (más “sucio” y realista)
      - mixed:      mezcla seno + ruido estrecho (control 'mix')

    Nota: El volumen final (dB) se recomienda manejarlo en audio_io.play_* con gain_db.
    Aquí dejamos señales normalizadas a [-1, 1] con fades.
    """
    mode = (mode or "pure").lower()

    if mode == "pure":
        return make_tone(freq_hz, dur=dur, fs=fs, fade_ms=fade_ms)

    if mode == "narrowband":
        return _narrowband_noise(freq_hz, dur=dur, fs=fs, q=q, fade_ms=fade_ms)

    # "mixed" → seno + narrowband con proporción 'mix'
    s = make_tone(freq_hz, dur=dur, fs=fs, fade_ms=fade_ms).astype(np.float64)
    n = _narrowband_noise(freq_hz, dur=dur, fs=fs, q=q, fade_ms=fade_ms).astype(np.float64)

    mix = float(np.clip(mix, 0.0, 1.0))
    x = (1.0 - mix) * s + mix * n

    # Normaliza a 0.999 para evitar clipping y devuelve float32
    m = max(1e-9, float(np.max(np.abs(x))))
    x = (x / m) * 0.999
    return _safe_float32(x)


# ==========================
# Prueba rápida en ejecución
# ==========================

if __name__ == "__main__":
    print(f"🎛️  FS={FS} Hz, DUR={DUR_SEC}s")

    tone = make_tone(1000)
    nb = _narrowband_noise(1000, DUR_SEC, FS)
    fb_pure = make_feedback(1000, mode="pure")
    fb_nb = make_feedback(1000, mode="narrowband", q=30.0)
    fb_mix = make_feedback(1000, mode="mixed", q=30.0, mix=0.25)

    print("OK: tone", tone.shape, "fb_pure", fb_pure.shape, "fb_nb", fb_nb.shape, "fb_mix", fb_mix.shape)
