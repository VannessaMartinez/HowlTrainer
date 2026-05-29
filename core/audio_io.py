"""
core/audio_io.py
----------------
Funciones utilitarias para reproducir audio numpy con sounddevice.

Diseño:
- Trabaja con arrays 1D (mono) en rango [-1.0, 1.0].
- Permite aplicar ganancia de salida (volumen) de forma segura.
- Aplica un pequeño fade-in/out para evitar clics al empezar/terminar.
- Ofrece reproducción bloqueante (play_blocking) y asíncrona (play_async).

Requisitos:
    pip install sounddevice
"""

from __future__ import annotations
import numpy as np
import sounddevice as sd

from config import FS


# --------------------------
# Pequeñas utilidades de DSP
# --------------------------

def normalize(sig: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    """
    Asegura que la señal esté en [-1, 1] sin 'clip'.
    Si la señal ya está normalizada, no cambia nada.
    """
    if not isinstance(sig, np.ndarray):
        try:
            sig = np.asarray(sig, dtype=np.float32)
        except (ValueError, TypeError) as e:
            raise TypeError(f"sig no se puede convertir a ndarray: {e}") from e
    if sig.size == 0:
        return sig.astype(np.float32)
    peak = np.max(np.abs(sig)) + eps
    out = sig / peak
    return out.astype(np.float32)


def apply_gain(sig: np.ndarray, gain_db: float) -> np.ndarray:
    """
    Aplica ganancia en dB de forma segura.
    gain_db = 0  -> igual
    gain_db = -6 -> reduce ~a la mitad
    gain_db = +6 -> duplica (cuidado con clipping)
    """
    if not isinstance(sig, np.ndarray):
        raise TypeError(f"sig debe ser np.ndarray, recibido: {type(sig).__name__}")
    if not isinstance(gain_db, (int, float)):
        raise TypeError(f"gain_db debe ser numérico, recibido: {type(gain_db).__name__}")
    g = 10 ** (gain_db / 20.0)
    out = sig * g
    # re-normaliza si nos pasamos del rango
    peak = np.max(np.abs(out)) if out.size else 0.0
    if peak > 1.0:
        out = out / peak
    return out.astype(np.float32)


def fade_edges(sig: np.ndarray, fade_ms: float = 10.0, fs: int = FS) -> np.ndarray:
    """
    Aplica un fade-in y fade-out corto para evitar clics.
    - 'fade_ms' define la duración en milisegundos.
    """
    out = sig.astype(np.float32, copy=True)
    n = out.size
    if n == 0:
        return out
    n_fade = int(fs * (fade_ms / 1000.0))
    n_fade = max(1, min(n_fade, n // 2))  # no más de la mitad de la señal

    # Curvas lineales simples
    fade_in = np.linspace(0.0, 1.0, n_fade, dtype=np.float32)
    fade_out = np.linspace(1.0, 0.0, n_fade, dtype=np.float32)

    out[:n_fade] *= fade_in
    out[-n_fade:] *= fade_out
    return out


# --------------------------
# Reproducción con sounddevice
# --------------------------

def play_blocking(sig: np.ndarray, fs: int = FS, gain_db: float = -6.0) -> None:
    """
    Reproduce la señal y espera a que termine (bloqueante).
    Uso ideal para scripts de prueba o CLI.

    Seguridad:
    - normaliza
    - baja volumen por defecto (-6 dB)
    - aplica fade-in/out 10 ms
    """
    if not isinstance(sig, np.ndarray):
        raise TypeError(f"sig debe ser np.ndarray, recibido: {type(sig).__name__}")
    if sig.size == 0:
        return
    if not isinstance(fs, int) or fs <= 0:
        raise ValueError(f"fs debe ser un entero positivo, recibido: {fs!r}")
    try:
        # Pipeline de preparación de señal
        y = normalize(sig)
        y = apply_gain(y, gain_db)
        y = fade_edges(y, fade_ms=10.0, fs=fs)

        sd.play(y, samplerate=fs, blocking=True)
        sd.stop()  # por si acaso
    except sd.PortAudioError as e:
        print(f"⚠️  Error de PortAudio: {e}")
        print("Sugerencias:")
        print(" - Verifica que otro programa no esté usando el dispositivo de audio.")
        print(" - Prueba a cambiar de dispositivo por defecto del sistema.")
        print(" - Asegúrate de que el sample rate del sistema soporte", fs, "Hz.")
    except Exception as e:
        print(f"⚠️  Error reproduciento audio: {e}")


def play_async(sig: np.ndarray, fs: int = FS, gain_db: float = -6.0) -> sd.OutputStream | None:
    """
    Reproduce la señal SIN bloquear (devuelve el stream).
    Útil para integrarlo con Tkinter (no congela la interfaz).

    Devuelve:
        - Un objeto sd.OutputStream que puedes .stop() más tarde, o
        - None si hubo error.
    """
    if not isinstance(sig, np.ndarray):
        raise TypeError(f"sig debe ser np.ndarray, recibido: {type(sig).__name__}")
    if sig.size == 0:
        return None
    if not isinstance(fs, int) or fs <= 0:
        raise ValueError(f"fs debe ser un entero positivo, recibido: {fs!r}")
    try:
        y = normalize(sig)
        y = apply_gain(y, gain_db)
        y = fade_edges(y, fade_ms=10.0, fs=fs)

        # Creamos un stream y escribimos el buffer
        stream = sd.OutputStream(samplerate=fs, channels=1, dtype="float32")
        stream.start()
        stream.write(y)  # escribe y suena
        return stream
    except sd.PortAudioError as e:
        print(f"⚠️  Error de PortAudio: {e}")
        return None
    except Exception as e:
        print(f"⚠️  Error reproduciento audio: {e}")
        return None


def stop_all() -> None:
    """Detiene cualquier reproducción en curso."""
    try:
        sd.stop()
    except Exception:
        pass
