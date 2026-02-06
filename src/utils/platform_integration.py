import sys
import ctypes

def set_app_user_model_id(app_id: str):
    """
    Sets the App User Model ID on Windows.
    This is necessary for the taskbar icon to group correctly and show the custom icon.
    """
    if sys.platform != 'win32':
        return

    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass
