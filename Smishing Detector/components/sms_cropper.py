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
        img_rgb = cv2.cvtColor(self.img_cv, cv2.COLOR_BGR2RGB)
        self.img_pil = Image.fromarray(img_rgb)

        # Resize if too big
        max_w, max_h = 800, 600
        self.scale = min(max_w / self.img_pil.width, max_h / self.img_pil.height, 1.0)
        new_size = (int(self.img_pil.width * self.scale), int(self.img_pil.height * self.scale))
        self.img_pil = self.img_pil.resize(new_size, Image.LANCZOS)

        self.top = tk.Toplevel(master)
        self.top.title("Select SMS Bubble")
        self.canvas = tk.Canvas(self.top, width=self.img_pil.width, height=self.img_pil.height, cursor="cross")
        self.canvas.pack()

        self.img_tk = ImageTk.PhotoImage(self.img_pil)
        self.canvas.create_image(0, 0, anchor="nw", image=self.img_tk)

        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)

    def on_mouse_down(self, event):
        self.start_x, self.start_y = event.x, event.y
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline="red", width=2)

    def on_mouse_drag(self, event):
        if self.rect_id:
            self.canvas.coords(self.rect_id, self.start_x, self.start_y, event.x, event.y)

    def on_mouse_up(self, event):
        end_x, end_y = event.x, event.y
        x1, x2 = sorted([self.start_x, end_x])
        y1, y2 = sorted([self.start_y, end_y])

        # Map back to original image coordinates
        x1 = int(x1 / self.scale)
        x2 = int(x2 / self.scale)
        y1 = int(y1 / self.scale)
        y2 = int(y2 / self.scale)

        crop = self.img_cv[y1:y2, x1:x2]
        if crop.size == 0:
            return

        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        text = pytesseract.image_to_string(gray)

        if text.strip():
            self.callback(text.strip())
        else:
            self.callback("[OCR failed: no text detected]")

        self.top.destroy()
