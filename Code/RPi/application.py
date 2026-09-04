import tkinter as tk

import csv_output
from c200_camera import C200Camera
from config import DESKTOP_RESULTS_DIR
from cycle_controller import CycleController
from gui import AutoLottoApp
from motion_control import setup_gpio


class AutoLottoApplication:
    def __init__(self):
        self.root = tk.Tk()
        self.camera = None
        self.controller = None

    def initialize(self):
        try:
            self.camera = C200Camera()
            setup_gpio()
            csv_output.DESKTOP_RESULTS_DIR = DESKTOP_RESULTS_DIR
            csv_output.initialize_csv_output()
        except (RuntimeError, ImportError) as exc:
            self._show_initialization_error(exc)
            return False

        self.controller = CycleController(self.camera)
        self.gui = AutoLottoApp(self.root, self.camera, self.controller)
        return True

    def _show_initialization_error(self, error):
        self.root.title("AutoLotto")
        self.root.geometry("800x480")
        self.root.configure(bg="#071727")
        tk.Label(
            self.root,
            text=f"Status: Unable to initialize: {error}",
            font=("Helvetica", 18, "bold"),
            fg="#ffffff",
            bg="#071727",
        ).pack(pady=(60, 20))
        tk.Button(
            self.root,
            text="CLOSE",
            command=self.root.destroy,
            font=("Helvetica", 24, "bold"),
        ).pack(pady=40, ipadx=40, ipady=20)

    def run(self):
        if self.initialize():
            self.gui.run()
        else:
            self.root.mainloop()
