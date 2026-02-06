import sys
import os
import threading
import subprocess
from typing import List, Dict, Optional
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QListWidget, QListWidgetItem, QProgressBar, QFileDialog, QMessageBox,
    QFrame, QRadioButton, QButtonGroup, QScrollArea, QAbstractItemView, QCheckBox,
    QSizePolicy, QStyle, QSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QSize, QEvent, QThreadPool, QRunnable
from PyQt6.QtGui import QIcon, QPixmap, QAction, QDragEnterEvent, QDropEvent

from ..utils.logger import logger
from ..utils.config import config
from ..utils.helpers import (
    normalize_path, get_video_info, get_video_codec_only,
    format_size, calculate_bitrates, calculate_quality_options, format_bitrate,
    format_time_simple, get_ffmpeg_path, generate_thumbnail
)
from .worker import ConversionWorker
from .preview_window_qt import VideoPreviewWindow
from .monitor import HardwareMonitorWorker
from ..core.converter import should_downscale_to_1080p
from ..utils.scan_cache import ScanCache
from ..utils.thumb_cache import ThumbnailCache
from send2trash import send2trash

# --- Helper for Async Thumbnails ---
class ThumbnailSignaller(QObject):
    finished = pyqtSignal(str, str) # item_path, thumb_path

class ThumbnailRunnable(QRunnable):
    def __init__(self, path, signaller):
        super().__init__()
        self.path = path
        self.signaller = signaller
    
    def run(self):
        import tempfile
        import time
        try:
            # Check Cache First
            cache = ThumbnailCache()
            try:
                stat = os.stat(self.path)
                mtime = stat.st_mtime
                size = stat.st_size
                
                cached_thumb = cache.get_entry(self.path, mtime, size)
                if cached_thumb:
                    self.signaller.finished.emit(self.path, cached_thumb)
                    return
            except OSError:
                pass

            # Generate new
            # Store in 'thumbs' folder in app data or local
            # Let's use a 'thumbs' folder next to executable for portability or logic
            # Using src/../thumbs
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            thumbs_dir = os.path.join(base_dir, "thumbs")
            if not os.path.exists(thumbs_dir):
                os.makedirs(thumbs_dir, exist_ok=True)
                
            fname = f"{os.path.basename(self.path)}_{int(time.time())}.jpg"
            # Sanitize filename? simple hash might be better to avoid length issues
            # But user wants simple.
            out = os.path.join(thumbs_dir, fname)
            
            res = generate_thumbnail(self.path, out)
            if res:
                # Update Cache
                if os.path.exists(self.path):
                    cache.update_entry(self.path, mtime, size, res)
                    cache.save()
                    
                self.signaller.finished.emit(self.path, res)
        except Exception as e:
            logger.error(f"Thumb generation failed: {e}")

class MetadataSignaller(QObject):
    finished = pyqtSignal(str, str) # path, codec

class MetadataRunnable(QRunnable):
    def __init__(self, path, signaller):
        super().__init__()
        self.path = path
        self.signaller = signaller
    
    def run(self):
        try:
            # Check Cache First
            cache = ScanCache()
            try:
                stat = os.stat(self.path)
                mtime = stat.st_mtime
                size = stat.st_size
                
                cached_codec = cache.get_cached_result(self.path, mtime, size)
                if cached_codec:
                    self.signaller.finished.emit(self.path, cached_codec)
                    return
                
                # If not cached, detect
                codec = get_video_codec_only(self.path)
                if codec:
                     # Do NOT save here (Thread race condition)
                     # Just return result
                     self.signaller.finished.emit(self.path, codec)
            except Exception as e:
                logger.error(f"Metadata check error for {self.path}: {e}")

        except Exception as e:
            logger.error(f"Metadata runnable failed: {e}")

class FileListItem(QWidget):
    """Custom Widget for the List Item."""
    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self.path = path
        self.thumb_path = None
        self.out_path = None
        self.video_info = None # Cache video info
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Checkbox
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(False)
        layout.addWidget(self.checkbox)
        
        # Thumbnail
        self.lbl_thumb = QLabel()
        self.lbl_thumb.setFixedSize(80, 45)
        self.lbl_thumb.setStyleSheet("background-color: #000; border-radius: 4px; border: 1px solid #444;")
        self.lbl_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_thumb.setText("...")
        layout.addWidget(self.lbl_thumb)
        
        # Text Info
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        
        self.lbl_name = QLabel(os.path.basename(path))
        self.lbl_name.setStyleSheet("font-weight: bold;")
        text_layout.addWidget(self.lbl_name)
        
        self.lbl_status = QLabel("Pending")
        self.lbl_status.setStyleSheet("color: gray; font-size: 10px;")
        text_layout.addWidget(self.lbl_status)
        
        layout.addLayout(text_layout)
        layout.addStretch()
        
        # Compare Button
        self.btn_compare = QPushButton("\u25B6") # Play symbol
        self.btn_compare.setObjectName("icon_button")
        self.btn_compare.setToolTip("Compare Original vs Converted")
        self.btn_compare.setFixedSize(28, 28)
        self.btn_compare.setEnabled(False)
        layout.addWidget(self.btn_compare)
        
        # Remove Button
        self.btn_remove = QPushButton("\U0001F5D1") # Trash can
        self.btn_remove.setObjectName("danger_icon_button")
        self.btn_remove.setToolTip("Remove and Delete File")
        self.btn_remove.setFixedSize(28, 28)
        layout.addWidget(self.btn_remove)

    def set_thumbnail(self, path):
        self.thumb_path = path
        pix = QPixmap(path)
        self.lbl_thumb.setPixmap(pix.scaled(
            self.lbl_thumb.size(), 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        ))
        
    def set_status(self, status, color=None):
        self.lbl_status.setText(status)
        if color:
            self.lbl_status.setStyleSheet(f"color: {color}; font-size: 10px;")

class SortableListWidgetItem(QListWidgetItem):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.file_size = 0

    def __lt__(self, other):
        # Sort by size (descending request means we need to handle order carefully)
        # QListWidget sort order determines how this is used.
        # If DescendingOrder is used: larger > smaller.
        # standard __lt__ is "is self less than other?".
        return self.file_size < other.file_size

class CombinedInfoCard(QFrame):
    """Unified card to display both input file details and output preview."""
    def __init__(self, data, profile_idx, bitrates_data, has_gpu):
        super().__init__()
        self.setObjectName("info_card")
        self.setStyleSheet("background-color: #2b2b2b; border-radius: 6px; border: 1px solid #3d3d3d;")
        self.setMaximumWidth(850)  # Prevent horizontal scrollbar
        
        # Main horizontal layout: [Input Section] | [Output Section]
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(12)
        
        # ==================== INPUT SECTION (LEFT) ====================
        input_section = QVBoxLayout()
        input_section.setSpacing(6)
        
        # Section Header
        input_header = QLabel("📁 SELECTED FILE INFO")
        input_header.setStyleSheet("font-weight: bold; font-size: 11px; color: #888; text-transform: uppercase;")
        input_section.addWidget(input_header)
        
        # Input Filename (truncate if too long)
        filename = data['filename']
        if len(filename) > 40:
            filename = filename[:37] + "..."
        lbl_input_name = QLabel(filename)
        lbl_input_name.setStyleSheet("font-weight: bold; font-size: 12px; color: #e0e0e0; margin-top: 4px;")
        lbl_input_name.setWordWrap(True)
        input_section.addWidget(lbl_input_name)
        
        # Input Details Row 1: Resolution | Codec
        input_row1 = QHBoxLayout()
        input_row1.setSpacing(8)
        lbl_input_res = QLabel(f"{data['width']}x{data['height']}")
        lbl_input_res.setStyleSheet("color: #a0a0a0; font-size: 11px;")
        lbl_input_codec = QLabel(data['codec'])
        lbl_input_codec.setStyleSheet("color: #a0a0a0; font-size: 11px;")
        input_row1.addWidget(lbl_input_res)
        input_row1.addWidget(QLabel("|"))
        input_row1.addWidget(lbl_input_codec)
        input_row1.addStretch()
        input_section.addLayout(input_row1)
        
        # Input Details Row 2: Size | Duration
        input_row2 = QHBoxLayout()
        input_row2.setSpacing(8)
        lbl_input_size = QLabel(format_size(data['size']))
        lbl_input_size.setStyleSheet("color: #a0a0a0; font-size: 11px;")
        lbl_input_dur = QLabel(format_time_simple(data['duration']))
        lbl_input_dur.setStyleSheet("color: #a0a0a0; font-size: 11px;")
        input_row2.addWidget(lbl_input_size)
        input_row2.addWidget(QLabel("|"))
        input_row2.addWidget(lbl_input_dur)
        input_row2.addStretch()
        input_section.addLayout(input_row2)
        
        input_section.addStretch()
        
        # Add input section to main layout
        main_layout.addLayout(input_section, stretch=1)
        
        # ==================== VERTICAL DIVIDER ====================
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.VLine)
        divider.setStyleSheet("background-color: #3d3d3d;")
        divider.setFixedWidth(1)
        main_layout.addWidget(divider)
        
        # ==================== OUTPUT SECTION (RIGHT) ====================
        output_section = QVBoxLayout()
        output_section.setSpacing(6)
        
        # Section Header
        output_header = QLabel("📤 OUTPUT PREVIEW")
        output_header.setStyleSheet("font-weight: bold; font-size: 11px; color: #888; text-transform: uppercase;")
        output_section.addWidget(output_header)
        
        # Calculate projected output filename
        out_name_base, _ = os.path.splitext(data['filename'])
        if "2160p" in out_name_base:
            out_name_base = out_name_base.replace("2160p", "")
        if "2160" in out_name_base:
            out_name_base = out_name_base.replace("2160", "")
        out_name = f"{out_name_base}_hevc.mp4"
        
        # Output Filename
        lbl_output_name = QLabel(out_name)
        lbl_output_name.setStyleSheet("font-weight: bold; font-size: 12px; color: #e0e0e0; margin-top: 4px;")
        lbl_output_name.setWordWrap(True)
        output_section.addWidget(lbl_output_name)
        
        # Output Details (if profile data available)
        if profile_idx < len(bitrates_data):
            opt = bitrates_data[profile_idx]
            est_size = opt['estimated_size']
            
            # Estimated Size (highlighted)
            lbl_est = QLabel(f"Est: ~{format_size(est_size)}")
            lbl_est.setStyleSheet("font-weight: bold; color: #4CAF50; font-size: 12px; margin-top: 2px;")
            output_section.addWidget(lbl_est)
            
            # Resolution calculation
            w, h = data.get('width', 0), data.get('height', 0)
            if w and h:
                if should_downscale_to_1080p(w, h):
                    out_h = 1080
                    out_w = int(w * (1080 / h))
                    if out_w % 2 != 0: out_w += 1
                    res_text = f"{out_w}x{out_h} (Scaled)"
                else:
                    res_text = f"{w}x{h} (Original)"
            else:
                res_text = "Unknown Res"
            
            # Quality metric: CRF or bitrate
            if 'crf' in opt:
                # New CRF-based system
                quality_text = f"CRF {opt['crf']}"
            elif 'bitrate' in opt:
                # Legacy bitrate system
                quality_text = format_bitrate(opt['bitrate'])
            else:
                quality_text = "Auto"
            
            # Output Details Row: Resolution | Quality
            output_row = QHBoxLayout()
            output_row.setSpacing(8)
            lbl_output_res = QLabel(res_text)
            lbl_output_res.setStyleSheet("color: #a0a0a0; font-size: 11px;")
            lbl_output_quality = QLabel(quality_text)
            lbl_output_quality.setStyleSheet("color: #a0a0a0; font-size: 11px;")
            output_row.addWidget(lbl_output_res)
            output_row.addWidget(QLabel("|"))
            output_row.addWidget(lbl_output_quality)
            output_row.addStretch()
            output_section.addLayout(output_row)
            
            # Encoder
            encoder = 'HEVC_NVENC' if has_gpu else 'HEVC (x265)'
            lbl_encoder = QLabel(encoder)
            lbl_encoder.setStyleSheet("color: #666; font-size: 10px;")
            output_section.addWidget(lbl_encoder)
        else:
            # No profile data available
            lbl_no_profile = QLabel("-")
            lbl_no_profile.setStyleSheet("color: #666;")
            output_section.addWidget(lbl_no_profile)
        
        output_section.addStretch()
        
        # Add output section to main layout
        main_layout.addLayout(output_section, stretch=1)



class MainWindow(QMainWindow):
    # Signal to update GPU status from background thread
    gpu_status_signal = pyqtSignal(str, str)
    
    @staticmethod
    def _should_exclude_codec(codec: str) -> bool:
        """
        Check if a codec should be excluded from the conversion queue.
        
        Args:
            codec: Codec name from ffprobe
            
        Returns:
            True if codec should be excluded, False otherwise
        """
        if not codec:
            return False
        
        codec_lower = codec.lower()
        
        # Exclude modern efficient codecs that don't benefit from HEVC conversion
        # AV1: Already more efficient than HEVC
        # HEVC/H265: Already the target format
        excluded_codecs = ['av1', 'hevc', 'h265']
        
        return any(excluded in codec_lower for excluded in excluded_codecs)
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pro Video Converter - HEVC Batch Edition")
        self.resize(1200, 800)
        self.setAcceptDrops(True)
        
        # Connect signal
        self.gpu_status_signal.connect(self._update_gpu_status)
        
        # State
        self.items: List[QListWidgetItem] = [] # Keeping track of list items
        self.added_paths = set() # O(1) duplicate check
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(3) # Limit concurrent ffmpeg processes
        
        self.bitrate_options = []
        self.has_gpu = False
        self.is_converting = False
        self.gpu_check_complete = False
        
        # Threading for thumbs
        self.thumb_signaller = ThumbnailSignaller()
        self.thumb_signaller.finished.connect(self.on_thumb_generated)

        # Threading for metadata (codec check)
        self.meta_signaller = MetadataSignaller()
        self.meta_signaller.finished.connect(self.on_metadata_ready)
        
        # Connect explicit scan signal
        self.scan_finished.connect(self.on_scan_finished)
        self.scan_progress.connect(self.on_scan_progress)
        
        self.setup_ui()
        
        # Initial GPU Check
        threading.Thread(target=self.check_gpu, daemon=True).start()

    def _create_stat_card(self, icon, value, label,color=None):
        card = QFrame()
        card.setObjectName("stat_card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(4)
        
        top_layout = QHBoxLayout()
        lbl_icon = QLabel(icon)
        lbl_icon.setStyleSheet("font-size: 20px;")
        top_layout.addWidget(lbl_icon)
        top_layout.addStretch()
        
        lbl_value = QLabel(value)
        lbl_value.setObjectName("stat_value")
        if color:
            lbl_value.setStyleSheet(f"color: {color};")
        top_layout.addWidget(lbl_value)
        
        card_layout.addLayout(top_layout)
        
        lbl_label = QLabel(label)
        lbl_label.setObjectName("stat_label")
        card_layout.addWidget(lbl_label)
        
        card.value_label = lbl_value
        return card


    def setup_ui(self):
        # Apply modern theme
        from .theme import MODERN_THEME
        self.setStyleSheet(MODERN_THEME)
        
        # Icon
        icon_path = os.path.join(os.path.dirname(__file__), "..", "assets", "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)
        
        # === HEADER ===
        header = QHBoxLayout()
        
        title_section = QVBoxLayout()
        lbl_title = QLabel("🎬 Pro Video Converter")
        lbl_title.setObjectName("title")
        lbl_subtitle = QLabel("HEVC Batch Edition - Modern UI")
        lbl_subtitle.setObjectName("subtitle")
        title_section.addWidget(lbl_title)
        title_section.addWidget(lbl_subtitle)
        title_section.addStretch()
        
        header.addLayout(title_section)
        header.addStretch()
        
        # Monitor Bars (Header Style - Compact)
        monitor_container = QWidget()
        monitor_container.setFixedWidth(200) # Fixed width to look neat in header
        mon_layout = QVBoxLayout(monitor_container)
        mon_layout.setContentsMargins(0, 0, 0, 0)
        mon_layout.setSpacing(4)
        
        self.pbar_cpu = QProgressBar()
        self.pbar_cpu.setRange(0, 100)
        self.pbar_cpu.setTextVisible(True)
        self.pbar_cpu.setFormat("CPU: %p%")
        self.pbar_cpu.setFixedHeight(12)
        self.pbar_cpu.setStyleSheet("""
            QProgressBar { border: none; background-color: #333; border-radius: 6px; text-align: center; color: white; font-size: 9px; font-weight: bold; }
            QProgressBar::chunk { background-color: #2196F3; border-radius: 6px; }
        """)
        
        self.pbar_gpu = QProgressBar()
        self.pbar_gpu.setRange(0, 100)
        self.pbar_gpu.setTextVisible(True)
        self.pbar_gpu.setFormat("GPU: %p%")
        self.pbar_gpu.setFixedHeight(12)
        self.pbar_gpu.setStyleSheet("""
            QProgressBar { border: none; background-color: #333; border-radius: 6px; text-align: center; color: white; font-size: 9px; font-weight: bold; }
            QProgressBar::chunk { background-color: #4CAF50; border-radius: 6px; }
        """)
        
        mon_layout.addWidget(self.pbar_cpu)
        mon_layout.addWidget(self.pbar_gpu)
        
        header.addWidget(monitor_container)
        
        # Start Monitor Thread (Moved here)
        try:
            self.hw_worker = HardwareMonitorWorker()
            self.hw_worker.metrics_updated.connect(self.update_hw_stats)
            self.hw_worker.start()
        except Exception as e:
            logger.error(f"Failed to start HW monitor: {e}")

        # GPU Badge
        self.lbl_gpu = QLabel("Checking GPU...")
        self.lbl_gpu.setObjectName("badge")
        header.addWidget(self.lbl_gpu)
        
        main_layout.addLayout(header)
        
        # === STATS DASHBOARD ===
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(12)
        
        # Create stat cards
        self.stat_total = self._create_stat_card("📊", "0", "Total Files")
        self.stat_pending = self._create_stat_card("⏳", "0", "Pending", "#f59e0b")
        self.stat_converting = self._create_stat_card("⚙️", "0", "Converting", "#3b82f6")
        self.stat_complete = self._create_stat_card("✅", "0", "Complete", "#10b981")
        
        stats_layout.addWidget(self.stat_total)
        stats_layout.addWidget(self.stat_pending)
        stats_layout.addWidget(self.stat_converting)
        stats_layout.addWidget(self.stat_complete)
        
        main_layout.addLayout(stats_layout)
        
        # === MAIN CONTENT ===
        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)
        
        # --- Left: Queue ---
        left_panel = QFrame()
        left_panel.setObjectName("card")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(16, 16, 16, 16)
        left_layout.setSpacing(8)
        
        lbl_queue = QLabel("Conversion Queue")
        lbl_queue.setObjectName("section_header")
        left_layout.addWidget(lbl_queue)

        # Filter Toolbar
        filter_layout = QHBoxLayout()
        self.chk_filter_hevc = QCheckBox("Only Show x265")
        self.chk_filter_hevc.setToolTip("Show only files that are already HEVC/x265")
        self.chk_filter_hevc.toggled.connect(self.apply_filters)
        filter_layout.addWidget(self.chk_filter_hevc)
        filter_layout.addStretch()
        left_layout.addLayout(filter_layout)
        
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        # self.list_widget.itemSelectionChanged.connect(self.on_selection_changed) # Removed: Selection doesn't drive info anymore
        left_layout.addWidget(self.list_widget)
        
        content_layout.addWidget(left_panel, stretch=1)
        
        # --- Right: Controls & Info ---
        right_panel = QFrame()
        right_panel.setObjectName("card")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(12)
        
        # Toolbar
        btn_row1 = QHBoxLayout()
        btn_row1.setSpacing(8)
        
        self.btn_add = QPushButton("➕ Add Files")
        self.btn_add.setObjectName("primary")
        self.btn_add.clicked.connect(self.browse_files)
        
        self.btn_scan = QPushButton("📁 Scan Folder")
        self.btn_scan.setObjectName("primary")
        self.btn_scan.clicked.connect(self.browse_folder)
        
        btn_row1.addWidget(self.btn_add)
        btn_row1.addWidget(self.btn_scan)
        btn_row1.addStretch()
        
        btn_row2 = QHBoxLayout()
        btn_row2.setSpacing(8)
        
        self.btn_sel_all = QPushButton("Select All")
        self.btn_sel_all.clicked.connect(self.select_all)
        
        self.btn_sel_none = QPushButton("Deselect All")
        self.btn_sel_none.clicked.connect(self.deselect_all)
        
        self.btn_clear = QPushButton("Clear List")
        self.btn_clear.clicked.connect(self.clear_list)
        
        self.btn_clear_cache = QPushButton("Delete Thumbs")
        self.btn_clear_cache.setToolTip("Delete all cached thumbnails from disk")
        self.btn_clear_cache.clicked.connect(self.clear_thumbnails)
        
        btn_row2.addWidget(self.btn_sel_all)
        btn_row2.addWidget(self.btn_sel_none)
        btn_row2.addWidget(self.btn_clear)
        btn_row2.addWidget(self.btn_clear_cache)
        
        right_layout.addLayout(btn_row1)
        right_layout.addLayout(btn_row2)
        

        
        
        # File Info Panel (Unified)
        self.grp_info = QFrame()
        self.grp_info.setObjectName("info_panel")
        info_panel_layout = QVBoxLayout(self.grp_info)
        info_panel_layout.addWidget(QLabel("File Information"))
        
        # Scroll Area for Combined Info Cards
        self.scroll_info = QScrollArea()
        self.scroll_info.setWidgetResizable(True)
        self.scroll_info.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_info.setStyleSheet("background: transparent; border: none;")
        
        self.container_info = QWidget()
        self.container_info.setStyleSheet("background: transparent;")
        self.c_lay_info = QVBoxLayout(self.container_info)
        self.c_lay_info.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.c_lay_info.setContentsMargins(0, 0, 0, 0)
        self.c_lay_info.setSpacing(12)
        
        # Initial Placeholder
        self.lbl_info_placeholder = QLabel("Select a file to view info.")
        self.lbl_info_placeholder.setObjectName("placeholder")
        self.lbl_info_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_info_placeholder.setStyleSheet("color: #666; margin-top: 20px;")
        self.c_lay_info.addWidget(self.lbl_info_placeholder)
        
        self.scroll_info.setWidget(self.container_info)
        info_panel_layout.addWidget(self.scroll_info)
        
        right_layout.addWidget(self.grp_info, stretch=1)

        
        # Compression Options
        opt_group = QFrame()
        opt_lay = QVBoxLayout(opt_group)
        opt_lay.addWidget(QLabel("Compression Level"))
        
        self.radio_group = QButtonGroup(self)
        self.radio_layout = QHBoxLayout()
        self.radio_layout.setSpacing(20)
        self.radios = []
        
        options = ["High Quality", "Balanced", "Compact", "Low Bitrate"]
        for i, name in enumerate(options):
            rb = QRadioButton(name)
            self.radio_group.addButton(rb, i)
            self.radio_layout.addWidget(rb)
            self.radios.append(rb)
            rb.toggled.connect(self.update_output_preview)
            
        self.radios[3].setChecked(True) # Low Bitrate default
        opt_lay.addLayout(self.radio_layout)
        
        # Parallel Task Selector - NEW
        parallel_layout = QHBoxLayout()
        parallel_layout.addWidget(QLabel("Parallel Tasks:"))
        self.spin_parallel = QSpinBox()
        self.spin_parallel.setRange(1, 3)
        self.spin_parallel.setValue(1)
        self.spin_parallel.setToolTip("Number of simultaneous conversions. Increase for high-end GPUs.")
        parallel_layout.addWidget(self.spin_parallel)
        parallel_layout.addStretch()
        
        parallel_layout.addStretch()
        
        opt_lay.addLayout(parallel_layout)
        
        # Auto Delete Toggle - NEW
        self.chk_auto_delete = QCheckBox("Auto Delete Original")
        self.chk_auto_delete.setStyleSheet("color: #ffcccc;") # Light red hint
        opt_lay.addWidget(self.chk_auto_delete)



        right_layout.addWidget(opt_group)
        
        # Start Conversion Button
        self.btn_convert = QPushButton("▶️ Start Batch Conversion")
        self.btn_convert.setObjectName("success")
        self.btn_convert.setMinimumHeight(50)
        # self.btn_convert.setStyleSheet(...) # Removed for theme.py
        self.btn_convert.clicked.connect(self.start_conversion)
        self.btn_convert.setEnabled(False)
        
        self.progress = QProgressBar()
        self.progress.setTextVisible(True)
        self.progress.setFormat("%p%")
        
        status_layout = QHBoxLayout()
        self.lbl_status = QLabel("Ready")
        self.lbl_eta = QLabel("")
        status_layout.addWidget(self.lbl_status)
        status_layout.addStretch()
        status_layout.addWidget(self.lbl_eta)
        
        right_layout.addWidget(self.btn_convert)
        right_layout.addWidget(self.progress)
        right_layout.addLayout(status_layout)
        
        content_layout.addWidget(right_panel, stretch=2)
        main_layout.addLayout(content_layout, stretch=1)

    def apply_filters(self):
        """Filter list items based on codec"""
        show_hevc_mode = self.chk_filter_hevc.isChecked()
        from ..utils.scan_cache import ScanCache
        cache = ScanCache()
        
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if not widget: continue
            
            # Check codec
            is_hevc = False
            codec = "unknown"
            
            # 1. Info in widget
            if widget.video_info:
                streams = widget.video_info.get('streams', [])
                vid = next((s for s in streams if s['codec_type'] == 'video'), {})
                codec = vid.get('codec_name', '').lower()
            
            # 2. Cache
            if codec == "unknown" or not codec:
                 # Try cache
                 try:
                     st = os.stat(widget.path)
                     c_res = cache.get_cached_result(widget.path, st.st_mtime, st.st_size)
                     if c_res: codec = c_res.lower()
                 except:
                     pass

            # 3. Check
            if 'hevc' in codec or 'h265' in codec:
                is_hevc = True
            
            # Exclusive Logic:
            # Mode A (Checked): Show x265 (is_hevc). Hide non-x265.
            # Mode B (Unchecked): Show non-x265 (not is_hevc). Hide x265.
            # Exception: Unknowns shown in both? Or just shown if we want to be safe.
            # Let's show unknown in both to avoid confusion.
            
            if codec == "unknown":
                item.setHidden(False)
                continue
                
            if show_hevc_mode:
                # Show ONLY x265
                item.setHidden(not is_hevc)
            else:
                # Show ONLY non-x265
                item.setHidden(is_hevc)

    def _get_checked_files_data(self):
        """Get data for all CHECKED files"""
        # Iterate all items to find checked ones
        items = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            w = self.list_widget.itemWidget(item)
            if w.checkbox.isChecked():
                items.append(item)
                
        # selected_items = self.list_widget.selectedItems() # OLD
        selected_items = items
        logger.info(f"Checked count: {len(selected_items)}")
        
        if not selected_items:
            return []
        
        files_data = []
        for item in selected_items:
            widget = self.list_widget.itemWidget(item)
            if not widget:
                logger.warning("Item has no widget")
                continue
            
            path = widget.path
            
            # Use cached info if available, otherwise fetch and cache
            if widget.video_info:
                info = widget.video_info
            else:
                info = get_video_info(path)
                if info:
                    widget.video_info = info
            
            # Helper for safe safe extraction
            size = 0
            try:
                size = os.path.getsize(path)
            except:
                pass
                
            dur = 0
            w, h = 0, 0
            codec = "Unknown"
            
            if info:
                dur = float(info.get('format', {}).get('duration', 0))
                streams = info.get('streams', [])
                vid = next((s for s in streams if s['codec_type'] == 'video'), {})
                w, h = vid.get('width', 0), vid.get('height', 0)
                codec = vid.get('codec_name', 'Unknown')
            
            files_data.append({
                'filename': os.path.basename(path),
                'path': path,
                'size': size,
                'duration': dur,
                'width': w,
                'height': h,
                'codec': codec,
                'info': info or {}
            })
            
        return files_data
    
    def _clear_layout(self, layout):
        """Safely clear all items from a layout"""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())
    
    def _update_info_panel(self, files_data):
        """Update unified info panel with combined cards for each file"""
        self._clear_layout(self.c_lay_info)
        
        if not files_data:
            # Recreate placeholder since it might have been deleted by _clear_layout
            self.lbl_info_placeholder = QLabel("Select a file to view info.")
            self.lbl_info_placeholder.setObjectName("placeholder")
            self.lbl_info_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.lbl_info_placeholder.setStyleSheet("color: #666; margin-top: 20px;")
            self.c_lay_info.addWidget(self.lbl_info_placeholder)
            return
        
        # Get current profile selection
        profile_idx = self.radio_group.checkedId()
        
        # Create combined card for each file
        for data in files_data:
            # Calculate bitrates for this file
            bitrates = calculate_quality_options(data['size'], data['duration'], data['info'])
            card = CombinedInfoCard(data, profile_idx, bitrates, self.has_gpu)
            self.c_lay_info.addWidget(card)


    # --- Logic ---

    def check_gpu(self):
        """Check for GPU availability and update UI"""
        try:
            subprocess.run(['nvidia-smi'], capture_output=True, check=True, timeout=2)
            self.has_gpu = True
            msg = "⚡ GPU"
            badge_name = "badge_gpu"
        except:
            self.has_gpu = False
            msg = "💻 CPU Mode"
            badge_name = "badge"
        
        # Emit signal to update UI from main thread
        self.gpu_status_signal.emit(msg, badge_name)
    
    def _update_gpu_status(self, msg, badge_name):
        """Update GPU status label (called from signal in main thread)"""
        self.lbl_gpu.setText(msg)
        self.lbl_gpu.setObjectName(badge_name)
        # Force style refresh
        self.lbl_gpu.style().unpolish(self.lbl_gpu)
        self.lbl_gpu.style().polish(self.lbl_gpu)
        self.lbl_gpu.update()



    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.accept()
            # Visual feedback
            self.centralWidget().setStyleSheet("border: 2px dashed #00dec0;")
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.centralWidget().setStyleSheet("")

    def dropEvent(self, event: QDropEvent):
        self.centralWidget().setStyleSheet("")
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        self.add_files(files)

    def browse_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Video Files", "", "Video Files (*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.webm *.ts)")
        if files:
            self.add_files(files)

    # Define signals
    scan_finished = pyqtSignal(list)
    scan_progress = pyqtSignal(int)

    def browse_folder(self):
        from ..utils.config import config
        last = config.get('last_folder', '')
        folder = QFileDialog.getExistingDirectory(self, "Select Folder", last)
        
        if folder:
            config.set('last_folder', folder)
            self.lbl_status.setText(f"Scanning: {folder}...")
            self.btn_scan.setEnabled(False)
            threading.Thread(target=self.scan_folder_thread, args=(folder,), daemon=True).start()

    def scan_folder_thread(self, folder):
        logger.info(f"Starting scan of folder: {folder}")
        cache = ScanCache()
        
        extensions = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.ts'}
        files_to_check = []
        
        # 1. Collect all candidate files first (Fast I/O)
        try:
            for root, _, files in os.walk(folder):
                for f in files:
                    if os.path.splitext(f)[1].lower() in extensions:
                        files_to_check.append(os.path.join(root, f))
        except Exception as e:
             logger.error(f"Error walking folder: {e}")
             return

        found = []
        
        # 2. Check cache first to avoid unnecessary threads
        tasks = []
        
        # Helper for thread pool
        def check_file(path):
            try:
                stat = os.stat(path)
                mtime = stat.st_mtime
                size = stat.st_size
                
                # We can read cache here safely (read-only dict access is thread-safe in Python for simple gets usually, 
                # but better to rely on local var if possible. ScanCache.get_cached_result is simple.)
                # Ideally, we checked cache in main loop, but for parallel efficiency we can do it here 
                # OR separating cached from non-cached tasks. 
                # Let's simple check:
                # But 'cache' object is shared. `get_cached_result` is read only.
                
                # Actually, `get_video_codec_only` is the slow part.
                # Let's do the probe.
                
                codec = get_video_codec_only(path)
                return (path, mtime, size, codec)
            except:
                return None

        # Filter out already cached items to save thread overhead
        unknown_files = []
        for path in files_to_check:
            try:
                stat = os.stat(path)
                mtime = stat.st_mtime
                size = stat.st_size
                cached = cache.get_cached_result(path, mtime, size)
                if cached:
                    # Check if codec should be excluded (AV1, HEVC)
                    if not self._should_exclude_codec(cached):
                        found.append(path)
                else:
                    unknown_files.append(path)
            except OSError:
                pass
        
        # Update progress for cached items
        if found:
            self.scan_progress.emit(len(found))
            
        # 3. Process unknown files in parallel
        from concurrent.futures import ThreadPoolExecutor
        if unknown_files:
            # CPU count * 2 or fixed limit. FFmpeg spawns process, so don't go too crazy.
            max_workers = min(32, (os.cpu_count() or 4) * 4) 
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all
                future_to_path = {executor.submit(check_file, p): p for p in unknown_files}
                
                completed_count = 0
                total_unknown = len(unknown_files)
                
                from concurrent.futures import as_completed
                for future in as_completed(future_to_path):
                    res = future.result()
                    if res:
                        path, mtime, size, codec = res
                        if codec:
                            # Update cache object (not saved to disk yet)
                            cache.update_result(path, mtime, size, codec)
                            # Check if codec should be excluded (AV1, HEVC)
                            if not self._should_exclude_codec(codec):
                                found.append(path)
                    
                    completed_count += 1
                    # Debounce progress updates to avoid UI flood
                    if completed_count % 5 == 0 or completed_count == total_unknown:
                        self.scan_progress.emit(len(found))

        # 4. Save Cache
        try:
            cache.save()
            logger.info(f"Scan complete. Found {len(found)} files.")
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
        
        # Emit signal to main thread
        self.scan_finished.emit(found)
    
    def on_scan_progress(self, count):
        self.lbl_status.setText(f"Scanning... Found {count} files")
    
    def on_scan_finished(self, found_files):
        self.btn_scan.setEnabled(True)
        if not found_files:
            self.lbl_status.setText("Scan complete. No files found.")
            QMessageBox.information(self, "Scan Result", "No video files found in folder.")
            return
            
        self.lbl_status.setText(f"Scan complete. Adding {len(found_files)} files...")
        self.add_files(found_files)
        self.lbl_status.setText("Ready")

    def add_files(self, paths: List[str]):
        new_items_added = False
        for path in paths:
            path = normalize_path(path)
            # Check duplicates O(1)
            if path in self.added_paths:
                continue
                
            self.added_paths.add(path)
            new_items_added = True

            # Create sortable item
            item = SortableListWidgetItem(self.list_widget)
            item.setSizeHint(QSize(0, 60))
            
            try:
                item.file_size = os.path.getsize(path)
            except OSError:
                item.file_size = 0
            
            widget = FileListItem(path)
            # Icons are set in FileListItem init
            
            widget.checkbox.toggled.connect(self.on_active_data_changed)
            widget.btn_compare.clicked.connect(lambda ch, w=widget: self.open_compare(w))
            widget.btn_remove.clicked.connect(lambda ch, it=item: self.remove_item(it))
            
            self.list_widget.setItemWidget(item, widget)
            
            # Queue thumbnail generation in ThreadPool
            task = ThumbnailRunnable(path, self.thumb_signaller)
            self.thread_pool.start(task)
            
            # Queue metadata code check
            meta_task = MetadataRunnable(path, self.meta_signaller)
            self.thread_pool.start(meta_task)
            
        if new_items_added:
            # Trigger sort (Descending = Heaviest First)
            self.list_widget.sortItems(Qt.SortOrder.DescendingOrder)
            
            self.update_convert_btn()
            
            if self.list_widget.count() > 0 and self.list_widget.currentRow() == -1:
                self.list_widget.setCurrentRow(0)
                # self.on_selection_changed()
        
        self.apply_filters()
        self.update_dashboard_counts()

    def remove_item(self, item):
        widget = self.list_widget.itemWidget(item)
        path = widget.path
        
        ret = QMessageBox.question(self, "Delete File", f"Are you sure you want to delete this file?\n{path}", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if ret == QMessageBox.StandardButton.Yes:
            try:
                ScanCache().remove_result(path)
                
                if path in self.added_paths:
                    self.added_paths.remove(path)

                send2trash(path)
                row = self.list_widget.row(item)
                self.list_widget.takeItem(row)
                self.update_convert_btn()
                self.update_dashboard_counts()
                # Reset selection details if empty
                if self.list_widget.count() == 0:
                    self._update_info_panel([])
                logger.info(f"Deleted file from queue and disk: {path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not delete file: {e}")



    def on_thumb_generated(self, path, thumb_path):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if widget.path == path:
                widget.set_thumbnail(thumb_path)
                break

    def on_metadata_ready(self, path, codec):
        """Called when metadata is ready"""
        # Save to cache here (Main Thread = Serialized)
        try:
            # We fetch file stats again or trust they haven't changed in sub-second time.
            # Re-fetch is safer for consistent cache key
            st = os.stat(path)
            from ..utils.scan_cache import ScanCache
            cache = ScanCache()
            cache.update_result(path, st.st_mtime, st.st_size, codec)
            cache.save()
        except Exception as e:
            logger.error(f"Failed to update cache in UI thread: {e}")

        # Update widget info if present
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if widget.path == path:
                # Re-apply filters to update visibility
                self.apply_filters()
                break

    def on_selection_changed(self):
        # Deprecated / Unused for info panels now.
        # But we keeping the method signature in case something triggers it, or we just pass.
        pass

    def on_active_data_changed(self):
        """Handle data changes (checkbox toggles)"""
        files_data = self._get_checked_files_data()
        
        # Update file info panel
        self._update_info_panel(files_data)
        
        # Update bitrate options for single file compatibility (for correct radio labels)
        if len(files_data) == 1:
            f = files_data[0]
            self.bitrate_options = calculate_quality_options(f['size'], f['duration'], f['info'])
            
            # Update radio labels with sizes
            for i, rb in enumerate(self.radios):
                if i < len(self.bitrate_options):
                    opt = self.bitrate_options[i]
                    rb.setText(f"{opt['name']} (~{format_size(opt['estimated_size'])})")
        else:
            # Multi-file: Reset labels to default names
            options = ["High Quality", "Balanced", "Compact", "Low Bitrate"]
            for i, name in enumerate(options):
                if i < len(self.radios):
                    self.radios[i].setText(name)
        
        # Update button state
        self.update_convert_btn()

    def update_output_preview(self):
        """Update info panel based on current selection"""
        files_data = self._get_checked_files_data()
        self._update_info_panel(files_data)

    def update_convert_btn(self):
        count = 0
        for i in range(self.list_widget.count()):
            w = self.list_widget.itemWidget(self.list_widget.item(i))
            if w.checkbox.isChecked():
                count += 1
        
        self.btn_convert.setEnabled(count > 0 and not self.is_converting)
        self.btn_convert.setText(f"Convert {count} File(s)" if count > 0 else "Select Files")

    def update_dashboard_counts(self):
        """Recalculate and update dashboard statistics"""
        total = self.list_widget.count()
        pending = 0
        converting = 0
        complete = 0
        
        for i in range(total):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if not widget: continue
            
            # Status is text in lbl_status
            status = widget.lbl_status.text()
            
            if status == "Pending":
                pending += 1
            elif status == "Converting...":
                converting += 1
            elif status == "Done":
                complete += 1
                
        self.stat_total.value_label.setText(str(total))
        self.stat_pending.value_label.setText(str(pending))
        self.stat_converting.value_label.setText(str(converting))
        self.stat_complete.value_label.setText(str(complete))

    def select_all(self):
        for i in range(self.list_widget.count()):
            w = self.list_widget.itemWidget(self.list_widget.item(i))
            w.checkbox.blockSignals(True)
            w.checkbox.setChecked(True)
            w.checkbox.blockSignals(False)
        self.on_active_data_changed()

    def deselect_all(self):
        for i in range(self.list_widget.count()):
            w = self.list_widget.itemWidget(self.list_widget.item(i))
            w.checkbox.blockSignals(True)
            w.checkbox.setChecked(False)
            w.checkbox.blockSignals(False)
        self.on_active_data_changed()

    def clear_list(self):
        self.list_widget.clear()
        self.update_convert_btn()
        self.update_dashboard_counts()
        self._update_info_panel([])

    def clear_thumbnails(self):
        ret = QMessageBox.question(self, "Clear Cache", "Delete all cached thumbnails?\nThis cannot be undone.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ret == QMessageBox.StandardButton.Yes:
            try:
                ThumbnailCache().clear()
                # Reload UI thumbnails? No, just clearing disk cache is enough as per request.
                QMessageBox.information(self, "Success", "Thumbnail cache cleared.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to clear cache: {e}")

    def start_conversion(self):
        # Check if already running (Stop action)
        if hasattr(self, 'is_converting') and self.is_converting:
            self.stop_conversion()
            return
            
        profile_idx = self.radio_group.checkedId()
        items = []
        for i in range(self.list_widget.count()):
            w = self.list_widget.itemWidget(self.list_widget.item(i))
            if w.checkbox.isChecked():
                # Construct item dict for Worker
                items.append({
                    'path': w.path, 
                    'profile_idx': profile_idx,
                    'delete_flag': self.chk_auto_delete.isChecked()
                })
                
        if not items:
            QMessageBox.warning(self, "No Selection", "Please check at least one file to convert.")
            return

        self.is_converting = True
        
        # UI State - Cancel Button
        self.btn_convert.setText("⏹ Stop Conversion")
        self.btn_convert.setObjectName("danger") 
        self.btn_convert.setStyleSheet("background-color: #ef4444; color: white; border: none; border-radius: 4px; font-weight: bold; font-size: 14px;")
        
        self.btn_add.setEnabled(False)
        self.btn_scan.setEnabled(False)
        self.spin_parallel.setEnabled(False)
        
        # Initialize Worker
        max_concurrency = self.spin_parallel.value()
        self.worker = ConversionWorker(items, self.has_gpu, max_concurrency=self.spin_parallel.value())
        self.worker.progress_updated.connect(self.on_worker_progress)
        self.worker.file_started.connect(self.on_file_started)
        self.worker.file_finished.connect(self.on_file_finished)
        self.worker.batch_finished.connect(self.on_batch_finished)
        
        self.worker.start()

    def stop_conversion(self):
        """Stop the running conversion"""
        if self.worker:
            self.worker.stop()
            self.lbl_status.setText("Stopped by User")
            
            # Reset State
            self.is_converting = False
            
            # Reset UI Elements
            self.btn_convert.setStyleSheet("") # Remove danger style
            self.update_convert_btn() # Resets text and enabled state
            
            self.btn_add.setEnabled(True)
            self.btn_scan.setEnabled(True)
            self.spin_parallel.setEnabled(True)

    def on_worker_progress(self, val, pct, eta):
        self.progress.setValue(int(val * 100))
        self.lbl_eta.setText(f"ETA: {eta}")

    def on_file_started(self, path, idx, total):
        self.lbl_status.setText(f"Processing {idx}/{total}: {os.path.basename(path)}")
        # Highlight in list
        for i in range(self.list_widget.count()):
            w = self.list_widget.itemWidget(self.list_widget.item(i))
            if w.path == path:
                w.set_status("Converting...", "#2196F3")
                self.update_dashboard_counts()

    def on_file_finished(self, path, success, result, deleted):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            w = self.list_widget.itemWidget(item)
            if w.path == path:
                 if success:
                     if deleted:
                        # Remove from UI as it was deleted from disk
                        row = self.list_widget.row(item)
                        self.list_widget.takeItem(row)
                        if path in self.added_paths:
                            self.added_paths.remove(path)
                        logger.info(f"Auto-deleted file removed from queue: {path}")
                        # If we removed the item, we need to break because the list changed
                        break
                     else:
                        w.set_status("Done", "#4CAF50")
                        w.out_path = result
                        # Enable compare
                        w.btn_compare.setEnabled(True)
                        w.setStyleSheet("background-color: #1e3d2f;") # Subtle hint
                 else:
                     w.set_status("Failed", "#F44336")
                     w.setStyleSheet("background-color: #3d1e1e;")
            
            self.update_dashboard_counts()

    def on_batch_finished(self):
        self.is_converting = False
        self.lbl_status.setText("Batch Complete")
        
        # Reset UI
        self.btn_convert.setStyleSheet("") 
        
        QMessageBox.information(self, "Done", "Batch conversion finished.")
        self.btn_convert.setEnabled(True)
        self.btn_add.setEnabled(True)
        self.btn_scan.setEnabled(True)
        self.spin_parallel.setEnabled(True)
        self.update_convert_btn()

    def update_hw_stats(self, cpu, gpu, video_engine):
        self.pbar_cpu.setValue(int(cpu))
        self.pbar_cpu.setFormat(f"CPU: {int(cpu)}%")
        
        if gpu is not None:
            self.pbar_gpu.setValue(int(gpu))
            self.pbar_gpu.setFormat(f"GPU: {int(gpu)}%")
            self.pbar_gpu.setVisible(True)
        else:
            self.pbar_gpu.setVisible(False) 

    def closeEvent(self, event):
        # Stop HW worker
        if hasattr(self, 'hw_worker'):
            self.hw_worker.stop()
        
        # Stop conversions if running
        if hasattr(self, 'worker') and self.worker:
            self.worker.stop()
            
        event.accept()

    def open_compare(self, widget):
        if widget.out_path and os.path.exists(widget.out_path):

            self.preview = VideoPreviewWindow(widget.path, widget.out_path)
            self.preview.file_deleted.connect(self.on_preview_file_deleted)
            self.preview.show()
        else:
            QMessageBox.critical(self, "Error", "Output file not found.")

    def on_preview_file_deleted(self, path):
        """Handle file deletion from preview window"""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            w = self.list_widget.itemWidget(item)
            if w and w.path == path:
                # Remove from UI
                row = self.list_widget.row(item)
                self.list_widget.takeItem(row) # This deletes the item and widget
                
                # Cleanup internal state
                if path in self.added_paths:
                    self.added_paths.remove(path)
                
                # Cleanup Cache
                try:
                    ThumbnailCache().remove_entry(path)
                    logger.info(f"Cleaned up cache for deleted file: {path}")
                except Exception as e:
                    logger.error(f"Failed to clean cache for {path}: {e}")
                
                self.update_dashboard_counts()
                self.update_convert_btn()
                self._update_info_panel([]) # Clear info panel if it was showing this file
                break

