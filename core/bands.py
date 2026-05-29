"""
core/bands.py

🧩 ¿Qué hace core/bands.py?

Imagina que tienes un oído entrenado digital dentro del programa.
Este módulo le enseña a ese “oído” a:

- Saber qué frecuencias existen (como notas o rangos de sonido).
- Saber cuál frecuencia está más cerca de la que escucha.
- Medir qué tan lejos está una de otra.
- Saber si el sonido pertenece a graves, medios o agudos.

En palabras simples:
👉 este archivo convierte frecuencias (números en Hz) en categorías humanas y organizadas, para que la IA simbólica pueda razonar sobre ellas.
-------------

Este módulo enseña al programa a entender frecuencias como si fueran "zonas" en una escala.
Aquí se definen funciones para comparar, ubicar y clasificar frecuencias (en Hz)
según las bandas de 1/3 de octava usadas en audio profesional.
"""

# Importamos herramientas de tipado y la función que carga las bandas desde config.py
from typing import List
from config import load_bands

# Cargamos la lista de bandas (por ejemplo: [250, 315, 400, 500, ...])
BANDS: List[int] = load_bands()

# Creamos un diccionario para encontrar más rápido la posición de cada banda
# Ejemplo: IDX[1000] = 6
IDX = {b: i for i, b in enumerate(BANDS)}


def nearest(freq_hz: float) -> int:
    """
    Busca dentro de la lista BANDS la frecuencia más parecida a 'freq_hz'.
    Ejemplo: nearest(1180) -> 1250
    """
    if not BANDS:
        raise RuntimeError("La lista BANDS está vacía; revisa config.py / data/bands.csv")
    if not isinstance(freq_hz, (int, float)):
        raise TypeError(f"freq_hz debe ser numérico, recibido: {type(freq_hz).__name__}")
    if freq_hz <= 0:
        raise ValueError(f"freq_hz debe ser positivo, recibido: {freq_hz}")
    return min(BANDS, key=lambda b: abs(b - freq_hz))


def index_of(band_hz: int) -> int:
    """
    Devuelve el índice (posición) de una banda en la lista.
    Si la banda no existe exactamente, usa la más cercana.
    Ejemplo: index_of(1180) -> índice de 1250
    """
    if band_hz in IDX:
        return IDX[band_hz]
    return IDX[nearest(band_hz)]


def band_distance(b_true: int, b_user: int) -> int:
    """
    Calcula cuántas "bandas" separan dos frecuencias.
    0 = la misma banda, 1 = vecina, 2 = más lejos, etc.
    Ejemplo: band_distance(1000, 1250) -> 1
    """
    return abs(index_of(b_true) - index_of(b_user))


def neighbors(band_hz: int, k: int = 1) -> List[int]:
    """
    Devuelve una pequeña lista con las bandas vecinas alrededor de 'band_hz'.
    Por ejemplo, con k=1 devuelve una banda antes y una después.
    Ejemplo: neighbors(1000, 1) -> [800, 1000, 1250]
    """
    if not isinstance(k, int) or k < 0:
        raise ValueError(f"k debe ser un entero no negativo, recibido: {k!r}")
    i = index_of(band_hz)
    lo = max(0, i - k)  # evita números negativos
    hi = min(len(BANDS) - 1, i + k)  # evita salir del final de la lista
    return BANDS[lo:hi + 1]


def region_of(freq_hz: float) -> str:
    """
    Clasifica una frecuencia según su zona perceptiva:
    - <500 Hz  → "graves" (bajos, sonido profundo)
    - 500–2000 Hz → "medios" (voz, instrumentos)
    - >2000 Hz → "agudos" (brillo, silbido)
    """
    if not isinstance(freq_hz, (int, float)):
        raise TypeError(f"freq_hz debe ser numérico, recibido: {type(freq_hz).__name__}")
    if freq_hz <= 0:
        raise ValueError(f"freq_hz debe ser positivo, recibido: {freq_hz}")
    if freq_hz < 500:
        return "graves"
    if freq_hz < 2000:
        return "medios"
    return "agudos"


# __all__ define qué funciones se exportan cuando otro módulo hace "from core.bands import *"
__all__ = [
    "BANDS", "nearest", "index_of", "band_distance", "neighbors", "region_of"
]
