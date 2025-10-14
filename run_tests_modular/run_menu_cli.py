"""
run_menu_cli.py
---------------
Menú por consola para EarTrainer – Detección de Feedback.

Opciones:
  1) Practicar (CLI)              → usa run_practice_cli.main()
  2) Ver estadísticas (KMeans)    → usa run_stats_cli.main()
  3) Demo sintética (opcional)    → usa run_kmeans_demo.main()
  0) Salir

Asegúrate de ejecutar desde la raíz del proyecto:
    python run_menu_cli.py
"""

from __future__ import annotations
import sys
from pathlib import Path

# Asegura que la raíz del proyecto esté en el path de Python
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))


def _print_header():
    print("\n==========================================")
    print("       🎧 EARTRAINER – MENÚ (CLI)         ")
    print("==========================================")
    print("1) Practicar (consola)")
    print("2) Ver estadísticas (KMeans)")
    print("3) Demo sintética (crear CSV y analizar)")
    print("4) Limpiar/Resetear session_log.csv")  # ← nueva opción
    print("0) Salir")
    print("==========================================")


def _run_practice():
    try:
        import run_practice_cli as mod
        mod.main()
    except KeyboardInterrupt:
        print("\n👋 Volviste al menú.")
    except Exception as e:
        print(f"❌ Error ejecutando práctica: {e}")


def _run_stats():
    try:
        import importlib, runpy, os
        import run_stats_cli
        run_stats_cli = importlib.reload(run_stats_cli)  # recarga por si editaste
        if hasattr(run_stats_cli, "main"):
            run_stats_cli.main()
        else:
            # Si no tiene main, ejecútalo como script para ver el error real
            runpy.run_path(os.path.join(ROOT, "run_stats_cli.py"), run_name="__main__")
    except Exception as e:
        print(f"❌ Error ejecutando stats: {e}")

def _run_demo():
    """
    Crea un CSV sintético (si no existe) y muestra clusters + recomendación.
    Útil si aún no hiciste práctica real.
    """
    try:
        import run_kmeans_demo as mod
        mod.main()
    except Exception as e:
        print(f"❌ Error ejecutando demo sintética: {e}")


def main():
    while True:
        _print_header()
        choice = input("Elige una opción: ").strip()
        if choice == "1":
            _run_practice()
        elif choice == "2":
            _run_stats()
        elif choice == "3":
            _run_demo()
        elif choice == "4":
            _run_reset_log()  # ← nueva opción
        elif choice == "0":
            print("👋 ¡Hasta luego!"); break
        else:
            print("⚠️ Opción no válida. Intenta de nuevo.")

def _run_reset_log():
    from data_logger import reset_session_log
    print("\n⚠️  Esta acción borrará los datos registrados en data/session_log.csv.")
    print("    (Mantendrás la cabecera si eliges 'limpiar').")
    choice = input("Elige: [L]impiar (conservar archivo) / [B]orrar archivo / [C]ancelar: ").strip().lower()
    if choice.startswith("l"):
        reset_session_log("keep_file")
    elif choice.startswith("b"):
        reset_session_log("delete_file")
    else:
        print("Operación cancelada.")


if __name__ == "__main__":
    main()
