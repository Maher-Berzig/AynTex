# menu_manager.py
"""
Menu Manager - Handles menu bar creation and management
"""
import os
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QMenu,
    QComboBox, QLabel, QTextEdit, QListWidget, QWidgetAction,
    QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox,  
    QSplitter, QGroupBox, QScrollArea, QMessageBox,
    QApplication,  QAction, QDialog, QFrame,
    QSizePolicy, QFileDialog, QDialogButtonBox,
    QToolBar, QToolButton, QButtonGroup, QRadioButton
)
from PyQt5.QtGui import QPixmap, QFont, QKeySequence, QIcon, QPixmap, QPainter, QCursor
from PyQt5.QtCore import Qt, QTimer
from math_symbols_menu import MathSymbolsMenu
from latex_commands_menu import LatexCommandsMenu
from icons_manager import IconsManager
from pdf_viewer import PDFViewer
from errors_manager import ErrorsManager
from settings_manager import SettingsManager
from typing import Any, Dict, List
try:
    from pdf_comparison import PDFComparisonViewerSimplified
    PDF_COMPARISON_AVAILABLE = True
except ImportError:
    PDF_COMPARISON_AVAILABLE = False
    PDFComparisonViewer = None
    #print("Warning: pdf_comparison module not found. PDF comparison features will be disabled.")
from PyQt5.QtCore import QObject, QEvent





from PyQt5.QtWidgets import (
    QDialog, QHBoxLayout, QVBoxLayout,
    QTextEdit, QPushButton
)

from PyQt5.QtGui import QTextOption, QTextBlockFormat, QTextCursor


from PyQt5.QtWidgets import (
    QDialog, QHBoxLayout, QVBoxLayout,
    QTextEdit, QPushButton
)
from PyQt5.QtGui import QFont, QTextCursor
from PyQt5.QtGui import QTextCursor, QTextBlockFormat



# Add this class at the top of menu_manager.py
from PyQt5.QtWidgets import QProxyStyle, QStyle
from PyQt5.QtCore import Qt



class RTLMenuStyle(QProxyStyle):
    """
    Fixes two RTL menu bugs in Qt:
    1. Submenus open on wrong side (right instead of left)
    2. Icon column appears on wrong side
    
    Works by overriding only the two relevant style hints.
    Does NOT touch layout direction anywhere.
    """
    def __init__(self, is_rtl=False):
        super().__init__()
        self.is_rtl = is_rtl

    def styleHint(self, hint, option=None, widget=None, returnData=None):
        if self.is_rtl:
            # Force submenus to open on the LEFT side
            if hint == QStyle.SH_Menu_SubMenuPopupDelay:
                return 0
            if hint == QStyle.SH_Menu_Scrollable:
                return 1
        return super().styleHint(hint, option, widget, returnData)

    def pixelMetric(self, metric, option=None, widget=None):
        return super().pixelMetric(metric, option, widget)


    def drawPrimitive(self, element, option, painter, widget=None):
        # Suppress the check indicator box — icon swapping handles it instead
        if self.is_rtl and element == QStyle.PE_IndicatorMenuCheckMark:
            return  # draw nothing, icon does the job
        super().drawPrimitive(element, option, painter, widget)


    def drawControl(self, element, option, painter, widget=None):
        if self.is_rtl and element == QStyle.CE_MenuScroller:
            return
        # Strip the checked-item sunken frame
        if self.is_rtl and element == QStyle.CE_MenuItem:
            from PyQt5.QtWidgets import QStyleOptionMenuItem
            if isinstance(option, QStyleOptionMenuItem):
                if option.checkType != QStyleOptionMenuItem.NotCheckable:
                    # Remove the "checked" flag before passing to native drawing
                    # so Qt skips drawing the sunken box around the icon
                    option.state &= ~QStyle.State_On
        super().drawControl(element, option, painter, widget)

class DoubleLanguagesInsertion(QDialog):
    def __init__(self, parent=None, lang="en"):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)   
        self.main_window = parent
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]                            

        self.setWindowTitle(tr["bilingual_insert"])
        self.setMinimumSize(600, 300)

        self.editor = None

        layout = QHBoxLayout(self)

        # ---------------- LEFT (natural behavior) ----------------
        left_layout = QVBoxLayout()

        self.left_text = QTextEdit()
        self.left_text.setFont(QFont("Noto Sans", 11))

        self.insert_left_btn = QPushButton("Insert")
        self.insert_left_btn.clicked.connect(self.insert_left)

        left_layout.addWidget(self.left_text)
        left_layout.addWidget(self.insert_left_btn)

        # ---------------- RIGHT (same editor, cursor starts right) ----------------
        right_layout = QVBoxLayout()

        self.right_text = QTextEdit()
        self.right_text.setFont(QFont("Noto Sans", 11))  # same behavior

        # Push cursor to the right ONLY when empty & focused
        self.right_text.focusInEvent = self._right_focus_in_event

        self.insert_right_btn = QPushButton("أدرج")
        self.insert_right_btn.clicked.connect(self.insert_right)

        right_layout.addWidget(self.right_text)
        right_layout.addWidget(self.insert_right_btn)

        layout.addLayout(left_layout)
        layout.addLayout(right_layout)

    # ------------------------------------------------------------
    # Editor setter
    # ------------------------------------------------------------
    def set_editor(self, editor):
        self.editor = editor

    # ------------------------------------------------------------
    # Right editor behavior
    # ------------------------------------------------------------
    def _right_focus_in_event(self, event):
        QTextEdit.focusInEvent(self.right_text, event)

        if not self.right_text.toPlainText():
            cursor = self.right_text.textCursor()

            block = QTextBlockFormat()
            block.setLayoutDirection(Qt.RightToLeft)

            cursor.setBlockFormat(block)
            self.right_text.setTextCursor(cursor)
    # ------------------------------------------------------------
    # Insert actions
    # ------------------------------------------------------------
    def insert_left(self):
        if self.editor:
            text = self.left_text.toPlainText().strip()
            if text:
                cursor = self.editor.textCursor()
                cursor.insertText(text)
                self.editor.setFocus()
                self.left_text.clear()

    def insert_right(self):
        if self.editor:
            text = self.right_text.toPlainText().strip()
            if text:
                cursor = self.editor.textCursor()
                cursor.insertText(text)
                self.editor.setFocus()
                self.right_text.clear()



                
class TooltipBlockFilter(QObject):
    """Event filter that blocks all tooltip events application-wide"""
    def eventFilter(self, obj, event):
        if event.type() == QEvent.ToolTip:
            return True  # Block the tooltip
        return super().eventFilter(obj, event)

class MenuManager:
    def __init__(self, main_window):
        self.main_window = main_window
        self.icons_manager = IconsManager()
        self.math_menu_builder = MathSymbolsMenu(
            main_window,
            main_window.editor_manager.insert_latex,
            main_window.menu_language
        )
        self.latex_commands_menu_builder = LatexCommandsMenu(
            main_window,
            main_window.editor_manager.insert_latex,
            main_window.menu_language
        )
        self.search_replace_dialog = None
        self.recent_files_menu = None  # Will be created

    def _setup_menu_close_protection(self):
        """Protect against stray clicks after a menu action is triggered."""
        from PyQt5.QtCore import QTimer
        from PyQt5.QtWidgets import QToolBar

        self._menu_close_timer = QTimer()
        self._menu_close_timer.setSingleShot(True)
        self._menu_close_timer.timeout.connect(self._reenable_toolbars)

        # Connect each top-level menu's triggered signal
        for action in self.main_window.menuBar().actions():
            menu = action.menu()
            if menu:
                menu.triggered.connect(self._on_menu_action_triggered)

    def _on_menu_action_triggered(self, action):
        """Called when any action in a menu is actually triggered (clicked)."""
        # Disable all toolbars briefly
        for tb in self.main_window.findChildren(QToolBar):
            tb.setEnabled(False)
        self._menu_close_timer.start(150)

    def _reenable_toolbars(self):
        """Re-enable toolbars after the protection period."""
        for tb in self.main_window.findChildren(QToolBar):
            tb.setEnabled(True)
            
    def create_menu_bar(self):
        """Create the entire menu bar (called once)"""
        if self.main_window.menus_initialized:
            return
        # Clear existing menus
        menu_bar = self.main_window.menuBar()
        menu_bar.clear()
        # Set layout direction BEFORE creating any menus
        lang = self.main_window.menu_language
        is_rtl = (lang == "ar")
        direction = Qt.RightToLeft if is_rtl else Qt.LeftToRight
        menu_bar.setLayoutDirection(direction)
        self.main_window.is_rtl = is_rtl
        # ✅ NEW: Update language in menu builders BEFORE creating menus
        self.math_menu_builder.menu_language = lang
        self.latex_commands_menu_builder.menu_language = lang 
        # ✅ ADD THESE TWO LINES to rebuild with correct language
        self.math_menu_builder.build_symbol_categories()
        self.latex_commands_menu_builder.build_commands_categories()        
        # Apply UI font to menu bar
        current_fonts = self.main_window.get_current_font_settings()
        ui_font_family = current_fonts.get('ui_font_family', 'Arial')
        ui_font_size = current_fonts.get('toolbar_font_size', 10)
        menu_font = QFont(ui_font_family, ui_font_size)
        menu_bar.setFont(menu_font)
        # Create menus with mnemonics (Alt + underlined letter)
        self._create_file_menu()    # → Alt+F
        self._create_edit_menu()    # → Alt+E
        self._create_view_menu()    # → Alt+V
        self._create_tools_menu()    # → Alt+T
        self._create_latex_menu()   # → Alt+L
        self._create_options_menu() # → Alt+O
        self._create_help_menu()    # → Alt+H
        self.main_window.menus_initialized = True
        # Apply RTL and font to all menus AFTER creation
        self._apply_menu_font_and_direction(menu_font)
        # Ensure visibility
        menu_bar.setVisible(True)
        menu_bar.show()
        
        self._setup_menu_close_protection()


    def _make_rtl_checkable(self, action, checked_icon="checked", unchecked_icon="unchecked"):
        """
        Replace Qt's broken RTL check indicator with icon swapping.
        Works because the icon column renders correctly in RTL.
        """
        def _update_icon(checked):
            icon_name = checked_icon if checked else unchecked_icon
            self.icons_manager.apply_icon_to_action(action, icon_name)

        # Set initial icon
        _update_icon(action.isChecked())
        # Keep it in sync on every toggle
        action.toggled.connect(_update_icon)
    
    # def _apply_menu_font_and_direction(self, font):
        # """
        # CLEAN VERSION - only QApplication gets direction.
        # No setLayoutDirection on any QMenu or QMenuBar children.
        # RTLMenuStyle handles submenu popup side and icon placement.
        # """
        # lang = self.main_window.menu_language
        # is_rtl = (lang == "ar")
        # direction = Qt.RightToLeft if is_rtl else Qt.LeftToRight

        # # ✅ ONLY set direction here — nowhere else
        # app = QApplication.instance()
        # if app:
            # app.setLayoutDirection(direction)
            # # Apply RTL style fix to the entire application
            # app.setStyle(RTLMenuStyle(is_rtl=is_rtl))

        # menu_bar = self.main_window.menuBar()
        # menu_bar.setFont(font)

        # # ONLY apply font — no setLayoutDirection on any menu
        # for menu in menu_bar.findChildren(QMenu):
            # menu.setFont(font)
            # for action in menu.actions():
                # action.setFont(font)


    def _apply_menu_font_and_direction(self, font):
        lang = self.main_window.menu_language
        is_rtl = (lang == "ar")
        direction = Qt.RightToLeft if is_rtl else Qt.LeftToRight

        app = QApplication.instance()
        if app:
            app.setLayoutDirection(direction)
            app.setStyle(RTLMenuStyle(is_rtl=is_rtl))

            # Tell style_manager whether RTL menu CSS is needed,
            # then re-apply the current theme — it will append RTL CSS automatically
            import style_manager
            style_manager.set_rtl_menu_active(is_rtl)
            current_theme = getattr(self.main_window, 'app_theme', 'default')
            style_manager.apply_theme(app, current_theme)

        menu_bar = self.main_window.menuBar()
        menu_bar.setFont(font)
        for menu in menu_bar.findChildren(QMenu):
            menu.setFont(font)
            for action in menu.actions():
                action.setFont(font)
            

    def update_menu_font(self):
        """Update font on existing menus without recreating them"""
        current_fonts = self.main_window.get_current_font_settings()
        ui_font_family = current_fonts.get('ui_font_family', 'Arial')
        ui_font_size = current_fonts.get('toolbar_font_size', 10)
        menu_font = QFont(ui_font_family, ui_font_size)
        self._apply_menu_font_and_direction(menu_font)            

    def _create_file_menu(self):
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]
        file_menu = self.main_window.menuBar().addMenu("&"+tr["file_menu"])
        # New
        new_action = QAction(tr["new"], self.main_window)
        new_action.setShortcut("Ctrl+N")
        new_action.setStatusTip(tr["new"])   # ✅ Status tip
        new_action.triggered.connect(self.main_window.editor_manager.new_file)
        self.icons_manager.apply_icon_to_action(new_action, "new")
        file_menu.addAction(new_action)
        file_menu.addSeparator()
        # Open
        open_action = QAction(tr["open"], self.main_window)
        open_action.setShortcut("Ctrl+O")
        open_action.setStatusTip(tr["open"])   # ✅ Status tip
        open_action.triggered.connect(self.main_window.editor_manager.open_file)
        self.icons_manager.apply_icon_to_action(open_action, "open")
        file_menu.addAction(open_action)
        # Open PDF
        open_pdf_action = QAction(tr["open_pdf"], self.main_window)
        open_pdf_action.setShortcut("Ctrl+Shift+O")
        open_pdf_action.setStatusTip(tr["open_pdf"])   # ✅ Status tip
        open_pdf_action.triggered.connect(self.main_window.pdf_manager.open_pdf_file)
        self.icons_manager.apply_icon_to_action(open_pdf_action, "pdf")
        file_menu.addAction(open_pdf_action)
        file_menu.addSeparator()
        # Recent Files
        self._create_recent_files_menu(file_menu)
        file_menu.addSeparator()
        # Create the submenu
        self.recent_pdf_files_menu = file_menu.addMenu(
            tr.get("recent_pdf_files", "Recent PDF Files")
        )
        # Populate it immediately
        self.update_recent_pdf_files_menu()
        file_menu.addSeparator()          
        # Save
        save_action = QAction(tr["save"]+"\tCtrl+S", self.main_window)
        save_action.setShortcut("Ctrl+S")
        save_action.setStatusTip(tr["save"])   # ✅ Status tip
        save_action.triggered.connect(self.main_window.editor_manager.save_file)
        self.icons_manager.apply_icon_to_action(save_action, "save")
        file_menu.addAction(save_action)
        # Save As
        save_as_action = QAction(tr["save_as"], self.main_window)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.setStatusTip(tr["save_as"])   # ✅ Status tip
        save_as_action.triggered.connect(self.main_window.editor_manager.save_as_file)
        self.icons_manager.apply_icon_to_action(save_as_action, "save_as")
        file_menu.addAction(save_as_action)
        # Save a Copy As
        save_copy_action = QAction(tr.get("save_copy_as", "Save a Copy As..."), self.main_window)
        save_copy_action.setShortcut("Ctrl+Shift+C")           # optional, but distinct
        save_copy_action.setStatusTip(tr.get("save_copy_as", "Save a copy of the current document under a new name"))
        save_copy_action.setToolTip(tr.get("tooltip_save_copy_as", "Save a copy without changing the active file"))
        save_copy_action.triggered.connect(self.main_window.editor_manager.save_copy_as)
        self.icons_manager.apply_icon_to_action(save_copy_action, "save_copy_as")   # you may need a dedicated icon
        file_menu.addAction(save_copy_action)
        file_menu.addSeparator()
        # ── Master Document ───────────────────────────────────────────────
        self.set_master_action = QAction(
            tr.get("set_master_document", "Set as Master Document"),
            self.main_window
        )
        self.set_master_action.setStatusTip(
            tr.get("status_set_master_document",
                   "Mark the active .tex file as the master document for compilation")
        )
        self.icons_manager.apply_icon_to_action(self.set_master_action, "flag")
        self.set_master_action.triggered.connect(self._set_master_document)
        file_menu.addAction(self.set_master_action)

        self.clear_master_action = QAction(
            tr.get("clear_master_document", "Clear Master Document"),
            self.main_window
        )
        self.clear_master_action.setStatusTip(
            tr.get("status_clear_master_document",
                   "Remove master document designation — compile the foreground file instead")
        )
        #self.icons_manager.apply_icon_to_action(self.clear_master_action, "clear_master")
        self.clear_master_action.triggered.connect(self._clear_master_document)
        file_menu.addAction(self.clear_master_action)

        # Keep action states fresh whenever the File menu opens
        file_menu.aboutToShow.connect(self._update_master_actions_state)
        self._update_master_actions_state()   # set initial state
        # ─────────────────────────────────────────────────────────────────
        file_menu.addSeparator()        
        # Close Tex File
        close_tex_action = QAction(tr["close_tex"], self.main_window)
        close_tex_action.setShortcut("Ctrl+Q")
        close_tex_action.setStatusTip(tr["close_tex"])   # ✅ Status tip
        close_tex_action.triggered.connect(self.main_window.editor_manager.close_current_file)
        self.icons_manager.apply_icon_to_action(close_tex_action, "close_tex")
        file_menu.addAction(close_tex_action)
        # Close PDF File
        close_pdf_action = QAction(tr["close_pdf"], self.main_window)
        close_pdf_action.setShortcut("Ctrl+Shift+Q")
        close_pdf_action.setStatusTip(tr["close_pdf"])   # ✅ Status tip
        close_pdf_action.triggered.connect(self.main_window.pdf_manager.close_current_pdf)
        self.icons_manager.apply_icon_to_action(close_pdf_action, "close_pdf")
        file_menu.addAction(close_pdf_action)
        file_menu.addSeparator()
        # Save all
        save_all_action = QAction(tr["save_all"], self.main_window)    
        save_all_action.setStatusTip(tr["save_all"])   # ✅ Status tip
        save_all_action.triggered.connect(self.main_window.editor_manager.save_all)
        self.icons_manager.apply_icon_to_action(save_all_action, "save_all")
        file_menu.addAction(save_all_action)
        # ✅ Add to main window to ensure global scope
        self.main_window.addAction(save_all_action)
        # Close All Tex Files
        close_all_tex_action = QAction(tr["close_all_tex"], self.main_window)        
        close_all_tex_action.setStatusTip(tr["close_all_tex"])   # ✅ Status tip
        close_all_tex_action.triggered.connect(self.main_window.editor_manager.close_all_files)
        self.icons_manager.apply_icon_to_action(close_all_tex_action, "close_all_tex")
        file_menu.addAction(close_all_tex_action)        
        # Close All PDF Files
        close_all_pdf_action = QAction(tr["close_all_pdf"], self.main_window)
        #close_all_pdf_action.setShortcut("Ctrl+Shift+Q")
        close_all_pdf_action.setStatusTip(tr["close_all_pdf"])   # ✅ Status tip
        close_all_pdf_action.triggered.connect(self.main_window.pdf_manager.close_all_pdfs)
        self.icons_manager.apply_icon_to_action(close_all_pdf_action, "close_all_pdf")
        file_menu.addAction(close_all_pdf_action)
        file_menu.addSeparator()
        # Exit
        exit_action = QAction(tr["exit"], self.main_window)
        exit_action.setStatusTip(tr["exit"])   # ✅ Status tip        
        exit_action.setText(f'{tr["exit"]}\tAlt+F4')
        exit_action.triggered.connect(self.main_window.close)
        self.icons_manager.apply_icon_to_action(exit_action, "exit")
        file_menu.addAction(exit_action)
        
        self._setup_menu_close_protection()


    def _create_recent_files_menu(self, parent_menu):
        """Create Recent Files submenu"""
        lang = self.main_window.menu_language
        self.recent_files_menu = parent_menu.addMenu(            
            self.main_window.translations[lang].get("recent_files", "Recent Files")
        )
        self.update_recent_files_menu()  # Populate it


    
    def create_number_icon(self, number):
        from PyQt5.QtGui import QPixmap, QPainter, QIcon, QFont
        from PyQt5.QtCore import Qt

        size = 18
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        try:
            painter.setRenderHint(QPainter.Antialiasing)

            # Set visible color
            painter.setPen(Qt.black)

            # Adjust font size
            font = QFont()
            font.setBold(True)
            font.setPointSize(8)
            painter.setFont(font)

            painter.drawText(pixmap.rect(), Qt.AlignCenter, str(number))
        finally:
            painter.end()

        return QIcon(pixmap)

    def update_recent_files_menu(self):
        """Update the recent files menu with current list — single scrollable column"""
        if not self.recent_files_menu:
            return

        self.recent_files_menu.clear()
        lang = self.main_window.menu_language

        if not hasattr(self.main_window, 'config_manager'):
            return

        recent_files = self.main_window.config_manager.get_recent_files()

        if not recent_files:
            no_files_action = QAction(
                self.main_window.translations[lang].get("no_recent_files", "No recent files"),
                self.main_window
            )
            no_files_action.setEnabled(False)
            self.recent_files_menu.addAction(no_files_action)
            return

        # --- Scrollable container widget ---
        from PyQt5.QtWidgets import (
            QScrollArea, QWidget, QVBoxLayout,
            QToolButton, QWidgetAction, QSizePolicy
        )
        from PyQt5.QtCore import Qt

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(2, 2, 2, 2)
        scroll_layout.setSpacing(1)


        for i, file_path in enumerate(recent_files[:100]):
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(0)

            btn = QToolButton()
            btn.setText(f"   {file_path}")
            btn.setIcon(self.create_number_icon(i + 1))
            btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            btn.setToolTip(file_path)
            btn.setStatusTip(
                self.main_window.translations[lang].get(
                    "open_recent_file_status", "Open this recent file"
                )
            )
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setAutoRaise(True)
            btn.setMinimumWidth(260)
            btn.clicked.connect(
                lambda checked, path=file_path: (
                    self.force_close_all_menus(),
                    #self.open_recent_file(path)
                    QTimer.singleShot(0, lambda: self.open_recent_file(path))
                )
            )

            remove_btn = QToolButton()
            remove_btn.setText("⨉")
            remove_btn.setAutoRaise(True)
            remove_btn.setToolTip(f"Remove from recent files")
            remove_btn.setFixedWidth(28)
            remove_btn.clicked.connect(
                lambda checked, path=file_path: self._remove_recent_file_and_refresh(path)
            )

            row_layout.addWidget(btn)
            row_layout.addWidget(remove_btn)
            scroll_layout.addWidget(row_widget)            
            
###


        scroll_area = QScrollArea()
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setMaximumHeight(400)
        scroll_area.setMinimumWidth(350)
        # Remove the box border
        scroll_area.setFrameShape(QScrollArea.NoFrame)

        container_action = QWidgetAction(self.recent_files_menu)
        container_action.setDefaultWidget(scroll_area)
        self.recent_files_menu.addAction(container_action)

        # --- Static actions below the scroll area ---
        self.recent_files_menu.addSeparator()

        open_all_action = QAction(
            self.main_window.translations[lang].get("open_all_recent", "Open All Recent Files"),
            self.main_window
        )
        open_all_action.setStatusTip(
            self.main_window.translations[lang].get(
                "open_all_recent_status", "Open all recent files at once"
            )
        )
        open_all_action.triggered.connect(self.open_all_recent_files)
        self.recent_files_menu.addAction(open_all_action)

        clear_action = QAction(
            self.main_window.translations[lang].get("clear_recent_files", "Clear Recent Files"),
            self.main_window
        )
        clear_action.setStatusTip(
            self.main_window.translations[lang].get(
                "clear_recent_files_status", "Remove all files from the recent list"
            )
        )
        clear_action.triggered.connect(self.clear_recent_files)
        self.recent_files_menu.addAction(clear_action)

    def _remove_recent_file_and_refresh(self, file_path):
        """Remove a single file from recent list and refresh the menu."""
        if hasattr(self.main_window, 'config_manager'):
            self.main_window.config_manager.remove_recent_file(file_path)
        self.update_recent_files_menu()

    # def open_recent_file(self, file_path):
        # """Open a recent file (delay opening to let menu close first)"""
        # if not file_path or not os.path.exists(file_path):
            # from PyQt5.QtWidgets import QMessageBox
            # reply = QMessageBox.question(
                # self.main_window,
                # "File Not Found",
                # f"File not found:\n{file_path}\n\nRemove from recent files?",
                # QMessageBox.Yes | QMessageBox.No
            # )
            # if reply == QMessageBox.Yes and hasattr(self.main_window, 'config_manager'):
                # self.main_window.config_manager.remove_recent_file(file_path)
                # self.update_recent_files_menu()
            # return

        # # Delay the actual opening – menu will close during this delay
        # QTimer.singleShot(30, lambda: (
            # self.main_window.editor_manager.open_specific_file(file_path),
            # self.update_recent_files_menu()
        # ))

    def open_recent_file(self, file_path):
        """Open a recent file with wait cursor for large files"""
        from PyQt5.QtWidgets import QApplication, QMessageBox
        from PyQt5.QtCore import Qt

        if not file_path or not os.path.exists(file_path):
            reply = QMessageBox.question(
                self.main_window,
                "File Not Found",
                f"File not found:\n{file_path}\n\nRemove from recent files?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes and hasattr(self.main_window, 'config_manager'):
                self.main_window.config_manager.remove_recent_file(file_path)
                self.update_recent_files_menu()
            return

        # --- Show wait cursor ---
        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()  # Force cursor update

        try:
            # Open the file (this may be slow for large files)
            self.main_window.editor_manager.open_specific_file(file_path)
            self.update_recent_files_menu()
        finally:
            # Restore normal cursor
            QApplication.restoreOverrideCursor()


    def open_all_recent_files(self):
        """Open all recent files (delayed to allow menu to close)"""
        QTimer.singleShot(10, self._do_open_all_recent_files)

        
    def _do_open_all_recent_files(self):
        """Actual batch opening after menu has closed, with wait cursor"""
        from PyQt5.QtWidgets import QMessageBox, QProgressDialog, QApplication
        from PyQt5.QtCore import Qt

        if not hasattr(self.main_window, 'config_manager'):
            return

        recent_files = self.main_window.config_manager.get_recent_files()
        if not recent_files:
            QMessageBox.information(
                self.main_window,
                "No Recent Files",
                "No recent files to open."
            )
            return

        # Filter existing files
        existing_files = [f for f in recent_files if os.path.exists(f)]
        if not existing_files:
            QMessageBox.information(
                self.main_window,
                "No Files Found",
                "None of the recent files could be found."
            )
            return

        if len(existing_files) > 5:
            reply = QMessageBox.question(
                self.main_window,
                "Open Many Files",
                f"This will open {len(existing_files)} files. Continue?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        # --- Show wait cursor immediately ---
        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()

        try:
            # Progress dialog (only if many files)
            progress = None
            if len(existing_files) > 3:
                progress = QProgressDialog(
                    "Opening files...",
                    "Cancel",
                    0,
                    len(existing_files),
                    self.main_window
                )
                progress.setWindowTitle("Opening files, please wait...")
                progress.setMinimumWidth(400)
                progress.setWindowModality(Qt.WindowModal)
                progress.show()

            opened_count = 0
            for i, file_path in enumerate(existing_files):
                if progress and progress.wasCanceled():
                    break
                try:
                    self.main_window.editor_manager.open_specific_file(file_path)
                    opened_count += 1
                    if progress:
                        progress.setValue(i + 1)
                        progress.setLabelText(f"Opened {os.path.basename(file_path)}")
                        QApplication.processEvents()
                except Exception as e:
                    print(f"Error opening {file_path}: {e}")

            if progress:
                progress.close()

            if opened_count > 0:
                self.main_window.update_status_bar(f"Opened {opened_count} files")
            else:
                QMessageBox.warning(
                    self.main_window,
                    "Open Error",
                    "Could not open any recent files."
                )

            self.update_recent_files_menu()
        finally:
            # Restore normal cursor after all files are opened
            QApplication.restoreOverrideCursor()        

    def clear_recent_files(self):
        """Clear all recent files"""
        from PyQt5.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self.main_window,
            "Clear Recent Files",
            "Are you sure you want to clear all recent files?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if hasattr(self.main_window, 'config_manager'):
                self.main_window.config_manager.clear_recent_files()
            self.update_recent_files_menu()
            # Refresh the editor welcome page immediately if it is currently showing
            # (welcome page is visible only when no editor files are open)
            em = self.main_window.editor_manager
            if not getattr(em, 'editor_files', None):
                lm = getattr(self.main_window, 'layout_manager', None)
                if lm and hasattr(lm, '_safe_recreate_editor_container'):
                    QTimer.singleShot(0, lm._safe_recreate_editor_container)

    def get_current_editor_or_warn(self):
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]                            
        
        current_editor = self.main_window.editor_manager.get_current_editor()
        current_file = self.main_window.editor_manager.get_current_file_path()
        if not current_editor or not current_file:
            self.show_error(tr["no_file_open"], tr["open_a_latex_file"])
            return None
        return current_editor

    def undo_current_editor(self):
        editor = self.get_current_editor_or_warn()
        if editor:
            editor.undo()

    def redo_current_editor(self):
        editor = self.get_current_editor_or_warn()
        if editor:
            editor.redo()

    def _create_edit_menu(self):
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]
        edit_menu = self.main_window.menuBar().addMenu("&"+tr["edit_menu"])
        # Undo
        undo_action = QAction(tr["undo"], self.main_window)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.setStatusTip(tr["undo"])   # ✅ Status tip
        undo_action.triggered.connect(self.undo_current_editor)
        self.icons_manager.apply_icon_to_action(undo_action, "undo")
        edit_menu.addAction(undo_action)
        # Redo
        redo_action = QAction(tr["redo"], self.main_window)
        redo_action.setShortcut("Ctrl+Y")
        redo_action.setStatusTip(tr["redo"])   # ✅ Status tip
        redo_action.triggered.connect(self.redo_current_editor)
        self.icons_manager.apply_icon_to_action(redo_action, "redo")
        edit_menu.addAction(redo_action)
        edit_menu.addSeparator()
        # Cut, Copy, Paste
        for text, shortcut, icon, func in [
            ("cut", "Ctrl+X", "cut", "cut"),
            ("copy", "Ctrl+C", "copy", "copy"),
            ("paste", "Ctrl+V", "paste", "paste")
        ]:
            action = QAction(tr[text], self.main_window)
            action.setShortcut(shortcut)
            action.setStatusTip(tr[text])   # ✅ Status tip
            action.triggered.connect(
                lambda checked, f=func: getattr(self.main_window.editor_manager.get_current_editor(), f, lambda: None)()
                if self.main_window.editor_manager.get_current_editor() else None
            )
            self.icons_manager.apply_icon_to_action(action, icon)
            edit_menu.addAction(action)
        edit_menu.addSeparator()
        # Go to Line
        go_to_line_action = QAction(tr.get("go_to_line", "Go to Line...")+"\tCtrl+G", self.main_window)        
        go_to_line_action.setToolTip(tr.get("tooltip_go_to_line", "Go to a specific line number"))
        go_to_line_action.setStatusTip(tr.get("status_jump_to_line", "Jump to a specific line number in the current document"))
        go_to_line_action.triggered.connect(self.main_window.editor_manager.go_to_line)
        edit_menu.addAction(go_to_line_action)
        # Add the action to the main window so it can be triggered globally
        self.main_window.addAction(go_to_line_action)      
        # Count the words in a selected text
        word_count_action = QAction(tr["word_count"], self.main_window)
        word_count_action.setStatusTip(tr["status_word_count"])
        word_count_action.triggered.connect(
            self.main_window.editor_manager.count_selected_words
        )
        edit_menu.addAction(word_count_action)        
        # Delete Auxiliary Files
        delete_aux_action = QAction(
            tr.get("delete_aux_files", "Delete Auxiliary Files...")+"\tCtrl+Shift+Del",
            self.main_window
        )        
        delete_aux_action.setToolTip(
            tr.get("tooltip_delete_aux_files", "Delete auxiliary files in the current document's directory")
        )
        delete_aux_action.setStatusTip(tr.get("status_delete_aux_files", "Remove .aux, .log, .out, etc. files generated by LaTeX"))
        delete_aux_action.triggered.connect(self.main_window.editor_manager.delete_auxiliary_files)
        edit_menu.addAction(delete_aux_action)
        self.main_window.addAction(delete_aux_action) 
        # Text Transformation menu
        transform_menu = edit_menu.addMenu(tr["text_transform"])
        edit_menu.addSeparator()        
        # Add actions
        lowercase_action = QAction(tr["lowercase"], self.main_window)
        lowercase_action.setShortcut(QKeySequence("Ctrl+Down"))
        lowercase_action.setStatusTip(tr["status_lowercase"])
        lowercase_action.triggered.connect(self.main_window.editor_manager.transform_to_lowercase)
        transform_menu.addAction(lowercase_action)
        uppercase_action = QAction(tr["uppercase"], self.main_window)
        uppercase_action.setShortcut(QKeySequence("Ctrl+Up"))
        uppercase_action.setStatusTip(tr["status_uppercase"])
        uppercase_action.triggered.connect(self.main_window.editor_manager.transform_to_uppercase)
        transform_menu.addAction(uppercase_action)
        title_case_action = QAction(tr["title_case"], self.main_window)
        title_case_action.setStatusTip(tr["status_title_case"])
        title_case_action.triggered.connect(self.main_window.editor_manager.transform_to_title_case)
        transform_menu.addAction(title_case_action)
        full_title_case_action = QAction(tr["full_title_case"], self.main_window)
        full_title_case_action.setStatusTip(tr["status_full_title_case"])
        full_title_case_action.triggered.connect(self.main_window.editor_manager.transform_to_full_title_case)
        transform_menu.addAction(full_title_case_action)   
        # Full title case can be without shortcut        
        self.setup_latex_comment_menu(edit_menu)
               
        edit_menu.addSeparator()       
        
        # Spell Check submenu
        spell_menu = edit_menu.addMenu(tr["spell_check"])

        # Populate lazily on first open so SpellChecker is guaranteed to exist.
        # _populated flag prevents rebuilding the submenu on every open.
        def _populate_spell_menu_once():
            if getattr(spell_menu, '_populated', False):
                return
            sc = getattr(self.main_window, 'spell_checker', None)
            if sc is None:
                return                        # still not ready — try again next open
            self.add_spell_check_menu(spell_menu)
            spell_menu._populated = True

        spell_menu.aboutToShow.connect(_populate_spell_menu_once)
        
        edit_menu.addSeparator()

        # Find / Replace
        find_action = QAction(tr.get("find", "Find"), self.main_window)
        find_action.setShortcut("Ctrl+F")
        find_action.setStatusTip(tr.get("status_find", "Find text in the current document"))
        find_action.triggered.connect(self.main_window.show_find_dialog)
        self.icons_manager.apply_icon_to_action(find_action, "find")
        edit_menu.addAction(find_action)
        replace_action = QAction(tr.get("replace", "Replace"), self.main_window)
        replace_action.setShortcut("Ctrl+H")
        replace_action.setStatusTip(tr.get("status_replace", "Find and replace text"))
        replace_action.triggered.connect(self.main_window.show_replace_dialog)
        edit_menu.addAction(replace_action)
        find_next_action = QAction(tr.get("find_next", "Find Next"), self.main_window)
        find_next_action.setShortcut("F3")
        find_next_action.setStatusTip(tr.get("status_find_next", "Find the next occurrence"))
        find_next_action.triggered.connect(self.main_window.find_next)
        edit_menu.addAction(find_next_action)
        find_previous_action = QAction(tr.get("find_previous", "Find Previous"), self.main_window)
        find_previous_action.setShortcut("Shift+F3")
        find_previous_action.setStatusTip(tr.get("status_find_previous", "Find the previous occurrence"))
        find_previous_action.triggered.connect(self.main_window.find_previous)
        edit_menu.addAction(find_previous_action)
        
        self._setup_menu_close_protection()


    def add_spell_check_menu(self, tools_menu):
        """Add spell check options to an existing Tools/Spell Check menu"""
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]

        # Guard: spell checker may not be ready yet if the menu is built
        # before _init_spell_checker fires.
        if not hasattr(self.main_window, 'spell_checker') \
                or self.main_window.spell_checker is None:
            return

        spell_checker = self.main_window.spell_checker

        # ── Language submenu ──────────────────────────────────────────────
        lang_menu = tools_menu.addMenu(tr.get("spell_check_language", "Spell checking language"))

        arabic_action = QAction(tr["arabic"], self.main_window)
        arabic_action.setCheckable(True)
        self._make_rtl_checkable(arabic_action)
        arabic_action.setStatusTip(tr["tooltip_load_arabic_dictionary"])
        arabic_action.triggered.connect(lambda: self._set_spell_language('ar'))
        lang_menu.addAction(arabic_action)


        english_action = QAction(tr["english"], self.main_window)
        english_action.setCheckable(True)
        self._make_rtl_checkable(english_action)
        english_action.setStatusTip(tr["tooltip_load_englsih_dictionary"])
        english_action.triggered.connect(lambda: self._set_spell_language('en'))
        lang_menu.addAction(english_action)


        # Keep check marks in sync when menu opens
        def update_lang_checks():
            active = getattr(spell_checker, 'active_language', None)
            enabled = getattr(spell_checker, 'enabled', False)
            english_action.setChecked(enabled and active == 'en')
            arabic_action.setChecked(enabled and active == 'ar')

        lang_menu.aboutToShow.connect(update_lang_checks)
        tools_menu.aboutToShow.connect(update_lang_checks)

        tools_menu.addSeparator()

        # ── Disable spell check ───────────────────────────────────────────
        disable_action = QAction(tr.get("disable_spell_check", "Disable spell check"), self.main_window)
        disable_action.setStatusTip(tr["tooltip_turn_off_spell_checking"])
        disable_action.triggered.connect(self._disable_spell_check)
        disable_action.setEnabled(False) 
        tools_menu.addAction(disable_action)

        # Keep disable action enabled only when spell check is active
        tools_menu.aboutToShow.connect(
            lambda: disable_action.setEnabled(getattr(spell_checker, 'enabled', False))
        )

        tools_menu.addSeparator()

        # ── Dictionary statistics (unchanged) ────────────────────────────
        info_action = QAction(tr["dictionary_statistics"], self.main_window)
        info_action.setStatusTip(tr["status_dictionary_statistics"])

        def show_dict_info():
            if not getattr(spell_checker, 'dictionaries_loaded', False):
                QMessageBox.information(
                    self.main_window,
                    "Dictionary Statistics",
                    "No dictionary loaded yet.\n\nSelect a language to enable spell check."
                )
                return
            stats = spell_checker.get_dictionary_stats()
            info = []
            total_words = 0
            for lang_key, count in stats.items():
                info.append(f"{lang_key.upper()}: {count:,} words")
                total_words += count
            if hasattr(spell_checker, 'personal_words') and spell_checker.personal_words:
                info.append(f"Personal: {len(spell_checker.personal_words)} words")
            info.append(f"\nTotal: {total_words:,} words")
            if hasattr(spell_checker, 'word_sets'):
                cached_words = sum(len(w) for w in spell_checker.word_sets.values())
                info.append(f"Memory usage: {cached_words:,} words in dictionary")
            if hasattr(spell_checker, '_suggestion_cache'):
                info.append(f"Suggestion cache: {len(spell_checker._suggestion_cache):,} entries")
            active = getattr(spell_checker, 'active_language', None)
            enabled = getattr(spell_checker, 'enabled', False)
            status = f"{'Enabled' if enabled else 'Disabled'}"
            if enabled and active:
                status += f" ({active.upper()})"
            info.append(f"\nStatus: {status}")
            QMessageBox.information(
                self.main_window, "Dictionary Statistics", "\n".join(info)
            )

        info_action.triggered.connect(show_dict_info)
        tools_menu.addAction(info_action)

    def _set_spell_language(self, lang):
        sc = getattr(self.main_window, 'spell_checker', None)
        if sc is None:
            return
        sc.set_language(lang)


    
    def _disable_spell_check(self):
        sc = getattr(self.main_window, 'spell_checker', None)
        if sc is None or not sc.enabled:
            return
        sc._disable_all("Spell check disabled")



    # Menu setup functions
    def setup_latex_comment_menu(self, edit_menu):
        """Add comment/uncomment actions to the Edit menu"""
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]
        # Comment action
        comment_action = QAction(tr["comment"], self.main_window)
        comment_action.setShortcut(QKeySequence("Ctrl+/"))
        comment_action.setToolTip(tr["tooltip_comment_selected_lines"])
        comment_action.setStatusTip(tr["status_comment"])
        comment_action.triggered.connect(self.main_window.editor_manager.comment_latex_lines)
        edit_menu.addAction(comment_action)
        # Uncomment action  
        uncomment_action = QAction(tr["uncomment"], self.main_window)
        uncomment_action.setShortcut(QKeySequence("Ctrl+Shift+/"))
        uncomment_action.setToolTip(tr["tooltip_remove_comments_from_selected_lines"])
        uncomment_action.setStatusTip(tr["status_uncomment"])
        uncomment_action.triggered.connect(self.main_window.editor_manager.uncomment_latex_lines)
        edit_menu.addAction(uncomment_action)
        # Toggle comment action (most common)
        toggle_action = QAction(tr["toggle_comments"], self.main_window)
        toggle_action.setShortcut(QKeySequence("Ctrl+D"))
        toggle_action.setToolTip(tr["tooltip_toggle_comments_on_selected_lines"])
        toggle_action.setStatusTip(tr["status_toggle_comments"])
        toggle_action.triggered.connect(self.main_window.editor_manager.toggle_latex_comments)
        edit_menu.addAction(toggle_action)

    # Alternative: Context menu integration
    def setup_latex_comment_context_menu(self, context_menu):
        """Add comment/uncomment actions to the editor context menu"""
        context_menu.addSeparator()
        # Toggle comment (most used)
        toggle_action = QAction("Toggle Comments (Ctrl+D)", self.main_window)
        toggle_action.triggered.connect(self.main_window.editor_manager.toggle_latex_comments)
        context_menu.addAction(toggle_action)
        # Individual comment/uncomment
        comment_action = QAction("Comment Lines (Ctrl+/)", self.main_window)
        comment_action.triggered.connect(self.main_window.editor_manager.comment_latex_lines)
        context_menu.addAction(comment_action)
        uncomment_action = QAction("Uncomment Lines (Ctrl+Shift+/)", self.main_window)
        uncomment_action.triggered.connect(self.main_window.editor_manager.uncomment_latex_lines)
        context_menu.addAction(uncomment_action)

    def _create_view_menu(self): 
        """Create view menu with proper output toggle functionality"""
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]
        view_menu = self.main_window.menuBar().addMenu("&"+tr["view_menu"])
        # Toggle visibility
        self.toggle_visibility_action = QAction(tr["show_hide_side_panel"], self.main_window)  
        self.toggle_visibility_action.setStatusTip(tr["status_show_hide_side_panel"])        
        self.toggle_visibility_action.setShortcut("F9")
        self.toggle_visibility_action.setCheckable(True)
        self.toggle_visibility_action.setChecked(True)  # Toolbar visible by default
        self._make_rtl_checkable(self.toggle_visibility_action)
        self.toggle_visibility_action.setToolTip(tr["tooltip_toggle_side_panel_visibility"])
        
        self.toggle_visibility_action.toggled.connect(self.main_window.set_side_panel_visible)
        view_menu.addAction(self.toggle_visibility_action)
        # ✅ ADD THIS - Show/Hide Main Toolbar
        toggle_toolbar_action = QAction(
            tr.get("toggle_main_toolbar", "Show/Hide Main Toolbar"), 
            self.main_window
        )
        toggle_toolbar_action.setShortcut("F10")  # F10 to toggle
        toggle_toolbar_action.setCheckable(True)
        toggle_toolbar_action.setChecked(True)  # Toolbar visible by default
        self._make_rtl_checkable(toggle_toolbar_action)            
        toggle_toolbar_action.setToolTip(tr["tooltip_toggle_main_toolbar_visibility"])
        toggle_toolbar_action.setStatusTip(tr.get("status_toggle_main_toolbar", "Show or hide the main toolbar"))
        toggle_toolbar_action.triggered.connect(self.toggle_main_toolbar)
        view_menu.addAction(toggle_toolbar_action)
        # Store reference for state updates
        self.main_window.toggle_toolbar_action = toggle_toolbar_action
        # ✅ ADD THIS - Show/Hide Menu Bar
        toggle_menubar_action = QAction(tr.get("toggle_menubar", "Show/Hide Menu Bar"), self.main_window)
        toggle_menubar_action.setShortcut("F11")  # F11 to toggle (common shortcut)
        toggle_menubar_action.setCheckable(True)
        toggle_menubar_action.setChecked(True)  # Menu bar visible by default
        self._make_rtl_checkable(toggle_menubar_action)            
        toggle_menubar_action.setToolTip(tr["tooltip_toggle_menu_bar_visibility"])
        toggle_menubar_action.setStatusTip(tr.get("status_toggle_menubar", "Show or hide the menu bar"))
        toggle_menubar_action.triggered.connect(self.toggle_menu_bar)
        view_menu.addAction(toggle_menubar_action)
        # Store reference for state updates
        self.main_window.toggle_menubar_action = toggle_menubar_action
        # Toggle Full/Normal Screen Mode
        full_screen_action =  QAction(tr["full_screen"], self.main_window)
        full_screen_action.setShortcut("F12")
        full_screen_action.setCheckable(True)
        full_screen_action.setChecked(False)
        self._make_rtl_checkable(full_screen_action)               
        full_screen_action.setStatusTip(tr["status_full_screen"])
        full_screen_action.triggered.connect(lambda checked: self.toggle_fullscreen(checked))
        view_menu.addAction(full_screen_action)
        # ======================================================
        # ✅ NEW ITEM 3: Show/Hide Toolbar Button Text
        # ======================================================
        toolbar_text_visible = getattr(self.main_window, '_toolbar_text_visible', True)
        self.toggle_toolbar_text_action = QAction(
            tr.get("toggle_toolbar_text", "Show Toolbar Button Text"),
            self.main_window
        )
        self.toggle_toolbar_text_action.setCheckable(True)
        self._make_rtl_checkable(self.toggle_toolbar_text_action)
        self.toggle_toolbar_text_action.setChecked(toolbar_text_visible)
        self.toggle_toolbar_text_action.setToolTip(tr["tooltip_show_or_hide_text_labels_under_toolbar_icons"])
        self.toggle_toolbar_text_action.setStatusTip(tr.get("status_toggle_toolbar_text", "Display text under toolbar icons"))
        self.toggle_toolbar_text_action.triggered.connect(self.toggle_toolbar_button_text)
        view_menu.addAction(self.toggle_toolbar_text_action)
        # ======================================================
        # ✅ NEW ITEM 4: Show/Hide Tooltips
        # ======================================================
        tooltips_visible = getattr(self.main_window, '_tooltips_visible', True)
        self.toggle_tooltips_action = QAction(
            tr.get("toggle_tooltips", "Show Tooltips"),
            self.main_window
        )
        self.toggle_tooltips_action.setCheckable(True)
        self._make_rtl_checkable(self.toggle_tooltips_action)
        self.toggle_tooltips_action.setChecked(tooltips_visible)
        self.toggle_tooltips_action.setToolTip(tr["tooltip_show_or_hide_all_tooltips"])
        self.toggle_tooltips_action.setStatusTip(tr.get("status_toggle_tooltips", "Enable or disable all tooltip popups"))
        self.toggle_tooltips_action.triggered.connect(self.toggle_tooltips)
        view_menu.addAction(self.toggle_tooltips_action)
        view_menu.addSeparator()
        # Show/Hide PDF Toolbar
        self.toggle_pdf_toolbar_action = QAction(tr["show_pdf_toolbar"], self.main_window)
        self.toggle_pdf_toolbar_action.setShortcut("Ctrl+F7")
        self.toggle_pdf_toolbar_action.setCheckable(True)
        self.toggle_pdf_toolbar_action.setChecked(True)  # Default: toolbars visible
        self._make_rtl_checkable(self.toggle_pdf_toolbar_action)
        self.toggle_pdf_toolbar_action.setStatusTip(tr["status_show_pdf_toolbar"])
        self.toggle_pdf_toolbar_action.triggered.connect(self.main_window.toggle_pdf_toolbars)
        view_menu.addAction(self.toggle_pdf_toolbar_action)
        # Store reference for updating state
        self.main_window.menu_pdf_toolbar_toggle_action = self.toggle_pdf_toolbar_action

        # Show/Hide DjVu Toolbar
        toggle_djvu_toolbar_action = QAction(tr.get("show_djvu_toolbar", "Show DjVu Toolbar"), self.main_window)
        toggle_djvu_toolbar_action.setShortcut("Ctrl+F8")   # different shortcut
        toggle_djvu_toolbar_action.setCheckable(True)
        toggle_djvu_toolbar_action.setChecked(True)   # default visible
        self._make_rtl_checkable(toggle_djvu_toolbar_action)
        toggle_djvu_toolbar_action.setStatusTip(tr.get("status_show_djvu_toolbar", "Show/hide DjVu viewer toolbar"))
        toggle_djvu_toolbar_action.triggered.connect(self.main_window.toggle_djvu_toolbar)
        view_menu.addAction(toggle_djvu_toolbar_action)
        # Store reference
        self.main_window.menu_djvu_toolbar_toggle_action = toggle_djvu_toolbar_action        
        # === LINE NUMBERS TOGGLE ===
        self.line_numbers_action = QAction(tr["show_line_numbers"], self.main_window)
        self.line_numbers_action.setCheckable(True)
        initial_line = getattr(self.main_window, 'is_line_numbers_visible', True)
        self._make_rtl_checkable(self.line_numbers_action)        
        self.line_numbers_action.setChecked(initial_line)
        self.line_numbers_action.setStatusTip(tr["status_show_line_numbers"])
        self.line_numbers_action.triggered.connect(lambda checked: self.toggle_line_numbers(checked))
        view_menu.addAction(self.line_numbers_action)
        # === FOLD MARKERS TOGGLE ===
        self.fold_markers_action = QAction(tr["show_fold_markers"], self.main_window)
        self.fold_markers_action.setCheckable(True)
        initial_fold = getattr(self.main_window, 'is_fold_markers_visible', True)
        self._make_rtl_checkable(self.fold_markers_action)
        self.fold_markers_action.setChecked(initial_fold)
        self.fold_markers_action.setStatusTip(tr["status_show_fold_markers"])
        self.fold_markers_action.triggered.connect(lambda checked: self.toggle_fold_markers(checked))
        view_menu.addAction(self.fold_markers_action)
        
        view_menu.addSeparator()
        # Side panel controls
        side_panel_menu = QMenu("Side Panel", self.main_window)
        # Toggle position
        toggle_position_action = QAction(tr["switch_side_panel"], self.main_window)
        toggle_position_action.setShortcut("Ctrl+F9")
        toggle_position_action.setToolTip(tr["tooltip_switch_side_panel"])
        toggle_position_action.setStatusTip(tr["status_switch_side_panel"])
        toggle_position_action.triggered.connect(self.main_window.toggle_side_panel_position)
        self.icons_manager.apply_icon_to_action(toggle_position_action, "switch_side_panel")
        view_menu.addAction(toggle_position_action)
        # Reset to default
        reset_default_action = QAction(tr["reset_side_panel_to_default"], self.main_window)
        reset_default_action.setStatusTip(tr["reset_side_panel_to_default"])
        reset_default_action.triggered.connect(self.main_window.reset_side_panel_to_default)
        view_menu.addAction(reset_default_action)
        # Editor layout action
        editor_layout_action = QAction(tr["tab_tex"], self.main_window)
        editor_layout_action.setShortcut("Ctrl+F10")
        editor_layout_action.setStatusTip(tr["status_tab_tex"])
        editor_layout_action.triggered.connect(self.main_window.layout_manager.toggle_editor_layout)
        self.icons_manager.apply_icon_to_action(editor_layout_action, "editor_layout")
        view_menu.addAction(editor_layout_action)
        # PDF layout action
        pdf_layout_action = QAction(tr["tab_pdf"], self.main_window)
        pdf_layout_action.setShortcut("Ctrl+F11")
        pdf_layout_action.setStatusTip(tr["status_tab_pdf"])
        pdf_layout_action.triggered.connect(self.main_window.layout_manager.toggle_pdf_layout)
        self.icons_manager.apply_icon_to_action(pdf_layout_action, "pdf_layout")
        view_menu.addAction(pdf_layout_action)
        # Switch Layout
        switch_layout_action = QAction(tr["switch_layout"], self.main_window)
        switch_layout_action.setShortcut("Ctrl+F12")
        switch_layout_action.setToolTip(tr["tooltip_switch_layout"])
        switch_layout_action.setStatusTip(tr["status_switch_layout"])
        switch_layout_action.triggered.connect(self.main_window.toolbar_manager.handle_switch_layout)
        self.icons_manager.apply_icon_to_action(switch_layout_action, "switch_layout")
        view_menu.addAction(switch_layout_action)
        view_menu.addSeparator()
        # Expand Editor to Full Width
        expand_editor_action = QAction(tr["expand_editor_to_full_width"], self.main_window)
        expand_editor_action.setShortcut("Ctrl+Shift+F9") 
        expand_editor_action.setStatusTip(tr["status_expand_editor_to_full_width"])
        expand_editor_action.triggered.connect(self.main_window.toggle_editor_expand_width)
        view_menu.addAction(expand_editor_action)
        # Expand PDF to Full Width
        expand_pdf_action = QAction(tr["expand_pdf_to_full_width"], self.main_window)
        expand_pdf_action.setShortcut("Ctrl+Shift+F10")  
        expand_pdf_action.setStatusTip(tr["status_expand_pdf_to_full_width"])
        expand_pdf_action.triggered.connect(self.main_window.toggle_pdf_expand_width)        
        view_menu.addAction(expand_pdf_action)
        # Split Window (Balanced View)
        split_window_action = QAction(tr["split_window"], self.main_window)
        split_window_action.setShortcut("Ctrl+Shift+F11") 
        split_window_action.setStatusTip(tr["status_split_window"])
        split_window_action.triggered.connect(self.main_window.split_window_width)
        view_menu.addAction(split_window_action)
        # Output toggle action - FIXED
        output_toggle_action = QAction("", self.main_window)
        output_toggle_action.setShortcut("Ctrl+Shift+F12")
        output_toggle_action.triggered.connect(self._handle_output_toggle)        
        output_toggle_action.toggled.connect(lambda checked: self.main_window.toggle_output_tabs(force_state=checked))
        view_menu.addAction(output_toggle_action)
        # Store reference for updates
        self.main_window.menu_output_toggle_action = output_toggle_action
        self._update_output_toggle_action()        
        view_menu.addSeparator()
        # Folding submenu
        self.folding_menu = self._create_folding_menu(view_menu)
        self.folding_menu.setEnabled(initial_fold)
        
        self._setup_menu_close_protection()


    def toggle_toolbar_button_text(self, checked):
        """Toggle text labels under toolbar buttons"""
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]
        toolbar = getattr(self.main_window.toolbar_manager, 'main_toolbar', None)
        if not toolbar:
            return
        self.main_window._toolbar_text_visible = checked
        if checked:
            toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        else:
            toolbar.setToolButtonStyle(Qt.ToolButtonIconOnly)
        # Save to config
        if hasattr(self.main_window, 'config_manager'):
            self.main_window.config_manager.set_config_value(
                'ui', 'toolbar_text_visible', str(checked)
            )
            self.main_window.config_manager.save_config()
        status = "shown" if checked else "hidden"
        if hasattr(self.main_window, 'statusBar'):
            #self.main_window.statusBar().showMessage(f"Toolbar button text {status}", 2000)
            self.main_window.update_status_bar(
                tr.get("status_toolbar_button_text", "Toolbar button text {status}").format(status=status)
            )
            QTimer.singleShot(
                2000,
                lambda: self.main_window.update_status_bar(tr.get("status_ready", "Ready"))
            )                                                    

    def toggle_tooltips(self, checked):
        """Toggle all tooltips on or off using an event filter"""
        self.main_window._tooltips_visible = checked
        app = QApplication.instance()
        if checked:
            # Remove the tooltip blocker if installed
            if hasattr(self.main_window, '_tooltip_filter'):
                app.removeEventFilter(self.main_window._tooltip_filter)
                del self.main_window._tooltip_filter
        else:
            # Install event filter that blocks all ToolTip events
            if not hasattr(self.main_window, '_tooltip_filter'):
                self.main_window._tooltip_filter = TooltipBlockFilter(self.main_window)
            app.installEventFilter(self.main_window._tooltip_filter)
        # Save to config
        if hasattr(self.main_window, 'config_manager'):
            self.main_window.config_manager.set_config_value(
                'ui', 'tooltips_visible', str(checked)
            )
            self.main_window.config_manager.save_config()
        status = "enabled" if checked else "disabled"
        if hasattr(self.main_window, 'statusBar'):
            self.main_window.statusBar().showMessage(f"Tooltips {status}", 2000)

    def toggle_fold_markers(self, checked=None):
        """Toggle fold markers visibility"""
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]
        # If called without argument, toggle current state
        if checked is None:
            checked = not getattr(self.main_window, 'is_fold_markers_visible', True)
        # Convert to bool
        checked = bool(checked) if not isinstance(checked, bool) else checked
        if isinstance(checked, int):
            checked = (checked != 0)
        #print(f"toggle_fold_markers: setting to {checked}")
        # Update main_window state
        self.main_window.is_fold_markers_visible = checked
        # Update menu checkbox
        if hasattr(self, 'fold_markers_action'):
            self.fold_markers_action.blockSignals(True)
            self.fold_markers_action.setChecked(checked)
            self.fold_markers_action.blockSignals(False)
        # Enable/disable folding menu
        if hasattr(self, 'folding_menu'):
            self.folding_menu.setEnabled(checked)
        # Apply to all editors
        if hasattr(self.main_window, 'editor_manager'):
            if hasattr(self.main_window.editor_manager, 'get_all_editors'):
                for editor in self.main_window.editor_manager.get_all_editors():
                    if hasattr(editor, 'set_fold_markers_visible'):
                        editor.set_fold_markers_visible(checked)
            else:
                editor = self.main_window.editor_manager.get_current_editor()
                if editor and hasattr(editor, 'set_fold_markers_visible'):
                    editor.set_fold_markers_visible(checked)
        # Save to config
        if hasattr(self.main_window, 'config_manager'):
            self.main_window.config_manager.set_config_value('ui', 'is_fold_markers_visible', str(checked))
            self.main_window.config_manager.save_config()
        # Status message
        if hasattr(self.main_window, 'statusBar'):
            status = "shown" if checked else "hidden"
            self.main_window.update_status_bar(f"Fold markers {status}", 2000)
            QTimer.singleShot(
                2000,
                lambda: self.main_window.update_status_bar(
                    tr.get("status_ready", "Ready"),
                    timeout=0
                )
            )            

    def _create_folding_menu(self, view_menu):
        """Create code folding submenu"""   
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]        
        folding_menu = view_menu.addMenu(tr["folding"])
        # Fold current
        fold_action = QAction(tr["fold_current_section"], self.main_window)
        fold_action.setShortcut("Ctrl+Shift+[")
        fold_action.setStatusTip(tr["status_fold_current_section"])
        fold_action.triggered.connect(self.main_window.editor_manager.fold_current_section)
        folding_menu.addAction(fold_action)
        # Unfold current
        unfold_action = QAction(tr["unfold_current_section"], self.main_window)
        unfold_action.setShortcut("Ctrl+Shift+]")
        unfold_action.setStatusTip(tr["status_unfold_current_section"])
        unfold_action.triggered.connect(self.main_window.editor_manager.unfold_current_section)
        folding_menu.addAction(unfold_action)
        folding_menu.addSeparator()
        # Fold all
        fold_all_action = QAction(tr["fold_all"], self.main_window)
        fold_all_action.setShortcut("Ctrl+Shift+-")
        fold_all_action.setStatusTip(tr["status_fold_all"])
        fold_all_action.triggered.connect(self.main_window.editor_manager.fold_all_sections)
        folding_menu.addAction(fold_all_action)
        # Unfold all
        unfold_all_action = QAction(tr["unfold_all"], self.main_window)
        unfold_all_action.setShortcut("Ctrl+Shift+=")
        unfold_all_action.setStatusTip(tr["status_unfold_all"])
        unfold_all_action.triggered.connect(self.main_window.editor_manager.unfold_all_sections)
        folding_menu.addAction(unfold_all_action)
        folding_menu.addSeparator()
        # Fold by level submenu
        level_menu = folding_menu.addMenu(tr["fold_to_level"])
        levels = [
            ("Parts", 0),
            ("Chapters", 1),
            ("Sections", 2),
            ("Subsections", 3),
            ("Subsubsections", 4),
        ]
        for name, level in levels:
            text = tr["fold_below"].format(name)
            action = QAction(text, self.main_window)
            action.setStatusTip(tr["status_fold_to_level"].format(name))
            action.triggered.connect(lambda checked, lvl=level: self.main_window.editor_manager.fold_to_level(lvl))
            level_menu.addAction(action)
        return folding_menu
        
        self._setup_menu_close_protection()


    def toggle_fullscreen(self, checked):
        if checked:
            self.main_window.showFullScreen()
        else:
            self.main_window.showMaximized()

    def toggle_line_numbers(self, checked=None):
        """Toggle line numbers visibility"""
        # If called without argument, toggle current state
        if checked is None:
            checked = not getattr(self.main_window, 'is_line_numbers_visible', True)
        # Convert to bool (handles int from stateChanged)
        checked = bool(checked) if not isinstance(checked, bool) else checked
        if isinstance(checked, int):
            checked = (checked != 0)
        #print(f"toggle_line_numbers: setting to {checked}")
        # Update main_window state
        self.main_window.is_line_numbers_visible = checked
        # Update menu checkbox
        if hasattr(self, 'line_numbers_action'):
            self.line_numbers_action.blockSignals(True)
            self.line_numbers_action.setChecked(checked)
            self.line_numbers_action.blockSignals(False)
        # Apply to all editors
        if hasattr(self.main_window, 'editor_manager'):
            if hasattr(self.main_window.editor_manager, 'get_all_editors'):
                for editor in self.main_window.editor_manager.get_all_editors():
                    if hasattr(editor, 'set_line_numbers_visible'):
                        editor.set_line_numbers_visible(checked)
            else:
                # Fallback: just current editor
                editor = self.main_window.editor_manager.get_current_editor()
                if editor and hasattr(editor, 'set_line_numbers_visible'):
                    editor.set_line_numbers_visible(checked)
        # Save to config
        if hasattr(self.main_window, 'config_manager'):
            self.main_window.config_manager.set_config_value('ui', 'is_line_numbers_visible', str(checked))
            self.main_window.config_manager.save_config()
        # Status message
        if hasattr(self.main_window, 'statusBar'):
            status = "shown" if checked else "hidden"
            self.main_window.statusBar().showMessage(f"Line numbers {status}", 2000)

    def toggle_menu_bar(self):
        """Toggle menu bar visibility"""
        menu_bar = self.main_window.menuBar()
        current_state = menu_bar.isVisible()
        new_state = not current_state
        # Toggle visibility
        menu_bar.setVisible(new_state)
        # Update action checked state
        if hasattr(self.main_window, 'toggle_menubar_action'):
            self.main_window.toggle_menubar_action.setChecked(new_state)
        # Update status bar
        status_msg = "Menu bar shown" if new_state else "Menu bar hidden (press F11 to show)"
        if hasattr(self.main_window, 'update_status_bar'):
            self.main_window.update_status_bar(status_msg)
        # Save state to config
        if hasattr(self.main_window, 'config_manager'):
            try:
                self.main_window.config_manager.set_config_value('ui', 'menubar_visible', new_state)
            except:
                pass

    def toggle_main_toolbar(self):
        """Toggle main toolbar visibility"""
        # Get toolbar from toolbar manager
        if not hasattr(self.main_window, 'toolbar_manager') or not self.main_window.toolbar_manager:
            return
        toolbar = self.main_window.toolbar_manager.main_toolbar
        if not toolbar:
            return
        # Toggle visibility
        current_state = toolbar.isVisible()
        new_state = not current_state
        toolbar.setVisible(new_state)
        # Update action checked state
        if hasattr(self.main_window, 'toggle_toolbar_action'):
            self.main_window.toggle_toolbar_action.setChecked(new_state)
        # Update status bar
        status_msg = "Main toolbar shown" if new_state else "Main toolbar hidden (press F12 to show)"
        if hasattr(self.main_window, 'update_status_bar'):
            self.main_window.update_status_bar(status_msg)
        # Save state to config
        if hasattr(self.main_window, 'config_manager'):
            try:
                self.main_window.config_manager.set_config_value('ui', 'main_toolbar_visible', new_state)
            except:
                pass

    def _create_tools_menu(self):         
        """Create tools menu"""
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]
        tools_menu = self.main_window.menuBar().addMenu("&"+tr["tools_menu"])
        # Tool 1: Latex Document Wizard
        latex_wizard_action = QAction(tr["latex_document_wizard"], self.main_window) 
        icon = QIcon("icons/wizard.svg")
        latex_wizard_action.setIcon(icon)          
        latex_wizard_action.setShortcut("Ctrl+W")
        latex_wizard_action.setStatusTip(tr["status_latex_document_wizard"])
        latex_wizard_action.triggered.connect(self.main_window.open_latex_wizard_tab) 
        tools_menu.addAction(latex_wizard_action)
        tools_menu.addSeparator()
        # Tool 2: Bibitex Manager
        bibtex_manager_action = QAction(tr["bibtex_manager"], self.main_window) 
        icon = QIcon("icons/bibtex.svg")
        bibtex_manager_action.setIcon(icon)                  
        bibtex_manager_action.setShortcut("Ctrl+M")
        bibtex_manager_action.setStatusTip(tr["status_bibtex_manager"])
        bibtex_manager_action.triggered.connect(self.main_window.open_bibtex_manager_tab) 
        tools_menu.addAction(bibtex_manager_action)
        tools_menu.addSeparator()
        # Tool 2: Calculator + Calendar 
        tools_tab_action = QAction(tr["tools_tab"], self.main_window)
        icon = QIcon("icons/accessories.svg")
        tools_tab_action.setIcon(icon)  
        tools_tab_action.setShortcut("Ctrl+T")
        tools_tab_action.setStatusTip(tr["status_tools_tab"])
        tools_tab_action.triggered.connect(self.main_window.open_tools_tab)
        tools_menu.addAction(tools_tab_action)
        tools_menu.addSeparator()
        # Tool 4: Knowledge Database Manager
        knowledge_db_action = QAction(tr.get("knowledge_database", "Knowledge Database"), self.main_window)
        icon = QIcon("icons/database.svg")
        knowledge_db_action.setIcon(icon)
        knowledge_db_action.setShortcut("Ctrl+K")
        knowledge_db_action.setStatusTip(tr["status_knowledge_database"])
        knowledge_db_action.triggered.connect(self.main_window.open_knowledge_database)
        tools_menu.addAction(knowledge_db_action)
        tools_menu.addSeparator()
       
        # Tool 3: Insert Character
        insert_char_action = QAction(tr.get("insert_character", "Insert Character"), self.main_window)
        icon = QIcon("icons/insert_character.svg")
        insert_char_action.setIcon(icon)
        insert_char_action.setShortcut("Ctrl+R")
        insert_char_action.setStatusTip(tr.get("status_insert_character", "Insert special characters"))
        insert_char_action.triggered.connect(self.main_window.open_insert_character_tab)
        tools_menu.addAction(insert_char_action)
        tools_menu.addSeparator()
        # Tool 3: Spreadsheet
        spreadsheet_action = QAction(tr["spreadsheet"], self.main_window)
        icon = QIcon("icons/spreadsheet.svg")
        spreadsheet_action.setIcon(icon)          
        spreadsheet_action.setShortcut("Ctrl+E")
        spreadsheet_action.setStatusTip(tr["status_spreadsheet"])
        spreadsheet_action.triggered.connect(self.main_window.open_spreadsheet_tab)
        tools_menu.addAction(spreadsheet_action)
        tools_menu.addSeparator()      
       
        # Tool 3: DjVu Viewer
        djvu_viewer_action = QAction(tr["djvu_viewer"], self.main_window)
        icon = QIcon("icons/djvu.svg")  # provide an appropriate icon
        djvu_viewer_action.setIcon(icon)
        djvu_viewer_action.setShortcut("Ctrl+J")
        djvu_viewer_action.setStatusTip(tr["status_open_djvu_viewer_tab"])
        djvu_viewer_action.triggered.connect(self.main_window.open_djvu_tab)
        tools_menu.addAction(djvu_viewer_action)
        tools_menu.addSeparator()        
        
        # Tool 4: Todo List
        todo_list_action = QAction(tr["todo_list"], self.main_window)
        icon = QIcon("icons/todo.svg")
        todo_list_action.setIcon(icon)        
        todo_list_action.setShortcut("Ctrl+L")
        todo_list_action.setStatusTip(tr["status_todo_list"])
        todo_list_action.triggered.connect(self.main_window.open_todo_list_tab)
        tools_menu.addAction(todo_list_action)
        tools_menu.addSeparator()        
        # Tool 5: Insert Tikz code
        tikz_plotter_action = QAction(tr["tikz_plotter"], self.main_window)
        icon = QIcon("icons/tikz.svg")
        tikz_plotter_action.setIcon(icon)                
        tikz_plotter_action.setShortcut("Ctrl+P")
        tikz_plotter_action.setStatusTip(tr["status_tikz_plotter"])
        tikz_plotter_action.triggered.connect(self.main_window.tikz_plotter_tab)
        tools_menu.addAction(tikz_plotter_action)
        tools_menu.addSeparator()
        # Tool 6: AI Assistant
        ai_tab_action = QAction(tr["ai_assistant"], self.main_window)
        icon = QIcon("icons/ai.svg")
        ai_tab_action.setIcon(icon)
        ai_tab_action.setShortcut("Ctrl+I")
        ai_tab_action.setStatusTip(tr["status_ai_assistant"])
        ai_tab_action.triggered.connect(
            lambda: QTimer.singleShot(150, self.main_window.open_ai_tab)
        )
        tools_menu.addAction(ai_tab_action)
        tools_menu.addSeparator()
        # Tool 7: Latex Files comparison - FIXED: Simple triggered connection
        tex_compare_action = QAction(tr["compare_latex_files"], self.main_window)
        icon = QIcon("icons/compare_tex.svg")
        tex_compare_action.setIcon(icon)        
        tex_compare_action.setStatusTip(tr["status_compare_latex_files"])
        tex_compare_action.triggered.connect(self._open_latex_comparator_with_expand)
        tools_menu.addAction(tex_compare_action)       
        # Tool 8: Pdf files comparison - FIXED: Simple triggered connection
        pdf_compare_action = QAction(tr["compare_pdf_files"], self.main_window)
        icon = QIcon("icons/compare_pdf.svg")
        pdf_compare_action.setIcon(icon)                
        pdf_compare_action.setStatusTip(tr["status_compare_pdf_files"])
        pdf_compare_action.triggered.connect(self._open_pdf_comparison_with_expand)
        tools_menu.addAction(pdf_compare_action)

        self._setup_menu_close_protection()

    def _open_pdf_comparison_with_expand(self):
        """Open PDF comparison and expand PDF viewer"""
        try:
            if hasattr(self.main_window, 'pdf_manager'):
                self.main_window.pdf_manager._remove_welcome_tab_if_exists()          
            # First open the comparison tab
            self.open_pdf_comparison_tab_via_layout_manager()
            # Then expand PDF viewer (only if not already expanded)
            if not getattr(self.main_window, '_pdf_expanded', False):
                self.main_window.toggle_pdf_expand_width()
            # Hide output tabs
            if hasattr(self.main_window, 'output_tabs_visible') and self.main_window.output_tabs_visible:
                self.main_window.toggle_output_tabs()
                
            #self.main_window.side_panel.setVisible(False) 

            
                              
        except Exception as e:
            print(f"❌ Error opening PDF comparison: {e}")
            import traceback
            traceback.print_exc()

    def _open_latex_comparator_with_expand(self):
        """Open LaTeX comparator and expand editor"""
        try:
            # Track if welcome was removed
            welcome_was_showing = False
            if hasattr(self.main_window, 'editor_manager'):
                em = self.main_window.editor_manager
                # Check if only welcome tab exists
                if hasattr(em, 'editor_tabs') and em.editor_tabs:
                    if em.editor_tabs.count() == 1:
                        if em.editor_tabs.tabText(0) == "Welcome":
                            welcome_was_showing = True
                em._remove_welcome_tabs_if_needed()
            # Store this state so close knows to restore welcome
            self.main_window._comparator_replaced_welcome = welcome_was_showing
            # First open the comparator
            self.main_window.open_latex_comparator()
            # Then expand editor (only if not already expanded)
            if not getattr(self.main_window, '_editor_expanded', False):
                self.main_window.toggle_editor_expand_width()
            # Hide output tabs
            if hasattr(self.main_window, 'output_tabs_visible') and self.main_window.output_tabs_visible:
                self.main_window.toggle_output_tabs()
        except Exception as e:
            print(f"❌ Error opening LaTeX comparator: {e}")
            import traceback
            traceback.print_exc()

    def open_pdf_comparison_tab_via_layout_manager(self):
        """Open PDF comparison tab via layout manager - FIXED for welcome tab"""
        try:
            from pdf_comparison import PDFComparisonViewerSimplified
        except ImportError as e:
            QMessageBox.critical(self.main_window, "Error",f"PDF comparison module not found:\n{str(e)}")
            return
        try:
            # Check if layout_manager exists
            if not hasattr(self.main_window, 'layout_manager'):
                QMessageBox.critical(self.main_window, "Error", "Layout manager not available")
                return
            layout_manager = self.main_window.layout_manager
            # Ensure PDF container exists
            if not hasattr(layout_manager, 'pdf_container') or layout_manager.pdf_container is None:
                layout_manager._recreate_pdf_container()  # ✅ Use recreate instead
            # Check if we have pdf_manager
            if not hasattr(self.main_window, 'pdf_manager'):
                QMessageBox.critical(self.main_window, "Error", "PDF manager not available")
                return
            pdf_manager = self.main_window.pdf_manager
            # Handle both tabbed and H/V modes
            if pdf_manager.pdf_layout_mode == "tabbed":
                # Initialize PDF tabs if they don't exist OR if showing welcome
                if not hasattr(pdf_manager, 'pdf_tabs') or pdf_manager.pdf_tabs is None:
                    layout_manager._recreate_pdf_container()  # ✅ Use recreate
                    tab_widget = pdf_manager.pdf_tabs
                else:
                    tab_widget = pdf_manager.pdf_tabs
                    # Check if only welcome tab exists
                    if tab_widget.count() == 1 and tab_widget.tabText(0) == "Welcome":
                        layout_manager._recreate_pdf_container()  # ✅ Use recreate
                        tab_widget = pdf_manager.pdf_tabs
                if tab_widget is None:
                    QMessageBox.critical(self.main_window, "Error", "Could not initialize PDF tabs")
                    return
                # ✅ Remove welcome tab if it exists
                for i in reversed(range(tab_widget.count())):
                    tab_text = tab_widget.tabText(i)
                    if tab_text == "Welcome":
                        tab_widget.removeTab(i)
                        break
                # Create new comparison viewer
                comparison_viewer = PDFComparisonViewerSimplified(self.main_window)
                
                comparison_viewer.destroyed.connect(lambda: self.main_window.split_window_width())
                self.main_window.pdf_comparison_viewer = comparison_viewer
                # Remove existing comparison tab if present
                for i in range(tab_widget.count()):
                    if tab_widget.tabText(i) == "PDF Comparison":
                        tab_widget.removeTab(i)
                        break
                # Add new tab
                tab_index = tab_widget.addTab(comparison_viewer, "PDF Comparison")
                # Set SVG icon properly
                icon = QIcon("icons/compare_pdf.svg")
                tab_widget.setTabIcon(tab_index, icon)                        
                tab_widget.setCurrentIndex(tab_index)
                tab_widget.setTabsClosable(True)  # ✅ Enable close button
                # Ensure tab_widget is in the PDF container layout
                pdf_layout = layout_manager.pdf_container.layout()
                if pdf_layout and pdf_layout.indexOf(tab_widget) == -1:
                    # Clear layout first
                    while pdf_layout.count():
                        item = pdf_layout.takeAt(0)
                        if item.widget() and item.widget() != tab_widget:
                            item.widget().setParent(None)
                    pdf_layout.addWidget(tab_widget)
                # Force visibility and updates
                tab_widget.show()
                tab_widget.setVisible(True)
                comparison_viewer.show()
                layout_manager.pdf_container.update()
                layout_manager.pdf_container.repaint()
            else:
                # H/V mode
                if not hasattr(pdf_manager, 'pdf_splitter') or pdf_manager.pdf_splitter is None:
                    if hasattr(layout_manager, '_recreate_pdf_container'):
                        layout_manager._recreate_pdf_container()
                splitter = pdf_manager.pdf_splitter
                if not splitter:
                    QMessageBox.critical(self.main_window, "Error", "Could not initialize PDF splitter")
                    return
                # Remove welcome widget if it exists
                while splitter.count() > 0:
                    widget = splitter.widget(0)
                    widget.setParent(None)
                # Create new comparison viewer
                comparison_viewer = PDFComparisonViewerSimplified(self.main_window)
                
                comparison_viewer.destroyed.connect(lambda: self.main_window.split_window_width())
                self.main_window.pdf_comparison_viewer = comparison_viewer
                # Wrap in tab widget for consistency
                tab_widget = QTabWidget()
                tab_widget.addTab(comparison_viewer, "PDF Comparison")
                tab_widget.setTabsClosable(True)
                # Add to splitter
                splitter.addWidget(tab_widget)
            # Ensure the PDF container is visible
            #if hasattr(layout_manager, '_arrange_containers'):
            #    layout_manager._arrange_containers()
        except RuntimeError as e:
            # Force cleanup and retry
            if hasattr(self.main_window, 'pdf_comparison_viewer'):
                delattr(self.main_window, 'pdf_comparison_viewer')
            # Retry once
            if not hasattr(self, '_comparison_retry_attempted'):
                self._comparison_retry_attempted = True
                self.open_pdf_comparison_tab_via_layout_manager()
                delattr(self, '_comparison_retry_attempted')
            else:
                QMessageBox.critical(self.main_window, "Error","Could not create PDF comparison tab after cleanup attempt")
        except Exception as e:
            QMessageBox.critical(self.main_window, "Error",f"Failed to open PDF comparison tab:\n{str(e)}")
            import traceback
            traceback.print_exc()

    def toggle_pdf_expand_width(self):
        """Toggle PDF viewer expand width from menu"""
        # Find the current active PDF viewer
        current_pdf_viewer = None
        if hasattr(self, 'pdf_manager') and hasattr(self.pdf_manager, 'pdf_tabs'):
            tab_widget = self.pdf_manager.pdf_tabs
            current_widget = tab_widget.currentWidget()
            # Check if current widget is a PDF viewer
            if hasattr(current_widget, 'toggle_expand_width'):
                current_pdf_viewer = current_widget
            else:
                # Look for PDF viewers in the widget hierarchy
                pdf_viewers = current_widget.findChildren(PDFViewer) if current_widget else []
                if pdf_viewers:
                    current_pdf_viewer = pdf_viewers[0]
        if current_pdf_viewer:
            current_pdf_viewer.toggle_expand_width()
        else:
            QMessageBox.information(self.main_window, "Info", "No active PDF viewer found to toggle.")

    def _handle_output_toggle(self):
        """Handle output toggle from menu - ensures proper state sync"""
        self.main_window.toggle_output_tabs()
        # Force menu update after toggle
        #QTimer.singleShot(50, self._update_output_toggle_action)

    def _update_output_toggle_action(self):
        """Update output toggle action text and icon based on current state"""
        if not hasattr(self.main_window, 'menu_output_toggle_action'):
            return
        lang = self.main_window.menu_language  
        action = self.main_window.menu_output_toggle_action
        # Get actual current state from the main window
        actual_state = self.main_window.get_actual_output_state()
        # Update based on ACTUAL current state
        if actual_state:            
            action.setText(self.main_window.translations[lang]["hide_output"])
            action.setToolTip(self.main_window.translations[lang]["tooltip_hide_output"])
            action.setStatusTip(self.main_window.translations[lang]["status_hide_output"])
        else:            
            action.setText(self.main_window.translations[lang]["show_output"])
            action.setToolTip(self.main_window.translations[lang]["tooltip_show_output"])
            action.setStatusTip(self.main_window.translations[lang]["status_show_output"])

    # def update_menu_language(self):
        # """SAFE menu language update - ONLY update texts, don't recreate menus"""
        # # Just update the output toggle action text
        # self._update_output_toggle_action()
        # # NOTE: Add other specific text updates here if needed, but NEVER clear menuBar()

    def _compile_with_engine(self, engine):
        """Compile with specific engine and update global setting"""
        self.main_window.latex_engine = engine  # ✅ Update global engine
        self.main_window.compilation_manager.compile_latex(engine)        

    def _create_latex_menu(self):
        lang = self.main_window.menu_language        
        tr = self.main_window.translations[lang]
        latex_menu = self.main_window.menuBar().addMenu("&"+tr["latex_menu"])
        # ✅ Create Compile menu
        compile_menu = QMenu(tr["compile"], self.main_window)
        compile_menu.setToolTip(tr["tooltip_compile_latex_with_selected_engine"])
        compile_menu.setStatusTip(tr["status_compile"])
        # ✅ Add engine actions
        pdflatex_action = QAction(tr.get("pdflatex", "PDFLaTeX"), self.main_window)
        pdflatex_action.setStatusTip(tr.get("status_pdflatex", "Compile with pdfLaTeX"))
        pdflatex_action.triggered.connect(lambda: self._compile_with_engine("pdflatex"))
        compile_menu.addAction(pdflatex_action)
        xelatex_action = QAction(tr.get("xelatex", "XeLaTeX"), self.main_window)
        xelatex_action.setStatusTip(tr.get("status_xelatex", "Compile with XeLaTeX"))
        xelatex_action.triggered.connect(lambda: self._compile_with_engine("xelatex"))
        compile_menu.addAction(xelatex_action)
        lualatex_action = QAction(tr.get("lualatex", "LuaLaTeX"), self.main_window)
        lualatex_action.setStatusTip(tr.get("status_lualatex", "Compile with LuaLaTeX"))
        lualatex_action.triggered.connect(lambda: self._compile_with_engine("lualatex"))
        compile_menu.addAction(lualatex_action)
        # ✅ Set F5 shortcut to trigger current default engine
        compile_action = QAction(self.main_window)
        compile_action.setShortcut(QKeySequence("F5"))
        # Show "Compile F5" in the menu
        compile_menu.menuAction().setText(f'{tr["compile"]}\tF5')
        compile_action.triggered.connect(
            lambda: self.main_window.compilation_manager.compile_latex(self.main_window.latex_engine)
        )
        compile_action.setStatusTip(tr["status_compile"])
        self.main_window.addAction(compile_action)  
        # ✅ Apply icon to menu (shows on toolbar if added)
        self.icons_manager.apply_icon_to_action(compile_action, "compile")
        compile_menu.setIcon(compile_action.icon())
        # Add menu to LaTeX menu
        latex_menu.addMenu(compile_menu)
        # Save references
        self.main_window.compile_menu = compile_menu
        self.main_window.menu_compile_action = compile_action
        # Refresh
        refresh_action = QAction(tr["refresh_pdf"], self.main_window)
        refresh_action.setShortcut("F6")
        refresh_action.setStatusTip(tr["status_refresh_pdf"])
        refresh_action.triggered.connect(self.main_window.pdf_manager.refresh_pdf)  # ✅ Correct Refresh PDF
        self.icons_manager.apply_icon_to_action(refresh_action, "refresh")
        latex_menu.addAction(refresh_action)
        # Jump
        jump_action = QAction(tr.get("view_in_pdf", "Jump"), self.main_window)        
        jump_action.setShortcut("F7")
        jump_action.setStatusTip(tr.get("status_view_in_pdf", "Jump to the current line in PDF"))
        jump_action.triggered.connect(self.main_window.toolbar_manager.handle_jump_action)
        self.icons_manager.apply_icon_to_action(jump_action, "jump_in_pdf")  
        latex_menu.addAction(jump_action)        
        # ✅ Create Backmatter menu
        backmatter_menu = QMenu(tr.get("backmatter","Backmatter"), self.main_window)
        backmatter_menu.setToolTip("Compile bibliography, index, and glossary")
        backmatter_menu.setStatusTip(tr.get("status_backmatter", "Compile auxiliary LaTeX files"))
        # ✅ Add actions
        bibtex_action = QAction(tr.get("bibtex", "BibTeX"), self.main_window)
        bibtex_action.setStatusTip(tr.get("status_bibtex", "Run BibTeX on the current document"))
        bibtex_action.triggered.connect(lambda: self.main_window.backmatter_compile.compile_backmatter("bibtex"))
        makeindex_action = QAction(tr.get("makeindex", "MakeIndex"), self.main_window)
        makeindex_action.setStatusTip(tr.get("status_makeindex", "Run MakeIndex for index generation"))
        makeindex_action.triggered.connect(lambda: self.main_window.backmatter_compile.compile_backmatter("makeindex"))
        makeglossaries_action = QAction(tr.get("makeglossaries", "MakeGlossaries"), self.main_window)
        makeglossaries_action.setStatusTip(tr.get("status_makeglossaries", "Run MakeGlossaries for glossary generation"))
        makeglossaries_action.triggered.connect(lambda: self.main_window.backmatter_compile.compile_backmatter("makeglossaries"))
        # Add to menu
        backmatter_menu.addAction(bibtex_action)
        backmatter_menu.addAction(makeindex_action)
        backmatter_menu.addAction(makeglossaries_action)
        #  Backmatter compile
        backmatter_action = QAction(self.main_window)
        backmatter_action.setShortcut("F8")
        # Show "Backmatter    F8" in the menu
        backmatter_menu.menuAction().setText(f'{tr["backmatter"]}\tF8')           
        backmatter_action.triggered.connect(
            lambda: self.main_window.backmatter_compile.compile_backmatter(self.main_window.backmatter_engine)
        )
        backmatter_action.setStatusTip(tr.get("status_backmatter", "Compile bibliography, index, and glossary"))
        self.main_window.addAction(backmatter_action)  
        # ✅ Apply icon to menu (shows on toolbar if added)
        self.icons_manager.apply_icon_to_action(backmatter_action, "backmatter_compile")
        backmatter_menu.setIcon(backmatter_action.icon())
        # ✅ Add menu to LaTeX menu
        latex_menu.addMenu(backmatter_menu)
        # Save reference
        self.main_window.backmatter_menu = backmatter_menu
        self.main_window.backmatter_action = backmatter_action
        latex_menu.addSeparator()


        # Arabic tool        
        arabic_action = QAction(tr["arabic_tool"], self.main_window)
        arabic_action.triggered.connect(self.main_window.toolbar_manager.open_arabic_command_dialog)
        arabic_action.setShortcut("Alt+A")
        arabic_action.setStatusTip(tr["status_arabic_tool"])
        self.icons_manager.apply_icon_to_action(arabic_action, "arabic")
        latex_menu.addAction(arabic_action)        
        
        # Double language insertion tool 
        if hasattr(self, 'double_lang_action'):
            try:
                self.double_lang_action.triggered.disconnect()
            except Exception:
                pass

        self.double_lang_action = QAction(tr["double_lang_tool"], self.main_window)
        self.double_lang_action.setShortcut("Alt+B")        
        self.double_lang_action.setStatusTip(tr["status_double_lang_tool"])
        self.double_lang_action.triggered.connect(self.open_double_language_dialog)
        self.icons_manager.apply_icon_to_action(self.double_lang_action, "bilingual")        
        latex_menu.addAction(self.double_lang_action)

        # Toggle Text direction LR/RL
        if hasattr(self, 'text_dir_action'):
            self.main_window.toolbar_manager.text_dir_action.triggered.disconnect()  # Disconnect all connections
            self.main_window.toolbar_manager.removeAction(self.main_window.toolbar_manager.text_dir_action)
        text_dir_action = QAction(tr["direction"], self.main_window)
        text_dir_action.setShortcut("Alt+D")
        text_dir_action.setStatusTip(tr["status_direction"])
        text_dir_action.triggered.connect(self.main_window.toggle_text_direction)      
        self.icons_manager.apply_icon_to_action(text_dir_action, "direction")
        latex_menu.addAction(text_dir_action)

        latex_menu.addSeparator()
        
        math_menu = latex_menu.addMenu(f'{tr["insert_math"]}\tAlt+S')  
        self.math_menu_builder.create_comprehensive_menu(math_menu)        
        self.icons_manager.apply_icon_to_action(math_menu, "symbols")
        latex_commands_menu = latex_menu.addMenu(f'{tr["insert_latex_commands"]}\tAlt+C')
        self.latex_commands_menu_builder.create_comprehensive_menu(latex_commands_menu)
        self.icons_manager.apply_icon_to_action(latex_commands_menu, "latex_commands")
        
        latex_menu.addSeparator()
        
        # Show Tree
        tree = QAction(tr.get("show_tree", "Tree"), self.main_window)        
        tree.setText(f'{tr["show_tree"]}\tAlt+R')
        tree.setStatusTip(tr.get("status_tree", "Show/hide the document structure tree"))
        tree.triggered.connect(self.main_window.toolbar_manager.toggle_tree_tab)
        self.icons_manager.apply_icon_to_action(tree, "tree")
        latex_menu.addAction(tree)        
        # Show bookmarks
        bookmarks = QAction(tr.get("bookmarks", "bookmarks"), self.main_window)        
        bookmarks.setText(f'{tr["show_bookmarks"]}\tAlt+M')
        bookmarks.setStatusTip(tr.get("status_show_bookmarks", "Show/hide bookmarks panel"))
        bookmarks.triggered.connect(self.main_window.toolbar_manager.toggle_bookmarks_tab)
        self.icons_manager.apply_icon_to_action(bookmarks, "bookmarks")
        latex_menu.addAction(bookmarks)        
        # Show terminal
        terminal = QAction(tr.get("terminal", "terminal"), self.main_window)        
        terminal.setText(f'{tr["show_terminal"]}\tAlt+N')
        terminal.setStatusTip(tr.get("status_show_terminal", "Show/hide terminal output"))
        terminal.triggered.connect(self.main_window.toolbar_manager.toggle_terminal_tab)  
        self.icons_manager.apply_icon_to_action(terminal, "terminal")
        latex_menu.addAction(terminal)        

        self._setup_menu_close_protection()

    def open_double_language_dialog(self):
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]

        current_editor = self.main_window.editor_manager.get_current_editor()
        current_file = self.main_window.editor_manager.get_current_file_path()

        if not current_editor or not current_file:
            self.main_window.show_error(tr["no_file_open"], tr["open_a_latex_file"])
            return

        dialog = DoubleLanguagesInsertion(self.main_window, lang)

        # ✅ Step 1 goes here
        dialog.set_editor(current_editor)

        # ✅ non-modal dialog
        dialog.show()

    def update_language(self):
        """Update menus with current language"""
        self.main_window.menus_initialized = False
        self.create_menu_bar()

    def _create_options_menu(self):
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]
        options_menu = self.main_window.menuBar().addMenu("&"+self.main_window.translations[lang]["options_menu"])
        settings_action = QAction(self.main_window.translations[lang]["settings"], self.main_window)
        settings_action.setShortcut("F2")
        settings_action.setStatusTip(tr["status_settings"])
        settings_action.triggered.connect(self.main_window.settings_manager.open_settings)
        self.icons_manager.apply_icon_to_action(settings_action, "settings")
        options_menu.addAction(settings_action)

        if lang == "ar":
            self.main_window.menuBar().setLayoutDirection(Qt.RightToLeft)
            self.main_window.is_rtl = True
            self._setup_menu_close_protection()
        else:
            self.main_window.menuBar().setLayoutDirection(Qt.LeftToRight)
            self.main_window.is_rtl = False
            self._setup_menu_close_protection()
            
        lang_action = QAction(self.main_window.translations[lang]["language"], self.main_window)
        lang_action.setStatusTip(tr["status_language"])
        lang_action.setShortcut("F4")
        lang_action.triggered.connect(self.main_window.toggle_menu_language)
        self.icons_manager.apply_icon_to_action(lang_action, "language")
        options_menu.addAction(lang_action)

        self._setup_menu_close_protection()

    def refresh_current_pdf(self):
        """Refresh the currently open PDF"""
        current_file = self.editor_manager.current_file        
        if not current_file:
            return
        self.pdf_viewer.fit_width()
        # Build PDF path
        pdf_path = os.path.splitext(current_file)[0] + ".pdf"
        if os.path.exists(pdf_path):
            # Force reload in PDF manager
            self.pdf_manager.load_pdf_in_viewer(pdf_path)
        else:
            # Show message in status bar
            self.update_status_bar("PDF not found. Compile first.")

    def update_recent_pdf_files_menu(self):
        """Update the recent PDF files menu with current list"""
        if not hasattr(self, 'recent_pdf_files_menu') or not self.recent_pdf_files_menu:
            return

        self.recent_pdf_files_menu.clear()
        lang = self.main_window.menu_language

        if not hasattr(self.main_window, 'config_manager'):
            return

        recent_pdf_files = self.main_window.config_manager.get_recent_pdf_files()

        if not recent_pdf_files:
            no_files_action = QAction(
                self.main_window.translations[lang].get("no_recent_pdf_files", "No recent PDF files"),
                self.main_window
            )
            no_files_action.setEnabled(False)
            self.recent_pdf_files_menu.addAction(no_files_action)
            return

        from PyQt5.QtWidgets import (
            QScrollArea, QWidget, QVBoxLayout, QHBoxLayout,
            QToolButton, QWidgetAction, QSizePolicy
        )
        from PyQt5.QtCore import Qt

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(2, 2, 2, 2)
        scroll_layout.setSpacing(1)

        for i, file_path in enumerate(recent_pdf_files[:100]):
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(0)

            btn = QToolButton()
            btn.setText(f"   {file_path}")
            btn.setIcon(self.create_number_icon(i + 1))
            btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            btn.setToolTip(file_path)
            btn.setStatusTip(
                self.main_window.translations[lang].get(
                    "open_recent_pdf_status", "Open this recent PDF file"
                )
            )
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setAutoRaise(True)
            btn.setMinimumWidth(260)
            btn.clicked.connect(
                lambda checked, path=file_path: (
                    self.force_close_all_menus(),
                    #self.open_recent_pdf_file(path)
                    QTimer.singleShot(0, lambda: self.open_recent_pdf_file(path))
                )
            )

            remove_btn = QToolButton()
            remove_btn.setText("⨉")
            remove_btn.setAutoRaise(True)
            remove_btn.setToolTip("Remove from recent PDF files")
            remove_btn.setFixedWidth(28)
            remove_btn.clicked.connect(
                lambda checked, path=file_path: self._remove_recent_pdf_file_and_refresh(path)
            )

            row_layout.addWidget(btn)
            row_layout.addWidget(remove_btn)
            scroll_layout.addWidget(row_widget)

        scroll_area = QScrollArea()
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setMaximumHeight(400)
        scroll_area.setMinimumWidth(350)
        scroll_area.setFrameShape(QScrollArea.NoFrame)

        container_action = QWidgetAction(self.recent_pdf_files_menu)
        container_action.setDefaultWidget(scroll_area)
        self.recent_pdf_files_menu.addAction(container_action)

        self.recent_pdf_files_menu.addSeparator()

        clear_action = QAction(
            self.main_window.translations[lang].get("clear_recent_pdf_files", "Clear Recent PDF Files"),
            self.main_window
        )
        clear_action.setStatusTip(
            self.main_window.translations[lang].get(
                "clear_recent_pdf_files_status", "Remove all recent PDF files from the list"
            )
        )
        clear_action.triggered.connect(self.clear_recent_pdf_files)
        self.recent_pdf_files_menu.addAction(clear_action)

    def force_close_all_menus(self):
        """Forcibly close any open popup menu (including submenus)"""
        from PyQt5.QtWidgets import QApplication, QMenu
        # Close the active popup widget (the menu that is currently open)
        popup = QApplication.activePopupWidget()
        if popup and isinstance(popup, QMenu):
            popup.close()
        # Also close any top-level menus that might still be visible
        for widget in QApplication.topLevelWidgets():
            if widget.isVisible() and isinstance(widget, QMenu):
                widget.close()
        # Tell the menu bar to release its active action
        menu_bar = self.main_window.menuBar()
        if menu_bar:
            menu_bar.setActiveAction(None)
            menu_bar.clearFocus()
        # Force Qt to process pending close events
        QApplication.processEvents()

    def _remove_recent_pdf_file_and_refresh(self, file_path):
        """Remove a single PDF file from recent list and refresh the menu."""
        if hasattr(self.main_window, 'config_manager'):
            self.main_window.config_manager.remove_recent_pdf_file(file_path)
        self.update_recent_pdf_files_menu()
        
    
    # def open_recent_pdf_file(self, file_path):
        # """Open a PDF from the recent files list"""
        # if not os.path.exists(file_path):
            # print(f"❌ Recent PDF file not found: {file_path}")
            # # Remove from recent list since it doesn't exist
            # if hasattr(self.main_window, 'config_manager'):
                # self.main_window.config_manager.remove_recent_pdf_file(file_path)
                # # Update menu to reflect the removal
                # if hasattr(self.main_window, 'menu_manager') and hasattr(self.main_window.menu_manager, 'update_recent_pdf_files_menu'):
                    # self.main_window.menu_manager.update_recent_pdf_files_menu()
            # return None
        # # Load the PDF
        # viewer = self.main_window.pdf_manager.load_pdf_in_viewer(file_path)
        # if viewer:
            # # Move to top of recent list (since it was accessed again)
            # if hasattr(self.main_window, 'config_manager'):
                # self.main_window.config_manager.add_recent_pdf_file(file_path)
            # # Update menu
            # if hasattr(self.main_window, 'menu_manager') and hasattr(self.main_window.menu_manager, 'update_recent_pdf_files_menu'):
                # self.main_window.menu_manager.update_recent_pdf_files_menu()
            # self.main_window.update_status_bar(f"Recent PDF opened: {os.path.basename(file_path)}")
        # return viewer

    def open_recent_pdf_file(self, file_path):
        """Open a recent PDF file with wait cursor for large PDFs"""
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import Qt

        if not os.path.exists(file_path):
            print(f"❌ Recent PDF file not found: {file_path}")
            if hasattr(self.main_window, 'config_manager'):
                self.main_window.config_manager.remove_recent_pdf_file(file_path)
                if hasattr(self.main_window, 'menu_manager'):
                    self.main_window.menu_manager.update_recent_pdf_files_menu()
            return None

        # --- Show wait cursor ---
        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()

        try:
            # Load the PDF (may take time for large files)
            viewer = self.main_window.pdf_manager.load_pdf_in_viewer(file_path)
            if viewer:
                # Move to top of recent list
                if hasattr(self.main_window, 'config_manager'):
                    self.main_window.config_manager.add_recent_pdf_file(file_path)
                # Update menu
                if hasattr(self.main_window, 'menu_manager'):
                    self.main_window.menu_manager.update_recent_pdf_files_menu()
                self.main_window.update_status_bar(f"Recent PDF opened: {os.path.basename(file_path)}")
            return viewer
        finally:
            # Restore normal cursor
            QApplication.restoreOverrideCursor()

    def remove_recent_pdf_file(self, file_path):
        """Remove a specific PDF file from the recent list."""
        if not file_path:
            return
        try:
            abs_path = os.path.abspath(file_path)
            current_files = self.get_recent_pdf_files(max_count=100)
            if abs_path in current_files:
                current_files.remove(abs_path)
                self._save_recent_pdf_files(current_files[:self.recent_pdf_files_limit])
        except Exception as e:
            print(f"❌ Error removing recent PDF file: {e}")

    def clear_recent_pdf_files(self):
        """Clear all recent PDF files from the list."""
        from PyQt5.QtWidgets import QMessageBox, QTabWidget
        # ✅ Add confirmation dialog
        reply = QMessageBox.question(
            self.main_window,
            "Clear Recent PDF Files",
            "Are you sure you want to clear all recent PDF files?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                # ✅ FIX: Access config through config_manager
                if hasattr(self.main_window, 'config_manager'):
                    self.main_window.config_manager.clear_recent_pdf_files()
                    # Update the menu to reflect changes
                    self.update_recent_pdf_files_menu()
                    # Refresh the PDF welcome page immediately if it is currently showing.
                    # pdf_tabs.widget(0) can carry any of these objectNames depending
                    # on which code path created the welcome tab.
                    pm = getattr(self.main_window, 'pdf_manager', None)
                    if pm:
                        pdf_tabs = getattr(pm, 'pdf_tabs', None)
                        welcome_showing = False
                        if isinstance(pdf_tabs, QTabWidget):
                            if pdf_tabs.count() == 1:
                                w = pdf_tabs.widget(0)
                                if w and w.objectName() in (
                                    "pdf_welcome_outer_frame",
                                    "pdf_welcome_widget",
                                    "pdf_welcome_tab",
                                ):
                                    welcome_showing = True
                        if welcome_showing:
                            QTimer.singleShot(0, pm._show_pdf_welcome_tab)
                else:
                    QMessageBox.warning(
                        self.main_window,
                        "Error",
                        "Configuration manager not available."
                    )
            except Exception as e:
                print(f"❌ Error clearing recent PDF files: {e}")
                QMessageBox.critical(
                    self.main_window,
                    "Error",
                    f"Failed to clear recent PDF files:\n{str(e)}"
                )

    def get_recent_pdf_files_for_menu(self):
        """Get recent PDF files formatted for menu display with existence check."""
        recent_files = self.get_recent_pdf_files()
        menu_items = []
        for i, file_path in enumerate(recent_files, 1):
            # Extract just the filename for display
            filename = os.path.basename(file_path)
            # Check if file still exists
            if os.path.exists(file_path):
                menu_items.append(f"{i}. {filename}")
            else:
                menu_items.append(f"{i}. {filename} (missing)")
        return menu_items, recent_files  

    # ─────────────────────────────────────────────────────────────────────────
    # Master Document helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _update_master_actions_state(self):
        """Enable/disable and relabel master document menu actions."""
        em = self.main_window.editor_manager
        current_file  = em.get_current_file_path()
        master_file   = em.get_master_document()
        has_tex_open  = bool(current_file and current_file.lower().endswith('.tex'))

        # "Set as Master" — enabled when a saved .tex file is active AND it is
        # not already the master.
        already_master = (master_file is not None and master_file == current_file)
        self.set_master_action.setEnabled(has_tex_open and not already_master)

        # Show which file is currently the master in the action text
        if master_file:
            label = self.main_window.translations[self.main_window.menu_language].get(
                "set_master_document", "Set as Master Document"
            )
            self.set_master_action.setText(label)
            self.clear_master_action.setEnabled(True)
            self.clear_master_action.setText(
                self.main_window.translations[self.main_window.menu_language].get(
                    "clear_master_document", "Clear Master Document"
                ) + f"  [{os.path.basename(master_file)}]"
            )
        else:
            self.set_master_action.setText(
                self.main_window.translations[self.main_window.menu_language].get(
                    "set_master_document", "Set as Master Document"
                )
            )
            self.clear_master_action.setEnabled(False)
            self.clear_master_action.setText(
                self.main_window.translations[self.main_window.menu_language].get(
                    "clear_master_document", "Clear Master Document"
                )
            )

    def _set_master_document(self):
        """Slot: set the currently active .tex file as the master document."""
        em = self.main_window.editor_manager
        current_file = em.get_current_file_path()

        if not current_file:
            QMessageBox.warning(
                self.main_window,
                self.main_window.translations[self.main_window.menu_language].get(
                    "no_file_open", "No file open"
                ),
                self.main_window.translations[self.main_window.menu_language].get(
                    "open_a_latex_file",
                    "Please open a LaTeX file first."
                )
            )
            return

        try:
            em.set_master_document(current_file)
            self._update_master_actions_state()
            QMessageBox.information(
                self.main_window.window(),
                self.main_window.translations[self.main_window.menu_language].get(
                    "master_document_set", "Master Document Set"
                ),
                self.main_window.translations[self.main_window.menu_language].get(
                    "master_document_set_msg",
                    "Master document set to:\n{file}\n\n"
                    "Compilation will now always use this file, regardless of "
                    "which tab is active."
                ).format(file=current_file)
            )
        except ValueError as e:
            QMessageBox.warning(self.main_window.window(), "Master Document", str(e))

    def _clear_master_document(self):
        """Slot: remove the master document designation."""
        em = self.main_window.editor_manager
        old_master = em.get_master_document()
        em.clear_master_document()
        self._update_master_actions_state()
        if old_master:
            QMessageBox.information(
                self.main_window.window(),
                self.main_window.translations[self.main_window.menu_language].get(
                    "master_document_cleared", "Master Document Cleared"
                ),
                self.main_window.translations[self.main_window.menu_language].get(
                    "master_document_cleared_msg",
                    "Master document designation removed.\n\n"
                    "Compilation will now target the foreground (active) file."
                )
            )

    def show_error(self, title, message):
        """Show error message dialog"""
        QMessageBox.critical(self.main_window, title, message)

    def _create_help_menu(self):
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]
        help_menu = self.main_window.menuBar().addMenu("&"+tr.get("help", "Help"))
        
        
        plugin_help_action = QAction("&"+tr.get("how_to_make_tikz_plugins", "How to Make Tikz Plugins"), self.main_window)
        plugin_help_action.setStatusTip(tr.get("status_how_to_make_tikz_plugins", "Learn how to create custom TikZ plugins"))
        plugin_help_action.triggered.connect(self.show_plugins_help)
        help_menu.addAction(plugin_help_action)
        
        help_menu.addSeparator()
        
        shortcuts_action = QAction("&"+tr.get("keyboard_shortcuts", "Keyboard Shortcuts"), self.main_window)
        shortcuts_action.setShortcut("Ctrl+F1")
        shortcuts_action.setStatusTip(tr.get("status_keyboard_shortcuts", "View all keyboard shortcuts"))
        shortcuts_action.triggered.connect(self.show_shortcuts_help)
        help_menu.addAction(shortcuts_action)
        
        help_menu.addSeparator()
        
        tip_day_action = QAction("&"+tr.get("tip_of_the_day", "Tip of the day"), self.main_window)        
        tip_day_action.setStatusTip(tr.get("status_show_tip_of_the_day", "Show tip of the day"))        
        tip_day_action.triggered.connect(lambda: self.main_window.show_tip_of_the_day(force=True))
        help_menu.addAction(tip_day_action)
        
        help_menu.addSeparator()

        log_action = QAction("&" + tr.get("view_ayntex_error_log", "View AynTex Error Log"), self.main_window)
        log_action.setStatusTip(tr.get("status_view_ayntex_error_log", "View AynTex error and freeze log"))
        log_action.triggered.connect(lambda: ErrorsManager.open_log_viewer(parent=self.main_window))
        help_menu.addAction(log_action)

        # QAction has no aboutToShow — attach to the menu instead
        help_menu.aboutToShow.connect(lambda: log_action.setText(
            "&" + tr.get("view_ayntex_error_log", "View AynTex Error Log") + ("  ⚠" if ErrorsManager.has_errors() else "")
        ))
        
        help_menu.addSeparator()        
        
        about_action = QAction(tr.get("about", "About AynTex"), self.main_window)
        about_action.setShortcut("F1")
        about_action.setStatusTip(tr.get("status_about", "Information about AynTeX"))
        about_action.triggered.connect(self.show_about_dialog)
        self.icons_manager.apply_icon_to_action(about_action, "help")
        help_menu.addAction(about_action)
        
        self._setup_menu_close_protection()

    def show_plugins_help(self):
        """Show the plugin creation help dialog"""
        from help_manager import PluginHelpDialog
        dialog = PluginHelpDialog(self.main_window)
        dialog.exec_()

    def show_about_dialog(self):
        """Show the about dialog"""
        from help_manager import AboutDialog
        dialog = AboutDialog(self.main_window)
        dialog.exec_()

    def show_shortcuts_help(self):
        from help_manager import ShortcutsDialog
        dialog = ShortcutsDialog(self.main_window)
        dialog.exec_()
