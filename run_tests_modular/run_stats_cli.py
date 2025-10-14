"""
run_stats_cli.py
----------------
"Stats Page" por consola para EarTrainer – Detección de Feedback.

Este script resume el rendimiento del usuario usando:
1) Un análisis con KMeans de patrones de error (si hay datos suficientes).
2) Un Fallback (plan B) que muestra estadísticas básicas cuando NO hay suficientes
   errores para ejecutar KMeans de forma confiable.

Por qué existe el Fallback:
- KMeans necesita una cantidad mínima de muestras (errores) para encontrar
  “formas” en los datos. Con muy pocos errores, los clusters son inestables y
  pueden llevar a conclusiones engañosas. Por eso, si no alcanzamos un mínimo,
  mostramos estadísticas básicas útiles (accuracy por banda y errores por región),
  además de una recomendación simple.

Uso:
  python run_stats_cli.py                    # k elegido automáticamente (2..4)
  python run_stats_cli.py --k 3              # forzar k=3
  python run_stats_cli.py --csv path_al_csv  # usar otro CSV
  python run_stats_cli.py --out reporte.txt  # guarda el reporte en un .txt

Requisitos:
  - pandas, numpy, scikit-learn
  - analytics/cluster_analysis.py: funciones de clustering (KMeans)
  - CSV con columnas: timestamp,module,band_true,band_user,correct,rt_ms
"""

from __future__ import annotations

# argparse: para leer flags (--csv, --k, etc.) desde la línea de comandos
import argparse
# Path: para manipular rutas de forma robusta (independiente de sistema operativo)
from pathlib import Path
# Tipado opcional, y utilidades
from typing import List
# os: para comprobaciones rápidas (existencia de archivo)
import os

# pandas: lectura y manipulación de datos tabulares
import pandas as pd

# Importamos el “motor” de analítica (KMeans y helpers)
from analytics.cluster_analysis import (
    load_session_log,            # carga el CSV como DataFrame
    build_error_features,        # construye “features” de errores para KMeans
    pick_k_by_silhouette,        # elige k automáticamente en un rango
    run_kmeans,                  # ejecuta KMeans sobre las features
    summarize_clusters,          # produce resúmenes legibles de cada cluster
    recommend_focus_from_clusters,  # da una recomendación final basada en clusters
)

# Ruta por defecto de tu CSV de sesión (se crea durante la práctica)
DEFAULT_CSV = "data/session_log.csv"


# ===============================
#  Helpers (validación + fallback)
# ===============================

def _validate_columns(df: pd.DataFrame) -> List[str]:
    """
    Verifica que el CSV tenga las columnas mínimas necesarias.
    Retorna una lista con las columnas faltantes (vacía si está todo OK).

    Por qué es importante:
    - Si faltan columnas, el resto del pipeline fallará. Es mejor detectarlo
      temprano y mostrar un mensaje claro al usuario.
    """
    required = {"timestamp", "module", "band_true", "band_user", "correct", "rt_ms"}
    return [c for c in required if c not in df.columns]


def _region_of(freq: float) -> str:
    """
    Mapea una frecuencia a una región perceptiva amplia:
      - graves   : < 500 Hz
      - medios   : 500–1999 Hz
      - agudos   : ≥ 2000 Hz
    Usado en el fallback para contar errores por región.
    """
    f = float(freq)
    if f < 500:
        return "graves"
    if f < 2000:
        return "medios"
    return "agudos"

def _ascii_bar(value: float, width: int = 25) -> str:
    """
    Dibuja una barra ASCII proporcional a 'value' en [0..1].
    Ej: 0.72 → '███████████████████----' (aprox. 72% lleno).
    """
    value = max(0.0, min(1.0, float(value)))
    filled = int(round(value * width))
    return "█" * filled + "-" * (width - filled)


def _basic_stats_report(csv_path: Path, df: pd.DataFrame) -> str:
    """
    Fallback: genera un reporte de “estadísticas básicas” cuando NO hay suficientes
    errores para ejecutar KMeans. Incluye:
      - accuracy global,
      - top 5 de bandas con menor accuracy,
      - errores por región (graves/medios/agudos),
      - recomendación simple basada en la región con más errores.

    Por qué este fallback es útil:
    - Aunque no haya clusters (patrones) confiables, aún podemos extraer
      insights simples que guíen la práctica del usuario.
    """
    # Métricas generales de la sesión
    n_total = len(df)
    n_correct = int((df["correct"] == 1).sum())
    acc = (n_correct / n_total) if n_total else 0.0

    # Accuracy por banda (band_true). “acc” es el promedio de correct (0/1).
    # - Ordenamos por menor accuracy para ver rápidamente las bandas más débiles.
    by_band = (
        df.groupby("band_true")["correct"]
          .agg(["count", "mean"])          # count = n intentos; mean = accuracy
          .rename(columns={"count": "n", "mean": "acc"})
          .sort_values("acc", ascending=True)
    )
    worst5 = by_band.head(5)

    # Errores por región (convierte band_true→región y cuenta correct==0)
    tmp = df.copy()
    tmp["region_true"] = tmp["band_true"].apply(_region_of)
    errs_by_region = (
        tmp[tmp["correct"] == 0]
        .groupby("region_true")["correct"]
        .count()
        .reindex(["graves", "medios", "agudos"])
        .fillna(0)
        .astype(int)
    )

    # Recomendación simple: elige la región con más errores
    region_focus = errs_by_region.idxmax() if errs_by_region.sum() > 0 else "general"
    reco_msg = {
        "graves": "Practica ≤500 Hz (250–500). Contrasta 250/315/400 Hz.",
        "medios": "Refuerza 500–2000 Hz. Contrasta 1 kHz vs 2 kHz.",
        "agudos": "Practica 2–8 kHz con pasos de 1 banda y Q estrecha.",
        "general": "Aún no hay suficientes intentos para recomendar región."
    }[region_focus]

    # Construimos el texto del reporte (string) para imprimir o guardar a archivo
    lines = []
    lines.append("==========================================")
    lines.append("          📊 EARTRAINER – STATS")
    lines.append("==========================================")
    lines.append(f"CSV: {csv_path.resolve()}")
    lines.append(f"Intentos totales: {n_total}  |  Aciertos: {n_correct}  |  Acc: {acc:.1%}")
    lines.append("------------------------------------------")
    lines.append("ℹ️  No hay suficientes errores para KMeans (se requieren ≥ 8).")
    lines.append("    Mostrando estadísticas básicas:\n")

    lines.append("• Top 5 bandas con menor accuracy:")
    if worst5.empty:
        lines.append("  (No hay suficientes datos por banda).")
    else:
        for band, row in worst5.iterrows():
            lines.append(f"  - {int(band)} Hz → acc={row['acc']:.1%}  (n={int(row['n'])})")
    
    # ⬇️ INSERTA AQUÍ EL BLOQUE DEL GRÁFICO ASCII ⬇️
    # Muestra un pequeño gráfico ASCII por banda (accuracy 0..1)
    lines.append("\n• Accuracy por banda (gráfico ASCII):")
    if by_band.empty:
        lines.append("  (No hay datos por banda todavía).")
    else:
        # Recorremos en orden de frecuencia (no el orden por acc)
        for band in sorted(by_band.index.tolist()):
            row = by_band.loc[band]
            acc_b = float(row["acc"]) if pd.notna(row["acc"]) else 0.0
            bar = _ascii_bar(acc_b, width=25)
            lines.append(f"  {int(band):>5} Hz | {bar} | {acc_b:5.1%}  (n={int(row['n'])})")
    # ⬆️ HASTA AQUÍ ⬆️

    lines.append("\n• Errores por región:")
    for reg in ["graves", "medios", "agudos"]:
        lines.append(f"  - {reg}: {int(errs_by_region.get(reg, 0))} errores")

    lines.append("\n🎯 Recomendación básica de práctica:")
    lines.append(f"   Región: {region_focus} → {reco_msg}\n")
    return "\n".join(lines)


# =======================================
#  Reporte completo (con KMeans disponible)
# =======================================

def _build_report(
    csv_path: Path,
    df: pd.DataFrame,
    k: int,
    feats,
    df_err: pd.DataFrame,
    summaries,
    reco
) -> str:
    """
    Arma el string del reporte completo cuando SÍ se pudo ejecutar KMeans.
    Se separa en una función para reutilizar esto más adelante (por ejemplo,
    al integrarlo con UI o para exportar el texto tal cual a un archivo).
    """
    n_total = len(df)
    n_correct = int((df["correct"] == 1).sum())
    acc = (n_correct / n_total) if n_total else 0.0

    lines = []
    lines.append("==========================================")
    lines.append("          📊 EARTRAINER – STATS")
    lines.append("==========================================")
    lines.append(f"CSV: {csv_path.resolve()}")
    lines.append(f"Intentos totales: {n_total}  |  Aciertos: {n_correct}  |  Acc: {acc:.1%}")
    lines.append("------------------------------------------")
    lines.append(f"Errores considerados: {len(df_err)}")
    lines.append(f"Features: {feats}")  # útil para entender qué “variables” vio KMeans
    lines.append("------------------------------------------")
    lines.append(f"k usado: {k}")
    lines.append("\n────────────── Resumen de Clusters ──────────────")
    for s in sorted(summaries, key=lambda x: x.label):
        lines.append(f"• Cluster {s.label}:")
        lines.append(f"    n_errores     : {s.n}")
        lines.append(f"    dist_media    : {s.mean_dist:.2f} bandas")
        lines.append(f"    sesgo         : {s.bias_txt}")
        lines.append(f"    región_dom    : {s.region_mode}")
        lines.append(f"    sugerencia    : {s.suggestion}")
    lines.append("─────────────────────────────────────────────────")
    lines.append(f"\n🎯 Recomendación de práctica → Región: {reco['region']}")
    lines.append(f"   {reco['message']}\n")
    return "\n".join(lines)


# =====
#  CLI
# =====

def main():
    """
    Punto de entrada del script cuando se ejecuta desde consola.

    Flujo:
      1) Parseo de argumentos.
      2) Carga del CSV (valida columnas).
      3) Intenta construir features de errores para KMeans.
         - Si no hay suficientes errores → Fallback de estadísticas básicas.
      4) Si hay suficientes errores:
         - Elige k (silhouette) o usa k forzado por argumento.
         - Ejecuta KMeans.
         - Resume clusters y produce recomendación.
      5) Imprime reporte (y lo guarda si se usa --out).
    """
    parser = argparse.ArgumentParser(description="Stats Page (KMeans) – EarTrainer")
    parser.add_argument("--csv", type=str, default=DEFAULT_CSV, help="Ruta al CSV de sesión")
    parser.add_argument("--k", type=int, default=None, help="Número de clusters (si se especifica, no usa silhouette)")
    parser.add_argument("--kmin", type=int, default=2, help="k mínimo para búsqueda automática")
    parser.add_argument("--kmax", type=int, default=4, help="k máximo para búsqueda automática")
    parser.add_argument("--out", type=str, default=None, help="Guardar reporte en un .txt")
    args = parser.parse_args()

    # Normalizamos y validamos la ruta del CSV
    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"❌ No existe el CSV: {csv_path}")
        print("   Corre primero práctica para generar datos (p. ej., python run_practice_cli.py).")
        return

    # (1) Cargar datos
    try:
        df = load_session_log(str(csv_path))
    except Exception as e:
        print(f"❌ Error cargando CSV: {e}")
        return

    # Validación de esquema del CSV (evita fallos crípticos más adelante)
    missing = _validate_columns(df)
    if missing:
        print(f"❌ El CSV no tiene las columnas requeridas: {missing}")
        print("   Esperado: timestamp,module,band_true,band_user,correct,rt_ms")
        return

    # (2) Intentar construir features SOLO de errores (para KMeans)
    #     build_error_features devuelve (X, features, df_err) o (None, [], df_err) si no alcanza.
    X, feats, df_err = build_error_features(df)

    # Fallback: si no hay suficientes errores, mostramos estadísticas básicas y salimos.
    if X is None or df_err is None or df_err.empty:
        report = _basic_stats_report(csv_path, df)
        print(report)
        if args.out:
            Path(args.out).write_text(report, encoding="utf-8")
            print(f"💾 Reporte guardado en: {Path(args.out).resolve()}")
        return

    # (3) Elegir k: por defecto usamos silhouette en el rango [kmin, kmax].
    #     Si el usuario pasa --k, respetamos ese valor directamente.
    if args.k is not None:
        k = int(args.k)
        print(f"🔧 Usando k={k} (forzado por argumento)")
    else:
        k = pick_k_by_silhouette(X, k_range=(args.kmin, args.kmax))
        # Seguridad: si por algún motivo silhouette no puede decidir, usa kmin
        if not isinstance(k, int):
            k = args.kmin
        print(f"🔧 k elegido automáticamente (silhouette): {k}")

    # (4) Ejecutar KMeans (con manejo de errores y fallback a k=2)
    try:
        labels, km, scaler = run_kmeans(X, k)
    except Exception as e:
        print(f"❌ Error en KMeans con k={k}: {e}")
        if k != 2:
            print("   Intentando con k=2…")
            try:
                labels, km, scaler = run_kmeans(X, 2)
                k = 2
            except Exception as e2:
                print(f"❌ También falló con k=2: {e2}")
                return
        else:
            return

    # (5) Resumen de clusters + recomendación
    summaries = summarize_clusters(labels, df_err)
    if not summaries:
        # Si algo raro pasó (clusters vacíos), volvemos al fallback básico.
        report = _basic_stats_report(csv_path, df)
        print(report)
        if args.out:
            Path(args.out).write_text(report, encoding="utf-8")
            print(f"💾 Reporte guardado en: {Path(args.out).resolve()}")
        return

    reco = recommend_focus_from_clusters(summaries)

    # (6) Construir e imprimir el reporte completo (y guardar si se pidió)
    report = _build_report(csv_path, df, k, feats, df_err, summaries, reco)
    print(report)
    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
        print(f"💾 Reporte guardado en: {Path(args.out).resolve()}")


# Guard estándar para que “python run_stats_cli.py” ejecute main()
if __name__ == "__main__":
    main()
