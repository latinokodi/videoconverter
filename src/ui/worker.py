import os
import time
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool
from ..core.converter import Converter
from ..utils.logger import logger
from ..utils.helpers import get_video_info, calculate_bitrates, calculate_quality_options

class Signals(QObject):
    """Signals for the Runnable"""
    progress = pyqtSignal(str, float, str, str) # file_path, progress, percent_str, eta_str
    finished = pyqtSignal(str, bool, str, bool) # file_path, success, result, deleted

class FileConversionRunnable(QRunnable):
    def __init__(self, item, has_gpu):
        super().__init__()
        self.item = item
        self.has_gpu = has_gpu
        self.signals = Signals()
        self.converter = Converter(has_gpu, self._update_callback)
        self._is_stopped = False
        
    def run(self):
        input_path = self.item['path']
        try:
            # Determine options if not provided
            options = self.item.get('options')
            if not options:
                try:
                    profile_idx = self.item.get('profile_idx', 1)
                    info = get_video_info(input_path)
                    if info:
                        size = os.path.getsize(input_path)
                        dur = float(info.get('format', {}).get('duration', 0))
                        bitrate_opts = calculate_quality_options(size, dur, info)
                        if bitrate_opts:
                            if profile_idx >= len(bitrate_opts): profile_idx = 1
                            options = bitrate_opts[profile_idx]
                except Exception as e:
                    logger.error(f"Error calculating options for {input_path}: {e}")
            
            if not options:
                self.signals.finished.emit(input_path, False, "Could not determine compression options.", False)
                return

            # Inject global flags
            if 'delete_flag' in self.item:
                options['delete_original'] = self.item['delete_flag']
            
            if 'smooth_motion' in self.item:
                options['smooth_motion'] = self.item['smooth_motion']

            if self._is_stopped:
                return

            # Execute conversion
            delete_original = options.get('delete_original', False)
            success_tuple = self.converter.convert_single_file(input_path, options, delete_original=delete_original)
            
            if self._is_stopped:
                return

            if success_tuple[0]: # Success
                _, _, result_path = success_tuple
                self.signals.finished.emit(input_path, True, result_path, delete_original)
            else: # Failure
                _, error_msg, _ = success_tuple
                self.signals.finished.emit(input_path, False, error_msg if error_msg else "Unknown Error", False)
                
        except Exception as e:
            self.signals.finished.emit(input_path, False, str(e), False)

    def stop(self):
        self._is_stopped = True
        self.converter.stop()

    def _update_callback(self, progress, percent_str, eta_str):
        if not self._is_stopped:
            self.signals.progress.emit(self.item['path'], progress, percent_str, eta_str)

class ConversionWorker(QObject):
    # Signals
    progress_updated = pyqtSignal(float, str, str) # Global progress (0.0-1.0), percent string, eta string
    file_started = pyqtSignal(str, int, int) # file path, index, total
    file_finished = pyqtSignal(str, bool, str, bool) # input path, success, result (output path or error msg), deleted
    batch_finished = pyqtSignal()
    
    def __init__(self, queue_items, has_gpu, max_concurrency=1):
        super().__init__()
        self.queue_items = queue_items
        self.has_gpu = has_gpu
        self.max_concurrency = max_concurrency
        
        self.pool = QThreadPool()
        self.pool.setMaxThreadCount(max_concurrency)
        
        self.active_runnables = []
        self.next_index = 0
        self.completed_count = 0
        self.total_count = len(queue_items)
        self._is_stopped = False
        
        # Track progress of all items: {path: current_progress_float}
        self.file_progress_map = {item['path']: 0.0 for item in queue_items}

    def start(self):
        self._schedule_next()

    def _schedule_next(self):
        if self._is_stopped:
            return

        while len(self.active_runnables) < self.max_concurrency and self.next_index < self.total_count:
            item = self.queue_items[self.next_index]
            self.next_index += 1
            
            runnable = FileConversionRunnable(item, self.has_gpu)
            runnable.signals.progress.connect(self._on_item_progress)
            runnable.signals.finished.connect(self._on_item_finished)
            
            self.active_runnables.append(runnable)
            
            self.file_started.emit(item['path'], self.next_index, self.total_count)
            self.pool.start(runnable)

        if self.completed_count == self.total_count:
            self.batch_finished.emit()

    def _on_item_progress(self, path, progress, pct_str, eta_str):
        if self._is_stopped: return
        
        # Update specific file progress
        self.file_progress_map[path] = progress
        
        # Calculate Global Progress
        # Sum of all progress / Total items
        total_progress_sum = sum(self.file_progress_map.values())
        global_progress = total_progress_sum / self.total_count if self.total_count > 0 else 0
        
        # We can use the ETA of the "slowest" or "current" file, but for batch it's complex.
        # Let's just show the ETA of the latest active file for liveness, or specific text.
        self.progress_updated.emit(global_progress, f"{int(global_progress*100)}%", f"Batch: {int(global_progress*100)}%")

    def _on_item_finished(self, path, success, result, deleted):
        if self._is_stopped: return

        # Ensure progress is 1.0 for finished items
        self.file_progress_map[path] = 1.0
        
        # Ensure UI errors don't kill the worker loop
        try:
            self.file_finished.emit(path, success, result, deleted)
        except Exception as e:
            logger.error(f"Error in UI handler for file_finished: {e}")
        
        # Remove from active list
        self.active_runnables = [r for r in self.active_runnables if r.item['path'] != path]
        
        self.completed_count += 1
        
        # Force update global progress
        total_progress_sum = sum(self.file_progress_map.values())
        global_progress = total_progress_sum / self.total_count if self.total_count > 0 else 0
        self.progress_updated.emit(global_progress, f"{int(global_progress*100)}%", f"Finished {self.completed_count}/{self.total_count}")

        self._schedule_next()

    def stop(self):
        self._is_stopped = True
        for r in self.active_runnables:
            r.stop()
        self.pool.clear()
        self.pool.waitForDone() # Wait for active ones to stop
