import sys
import os

# Add current directory to path so we can import src
sys.path.append(os.getcwd())

try:
    print("Verifying imports...")
    import src.main
    import src.ui.main_window
    from src.core.converter import Converter
    from src.utils.logger import logger
    from src.utils.config import config
    
    print("Imports successful.")
    
    # Check if config loads
    config.load()
    print(f"Config loaded. Theme: {config.get('theme')}")
    
    # Check logger
    logger.info("Verification script: Logger working.")
    
    print("Verification passed!")
except ImportError as e:
    print(f"Verification FAILED: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Verification FAILED with error: {e}")
    sys.exit(1)
