import threading
import socket
import sys
import time
import traceback
import random

# --- TCP Configuration ---
# Use an empty string for the hostname to listen on all available interfaces (0.0.0.0)
HOST = '' 
PORT = 65432       # Port to listen on (non-privileged ports are > 1023)
BUFFER_SIZE = 1024 # Size of buffer for receiving data

class NetworkSMSReceiver:
    """
    Manages TCP server creation, client connection, and synchronous data 
    reception in a dedicated thread.
    """

    def __init__(self, root_instance, sms_callback, log_callback):
        """
        :param root_instance: Tk root (used for root.after safe callbacks).
        :param sms_callback: function to call on received SMS: sms_callback(message_str).
        :param log_callback: function to call for log messages: log_callback(text, label).
        """
        self.root = root_instance
        self.sms_callback = sms_callback
        self.log_callback = log_callback

        self.server_socket = None
        self.client_socket = None
        self.conn_address = None
        self.thread = None
        
        self.is_running = False
        self.ui_callback = None # UI callback to update the connection status/IP

    # ---------- UI callback setters ----------
    def set_ui_update_callback(self, callback):
        """Sets the function from the UI window used to update the status."""
        self.ui_callback = callback
        
    def _update_ui_status_safe(self, status):
        """Sends connection status back to the UI thread."""
        if self.ui_callback:
            # Safely execute the UI update callback in the main thread
            self.root.after(0, self.ui_callback, status)

    # ---------- Server Control ----------
    def start_server(self, port=PORT):
        """Starts the main server thread."""
        if self.is_running:
            self.log_callback("Server already running.", "Info")
            return

        self.is_running = True
        self.thread = threading.Thread(target=self._run_server_thread, args=(port,), daemon=True, name="TCP-Server-Thread")
        self.thread.start()

    def stop_server(self):
        """Stops the server, closes connections, and terminates the thread cleanly."""
        if not self.is_running:
            return

        self.is_running = False
        
        # Close client connection first
        if self.client_socket:
            try:
                self.client_socket.close()
            except Exception:
                pass
            self.client_socket = None
            self.conn_address = None
            
        # Close the server listening socket
        if self.server_socket:
            try:
                # Unblock socket.accept() by connecting a temporary socket to itself
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


    # ---------- Background Server Thread ----------
    def _run_server_thread(self, port):
        """The main execution loop for the TCP server thread."""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Allows the server to reuse the same port immediately after shutdown
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
            
            self.server_socket.bind((HOST, port))
            self.server_socket.listen(1) # Allow only one simultaneous connection (the phone app)
            
            # Determine actual IP and port used for display
            host_ip = socket.gethostbyname(socket.gethostname())
            server_port = self.server_socket.getsockname()[1]
            
            self.log_callback(f"Server started on {host_ip}:{server_port}. Waiting for connection...", "Info")
            self._update_ui_status_safe(f"Listening on {host_ip}:{server_port}")
            
            while self.is_running:
                self.client_socket, self.conn_address = self.server_socket.accept() # Blocking call
                
                if not self.is_running: break # Check if stop was called while waiting for accept
                
                self._update_ui_status_safe(f"Connected to {self.conn_address[0]}")
                
                # Start data reception loop
                self._receive_data_loop()
                
        except Exception as e:
            if self.is_running: # Only log error if not explicitly shutting down
                tb = traceback.format_exc()
                self.root.after(0, self.log_callback, f"Server thread error: {e}\n{tb}", "Error")
            
        finally:
            self.is_running = False
            self.client_socket = None
            self.conn_address = None
            self._update_ui_status_safe("Stopped")
            
    # ---------- Data Reception Loop ----------
    def _receive_data_loop(self):
        """Handles continuous data reception from the connected client."""
        while self.is_running and self.client_socket:
            try:
                data = self.client_socket.recv(BUFFER_SIZE)
                if not data:
                    # Client disconnected gracefully
                    self.log_callback(f"Client {self.conn_address[0]} disconnected.", "Info")
                    break
                
                # Decode the received data
                message = data.decode('utf-8').strip()
                
                # --- Simulating SMS Data Transfer ---
                # Since the phone app sends a string, we treat it as the SMS content.
                if message:
                    self.root.after(0, self.log_callback, f"Received {len(message)} chars from client.", "Info")
                    # Send the received message to the main application for prediction
                    self.root.after(0, self.sms_callback, message)
                    
            except ConnectionResetError:
                self.log_callback(f"Client {self.conn_address[0]} forcibly closed connection.", "Error")
                break
            except Exception as e:
                self.log_callback(f"Data reception error: {e}", "Error")
                break

        # Clean up client socket state after exit
        if self.client_socket:
            try: self.client_socket.close()
            except Exception: pass
        self.client_socket = None
        self.conn_address = None
        self._update_ui_status_safe("Listening") # Go back to listening if server is still running
