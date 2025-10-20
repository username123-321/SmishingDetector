import tkinter as tk
from tkinter import ttk

class IntroScreen:
    def __init__(self, master, duration=3000):
        """
        master: main Tk() window
        duration: how long the intro is visible in ms
        """
        self.master = master
        self.duration = duration

        # Create intro as Toplevel
        self.root = tk.Toplevel(master)
        self.root.overrideredirect(True)  # no title bar
        self.root.configure(bg="#1e1e1e")

        # Center the window
        self.width = 500
        self.height = 300
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (self.width // 2)
        y = (screen_height // 2) - (self.height // 2)
        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")

        # Make sure the intro is on top
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after_idle(self.root.attributes, "-topmost", False)

        # Start invisible for fade-in
        self.root.attributes("-alpha", 0.0)
        self.alpha = 0.0

        # Title label
        tk.Label(
            self.root,
            text="🕵🏽 Smishing/Spam Detector",
            font=("Arial", 22, "bold"),
            fg="white",
            bg="#1e1e1e"
        ).pack(expand=True)

        # Loading label
        self.loading_label = tk.Label(
            self.root,
            text="Loading...",
            font=("Arial", 16),
            fg="white",
            bg="#1e1e1e"
        )
        self.loading_label.pack()

        # Smooth progress bar
        self.progress = ttk.Progressbar(
            self.root,
            orient=tk.HORIZONTAL,
            length=350,
            mode='determinate',
            maximum=100
        )
        self.progress.pack(pady=20)
        self.progress_value = 0

        # Hide main window
        self.master.withdraw()

        # Start animations
        self.fade_in()
        self.update_progress()

    def fade_in(self):
        if self.alpha < 1.0:
            self.alpha += 0.02
            self.root.attributes("-alpha", self.alpha)
            self.root.after(20, self.fade_in)
        else:
            self.root.after(self.duration, self.fade_out)

    def fade_out(self):
        if self.alpha > 0.0:
            self.alpha -= 0.02
            self.root.attributes("-alpha", self.alpha)
            self.root.after(20, self.fade_out)
        else:
            self.close()

    def update_progress(self):
        if self.progress_value < 100:
            self.progress_value += 1
            self.progress['value'] = self.progress_value
            self.root.after(self.duration // 100, self.update_progress)

    def close(self):
        self.root.destroy()
        self.master.deiconify()
