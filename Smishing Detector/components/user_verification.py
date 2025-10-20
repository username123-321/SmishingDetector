import tkinter as tk
from tkinter import ttk

class UserVerification:
    def __init__(self, root, comp_name, model_result):
        """
        root: main Tk window or parent frame
        comp_name: the SMS text that was classified
        model_result: predicted label (e.g., 'Smish', 'Spam', 'Ham')
        """
        self.root = root
        self.comp_name = comp_name
        self.model_result = model_result
        self.result = None

    def ask_user(self):
        """Show modern dark-themed popup asking for user confirmation."""
        self.popup = tk.Toplevel(self.root)
        self.popup.title("Message Verification")
        self.popup.configure(bg="#1e1e1e")
        self.popup.geometry("410x360")
        self.popup.resizable(False, False)
        self.popup.transient(self.root)
        self.popup.grab_set()

        # --- Center popup relative to main window ---
        self.root.update_idletasks()
        root_x = self.root.winfo_x()
        root_y = self.root.winfo_y()
        root_width = self.root.winfo_width()
        root_height = self.root.winfo_height()

        popup_width = 410
        popup_height = 360

        x = root_x + (root_width // 2) - (popup_width // 2)
        y = root_y + (root_height // 2) - (popup_height // 2)

        self.popup.geometry(f"{popup_width}x{popup_height}+{x}+{y}")

        # --- Frame content ---
        title = tk.Label(
            self.popup, text="🔔 Verification Required",
            bg="#1e1e1e", fg="white", font=("Arial", 16, "bold")
        )
        title.pack(pady=(20, 10))

        color = "#ff0000" if self.model_result == "Smishing" else "#aeff00"

        detected = tk.Label(
            self.popup,
            text=f"Model detected: {self.model_result}",
            bg="#1e1e1e", fg=color, font=("Arial", 13)
        )
        detected.pack(pady=(0, 10))

        msg = tk.Message(
            self.popup,
            text=f"Message:\n\"{self.comp_name[:80]}...\"\n\n"
                 "Were you expecting this message from the sender/site?",
            bg="#1e1e1e", fg="white", width=360, font=("Arial", 12)
        )
        msg.pack(padx=10, pady=(5, 20))
        # --- Buttons ---
        button_frame = tk.Frame(self.popup, bg="#1e1e1e")
        button_frame.pack(pady=(5, 10))

        # Green button (YES)
        yes_btn = tk.Button(
            button_frame,
            text="✅ Yes, I was expecting it",
            bg="#27ae60",        # dark green
            activebackground="#2ecc71",  # lighter green on hover
            fg="white",
            activeforeground="white",
            font=("Arial", 12, "bold"),
            relief="flat",
            padx=10, pady=6,
            command=self._on_yes
        )
        yes_btn.grid(row=0, column=0, padx=10)

        # Red button (NO)
        no_btn = tk.Button(
            button_frame,
            text="🚫 No, I wasn't",
            bg="#c0392b",        # dark red
            activebackground="#e74c3c",  # lighter red on hover
            fg="white",
            activeforeground="white",
            font=("Arial", 12, "bold"),
            relief="flat",
            padx=10, pady=6,
            command=self._on_no
        )
        no_btn.grid(row=0, column=1, padx=10)

        self.popup.wait_window()
        return self.result

    def _on_yes(self):
        """User says yes → Legit"""
        self.result = "Legit"
        self.popup.destroy()

    def _on_no(self):
        """User says no → Return model result"""
        self.result = self.model_result
        self.popup.destroy()
