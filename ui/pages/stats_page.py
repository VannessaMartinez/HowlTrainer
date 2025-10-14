"""
ui/pages/stats_page.py
----------------------
Página de "Stats" (dentro de la UI) para EarTrainer – Detección de Feedback.

Objetivo de esta página:
- Leer el CSV de práctica (por defecto: data/session_log.csv).
- Si hay suficientes errores, ejecutar KMeans y mostrar:
    * clusters con resumen legible,
    * recomendación de práctica basada en patrones de confusión.
- Si NO hay suficientes errores, mostrar un "fallback" útil:
    * accuracy global,
    * peores bandas,
    * errores por región (graves/medios/agudos),
    * barritas ASCII de accuracy por banda,
    * recomendación simple por región.

Ventajas de tener el reporte aquí (en la UI):
- El usuario no necesita abrir la consola; puede ver su progreso "en vivo".
- Reutilizamos la lógica de analytics (mismos resultados que run_stats_cli.py).

Buenas prácticas que aplicamos:
- Separar helpers "puros" (que devuelven strings) de la UI (Text/Buttons).
- Manejo de errores con mensajes descriptivos (sin stacktraces para el usuario).
- Un método público `refresh_now()` para que otras páginas (Práctica) puedan
  pedir un refresco del reporte con un clic.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import List

import pandas as pd

# Importamos las funciones del "motor" de analítica.
# Nota pedagógica: esto mantiene el código de UI delgado y enfocado en mostrar.
from analytics.cluster_analysis import (
    load_session_log,            # lee un CSV y lo devuelve como DataFrame
    build_error_features,        # crea features SOLO de errores para clusterizar
    pick_k_by_silhouette,        # elige k automáticamente en un rango
    run_kmeans,                  # ejecuta KMeans (con estandarización interna)
    summarize_clusters,          # produce resúmenes legibles por cluster
    recommend_focus_from_clusters,  # recomienda región de práctica
)

# Ruta por defecto del CSV (el logger lo crea/actualiza ahí)
DEFAULT_CSV = "data/session_log.csv"


# =======================================================================
# Helpers "puros" (no tocan la UI): validan, formatean y construyen texto
# =======================================================================

def _validate_columns(df: pd.DataFrame) -> List[str]:
    """
    Verifica que el CSV tenga las columnas mínimas.
    Si faltan, el resto del pipeline fallaría o daría resultados confusos,
    así que paramos temprano con un mensaje claro.
    """
    required = {"timestamp", "module", "band_true", "band_user", "correct", "rt_ms"}
    return [c for c in required if c not in df.columns]


def _region_of(freq: float) -> str:
    """
    Mapea una frecuencia a una región perceptiva amplia.
    Esto es útil para "agrupar" errores en grandes zonas del espectro.
    - graves:  < 500 Hz
    - medios:  500–1999 Hz
    - agudos:  ≥ 2000 Hz
    """
    f = float(freq)
    if f < 500: 
        return "graves"
    if f < 2000: 
        return "medios"
    return "agudos"


def _ascii_bar(value: float, width: int = 25) -> str:
    """
    Dibuja una barrita ASCII para visualizar un porcentaje (0..1) sin gráficos.
    Ejemplo: value=0.72 → '███████████████████----' (~72% lleno).
    - ¿Por qué útil? Aporta una "sensación" visual en puro texto.
    """
    value = max(0.0, min(1.0, float(value)))   # clamp a [0, 1]
    filled = int(round(value * width))
    return "█" * filled + "-" * (width - filled)


def _basic_stats_report(csv_path: Path, df: pd.DataFrame) -> str:
    """
    Fallback de estadísticas cuando NO hay suficientes errores para KMeans.
    Devuelve un string autoexplicativo que la UI colocará en el widget Text.
    """
    # Métricas globales
    n_total = len(df)
    n_correct = int((df["correct"] == 1).sum())
    acc = (n_correct / n_total) if n_total else 0.0

    # Accuracy por banda (ordenamos por menor acc para ver "puntos débiles")
    by_band = (
        df.groupby("band_true")["correct"]
          .agg(["count", "mean"])    # count = n intentos, mean = accuracy promedio (0/1)
          .rename(columns={"count": "n", "mean": "acc"})
          .sort_values("acc", ascending=True)
    )
    worst5 = by_band.head(5)

    # Errores por región (graves/medios/agudos)
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

    # Recomendación simple basada en la región con más errores
    region_focus = errs_by_region.idxmax() if errs_by_region.sum() > 0 else "general"
    reco_msg = {
        "graves": "Practica ≤500 Hz (250–500). Contrasta 250/315/400 Hz.",
        "medios": "Refuerza 500–2000 Hz. Contrasta 1 kHz vs 2 kHz.",
        "agudos": "Practica 2–8 kHz con pasos de 1 banda y Q estrecha.",
        "general": "Aún no hay suficientes intentos para recomendar región."
    }[region_focus]

    # Construimos el reporte como texto (la UI solo muestra este string)
    lines = []
    lines.append("==========================================")
    lines.append("          📊 EARTRAINER – STATS (UI)")
    lines.append("==========================================")
    lines.append(f"CSV: {csv_path.resolve()}")
    lines.append(f"Intentos totales: {n_total}  |  Aciertos: {n_correct}  |  Acc: {acc:.1%}")
    lines.append("------------------------------------------")
    lines.append("ℹ️  No hay suficientes errores para KMeans (se recomiendan ≥ 8).")
    lines.append("    Mostrando estadísticas básicas:\n")

    lines.append("• Top 5 bandas con menor accuracy:")
    if worst5.empty:
        lines.append("  (No hay suficientes datos por banda).")
    else:
        for band, row in worst5.iterrows():
            lines.append(f"  - {int(band)} Hz → acc={row['acc']:.1%}  (n={int(row['n'])})")

    # Mini "gráfico" ASCII por banda (orden natural por frecuencia)
    lines.append("\n• Accuracy por banda (gráfico ASCII):")
    if by_band.empty:
        lines.append("  (No hay datos por banda todavía).")
    else:
        for band in sorted(by_band.index.tolist()):
            row = by_band.loc[band]
            acc_b = float(row["acc"]) if pd.notna(row["acc"]) else 0.0
            bar = _ascii_bar(acc_b, width=25)
            lines.append(f"  {int(band):>5} Hz | {bar} | {acc_b:5.1%}  (n={int(row['n'])})")

    # Conteo de errores por región (útil para guiar práctica gruesa)
    lines.append("\n• Errores por región:")
    for reg in ["graves", "medios", "agudos"]:
        lines.append(f"  - {reg}: {int(errs_by_region.get(reg, 0))} errores")

    # Recomendación "rápida" cuando no hay KMeans
    lines.append("\n🎯 Recomendación básica de práctica:")
    lines.append(f"   Región: {region_focus} → {reco_msg}\n")
    return "\n".join(lines)


def _build_full_report(
    csv_path: Path,
    df: pd.DataFrame,
    k: int,
    feats,
    df_err: pd.DataFrame,
    summaries,
    reco,
) -> str:
    """
    Construye el reporte de texto cuando SÍ hay suficientes errores para
    ejecutar KMeans con sentido. Separa "datos" de "presentación".
    """
    n_total = len(df)
    n_correct = int((df["correct"] == 1).sum())
    acc = (n_correct / n_total) if n_total else 0.0

    lines = []
    lines.append("==========================================")
    lines.append("          📊 EARTRAINER – STATS (UI)")
    lines.append("==========================================")
    lines.append(f"CSV: {csv_path.resolve()}")
    lines.append(f"Intentos totales: {n_total}  |  Aciertos: {n_correct}  |  Acc: {acc:.1%}")
    lines.append("------------------------------------------")
    lines.append(f"Errores considerados: {len(df_err)}")
    lines.append(f"Features: {feats}")      # útil para recordar qué variables vio KMeans
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


# ===========================
# Clase de UI: StatsPage (Tk)
# ===========================

class StatsPage(ttk.Frame):
    """
    Un Frame (pestaña) que muestra estadísticas "en vivo" desde la UI.
    Contiene:
    - entrada para elegir el CSV,
    - entrada para k (auto o número),
    - botones para actualizar y guardar,
    - un Text grande donde pegamos el reporte.

    Diseño pedagógico:
    - Todo el "cálculo" está fuera (helpers / analytics). Aquí solo orquestamos
      y controlamos la experiencia de usuario.
    """

    def __init__(self, parent):
        super().__init__(parent)

        # ------- Controles superiores (inputs y botones) -------
        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 8))

        ttk.Label(top, text="CSV de sesión:").pack(side="left")
        self.csv_var = tk.StringVar(value=DEFAULT_CSV)
        self.csv_entry = ttk.Entry(top, textvariable=self.csv_var, width=50)
        self.csv_entry.pack(side="left", padx=6)

        ttk.Button(top, text="📂 Buscar…", command=self.on_browse).pack(side="left", padx=(0, 8))

        # Campo para k: "auto" o un número entero (>=2).
        self.k_var = tk.StringVar(value="auto")
        ttk.Label(top, text="k:").pack(side="left")
        self.k_entry = ttk.Entry(top, textvariable=self.k_var, width=6)
        self.k_entry.pack(side="left", padx=(4, 8))

        ttk.Button(top, text="🔄 Actualizar stats", command=self.on_refresh).pack(side="left")
        ttk.Button(top, text="💾 Guardar reporte…", command=self.on_save).pack(side="left", padx=(6, 0))

        # ------- Área de reporte (solo texto) -------
        self.txt = tk.Text(self, wrap="word")
        self.txt.configure(state="disabled")
        self.txt.pack(fill="both", expand=True)

        # Mensaje inicial para guiar al usuario
        self._set_report("Pulsa “🔄 Actualizar stats” para generar el reporte.")

    # -----------------------
    # Métodos utilitarios UI
    # -----------------------

    def _set_report(self, text: str):
        """
        Coloca un string en el Text de reporte.
        Lo hacemos "atómico": deshabilitamos el Text para evitar edición accidental.
        """
        self.txt.configure(state="normal")
        self.txt.delete("1.0", "end")
        self.txt.insert("1.0", text)
        self.txt.configure(state="disabled")

    # -----------------------
    # Callbacks de los botones
    # -----------------------

    def on_browse(self):
        """
        Permite elegir un CSV distinto (por si quieres analizar otro archivo).
        """
        path = filedialog.askopenfilename(
            title="Selecciona session_log.csv",
            filetypes=[("CSV", "*.csv"), ("Todos", "*.*")]
        )
        if path:
            self.csv_var.set(path)

    def on_save(self):
        """
        Guarda en disco el contenido actual del Text (el reporte tal cual).
        Útil para entregas o compartir con un tutor.
        """
        content = self.txt.get("1.0", "end").strip()
        if not content:
            messagebox.showinfo("Info", "No hay reporte para guardar.")
            return
        dest = filedialog.asksaveasfilename(
            title="Guardar reporte",
            defaultextension=".txt",
            filetypes=[("Texto", "*.txt")]
        )
        if dest:
            Path(dest).write_text(content, encoding="utf-8")
            messagebox.showinfo("Listo", f"Reporte guardado en:\n{dest}")

    def on_refresh(self):
        """
        Genera el reporte:
        1) Carga el CSV y valida columnas.
        2) Intenta construir features de errores para KMeans.
        3) Si no hay suficientes errores → fallback básico.
        4) Si hay suficientes errores:
           - elige k (auto o forzado),
           - corre KMeans,
           - resume clusters + recomienda,
           - muestra el reporte completo.
        """
        csv_path = Path(self.csv_var.get()).expanduser()
        if not csv_path.exists():
            self._set_report(f"❌ No existe el CSV: {csv_path}")
            return

        # 1) Cargar CSV
        try:
            df = load_session_log(str(csv_path))
        except Exception as e:
            self._set_report(f"❌ Error cargando CSV: {e}")
            return

        # 2) Validar columnas
        missing = _validate_columns(df)
        if missing:
            self._set_report("❌ CSV inválido. Faltan columnas: " + ", ".join(missing))
            return

        # 3) Construir features SOLO de errores (si no hay, no tiene sentido clusterizar)
        X, feats, df_err = build_error_features(df)
        if X is None or df_err is None or df_err.empty:
            # Fallback (estadísticas básicas)
            report = _basic_stats_report(csv_path, df)
            self._set_report(report)
            return

        # 4) Determinar k: automático (silhouette) o forzado por el usuario
        k_str = self.k_var.get().strip().lower()
        if k_str == "auto" or k_str == "":
            k = pick_k_by_silhouette(X, k_range=(2, 4))
            if not isinstance(k, int):   # por si silhouette no decide bien
                k = 2
        else:
            try:
                k = max(2, int(k_str))  # garantizamos k>=2
            except ValueError:
                messagebox.showwarning("k inválido", "Usando k automático (2..4).")
                k = pick_k_by_silhouette(X, k_range=(2, 4)) or 2

        # 5) Ejecutar KMeans (con un pequeño fallback)
        try:
            labels, km, scaler = run_kmeans(X, k)
        except Exception as e:
            messagebox.showwarning("KMeans", f"Fallo con k={k}: {e}\nProbando k=2…")
            try:
                labels, km, scaler = run_kmeans(X, 2)
                k = 2
            except Exception as e2:
                self._set_report(f"❌ KMeans falló incluso con k=2: {e2}")
                return

        # 6) Resumir clusters (si por algún motivo quedan vacíos, usa fallback)
        summaries = summarize_clusters(labels, df_err)
        if not summaries:
            report = _basic_stats_report(csv_path, df)
            self._set_report(report)
            return

        # 7) Recomendación + reporte final
        reco = recommend_focus_from_clusters(summaries)
        report = _build_full_report(csv_path, df, k, feats, df_err, summaries, reco)
        self._set_report(report)

    # ------------------------------------------
    # API pública para otras páginas de la app
    # ------------------------------------------

    def refresh_now(self):
        """
        Método público: refresca el reporte como si el usuario hubiese
        pulsado el botón “🔄 Actualizar stats”.

        ¿Por qué existe?
        - Para que la página de Práctica (TonesPage) pueda, tras un intento,
          mandar a refrescar el análisis y mostrarlo de inmediato.
        """
        self.on_refresh()
