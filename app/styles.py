"""Desktop theme for the clinical workspace."""
APP_STYLE = """
QMainWindow, QWidget#centralWidget, QScrollArea, QWidget#workspace { background: #f4f7f9; }
QMessageBox, QInputDialog, QProgressDialog { background: #f4f7f9; color: #213547; }
QMessageBox QLabel, QInputDialog QLabel, QProgressDialog QLabel { color: #213547; background: transparent; }
QToolTip { background: #ffffff; color: #213547; border: 1px solid #c4d2da; padding: 6px; }
QPushButton#homeButton { background: transparent; border: 1px solid transparent; text-align: left; color: #586d7b; padding: 10px 14px; font-size: 13px; }
QPushButton#homeButton:hover { background: #f0f5f7; }
QPushButton[selected="true"] { background: #eaf5f2; color: #106b65; border-color: transparent; }
QPushButton#homeButton[selected="true"], QPushButton#dashboardCompactButton[selected="true"],
QPushButton#historyCompactButton[selected="true"], QPushButton#settingsButton[selected="true"] {
    background: #eaf5f2; color: #106b65; border-color: transparent;
}
QComboBox#homeQueueMode { background: white; color: #234653; border: 1px solid #d7e1e7; border-radius: 8px; padding: 5px 10px; }
QWidget { font-family: "Segoe UI"; font-size: 14px; color: #213547; }
QLabel { background: transparent; border: none; }
QPushButton {
    background: #ffffff; color: #304554; border: 1px solid #dce4e9;
    border-radius: 8px; padding: 8px 14px; font-size: 14px; font-weight: 600;
}
QPushButton:hover { background: #edf3f5; border-color: #c4d2da; }
QPushButton:pressed { background: #e1ebee; }
QPushButton:focus { border: 2px solid #16867d; }
QPushButton:disabled { color: #96a5af; background: #f0f4f6; border-color: #e4eaee; }
QFrame#sidebar { background: #ffffff; border: none; border-right: 1px solid #dfe7ec; }
QLabel#brandMark { background: #147d75; color: #ffffff; border-radius: 10px; font-size: 19px; font-weight: 700; }
QLabel#brandName { color: #173544; font-size: 16px; font-weight: 700; }
QLabel#brandSubtitle, QLabel#navSection, QLabel#versionLabel { color: #84949f; font-size: 11px; }
QLabel#navSection { font-weight: 600; padding-left: 12px; }
QLabel#navCurrent { color: #106b65; background: #eaf5f2; border-radius: 8px; padding: 12px 14px; font-weight: 600; }
QPushButton#displayCompactButton, QPushButton#dashboardCompactButton,
QPushButton#historyCompactButton, QPushButton#settingsButton, QPushButton#aboutButton {
    background: transparent; border: 1px solid transparent; text-align: left;
    color: #586d7b; padding: 10px 14px; border-radius: 8px; font-size: 13px;
}
QPushButton#displayCompactButton:hover, QPushButton#dashboardCompactButton:hover,
QPushButton#historyCompactButton:hover, QPushButton#settingsButton:hover, QPushButton#aboutButton:hover {
    background: #f0f5f7; color: #173544;
}
QLabel#titleLabel { color: #183644; font-size: 28px; font-weight: 700; }
QLabel#subtitleLabel { color: #788b97; font-size: 13px; }
QLabel#queueStatusActive, QLabel#queueStatusInactive { border-radius: 12px; padding: 4px 12px; font-size: 12px; font-weight: 600; }
QLabel#queueStatusActive { color: #157761; background: #e5f4ec; }
QLabel#queueStatusInactive { color: #71838d; background: #e8eef2; }
QPushButton#queueStartButton { background: #147d75; color: white; border: 1px solid #147d75; }
QPushButton#queueStartButton:hover { background: #106c65; }
QPushButton#queueStopButton { color: #a14a43; background: #ffffff; border: 1px solid #e3cbc8; }
QPushButton#queueStopButton:hover { color: #973b34; background: #fcf1ef; }
QFrame#timerPanel, QFrame#tvPanel { background: #ffffff; border: 1px solid #dfe7ec; border-radius: 12px; }
QLabel#panelEyebrow { font-size: 10px; font-weight: 600; color: #81929d; }
QLabel#patientTimerLabel { color: #8a9aa5; font-size: 19px; font-weight: 600; }
QLabel#patientTimerLabel[active="true"] { color: #234654; }
QLabel#patientTimerLabel[warning="true"] { color: #b34935; }
QPushButton#patientPauseButton { background: #f5f8f9; border: 1px solid #dfe7ec; color: #49616f; font-size: 12px; }
QPushButton#patientPauseButton:hover { background: #eaf1f3; }
QPushButton#patientPauseButton[paused="true"] { background: #fff7e8; border-color: #ecd5a7; color: #926b22; }
QPushButton#patientPauseButton:disabled { background: #f6f8f9; color: #a2afb8; }
QLabel#tvPanelTitle { color: #405a68; font-size: 12px; font-weight: 600; }
QLabel#tvAddress { color: #6c8290; font-size: 12px; }
QPushButton#copyTvButton { color: #356b70; background: #f8fbfb; font-size: 12px; padding: 6px 10px; }
QLabel#networkSummary { color: #8a9aa5; font-size: 11px; }
QLabel#networkSummary[connection="online"] { color: #478475; }
QLabel#networkSummary[connection="waiting"] { color: #9a7b3f; }
QLabel#networkSummary[connection="error"] { color: #b34935; }
QScrollArea { border: none; }
QScrollBar:vertical { background: transparent; width: 7px; margin: 2px; }
QScrollBar::handle:vertical { background: #cad7de; border-radius: 3px; min-height: 28px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
"""

DIALOG_STYLE = APP_STYLE + """
QDialog, QWidget#dashboardScrollContent, QWidget#dashboardFooter { background: #f4f7f9; }
QDialog QLabel { color: #405a68; }
QLabel#settingsTitle, QLabel#dashboardTitle, QLabel#historyTitle, QLabel#aboutTitle,
QLabel#passwordTitle { color: #183644; font-size: 26px; font-weight: 600; }
QLabel#settingsDescription, QLabel#aboutDescription, QLabel#aboutAuthor,
QLabel#passwordDescription, QLabel#historySummary, QLabel#patientDetailsHint,
QLabel#dashboardCardSubtitle { color: #667d89; font-size: 13px; }
QLabel#dashboardDoctor, QLabel#historyDoctor, QLabel#passwordDoctor,
QLabel#dashboardLastDate { color: #147d75; font-size: 18px; font-weight: 600; }
QLabel#settingsSection, QLabel#dashboardSection, QLabel#patientDetailsTitle {
    color: #526e7a; font-size: 12px; font-weight: 600; padding-top: 8px;
}
QLabel#settingsVersion, QLabel#aboutVersion { color: #667d89; font-size: 13px; }
QLineEdit, QSpinBox, QComboBox, QTextEdit, QPlainTextEdit {
    color: #213547; background: #ffffff; border: 1px solid #d7e1e7;
    border-radius: 8px; padding: 7px 10px; selection-background-color: #d7eee8;
    selection-color: #173d4c;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border: 1px solid #147d75; }
QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled { color: #748591; background: #eaf0f3; }
QComboBox QAbstractItemView { color: #213547; background: white; selection-background-color: #d7eee8; selection-color: #173d4c; }
QCheckBox { color: #405a68; spacing: 10px; }
QCheckBox::indicator { width: 18px; height: 18px; }
QFrame#dashboardCard, QFrame#dashboardAccentCard, QFrame#dashboardLastSession {
    background: white; border: 1px solid #dfe7ec; border-radius: 12px;
}
QFrame#dashboardCard, QFrame#dashboardAccentCard { min-height: 130px; }
QFrame#dashboardAccentCard { border-top: 3px solid #147d75; }
QLabel#dashboardCardTitle { color: #667d89; font-size: 13px; font-weight: 600; }
QLabel#dashboardCardValue { color: #183644; font-size: 30px; font-weight: 600; }
QLabel#dashboardQueueStatus { color: #667d89; font-size: 13px; }
QLabel#dashboardQueueStatus[active="true"] { color: #147d75; }
QTableWidget { color: #213547; background: white; alternate-background-color: #f4f7f9;
    border: 1px solid #dfe7ec; gridline-color: #e5ecef; border-radius: 8px; }
QTableWidget::item { padding: 8px; }
QTableWidget::item:selected { color: #173d4c; background: #d7eee8; }
QHeaderView, QTableCornerButton::section { background: #eaf0f3; }
QHeaderView::section { color: #405a68; background: #eaf0f3; border: none;
    border-bottom: 1px solid #d7e1e7; padding: 10px 8px; font-weight: 600; }
QPushButton#settingsSaveButton, QPushButton#dashboardPrimaryButton,
QPushButton#historyPrimaryButton, QPushButton#aboutCloseButton, QPushButton#primaryButton {
    background: #147d75; color: white; border: 1px solid #147d75;
}
QPushButton#settingsSaveButton:hover, QPushButton#dashboardPrimaryButton:hover,
QPushButton#historyPrimaryButton:hover, QPushButton#aboutCloseButton:hover,
QPushButton#primaryButton:hover { background: #106c65; }
QPushButton#settingsDeleteAccountButton, QPushButton#historyDangerButton {
    background: #fcf1ef; color: #a14a43; border: 1px solid #e3cbc8;
}
QPushButton#settingsDeleteAccountButton:hover, QPushButton#historyDangerButton:hover { background: #f6e4e0; }
QMessageBox QPushButton:default { background: #147d75; color: white; border-color: #147d75; }
"""


def apply_application_theme(app):
    """Use an explicit light palette even when Windows uses dark mode."""
    from PySide6.QtGui import QColor, QPalette
    app.setStyle('Fusion')
    palette = QPalette()
    colors = {'Window':'#f4f7f9', 'WindowText':'#213547', 'Base':'#ffffff',
              'AlternateBase':'#f4f7f9', 'Text':'#213547', 'Button':'#ffffff',
              'ButtonText':'#304554', 'Highlight':'#d7eee8', 'HighlightedText':'#173d4c',
              'ToolTipBase':'#ffffff', 'ToolTipText':'#213547', 'PlaceholderText':'#667d89',
              'Link':'#147d75'}
    for role, color in colors.items():
        palette.setColor(getattr(QPalette.ColorRole, role), QColor(color))
    for role in ('WindowText','Text','ButtonText'):
        palette.setColor(QPalette.ColorGroup.Disabled, getattr(QPalette.ColorRole,role), QColor('#748591'))
    app.setPalette(palette)
    app.setStyleSheet(DIALOG_STYLE)

REFINEMENT_STYLE = """
QPushButton#modeButton { background: #ffffff; color: #526e7a; border: 1px solid #d7e1e7; padding: 5px 12px; font-size: 13px; }
QPushButton#modeButton:checked { background: #147d75; color: white; border-color: #147d75; }
QComboBox#homeQueueMode:disabled { background: #edf2f4; color: #748591; border-color: #e0e7eb; }
QPushButton#modeButton:hover { border-color: #147d75; }
QPushButton#modeButton:checked:hover { background: #106c65; }
QLabel#settingsTitle, QLabel#dashboardTitle, QLabel#historyTitle { font-size: 28px; font-weight: 700; color: #183644; }
QLabel#dashboardDoctor, QLabel#historyDoctor { color: #667d89; font-size: 14px; font-weight: 400; }
QFrame#dashboardCard[prominence="primary"], QFrame#dashboardAccentCard[prominence="primary"] { background: white; border: 1px solid #dfe7ec; border-top: 3px solid #147d75; border-radius: 12px; min-height: 130px; }
QFrame#dashboardCard[prominence="secondary"], QFrame#dashboardAccentCard[prominence="secondary"] { background: #edf3f5; border: 1px solid #dfe7ec; border-radius: 12px; min-height: 94px; }
QFrame[prominence="secondary"] QLabel#dashboardCardValue { color: #526e7a; font-size: 23px; }
QFrame[prominence="primary"] QLabel#dashboardCardValue { color: #183644; font-size: 32px; }
QLabel#historyEmpty { background: white; color: #667d89; border: 1px solid #dfe7ec; border-radius: 12px; padding: 24px; font-size: 15px; }
QTableWidget::item { padding: 7px 10px; border-bottom: 1px solid #edf2f4; }
"""
APP_STYLE += REFINEMENT_STYLE
DIALOG_STYLE += REFINEMENT_STYLE
