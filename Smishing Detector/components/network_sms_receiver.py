import threading
import socket
import sys
import traceback
import json
from typing import Optional, Dict
from datetime import datetime
from pathlib import Path
import qrcode
from PIL import Image, ImageTk
import tkinter as tk

# --- TCP Configuration ---
HOST = ''          # Listen on all interfaces
PORT = 65432       # Fixed port
BUFFER_SIZE = 1024


class NetworkSMSReceiver:
    """
    Manages TCP server creation, QR display, client connection, and data reception.
    """

    def __init__(self, root_instance, sms_callback, log_callback):
        self.root = root_instance
        self.sms_callback = sms_callback
        self.log_callback = log_callback

        self.server_socket = None
        self.client_socket = None
        self.conn_address = None
        self.thread = None

        self.is_running = False
        self.ui_callback = None  # For UI connection status

    # ---------- UI callback ----------
    def set_ui_update_callback(self, callback):
        self.ui_callback = callback

    def _update_ui_status_safe(self, status):
        if self.ui_callback:
            self.root.after(0, self.ui_callback, status)

    # ---------- Start / Stop Server ----------
    def start_server(self, port=PORT):
        """Starts the TCP server thread and QR display."""
        if self.is_running:
            self.log_callback("Server already running.", "Info")
            return

        self.is_running = True
        self.thread = threading.Thread(
            target=self._run_server_thread, args=(port,), daemon=True, name="TCP-Server-Thread"
        )
        self.thread.start()

    def stop_server(self):
        """Stops the server cleanly."""
        if not self.is_running:
            return

        self.is_running = False

        # Close client connection
        if self.client_socket:
            try:
                self.client_socket.close()
            except Exception:
                pass
            self.client_socket = None
            self.conn_address = None

        # Close listening socket
        if self.server_socket:
            try:
                temp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                temp_sock.connect(('127.0.0.1', self.server_socket.getsockname()[1]))
                temp_sock.close()
                self.server_socket.close()
            except Exception:
                pass
            self.server_socket = None

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1)
        self.thread = None

        self.log_callback("Network server stopped.", "Info")
        self._update_ui_status_safe("Stopped")

    # ---------- Helper: Get local IP ----------
    @staticmethod
    def _get_local_ip():
        """Detects current LAN IP correctly (works on Wi-Fi/hotspot)."""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = "127.0.0.1"
        finally:
            s.close()
        return ip

    # ---------- Helper: Create QR popup ----------
    def _show_qr_popup(self, payload: str):
        """Generates and displays a QR with tcp://IP:PORT."""
        try:
            img = qrcode.make(payload)
            qr_path = Path.cwd() / "connection_qr.png"
            img.save(qr_path)

            qr_win = tk.Toplevel(self.root)
            qr_win.title("📡 Scan to Connect")

            qr_image = ImageTk.PhotoImage(img)
            lbl_img = tk.Label(qr_win, image=qr_image)
            lbl_img.image = qr_image
            lbl_img.pack(padx=8, pady=8)

            tk.Label(qr_win, text=payload, font=("Arial", 12, "bold")).pack(pady=(0, 10))
            tk.Label(qr_win, text="Scan this QR with your phone app").pack()

            qr_win.lift()
            qr_win.attributes("-topmost", True)
            qr_win.after(100, lambda: qr_win.attributes("-topmost", False))

            self.log_callback(f"📱 QR shown: {payload}", "Info")
        except Exception as e:
            self.log_callback(f"QR generation failed: {e}", "Error")

    # ---------- SMS JSON parser ----------
    @staticmethod
    def extract_sms_data(raw_request_data: bytes) -> Optional[Dict[str, str]]:
        SEPARATOR = b'\r\n\r\n'
        try:
            sep_index = raw_request_data.index(SEPARATOR)
            body_raw = raw_request_data[sep_index + len(SEPARATOR):]
        except ValueError:
            print("Parser Error: Could not find end of HTTP headers.")
            return None

        try:
            json_string = body_raw.decode('utf-8').strip()
            sms_data = json.loads(json_string)
        except Exception as e:
            print(f"Parser Error: {e}")
            return None

        sms_message = sms_data.get('message', '--- MESSAGE MISSING ---')
        sender = sms_data.get('sender', '--- SENDER MISSING ---')
        user = sms_data.get('phoneNumber','--- USER MISSING ---')
        device_name = sms_data.get('deviceName','--- DEVICE MISSING ---')
        timestamp_ms = sms_data.get('timestamp')
        formatted_time = '--- TIME MISSING ---'
        if isinstance(timestamp_ms, (int, float)):
            dt = datetime.fromtimestamp(timestamp_ms / 1000)
            formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')

        return {"message": sms_message,"phoneNumber" : user,"deviceName" : device_name, "sender": sender, "time": formatted_time}

    # ---------- Main server thread ----------
    def _run_server_thread(self, port):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((HOST, port))
            self.server_socket.listen(1)

            host_ip = self._get_local_ip()
            server_port = self.server_socket.getsockname()[1]
            payload = f"tcp://{host_ip}:{server_port}"

            # Show QR code popup
            self.root.after(0, self._show_qr_popup, payload)

            self.log_callback(f"Server started on {host_ip}:{server_port}. Waiting for connection...", "Info")
            self._update_ui_status_safe(f"Listening on {host_ip}:{server_port}")

            while self.is_running:
                self.client_socket, self.conn_address = self.server_socket.accept()
                if not self.is_running:
                    break

                self._update_ui_status_safe(f"Connected: {self.conn_address[0]}")
                self.log_callback(f"📶 Client connected: {self.conn_address[0]}", "Info")
                self._receive_data_loop()

        except Exception as e:
            if self.is_running:
                tb = traceback.format_exc()
                self.root.after(0, self.log_callback, f"Server thread error: {e}\n{tb}", "Error")
        finally:
            self.is_running = False
            self.client_socket = None
            self.conn_address = None
            self._update_ui_status_safe("Stopped")

    # ---------- Continuous data reception ----------
    def _receive_data_loop(self):
        while self.is_running and self.client_socket:
            try:
                data = self.client_socket.recv(BUFFER_SIZE)
                if not data:
                    self.log_callback(f"Client {self.conn_address[0]} disconnected.", "Info")
                    break
                message = NetworkSMSReceiver.extract_sms_data(data)
                if message:
                    self.root.after(0, self.log_callback, f"Received {len(message)} chars.", "Info")
                    self.root.after(0, self.sms_callback, message)

            except ConnectionResetError:
                self.log_callback(f"Client {self.conn_address[0]} forcibly closed connection.", "Error")
                break
            except Exception as e:
                self.log_callback(f"Data reception error: {e}", "Error")
                break

        if self.client_socket:
            try:
                self.client_socket.close()
            except Exception:
                pass
        self.client_socket = None
        self.conn_address = None
        self._update_ui_status_safe("Listening")
