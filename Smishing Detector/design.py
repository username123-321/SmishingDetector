import customtkinter as ctk
import json
import builtins
import os

SETTINGS_FILE = "user_settings.json"
PLACEHOLDER_TEXT = "Type here..."


# ===== Load & Save Persistent Settings =====
def load_user_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_user_settings(data):
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print("Settings save error:", e)


def build_ui():
    # ===== Load previous settings =====
    settings = load_user_settings()
    last_font_size = settings.get("font_size", 13)
    last_theme = settings.get("theme", "System")
    auto_save = settings.get("auto_save", "off")

    # ===== Theme & Root =====
    ctk.set_appearance_mode(last_theme.lower())
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("🕵🏽 SMS Detector 🕵🏽")
    root.geometry("1000x600")
    root.minsize(880, 550)

    # ===== Tab Control =====
    tabs = ctk.CTkTabview(
        root,
        corner_radius=18,
        fg_color=("#2b2b2b", "#1f1f1f"),
        segmented_button_fg_color=("#3a3a3a", "#292929"),
        segmented_button_selected_color=("#1e88e5", "#1565c0"),
        segmented_button_selected_hover_color=("#2196f3", "#1976d2"),
        segmented_button_unselected_color=("#4a4a4a", "#3a3a3a"),
        segmented_button_unselected_hover_color=("#5a5a5a", "#4a4a4a"),
        text_color=("#ffffff", "#e0e0e0"),
        height=80,
    )
    tabs._segmented_button.configure(
        font=ctk.CTkFont(size=16, weight="bold"),
        height=42,
        corner_radius=12,
    )
    tabs.pack(fill="both", expand=True, padx=15, pady=(20, 15))

    detect_tab = tabs.add("Detect")
    log_tab = tabs.add("Anatomy")
    settings_tab = tabs.add("Settings")

    for tab in (detect_tab, log_tab, settings_tab):
        tab.pack_propagate(False)
        tab.grid_propagate(False)

    # ============================================================== #
    #                      DETECT TAB                                #
    # ============================================================== #
    detect_container = ctk.CTkFrame(detect_tab, corner_radius=10)
    detect_container.pack(fill="both", expand=True, padx=10, pady=10)

    left_frame = ctk.CTkFrame(detect_container, corner_radius=12)
    left_frame.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=10)

    right_frame = ctk.CTkFrame(detect_container, width=240, corner_radius=12)
    right_frame.pack(side="right", fill="y", pady=10)

    # ===== SMS Input =====
    title_label = ctk.CTkLabel(
        left_frame, text="💬 SMS BOX",
        font=ctk.CTkFont(size=18, weight="bold"),
    )
    title_label.pack(anchor="w", pady=(10, 5), padx=10)

    input_box = ctk.CTkTextbox(
        left_frame, height=100, corner_radius=10,
        font=ctk.CTkFont("Consolas", last_font_size),
    )
    input_box.pack(fill="x", padx=10, pady=(0, 10))

    # FIXED: Proper placeholder system
    input_box._placeholder_active = False

    def reset_placeholder():
        """Reset to placeholder state"""
        input_box.delete("1.0", "end")
        input_box.insert("1.0", PLACEHOLDER_TEXT)
        input_box._placeholder_active = True

    def clear_placeholder():
        """Clear placeholder if active"""
        if input_box._placeholder_active:
            input_box.delete("1.0", "end")
            input_box._placeholder_active = False

    def get_actual_text():
        """Get text from input box, excluding placeholder"""
        if input_box._placeholder_active:
            return ""
        return input_box.get("1.0", "end-1c").strip()

    # Initial placeholder
    reset_placeholder()

    # Event handlers
    def on_focus_in(event):
        clear_placeholder()

    def on_focus_out(event):
        if not input_box.get("1.0", "end-1c").strip():
            reset_placeholder()

    def on_key(event):
        # If any key pressed while placeholder is active, clear it
        if input_box._placeholder_active and event.char:
            root.after(1, clear_placeholder)

    input_box.bind("<FocusIn>", on_focus_in)
    input_box.bind("<FocusOut>", on_focus_out)
    input_box.bind("<Key>", on_key)

    # ===== Button Builder =====
    def make_button(parent, text, color, icon=""):
        btn = ctk.CTkButton(
            parent,
            text=f"{icon} {text}".strip(),
            fg_color=color,
            hover_color=color,
            width=190,
            height=38,
            corner_radius=8,
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        btn.pack(pady=5)
        return btn

    # ===== Buttons / Headings =====
    ra_label = ctk.CTkLabel(
        right_frame, text="RUN ANALYSIS",
        font=ctk.CTkFont(size=14, weight="bold"), text_color="#00b0ff",
    )
    ra_label.pack(anchor="w", padx=10, pady=(12, 6))

    predict_btn = make_button(right_frame, "Predict SMS", "#4A8B5D", "▶")
    clear_btn = make_button(right_frame, "Clear Input", "#A94B4B", "🗑")
    load_image_btn = make_button(right_frame, "Load Image/OCR", "#4E7CA1", "🖼")

    nc_label = ctk.CTkLabel(
        right_frame, text="NETWORK CONTROL",
        font=ctk.CTkFont(size=14, weight="bold"), text_color="#00b0ff",
    )
    nc_label.pack(anchor="w", padx=10, pady=(14, 6))

    manage_server_btn = make_button(right_frame, "Manage Server", "#6C5B8D", "🌐")

    # ===== Detected =====
    log_results_label = ctk.CTkLabel(
        left_frame, text="📋 DETECTED",
        font=ctk.CTkFont(size=18, weight="bold"),
    )
    log_results_label.pack(anchor="w", padx=10, pady=(8, 3))

    log_results_hint = ctk.CTkLabel(
        left_frame, text="Detected messages (double-click to view details)",
        font=ctk.CTkFont(size=12),
    )
    log_results_hint.pack(anchor="w", padx=10, pady=(0, 3))

    # --- Filter Dropdown ---
    filter_var = ctk.StringVar(value="All")
    filter_menu = ctk.CTkOptionMenu(
        left_frame, variable=filter_var,
        values=["All", "Smishing", "Spam", "Legit"],
        width=130,
    )
    filter_menu.pack(anchor="w", padx=10, pady=(0, 5))

    # --- Scrollable list ---
    log_box = ctk.CTkScrollableFrame(left_frame, height=230, corner_radius=10)
    log_box.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    _log_entries = []
    builtins._shared_log_entries = _log_entries
    _log_label_widgets = []
    _selected_frame_holder = {"ref": None}
    # Store current displayed entry for refresh
    _current_entry = {"entry": None}
    # Store current font size for log labels
    _current_font_size = {"value": last_font_size}

    def _color_for_label(lbl_lower: str) -> str:
        if lbl_lower == "smishing":
            return "#ff4d4d"
        if lbl_lower == "spam":
            return "#ffcc00"
        if lbl_lower == "legit":
            return "#4caf50"
        return "#00b0ff"

    def _highlight(frame: ctk.CTkFrame):
        """Single-selection highlight."""
        try:
            prev = _selected_frame_holder["ref"]
            if prev and prev.winfo_exists():
                prev.configure(fg_color=("#E5E5E5", "#2A2A2A"))
            from customtkinter import get_appearance_mode
            mode = get_appearance_mode().lower()
            frame.configure(fg_color=("#B5D3FF" if mode == "light" else "#1E3A5F"))
            _selected_frame_holder["ref"] = frame
        except Exception:
            pass

    def _open_details(entry: dict):
        """Display entry in Anatomy tab with proper formatting."""
        tabs.set("Anatomy")
        
        # Store current entry for refresh
        _current_entry["entry"] = entry
        
        details_text.configure(state="normal")
        details_text.delete("1.0", "end")

        # Extract message data
        msg_full   = entry.get("message", "")
        warnings   = entry.get("warnings", [])
        label_text = entry.get("label", "Unknown")
        sender     = entry.get("sender", "Unknown")
        user_phone = entry.get("user_phone", "Unknown")
        device     = entry.get("device_name", "Unknown")
        sent_time  = entry.get("sent_time", "Unknown")

        # Get current settings
        from customtkinter import get_appearance_mode
        mode = get_appearance_mode().lower()
        current_size = int(font_size_var.get())
        
        # Classification scheme
        label_lower = str(label_text).lower()
        if label_lower == "smishing":
            icon = "🚨"
            class_color_dark = "#ff6b6b"
            class_color_light = "#d32f2f"
        elif label_lower == "spam":
            icon = "⚠️"
            class_color_dark = "#ffd93d"
            class_color_light = "#f57c00"
        elif label_lower == "legit":
            icon = "✅"
            class_color_dark = "#6bcf7f"
            class_color_light = "#388e3c"
        else:
            icon = "ℹ️"
            class_color_dark = "#00bfff"
            class_color_light = "#0288d1"
        
        # Theme colors
        if mode == "dark":
            text_color = "#EAEAEA"
            info_color = "#00bfff"
            class_color = class_color_dark
            warn_color = "#ff6b6b"
            safe_color = "#6bcf7f"
        else:
            text_color = "#1A1A1A"
            info_color = "#0288d1"
            class_color = class_color_light
            warn_color = "#d32f2f"
            safe_color = "#388e3c"

        # Build content with proper spacing
        details_text.insert("end", " MESSAGE DETAILS ", "header")
        details_text.insert("end", "\n")
        details_text.insert("end", f"Sender: {sender}\n", "info")
        details_text.insert("end", f"User Phone: {user_phone}\n", "info")
        details_text.insert("end", f"Device: {device}\n", "info")
        details_text.insert("end", f"Time: {sent_time}\n\n", "info")

        details_text.insert("end", " CLASSIFICATION ", "header")
        details_text.insert("end", "\n\n")
        details_text.insert("end", f"{icon} {label_text.capitalize()}\n\n", "classification")

        details_text.insert("end", " MESSAGE ", "header")
        details_text.insert("end", "\n\n")
        details_text.insert("end", f"{msg_full}\n\n", "message")

        if warnings:
            details_text.insert("end", " DETECTED FEATURES ", "header")
            details_text.insert("end", "\n\n")
            for w in warnings:
                details_text.insert("end", f"• {w}\n", "warning")
        else:
            details_text.insert("end", " STATUS ", "header")
            details_text.insert("end", "\n\n")
            details_text.insert("end", "✅ No suspicious features detected", "safe")

        # Apply current theme and font to all tags
        _update_detail_tags(current_size, mode, text_color, info_color, class_color, warn_color, safe_color)
        
        details_text.configure(state="disabled")

    def _update_detail_tags(size, mode, text_color, info_color, class_color, warn_color, safe_color):
        """Update all detail text tags with current theme and font size."""
        header_bg = "#3a3a3a" if mode == "dark" else "#E0E0E0"
        header_fg = "#ffffff" if mode == "dark" else "#1A1A1A"
        
        details_text.tag_config("header", 
                               background=header_bg,
                               foreground=header_fg,
                               font=("Consolas", size, "bold"))
        
        details_text.tag_config("info",
                               foreground=info_color,
                               font=("Consolas", size))
        
        details_text.tag_config("classification",
                               foreground=class_color,
                               font=("Consolas", size + 2, "bold"))
        
        details_text.tag_config("message",
                               foreground=text_color,
                               font=("Consolas", size))
        
        details_text.tag_config("warning",
                               foreground=warn_color,
                               font=("Consolas", size))
        
        details_text.tag_config("safe",
                               foreground=safe_color,
                               font=("Consolas", size, "bold"))

    def _refresh_current_details():
        """Refresh the currently displayed entry with new theme/font settings WITHOUT switching tabs."""
        if not _current_entry["entry"]:
            return
        
        entry = _current_entry["entry"]
        
        details_text.configure(state="normal")
        details_text.delete("1.0", "end")

        # Extract message data
        msg_full   = entry.get("message", "")
        warnings   = entry.get("warnings", [])
        label_text = entry.get("label", "Unknown")
        sender     = entry.get("sender", "Unknown")
        user_phone = entry.get("user_phone", "Unknown")
        device     = entry.get("device_name", "Unknown")
        sent_time  = entry.get("sent_time", "Unknown")

        # Get current settings
        from customtkinter import get_appearance_mode
        mode = get_appearance_mode().lower()
        current_size = int(font_size_var.get())
        
        # Classification scheme
        label_lower = str(label_text).lower()
        if label_lower == "smishing":
            icon = "🚨"
            class_color_dark = "#ff6b6b"
            class_color_light = "#d32f2f"
        elif label_lower == "spam":
            icon = "⚠️"
            class_color_dark = "#ffd93d"
            class_color_light = "#f57c00"
        elif label_lower == "legit":
            icon = "✅"
            class_color_dark = "#6bcf7f"
            class_color_light = "#388e3c"
        else:
            icon = "ℹ️"
            class_color_dark = "#00bfff"
            class_color_light = "#0288d1"
        
        # Theme colors
        if mode == "dark":
            text_color = "#EAEAEA"
            info_color = "#00bfff"
            class_color = class_color_dark
            warn_color = "#ff6b6b"
            safe_color = "#6bcf7f"
        else:
            text_color = "#1A1A1A"
            info_color = "#0288d1"
            class_color = class_color_light
            warn_color = "#d32f2f"
            safe_color = "#388e3c"

        # Build content with proper spacing
        details_text.insert("end", " MESSAGE DETAILS ", "header")
        details_text.insert("end", "\n")
        details_text.insert("end", f"Sender: {sender}\n", "info")
        details_text.insert("end", f"User Phone: {user_phone}\n", "info")
        details_text.insert("end", f"Device: {device}\n", "info")
        details_text.insert("end", f"Time: {sent_time}\n\n", "info")

        details_text.insert("end", " CLASSIFICATION ", "header")
        details_text.insert("end", "\n\n")
        details_text.insert("end", f"{icon} {label_text.capitalize()}\n\n", "classification")

        details_text.insert("end", " MESSAGE ", "header")
        details_text.insert("end", "\n\n")
        details_text.insert("end", f"{msg_full}\n\n", "message")

        if warnings:
            details_text.insert("end", " DETECTED FEATURES ", "header")
            details_text.insert("end", "\n\n")
            for w in warnings:
                details_text.insert("end", f"• {w}\n", "warning")
        else:
            details_text.insert("end", " STATUS ", "header")
            details_text.insert("end", "\n\n")
            details_text.insert("end", "✅ No suspicious features detected", "safe")

        # Apply current theme and font to all tags
        _update_detail_tags(current_size, mode, text_color, info_color, class_color, warn_color, safe_color)
        
        details_text.configure(state="disabled")

    def _make_row(parent: ctk.CTkScrollableFrame, entry: dict, index: int):
        """Create one selectable, double-clickable row with context menu."""
        label = (entry.get("label") or "Unknown").capitalize()
        msg   = entry.get("message") or "(no message)"
        color = _color_for_label(label.lower())

        preview = msg.split("\n", 1)[0].strip()
        if len(preview) > 90:
            preview = preview[:87] + "..."

        row = ctk.CTkFrame(parent, corner_radius=8, fg_color=("#E5E5E5", "#2A2A2A"))
        row.pack(fill="x", padx=5, pady=3)

        txt = ctk.CTkLabel(
            row,
            text=f"[{label}] {preview}",
            text_color=color,
            font=ctk.CTkFont("Consolas", _current_font_size["value"]),
            anchor="w", justify="left", padx=6,
        )
        txt.pack(fill="x", padx=8, pady=6)
        _log_label_widgets.append(txt)

        # selection
        row.bind("<Button-1>", lambda e: _highlight(row))
        txt.bind("<Button-1>", lambda e: _highlight(row))

        # double-click → open details
        def _dbl(_):
            try:
                _open_details(_log_entries[index])
            except Exception:
                _open_details(entry)
        row.bind("<Double-Button-1>", _dbl)
        txt.bind("<Double-Button-1>", _dbl)

        # context menu
        import tkinter as tk
        from tkinter import filedialog, messagebox
        menu = tk.Menu(row, tearoff=0)

        def _save():
            try:
                save_path = filedialog.asksaveasfilename(
                    defaultextension=".txt",
                    filetypes=[("Text Files", "*.txt")],
                    title="Save Log Entry"
                )
                if not save_path:
                    return
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(f"[{entry.get('label', label)}]\n\n")
                    f.write(entry.get("message", msg))
                    warns = entry.get("warnings", [])
                    if warns:
                        f.write("\n\nDetected Features:\n")
                        for w in warns:
                            f.write(f"• {w}\n")
                messagebox.showinfo("Saved", f"Log saved:\n{save_path}")
            except Exception as ex:
                messagebox.showerror("Save Error", str(ex))

        def _append():
            try:
                with open("combined_logs.txt", "a", encoding="utf-8") as f:
                    f.write(f"\n\n--- LOG ENTRY ---\n[{entry.get('label', label)}]\n\n")
                    f.write(entry.get("message", msg))
                    warns = entry.get("warnings", [])
                    if warns:
                        f.write("\n\nDetected Features:\n")
                        for w in warns:
                            f.write(f"• {w}\n")
                messagebox.showinfo("Appended", "Log entry added to combined_logs.txt")
            except Exception as ex:
                messagebox.showerror("Append Error", str(ex))

        def _delete():
            try:
                row.destroy()
                if entry in _log_entries:
                    _log_entries.remove(entry)
                if hasattr(builtins, "_shared_log_entries") and entry in builtins._shared_log_entries:
                    builtins._shared_log_entries.remove(entry)
                _render_list(filter_var.get())
                messagebox.showinfo("Deleted", "Log entry deleted.")
            except Exception as ex:
                messagebox.showerror("Delete Error", str(ex))

        menu.add_command(label="💾 Save Log (Single)", command=_save)
        menu.add_command(label="📚 Append to Combined Log", command=_append)
        menu.add_separator()
        menu.add_command(label="🗑 Delete Log", command=_delete)

        def _popup(ev):
            _highlight(row)
            try:
                menu.tk_popup(ev.x_root, ev.y_root)
            finally:
                menu.grab_release()

        row.bind("<Button-3>", _popup)
        txt.bind("<Button-3>", _popup)

        return row

    def _render_list(selected_value: str):
        """(Re)build visible rows according to the filter."""
        for child in log_box.winfo_children():
            child.destroy()
        _selected_frame_holder["ref"] = None
        _log_label_widgets.clear()

        for idx, entry in enumerate(_log_entries):
            lbl = (entry.get("label") or "Unknown").capitalize()
            if selected_value == "All" or selected_value.lower() == lbl.lower():
                _make_row(log_box, entry, idx)

    def apply_filter(selected_value):
        _render_list(selected_value)

    filter_menu.configure(command=apply_filter)

    def add_log_message(label, full_text, color, entry_data=None):
        """Append entry and re-render with current filter."""
        if entry_data is None:
            entry_data = {"label": label, "message": full_text, "warnings": []}
        else:
            entry_data.setdefault("label", label)
            entry_data.setdefault("message", full_text)

        _log_entries.append(entry_data)
        _render_list(filter_var.get())
        
        # FIXED: Auto-clear placeholder after prediction
        root.after(100, reset_placeholder)
        
        return True

    # ============================================================== #
    #                      LOG DETAILS TAB (ANATOMY)                 #
    # ============================================================== #
    log_frame = ctk.CTkFrame(log_tab, corner_radius=10)
    log_frame.pack(fill="both", expand=True, padx=10, pady=10)

    log_label = ctk.CTkLabel(
        log_frame, text="📖 Details",
        font=ctk.CTkFont(size=18, weight="bold"),
    )
    log_label.pack(anchor="w", padx=10, pady=(10, 5))

    import tkinter as tk

    details_text_frame = ctk.CTkFrame(log_frame, corner_radius=10)
    details_text_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    details_text = tk.Text(
        details_text_frame,
        height=520,
        wrap="word",
        font=("Consolas", last_font_size),
        bg="#1A1A1A",
        fg="#EAEAEA",
        insertbackground="#EAEAEA",
        relief="flat",
        padx=15,
        pady=15,
        borderwidth=0,
        cursor="arrow",
    )
    details_text.pack(fill="both", expand=True, padx=2, pady=2)
    details_text.configure(state="disabled")

    # ============================================================== #
    #                      SETTINGS TAB                              #
    # ============================================================== #
    settings_frame = ctk.CTkFrame(settings_tab, corner_radius=10)
    settings_frame.pack(fill="both", expand=True, padx=10, pady=10)

    center_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
    center_frame.place(relx=0.5, rely=0.5, anchor="center")

    ctk.CTkLabel(
        center_frame, text="⚙️ Settings",
        font=ctk.CTkFont(size=20, weight="bold"),
    ).pack(pady=(0, 15))

    # Theme selector
    theme_var = ctk.StringVar(value=last_theme)
    ctk.CTkLabel(center_frame, text="Theme Mode:",
                 font=ctk.CTkFont(size=13)).pack(pady=(5, 2))
    theme_menu = ctk.CTkOptionMenu(center_frame, variable=theme_var,
                                   values=["Light", "Dark", "System"], width=160)
    theme_menu.pack(pady=(0, 10))

    # Font size
    font_size_var = ctk.IntVar(value=last_font_size)
    ctk.CTkLabel(center_frame, text="Font Size:",
                 font=ctk.CTkFont(size=13)).pack(pady=(5, 2))
    font_slider = ctk.CTkSlider(center_frame, from_=8, to=30,
                                variable=font_size_var, number_of_steps=22, width=200)
    font_slider.pack(pady=(0, 15))

    # Auto Save
    auto_save_var = ctk.StringVar(value=auto_save)
    auto_save_switch = ctk.CTkSwitch(center_frame, text="Enable Auto Save",
                                     onvalue="on", offvalue="off",
                                     variable=auto_save_var)
    auto_save_switch.pack(pady=(5, 15))

    # ============================================================== #
    #                      STATUS BAR                                #
    # ============================================================== #
    status_bar = ctk.CTkLabel(root, text="Ready", anchor="w",
                              font=ctk.CTkFont(size=12), height=26)
    status_bar.pack(fill="x", side="bottom", padx=10, pady=(0, 5))

    # ================== Theme / Font Updaters ================== #
    def _apply_palette(mode: str):
        """Apply theme colors to all widgets."""
        palettes = {
            "dark":  {"bg": "#0E0E0E", "frame": "#1A1A1A", "inner": "#222222", "text": "#EAEAEA"},
            "light": {"bg": "#FAFAFA", "frame": "#EFEFEF", "inner": "#FFFFFF", "text": "#1A1A1A"},
        }
        C = palettes["dark" if mode == "dark" else "light"]

        root.configure(fg_color=C["bg"])
        status_bar.configure(fg_color=C["bg"], text_color=C["text"])

        try:
            tabs.configure(fg_color=C["frame"])
            if hasattr(tabs, "_border_frame"):
                tabs._border_frame.configure(fg_color=C["bg"])
            if hasattr(tabs, "_top_frame"):
                tabs._top_frame.configure(fg_color=C["frame"])
            if hasattr(tabs, "_segmented_button"):
                tabs._segmented_button.configure(
                    fg_color=C["frame"],
                    selected_color=("#1e88e5" if mode == "dark" else "#1976D2"),
                    selected_hover_color=("#2196f3" if mode == "dark" else "#1E88E5"),
                    unselected_color=("#3d3d3d" if mode == "dark" else "#D0D0D0"),
                    unselected_hover_color=("#4a4a4a" if mode == "dark" else "#C0C0C0"),
                    text_color=C["text"],
                )
        except Exception:
            pass

        for f in [detect_tab, log_tab, settings_tab, detect_container, left_frame, 
                  right_frame, log_frame, settings_frame, center_frame]:
            f.configure(fg_color=C["frame"])

        log_box.configure(fg_color=C["inner"])
        for attr in ("scrollable_frame", "_scrollable_frame", "_frame"):
            inner = getattr(log_box, attr, None)
            if inner:
                inner.configure(fg_color=C["inner"])

        input_box.configure(fg_color=C["inner"], text_color=C["text"])
        filter_menu.configure(fg_color=C["inner"], text_color=C["text"])
        
        # Update details text widget
        details_text.config(bg=C["inner"], fg=C["text"], insertbackground=C["text"])

        for lbl in [title_label, log_results_label, log_results_hint, log_label]:
            lbl.configure(text_color=C["text"])

        for blue_lbl in [ra_label, nc_label]:
            blue_lbl.configure(text_color="#00b0ff")

        root.update_idletasks()
        
        # Refresh anatomy content with new theme
        _refresh_current_details()

    def refresh_theme():
        """Switch theme and refresh UI."""
        choice = theme_var.get().lower()

        def apply_resolved():
            resolved = ctk.get_appearance_mode().lower()
            _apply_palette(resolved)
            settings["theme"] = theme_var.get()
            save_user_settings(settings)
            status_bar.configure(text=f"Theme: {theme_var.get()} ({resolved})")

        if choice == "system":
            ctk.set_appearance_mode("system")
            root.after(120, apply_resolved)
        else:
            ctk.set_appearance_mode(choice)
            _apply_palette(choice)
            settings["theme"] = theme_var.get()
            save_user_settings(settings)
            status_bar.configure(text=f"Theme: {theme_var.get()}")

    def update_font_size(_=None):
        """FIXED: Update font size immediately for all components."""
        new_size = int(font_size_var.get())
        
        # Update current font size tracker
        _current_font_size["value"] = new_size
        
        # Update input box
        input_box.configure(font=ctk.CTkFont("Consolas", new_size))
        
        # Update details text
        details_text.config(font=("Consolas", new_size))

        # FIXED: Update ALL existing log label widgets immediately
        for lbl in _log_label_widgets:
            try:
                if lbl.winfo_exists():
                    lbl.configure(font=ctk.CTkFont("Consolas", new_size))
            except Exception:
                pass

        # Save settings
        settings["font_size"] = new_size
        save_user_settings(settings)
        status_bar.configure(text=f"Font size: {new_size}")
        
        # Refresh anatomy content with new font size
        _refresh_current_details()

    def update_auto_save():
        settings["auto_save"] = auto_save_var.get()
        save_user_settings(settings)
        status_bar.configure(text=f"Auto Save: {auto_save_var.get().title()}")

    font_slider.configure(command=update_font_size)
    theme_menu.configure(command=lambda *_: refresh_theme())
    auto_save_switch.configure(command=update_auto_save)

    root.after(30, refresh_theme)

    return {
        "root": root,
        "tabs": tabs,
        "input_box": input_box,
        "predict_btn": predict_btn,
        "clear_btn": clear_btn,
        "load_image_btn": load_image_btn,
        "manage_server_btn": manage_server_btn,
        "log_box": log_box,
        "log_list": log_box,
        "filter_var": filter_var,
        "filter_menu": filter_menu,
        "details_text": details_text,
        "theme_var": theme_var,
        "font_size_var": font_size_var,
        "auto_save_var": auto_save_var,
        "status_bar": status_bar,
        "add_log_message": add_log_message,
        "log_entries": _log_entries,
        "reset_placeholder": reset_placeholder,
        "get_actual_text": get_actual_text,
    }

if __name__ == "__main__":
    ui = build_ui()
    ui["root"].mainloop()