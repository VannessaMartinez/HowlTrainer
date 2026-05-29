"""
analytics/cluster_analysis.py
-----------------------------
Analítica de errores con KMeans para detectar "patrones de confusión" y
sugerir práctica focalizada en el EarTrainer – Detección de Feedback.

Flujo:
1) Cargar el log de sesión (CSV).
2) Filtrar SOLO intentos fallidos (correct == 0).
3) Construir FEATURES simples de cada error (true_idx, pred_idx, etc.).
4) Ejecutar KMeans para agrupar "tipos de error".
5) Resumir clusters en texto y sugerir práctica.

Este módulo NO depende de la UI. Se puede ejecutar desde consola.
"""

from __future__ import annotations
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict

from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score

# Bandas "oficiales" 1/3 octava (deben coincidir con core/bands.py)
BANDS = [250,315,400,500,630,800,1000,1250,1600,2000,2500,3150,4000,5000,6300,8000]
BAND_TO_IDX = {b:i for i,b in enumerate(BANDS)}


# ---------------------------
# Estructuras de datos útiles
# ---------------------------

@dataclass
class ClusterSummary:
    label: int
    n: int
    mean_dist: float
    bias_txt: str
    region_mode: str
    suggestion: str


# ---------------------------
# 1) Carga del session log
# ---------------------------

def load_session_log(csv_path: str = "data/session_log.csv") -> pd.DataFrame:
    """
    Carga el CSV de intentos. Se espera (mínimo):
    timestamp,module,band_true,band_user,correct,rt_ms

    Si no existe, levanta FileNotFoundError.
    """
    if not csv_path or not isinstance(csv_path, str):
        raise ValueError(f"csv_path debe ser un string no vacío, recibido: {csv_path!r}")
    df = pd.read_csv(csv_path)
    if df.empty:
        raise ValueError(f"El CSV está vacío o solo tiene cabecera: {csv_path}")
    return df


# ---------------------------
# 2) Construcción de features
# ---------------------------

def _region_of(freq: float) -> int:
    """Mapea frecuencia a región: 0=graves (<500), 1=medios (<2000), 2=agudos."""
    f = float(freq)
    if f < 500: return 0
    if f < 2000: return 1
    return 2

def build_error_features(df: pd.DataFrame) -> Tuple[Optional[np.ndarray], List[str], pd.DataFrame]:
    """
    Toma el dataframe completo y devuelve:
      X: matriz de features SOLO de errores (o None si no hay suficientes)
      feature_names: nombres de columnas en X
      df_err: subset con los errores y columnas auxiliares

    Features (simples y explicables):
      - true_idx  : índice de banda real
      - pred_idx  : índice de banda elegida
      - dist_idx  : |true_idx - pred_idx| (cuántas bandas de error)
      - sign      : +1 si se fue "hacia agudos", -1 si "hacia graves"
      - region_true : 0/1/2 (graves/medios/agudos)
      - rt_ms     : tiempo de respuesta (sin escalar aquí)
    """
    if df.empty:
        return None, [], df

    df_err = df[df["correct"] == 0].copy()
    if df_err.empty or len(df_err) < 8:
        # Menos de 8 errores suele ser poca señal para clusterizar
        return None, [], df_err

    df_err["true_idx"] = df_err["band_true"].map(BAND_TO_IDX)
    df_err["pred_idx"] = df_err["band_user"].map(BAND_TO_IDX)
    df_err["dist_idx"] = (df_err["true_idx"] - df_err["pred_idx"]).abs()
    df_err["sign"] = np.where(df_err["pred_idx"] > df_err["true_idx"], 1, -1)
    df_err["region_true"] = df_err["band_true"].apply(_region_of)

    features = ["true_idx", "pred_idx", "dist_idx", "sign", "region_true", "rt_ms"]
    X = df_err[features].to_numpy(dtype=float)
    return X, features, df_err


# ---------------------------
# 3) KMeans (selección de k)
# ---------------------------

def pick_k_by_silhouette(X: np.ndarray, k_range: Tuple[int,int] = (2,4)) -> int:
    """
    Elige k en un rango pequeño (2..4 por defecto) maximizando silhouette score.
    Requiere al menos k clusters distintos (si X es muy chico, cae en k=2).
    """
    if not isinstance(X, np.ndarray) or X.ndim != 2:
        raise ValueError("X debe ser un ndarray 2D")
    if X.shape[0] < k_range[0]:
        raise ValueError(
            f"Se necesitan al menos {k_range[0]} muestras para clusterizar, "
            f"recibidas: {X.shape[0]}"
        )
    if k_range[0] < 2:
        raise ValueError(f"k_range mínimo debe ser >= 2, recibido: {k_range}")
    Xs = StandardScaler().fit_transform(X)
    best_k, best_score = None, -1.0
    for k in range(k_range[0], k_range[1]+1):
        try:
            km = KMeans(n_clusters=k, n_init="auto", random_state=42)
            labels = km.fit_predict(Xs)
            score = silhouette_score(Xs, labels)
            if score > best_score:
                best_k, best_score = k, score
        except Exception:
            continue
    return best_k or k_range[0]

def run_kmeans(X: np.ndarray, k: int) -> Tuple[np.ndarray, KMeans, StandardScaler]:
    """
    Estandariza X, ejecuta KMeans y devuelve:
      labels: etiqueta de cluster por fila
      km: modelo KMeans ajustado
      scaler: StandardScaler usado (por si quieres reutilizarlo)
    """
    if not isinstance(X, np.ndarray) or X.ndim != 2:
        raise ValueError("X debe ser un ndarray 2D")
    if not isinstance(k, int) or k < 2:
        raise ValueError(f"k debe ser un entero >= 2, recibido: {k!r}")
    if X.shape[0] < k:
        raise ValueError(
            f"Se necesitan al menos k={k} muestras, recibidas: {X.shape[0]}"
        )
    scaler = StandardScaler().fit(X)
    Xs = scaler.transform(X)
    km = KMeans(n_clusters=k, n_init="auto", random_state=42)
    labels = km.fit_predict(Xs)
    return labels, km, scaler


# ---------------------------
# 4) Resumen e interpretación
# ---------------------------

def summarize_clusters(labels: np.ndarray, df_err: pd.DataFrame) -> List[ClusterSummary]:
    """
    Produce resúmenes legibles por humano para cada cluster.
    """
    out: List[ClusterSummary] = []
    for c in sorted(set(labels)):
        group = df_err[labels == c]
        if group.empty:
            continue
        mean_dist = float(group["dist_idx"].mean())
        bias = np.sign((group["pred_idx"] - group["true_idx"]).mean())
        bias_txt = "tendencia a pasarse a AGUDOS" if bias > 0 else "tendencia a irse a GRAVES"
        reg_mode = int(group["region_true"].mode().iat[0])
        reg_txt = {0:"graves",1:"medios",2:"agudos"}[reg_mode]

        # Sugerencia pedagógica por región predominante
        if reg_mode == 2:
            sug = "Practica 2–8 kHz con pasos de 1 banda y Q estrecha."
        elif reg_mode == 1:
            sug = "Refuerza 500 Hz–2 kHz; contrasta 1 kHz vs 2 kHz."
        else:
            sug = "Trabaja ≤500 Hz; compara 250, 315 y 400 Hz."

        out.append(ClusterSummary(
            label=int(c),
            n=int(len(group)),
            mean_dist=mean_dist,
            bias_txt=bias_txt,
            region_mode=reg_txt,
            suggestion=sug
        ))
    return out


def recommend_focus_from_clusters(summaries: List[ClusterSummary]) -> Dict[str, str]:
    """
    Dada la lista de resúmenes, elige un "foco de práctica":
      - Prioriza el cluster con mayor 'n' (más errores acumulados).
      - Devuelve un diccionario con región sugerida y un mensaje corto.

    Retorno ejemplo:
      {"region": "agudos", "message": "Practica 2–8 kHz con pasos de 1 banda..."}
    """
    if not summaries:
        return {"region": "general", "message": "Aún no hay suficientes errores para clusterizar."}
    # Orden: más errores primero; en empate, mayor distancia media
    summaries = sorted(summaries, key=lambda s: (s.n, s.mean_dist), reverse=True)
    top = summaries[0]
    return {"region": top.region_mode, "message": top.suggestion}
