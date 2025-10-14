"""
run_kmeans_demo.py
------------------
Demo de KMeans sin UI:
- Carga session_log.csv (si existe).
- Si no existe, crea datos sintéticos de errores.
- Construye features de error, elige k, ejecuta KMeans y resume clusters.
"""

import os
import numpy as np
import pandas as pd

from analytics.cluster_analysis import (
    load_session_log,
    build_error_features,
    pick_k_by_silhouette,
    run_kmeans,
    summarize_clusters,
    recommend_focus_from_clusters,
    BANDS
)

CSV = "data/session_log.csv"

def _make_synthetic_log(path: str) -> None:
    """Crea un pequeño CSV de ejemplo con errores intencionales en ciertas zonas."""
    rng = np.random.default_rng(123)
    rows = []
    for _ in range(40):
        true = int(rng.choice(BANDS))
        # simular errores con sesgo hacia agudos en medios/agudos
        if true >= 1000:
            # 60% de veces se va 1-2 bandas hacia arriba
            shift = int(rng.choice([+1,+1,+2,0,-1]))
        else:
            # en graves, errores más pequeños/variados
            shift = int(rng.choice([0,+1,-1,+2,-2]))
        pred_idx = np.clip(BANDS.index(true) + shift, 0, len(BANDS)-1)
        pred = BANDS[pred_idx]
        correct = int(pred == true)
        rt_ms = int(rng.normal(900 if correct else 1200, 200))
        rows.append({"timestamp": "2025-10-06T12:00:00",
                     "module": "demo",
                     "band_true": true,
                     "band_user": pred,
                     "correct": correct,
                     "rt_ms": rt_ms})
    df = pd.DataFrame(rows)
    os.makedirs("data", exist_ok=True)
    df.to_csv(path, index=False)
    print(f"⚠️  No había CSV. Se generó uno sintético en {path} con {len(df)} filas.")

def main():
    # 1) Cargar (o crear) CSV
    if os.path.exists(CSV):
        df = load_session_log(CSV)
        print(f"✅ Cargado {CSV} con {len(df)} filas.")
    else:
        _make_synthetic_log(CSV)
        df = load_session_log(CSV)

    # 2) Construir features de errores
    X, feats, df_err = build_error_features(df)
    if X is None or df_err is None or df_err.empty:
        print("ℹ️ Aún no hay suficientes errores para hacer KMeans (necesitas ≥ 8).")
        return

    print(f"📊 Errores: {len(df_err)}  |  Features: {feats}")

    # 3) Elegir k automáticamente (2..4) y ejecutar KMeans
    k = pick_k_by_silhouette(X, k_range=(2,4))
    print(f"🔧 k elegido por silhouette: {k}")
    labels, km, scaler = run_kmeans(X, k)

    # 4) Resumir clusters y sugerir foco
    summaries = summarize_clusters(labels, df_err)
    for s in summaries:
        print(f"— Cluster {s.label}: n={s.n}, dist_media={s.mean_dist:.2f}, "
              f"{s.bias_txt}, región={s.region_mode}. Sugerencia: {s.suggestion}")

    reco = recommend_focus_from_clusters(summaries)
    print(f"\n🎯 Recomendación de práctica: región={reco['region']} → {reco['message']}")

if __name__ == "__main__":
    main()
