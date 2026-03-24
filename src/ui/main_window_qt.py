import sys
import os
import threading
import subprocess
from typing import List, Dict, Optional
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QListWidget, QListWidgetItem, QProgressBar, QFileDialog, QMessageBox,
    QFrame, QRadioButton, QButtonGroup, QScrollArea, QAbstractItemView, QCheckBox,
    QSizePolicy, QStyle, QSpinBox, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QSize, QEvent, QThreadPool, QRunnable
from PyQt6.QtGui import QIcon, QPixmap, QAction, QDragEnterEvent, QDropEvent

from ..utils.logger import logger
from ..utils.config import config
from ..utils.helpers import (
    normalize_path, get_video_info, get_video_codec_only,
    format_size, calculate_bitrates, calculate_quality_options, format_bitrate,
    format_time_simple, get_ffmpeg_path
)
from .worker import ConversionWorker
from .preview_window_qt import VideoPreviewWindow
from .monitor import HardwareMonitorWorker
from ..core.converter import should_downscale_to_1080p
from ..utils.scan_cache import ScanCache
from send2trash import send2trash


class MetadataSignaller(QObject):
    finished = pyqtSignal(str, dict, str) # path, info_dict, codec

class MetadataRunnable(QRunnable):
    def __init__(self, path, signaller):
        super().__init__()
        self.path = path
        self.signaller = signaller
    
    def run(self):
        try:
            from pathlib import Path as _P
            norm_path = str(_P(self.path))

            # Check details cache first
            from ..utils.scan_cache import ScanCache
            cache = ScanCache()
            try:
                st = os.stat(norm_path)
                cached = cache.get_cached_details(norm_path, st.st_mtime, st.st_size)
                if cached:
                    # Build a minimal info dict from cached data so widget can render
                    info = {
                        'streams': [{
                            'codec_type': 'video',
                            'codec_name': cached['codec'],
                            'width': cached['width'],
                            'height': cached['height'],
                        }],
                        'format': {'duration': str(cached['duration'])}
                    }
                    self.signaller.finished.emit(norm_path, info, cached['codec'])
                    return
            except OSError:
                pass

            # Cache miss — probe with ffprobe
            from ..utils.helpers import get_video_info
            info = get_video_info(norm_path)
            codec = 'Unknown'
            width = height = 0
            duration = 0.0
            if info:
                vid = next((s for s in info.get('streams', []) if s.get('codec_type') == 'video'), {})
                codec = vid.get('codec_name', 'Unknown')
                width = vid.get('width', 0)
                height = vid.get('height', 0)
                duration = float(info.get('format', {}).get('duration', 0))
                # Persist to cache
                try:
                    st = os.stat(norm_path)
                    cache.update_details(norm_path, st.st_mtime, st.st_size,
                                         codec, width, height, duration)
                    cache.save()
                except OSError:
                    pass

            self.signaller.finished.emit(norm_path, info or {}, codec)
        except Exception as e:
            logger.error(f"Metadata runnable failed for {self.path}: {e}")

class FileListItem(QWidget):
    """Custom Integrated Widget for the List Item."""
    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self.path = path
        self.out_path = None
        self.video_info = None # Cache video info
        self.codec = "Unknown"
        
        from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QCheckBox, QLabel, QComboBox, QPushButton
        from PyQt6.QtCore import Qt
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(12)
        
        # Checkbox
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(False)
        layout.addWidget(self.checkbox)
        
        # Filename
        import os
        filename = os.path.basename(path)
        if len(filename) > 55: filename = filename[:52] + "..."
        self.lbl_name = QLabel(filename)
        self.lbl_name.setStyleSheet("font-weight: bold; font-size: 12px; color: #e0e0e0;")
        self.lbl_name.setMinimumWidth(200)
        layout.addWidget(self.lbl_name, stretch=1)
        
        # Details (resolution | codec | size | duration)
        self.lbl_details = QLabel("Loading...")
        self.lbl_details.setStyleSheet("color: #a0a0a0; font-size: 11px;")
        self.lbl_details.setMinimumWidth(180)
        layout.addWidget(self.lbl_details)
        
        # Status
        self.lbl_status = QLabel("Pending")
        self.lbl_status.setStyleSheet("color: gray; font-size: 11px; font-weight: bold;")
        self.lbl_status.setFixedWidth(80)
        layout.addWidget(self.lbl_status)
        
        # Quality combo
        self.combo_quality = QComboBox()
        self.combo_quality.addItems(["High Quality", "Balanced", "Compact", "Low Bitrate"])
        self.combo_quality.setCurrentIndex(2)  # Default: Compact
        self.combo_quality.setFixedWidth(120)
        layout.addWidget(self.combo_quality)
        
        # Estimated size
        self.lbl_est_size = QLabel("Est: --")
        self.lbl_est_size.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 11px;")
        self.lbl_est_size.setFixedWidth(90)
        self.lbl_est_size.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.lbl_est_size)
        
        # Action buttons
        self.btn_compare = QPushButton("▶")
        self.btn_compare.setObjectName("icon_button")
        self.btn_compare.setToolTip("Compare Original vs Converted")
        self.btn_compare.setFixedSize(26, 26)
        self.btn_compare.setEnabled(False)
        layout.addWidget(self.btn_compare)
        
        self.btn_remove = QPushButton("🗑")
        self.btn_remove.setObjectName("danger_icon_button")
        self.btn_remove.setToolTip("Remove and Delete File")
        self.btn_remove.setFixedSize(26, 26)
        layout.addWidget(self.btn_remove)
        
        # Keep row compact
        self.setFixedHeight(36)
        
        self.combo_quality.currentIndexChanged.connect(self.refresh_details)



    def set_status(self, status, color=None):
        self.lbl_status.setText(status)
        if color:
            self.lbl_status.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: bold;")

    def refresh_details(self):
        if not getattr(self, 'video_info', None):
            return
            
        import os
        try:
            size = os.path.getsize(self.path)
        except OSError:
            size = 0
            
        dur = float(self.video_info.get('format', {}).get('duration', 0))
        streams = self.video_info.get('streams', [])
        vid = next((s for s in streams if s.get('codec_type', '') == 'video'), {})
        w, h = vid.get('width', 0), vid.get('height', 0)
        codec = getattr(self, 'codec', 'Unknown')
        
        # Update source info
        from ..utils.helpers import format_size, format_time_simple
        self.lbl_details.setText(f"{w}x{h} | {codec.upper()} | {format_size(size)} | {format_time_simple(dur)}")
        
        # Target estimate
        from ..utils.helpers import calculate_quality_options
        opts = calculate_quality_options(size, dur, self.video_info)
        idx = self.combo_quality.currentIndex()
        if idx < len(opts):
            est = opts[idx]['estimated_size']
            self.lbl_est_size.setText(f"Est: ~{format_size(est)}")
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
        excluded_codecs = ['av1', 'hevc', 'h265', 'x265']
        
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
        content_layout = QVBoxLayout()
        content_layout.setSpacing(10)
        
        # --- Top Toolbars ---
        toolbar_container = QFrame()
        toolbar_container.setObjectName("card")
        top_layout = QHBoxLayout(toolbar_container)
        top_layout.setContentsMargins(8, 6, 8, 6)
        top_layout.setSpacing(8)
        
        # Left: Add & Scan
        self.btn_add = QPushButton("➕ Add Files")
        self.btn_add.setObjectName("primary")
        self.btn_add.clicked.connect(self.browse_files)
        self.btn_scan = QPushButton("📁 Scan Folder")
        self.btn_scan.setObjectName("primary")
        self.btn_scan.clicked.connect(self.browse_folder)
        top_layout.addWidget(self.btn_add)
        top_layout.addWidget(self.btn_scan)
        
        top_layout.addWidget(QLabel("|"))
        
        # Filters & Options
        self.chk_filter_hevc = QCheckBox("Hide x265/HEVC")
        self.chk_filter_hevc.toggled.connect(self.apply_filters)
        top_layout.addWidget(self.chk_filter_hevc)
        
        top_layout.addWidget(QLabel("Parallel:"))
        
        # Segmented toggle buttons for parallel task count
        from PyQt6.QtWidgets import QButtonGroup
        self._parallel_group = QButtonGroup(self)
        self._parallel_group.setExclusive(True)
        _seg_style = """
            QPushButton { 
                min-width: 28px; max-width: 28px; min-height: 24px; max-height: 24px;
                border: 1px solid #555; background: #2a2a3a; color: #ccc; 
                font-weight: bold; font-size: 12px; 
            }
            QPushButton:checked { background: #7c3aed; color: white; border-color: #9f67ff; }
            QPushButton:hover:!checked { background: #3a3a4a; }
        """
        for i in range(1, 4):
            btn = QPushButton(str(i))
            btn.setCheckable(True)
            btn.setStyleSheet(_seg_style)
            if i == 1:
                btn.setChecked(True)
            self._parallel_group.addButton(btn, i)
            top_layout.addWidget(btn)
        
        # Compatibility shim: expose .value() and .setEnabled() like the old QSpinBox
        class _ParallelAccessor:
            def __init__(self, group):
                self._group = group
            def value(self):
                return self._group.checkedId()
            def setEnabled(self, enabled):
                for b in self._group.buttons():
                    b.setEnabled(enabled)
        self.spin_parallel = _ParallelAccessor(self._parallel_group)
        
        self.chk_auto_delete = QCheckBox("Auto Delete Original")
        self.chk_auto_delete.setChecked(True)
        self.chk_auto_delete.setStyleSheet("color: #ffcccc;")
        top_layout.addWidget(self.chk_auto_delete)
        
        top_layout.addStretch()
        
        # Right: Selection & Cache
        self.btn_sel_all = QPushButton("Select All")
        self.btn_sel_all.clicked.connect(self.select_all)
        self.btn_sel_none = QPushButton("Deselect All")
        self.btn_sel_none.clicked.connect(self.deselect_all)
        self.btn_clear = QPushButton("Clear List")
        self.btn_clear.clicked.connect(self.clear_list)
        self.btn_clear_cache = QPushButton("🗑 Clear Cache")
        self.btn_clear_cache.setToolTip("Clear the file details cache (forces ffprobe re-scan on next load)")
        self.btn_clear_cache.clicked.connect(self.clear_cache)
        
        top_layout.addWidget(self.btn_sel_all)
        top_layout.addWidget(self.btn_sel_none)
        top_layout.addWidget(self.btn_clear)
        top_layout.addWidget(self.btn_clear_cache)

        
        content_layout.addWidget(toolbar_container)
        
        # --- Center: Queue ---
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        content_layout.addWidget(self.list_widget, stretch=1)
        
        # --- Bottom: Controls & Status ---
        bottom_container = QFrame()
        bottom_container.setObjectName("card")
        bottom_layout = QVBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(12, 12, 12, 12)
        bottom_layout.setSpacing(8)
        
        self.btn_convert = QPushButton("▶️ Start Batch Conversion")
        self.btn_convert.setObjectName("success")
        self.btn_convert.setMinimumHeight(45)
        self.btn_convert.clicked.connect(self.start_conversion)
        self.btn_convert.setEnabled(False)
        bottom_layout.addWidget(self.btn_convert)
        
        self.progress = QProgressBar()
        self.progress.setTextVisible(True)
        self.progress.setFormat("%p%")
        bottom_layout.addWidget(self.progress)
        
        status_layout = QHBoxLayout()
        self.lbl_status = QLabel("Ready")
        self.lbl_eta = QLabel("")
        status_layout.addWidget(self.lbl_status)
        status_layout.addStretch()
        status_layout.addWidget(self.lbl_eta)
        bottom_layout.addLayout(status_layout)
        
        content_layout.addWidget(bottom_container)
        
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
                'info': info or {},
                'profile_idx': widget.combo_quality.currentIndex()
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
    
    def clear_cache(self):
        """Clear the scan/details cache and reset the LRU cache on get_video_info."""
        try:
            ScanCache().clear()
            # Also reset the in-memory LRU cache so re-probes are fresh
            get_video_info.cache_clear()
            self.lbl_status.setText("Cache cleared.")
            logger.info("File details cache cleared by user.")
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            self.lbl_status.setText("Failed to clear cache.")

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

    def add_files(self, paths: list[str]):
        new_items_added = False
        import os
        from ..utils.helpers import normalize_path
        for path in paths:
            path = normalize_path(path)
            if path in getattr(self, 'added_paths', set()):
                continue
                
            self.added_paths.add(path)
            new_items_added = True

            item = SortableListWidgetItem(self.list_widget)
            
            try:
                item.file_size = os.path.getsize(path)
            except OSError:
                item.file_size = 0
            
            widget = FileListItem(path)
            # Size hint: use widget's natural height so nothing gets clipped
            item.setSizeHint(widget.sizeHint())
            
            widget.checkbox.toggled.connect(self.on_active_data_changed)
            widget.combo_quality.currentIndexChanged.connect(self.on_active_data_changed)
            widget.btn_compare.clicked.connect(lambda ch, w=widget: self.open_compare(w))
            widget.btn_remove.clicked.connect(lambda ch, it=item: self.remove_item(it))
            
            self.list_widget.setItemWidget(item, widget)

            # Try to populate immediately from cache
            needs_probe = True
            try:
                st = os.stat(path)
                cached = ScanCache().get_cached_details(path, st.st_mtime, st.st_size)
                if cached:
                    widget.video_info = {
                        'streams': [{
                            'codec_type': 'video',
                            'codec_name': cached['codec'],
                            'width': cached['width'],
                            'height': cached['height'],
                        }],
                        'format': {'duration': str(cached['duration'])}
                    }
                    widget.codec = cached['codec']
                    widget.refresh_details()
                    needs_probe = False
            except OSError:
                pass

            # Queue metadata probe only when not already cached
            if needs_probe:
                meta_task = MetadataRunnable(path, getattr(self, 'meta_signaller'))
                self.thread_pool.start(meta_task)
            
        if new_items_added:
            from PyQt6.QtCore import Qt
            self.list_widget.sortItems(Qt.SortOrder.DescendingOrder)
            self.update_convert_btn()
            
            if self.list_widget.count() > 0 and self.list_widget.currentRow() == -1:
                self.list_widget.setCurrentRow(0)
        
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



    def on_metadata_ready(self, path, info_dict, codec):
        """Called when metadata is ready"""
        try:
            st = os.stat(path)
            from ..utils.scan_cache import ScanCache
            cache = ScanCache()
            cache.update_result(path, st.st_mtime, st.st_size, codec)
            cache.save()
        except Exception as e:
            logger.error(f"Failed to update cache in UI thread: {e}")

        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if widget.path == path:
                widget.video_info = info_dict
                widget.codec = codec
                widget.refresh_details()
                self.apply_filters()
                break

    def on_selection_changed(self):
        # Deprecated / Unused for info panels now.
        # But we keeping the method signature in case something triggers it, or we just pass.
        pass

    def on_active_data_changed(self):
        """Handle data changes (checkbox toggles and combo updates)"""
        files_data = self._get_checked_files_data()
        
        # Update file info panel
        
        # Update button state
        self.update_convert_btn()

    def update_output_preview(self):
        """Update info panel based on current selection"""
        files_data = self._get_checked_files_data()

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

    def start_conversion(self):
        # Check if already running (Stop action)
        if hasattr(self, 'is_converting') and self.is_converting:
            self.stop_conversion()
            return
            
        items = []
        for i in range(self.list_widget.count()):
            w = self.list_widget.itemWidget(self.list_widget.item(i))
            if w.checkbox.isChecked():
                # Construct item dict for Worker
                items.append({
                    'path': w.path, 
                    'profile_idx': w.combo_quality.currentIndex(),
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
                logger.info(f"Cleaned up file from UI: {path}")
                
                self.update_dashboard_counts()
                self.update_convert_btn()
                self._update_info_panel([]) # Clear info panel if it was showing this file
                break

