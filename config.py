"""
Config global del proyecto EarTrainer – Detección de Feedback.
Define sample rate, duración por defecto y cómo cargar las bandas 1/3 octava.
"""
from pathlib import Path
from typing import List

# Raíz del proyecto (carpeta donde está este archivo)
PROJECT_ROOT = Path(__file__).resolve().parent

# Audio
FS: int = 48_000         # Frecuencia de muestreo por defecto
DUR_SEC: float = 2.0      # Duración por defecto de los estímulos (segundos)

# Ruta del CSV de bandas (puedes editarlo si lo mueves)
BANDS_CSV = PROJECT_ROOT / "data" / "bands.csv"

# Fallback en caso de que no exista el CSV (1/3 octava aproximada)
DEFAULT_BANDS: List[int] = [
    250, 315, 400, 500, 630, 800,
    1000, 1250, 1600, 2000, 2500, 3150,
    4000, 5000, 6300, 8000
]

def load_bands() -> List[int]:
    """
    Carga bandas desde data/bands.csv si existe, de lo contrario usa DEFAULT_BANDS.
    Espera un CSV con cabecera: band_hz
    """
    if BANDS_CSV.exists():
        # Usamos csv puro para no depender de pandas en esta capa
        import csv
        vals = []
        with BANDS_CSV.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    vals.append(int(float(row["band_hz"])))
                except Exception:
                    continue
        # Si el archivo está vacío o malo, volvemos al default
        if vals:
            return vals
    return DEFAULT_BANDS
