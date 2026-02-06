"""
Modern glassmorphic dark theme stylesheet for Video Converter
"""

MODERN_THEME = """
/* ===== GLOBAL ===== */
QMainWindow {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #0f172a, stop:0.5 #1e293b, stop:1 #0f172a);
}

QWidget {
    color: #f1f5f9;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}

/* ===== TYPOGRAPHY ===== */
QLabel {
    color: #f1f5f9;
    background: transparent;
}

QLabel#title {
    font-size: 24px;
    font-weight: bold;
    color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #6366f1, stop:0.5 #a855f7, stop:1 #ec4899);
}

QLabel#subtitle {
    font-size: 13px;
    color: #94a3b8;
}

QLabel#section_header {
    font-size: 16px;
    font-weight: 600;
    color: #e2e8f0;
    margin-bottom: 8px;
}

QLabel#stat_value {
    font-size: 28px;
    font-weight: bold;
    color: #ffffff;
}

QLabel#stat_label {
    font-size: 11px;
    color: #94a3b8;
    font-weight: 500;
}

/* ===== BUTTONS ===== */
QPushButton {
    background: rgba(51, 65, 85, 0.4);
    border: 1px solid rgba(71, 85, 105, 0.3);
    border-radius: 8px;
    padding: 8px 16px;
    color: #f1f5f9;
    font-weight: 500;
    min-height: 32px;
}

QPushButton:hover {
    background: rgba(71, 85, 105, 0.5);
    border: 1px solid rgba(100, 116, 139, 0.5);
}

QPushButton:pressed {
    background: rgba(51, 65, 85, 0.6);
}

QPushButton:disabled {
    background: rgba(30, 41, 59, 0.3);
    color: #64748b;
    border: 1px solid rgba(51, 65, 85, 0.3);
}

QPushButton#primary {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #6366f1, stop:1 #a855f7);
    border: none;
    color: #ffffff;
    font-weight: 600;
    padding: 12px 24px;
}

QPushButton#primary:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #4f46e5, stop:1 #9333ea);
}

QPushButton#primary:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #4338ca, stop:1 #7e22ce);
}

QPushButton#primary:disabled {
    background: rgba(99, 102, 241, 0.3);
    color: rgba(255, 255, 255, 0.5);
}

QPushButton#secondary {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #8b5cf6, stop:1 #ec4899);
    border: none;
    color: #ffffff;
    font-weight: 600;
}

QPushButton#secondary:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #7c3aed, stop:1 #db2777);
}

QPushButton#danger {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #dc2626, stop:1 #ef4444);
    border: none;
    color: #ffffff;
}

QPushButton#danger:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #b91c1c, stop:1 #dc2626);
}

QPushButton#success {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #10b981, stop:1 #059669);
    border: none;
    color: #ffffff;
    font-weight: 600;
    font-size: 15px;
}

QPushButton#success:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #059669, stop:1 #047857);
}

QPushButton#icon_button {
    background: rgba(99, 102, 241, 0.1);
    border: 1px solid rgba(99, 102, 241, 0.3);
    color: #a5b4fc;
    border-radius: 6px;
    font-size: 16px;
    font-family: "Segoe UI Emoji", "Segoe UI Symbol", "Segoe UI";
    padding: 0;
}

QPushButton#icon_button:hover {
    background: rgba(99, 102, 241, 0.2);
    border: 1px solid rgba(99, 102, 241, 0.5);
    color: #c7d2fe;
}

QPushButton#icon_button:pressed {
    background: rgba(99, 102, 241, 0.3);
}

QPushButton#icon_button:disabled {
    background: rgba(71, 85, 105, 0.1);
    border: 1px solid rgba(71, 85, 105, 0.2);
    color: #64748b;
}

QPushButton#danger_icon_button {
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.3);
    color: #fca5a5;
    border-radius: 6px;
    font-size: 16px;
    font-family: "Segoe UI Emoji", "Segoe UI Symbol", "Segoe UI";
    padding: 0; 
}

QPushButton#danger_icon_button:hover {
    background: rgba(239, 68, 68, 0.2);
    border: 1px solid rgba(239, 68, 68, 0.5);
    color: #fecaca;
}

QPushButton#danger_icon_button:pressed {
    background: rgba(239, 68, 68, 0.3);
}

/* ===== CONTAINERS ===== */
QFrame {
    background: transparent;
    border: none;
}

QFrame#card {
    background: rgba(30, 41, 59, 0.4);
    border: 1px solid rgba(71, 85, 105, 0.3);
    border-radius: 12px;
    padding: 16px;
}

QFrame#stat_card {
    background: rgba(30, 41, 59, 0.4);
    border: 1px solid rgba(71, 85, 105, 0.3);
    border-radius: 12px;
    padding: 12px;
}

QFrame#info_panel {
    background: rgba(30, 41, 59, 0.3);
    border: 1px solid rgba(71, 85, 105, 0.2);
    border-radius: 8px;
    padding: 12px;
}

QGroupBox {
    background: rgba(30, 41, 59, 0.3);
    border: 1px solid rgba(71, 85, 105, 0.3);
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: 600;
    color: #e2e8f0;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 4px 8px;
    color: #e2e8f0;
}

/* ===== INPUTS ===== */
QLineEdit {
    background: rgba(15, 23, 42, 0.5);
    border: 1px solid rgba(71, 85, 105, 0.3);
    border-radius: 6px;
    padding: 8px;
    color: #f1f5f9;
    selection-background-color: #6366f1;
}

QLineEdit:focus {
    border: 1px solid #6366f1;
}

QSpinBox {
    background: rgba(15, 23, 42, 0.5);
    border: 1px solid rgba(71, 85, 105, 0.3);
    border-radius: 6px;
    padding: 6px;
    color: #f1f5f9;
    min-width: 60px;
}

QSpinBox:focus {
    border: 1px solid #6366f1;
}

QSpinBox::up-button, QSpinBox::down-button {
    background: rgba(71, 85, 105, 0.3);
    border: none;
    width: 16px;
}

QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background: rgba(99, 102, 241, 0.5);
}

QComboBox {
    background: rgba(15, 23, 42, 0.5);
    border: 1px solid rgba(71, 85, 105, 0.3);
    border-radius: 6px;
    padding: 6px 12px;
    color: #f1f5f9;
    min-width: 120px;
}

QComboBox:hover {
    border: 1px solid #6366f1;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    background: #1e293b;
    border: 1px solid rgba(71, 85, 105, 0.5);
    selection-background-color: #6366f1;
    color: #f1f5f9;
    outline: none;
}

/* ===== RADIO BUTTONS ===== */
QRadioButton {
    color: #e2e8f0;
    spacing: 8px;
}

QRadioButton::indicator {
    width: 18px;
    height: 18px;
    border-radius: 9px;
    border: 2px solid #64748b;
    background: rgba(15, 23, 42, 0.5);
}

QRadioButton::indicator:hover {
    border: 2px solid #a855f7;
}

QRadioButton::indicator:checked {
    background: qradialgradient(cx:0.5, cy:0.5, radius:0.5,
        fx:0.5, fy:0.5, stop:0 #a855f7, stop:0.5 #a855f7, stop:0.6 rgba(0,0,0,0));
    border: 2px solid #a855f7;
}

/* ===== CHECKBOXES ===== */
QCheckBox {
    color: #e2e8f0;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid #64748b;
    background: rgba(15, 23, 42, 0.5);
}

QCheckBox::indicator:hover {
    border: 2px solid #a855f7;
}

QCheckBox::indicator:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #8b5cf6, stop:1 #a855f7);
    border: 2px solid #a855f7;
}

/* ===== LIST WIDGET ===== */
QListWidget {
    background: rgba(15, 23, 42, 0.3);
    border: 1px solid rgba(71, 85, 105, 0.3);
    border-radius: 8px;
    outline: none;
    padding: 4px;
}

QListWidget::item {
    background: rgba(30, 41, 59, 0.4);
    border: 1px solid rgba(71, 85, 105, 0.2);
    border-radius: 8px;
    padding: 4px;
    margin: 3px;
}

QListWidget::item:hover {
    background: rgba(51, 65, 85, 0.5);
    border: 1px solid rgba(99, 102, 241, 0.3);
}

QListWidget::item:selected {
    background: rgba(99, 102, 241, 0.2);
    border: 1px solid rgba(99, 102, 241, 0.5);
}

/* ===== PROGRESS BAR ===== */
QProgressBar {
    background: rgba(15, 23, 42, 0.5);
    border: 1px solid rgba(71, 85, 105, 0.3);
    border-radius: 8px;
    text-align: center;
    color: #ffffff;
    font-weight: 600;
    height: 24px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #10b981, stop:1 #059669);
    border-radius: 7px;
}

QProgressBar#converting::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #3b82f6, stop:1 #2563eb);
}

QProgressBar#pending::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #f59e0b, stop:1 #d97706);
}

/* ===== SCROLLBAR ===== */
QScrollBar:vertical {
    background: rgba(15, 23, 42, 0.3);
    width: 12px;
    border-radius: 6px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: rgba(100, 116, 139, 0.5);
    border-radius: 6px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: rgba(148, 163, 184, 0.7);
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background: rgba(15, 23, 42, 0.3);
    height: 12px;
    border-radius: 6px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background: rgba(100, 116, 139, 0.5);
    border-radius: 6px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background: rgba(148, 163, 184, 0.7);
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* ===== STATUS BADGES ===== */
QLabel#badge {
    border-radius: 6px;
    padding: 4px 12px;
    font-size: 11px;
    font-weight: 600;
}

QLabel#badge_pending {
    background: rgba(245, 158, 11, 0.2);
    border: 1px solid rgba(245, 158, 11, 0.4);
    color: #fbbf24;
}

QLabel#badge_converting {
    background: rgba(59, 130, 246, 0.2);
    border: 1px solid rgba(59, 130, 246, 0.4);
    color: #60a5fa;
}

QLabel#badge_complete {
    background: rgba(16, 185, 129, 0.2);
    border: 1px solid rgba(16, 185, 129, 0.4);
    color: #34d399;
}

QLabel#badge_error {
    background: rgba(239, 68, 68, 0.2);
    border: 1px solid rgba(239, 68, 68, 0.4);
    color: #f87171;
}

QLabel#badge_gpu {
    background: rgba(168, 85, 247, 0.2);
    border: 1px solid rgba(168, 85, 247, 0.4);
    color: #c084fc;
}

QLabel#badge_online {
    background: rgba(16, 185, 129, 0.2);
    border: 1px solid rgba(16, 185, 129, 0.4);
    color: #34d399;
}
"""

def get_custom_stylesheet(accent_color="#6366f1"):
    """Backward compatibility wrapper - returns MODERN_THEME"""
    return MODERN_THEME

