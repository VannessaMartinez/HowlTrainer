# data_logger.py
"""
Pequeño logger de intentos hacia data/session_log.csv
Formato: timestamp,module,band_true,band_user,correct,rt_ms
"""

from __future__ import annotations
from pathlib import Path
from datetime import datetime
from typing import Literal
import csv

CSV_PATH = Path("data/session_log.csv")
CSV_HEADERS = ["timestamp","module","band_true","band_user","correct","rt_ms"]

def ensure_csv():
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not CSV_PATH.exists():
        with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADERS)

def log_attempt(module: str, band_true: int, band_user: int, correct: int, rt_ms: int) -> None:
    ensure_csv()
    ts = datetime.now().isoformat(timespec="seconds")
    with CSV_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([ts, module, band_true, band_user, int(correct), int(rt_ms)])


def reset_session_log(mode: Literal["keep_file", "delete_file"] = "keep_file") -> None:
    """
    Resetea el session log:
      - "keep_file": reescribe el archivo manteniendo solo la cabecera.
      - "delete_file": elimina el archivo completo (se recreará al primer log_attempt).

    Uso:
        reset_session_log("keep_file")   # limpia contenido pero deja el archivo
        reset_session_log("delete_file") # borra el archivo
    """
    ensure_csv()
    if mode == "delete_file":
        try:
            CSV_PATH.unlink()
            print("🗑️  session_log.csv eliminado. Se recreará automáticamente al registrar un intento.")
            return
        except FileNotFoundError:
            return

    # keep_file: reescribe cabecera
    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADERS)
    print("🧹 session_log.csv limpiado (cabecera conservada).")
