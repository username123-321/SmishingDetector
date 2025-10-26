import customtkinter as ctk
import tkinter as tk
import itertools


class IntroScreen:
    def __init__(self, master, duration=3000):
        """
        Police-style intro screen (blue-red flashing shield, smoother & slower)
        """
        self.master = master
        self.duration = duration

        # === Splash window ===
        self.root = ctk.CTkToplevel(master)
        self.root.overrideredirect(True)
        self.root.configure(fg_color=("#F9F9F9", "#0D1117"))
        self.root.geometry("520x300")
        self._center_window()
        self.alpha = 0.0
        self.root.attributes("-alpha", self.alpha)

        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after_idle(self.root.attributes, "-topmost", False)

        self.master.withdraw()
        self.root.withdraw()
        self.root.after(80, self._show_and_start)

        # === Card frame ===
        frame = ctk.CTkFrame(self.root, corner_radius=18)
        frame.pack(expand=True, fill="both", padx=15, pady=15)

        # === Title ===
        title_row = ctk.CTkFrame(frame, fg_color="transparent")
        title_row.pack(pady=(68, 10))

        mode = ctk.get_appearance_mode().lower()
        bg_color = "#F9F9F9" if mode == "light" else "#0D1117"

        # === Canvas shield ===
        self.canvas = tk.Canvas(
            title_row, width=26, height=26,
            bg=bg_color, highlightthickness=0, bd=0, relief="flat"
        )
        self.canvas.pack(side="left", padx=(0, 10))
        self.shield_shape = self.canvas.create_polygon(
            13, 2, 23, 8, 23, 17, 13, 24, 3, 17, 3, 8,
            fill="#1e88e5", outline="#1e88e5"
        )

        # === Title Text ===
        ctk.CTkLabel(
            title_row, text="SMS ",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="normal"),
            text_color=("#1e88e5", "#58a6ff")
        ).pack(side="left", anchor="s")

        ctk.CTkLabel(
            title_row, text="Detector",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color=("#1e88e5", "#58a6ff")
        ).pack(side="left", anchor="s")

        # === Loading text ===
        self.loading_label = ctk.CTkLabel(
            frame, text="Starting...",
            font=ctk.CTkFont(family="Segoe UI", size=15, slant="italic"),
            text_color=("#333333", "#C9D1D9")
        )
        self.loading_label.pack(pady=(8, 20))

        # === Progress bar ===
        self.progress = ctk.CTkProgressBar(frame, width=340, height=10)
        self.progress.pack(pady=(5, 20))
        self.progress.set(0)
        self.progress_value = 0

        # === Footer ===
        self.footer_label = ctk.CTkLabel(
            frame, text="Be responsible for your security.",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=("#666666", "#9AA0A6")
        )
        self.footer_label.pack(side="bottom", pady=(0, 25))

        # Animations
        self.loading_states = itertools.cycle(["Starting.", "Starting..", "Starting..."])
        self.light_colors = itertools.cycle(["#1e88e5", "#ff1744"])  # blue/red alternating

    # ----- Helpers -----
    def _center_window(self):
        self.root.update_idletasks()
        w, h = 520, 300
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = int((sw - w) / 2)
        y = int((sh - h) / 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _show_and_start(self):
        self._center_window()
        self.root.deiconify()
        self._fade_in()
        self._animate_loading()
        self._update_progress()
        self._animate_police_lights()

    # ----- Animations -----
    def _fade_in(self):
        if self.alpha < 1.0:
            self.alpha += 0.03
            self.root.attributes("-alpha", self.alpha)
            self.root.after(20, self._fade_in)
        else:
            self.root.after(self.duration, self._fade_out)

    def _fade_out(self):
        if self.alpha > 0.0:
            self.alpha -= 0.03
            self.root.attributes("-alpha", self.alpha)
            self.root.after(20, self._fade_out)
        else:
            self._close()

    def _animate_loading(self):
        self.loading_label.configure(text=next(self.loading_states))
        self.root.after(350, self._animate_loading)

    def _update_progress(self):
        if self.progress_value < 100:
            self.progress_value += 1
            self.progress.set(self.progress_value / 100)
            self.root.after(self.duration // 100, self._update_progress)

    def _animate_police_lights(self):
        """Alternates shield color between blue and red smoothly."""
        next_color = next(self.light_colors)
        self.canvas.itemconfig(self.shield_shape, fill=next_color, outline=next_color)
        # slower and smoother switching (was 450ms → now 700ms)
        self.root.after(700, self._animate_police_lights)

    # ----- Teardown -----
    def _close(self):
        self.root.destroy()
        self.master.deiconify()
