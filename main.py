# main.py
"""
Main - Main Application Entry Point
"""
import sys
from PyQt5.QtWidgets import QApplication, QPushButton
from main_window import MainWindow
from PyQt5.QtGui import QIcon, QPixmap, QPalette, QColor
from PyQt5.QtCore import  Qt, QTimer

from style_manager import apply_theme
from PyQt5.QtWidgets import QProxyStyle, QStyle, QStyleOptionMenuItem
from PyQt5.QtCore import QRect
from single_instance import ensure_single_instance
import app_info
APP_ORG = app_info.APP_ORGANIZATION
APP_NAME = app_info.APP_NAME
APP_VER = app_info.APP_VERSION
APP_AUT = app_info.APP_AUTHOR

def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_ORG)
    app.setApplicationVersion(APP_VER)


    app.setWindowIcon(QIcon("icons/ayntexlogo.svg"))    
    
    # Must be called after QApplication but before showing the window
    _instance_guard = ensure_single_instance(app_info.APP_NAME)

    # Wire up "open file from second instance" if your app supports it
    def _on_args_received(args: list):
        if args and os.path.isfile(args[0]):
            main_window.editor_manager.open_specific_file(args[0])
        main_window.raise_()          # bring window to front
        main_window.activateWindow()

    _instance_guard.args_received.connect(_on_args_received)
    
    
    
    main_window = MainWindow()

    # After QApplication is created and config is loaded:
    saved_theme = main_window.config_manager.get_config_value('ui', 'app_theme', 'default')
    apply_theme(app, saved_theme)
    
    main_window.show()
    main_window.showMaximized()
    
    # Keep _instance_guard alive for the whole session
    app.aboutToQuit.connect(_instance_guard.close)

    
    sys.exit(app.exec_())
    
if __name__ == "__main__":
    main()