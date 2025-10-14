"""
run_tests.py
-------------
Pequeño script de verificación manual para el proyecto EarTrainer – Detección de Feedback.

Este archivo permite probar las funciones básicas del módulo core/bands.py
sin necesidad de instalar pytest u otras herramientas externas.

👉 Cómo usarlo:
1. Asegúrate de tener tu entorno virtual activo (venv).
2. Desde la carpeta raíz del proyecto, ejecuta:
       python run_tests.py
3. Observa los resultados en la consola.
"""

from core.bands import (
    nearest,
    band_distance,
    region_of,
    neighbors,
    BANDS,
)

print("\n🎧 Verificación de módulo: core/bands.py\n")
print("Bandas cargadas correctamente:\n", BANDS, "\n")

# === 1. Prueba de nearest() ===
print("🔹 Test 1: Función nearest() — encontrar la banda más cercana\n")
print(f"nearest(1000)  ➜ {nearest(1000)}   (esperado: 1000)")
print(f"nearest(260)   ➜ {nearest(260)}    (esperado: 250)")
print(f"nearest(1180)  ➜ {nearest(1180)}   (esperado: 1250)")
print("-" * 50, "\n")

# === 2. Prueba de band_distance() ===
print("🔹 Test 2: Función band_distance() — medir distancia entre bandas\n")
print(f"band_distance(1000, 1000) ➜ {band_distance(1000, 1000)}   (esperado: 0)")
print(f"band_distance(1000, 1250) ➜ {band_distance(1000, 1250)}   (esperado: 1)")
print(f"band_distance(1000, 1600) ➜ {band_distance(1000, 1600)}   (esperado: 2)")
print("-" * 50, "\n")

# === 3. Prueba de region_of() ===
print("🔹 Test 3: Función region_of() — clasificar frecuencia por zona\n")
print(f"region_of(200)  ➜ {region_of(200)}   (esperado: graves)")
print(f"region_of(800)  ➜ {region_of(800)}   (esperado: medios)")
print(f"region_of(2500) ➜ {region_of(2500)}  (esperado: agudos)")
print("-" * 50, "\n")

# === 4. Prueba de neighbors() ===
print("🔹 Test 4: Función neighbors() — obtener bandas vecinas\n")
print(f"neighbors(1000, k=1) ➜ {neighbors(1000, k=1)}   (esperado: [800, 1000, 1250])")
print(f"neighbors(250, k=2)  ➜ {neighbors(250, k=2)}    (esperado: [250, 315, 400])")
print(f"neighbors(8000, k=2) ➜ {neighbors(8000, k=2)}   (esperado: [5000, 6300, 8000])")
print("-" * 50, "\n")

print("✅ Fin de las pruebas manuales.")
print("Si los resultados coinciden con los valores esperados, el módulo core/bands.py funciona correctamente.\n")

# ==== Prueba rápida de ai/rules.py (feedback pedagógico) ====
from ai.rules import feedback_text

print("\n🧠 Pruebas de feedback_text() de ai/rules.py\n")
print("Caso 1 (Correcto):", feedback_text(1600, 1600))
print("Caso 2 (Casi):    ", feedback_text(1600, 1250))
print("Caso 3 (Lejos):   ", feedback_text(2000, 800))
