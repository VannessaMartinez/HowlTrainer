"""
tests/test_bands.py
-------------------
Estas pruebas verifican la lógica básica de bandas de frecuencia que usa el EarTrainer.
La idea es asegurar que:
- Podemos "anclar" cualquier frecuencia real a una banda oficial (nearest).
- Podemos medir qué tan lejos está una respuesta (band_distance).
- Podemos clasificar una frecuencia como graves / medios / agudos (region_of).
- Podemos obtener las bandas vecinas (neighbors) para feedback y ejercicios.

Si estos tests pasan, la base del entrenamiento auditivo es fiable.
"""

from core.bands import (
    BANDS,
    nearest,
    band_distance,
    region_of,
    neighbors,
    index_of
)


def test_nearest_basic():
    """
    Verifica que 'nearest' elige la banda "oficial" más cercana a una frecuencia real.
    Casos:
    - Coincidencia exacta (1000 -> 1000)
    - Número cercano a una banda (260 -> 250)
    - Número entre dos bandas (1180 -> 1250, porque está más cerca de 1250 que de 1000)
    """
    assert nearest(1000) == 1000
    assert nearest(260) == 250
    # Distancias: |1180-1250| = 70  y  |1180-1000| = 180 -> gana 1250
    assert nearest(1180) == 1250


def test_band_distance():
    """
    'band_distance' mide en "pasos de banda":
    - 0 si es la misma banda (acierto exacto)
    - 1 si es vecina (error "por poquito")
    - 2 si está dos bandas más allá (error más grande)
    """
    assert band_distance(1000, 1000) == 0
    assert band_distance(1000, 1250) == 1
    assert band_distance(1000, 1600) == 2


def test_region_of():
    """
    'region_of' traduce una frecuencia a un nombre humano útil para el feedback:
    - < 500 Hz  => "graves"
    - 500–1999  => "medios"
    - >= 2000   => "agudos"
    Esto ayuda a explicar: "era brillo/sibilancia" (agudos) o "era cuerpo" (graves).
    """
    assert region_of(200) == "graves"
    assert region_of(800) == "medios"
    assert region_of(2500) == "agudos"


def test_neighbors_k1():
    """
    'neighbors' devuelve las bandas vecinas alrededor de una banda dada.
    Con k=1, esperamos una banda antes y una después (recortando en extremos).
    Alrededor de 1000, nuestras bandas son: [800, 1000, 1250].
    """
    nb = neighbors(1000, k=1)
    assert 800 in nb and 1000 in nb and 1250 in nb
    # También comprobamos que el orden sea ascendente y no esté vacía
    assert nb == sorted(nb)
    assert len(nb) >= 2


def test_neighbors_edges():
    """
    Caso borde (edge case): si pido vecinos de la banda más baja o más alta,
    la función debe "recortar" (no irse fuera de la lista).
    """
    first = BANDS[0]
    last = BANDS[-1]
    nb_first = neighbors(first, k=2)  # no puede ir "hacia abajo" más allá del inicio
    nb_last = neighbors(last, k=2)    # no puede ir "hacia arriba" más allá del final

    # La primera lista debe empezar en la primera banda
    assert nb_first[0] == first
    # La última lista debe terminar en la última banda
    assert nb_last[-1] == last


def test_index_of_accepts_non_exact_values():
    """
    'index_of' debe aceptar valores que no estén exactamente en BANDS,
    usando internamente 'nearest'. Así, 1180 "se comporta" como si fuera 1250.
    """
    i_exact = index_of(1250)
    i_1180 = index_of(1180)  # nearest(1180)=1250
    assert i_exact == i_1180
