import os
import sys
import joblib
import builtins
from tkinter import messagebox, filedialog
from components.preprocess import clean_text
from components.sms_cropper import SMSCropper
from components.feature_extraction import detect_urls, detect_emails, detect_phone_numbers, detect_domains
from components.intro_screen import IntroScreen
from components.user_verification import UserVerification
from components.network_sms_receiver import NetworkSMSReceiver, PORT
import socket
import customtkinter as ctk
import qrcode
from PIL import Image, ImageTk
import io

# Import the UI builder from design.py
from design import build_ui, load_user_settings, save_user_settings

# Resource path helper for PyInstaller
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Paths
MODEL_PATH = resource_path("model/sms_model.joblib")
VECTORIZER_PATH = resource_path('model/tfidf_vectorizer.joblib')

# Load model
MODEL = None
VECTORIZER = None

if os.path.exists(MODEL_PATH):
    try:
        MODEL = joblib.load(MODEL_PATH)
        VECTORIZER = joblib.load(VECTORIZER_PATH)
    except Exception as e:
        print(f"WARNING: Failed to load model bundle:\n{e}")
else:
    print(f"WARNING: Model file '{MODEL_PATH}' not found. Prediction disabled.")

# Global state
network_manager = None
details_dict = {}

# ----------------- Helper Functions -----------------
def add_detail(detail_name, detail):
    global details_dict
    details_dict[detail_name] = detail

def take_details(user, device_name, sent_time):
    add_detail("user_phone", user)
    add_detail("device_name", device_name)
    add_detail("sent_time", sent_time)

def show_error_popup(parent, title, message):
    """Displays an error message in a modal popup window."""
    err_win = ctk.CTkToplevel(parent)
    err_win.title(title)
    err_win.geometry("400x200")
    err_win.resizable(False, False)
    err_win.grab_set()

    ctk.CTkLabel(
        err_win,
        text="⚠️ " + title,
        text_color="red",
        font=ctk.CTkFont(size=14, weight="bold")
    ).pack(pady=(15, 5))

    msg_box = ctk.CTkTextbox(err_win, height=80, width=350)
    msg_box.insert("1.0", message)
    msg_box.configure(state="disabled")
    msg_box.pack(padx=10, pady=10)

    ctk.CTkButton(
        err_win,
        text="OK",
        command=err_win.destroy,
        fg_color="#ff4444",
        hover_color="#cc0000"
    ).pack(pady=(0, 10))

# ----------------- Core Prediction Logic -----------------
def process_message_for_prediction(sms, sender="Unknown", ui_components=None):
    """Core logic for cleaning, predicting, and logging a message."""
    if isinstance(sms, dict):
        sender = sms.get('sender', 'Unknown')
        text = sms['message']
    else:
        text = sms

    if MODEL is None or VECTORIZER is None:
        show_error_popup(
            parent=ui_components['root'],
            title="Model Not Loaded",
            message=f"Received message from {sender}, but the prediction model is not loaded."
        )
        return

    # Extract features
    urls = detect_urls(text)
    emails = detect_emails(text)
    phones = detect_phone_numbers(text)
    domains = detect_domains(text)

    text_clean = clean_text(text)
    labels = ['ham', 'smishing', 'spam']
    
    try:
        X = VECTORIZER.transform([text_clean])
        label = MODEL.predict(X)[0]
        label = labels[label]
        label_display = "Legit" if str(label).lower() == "ham" else str(label).capitalize()
        
        # User verification for non-legit messages
        if label_display != "Legit":
            verifier = UserVerification(ui_components['root'], text, label_display)
            label_display = verifier.ask_user(sender)
        
        # Build warnings list
        warnings_list = []
        if urls:
            warnings_list.append("URLs detected: " + ", ".join(urls))
        if emails:
            warnings_list.append("Emails detected: " + ", ".join(emails))
        if phones:
            warnings_list.append("Phone numbers detected: " + ", ".join(phones))
        if domains:
            warnings_list.append("Suspicious domains: " + ", ".join(domains))

        # Determine color based on label
        if label_display.lower() == "smishing":
            color = "#ff4d4d"
        elif label_display.lower() == "spam":
            color = "#ffcc00"
        else:  # Legit
            color = "#4caf50"

        # Add to log using design.py's add_log_message
        entry_data = {
            "message": text,
            "label": label_display,
            "warnings": warnings_list,
            "sender": sender,
            "user_phone": details_dict.get("user_phone", "Unknown"),
            "device_name": details_dict.get("device_name", "Unknown"),
            "sent_time": details_dict.get("sent_time", "Unknown")
        }
        
        ui_components['add_log_message'](label_display, text, color, entry_data)
        ui_components['status_bar'].configure(text=f"✅ Analyzed: {label_display}")
        
    except Exception as e:
        show_error_popup(
            parent=ui_components['root'],
            title="Prediction Failed",
            message=f"Prediction failed for message from {sender}: {e}"
        )

# ----------------- UI Action Handlers -----------------
def predict_action(ui_components):
    """Handles prediction for manual text input."""
    text = ui_components['input_box'].get("1.0", "end-1c").strip()
    
    # Check for placeholder text
    PLACEHOLDER_TEXT = "Type here..."
    if not text or text == PLACEHOLDER_TEXT:
        messagebox.showwarning("Warning", "Enter a message first")
        return

    if MODEL is None or VECTORIZER is None:
        show_error_popup(
            parent=ui_components['root'],
            title="Error",
            message="Model not loaded properly."
        )
        return

    process_message_for_prediction(text, sender="Manual Input", ui_components=ui_components)
    
    # Clear input and restore placeholder
    ui_components['input_box'].delete("1.0", "end")
    ui_components['input_box'].insert("1.0", PLACEHOLDER_TEXT)

def clear_input_action(ui_components):
    """Clear the input box."""
    PLACEHOLDER_TEXT = "Type here..."
    ui_components['input_box'].delete("1.0", "end")
    ui_components['input_box'].insert("1.0", PLACEHOLDER_TEXT)

def load_image_action(ui_components):
    """Load image and extract text via OCR."""
    file_path = filedialog.askopenfilename(
        filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.bmp")]
    )
    if not file_path:
        return

    def insert_text(text):
        ui_components['input_box'].delete("1.0", "end")
        ui_components['input_box'].insert("end", text)

    SMSCropper(ui_components['root'], file_path, insert_text)

# ----------------- Network Management -----------------
def on_sms_received_callback(sms_message, ui_components):
    """Callback when SMS is received via network."""
    message = sms_message['message']
    sender = sms_message['sender']
    user = sms_message['phoneNumber']
    device_name = sms_message['deviceName']
    sent_time = sms_message['time']
    
    take_details(user, device_name, sent_time)
    process_message_for_prediction(message, sender=sender, ui_components=ui_components)

class NetworkConnectWindow(ctk.CTkToplevel):
    """Network connection management window with QR code."""
    def __init__(self, master, manager, ui_components):
        super().__init__(master)
        self.manager = manager
        self.ui_components = ui_components
        self.current_status = "Stopped"
        
        self.title("🌐 Network SMS Receiver")
        self.geometry("450x550")
        self.resizable(False, False)
        self.transient(master)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Get local IP
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            self.host_ip = s.getsockname()[0]
            s.close()
        except:
            self.host_ip = "0.0.0.0"
        
        self.port = PORT
        self.connection_url = f"http://{self.host_ip}:{self.port}"
        
        self._create_widgets()
        
        if hasattr(manager, 'set_ui_update_callback'):
            manager.set_ui_update_callback(self.update_status)
        
        self.update_status("Stopped")

    def _create_widgets(self):
        # Title
        ctk.CTkLabel(
            self,
            text="🌐 TCP Server Control",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(pady=15)

        # Status Label
        self.status_label = ctk.CTkLabel(
            self,
            text="Status: Stopped",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="yellow"
        )
        self.status_label.pack(pady=10)

        # Start/Stop Button
        self.toggle_btn = ctk.CTkButton(
            self,
            text="Start Server",
            command=self._toggle_server,
            fg_color="#28a745",
            hover_color="#218838",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            width=200
        )
        self.toggle_btn.pack(pady=15)

        # QR Code Section
        qr_frame = ctk.CTkFrame(self, corner_radius=10)
        qr_frame.pack(pady=10, padx=20, fill="both", expand=True)

        ctk.CTkLabel(
            qr_frame,
            text="📱 Scan to Connect",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=10)

        # QR Code Display
        self.qr_label = ctk.CTkLabel(qr_frame, text="")
        self.qr_label.pack(pady=10)

        # Generate and display QR code
        self._generate_qr_code()

        # Connection info
        self.info_label = ctk.CTkLabel(
            qr_frame,
            text=f"Connection URL:\n{self.connection_url}",
            font=ctk.CTkFont(size=11),
            justify="center"
        )
        self.info_label.pack(pady=10)

    def _generate_qr_code(self):
        """Generate QR code for connection URL."""
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(self.connection_url)
            qr.make(fit=True)

            qr_image = qr.make_image(fill_color="black", back_color="white")
            qr_image = qr_image.resize((250, 250))

            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(qr_image)
            self.qr_label.configure(image=photo, text="")
            self.qr_label.image = photo  # Keep reference

        except Exception as e:
            self.qr_label.configure(text=f"QR Code Error:\n{str(e)}")

    def update_status(self, new_status):
        """Update status label and button based on server state."""
        self.current_status = new_status
        
        if "Listening" in new_status or "Connected" in new_status:
            status_color = "green" if "Connected" in new_status else "yellow"
            self.status_label.configure(text=f"Status: {new_status}", text_color=status_color)
            self.toggle_btn.configure(text="Stop Server", fg_color="#dc3545", hover_color="#c82333")
        else:
            status_color = "red" if "Error" in new_status else "yellow"
            self.status_label.configure(text=f"Status: {new_status}", text_color=status_color)
            self.toggle_btn.configure(text="Start Server", fg_color="#28a745", hover_color="#218838")

    def _toggle_server(self):
        """Toggle server state."""
        if not self.manager:
            return
        
        if self.manager.is_running:
            self.manager.stop_server()
        else:
            self.manager.start_server()

    def on_close(self):
        """Handle window close."""
        if self.manager and self.manager.is_running:
            self.manager.stop_server()
        
        self.ui_components['manage_server_btn'].configure(state="normal")
        self.destroy()

def manage_server_action(ui_components):
    """Open network management window."""
    global network_manager
    
    # Check if window is already open
    if hasattr(manage_server_action, 'window') and manage_server_action.window and manage_server_action.window.winfo_exists():
        manage_server_action.window.lift()  # Bring existing window to front
        return
    
    if network_manager is None:
        try:
            # Create callback wrapper that includes ui_components
            def wrapped_callback(sms_msg):
                on_sms_received_callback(sms_msg, ui_components)
            
            def wrapped_log(msg, label):
                # Use status bar for network logs
                ui_components['status_bar'].configure(text=f"{label}: {msg}")
            
            network_manager = NetworkSMSReceiver(
                ui_components['root'],
                wrapped_callback,
                wrapped_log
            )
        except Exception as e:
            show_error_popup(
                parent=ui_components['root'],
                title="Setup Error",
                message=f"Network Initialization Failed: {e}"
            )
            return
    
    manage_server_action.window = NetworkConnectWindow(ui_components['root'], network_manager, ui_components)
    ui_components['manage_server_btn'].configure(state="disabled")

# ----------------- Application Cleanup -----------------
def on_closing(ui_components):
    """Handle application closing with conditional save prompt."""
    global network_manager
    
    # Get current settings
    settings = load_user_settings()
    auto_save = settings.get("auto_save", "off")
    
    # Check if there are logs to save
    has_logs = hasattr(builtins, '_shared_log_entries') and builtins._shared_log_entries
    
    if has_logs:
        if auto_save == "on":
            # Auto-save is enabled - directly ask for file location
            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text Files", "*.txt")],
                title="Auto-Save: Choose location and filename",
                initialfile="sms_logs.txt"
            )
            
            if file_path:  # User selected a location
                save_logs_to_file(file_path, ui_components)
            else:  # User cancelled
                result = messagebox.askyesno(
                    "Exit Without Saving?",
                    "You cancelled the auto-save. Do you still want to exit without saving?"
                )
                if not result:
                    return  # Don't exit
        else:
            # Auto-save is disabled - inform and ask
            result = messagebox.askyesnocancel(
                "Save Predictions?",
                "Auto-save is disabled. Your predictions will not be saved.\n\n"
                "Do you want to save them before exiting?\n\n"
                "• Yes: Save predictions\n"
                "• No: Exit without saving\n"
                "• Cancel: Return to application"
            )
            
            if result is True:  # Yes - save
                file_path = filedialog.asksaveasfilename(
                    defaultextension=".txt",
                    filetypes=[("Text Files", "*.txt")],
                    title="Save Predictions",
                    initialfile="sms_logs.txt"
                )
                if file_path:
                    save_logs_to_file(file_path, ui_components)
            elif result is None:  # Cancel - don't exit
                return
            # If No, continue to exit
    
    # Stop network manager
    if network_manager and isinstance(network_manager, NetworkSMSReceiver):
        network_manager.stop_server()
    
    ui_components['root'].destroy()

def save_logs_to_file(file_path, ui_components):
    """Save all logs to the specified file."""
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write("SMS DETECTOR - COMPLETE LOG EXPORT\n")
            f.write("=" * 80 + "\n\n")
            
            for i, entry in enumerate(builtins._shared_log_entries, 1):
                f.write(f"\n{'=' * 80}\n")
                f.write(f"LOG ENTRY #{i}\n")
                f.write(f"{'=' * 80}\n\n")
                f.write(f"Classification: [{entry.get('label', 'Unknown')}]\n")
                f.write(f"Sender: {entry.get('sender', 'Unknown')}\n")
                f.write(f"User Phone: {entry.get('user_phone', 'Unknown')}\n")
                f.write(f"Device: {entry.get('device_name', 'Unknown')}\n")
                f.write(f"Time: {entry.get('sent_time', 'Unknown')}\n\n")
                f.write("Message:\n")
                f.write("-" * 80 + "\n")
                f.write(entry.get('message', 'N/A') + "\n")
                f.write("-" * 80 + "\n\n")
                
                warnings = entry.get('warnings', [])
                if warnings:
                    f.write("Detected Features:\n")
                    for w in warnings:
                        f.write(f"  • {w}\n")
                else:
                    f.write("✅ No suspicious features detected\n")
                
                f.write("\n")
        
        messagebox.showinfo("Saved", f"Logs saved successfully to:\n{file_path}")
        ui_components['status_bar'].configure(text=f"✅ Logs saved to {os.path.basename(file_path)}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save logs:\n{e}")

# ----------------- Main Application -----------------
def main():
    # Build UI using design.py
    ui_components = build_ui()
    
    # Wire up button actions to app.py functions
    ui_components['predict_btn'].configure(command=lambda: predict_action(ui_components))
    ui_components['clear_btn'].configure(command=lambda: clear_input_action(ui_components))
    ui_components['load_image_btn'].configure(command=lambda: load_image_action(ui_components))
    ui_components['manage_server_btn'].configure(command=lambda: manage_server_action(ui_components))
    
    # Set up window close protocol
    ui_components['root'].protocol("WM_DELETE_WINDOW", lambda: on_closing(ui_components))
    
    # Show intro screen
    intro = IntroScreen(ui_components['root'], duration=3000)
    
    # Start the application
    ui_components['root'].mainloop()

if __name__ == "__main__":
    main()