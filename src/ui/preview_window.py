import customtkinter as ctk
import cv2
import os
from PIL import Image, ImageTk
from tkinter import messagebox
from send2trash import send2trash
from ..utils.logger import logger
from ..utils.config import config

class Colors:
    SUCCESS = "#2CC985"
    ERROR = "#FF4B4B"
    WARNING = "#FFB302"
    INFO = "#3B8ED0"

class VideoPreviewWindow(ctk.CTkToplevel):
    def __init__(self, original_path, converted_path, parent=None):
        super().__init__(parent)
        self.title("Conversion Preview")
        
        # Set full screen
        self.attributes('-fullscreen', True)
        
        self.original_path = original_path
        self.converted_path = converted_path
        self.is_playing = False
        
        # Validation
        if not os.path.exists(original_path) or not os.path.exists(converted_path):
            messagebox.showerror("Error", "One of the files is missing.")
            self.destroy()
            return

        try:
            self.cap_orig = cv2.VideoCapture(self.original_path)
            self.cap_conv = cv2.VideoCapture(self.converted_path)
        except Exception as e:
            logger.error(f"Failed to open video files: {e}")
            messagebox.showerror("Error", "Could not open video files.")
            self.destroy()
            return

        # Get video properties
        self.total_frames = int(self.cap_orig.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap_orig.get(cv2.CAP_PROP_FPS)
        if self.fps <= 0: self.fps = 30
        self.delay = int(1000 / self.fps)
        
        self._create_ui()
        self.update_frames()
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.bind("<Escape>", lambda e: self.on_close())

    def _create_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        
        # Video Frames
        self.frame_orig = ctk.CTkLabel(self, text="Original", fg_color="black")
        self.frame_orig.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        self.frame_conv = ctk.CTkLabel(self, text="Converted", fg_color="black")
        self.frame_conv.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        # Controls
        self.controls_frame = ctk.CTkFrame(self)
        self.controls_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=10)
        
        self.btn_play = ctk.CTkButton(self.controls_frame, text="Play", command=self.toggle_play, width=80)
        self.btn_play.pack(side="left", padx=10)
        
        self.slider = ctk.CTkSlider(self.controls_frame, from_=0, to=self.total_frames, command=self.on_seek)
        self.slider.pack(side="left", fill="x", expand=True, padx=10)
        self.slider.set(0)
        
        self.btn_delete_orig = ctk.CTkButton(self.controls_frame, text="Delete Original", command=self.delete_original, fg_color=Colors.ERROR, hover_color="#D63D3D")
        self.btn_delete_orig.pack(side="right", padx=10)

        self.btn_delete_conv = ctk.CTkButton(self.controls_frame, text="Delete Converted", command=self.delete_converted, fg_color=Colors.WARNING, hover_color="#D99B00")
        self.btn_delete_conv.pack(side="right", padx=10)

        self.btn_close = ctk.CTkButton(self.controls_frame, text="Close", command=self.on_close, width=80, fg_color="#555555", hover_color="#444444")
        self.btn_close.pack(side="right", padx=10)

    def toggle_play(self):
        self.is_playing = not self.is_playing
        self.btn_play.configure(text="Stop" if self.is_playing else "Play")
        if self.is_playing:
            self.play_loop()

    def play_loop(self):
        if not self.is_playing: return
        
        current_frame = int(self.cap_orig.get(cv2.CAP_PROP_POS_FRAMES))
        if current_frame >= self.total_frames:
            self.is_playing = False
            self.btn_play.configure(text="Play")
            return
            
        self.update_frames()
        self.slider.set(current_frame)
        self.after(self.delay, self.play_loop)

    def on_seek(self, value):
        frame_no = int(value)
        self.cap_orig.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
        self.cap_conv.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
        self.update_frames()

    def update_frames(self):
        ret1, frame1 = self.cap_orig.read()
        ret2, frame2 = self.cap_conv.read()
        
        if ret1:
            self._display_frame(frame1, self.frame_orig)
        if ret2:
            self._display_frame(frame2, self.frame_conv)

    def _display_frame(self, frame, label_widget):
        # Resize to fit label using aspect ratio
        h, w = frame.shape[:2]
        target_h = label_widget.winfo_height()
        if target_h < 100: target_h = 400
        
        # Keep aspect ratio
        ratio = target_h / h
        target_w = int(w * ratio)
        
        # Ensure we don't exceed container width too much (simple check)
        max_w = self.winfo_width() // 2 - 20
        if max_w > 100 and target_w > max_w:
             ratio = max_w / w
             target_w = max_w
             target_h = int(h * ratio)

        frame = cv2.resize(frame, (target_w, target_h))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame)
        imgtk = ImageTk.PhotoImage(image=img)
        label_widget.configure(image=imgtk, text="")
        label_widget.image = imgtk

    def delete_original(self):
        if messagebox.askyesno("Confirm Delete", "Send ORIGINAL file to Recycle Bin?"):
            try:
                self.cap_orig.release()
                send2trash(self.original_path)
                logger.info(f"Sent to trash: {self.original_path}")
                messagebox.showinfo("Deleted", "Original file sent to Recycle Bin.")
                self.btn_delete_orig.configure(state="disabled", text="Orig Deleted")
            except Exception as e:
                logger.error(f"Error deleting file: {e}")
                messagebox.showerror("Error", f"Could not delete: {e}")

    def delete_converted(self):
        if messagebox.askyesno("Confirm Delete", "Send CONVERTED file to Recycle Bin?"):
            try:
                self.cap_conv.release()
                send2trash(self.converted_path)
                logger.info(f"Sent to trash: {self.converted_path}")
                messagebox.showinfo("Deleted", "Converted file sent to Recycle Bin.")
                self.btn_delete_conv.configure(state="disabled", text="Conv Deleted")
            except Exception as e:
                logger.error(f"Error deleting file: {e}")
                messagebox.showerror("Error", f"Could not delete: {e}")

    def on_close(self):
        self.is_playing = False
        if hasattr(self, 'cap_orig'): self.cap_orig.release()
        if hasattr(self, 'cap_conv'): self.cap_conv.release()
        self.destroy()
