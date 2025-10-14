"""
run_audio_test.py
-----------------
Pruebas rápidas de generación + reproducción:
- 1 kHz tono puro
- 'feedback' simulado a 2 kHz (ruido rosa + pico resonante)

Úsalo para confirmar que scipy + sounddevice están funcionando con tu dispositivo.
"""

from time import sleep
from core.synth import make_tone, make_feedback
from core.audio_io import play_blocking, stop_all
from config import FS

if __name__ == "__main__":
    print(f"🔊 Test de audio a {FS} Hz")

    print("▶️  Reproduciendo tono puro de 1 kHz...")
    tone = make_tone(1000, dur=1.5, fs=FS)
    play_blocking(tone, fs=FS, gain_db=-9.0)  # más bajo por seguridad
    sleep(0.2)

    print("▶️  Reproduciendo 'feedback' simulado a 2 kHz...")
    fb = make_feedback(2000, dur=1.5, fs=FS)
    play_blocking(fb, fs=FS, gain_db=-9.0)
    sleep(0.2)

    stop_all()
    print("✅ Prueba de audio finalizada.")
