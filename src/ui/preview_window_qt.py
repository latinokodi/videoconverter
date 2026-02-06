import cv2
import os
from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QSlider, QHBoxLayout, QVBoxLayout, 
    QMessageBox, QFrame, QSizePolicy, QApplication
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QImage, QPixmap, QIcon
from send2trash import send2trash
from ..utils.logger import logger

class ResizableLabel(QLabel):
    """QLabel that doesn't force the layout to expand based on its pixmap content."""
    def sizeHint(self):
        return QSize(1, 1) # Minimal size hint
    
    def minimumSizeHint(self):
        return QSize(1, 1)

class VideoPreviewWindow(QWidget):
    closed = pyqtSignal()

    def __init__(self, original_path, converted_path):
        super().__init__()
        self.setWindowTitle("Conversion Preview")
        self.showFullScreen()
        
        self.original_path = original_path
        self.converted_path = converted_path
        self.is_playing = False
        
        # Style
        self.setStyleSheet("background-color: #121212; color: white;")

        # Validate
        if not os.path.exists(original_path) or not os.path.exists(converted_path):
            QMessageBox.critical(self, "Error", "One of the files is missing.")
            self.close()
            return

        try:
            self.cap_orig = cv2.VideoCapture(self.original_path)
            self.cap_conv = cv2.VideoCapture(self.converted_path)
        except Exception as e:
            logger.error(f"Failed to open video files: {e}")
            QMessageBox.critical(self, "Error", "Could not open video files.")
            self.close()
            return

        # Properties
        self.total_frames = int(self.cap_orig.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap_orig.get(cv2.CAP_PROP_FPS)
        if self.fps <= 0: self.fps = 30
        self.delay = int(1000 / self.fps)

        self._create_ui()
        self.update_frames()
        
        # Timer for playback
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.play_loop)
        
        # Timer for seek debouncing
        self.seek_timer = QTimer(self)
        self.seek_timer.setSingleShot(True)
        self.seek_timer.timeout.connect(self._execute_pending_seek)
        self.pending_seek_val = -1

    def _create_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Screens Layout
        screens_layout = QHBoxLayout()
        
        # Original Frame
        self.lbl_orig = ResizableLabel("Original")
        self.lbl_orig.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_orig.setStyleSheet("border: 1px solid #333; background-color: black;")
        self.lbl_orig.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Converted Frame
        self.lbl_conv = ResizableLabel("Converted")
        self.lbl_conv.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_conv.setStyleSheet("border: 1px solid #333; background-color: black;")
        self.lbl_conv.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        screens_layout.addWidget(self.lbl_orig)
        screens_layout.addWidget(self.lbl_conv)
        main_layout.addLayout(screens_layout, stretch=1)
        
        # Controls
        controls_frame = QFrame()
        controls_layout = QHBoxLayout(controls_frame)
        controls_layout.setContentsMargins(0, 10, 0, 0)
        
        self.btn_play = QPushButton("Play")
        self.btn_play.setFixedWidth(80)
        self.btn_play.clicked.connect(self.toggle_play)
        
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, self.total_frames)
        self.slider.sliderMoved.connect(self.on_seek_request)
        self.slider.sliderPressed.connect(self.pause_slider)
        self.slider.sliderReleased.connect(self.resume_slider)
        
        self.btn_del_orig = QPushButton("Delete Original")
        self.btn_del_orig.setStyleSheet("background-color: #d32f2f;")
        self.btn_del_orig.clicked.connect(self.delete_original)
        
        self.btn_del_conv = QPushButton("Delete Converted")
        self.btn_del_conv.setStyleSheet("background-color: #f57c00;")
        self.btn_del_conv.clicked.connect(self.delete_converted)
        
        self.btn_close = QPushButton("Close")
        self.btn_close.setFixedWidth(80)
        self.btn_close.clicked.connect(self.close)
        
        controls_layout.addWidget(self.btn_play)
        controls_layout.addWidget(self.slider)
        controls_layout.addWidget(self.btn_del_orig)
        controls_layout.addWidget(self.btn_del_conv)
        controls_layout.addWidget(self.btn_close)
        
        main_layout.addWidget(controls_frame)
        
        # Key bindings
        # QWidget doesn't have bind like Tk, override keyPressEvent
        
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event.key() == Qt.Key.Key_Space:
            self.toggle_play()
        super().keyPressEvent(event)

    def toggle_play(self):
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.btn_play.setText("Stop")
            self.timer.start(self.delay)
        else:
            self.btn_play.setText("Play")
            self.timer.stop()

    def pause_slider(self):
        self.was_playing = self.is_playing
        if self.is_playing:
            self.toggle_play() # Stop

    def resume_slider(self):
        # Ensure final seek happens
        if self.pending_seek_val != -1:
            self._execute_pending_seek()
            
        if hasattr(self, 'was_playing') and self.was_playing:
            self.toggle_play() # Resume

    def play_loop(self):
        current_frame = int(self.cap_orig.get(cv2.CAP_PROP_POS_FRAMES))
        if current_frame >= self.total_frames:
            self.toggle_play()
            return
            
        self.update_frames()
        self.slider.blockSignals(True) # Avoid seeking while playing
        self.slider.setValue(current_frame)
        self.slider.blockSignals(False)

    def on_seek_request(self, value):
        """Called when slider is moved. Debounce the actual seek."""
        self.pending_seek_val = value
        # Restart timer (debounce)
        self.seek_timer.start(100) # 100ms debounce

    def _execute_pending_seek(self):
        if self.pending_seek_val != -1:
            value = self.pending_seek_val
            self.cap_orig.set(cv2.CAP_PROP_POS_FRAMES, value)
            self.cap_conv.set(cv2.CAP_PROP_POS_FRAMES, value)
            self.update_frames()
            self.pending_seek_val = -1

    def update_frames(self):
        if hasattr(self, 'cap_orig') and self.cap_orig.isOpened():
            ret1, frame1 = self.cap_orig.read()
            if ret1:
                self._display_frame(frame1, self.lbl_orig)
                
        if hasattr(self, 'cap_conv') and self.cap_conv.isOpened():
            ret2, frame2 = self.cap_conv.read()
            if ret2:
                self._display_frame(frame2, self.lbl_conv)

    def _display_frame(self, frame, label):
        # CV2 BGR -> RGB
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        
        # Scale to fit label
        pixmap = QPixmap.fromImage(qt_image)
        scaled_pixmap = pixmap.scaled(
            label.size(), 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )
        label.setPixmap(scaled_pixmap)

    def delete_original(self):
        ret = QMessageBox.question(self, "Confirm Delete", "Send ORIGINAL file to Recycle Bin?")
        if ret == QMessageBox.StandardButton.Yes:
            # Stop playback and release
            if self.is_playing:
                self.toggle_play()
                
            if hasattr(self, 'cap_orig'):
                self.cap_orig.release()
                
            try:
                send2trash(self.original_path)
                logger.info(f"Sent to trash: {self.original_path}")
                self.btn_del_orig.setEnabled(False)
                self.btn_del_orig.setText("Deleted")
                self.lbl_orig.setText("File Deleted")
                del self.cap_orig
            except Exception as e:
                # Try to recover capture if delete failed
                self.cap_orig = cv2.VideoCapture(self.original_path)
                logger.error(f"Error deleting file: {e}")
                QMessageBox.critical(self, "Error", f"Could not delete file:\n{e}")

    def delete_converted(self):
        ret = QMessageBox.question(self, "Confirm Delete", "Send CONVERTED file to Recycle Bin?")
        if ret == QMessageBox.StandardButton.Yes:
            # Stop playback and release
            if self.is_playing:
                self.toggle_play()
                
            if hasattr(self, 'cap_conv'):
                self.cap_conv.release()
                
            try:
                send2trash(self.converted_path)
                logger.info(f"Sent to trash: {self.converted_path}")
                self.btn_del_conv.setEnabled(False)
                self.btn_del_conv.setText("Deleted")
                self.lbl_conv.setText("File Deleted")
                del self.cap_conv
            except Exception as e:
                # Try to recover capture if delete failed
                self.cap_conv = cv2.VideoCapture(self.converted_path)
                logger.error(f"Error deleting file: {e}")
                QMessageBox.critical(self, "Error", f"Could not delete file:\n{e}")

    def closeEvent(self, event):
        self.timer.stop()
        if hasattr(self, 'cap_orig'): self.cap_orig.release()
        if hasattr(self, 'cap_conv'): self.cap_conv.release()
        self.closed.emit()
        event.accept()
