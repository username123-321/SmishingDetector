import cv2
import pytesseract
from PIL import Image, ImageTk
import tkinter as tk

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

class SMSCropper:
    def __init__(self, master, file_path, callback):
        self.master = master
        self.file_path = file_path
        self.callback = callback
        self.start_x = None
        self.start_y = None
        self.rect_id = None

        # Load image
        self.img_cv = cv2.imread(file_path)
        if self.img_cv is None:
            raise ValueError(f"Failed to load image: {file_path}")
            
        img_rgb = cv2.cvtColor(self.img_cv, cv2.COLOR_BGR2RGB)
        self.img_pil = Image.fromarray(img_rgb)

        # Resize if too big
        max_w, max_h = 800, 600
        self.scale = min(max_w / self.img_pil.width, max_h / self.img_pil.height, 1.0)
        new_size = (int(self.img_pil.width * self.scale), int(self.img_pil.height * self.scale))
        self.img_pil = self.img_pil.resize(new_size, Image.LANCZOS)

        # Create Toplevel window (standard tkinter, not CTk)
        self.top = tk.Toplevel(master)
        self.top.title("Select SMS Bubble")
        self.top.resizable(False, False)
        
        # Create frame for better organization
        frame = tk.Frame(self.top, bg="#2b2b2b")
        frame.pack(fill="both", expand=True)
        
        # Instruction label
        instruction = tk.Label(
            frame,
            text="📱 Click and drag to select the SMS message area",
            font=("Arial", 11, "bold"),
            bg="#2b2b2b",
            fg="white",
            pady=10
        )
        instruction.pack()

        # Canvas for image display
        self.canvas = tk.Canvas(
            frame,
            width=self.img_pil.width,
            height=self.img_pil.height,
            cursor="cross",
            bg="#1a1a1a",
            highlightthickness=0
        )
        self.canvas.pack(padx=10, pady=(0, 10))

        # Convert PIL image to PhotoImage (this is correct for tk.Canvas)
        self.img_tk = ImageTk.PhotoImage(self.img_pil)
        self.canvas.create_image(0, 0, anchor="nw", image=self.img_tk)

        # Bind mouse events
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        
        # Bind Escape key to cancel
        self.top.bind("<Escape>", lambda e: self.top.destroy())
        
        # Center window on screen
        self.top.update_idletasks()
        self.top.geometry(f"+{(self.top.winfo_screenwidth() - self.top.winfo_width()) // 2}+"
                         f"{(self.top.winfo_screenheight() - self.top.winfo_height()) // 2}")

    def on_mouse_down(self, event):
        """Handle mouse button press."""
        self.start_x, self.start_y = event.x, event.y
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(
            self.start_x, self.start_y,
            self.start_x, self.start_y,
            outline="#00ff00",
            width=3
        )

    def on_mouse_drag(self, event):
        """Handle mouse drag motion."""
        if self.rect_id:
            self.canvas.coords(self.rect_id, self.start_x, self.start_y, event.x, event.y)

    def on_mouse_up(self, event):
        """Handle mouse button release and perform OCR."""
        end_x, end_y = event.x, event.y
        x1, x2 = sorted([self.start_x, end_x])
        y1, y2 = sorted([self.start_y, end_y])

        # Validate selection
        if abs(x2 - x1) < 10 or abs(y2 - y1) < 10:
            self.canvas.delete(self.rect_id)
            return

        # Map back to original image coordinates
        x1 = int(x1 / self.scale)
        x2 = int(x2 / self.scale)
        y1 = int(y1 / self.scale)
        y2 = int(y2 / self.scale)

        # Crop and process
        crop = self.img_cv[y1:y2, x1:x2]
        if crop.size == 0:
            self.callback("[OCR failed: invalid selection]")
            self.top.destroy()
            return

        try:
            # Preprocess for better OCR
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            
            # Apply thresholding for better text extraction
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Perform OCR
            text = pytesseract.image_to_string(thresh, config='--psm 6')

            if text.strip():
                self.callback(text.strip())
            else:
                self.callback("[OCR failed: no text detected]")
        except Exception as e:
            self.callback(f"[OCR error: {str(e)}]")

        self.top.destroy()