
import time
import psutil
import pynvml
from PyQt6.QtCore import QThread, pyqtSignal
from ..utils.logger import logger

class HardwareMonitorWorker(QThread):
    # Signal emits (cpu_percent, gpu_percent_or_none, video_engine_percent_or_none)
    metrics_updated = pyqtSignal(float, object, object)

    def __init__(self):
        super().__init__()
        self._is_running = True
        self.gpu_handle = None
        self.has_nvidia = False
        
        # Initialize NVIDIA management library
        try:
            pynvml.nvmlInit()
            device_count = pynvml.nvmlDeviceGetCount()
            if device_count > 0:
                self.gpu_handle = pynvml.nvmlDeviceGetHandleByIndex(0) # Monitor primary GPU
                self.has_nvidia = True
                logger.info(f"NVIDIA GPU monitoring initialized: {pynvml.nvmlDeviceGetName(self.gpu_handle)}")
        except Exception as e:
            logger.warning(f"Could not initialize NVIDIA monitoring: {e}")
            self.has_nvidia = False

    def run(self):
        while self._is_running:
            try:
                # CPU Usage (blocking call if interval is used, but we use sleep)
                cpu = psutil.cpu_percent(interval=None)
                
                gpu_util = None
                video_util = None
                
                if self.has_nvidia and self.gpu_handle:
                    try:
                        utilization = pynvml.nvmlDeviceGetUtilizationRates(self.gpu_handle)
                        gpu_util = float(utilization.gpu)
                        
                        # NVML doesn't explicitly separate 'Video Engine' (NVENC/DEC) in simple utilization struct
                        # usually 'gpu' covers compute/graphics. 
                        # For now, we return gpu_util. 
                        # Advanced metrics (Encoder utilization) require `nvmlDeviceGetEncoderUtilization`
                        
                        try:
                            # Try retrieving Encoder utilization specifically
                            encoder_util_tuple = pynvml.nvmlDeviceGetEncoderUtilization(self.gpu_handle)
                            # encoder_util_tuple is (utilization, samplingPeriodUs)
                            video_util = float(encoder_util_tuple[0])
                        except Exception:
                            # Fallback if unsupported on specific driver/card
                            video_util = None
                            
                    except Exception as e:
                        logger.debug(f"Error reading GPU stats: {e}")
                
                self.metrics_updated.emit(cpu, gpu_util, video_util)
                
            except Exception as e:
                logger.error(f"Hardware Monitor Error: {e}")
            
            # Sleep 1s
            for _ in range(10): 
                if not self._is_running: break
                time.sleep(0.1)

    def stop(self):
        self._is_running = False
        self.wait()
        try:
            if self.has_nvidia:
                pynvml.nvmlShutdown()
        except:
            pass
