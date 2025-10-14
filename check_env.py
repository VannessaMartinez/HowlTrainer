import sys
import os
import site
import subprocess

def is_venv_active():
    """Verifica si estás dentro de un entorno virtual."""
    # Método confiable: comparar sys.prefix con sys.base_prefix
    return sys.prefix != getattr(sys, "base_prefix", sys.prefix)

def show_python_info():
    print("🐍  Python ejecutándose desde:")
    print(sys.executable)
    print(f"Versión: {sys.version}\n")

def list_installed_packages():
    print("📦  Paquetes instalados (primeros 10):")
    try:
        output = subprocess.check_output([sys.executable, "-m", "pip", "list", "--format=columns"])
        lines = output.decode().splitlines()
        for line in lines[:12]:  # muestra encabezado + 10 paquetes
            print(line)
    except Exception as e:
        print(f"Error al listar paquetes: {e}")
    print()

def main():
    show_python_info()
    if is_venv_active():
        print("✅  Estás dentro de un entorno virtual (venv).")
        print(f"Ruta del entorno: {sys.prefix}\n")
    else:
        print("⚠️  No estás dentro de un entorno virtual.")
        print("   Ejecuta: source venv/bin/activate  (macOS/Linux)")
        print("   o:       venv\\Scripts\\Activate.ps1  (Windows)\n")

    list_installed_packages()

if __name__ == "__main__":
    main()
