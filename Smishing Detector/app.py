import tkinter as tk
import os
import sys
import joblib
from tkinter import messagebox, filedialog
from components.preprocess import clean_text
from PIL import Image, ImageTk
from components.sms_cropper import SMSCropper
from components.feature_extraction import detect_urls, detect_emails, detect_phone_numbers, detect_domains
from components.intro_screen import IntroScreen
import math
from functools import lru_cache
from components.user_verification import UserVerification

# --- IMPORTS FOR NETWORK INTEGRATION (TCP/IP) ---
import threading 
import socket # Needed for IP lookup
# Import the network server module and the default port
from components.network_sms_receiver import NetworkSMSReceiver, PORT 

# Resource path helper for PyInstaller
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Paths
MODEL_PATH = resource_path("sms_model.joblib")
VECTORIZER_PATH = resource_path('tfidf_vectorizer.joblib')

if not os.path.exists(MODEL_PATH):
    print(f"WARNING: Model file '{MODEL_PATH}' not found. Prediction disabled.")

try:
    if os.path.exists(MODEL_PATH):
        MODEL = joblib.load(MODEL_PATH)
        VECTORIZER = joblib.load(VECTORIZER_PATH)
except Exception as e:
    print(f"WARNING: Failed to load model bundle:\n{e}")

message_store = []
filtered_indices = []
network_manager = None # Global instance of the NetworkSMSReceiver
network_btn = None     # Reference to the Network button

# Global state for Log Details panel
current_detailed_index = -1
details_visible = [False]

# Panel size parameters
target_width_open = 500
target_width_closed = 70  # small width to show pointer nicely
base_window_width = 700
animation_steps = 25
animation_delay = 10

# ----------------- Functions -----------------
def clear_input():
    input_box.delete("1.0", tk.END)

def add_log(message, label, warnings_list=None):
    """
    Add a log entry. warnings_list (list of str) is optional and stored with message.
    """
    if label is None:
        label = "Info"

    label_lower = label.lower()
    
    # Determine color for Listbox display
    if label_lower == "smishing":
        color = "red"
    elif label_lower == "spam":
        color = "yellow"
    elif label_lower == "error":
        color = "red"
    elif label_lower == "info":
        color = "white"
    else: # Legit
        color = "green"

    snippet_content = message if message is not None else "System Message"
    snippet = snippet_content[:50] + ("..." if len(snippet_content) > 50 else "")
    display_text = f"[{label}] {snippet if message is not None else snippet_content}"

    # Log entry is inserted regardless of filtering status
    log_list.insert(tk.END, display_text)
    log_list.itemconfig(tk.END, {'fg': color})
    log_list.see(tk.END)

    # Store message. Store None if it's an Info or Error system message.
    message_to_store = message if label_lower not in ["info", "error"] else None
    message_store.append({"message": message_to_store, "label": label, "warnings": warnings_list or []})
    filter_logs()

def show_error_popup(parent, title, message):
    """
    Displays an error message in a modal popup window.
    """
    # Create a new top-level window
    err_win = tk.Toplevel(parent)
    err_win.title(title)
    err_win.configure(bg="#252526")
    err_win.geometry("400x200")
    err_win.resizable(False, False)
    err_win.grab_set()  # Makes it modal (blocks interaction with parent)

    # Error title label
    tk.Label(
        err_win,
        text="⚠️ " + title,
        fg="red",
        bg="#252526",
        font=("Arial", 14, "bold")
    ).pack(pady=(15, 5))

    # Error message text box
    msg_box = tk.Text(
        err_win,
        wrap="word",
        height=6,
        width=45,
        bg="#2d2d2d",
        fg="white",
        font=("Consolas", 11),
        relief="flat"
    )
    msg_box.insert("1.0", message)
    msg_box.config(state="disabled")  # Prevent editing
    msg_box.pack(padx=10, pady=10)

    # OK button to close the popup
    tk.Button(
        err_win,
        text="OK",
        command=err_win.destroy,
        bg="#ff4444",
        fg="white",
        font=("Arial", 12, "bold"),
        relief="flat"
    ).pack(pady=(0, 10))
    
# --- Reusable Prediction Core Logic ---
def process_message_for_prediction(text, source="Manual Input"):
    """
    Core logic for cleaning, predicting, and logging a message.
    """
    if MODEL is None or VECTORIZER is None:
        show_error_popup(
            parent=root,
            title="Model Not Loaded",
            message=f"Received message from {source}, but the prediction model is not loaded. Please check your model file."
        )
        return

    # Extract simple features (regex)
    urls = detect_urls(text)
    emails = detect_emails(text)
    phones = detect_phone_numbers(text)
    domains = detect_domains(text)

    text_clean = clean_text(text)
    labels = ['ham','smishing','spam']
    try:
        X = VECTORIZER.transform([text_clean])
        label = MODEL.predict(X)[0]
        label = labels[label]
        label_display = "Legit" if str(label).lower() == "ham" else str(label).capitalize()
        
        if label_display != "Legit":
            # Only apply user verification for manual input
            if source == "Manual Input":
                verifier = UserVerification(root, text, label_display)
                label_display = verifier.ask_user() 
        
        # Build warnings list
        warnings_list = []
        if urls:
            warnings_list.append("URLs: " + ", ".join(urls))
        if emails:
            warnings_list.append("Emails: " + ", ".join(emails))
        if phones:
            warnings_list.append("Phones: " + ", ".join(phones))
        if domains:
            warnings_list.append("Domains: " + ", ".join(domains))

        add_log(f"{text}", label_display, warnings_list)
        
    except Exception as e:
        # Show error in messagebox
        show_error_popup(
            parent=root,
            title="Prediction Fail",
            message=f"Prediction failed for message from {source}: {e}"
        )
        # Log the failure as an 'Error' system message
        add_log(f"Prediction failed for message from {source}: {e}", "Error") 

def predict_action():
    """Handles prediction for manual text input."""
    text = input_box.get("1.0", tk.END).strip()
    if not text or text == "Type here...":
        messagebox.showwarning("Warning", "Enter a message first")
        return

    if MODEL is None or VECTORIZER is None:
        show_error_popup(
            parent=root,
            title="Error",
            message=f"Model not loaded properly."
        )
        return

    process_message_for_prediction(text, source="Manual Input")
    clear_input()

# --- Network Handlers ---
def on_sms_received_callback(message):
    """
    Called by the Network thread (via root.after) to pass message to the main thread.
    """
    process_message_for_prediction(message, source="Network")

def _toggle_server_wrapper():
    """Wrapper function called by the Toplevel window's button to start/stop the server."""
    global network_manager
    if not network_manager: return
    
    if network_manager.is_running:
        network_manager.stop_server()
    else:
        network_manager.start_server()


class NetworkConnectWindow(tk.Toplevel):
    """
    A separate Toplevel window for initializing and managing the Network TCP connection.
    """
    def __init__(self, master, manager, main_log_callback, toggle_server_callback):
        super().__init__(master)
        self.manager = manager
        self.main_log_callback = main_log_callback
        self.toggle_server_callback = toggle_server_callback
        self.current_status = "Stopped"
        self.title("🌐 Network SMS Receiver (TCP)") 
        self.geometry("450x200") 
        self.configure(bg="#252526")
        self.transient(master) 
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self._create_widgets()
        
        # Pass the update function back to the Network manager
        if hasattr(manager, 'set_ui_update_callback'):
            manager.set_ui_update_callback(self.update_status)
        
        # Get local IP/Port for display
        try:
            # Get the host machine's IP address
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            self.host_ip = s.getsockname()[0]
            s.close()
        except socket.gaierror:
            self.host_ip = "127.0.0.1"
        except OSError:
            # Fallback if no network connection is available
            self.host_ip = "127.0.0.1 (No network)"
            
        self.port = PORT
        
        self.ip_port_label.config(text=f"Host IP: {self.host_ip} | Port: {self.port}")
        self.update_status("Stopped")

    def _create_widgets(self):
        main_frame = tk.Frame(self, bg="#252526")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        tk.Label(main_frame, text="TCP Server Control", fg="#00ccff", bg="#252526", font=("Arial", 16, "bold")).pack(pady=10)

        # IP and Port Display
        self.ip_port_label = tk.Label(main_frame, text="Host IP: N/A | Port: N/A", 
                                     fg="white", bg="#252526", font=("Consolas", 12))
        self.ip_port_label.pack(pady=(0, 10))

        # Status Label
        self.status_label = tk.Label(main_frame, text="Status: Stopped", 
                                     fg="yellow", bg="#252526", font=("Arial", 14, "bold"))
        self.status_label.pack(pady=(0, 15))

        # Start/Stop Button
        self.toggle_btn = tk.Button(main_frame, text="Start Server", command=self._toggle_server_wrapper, 
                                     bg="#28a745", fg="white", font=("Arial", 12, "bold"), relief="flat")
        self.toggle_btn.pack(pady=10)
        
    def update_status(self, new_status):
        """
        Updates the status label and the button text/color based on the server's state.
        """
        self.current_status = new_status
        
        # Check if the server is in an active/listening state
        if "Listening" in new_status or "Connected" in new_status:
            # Server is running, user must be able to stop it.
            status_fg = "green" if "Connected" in new_status else "yellow"
            
            self.status_label.config(text=f"Status: {new_status}", fg=status_fg)
            self.toggle_btn.config(text="Stop Server", bg="#dc3545") # Red for Stop

        elif "Stopped" in new_status or "Error" in new_status:
            # Server is stopped or failed to start, user must be able to start it.
            status_fg = "red" if "Error" in new_status else "yellow"

            self.status_label.config(text=f"Status: {new_status}", fg=status_fg)
            self.toggle_btn.config(text="Start Server", bg="#28a745") # Green for Start
            
    def _toggle_server_wrapper(self):
        """Wrapper for button command to call the manager toggle and update local log."""
        self.toggle_server_callback() # Calls _toggle_server_wrapper in the main module

    def update_log(self, message):
        """
        Allows the manager or main app to write status. Since the visual log 
        was removed, this function now primarily serves as a placeholder.
        """
        # We only need to check if the window exists, but don't perform any visual updates.
        if not self.winfo_exists():
            return
        
    def on_close(self):
        """When the window is closed, stop the server and re-enable the main app's button."""
        if self.manager and self.manager.is_running:
            self.manager.stop_server() 
             
        global network_btn
        if network_btn:
            network_btn.config(state=tk.NORMAL, text="📶 Connect Network")
        self.destroy()

def bluetooth_connect_action():
    """Function handler for the Network button."""
    global network_manager, network_btn
    
    # 1. Initialize the manager (if not done)
    if network_manager is None:
        try:
            network_manager = NetworkSMSReceiver(
                root, 
                on_sms_received_callback, # Function to receive SMS data
                add_log # Function to receive system messages
            )
        except Exception as e:
            # Catch general setup failure (e.g., if socket module is somehow missing)
            show_error_popup(
                parent=root,
                title="Setup Error",
                message=f"Network Initialization Failed: {e}."
            )
            class DummyManager:
                is_running = False
            network_manager = DummyManager() 
            return 
    
    # 2. Launch the new Toplevel window
    NetworkConnectWindow(root, network_manager, add_log, _toggle_server_wrapper) 
    
    # Disable the main button until the window is closed
    if network_btn:
        network_btn.config(state=tk.DISABLED, text="Manager Open")

# --- Cleanup on window close ---
def on_closing():
    """Stops the Network server thread and prompts user to save logs before closing."""
    global network_manager, message_store
    
    if message_store:
        # Prompt user to save logs
        result = messagebox.askyesnocancel(
            "Save Logs?", 
            "You have unsaved log results. Do you want to save them before exiting?"
        )
        
        if result is True:
            # Proceed with saving
            _save_logs_prompt()
        elif result is None:
            # User clicked cancel, abort exit process
            return

    # Stop the network manager cleanly
    if network_manager and isinstance(network_manager, NetworkSMSReceiver):
        network_manager.stop_server()
        
    root.destroy()

def _save_logs_prompt():
    """Helper function to execute the file dialog save process."""
    if not message_store:
        return
        
    file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files","*.txt")])
    
    if file_path:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                for data in message_store:
                    f.write(f"[{data['label']}] {data['message'] if data['message'] else 'System message'}\n")
                    if data.get("warnings"):
                        for w in data["warnings"]:
                            f.write(f"    {w}\n")
            messagebox.showinfo("Saved", f"Logs saved to {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save logs:\n{e}")

# --- GUI Helper Functions (Rest of your existing code) ---

# Elastic easing function (fixed)
def ease_out_elastic(t):
    c4 = (2 * math.pi) / 3  # use math.pi
    if t == 0:
        return 0
    if t == 1:
        return 1
    return pow(2, -10 * t) * math.sin((t * 10 - 0.75) * c4) + 1

def toggle_details(event=None):
    if details_visible[0]:
        # Closing animation
        start_width = right_frame.winfo_width()

        def step_close(i=0):
            t = i / animation_steps
            new_width = int(start_width * (1 - ease_out_elastic(t)))
            main_pane.paneconfig(right_frame, width=max(new_width, target_width_closed))
            root.update_idletasks()
            root.geometry(f"{base_window_width + max(new_width, target_width_closed)}x600")
            if i < animation_steps:
                root.after(animation_delay, step_close, i + 1)
            else:
                details_text.pack_forget()
                details_toggle.config(text="📖 Log Details ▶")
                details_visible[0] = False
                global current_detailed_index
                current_detailed_index = -1

        step_close()
    else:
        # Opening animation
        details_text.pack(fill="both", expand=True, pady=5)
        start_width = right_frame.winfo_width()

        def step_open(i=0):
            t = i / animation_steps
            new_width = int(target_width_open * ease_out_elastic(t))
            main_pane.paneconfig(right_frame, width=new_width)
            root.update_idletasks()
            root.geometry(f"{base_window_width + new_width}x600")
            if i < animation_steps:
                root.after(animation_delay, step_open, i + 1)
            else:
                details_toggle.config(text="📖 Log Details ▼")
                details_visible[0] = True

        step_open()

def on_log_double_click(event):
    global current_detailed_index
    selection = log_list.curselection()
    if not selection:
        return
    index = selection[0]
    original_index = filtered_indices[index]
    
    data = message_store[original_index]
    message_content = data.get("message")

    # --- NEW LOGIC: Load content into Input Box ---
    if message_content:
        # 1. Clear input box
        input_box.delete("1.0", tk.END)
        # 2. Insert message content
        input_box.insert(tk.END, message_content)
        # 3. Ensure input box is active and showing white text
        input_box.config(fg="white") 
        # 4. Give focus (optional but helpful)
        input_box.focus_set()


    # If the same item is clicked AND the details panel is open, close it.
    if current_detailed_index == original_index and details_visible[0]:
        toggle_details()
        return

    details_text.config(state="normal")
    details_text.delete("1.0", tk.END)

    # Clear previous tags
    for tag in details_text.tag_names():
        details_text.tag_delete(tag)

    # Define new tags for readability
    details_text.tag_config("header", font=("Consolas", 14, "bold"), foreground="#ff4800") 
    details_text.tag_config("prediction_smishing", font=("Consolas", 13, "bold"), foreground="red")
    details_text.tag_config("prediction_spam", font=("Consolas", 13, "bold"), foreground="orange")
    details_text.tag_config("prediction_legit", font=("Consolas", 13, "bold"), foreground="green")
    details_text.tag_config("message", font=("Consolas", 12), foreground="white")
    details_text.tag_config("warning_url", font=("Consolas", 12, "italic"), foreground="red")
    details_text.tag_config("warning_email", font=("Consolas", 12, "italic"), foreground="red")
    details_text.tag_config("warning_phone", font=("Consolas", 12, "italic"), foreground="red")
    details_text.tag_config("warning_domain", font=("Consolas", 12, "italic"), foreground="red")
    details_text.tag_config("warning_other", font=("Consolas", 12, "italic"), foreground="#ff80ff") 

    if data["message"] is None:
        details_text.insert("end", "ℹ️ System Message\n", "header")
        details_text.insert("end", f"[{data['label']}] {log_list.get(selection[0])[len(data['label'])+3:].strip()}", "message")
    else:
        # Prediction label with color
        label_lower = data["label"].lower()
        if label_lower == "smishing":
            pred_tag = "prediction_smishing"
        elif label_lower == "spam":
            pred_tag = "prediction_spam"
        elif label_lower == "legit":
            pred_tag = "prediction_legit"
        else:
            pred_tag = "message"

        details_text.insert("end", "📌 Prediction:\n", "header")
        details_text.insert("end", f"{data['label']}\n\n", pred_tag)

        # REMOVED redundancy: The main message is now in the Input Box for editing.
        # details_text.insert("end", "💬 Original Message:\n", "header")
        # details_text.insert("end", f"{data['message']}\n\n", "message") 

        # Warnings with proper indentation and color
        if data.get("warnings"):
            details_text.insert("end", "⚠️ Detections:\n", "header")
            for w in data["warnings"]:
                if w.startswith("URLs:"):
                    details_text.insert("end", f"   - {w}\n", "warning_url")
                elif w.startswith("Emails:"):
                    details_text.insert("end", f"   - {w}\n", "warning_email")
                elif w.startswith("Phones:"):
                    details_text.insert("end", f"   - {w}\n", "warning_phone")
                elif w.startswith("Domains:"):
                    details_text.insert("end", f"   - {w}\n", "warning_domain")
                else:
                    details_text.insert("end", f"   - {w}\n", "warning_other")
        else:
            details_text.insert("end", "✅ No suspicious features detected.", "prediction_legit")
    
    
    details_text.config(state="disabled")
    details_text.see("1.0")

    if details_visible[0] == False:
        toggle_details()
    
    current_detailed_index = original_index


def on_log_right_click(event):
    selection = log_list.curselection()
    if not selection: return
    index = selection[0]
    original_index = filtered_indices[index]

    menu = tk.Menu(root, tearoff=0)
    menu.add_command(label="Copy Message", command=lambda: copy_message(original_index))
    menu.add_command(label="Delete Log", command=lambda: delete_log(original_index))
    menu.post(event.x_root, event.y_root)

def copy_message(index):
    data = message_store[index]
    if data["message"]:
        root.clipboard_clear()
        root.clipboard_append(data["message"])
        messagebox.showinfo("Copied", "Message copied to clipboard")

def delete_log(index):
    global current_detailed_index
    del message_store[index]
    
    # If the currently viewed detail was deleted, close the panel
    if current_detailed_index == index:
        current_detailed_index = -1
        if details_visible[0]:
            toggle_details()
        details_text.config(state="normal")
        details_text.delete("1.0", tk.END)
        details_text.config(state="disabled")
    
    filter_logs()
    

def filter_logs(*args):
    global filtered_indices
    selected = filter_var.get().lower()
    log_list.delete(0, tk.END)
    filtered_indices = []

    # Labels that are NOT prediction results (system messages)
    system_labels = ["info", "error"]

    for i, data in enumerate(message_store):
        label_lower = data["label"].lower()
        
        show_entry = False

        if label_lower in system_labels:
            # System messages (Info/Error) are ONLY shown if they are explicitly selected in the filter dropdown
            if label_lower == selected:
                show_entry = True
        else:
            # Prediction results (Legit, Spam, Smishing) are shown if 'All' is selected OR if their label is selected
            if selected == "all" or label_lower == selected:
                show_entry = True

        if show_entry:
            message_content = data["message"]
            snippet = message_content[:50] + ("..." if message_content and len(message_content) > 50 else "") if message_content else ""
            display_text = f"[{data['label']}] {snippet if snippet else 'System Message'}"
            log_list.insert(tk.END, display_text)

            color = "white" if label_lower=="info" else "red" if label_lower in ["smishing", "error"] else "yellow" if label_lower=="spam" else "green"
            log_list.itemconfig(tk.END, {'fg': color})
            filtered_indices.append(i)

# --- Removed Save Logs and Load Logs functions ---
# The save logic is now integrated into on_closing

def load_image_to_input():
    file_path = filedialog.askopenfilename(filetypes=[("Image files","*.png;*.jpg;*.jpeg;*.bmp")])
    if not file_path:
        return

    def insert_text(text):
        input_box.delete("1.0", tk.END)
        input_box.insert(tk.END, text)

    SMSCropper(root, file_path, insert_text)

# ----------------- GUI -----------------
root = tk.Tk()
root.title("🕵🏽 Smishing/Spam/Legit Detector")
root.configure(bg="#1e1e1e")
root.geometry("700x600") 

# ----------------- Resizable PanedWindow -----------------
main_pane = tk.PanedWindow(root, orient=tk.HORIZONTAL, sashrelief="raised", sashwidth=6, bg="#1e1e1e")
main_pane.pack(fill="both", expand=True, padx=10, pady=10)

# LEFT FRAME (Input, Controls, Log List)
left_frame = tk.Frame(main_pane, bg="#252526", width=500)
main_pane.add(left_frame)

# Top section: Input Box and Controls
top_controls_frame = tk.Frame(left_frame, bg="#252526")
top_controls_frame.pack(fill="x", pady=(0, 5))

# --- LEFT: INPUT AREA ---
input_area_frame = tk.Frame(top_controls_frame, bg="#252526")
input_area_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

tk.Label(input_area_frame, text="💬 SMS Box", bg="#252526", fg="white",
          font=("Arial", 16, "bold")).pack(anchor="w", pady=(0,5))

# INPUT BOX (RESIZED TO HEIGHT 6)
input_box = tk.Text(input_area_frame, height=6, width=45, wrap="word",
                    bg="#2d2d2d", fg="white", insertbackground="white",
                    font=("Consolas", 13))
input_box.pack(pady=5, fill="both", expand=True)

# Set initial placeholder text
placeholder_text = "Type here..."
input_box.insert("1.0", placeholder_text)

# Define placeholder behavior
def on_focus_in(event):
    if input_box.get("1.0", "end-1c") == placeholder_text:
        input_box.delete("1.0", "end")
        input_box.config(fg="white")

def on_focus_out(event):
    if input_box.get("1.0", "end-1c").strip() == "":
        input_box.insert("1.0", placeholder_text)
        input_box.config(fg="white")

# Bind events
input_box.bind("<FocusIn>", on_focus_in)
input_box.bind("<FocusOut>", on_focus_out)


# --- RIGHT: VERTICAL CONTROL PANEL (MODERNIZED) ---
control_panel_frame = tk.Frame(top_controls_frame, bg="#1e1e1e", bd=2, relief="flat", padx=10, pady=10)
control_panel_frame.pack(side="right", fill="y", padx=5, pady=5)


def create_modern_button(parent, text, cmd, icon, color, row, column):
    """Creates a unified, large button for modern design."""
    btn = tk.Button(parent, text=f"{icon} {text}", command=cmd, bg=color, fg="#1e1e1e", # Text color changed to black for contrast
                    font=("Arial", 10, "bold"), relief="flat", 
                    padx=10, pady=8, width=20, # Set a uniform width for a clean grid
                    activebackground=color, activeforeground="#252526") 
    btn.grid(row=row, column=column, padx=5, pady=5, sticky="ew")

    # Capture reference for the network button
    if "Network" in text:
        global network_btn
        network_btn = btn
    
    return btn

# Use a clean grid layout inside the control panel
control_panel_frame.grid_columnconfigure(0, weight=1)

# 1. RUN ANALYSIS
# ANALYSIS buttons placed vertically for prominence

tk.Label(control_panel_frame, text="1. RUN ANALYSIS", bg="#1e1e1e", fg="#00ccff", 
         font=("Arial", 10, "bold")).grid(row=0, column=0, padx=5, pady=(5, 0), sticky="w")

create_modern_button(control_panel_frame, "Predict SMS", predict_action, "▶", "#28a745", 1, 0)
create_modern_button(control_panel_frame, "Clear Input", clear_input, "🗑️", "#dc3545", 2, 0)
create_modern_button(control_panel_frame, "Load Image/OCR", load_image_to_input, "🖼️", "#17a2b8", 3, 0)


# 2. NETWORK CONTROL
tk.Label(control_panel_frame, text="2. NETWORK CONTROL", bg="#1e1e1e", fg="#00ccff", 
         font=("Arial", 10, "bold")).grid(row=4, column=0, padx=5, pady=(10, 0), sticky="w")

create_modern_button(control_panel_frame, "Manage Server", bluetooth_connect_action, "🌐", "#6610f2", 5, 0)


# 3. APP CONTROL (Simplified)
tk.Label(control_panel_frame, text="3. APP CONTROL", bg="#1e1e1e", fg="#00ccff", 
         font=("Arial", 10, "bold")).grid(row=6, column=0, padx=5, pady=(10, 0), sticky="w")

# The only button here is Exit, which triggers the save prompt in on_closing
create_modern_button(control_panel_frame, "Exit App", on_closing, "❌", "#6c6c6c", 7, 0)


# --- BOTTOM SECTION: LOGS ---
log_section_frame = tk.Frame(left_frame, bg="#252526")
log_section_frame.pack(fill="both", expand=True, pady=(10, 0))

# FILTER DROPDOWN
filter_var = tk.StringVar()
filter_var.set("All")
filter_options = ["All", "Smishing", "Spam", "Legit", "Info", "Error"]
filter_menu = tk.OptionMenu(log_section_frame, filter_var, *filter_options, command=filter_logs)
filter_menu.config(font=("Consolas", 12), bg="#2d2d2d", fg="white", relief="flat", width=10)
filter_menu.pack(side="left", pady=5)

tk.Label(log_section_frame, text="Log Results (Right-Click for options):", bg="#252526", fg="white",
          font=("Arial", 12)).pack(side="left", padx=10, pady=5)


# LOG LIST
log_list = tk.Listbox(left_frame, height=12, width=45,
                      bg="#121212", fg="white", font=("Consolas", 13, "bold"),
                      selectbackground="#444", activestyle="none")
log_list.pack(pady=5, fill="both", expand=True)
log_list.bind("<Double-1>", on_log_double_click)
log_list.bind("<Button-3>", on_log_right_click)

main_pane.add(left_frame, minsize=400) # Ensure left panel has space


# ----------------- RIGHT FRAME (Details) -----------------
right_frame = tk.Frame(main_pane, bg="#1e1e1e")
main_pane.add(right_frame, minsize=50) # minimum size when collapsed

# Styled toggle label (pointer)
details_toggle = tk.Label(
    right_frame,
    text="📖 Log Details ▶",
    bg="#444444",
    fg="white",
    font=("Arial", 16, "bold"),
    cursor="hand2",
    padx=10,
    pady=5,
    bd=2,
    relief="ridge"
)
details_toggle.pack(anchor="nw", pady=10, padx=5)

# Details text (start hidden)
details_text = tk.Text(
    right_frame,
    height=30,
    width=45,
    wrap="word",
    bg="#2d2d2d",
    fg="white",
    font=("Consolas", 14, "bold"),
    bd=2,
    relief="sunken"
)
# do NOT pack it yet; it will be packed when opening

details_toggle.bind("<Button-1>", toggle_details)

# Initially collapse the right frame (show only pointer)
main_pane.paneconfig(right_frame, width=target_width_closed)
root.geometry(f"{base_window_width + target_width_closed}x600")


# Bind the cleanup function to the window close event
root.protocol("WM_DELETE_WINDOW", on_closing)

# Show intro screen (smooth fade + progress)
intro = IntroScreen(root, duration=3000)

root.mainloop()
