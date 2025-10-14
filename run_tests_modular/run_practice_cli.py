"""
run_practice_cli.py
-------------------
Pequeña práctica por consola para generar datos reales:
- Elige una banda objetivo.
- Reproduce un “feedback” simulado.
- Pide tu respuesta (en Hz o selecciona la banda).
- Evalúa, muestra mensaje simbólico y registra en CSV.

Usa play_blocking para simplificar (sin UI).
"""

import time
from core.bands import BANDS, nearest, band_distance
from core.synth import make_feedback
from core.audio_io import play_blocking, stop_all
from ai.rules import feedback_text
from ai.policy import next_band, update as policy_update
from data_logger import log_attempt
from config import FS

def _prompt_user_band() -> int:
    print("\nBandas disponibles:", BANDS)
    raw = input("👉 Tu respuesta (Hz exactos o elige una banda de la lista): ").strip()
    try:
        val = int(float(raw))
        return nearest(val)
    except Exception:
        print("Entrada inválida. Intenta con un número (Hz).")
        return _prompt_user_band()

def main():
    print("🎧 Entrenamiento CLI – Detección de Feedback (Ctrl+C para salir)")
    last_idx = None
    while True:
        try:
            target = next_band(last_idx)
            print(f"\n🎯 Objetivo oculto (banda): {target} Hz")
            sig = make_feedback(target, dur=1.8, fs=FS)
            t0 = time.perf_counter()
            play_blocking(sig, fs=FS, gain_db=-9.0)
            stop_all()
            user_band = _prompt_user_band()
            rt_ms = int((time.perf_counter() - t0) * 1000)

            correct = int(user_band == target)
            print("📝", feedback_text(target, user_band))

            # logging + política
            log_attempt("cli", target, user_band, correct, rt_ms)
            policy_update(target, correct)

            # siguiente
            last_idx = BANDS.index(target)
            print(f"⏱️  RT: {rt_ms} ms  |  Dist: {band_distance(target, user_band)} bandas")
        except KeyboardInterrupt:
            print("\n👋 Fin de la sesión.")
            break

if __name__ == "__main__":
    main()
