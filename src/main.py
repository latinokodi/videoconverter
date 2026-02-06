import sys
from PyQt6.QtWidgets import QApplication
from qt_material import apply_stylesheet
from .utils.logger import logger
from .utils.config import config
from .ui.main_window_qt import MainWindow

def main():
    logger.info("Starting Video Converter App (PyQt6)")
    
    # Initialize Config
    config.load()
    
    # Initialize App
    # Set App User Model ID for taskbar icon
    # Set App User Model ID for taskbar icon
    from .utils.platform_integration import set_app_user_model_id
    set_app_user_model_id('mycompany.videoconverter.hevc.1.0')

    app = QApplication(sys.argv)
    
    # Apply Theme
    # 'dark_teal.xml', 'dark_cyan.xml', 'dark_medical.xml' are good options.
    # We can check config for theme preference or default to dark_teal
    theme = "dark_teal.xml"
    apply_stylesheet(app, theme=theme)
    
    # Custom Overrides
    from .ui.theme import get_custom_stylesheet
    app.setStyleSheet(app.styleSheet() + get_custom_stylesheet())
    
    # Create Main Window
    window = MainWindow()
    window.show()
    
    # Run
    try:
        sys.exit(app.exec())
    except Exception as e:
        logger.critical(f"Application crashed: {e}")
        raise

if __name__ == "__main__":
    main()
