"""
main.py
-------
Punto de entrada de la aplicación Tkinter para el EarTrainer - Detección de Feedback.

Qué hace este archivo:
- Crea la ventana principal (Tk) y un contenedor con un Notebook (pestañas).
- Agrega dos páginas (Frames):
    1) TonesPage  → práctica de detección de feedback (reproducir, responder, registrar).
    2) StatsPage  → ver estadísticas (KMeans o fallback) y guardar reporte.
- Implementa un cierre seguro: si hay audio reproduciéndose, lo detiene al salir.

Diseño pedagógico:
- Mantener la **UI desacoplada**: la lógica “pesada” vive en módulos (core/ai/analytics).
- Usar un **callback** inyectado para que TonesPage pueda “saltar” a StatsPage
  sin conocer su implementación (bajo acoplamiento, alta cohesión).
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

# Importamos las páginas (Frames) que componen las pestañas del Notebook.
# Nota: estas rutas funcionan si ejecutas "python main.py" desde la raíz del proyecto.
from ui.pages.tones_page import TonesPage
from ui.pages.stats_page import StatsPage
from ui.pages.about_page import AboutPage


class App(tk.Tk):
    """
    Ventana principal de la aplicación.
    Hereda de tk.Tk (la “raíz” de Tkinter) y configura:
      - título, tamaño inicial y mínimo
      - un contenedor principal con padding
      - un Notebook (pestañas) con:
          * TonesPage (Práctica)
          * StatsPage (Stats)
      - manejo de cierre seguro (detener audio antes de salir)
    """

    def __init__(self) -> None:
        super().__init__()

        # Icono de ventana (funciona en Windows y Linux; en macOS cambia el icono de la ventana,
        # pero el del Dock puede seguir siendo el de Tk por limitación de Tk)
        try:
            import tkinter as tk  # ya importado
            self._icon = tk.PhotoImage(file="assets/howl_logo.png")  # guarda referencia en self para que no se libere
            self.iconphoto(True, self._icon)
        except Exception as e:
            # Si el archivo no está o hay un problema, no rompemos la app
            print(f"[Icono] No se pudo cargar el logo: {e}")

        # --- Configuración básica de la ventana ---
        self.title("HowlTrainer – Detección de Feedback")
        # geometry: tamaño inicial (ancho x alto). minsize: tamaño mínimo permitido.
        self.geometry("820x560")
        self.minsize(780, 520)

        # --- Contenedor principal ---
        # Usamos un Frame con padding para que el contenido “respire”.
        container = ttk.Frame(self, padding=12)
        container.pack(fill="both", expand=True)

        # --- Notebook (pestañas) ---
        # El Notebook nos permite tener múltiples “páginas” en la misma ventana.
        nb = ttk.Notebook(container)
        nb.pack(fill="both", expand=True)

        # 1) Creamos primero la página de Stats para tener su referencia disponible.
        #    Esto permite inyectar un callback en TonesPage que interactúe con StatsPage.
        self.page_stats = StatsPage(nb)

        # 2) Definimos un callback que:
        #    a) Cambia a la pestaña Stats
        #    b) Pide a StatsPage que se refresque (cálculo de KMeans o fallback)
        #    Nota: NO llamamos nada aquí todavía; solo definimos la función.
        def _go_to_stats():
            nb.select(self.page_stats)     # cambia visualmente a la pestaña Stats
            self.page_stats.refresh_now()  # recalcula y muestra el reporte dentro de la UI

        # 3) Creamos la página de práctica e **inyectamos** el callback.
        #    Orden correcto de argumentos:
        #      - primero el posicional `parent` (nb),
        #      - luego el keyword `go_to_stats` con la función (sin paréntesis).
        self.page_tones = TonesPage(
            nb,
            go_to_stats=_go_to_stats
        )
        # 4) AboutPage (Ayuda) como tercera pestaña
        self.page_about = AboutPage(nb)

        # 4) Añadimos las dos páginas al Notebook con sus etiquetas.
        nb.add(self.page_tones, text="Práctica")
        nb.add(self.page_stats, text="Stats")
        nb.add(self.page_about, text="About")

        # --- Cierre seguro ---
        # Si el usuario cierra la ventana (botón X), detén audio (si suena)
        # y luego destruye la app. Esto evita que queden streams abiertos.
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # --- Menú superior: Ayuda ---
        # Nota pedagógica: en macOS, Tk puede integrar un menú global del sistema.
        menubar = tk.Menu(self)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Acerca de / Ayuda", command=self.show_about_help)
        menubar.add_cascade(label="Ayuda", menu=help_menu)

        # Asigna el menú a la ventana
        self.config(menu=menubar)


    def on_close(self) -> None:
        """
        Callback de cierre de la app.
        Intenta parar cualquier audio en reproducción (si la página de práctica lo inició),
        y luego destruye la ventana. Si algo falla, no interrumpe el cierre.
        """
        try:
            # La TonesPage expone un método seguro para detener el audio activo.
            self.page_tones.safe_stop_audio()
        except Exception:
            # No queremos que un error al detener audio impida cerrar la app.
            pass

        # Cierra la ventana y finaliza el bucle principal de Tkinter.
        self.destroy()


# Guard estándar: si ejecutamos "python main.py", se crea la App y se corre el mainloop.
# (Si este módulo fuese importado por otro archivo, este bloque no se ejecutaría.)

    def show_about_help(self):
        """
        Abre el diálogo 'Acerca de / Ayuda'.
        Lo mantenemos en un módulo separado para que main.py quede limpio.
        """
        try:
            from ui.dialogs.about import AboutDialog
            AboutDialog(self)
        except Exception as e:
            # Si algo raro pasa, degradamos a un messagebox informativo
            import tkinter.messagebox as mbox
            mbox.showinfo("Acerca de / Ayuda", f"No se pudo abrir el diálogo.\n\nDetalle: {e}")

if __name__ == "__main__":
    app = App()
    app.mainloop()
