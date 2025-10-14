"""
ai/policy.py
------------
Política simple para elegir la próxima banda objetivo.

Características:
- Evita repetir la misma banda inmediatamente.
- Cooldown de las últimas N bandas para aumentar variedad.
- Mezcla "explotación" (practicar debilidades) con "exploración" (aleatorio).
"""

from __future__ import annotations
import random
from collections import deque
from typing import Deque, Dict, List, Tuple

from core.bands import BANDS

# ------------------------------
# Estado interno de la política
# ------------------------------

# Conteo de aciertos/errores por índice de banda
_stats: Dict[int, Tuple[int, int]] = {}  # idx -> (aciertos, errores)

# Historial reciente para evitar repeticiones
_HISTORY_MAX = 3
_history: Deque[int] = deque(maxlen=_HISTORY_MAX)

# Parámetros de equilibrio
_EPSILON = 0.25   # probabilidad de explorar (aleatorio)
_MIN_CANDIDATES = 6  # cómo de amplia es la elección al explorar


def update(true_band_hz: int, correct: int) -> None:
    """
    Actualiza estadísticas básicas de desempeño.
    correct: 1 acierto, 0 error
    """
    idx = BANDS.index(true_band_hz)
    ok, bad = _stats.get(idx, (0, 0))
    if correct:
        ok += 1
    else:
        bad += 1
    _stats[idx] = (ok, bad)


def _weakness_score(idx: int) -> float:
    """
    Puntaje de "debilidad": mayor si hay más errores y/o pocos aciertos.
    Se usa para sesgar la selección hacia lo que conviene practicar.
    """
    ok, bad = _stats.get(idx, (0, 0))
    total = ok + bad
    if total == 0:
        return 0.5  # desconocido → neutro
    # proporción de errores, con pequeño sesgo hacia revisar bandas con datos
    return 0.55 * (bad / total) + 0.45 * (bad / (bad + 1))


def _candidates_excluding_recent() -> List[int]:
    """
    Devuelve índices de bandas excluyendo el historial reciente para dar variedad.
    Si se filtra demasiado, relaja el filtro.
    """
    candidates = [i for i in range(len(BANDS)) if i not in _history]
    if len(candidates) < max(1, len(BANDS) - _MIN_CANDIDATES):
        # Relajar un poco: solo evita repetir la última exactamente
        candidates = [i for i in range(len(BANDS)) if (len(_history) == 0 or i != _history[-1])]
    return candidates


def next_band(last_idx: int | None) -> int:
    """
    Elige el índice de la próxima banda objetivo (Hz = BANDS[idx]).

    Estrategia:
    - Siempre evitamos repetir la última banda exacta.
    - Con prob. EPSILON exploramos (aleatorio entre candidatos).
    - En explotación, elegimos entre candidatos el de mayor "debilidad".
    - Añadimos el elegido al historial (cooldown de las últimas N bandas).
    """
    # 1) Construir candidatos excluyendo recentísimos
    candidates = _candidates_excluding_recent()

    # 2) Asegurar que no devolvemos exactamente la última, si se coló
    if last_idx is not None and last_idx in candidates and len(candidates) > 1:
        # Quita la última banda exacta de la lista de candidatos
        candidates = [i for i in candidates if i != last_idx]

    # 3) Decidir exploración vs explotación
    if random.random() < _EPSILON:
        # Exploración: aleatorio entre un subconjunto suficientemente grande
        if len(candidates) >= _MIN_CANDIDATES:
            choice = random.choice(candidates)
        else:
            # En caso extremo, elige al azar del espacio completo evitando la última
            pool = [i for i in range(len(BANDS)) if i != last_idx] or list(range(len(BANDS)))
            choice = random.choice(pool)
    else:
        # Explotación: escoger el candidato con mayor "debilidad"
        scored = [(idx, _weakness_score(idx)) for idx in candidates]
        # Si todos tienen puntuación igual, random entre candidatos
        max_score = max(s for _, s in scored) if scored else 0.0
        top = [idx for idx, s in scored if s == max_score] or candidates
        choice = random.choice(top)

    # 4) Registrar historial y devolver Hz
    _history.append(choice)
    return BANDS[choice]
