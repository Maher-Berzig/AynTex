# toolbar_manager.py
"""
Toolbar Manager - Handles toolbar creation and management
"""
import os
import sys
from PyQt5.QtWidgets import (
    QToolBar, QToolButton,  QFrame,   QListWidgetItem, 
    QPlainTextEdit, QTabWidget, QVBoxLayout, QWidget, QLabel, QSizePolicy, QTreeWidget, QTreeWidgetItem, 
    QTextEdit, QPushButton, QListWidget, QSplitter, QMenu, QAction, QScrollArea, QGridLayout, QStyle, QCheckBox,
    QMessageBox, QFileDialog, QApplication, QDialog, QHBoxLayout, QDialogButtonBox, QComboBox, QShortcut    
)

from PyQt5.QtCore import Qt, QPoint, QSize, QTimer, QObject, pyqtSignal
from PyQt5.QtGui import QFont, QKeySequence,  QTextCursor, QIcon, QPixmap, QPainter, QBrush, QPen, QPainterPath, QColor
from icons_manager import IconsManager

from search_replace_dialog import SearchReplaceDialog



# Safe import for Arabic Command 
try:
    from arabic_command_dialog import ArabicCommandDialog
    ARABIC_DIALOG_AVAILABLE = True
except ImportError:
    ARABIC_DIALOG_AVAILABLE = False
    print("Warning: arabic_command_dialog.py not found. Arabic command button will show an info message.")

# Safe import for Math Symbols Menu
try:
    from math_symbols_menu import MathSymbolsMenu
    MATH_SYMBOLS_AVAILABLE = True
except ImportError:
    MATH_SYMBOLS_AVAILABLE = False
    print("Warning: math_symbols_menu.py not found. Math symbols button will show an info message.")

# Safe import for Latex Commands Menu
try:
    from latex_commands_menu import LatexCommandsMenu
    LATEX_COMMANDS_AVAILABLE = True
except ImportError:
    LATEX_COMMANDS_AVAILABLE = False
    print("Warning: latex_commands_menu.py not found. Latex commands button will show an info message.")
    

class ToolbarManager:
    def __init__(self, main_window):
        self.main_window = main_window
        self.icons_manager = main_window.icons_manager 
        self.main_toolbar = None
        text_dir_action = self.main_window.is_rtl        
        self.bookmarks_action = None
        
        # Initialize tab visibility states - sync with main_window
        self.symbols_tab_visible = getattr(main_window, 'symbols_tab_visible', False)
        self.commands_tab_visible = getattr(main_window, 'commands_tab_visible', False)
        self.tree_tab_visible = getattr(main_window, 'tree_tab_visible', False)
        self.bookmarks_tab_visible = getattr(main_window, 'bookmarks_tab_visible', False)
        self.terminal_tab_visible = getattr(main_window, 'terminal_tab_visible', False)
        
        icons_manager = IconsManager(icons_folder="icons")
        self.main_window = main_window
        self.icons_manager = icons_manager
        
        # ✅ ADD: Double-click protection timers
        self._last_compile_click_time = 0
        self._last_backmatter_click_time = 0
        self._click_debounce_ms = 500 
        
        # Initialize symbol and command handlers
        self.math_symbols_handler = MathSymbolsMenu(
            main_window, 
            main_window.editor_manager.insert_latex_command,
            main_window.menu_language
        )
        self.latex_commands_handler = LatexCommandsMenu(
            main_window,
            main_window.editor_manager.insert_latex_command, 
            main_window.menu_language
        )


    def _is_debounced(self, last_click_time):
        """Check if click should be ignored due to debouncing"""
        import time
        current_time = time.time() * 1000  # Convert to milliseconds
        if current_time - last_click_time < self._click_debounce_ms:
            return True
        return False
       
       
    def create_main_toolbar(self):
        """Create the main toolbar"""        
        
        # Synchronously remove all "Main" toolbars
        for toolbar in self.main_window.findChildren(QToolBar):
            if toolbar.windowTitle() == "Main":
                self.main_window.removeToolBar(toolbar)
                toolbar.setParent(None)  # ← synchronous, forces immediate destruction
                del toolbar
        self.main_toolbar = None
                
        self.main_toolbar = self.main_window.addToolBar("Main")
        self.main_toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)       
        
        current_fonts = self.main_window.get_current_font_settings()
        ui_font_family = current_fonts.get('ui_font_family', 'Arial')
        ui_font_size = current_fonts.get('toolbar_font_size', 10)  # ← ADD THIS
        
        # Create font with BOTH family and size
        font = QFont(ui_font_family, ui_font_size)
        self.main_toolbar.setFont(font)
        
       
        #self.main_toolbar.setToolButtonStyle(Qt.ToolButtonIconOnly)# Set icon-only mode (removes text labels below icons)

            
        self.main_toolbar.setIconSize(QSize(30, 30))
        self.main_toolbar.setStyleSheet("QToolBar { spacing: 2px; } QToolButton { padding: 2px; }")
        #self.main_window.addToolBar(self.main_toolbar)        
        
        self._create_file_actions()
        #self.main_toolbar.addSeparator()
        self._create_edit_actions()
        self.main_toolbar.addSeparator()
        self._create_latex_actions()
        self.main_toolbar.addSeparator()
        self._create_arabic_actions()
        self.main_toolbar.addSeparator()

        # Replace menu-based symbols/commands with toggle buttons
        self._create_symbols_toggle()
        self._create_commands_toggle()
        # Add tree button
        self._create_tree_toggle()
        # Add bookmarks button
        self._create_bookmarks_toggle()
        # Add terminal button
        #self._create_terminal_toggle()
        self.main_toolbar.addSeparator()
        self._create_view_actions()
        self.main_toolbar.addSeparator()
        self._create_settings_actions()

        # Apply font to all toolbar buttons AFTER creating actions
        self._apply_font_to_toolbar_buttons(font)
        
        # Add context menu to toolbar
        self.main_toolbar.setContextMenuPolicy(Qt.CustomContextMenu)
        self.main_toolbar.customContextMenuRequested.connect(self.show_toolbar_context_menu)
        
        # Force UI refresh
        self.main_toolbar.update()
        self.main_toolbar.repaint()
        self.main_window.update()        

    def _apply_font_to_toolbar_buttons(self, font):
        """Apply font to all toolbar button widgets"""
        if not self.main_toolbar:
            return
        
        for action in self.main_toolbar.actions():
            widget = self.main_toolbar.widgetForAction(action)
            if widget:
                widget.setFont(font)
        
    def show_toolbar_context_menu(self, position):
        """Show context menu for toolbar"""
        menu = QMenu(self.main_window)
        
        # Hide toolbar action
        hide_action = QAction("Hide Toolbar (F10)", self.main_window)
        hide_action.triggered.connect(lambda: self.main_window.menu_manager.toggle_main_toolbar())
        menu.addAction(hide_action)
        
        # Customize toolbar action (optional)
        # customize_action = QAction("Customize Toolbar...", self.main_window)
        # customize_action.triggered.connect(self.customize_toolbar)
        # menu.addAction(customize_action)
        
        # Show menu at cursor position
        menu.exec_(self.main_toolbar.mapToGlobal(position))
    
    def _create_file_actions(self):
        """Create file-related toolbar actions"""
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]
        
        # New File
        new_action = QAction(tr["new"], self.main_window)
        #new_action.setShortcut("Ctrl+N")
        new_action.setToolTip(tr["tooltip_new"])
        new_action.triggered.connect(self.main_window.editor_manager.new_file)
        self.icons_manager.apply_icon_to_action(new_action, "new")
        self.main_toolbar.addAction(new_action)
        
        # Open File      
        open_action = QAction(tr["open"], self.main_window)
        #open_action.setShortcut("Ctrl+O")
        open_action.setToolTip(tr["tooltip_open"])
        open_action.triggered.connect(self.main_window.editor_manager.open_file)
        self.icons_manager.apply_icon_to_action(open_action, "open")
        self.main_toolbar.addAction(open_action)
        
        
        # Open PDF - FIXED: Added missing Open PDF button
        open_pdf_action = QAction(tr["open_pdf"], self.main_window)
        #open_pdf_action.setShortcut("Ctrl+Shift+O")
        open_pdf_action.setToolTip(tr["tooltip_open_pdf"])
        open_pdf_action.triggered.connect(self.main_window.pdf_manager.open_pdf_file)
        self.icons_manager.apply_icon_to_action(open_pdf_action, "pdf")
        self.main_toolbar.addAction(open_pdf_action)
        
        # Save File
        save_action = QAction(tr["save"], self.main_window)
        #save_action.setShortcut("Ctrl+S")
        save_action.setToolTip(tr["tooltip_save"])
        save_action.triggered.connect(self.main_window.editor_manager.save_file)
        self.icons_manager.apply_icon_to_action(save_action, "save")
        self.main_toolbar.addAction(save_action)
        
        
    def _create_edit_actions(self):
        """Create edit-related toolbar actions"""
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]
        # Cut, Copy, Paste
        for text, shortcut, icon, func in [
            ("cut", "Ctrl+X", "cut", "cut"),
            ("copy", "Ctrl+C", "copy", "copy"),
            ("paste", "Ctrl+V", "paste", "paste")
        ]:
            action = QAction(tr[text], self.main_window)
            action.setShortcut(shortcut)
            #action.setToolTip(tr["tooltip_copy"])
            action.triggered.connect(
                lambda checked, f=func: getattr(self.main_window.editor_manager.get_current_editor(), f, lambda: None)()
                if self.main_window.editor_manager.get_current_editor() else None
            )
            self.icons_manager.apply_icon_to_action(action, icon)
            #self.main_toolbar.addAction(action)
        
        # Undo
        undo_action = QAction(tr["undo"], self.main_window)
        #undo_action.setShortcut("Ctrl+Z")
        undo_action.setToolTip(tr["tooltip_undo"])
        undo_action.triggered.connect(
            lambda: (
                self.show_error(tr["no_file_open"], tr["open_a_latex_file"])
                if not (self.main_window.editor_manager.get_current_editor() and 
                        self.main_window.editor_manager.get_current_file_path())
                else self.main_window.editor_manager.get_current_editor().undo()
            )
        )
        if lang == "ar":
            self.icons_manager.apply_icon_to_action_mirrored(undo_action, "undo", self._get_icon_angle())
        else:
            self.icons_manager.apply_icon_to_action(undo_action, "undo")
        self.main_toolbar.addAction(undo_action)
        
        # Redo
        redo_action = QAction(tr["redo"], self.main_window)
        #redo_action.setShortcut("Ctrl+Y")
        redo_action.setToolTip(tr["tooltip_redo"])
        redo_action.triggered.connect(
            lambda: (
                self.show_error(tr["no_file_open"], tr["open_a_latex_file"])
                if not (self.main_window.editor_manager.get_current_editor() and 
                        self.main_window.editor_manager.get_current_file_path())
                else self.main_window.editor_manager.get_current_editor().redo()
            )
        )
        if lang == "ar":
            self.icons_manager.apply_icon_to_action_mirrored(redo_action, "redo", self._get_icon_angle())
        else:
            self.icons_manager.apply_icon_to_action(redo_action, "redo")
        self.main_toolbar.addAction(redo_action)
        
        # Find / Replace
        find_action = QAction(tr.get("find", "Find"), self.main_window)
        #find_action.setShortcut("Ctrl+F")
        find_action.triggered.connect(self.main_window.show_find_dialog)
        self.icons_manager.apply_icon_to_action(find_action, "find")
        self.main_toolbar.addAction(find_action)
            
    def _create_latex_actions(self):
        """Create LaTeX-related toolbar actions with unified compile/stop button"""
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]
        #print(f"DEBUG _create_latex_actions lang={lang}, refresh_pdf={tr.get('refresh_pdf')}")
        # Create unified compile/stop toggle action
        self.compile_action = QAction(self.main_window.latex_engine, self.main_window)
        #self.compile_action.setShortcut("F5")
        self.compile_action.setToolTip(
            tr["tooltip_compile"].format(self.main_window.latex_engine)
        )
        
        # Connect to our unified handler instead of directly to compilation_manager
        self.compile_action.triggered.connect(self.handle_compile_action)        
        #self.icons_manager.apply_icon_to_action(self.compile_action, "compile")
        if lang == "ar":
            self.icons_manager.apply_icon_to_action_mirrored(self.compile_action, "compile", self._get_icon_angle())
        else:
            self.icons_manager.apply_icon_to_action(self.compile_action, "compile")
        
        self.main_window.toolbar_compile_action = self.compile_action  # For backward compatibility
        self.main_toolbar.addAction(self.compile_action)
        
        # Create hidden stop action for compatibility with existing update_compile_actions
        self.stop_action = QAction("Stop", self.main_window)
        self.stop_action.setVisible(False)  # Hidden, just for compatibility
        self.main_window.toolbar_stop_action = self.stop_action
        
        # ✅ Get the actual QToolButton and fix its size
        self.compile_button = self.main_toolbar.widgetForAction(self.compile_action)
        if self.compile_button:
            self.compile_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.compile_button.setMinimumWidth(80)  # Wider to fit engine names
            self.compile_button.setMaximumWidth(120)  # Allow some flexibility
            
       
        # Initialize state tracking
        self._compiling = False
        
        # Update button text to show current engine
        self.update_compile_button_text()
        
        # Refresh PDF action (unchanged)
        self.refresh_action = QAction(
            tr["refresh_pdf"], self.main_window
        )
        #self.refresh_action.setShortcut("F6")
        self.refresh_action.setToolTip(
            tr["tooltip_refresh_pdf"]
        )
        self.refresh_action.triggered.connect(self.main_window.pdf_manager.refresh_pdf)
        self.icons_manager.apply_icon_to_action(self.refresh_action, "refresh")
        self.main_window.toolbar_refresh_action = self.refresh_action
        self.main_toolbar.addAction(self.refresh_action)
        
        # View/SyncTeX Forward Search action
        self.jump_action = QAction(
            tr.get("jump_in_pdf", "Jump"), self.main_window
        )
        #self.jump_action.setShortcut("F7")
        self.jump_action.setToolTip(
            tr.get("tooltip_jump_in_pdf", "Jump to current line in PDF")
        )
        self.jump_action.triggered.connect(self.handle_jump_action)
        self.icons_manager.apply_icon_to_action(self.jump_action, "jump_in_pdf") 
        #self.main_window.toolbar_jump_action = self.jump_action
        self.main_toolbar.addAction(self.jump_action)
        
        # Backmatter compile
        self.backmatter_action = QAction(self.main_window.backmatter_engine, self.main_window)
        # self.backmatter_action.setShortcut("F8")
        self.backmatter_action.setToolTip(
            tr["tooltip_backmatter_compile"].format(self.main_window.backmatter_engine)
        )
        
        # Key fix: Connect to our unified handler instead of directly to compilation_manager
        self.backmatter_action.triggered.connect(self.handle_backmatter_action)
        
        #self.icons_manager.apply_icon_to_action(self.backmatter_action, "backmatter_compile")
        if lang == "ar":
            self.icons_manager.apply_icon_to_action_mirrored(self.backmatter_action, "backmatter_compile", self._get_icon_angle())
        else:
            self.icons_manager.apply_icon_to_action(self.backmatter_action, "backmatter_compile")
        
        self.main_window.toolbar_backmatter_action = self.backmatter_action  # For backward compatibility
        self.main_toolbar.addAction(self.backmatter_action)
        
        # Create hidden stop action for compatibility with existing update_compile_actions
        self.backmatter_stop_action = QAction("Stop", self.main_window)
        self.backmatter_stop_action.setVisible(False)  # Hidden, just for compatibility
        self.main_window.toolbar_backmatter_stop_action = self.backmatter_stop_action
        
        # ✅ Get the actual QToolButton and fix its size
        button2 = self.main_toolbar.widgetForAction(self.backmatter_action)
        if button2:
            button2.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            button2.setMinimumWidth(70)  # Fits "Compile" comfortably
            button2.setMaximumWidth(0)
        
        # Initialize state tracking
        self.backmatter_compiling = False
        
        # Update button text to show current engine
        self.update_backmatter_compile_button_text()

    def _get_icon_angle(self):
        """Return rotation angle based on current language direction"""
        return 180 if self.main_window.menu_language == "ar" else 0
        
    def update_language(self):
        """Update toolbar with current language"""
        # Recreate toolbar with new language
        self.create_main_toolbar()
        self.math_symbols_handler.build_symbol_categories()  # ← rebuild translations
        self._create_symbols_widget()                         # ← then rebuild UI        
        
        
    def update_compile_button_text(self):
        """Update the compile button text to show current LaTeX engine"""
        if hasattr(self, 'compile_action') and self.compile_action:
            lang = getattr(self.main_window, 'menu_language', 'en')
            tr = self.main_window.translations.get(lang, {})
            if self._compiling:
                self.compile_action.setText(tr.get("stop", "Stop"))
                self.compile_action.setToolTip(tr.get("stop_compilation", "Stop compilation"))
                if hasattr(self, 'icons_manager'):
                    self.icons_manager.apply_icon_to_action(self.compile_action, "stop")
            else:
                engine = str(getattr(self.main_window, 'latex_engine', 'pdflatex')).strip()
                # Look up translated engine name, fall back to raw name
                engine_title = tr.get(engine, engine.replace('_', ' ').title())
                self.compile_action.setText(engine_title)
                #print("="*20,engine_title)
                tooltip_template = tr.get("tooltip_compile", "Compile with {}")
                self.compile_action.setToolTip(tooltip_template.format(engine_title))
                if hasattr(self, 'icons_manager'):
                    #self.icons_manager.apply_icon_to_action(self.compile_action, "compile")
                    self.icons_manager.apply_icon_to_action_rotated(self.compile_action, "compile", self._get_icon_angle())

    def update_backmatter_compile_button_text(self):
        """Update the compile button text to show current LaTeX engine"""
        if hasattr(self, 'backmatter_action') and self.backmatter_action:
            lang = getattr(self.main_window, 'menu_language', 'en')
            tr = self.main_window.translations.get(lang, {})
            if self.backmatter_compiling:
                self.backmatter_action.setText(tr.get("stop", "Stop"))
                self.backmatter_action.setToolTip(tr.get("stop_compilation", "Stop compilation"))
                if hasattr(self, 'icons_manager'):
                    self.icons_manager.apply_icon_to_action(self.backmatter_action, "stop")
            else:
                backmatter_engine = str(getattr(self.main_window, 'backmatter_engine', 'bibtex')).strip()
                # Look up translated engine name, fall back to raw name
                backmatter_title = tr.get(backmatter_engine, backmatter_engine.replace('_', ' ').title())
                self.backmatter_action.setText(backmatter_title)
                tooltip_template = tr.get("tooltip_backmatter_compile", "Compile with {}")
                self.backmatter_action.setToolTip(tooltip_template.format(backmatter_title))  # ← bug fixed
                if hasattr(self, 'icons_manager'):
                    #self.icons_manager.apply_icon_to_action(self.backmatter_action, "backmatter_compile")
                    self.icons_manager.apply_icon_to_action_rotated(self.backmatter_action, "backmatter_compile", self._get_icon_angle())

    def handle_compile_action(self):
        """Handle the unified compile/stop button click"""
        
        import time
        current_time = time.time() * 1000  # Convert to milliseconds
        
        # ✅ Debounce check - ignore rapid clicks
        if self._is_debounced(self._last_compile_click_time):
            #print("⚠️ Ignoring rapid compile button click")
            return
            
        self._last_compile_click_time = current_time  
            
        lang = self.main_window.menu_language 
        tr = self.main_window.translations[lang]                                        
        current_editor = self.main_window.editor_manager.get_current_editor()
        current_file = self.main_window.editor_manager.get_current_file_path()
        
        if not current_editor or not current_file:
            self.show_error(tr["no_file_open"], tr["open_a_latex_file"])
            return

        try:
            if self._compiling:
                # Currently compiling, so stop
                self.main_window.compilation_manager.stop_compilation()
                self._compiling = False
                self.update_compile_button_text()
            else:
                # Not compiling, so start
                self._compiling = True
                self.update_compile_button_text()
                self.main_window.compilation_manager.compile_latex()
        except Exception as e:
            print(f"Error in handle_compile_action: {e}")
            import traceback
            traceback.print_exc()
            # Reset state on error
            self._compiling = False
            self.update_compile_button_text()

    def on_compilation_started(self):
        """Called when compilation starts"""
        self._compiling = True
        self.update_compile_button_text()

    def on_compilation_finished(self):
        """Called when compilation finishes"""
        self._compiling = False
        self.update_compile_button_text()

    def update_engine_in_button(self, new_engine):
        """Update button text when LaTeX engine changes"""
        if hasattr(self.main_window, 'latex_engine'):
            self.main_window.latex_engine = new_engine
        self.update_compile_button_text()   
        
    def handle_backmatter_action(self):
        """Handle the unified compile/stop button click"""
        
        import time
        current_time = time.time() * 1000  # Convert to milliseconds
        
        # ✅ Debounce check - ignore rapid clicks
        if self._is_debounced(self._last_backmatter_click_time):
            #print("⚠️ Ignoring rapid backmatter button click")
            return
            
        self._last_backmatter_click_time = current_time    

        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]                                        
        current_editor = self.main_window.editor_manager.get_current_editor()
        current_file = self.main_window.editor_manager.get_current_file_path()
        
        if not current_editor or not current_file:
            self.show_error(tr["no_file_open"], tr["open_a_latex_file"])
            return


        try:
            if self.backmatter_compiling:
                # Currently compiling, so stop
                self.main_window.backmatter_compile._cancel_process()
                self.backmatter_compiling = False
                self.update_backmatter_compile_button_text()
            else:
                # Not compiling, so start
                self.backmatter_compiling = True
                self.update_backmatter_compile_button_text()
                self.main_window.backmatter_compile.compile_backmatter(self.main_window.backmatter_engine)
        except Exception as e:
            print(f"Error in handle_compile_action: {e}")
            import traceback
            traceback.print_exc()
            

    def update_compile_actions(self, compiling=False):
        """Update compile/stop button based on compilation state"""
        self._compiling = compiling

        if hasattr(self, 'compile_action') and self.compile_action:
            if compiling:
                self.compile_action.setText("Stop")
                self.compile_action.setToolTip("Stop compilation (F5)")
                self.icons_manager.apply_icon_to_action(self.compile_action, "stop")
            else:
                engine_name = str(self.main_window.latex_engine).strip()

                # INLINE transformation
                engine_title = engine_name.replace('_', ' ').title()

                self.compile_action.setText(engine_title)
                self.compile_action.setToolTip(f"Compile with {engine_title} (F5)")
                self.icons_manager.apply_icon_to_action(self.compile_action, "compile")

            self.compile_action.setEnabled(True)

        if hasattr(self, 'stop_action'):
            self.stop_action.setEnabled(compiling)
        elif hasattr(self.main_window, 'toolbar_stop_action'):
            self.main_window.toolbar_stop_action.setEnabled(compiling)


    def update_backmatter_actions(self, compiling=False):
        """Update compile/stop button based on compilation state"""
            
        self.backmatter_compiling = compiling        
            
        if compiling:
            self.backmatter_action.setText("Stop")
            self.backmatter_action.setToolTip("Stop backmatter compilation (F9)")
            self.icons_manager.apply_icon_to_action(self.backmatter_action, "stop")
        else:
            backmatter_name = str(self.main_window.backmatter_engine).strip()

            # INLINE transformation
            backmatter_title = backmatter_name.replace('_', ' ').title()

            self.backmatter_action.setText(backmatter_title)
            self.backmatter_action.setToolTip(
                f"Backmatter compile with {backmatter_title} (F9)"
            )

            self.icons_manager.apply_icon_to_action(
                self.backmatter_action, "backmatter_compile"
            )

        self.backmatter_action.setEnabled(True)
            
        if hasattr(self, 'backmatter_stop_action'):
            self.backmatter_stop_action.setEnabled(compiling)
        elif hasattr(self.main_window, 'toolbar_backmatter_stop_action'):
            self.main_window.toolbar_backmatter_stop_action.setEnabled(compiling)

        
    def handle_jump_action(self):
        """Handle View button click - SyncTeX forward search from editor to PDF"""
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]                                    
        current_editor = self.main_window.editor_manager.get_current_editor()
        current_file = self.main_window.editor_manager.get_current_file_path()
        
        if not current_editor or not current_file:
            self.show_error(tr["no_file_open"], tr["open_a_latex_file"])
            return
        
        # Get current line number (1-indexed for SyncTeX)
        cursor = current_editor.textCursor()
        line_number = cursor.blockNumber() + 1
        column_number = cursor.columnNumber() + 1
        
        # Perform forward SyncTeX search
        if hasattr(self.main_window, 'pdf_manager'):
            self.main_window.pdf_manager.synctex_forward_search(
                current_file, line_number, column_number
            )
        

    def _create_symbols_toggle(self):
        """Create symbols toggle button"""
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]
        
        symbols_action = QAction(tr["symbols_text"], self.main_window)
        symbols_action.setToolTip(tr["tooltip_symbols"])
        symbols_action.setCheckable(True)
        symbols_action.setChecked(self.symbols_tab_visible)
        symbols_action.triggered.connect(self.toggle_symbols_tab)
        
        self.icons_manager.apply_icon_to_action(symbols_action, "symbols")
        self.main_toolbar.addAction(symbols_action)
        
        self.symbols_action = symbols_action
        
    def toggle_symbols_tab(self):
        """Toggle the symbols tab visibility and sync with settings"""
        self.symbols_tab_visible = not self.symbols_tab_visible
        self.symbols_action.setChecked(self.symbols_tab_visible)
        
        # Sync with main window
        self.main_window.symbols_tab_visible = self.symbols_tab_visible
        
        # Update UI
        output_container = self.main_window.layout_manager.output_container
        if not output_container:
            return
            
        if self.symbols_tab_visible:
            # Ensure output container is visible when showing sub-tabs
            self._ensure_output_visible()
            self._add_symbols_tab(output_container)
            self._focus_tab(output_container, "Symbols")
        else:
            self._remove_symbols_tab(output_container)
        
        # Notify settings dialog if open
        self._notify_settings_dialog_update()
        

    def _create_commands_toggle(self):
        """Create commands toggle button"""
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]
        
           
        commands_action = QAction(tr["commands_text"], self.main_window)
        commands_action.setToolTip(tr["tooltip_commands"])
        commands_action.setCheckable(True)
        commands_action.setChecked(self.commands_tab_visible)
        commands_action.triggered.connect(self.toggle_commands_tab)
        
        self.icons_manager.apply_icon_to_action(commands_action, "latex_commands")
        self.main_toolbar.addAction(commands_action)
        
        self.commands_action = commands_action
        
    def toggle_commands_tab(self):
        """Toggle the commands tab visibility and sync with settings"""
        self.commands_tab_visible = not self.commands_tab_visible
        self.commands_action.setChecked(self.commands_tab_visible)
        
        # Sync with main window
        self.main_window.commands_tab_visible = self.commands_tab_visible
        
        # Update UI
        output_container = self.main_window.layout_manager.output_container
        if not output_container:
            return
            
        if self.commands_tab_visible:
            # Ensure output container is visible when showing sub-tabs
            self._ensure_output_visible()
            self._add_commands_tab(output_container)
            self._focus_tab(output_container, "Commands")
        else:
            self._remove_commands_tab(output_container)
        
        # Notify settings dialog if open
        self._notify_settings_dialog_update()
        
        
    def _create_tree_toggle(self):
        """Create tree toggle button"""
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]
        
           
        tree_action = QAction(tr["tree_text"], self.main_window)
        tree_action.setToolTip(tr["tooltip_tree"])
        tree_action.setCheckable(True)
        tree_action.setChecked(self.tree_tab_visible)
        tree_action.triggered.connect(self.toggle_tree_tab)
        
        self.icons_manager.apply_icon_to_action(tree_action, "tree")
        self.main_toolbar.addAction(tree_action)
        
        self.tree_action = tree_action


            
    def toggle_tree_tab(self):
        """Toggle the tree tab visibility and sync with settings"""
        self.tree_tab_visible = not self.tree_tab_visible
        self.tree_action.setChecked(self.tree_tab_visible)
        
        # Sync with main window
        self.main_window.tree_tab_visible = self.tree_tab_visible
        
        # Update UI
        output_container = self.main_window.layout_manager.output_container
        if not output_container:
            return
            
        if self.tree_tab_visible:
            # Ensure output container is visible when showing sub-tabs
            self._ensure_output_visible()
            self._add_tree_tab(output_container)
            self._focus_tab(output_container, "Tree")
        else:
            self._remove_tree_tab(output_container)
        
        # Notify settings dialog if open
        self._notify_settings_dialog_update()
            
    
    def enhanced_create_main_toolbar(self):
        # Call original method
        original_create_toolbar()
        
        # Add bookmarks button
        #self._create_bookmarks_toggle()
    
    def _create_bookmarks_toggle(self):
        """Create bookmarks toggle button"""
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]
      
        
        from PyQt5.QtWidgets import QAction
        bookmarks_action = QAction(tr["bookmarks_text"], self.main_window)
        bookmarks_action.setToolTip(tr["tooltip_bookmarks"])
        bookmarks_action.setCheckable(True)
        bookmarks_action.setChecked(self.bookmarks_tab_visible)
        bookmarks_action.triggered.connect(self.toggle_bookmarks_tab)
        
        # Apply icon
        if hasattr(self, 'icons_manager'):
            self.icons_manager.apply_icon_to_action(bookmarks_action, "bookmarks")
        
        self.main_toolbar.addAction(bookmarks_action)
        self.bookmarks_action = bookmarks_action
    
    def toggle_bookmarks_tab(self):
        """Toggle bookmarks tab visibility and sync with settings"""
        self.bookmarks_tab_visible = not self.bookmarks_tab_visible
        self.bookmarks_action.setChecked(self.bookmarks_tab_visible)

        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]
        
        # Sync with main window
        self.main_window.bookmarks_tab_visible = self.bookmarks_tab_visible
        
        # Update UI
        output_container = self.main_window.layout_manager.output_container
        if not output_container:
            return
            
        if self.bookmarks_tab_visible:
            # Ensure output container is visible when showing sub-tabs
            self._ensure_output_visible()
            self._add_bookmarks_tab(output_container)
            self._focus_tab(output_container, tr["bookmarks"])
        else:
            self._remove_bookmarks_tab(output_container)
        
        # Notify settings dialog if open
        self._notify_settings_dialog_update()
    
    def _add_bookmarks_tab(self, output_container):
        """Add bookmarks tab to output container"""
        # Check if tab already exists
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]        
        
        for i in range(output_container.count()):
            if output_container.tabText(i) == tr["bookmarks"]:
                return
        
        # Create bookmarks widget if it doesn't exist
        if not hasattr(self.main_window, 'bookmarks_widget'):
            self.main_window.bookmarks_widget = BookmarksWidget(self.main_window)
        
        output_container.addTab(self.main_window.bookmarks_widget, tr["bookmarks"])
    
    def _remove_bookmarks_tab(self, output_container):
        """Remove bookmarks tab from output container"""
        translations = self.main_window.translations

        # Collect all possible labels for "tree"
        possible_labels = {"Bookmarks"}  # source text
        for lang in translations:
            possible_labels.add(translations[lang]["bookmarks"])
            
        for i in range(output_container.count()):
            if output_container.tabText(i) in possible_labels:
                output_container.removeTab(i)
                break
                
    def _ensure_output_visible(self):
        """Ensure output container is visible when enabling sub-tabs"""
        if (hasattr(self.main_window, 'layout_manager') and 
            hasattr(self.main_window.layout_manager, 'output_container') and
            self.main_window.layout_manager.output_container and
            not self.main_window.layout_manager.output_container.isVisible()):
            
            # Show output container
            self.main_window.layout_manager.output_container.setVisible(True)
            self.main_window.output_tab_visible = True
            
            # Update output toggle action if it exists
            if (hasattr(self.main_window, 'menu_manager') and 
                hasattr(self.main_window.menu_manager, 'output_action')):
                self.main_window.menu_manager.output_action.setChecked(True)

    def _notify_settings_dialog_update(self):
        """Notify settings dialog to update checkboxes if open"""
        # Check if settings dialog is open
        if (hasattr(self.main_window, 'settings_manager') and
            hasattr(self.main_window.settings_manager, 'dialog') and
            self.main_window.settings_manager.dialog and
            self.main_window.settings_manager.dialog.isVisible()):
            
            dialog = self.main_window.settings_manager.dialog
            # Reload current settings to sync checkboxes
            if hasattr(dialog, 'load_current_settings'):
                dialog.load_current_settings()

######
    def remove_bookmarks_tab(self, file_path):
        """Remove bookmarks tab when closing a file"""
        translations = self.main_window.translations

        # Collect all possible labels for "tree"
        possible_labels = {"Bookmarks"}  # source text
        for lang in translations:
            possible_labels.add(translations[lang]["bookmarks"])
            
        try:
            #print(f"Processing bookmark removal for file: {file_path}")
            
            # Find output tab widget containing bookmarks
            output_tab_widget = None
            
            # Simple search for any QTabWidget with "Bookmarks" tab
            central_widget = self.main_window.centralWidget()
            if central_widget:
                tab_widgets = central_widget.findChildren(QTabWidget)
                for tab_widget in tab_widgets:
                    for i in range(tab_widget.count()):
                        if tab_widget.tabText(i)  in possible_labels:
                            output_tab_widget = tab_widget
                            break
                    if output_tab_widget:
                        break
            
            # Remove the bookmarks tab entirely
            if output_tab_widget:
                for i in range(output_tab_widget.count()):
                    if output_tab_widget.tabText(i)  in possible_labels:
                        output_tab_widget.removeTab(i)
                        #print("Removed bookmarks tab")
                        break
            else:
                pass
                #print("No bookmarks tab found to remove")
                
        except Exception as e:
            print(f"Error in remove_bookmarks_tab: {e}")    
######          

    def _create_tree_widget(self):
        """Create the tree tab widget showing document structure"""
        ui_font = self._get_ui_font()  # ✅

        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(2, 2, 2, 2)

        tree = DocumentTreeWidget(self.main_window)
        tree.setFont(ui_font)          # ✅ Tree content font
        tree.header().setFont(ui_font) # ✅ Tree header font
        layout.addWidget(tree)

        if hasattr(self.main_window, 'editor_manager'):
            tree.refresh_tree()

        return main_widget

    def _focus_tab(self, output_container, tab_name):
        """Focus on a specific tab by name - P2 Fix"""
        for i in range(output_container.count()):
            if output_container.tabText(i) == tab_name:
                output_container.setCurrentIndex(i)
                break           

                
    def _add_tree_tab(self, output_container):
        """Add tree tab to output container"""
        # Check if tab already exists
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]        
        
        for i in range(output_container.count()):
            if output_container.tabText(i) == tr["tree"]:
                return
                
        tree_widget = self._create_tree_widget()
        output_container.addTab(tree_widget, tr["tree"])

    def _remove_tree_tab(self, output_container):
        """Remove tree tab from output container"""
        translations = self.main_window.translations

        # Collect all possible labels for "tree"
        possible_labels = {"Tree"}  # source text
        for lang in translations:
            possible_labels.add(translations[lang]["tree"])
            
        for i in range(output_container.count()):
            if output_container.tabText(i)  in possible_labels:
                output_container.removeTab(i)
                break
                
    def _get_ui_font(self):
        """Get the current UI font"""
        if hasattr(self.main_window, 'get_current_font_settings'):
            fonts = self.main_window.get_current_font_settings()
            family = fonts.get('ui_font_family', 'Arial')
            size = fonts.get('toolbar_font_size', 10)
            return QFont(family, size)
        return QFont('Arial', 10)

    def _add_symbols_tab(self, output_container):
        """Add symbols tab to output container"""
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]
        # Check if tab already exists
        possible_labels = {"Symbols"}
        for lang in self.main_window.translations:
            possible_labels.add(tr["symbols"])
       
        
        for i in range(output_container.count()):
            if output_container.tabText(i) in possible_labels:        
                return
                
        symbols_widget = self._create_symbols_widget()
        output_container.addTab(symbols_widget, tr["symbols"])

    def _remove_symbols_tab(self, output_container):
        translations = self.main_window.translations

        # Collect all possible labels for "symbols"
        possible_labels = {"Symbols"}  # source text
        for lang in translations:
            possible_labels.add(translations[lang]["symbols"])

        for i in range(output_container.count()):
            if output_container.tabText(i) in possible_labels:
                output_container.removeTab(i)
                break

    def _add_commands_tab(self, output_container):
        """Add commands tab to output container"""
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]        

        # Check if tab already exists
        possible_labels = {"Commands"}
        for lang in self.main_window.translations:
            possible_labels.add(tr["commands"])

        
        for i in range(output_container.count()):
            if output_container.tabText(i) in possible_labels:        
                return
                
        commands_widget = self._create_commands_widget()
        output_container.addTab(commands_widget, tr["commands"])

    def _remove_commands_tab(self, output_container):
        """Remove commands tab from output container"""
        translations = self.main_window.translations

        # Collect all possible labels for "symbols"
        possible_labels = {"Commands"}  # source text
        for lang in translations:
            possible_labels.add(translations[lang]["commands"])                
        
        for i in range(output_container.count()):
            if output_container.tabText(i) in possible_labels:
                output_container.removeTab(i)
                break

    
    def _create_symbols_widget(self):
        """Create the symbols tab widget with category tabs"""
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(2, 2, 2, 2)
        
        ui_font = self._get_ui_font()  # ✅

        # Create tab widget for symbol categories
        symbols_tabs = QTabWidget()
        symbols_tabs.setTabPosition(QTabWidget.North)
        symbols_tabs.tabBar().setFont(ui_font)  # ✅ Apply font to tab bar
        
        # Add each symbol category as a tab
        for category_key, category_data in self.math_symbols_handler.symbol_categories.items():
            category_name = category_data["tr"]
            category_widget = self._create_symbol_category_widget(category_key, category_data)
            symbols_tabs.addTab(category_widget, category_name)
        
        layout.addWidget(symbols_tabs)
        
        
        # ✅ CRITICAL: store references
        main_widget.symbols_tabs = symbols_tabs
        main_widget.math_menu = self.math_symbols_handler        
        
        return main_widget


    def _create_commands_widget(self):
        """Create the commands tab widget with category tabs"""
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(2, 2, 2, 2)

        ui_font = self._get_ui_font()  # ✅
        
        # Create tab widget for command categories
        commands_tabs = QTabWidget()
        commands_tabs.setTabPosition(QTabWidget.North)
        commands_tabs.tabBar().setFont(ui_font)  # ✅ Apply font to tab bar
        
        # Add each command category as a tab
        for category_key, category_data in self.latex_commands_handler.sectionning_categories.items():
            category_name = category_data["tr"]
            category_widget = self._create_command_category_widget(category_key, category_data)
            commands_tabs.addTab(category_widget, category_name)
        
        layout.addWidget(commands_tabs)

       # ✅ CRITICAL: store references
        main_widget.commands_tabs = commands_tabs
        main_widget.commands_menu = self.latex_commands_handler
        
        
        return main_widget


    def _create_symbol_category_widget(self, category_key, category_data):
        """Create widget for a symbol category with button matrix - IMPROVED LAYOUT"""
        # Main widget with scroll area
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(2, 2, 2, 2)
        
        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Content widget with grid layout
        content_widget = QWidget()
        grid_layout = QGridLayout(content_widget)
        grid_layout.setSpacing(4)  # ✅ Thicker spacing between buttons
        grid_layout.setContentsMargins(1, 1, 1, 1)
        
        # Create buttons for symbols
        symbols = category_data["symbols"]
        cols = 6  # Number of columns in the grid
        
        for i, item in enumerate(symbols):
            if len(item) == 3:
                symbol_display, latex_code, description = item
                package = None
            else:
                symbol_display, latex_code, description, package = item                
            row = i // cols
            col = i % cols
            button = self._create_symbol_button(symbol_display, latex_code, description, package)
            grid_layout.addWidget(button, row, col)
        
        # ✅ Make grid expand to fill space
        for col in range(cols):
            grid_layout.setColumnStretch(col, 1)
        
        # Set content widget to scroll area
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
        
        return main_widget



    def _create_command_category_widget(self, category_key, category_data):
        """Create widget for a command category with button matrix - IMPROVED LAYOUT"""
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(2, 2, 2, 2)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        content_widget = QWidget()
        grid_layout = QGridLayout(content_widget)
        grid_layout.setSpacing(4)
        grid_layout.setContentsMargins(1, 1, 1, 1)

        commands = category_data["commands"]
        cols = 4

        for i, item in enumerate(commands):
            # Unpack safely (3 or 4 elements)
            if len(item) == 3:
                command_display, latex_code, description = item
                package = None
            else:
                command_display, latex_code, description, package = item
            row = i // cols
            col = i % cols
            button = self._create_command_button(command_display, latex_code, description, package)
            grid_layout.addWidget(button, row, col)

        for col in range(cols):
            grid_layout.setColumnStretch(col, 1)

        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)

        return main_widget

    def _create_symbol_button(self, symbol_display, latex_code, description, package=None, icon_size=32):
        """
        Create a button for a mathematical symbol with dynamic icon sizing
        
        Args:
            symbol_display: Display text for the symbol (Unicode character)
            latex_code: LaTeX code to insert (e.g., r"\alpha")
            description: Tooltip description
            icon_size: Initial icon size (will scale with button resize)
        
        Returns:
            QPushButton configured for the symbol
        """
        button = QPushButton()        
        tooltip = f"<b>{description}</b><br>"
        tooltip += f"Symbol: {symbol_display}<br>"
        tooltip += f"LaTeX: <code>{latex_code}</code>"

        if package:
            tooltip += f"<br><span style='color:gray;'>Requires: <code>{package}</code></span>"

        button.setToolTip(tooltip)        
        button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        button.setMinimumHeight(40)


        # ✅ Apply UI font
        current_fonts = self.main_window.get_current_font_settings()
        ui_font = QFont(
            current_fonts.get('ui_font_family', 'Arial'),
            current_fonts.get('toolbar_font_size', 10)
        )
        button.setFont(ui_font)
        
        # Try to get icon from icons manager
        icon = self.icons_manager.get_math_symbol_icon(latex_code, size=icon_size)
        
        if icon and not icon.isNull():
            button.setIcon(icon)
            button._has_icon = True
            button._latex_code = latex_code  # Store for dynamic resizing
            button._is_symbol = True
            
            # Set icon alignment and positioning
            button.setIconSize(QSize(icon_size, icon_size))
            # Remove any text to ensure icon is centered
            button.setText("")
            
            # Override resizeEvent to dynamically adjust icon size
            original_resize = button.resizeEvent
            
            def resize_with_dynamic_icon(event):
                original_resize(event)
                # Make icon 70% of button height, with reasonable bounds
                new_size = min(int(button.height() * 0.75), 64)
                new_size = max(new_size, 16)  # Minimum 16px
                
                # Get resized icon from manager (uses cache)
                resized_icon = self.icons_manager.get_math_symbol_icon(
                    button._latex_code, 
                    size=new_size
                )
                if resized_icon and not resized_icon.isNull():
                    button.setIcon(resized_icon)
                    button.setIconSize(QSize(new_size, new_size))
            
            button.resizeEvent = resize_with_dynamic_icon
        #else:
            # Fallback to text display
        #    button.setText(symbol_display)
        else:
            # Fallback to text display with larger bold font
            button.setText(symbol_display)
            fallback_font = QFont(
                current_fonts.get('ui_font_family', 'Arial'),
                14  # Larger size for readability
            )
            fallback_font.setBold(True)
            button.setFont(fallback_font)            
        
        # Apply styling (assumes NORMAL_BUTTON is defined in style.py)
        try:
            from style_manager import NORMAL_BUTTON
            button.setStyleSheet(NORMAL_BUTTON())
        except ImportError:
            # Fallback styling if style module not available
            button.setStyleSheet("""
                QPushButton {
                    border: 1px solid #ccc;
                    border-radius: 3px;
                    background-color: #f9f9f9;
                    padding: 5px;
                }
                QPushButton:hover {
                    background-color: #e9e9e9;
                }
                QPushButton:pressed {
                    background-color: #d9d9d9;
                }
            """)
        
        # Connect to insert function
        button.clicked.connect(
            lambda: self.main_window.editor_manager.insert_latex_command(latex_code)
        )
        
        return button
    

    def _create_command_button(self, command_display, latex_code, description, package=None, icon_size=24):
        """
        Create a button for a LaTeX command with dynamic icon sizing

        Args:
            command_display: Display text for the command
            latex_code: LaTeX code to insert (e.g., r"\section{}")
            description: Tooltip description
            package: Optional required LaTeX package (e.g., "amsmath")
            icon_size: Initial icon size

        Returns:
            QPushButton configured for the command
        """
        button = QPushButton()
        
        # Build rich tooltip (same format as symbol button)
        tooltip = f"<b>{description}</b><br>"
        tooltip += f"LaTeX: <code>{latex_code}</code>"
        if package:
            tooltip += f"<br><span style='color:gray;'>Requires: <code>{package}</code></span>"
        button.setToolTip(tooltip)
        
        button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        button.setMinimumHeight(40)

        # Apply UI font
        current_fonts = self.main_window.get_current_font_settings()
        ui_font = QFont(
            current_fonts.get('ui_font_family', 'Arial'),
            current_fonts.get('toolbar_font_size', 10)
        )
        button.setFont(ui_font)
        
        # Try to get icon from icons manager
        icon = self.icons_manager.get_latex_command_icon(latex_code, size=icon_size)
        
        if icon and not icon.isNull():
            button.setIcon(icon)
            button._has_icon = True
            button._latex_code = latex_code
            button._is_command = True
            
            # Dynamic resizing for command icons
            original_resize = button.resizeEvent
            
            def resize_with_dynamic_icon(event):
                original_resize(event)
                new_size = min(int(button.height() * 0.75), 48)
                new_size = max(new_size, 14)
                
                resized_icon = self.icons_manager.get_latex_command_icon(
                    button._latex_code,
                    size=new_size
                )
                if resized_icon and not resized_icon.isNull():
                    button.setIcon(resized_icon)
                    button.setIconSize(QSize(new_size, new_size))
            
            button.resizeEvent = resize_with_dynamic_icon
            button.setIconSize(QSize(icon_size, icon_size))
            
            # Show abbreviated text with icon
            display_text = command_display[:12] if len(command_display) > 12 else command_display
            button.setText(display_text)
        else:
            # Use text only (truncated if too long) with larger bold font
            display_text = command_display if len(command_display) <= 18 else command_display[:15] + "..."
            button.setText(display_text)
            fallback_font = QFont(
                current_fonts.get('ui_font_family', 'Arial'),
                14
            )
            fallback_font.setBold(True)
            button.setFont(fallback_font)            
        
        # Apply styling
        try:
            from style_manager import GREEN_BUTTON
            button.setStyleSheet(GREEN_BUTTON())
        except ImportError:
            button.setStyleSheet("""
                QPushButton {
                    border: 1px solid #4CAF50;
                    border-radius: 3px;
                    background-color: #E8F5E9;
                    padding: 5px;
                }
                QPushButton:hover {
                    background-color: #C8E6C9;
                }
                QPushButton:pressed {
                    background-color: #A5D6A7;
                }
            """)
        
        # Connect to insert function
        button.clicked.connect(
            lambda: self.main_window.editor_manager.insert_latex_command(latex_code)
        )
        
        return button


    def refresh_button_styles(self):
        """Re-apply current theme styles to all symbol/command buttons."""
        from style_manager import get_button_style
        normal_style = get_button_style("normal")
        green_style  = get_button_style("green")

        # Search the entire main window widget tree — buttons may be
        # inside QWidget containers inside toolbars, not direct children
        for widget in self.main_window.findChildren(QPushButton):
            if getattr(widget, '_is_command', False):
                widget.setStyleSheet(green_style)
            elif getattr(widget, '_is_symbol', False):
                widget.setStyleSheet(normal_style)

            
    def _get_symbol_icon(self, symbol_display, latex_code, size=24):
        """
        Get icon for a mathematical symbol
        Compatibility wrapper for existing code
        
        Args:
            symbol_display: Display text (not used, for compatibility)
            latex_code: LaTeX code
            size: Icon size in pixels
        
        Returns:
            QIcon or None
        """
        return self.icons_manager.get_math_symbol_icon(latex_code, size)
    
    def _get_command_icon(self, command_display, latex_code, size=24):
        """
        Get icon for a LaTeX command
        Compatibility wrapper for existing code
        
        Args:
            command_display: Display text (not used, for compatibility)
            latex_code: LaTeX code
            size: Icon size in pixels
        
        Returns:
            QIcon or None
        """
        return self.icons_manager.get_latex_command_icon(latex_code, size)
    
    def _create_text_icon(self, text, font_size=16):
        """
        Create a text-based icon
        Delegates to icons_manager for consistency
        
        Args:
            text: Text to render
            font_size: Font size for the text
        
        Returns:
            QIcon
        """
        return self.icons_manager._create_text_icon(text, font_size)


        
    def _create_arabic_actions(self):
        """Create Arabic-related toolbar actions"""
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]
        
        
        
        arabic_action = QAction(tr["insert_arabic_command"], self.main_window)        
        arabic_action.setToolTip(tr["tooltip_arabic_command"])           
        arabic_action.triggered.connect(self.open_arabic_command_dialog)
        self.icons_manager.apply_icon_to_action(arabic_action, "arabic")
        self.main_toolbar.addAction(arabic_action)



        if hasattr(self, 'double_lang_action') or hasattr(self, 'bilingual'):
            try:
                self.double_lang_action.triggered.disconnect()
            except Exception:
                pass

        double_lang_action = QAction(tr["bilingual"], self.main_window)
        #self.double_lang_action.setShortcut("Alt+B")
        #double_lang_action.setStatusTip(tr["status_double_lang_tool"])
        double_lang_action.setToolTip(tr.get("tooltip_double_lang_tool", "A tool for inserting mixed Arabic/English text"))
        double_lang_action.triggered.connect(self.main_window.menu_manager.open_double_language_dialog)
        self.icons_manager.apply_icon_to_action(double_lang_action, "bilingual")
        self.main_toolbar.addAction(double_lang_action)



        # # Toggle Text direction LR/RL
        # if hasattr(self, 'text_dir_action'):
            # self.text_dir_action.triggered.disconnect()  # Disconnect all connections
            # self.main_toolbar.removeAction(self.text_dir_action)
        
        # # Create new action
        # self.text_dir_action = QAction(tr["direction"], self.main_window)
        # self.text_dir_action.setToolTip(tr["tooltip_direction"])
        # self.text_dir_action.setCheckable(False)
        
        # # Single connection only
        # self.text_dir_action.triggered.connect(self.main_window.toggle_text_direction)
        
        # # Apply icon and add to toolbar
        # self.icons_manager.apply_icon_to_action(self.text_dir_action, "direction")
        # self.main_toolbar.addAction(self.text_dir_action)
        #self.debug_signal_connections()        

        

    def handle_switch_layout(self):
        """Handle layout switch with safety checks"""
        try:
            print("🔄 Starting layout switch...")
            
            # Check if we have necessary components
            if not hasattr(self.main_window, 'layout_manager'):
                #print("❌ No layout_manager found")
                return
                
            # Perform the switch
            self.main_window.layout_manager.switch_layout()
            
            # Note: Don't call toggle_side_panel_position separately
            # Let switch_layout handle everything to avoid double rebuilds
            
            #print("✅ Layout switch completed")
            
        except Exception as e:
            print(f"❌ Error in handle_switch_layout: {e}")
            import traceback
            traceback.print_exc()  
            
    def _create_view_actions(self):
        """Create view-related toolbar actions"""
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]

        # Editor Layout - Now called "Tex Layout"
        editor_layout_action = QAction(tr["tab_tex"], self.main_window)
        #editor_layout_action.setShortcut("Ctrl+F3")  # Ctrl+F3 to avoid conflict
        editor_layout_action.setToolTip(tr["tooltip_editor_layout"])
        editor_layout_action.triggered.connect(self.main_window.layout_manager.toggle_editor_layout)
        self.icons_manager.apply_icon_to_action(editor_layout_action, "editor_layout")
        self.main_toolbar.addAction(editor_layout_action)

        # Toggle PDF Layout
        pdf_layout_action = QAction(tr["tab_pdf"], self.main_window)
        #pdf_layout_action.setShortcut("Ctrl+F4")
        pdf_layout_action.setToolTip(tr["tooltip_pdf_layout"])
        pdf_layout_action.triggered.connect(self.main_window.layout_manager.toggle_pdf_layout)
        self.icons_manager.apply_icon_to_action(pdf_layout_action, "pdf_layout")
        self.main_toolbar.addAction(pdf_layout_action)
        
        
        # Switch Layout
        switch_layout_action = QAction(tr["switch_layout"], self.main_window)
        #switch_layout_action.setShortcut("F4")
        switch_layout_action.setToolTip(tr["tooltip_switch_layout"])
        switch_layout_action.triggered.connect(self.handle_switch_layout)
        self.icons_manager.apply_icon_to_action(switch_layout_action, "switch_layout")
        self.main_toolbar.addAction(switch_layout_action)
        



    def _create_terminal_toggle(self):
        """Create terminal toggle button"""
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]        
        
        terminal_action = QAction(tr["terminal_text"], self.main_window)
        terminal_action.setToolTip(tr["tooltip_terminal"])
        terminal_action.setCheckable(True)
        terminal_action.setChecked(self.terminal_tab_visible)
        terminal_action.triggered.connect(self.toggle_terminal_tab)
        
        # Use appropriate icon (you may need to add this icon to your icons_manager)
        # If you don't have a terminal icon, you can use a generic icon or leave it blank
        if hasattr(self.icons_manager, 'apply_icon_to_action'):
            self.icons_manager.apply_icon_to_action(terminal_action, "terminal")
        
        self.main_toolbar.addAction(terminal_action)
        self.terminal_action = terminal_action

    def toggle_terminal_tab(self):
        """Toggle the terminal tab visibility and sync with settings"""
        self.terminal_tab_visible = not self.terminal_tab_visible
        #self.terminal_action.setChecked(self.terminal_tab_visible)
        
        # Sync with main window
        self.main_window.terminal_tab_visible = self.terminal_tab_visible
        
        # Update UI
        output_container = self.main_window.layout_manager.output_container
        if not output_container:
            return
        
        if self.terminal_tab_visible:
            # Ensure output container is visible when showing sub-tabs
            self._ensure_output_visible()
            self._add_terminal_tab(output_container)
            self._focus_tab(output_container, "Terminal")
        else:
            self._remove_terminal_tab(output_container)
        
        # Notify settings dialog if open
        self._notify_settings_dialog_update()

    def _remove_terminal_tab(self, output_container):
        """Remove terminal tab from output container"""
        translations = self.main_window.translations

        # Collect all possible labels for "symbols"
        possible_labels = {"Terminal"}  # source text
        for lang in translations:
            possible_labels.add(translations[lang]["terminal"])                
        
        for i in range(output_container.count()):
            if output_container.tabText(i) in possible_labels:
                output_container.removeTab(i)
                break
                
                
    def _add_terminal_tab(self, output_container):
        """Add terminal tab to output container"""
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]                
        # Check if terminal tab already exists
        for i in range(output_container.count()):
            if output_container.tabText(i) == tr["terminal"]:
                return  # Already exists
        
        # Create terminal widget if needed
        if not hasattr(self.main_window.layout_manager, 'terminal_widget') or \
           self.main_window.layout_manager.terminal_widget is None:
            from terminal_widget import TerminalWidget  # Import your terminal widget
            self.main_window.layout_manager.terminal_widget = TerminalWidget(self.main_window)
        
        # Add tab
        terminal_widget = self.main_window.layout_manager.terminal_widget
        output_container.addTab(terminal_widget, tr["terminal"])
        
        # Update working directory if there's a current file
        if hasattr(self.main_window, 'editor_manager'):
            current_file = self.main_window.editor_manager.get_current_file_path()
            if current_file:
                terminal_widget.set_working_directory(current_file)

    
    def _create_settings_actions(self):
        """Create settings-related toolbar actions"""
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]
        
        # Settings 
        self.settings_action = QAction(tr["settings"], self.main_window) # Store as self.settings_action
        
        # Self.settings_action.setShortcut("Ctrl+F1,")
        self.settings_action.setToolTip(tr["tooltip_settings"])
        
        # Connect to settings_manager
        self.settings_action.triggered.connect(self.main_window.settings_manager.open_settings)
        self.icons_manager.apply_icon_to_action(self.settings_action, "settings")
        self.main_window.toolbar_settings_action = self.settings_action  # Backward compatibility
        self.main_toolbar.addAction(self.settings_action)
        
        # Language Toggle  
        self.lang_action = QAction(tr["language"], self.main_window) # Store as self.lang_action
        self.lang_action.setToolTip(tr["tooltip_language"])
        
        

            
    def open_arabic_command_dialog(self):
        """Open the Arabic command dialog"""
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]                                    
        current_editor = self.main_window.editor_manager.get_current_editor()
        current_file = self.main_window.editor_manager.get_current_file_path()
            
        if not current_editor or not current_file:
            self.show_error(tr["no_file_open"], tr["open_a_latex_file"])
            return
            
        if not ARABIC_DIALOG_AVAILABLE:
            # Show info message if dialog is not available
            title = tr["file_missing"]
            message = tr["file_missing_message"]
            QMessageBox.information(self.main_window, title, message)
            return
        
        # Open the dialog if available
        dialog = ArabicCommandDialog(self.main_window, self.main_window.menu_language)
        
        if dialog.exec_() == dialog.Accepted:
            latex_command = dialog.get_latex_command()
            if latex_command:
                # Insert the LaTeX command into the current editor
                current_editor = self.main_window.editor_manager.get_current_editor()
                if current_editor:
                    cursor = current_editor.textCursor()
                    cursor.insertText(latex_command)
                    current_editor.setFocus()
                    
                    # Mark as modified
                    self.main_window.editor_manager.on_text_changed()
                    
                    # Update status
                    status_msg = tr["status_inserted_arabic_command"].format(latex_command=latex_command)
                    self.main_window.update_status_bar(status_msg)
                else:
                    # No editor available - show message
                    if lang == "ar":
                        QMessageBox.information(self.main_window, "تنبيه", "لا يوجد محرر مفتوح لإدراج الأمر.")
                    else:
                        QMessageBox.information(self.main_window, "Notice", "No editor available to insert command.")
        
        
    
    def update_toolbar_font(self, font_family=None, font_size=None):
        """Update toolbar font family and/or size"""
        if not self.main_toolbar:
            return
        
        # Get current settings as fallback
        current_fonts = self.main_window.get_current_font_settings()
        
        if font_family is None:
            font_family = current_fonts.get('ui_font_family', 'Arial')
        if font_size is None:
            font_size = current_fonts.get('toolbar_font_size', 10)
        
        font = QFont(font_family, int(font_size))
        self.main_toolbar.setFont(font)
        
        # Apply to all toolbar buttons
        self._apply_font_to_toolbar_buttons(font)
        
        #print(f"Toolbar font updated: {font_family}, size {font_size}")
    
        
    def show_error(self, title, message):
        """Show error message dialog with translated button."""
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]

        msg_box = QMessageBox(self.main_window)
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)

        # Add a single OK button with translated text
        ok_button = msg_box.addButton(tr.get("ok", "OK"), QMessageBox.AcceptRole)
        msg_box.setDefaultButton(ok_button)

        msg_box.exec_()        
    
    def _refresh_symbols_tab(self):
        """Refresh symbols tab with current language"""
        output_container = self.main_window.layout_manager.output_container
        if output_container and output_container.has_tab("Symbols"):
            self._remove_symbols_tab(output_container)
            self._add_symbols_tab(output_container)
    
    def _refresh_commands_tab(self):
        """Refresh commands tab with current language"""
        output_container = self.main_window.layout_manager.output_container
        if output_container and output_container.has_tab("Commands"):
            self._remove_commands_tab(output_container)
            self._add_commands_tab(output_container)



        

# Custom widget for symbol/command buttons with enhanced features

class SymbolCommandButton(QPushButton):
    """Enhanced button for symbols and commands with context menu"""
    def __init__(self, display_text, latex_code, description, button_type="symbol", 
                 icons_manager=None, icon_size=24):
        """
        Initialize enhanced symbol/command button
        
        Args:
            display_text: Text to display on button
            latex_code: LaTeX code to insert
            description: Description for tooltip
            button_type: "symbol" or "command"
            icons_manager: IconsManager instance
            icon_size: Size of the icon
        """
        super().__init__()
        self.display_text = display_text
        self.latex_code = latex_code
        self.description = description
        self.button_type = button_type
        self.icons_manager = icons_manager
        self.icon_size = icon_size
        
        self.setup_button()
        self.setup_context_menu()

    def setup_button(self):
        """Setup button appearance with icons from IconsManager"""
        self.setToolTip(f"{self.description}\nInsert: {self.latex_code}\nRight-click for options")
        
        # Set size constraints based on button type
        if self.button_type == "symbol":
            self.setMaximumSize(60, 40)
            self.setMinimumSize(40, 30)
        else:  # command
            self.setMaximumSize(120, 40)
            self.setMinimumSize(80, 30)
        
        # Try to load icon from IconsManager
        if self.icons_manager:
            if self.button_type == "symbol":
                icon = self.icons_manager.get_math_symbol_icon(self.latex_code, self.icon_size)
            else:
                icon = self.icons_manager.get_latex_command_icon(self.latex_code, self.icon_size)
            
            if icon and not icon.isNull():
                self.setIcon(icon)
                self.setIconSize(QSize(self.icon_size, self.icon_size))
            else:
                self.setText(self.display_text)
        else:
            # No icons manager, use text
            self.setText(self.display_text)
        
        # Apply styling
        self.setStyleSheet("""
            SymbolCommandButton {
                border: 1px solid #ccc;
                border-radius: 3px;
                background-color: #f9f9f9;
                font-weight: bold;
            }
            SymbolCommandButton:hover {
                background-color: #e9e9e9;
                border-color: #999;
            }
            SymbolCommandButton:pressed {
                background-color: #d9d9d9;
            }
        """)
    
    def setup_context_menu(self):
        """Setup context menu for additional options"""
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
    
    def show_context_menu(self, position):
        """Show context menu with additional options"""
        menu = QMenu(self)
        
        # Copy LaTeX code action
        copy_action = menu.addAction("Copy LaTeX Code")
        copy_action.triggered.connect(self.copy_latex_code)
        
        # Copy symbol/command display
        copy_display_action = menu.addAction("Copy Display Text")
        copy_display_action.triggered.connect(self.copy_display_text)
        
        # Add to favorites (if favorites system exists)
        if hasattr(self.parent(), 'add_to_favorites'):
            favorite_action = menu.addAction("Add to Favorites")
            favorite_action.triggered.connect(self.add_to_favorites)
        
        # Show description
        menu.addSeparator()
        desc_action = menu.addAction(f"Description: {self.description}")
        desc_action.setEnabled(False)
        
        menu.exec_(self.mapToGlobal(position))
    
    def copy_latex_code(self):
        """Copy LaTeX code to clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.latex_code)
    
    def copy_display_text(self):
        """Copy display text to clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.display_text)
    
    def add_to_favorites(self):
        """Add this symbol/command to favorites (if implemented)"""
        if hasattr(self.parent(), 'add_to_favorites'):
            self.parent().add_to_favorites(self.latex_code, self.display_text, 
                                          self.description, self.button_type)




def _build_tree_stylesheet(s: dict, obj_name: str = "") -> str:
    """Build a theme-aware QTreeWidget stylesheet.
    When obj_name is supplied the selectors are ID-qualified (#name),
    giving them higher specificity than the global app stylesheet."""
    sel  = f"QTreeWidget#{obj_name}" if obj_name else "QTreeWidget"
    hsel = f"QHeaderView::section"   # header is always global enough

    return f"""
        {sel} {{
            border: 1px solid {s['border']};
            background-color: {s['bg']};
            font-size: 11px;
        }}
        {sel}::item {{
            padding: 3px;
            border-bottom: 1px solid {s['item_border']};
        }}
        {sel}::item:hover {{
            background-color: {s['hover_bg']};
        }}
        {sel}::item:selected {{
            background-color: {s['selected_bg']};
            color: {s['selected_color']};
        }}
        {sel} QHeaderView::section {{
            background-color: {s['header_bg']};
            color: {s['header_color']};
            border: 1px solid {s['header_border']};
            padding: 3px;
        }}
        {sel}::branch {{
            background: transparent;
            border: none;
        }}
    """

# New DocumentTreeWidget class for the Tree tab
class DocumentTreeWidget(QTreeWidget):
    """Tree widget showing LaTeX document structure"""
   
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setObjectName("document_tree")   
        self.setHeaderLabels(["Structure", "Line"])
        self.setRootIsDecorated(True)
        self.setAlternatingRowColors(True)
        
        # Enhanced tree styling
        self.setIndentation(20)  # Increase indentation for better hierarchy visualization

        # ✅ Apply UI font
        self.update_font()
        
        # Apply theme-aware stylesheet instead of hardcoded colors
        self.refresh_theme()
        
        # Single click on any column navigates to line
        self.itemClicked.connect(self._on_item_clicked)
        # Double click also navigates (for accessibility)
        self.itemDoubleClicked.connect(self.go_to_line)

        # ✅ Connect expand/collapse signals to update icons
        self.itemExpanded.connect(self._on_item_expanded)
        self.itemCollapsed.connect(self._on_item_collapsed)


    def refresh_theme(self):
        from style_manager import get_tree_widget_style
        s = get_tree_widget_style()
        self.setStyleSheet(_build_tree_stylesheet(s, obj_name="document_tree"))  # ← ID-qualified
        # Force Qt to re-evaluate immediately
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()
        
    def update_font(self):
        """Update tree font to match interface font"""
        if hasattr(self.main_window, 'get_current_font_settings'):
            current_fonts = self.main_window.get_current_font_settings()
            ui_font_family = current_fonts.get('ui_font_family', 'Arial')
            ui_font_size = current_fonts.get('toolbar_font_size', 10)
        else:
            ui_font_family = getattr(self.main_window, 'ui_font_family', 'Arial')
            ui_font_size = getattr(self.main_window, 'toolbar_font_size', 10)

        ui_font = QFont(ui_font_family, ui_font_size)
        self.setFont(ui_font)
        self.header().setFont(ui_font)
#########
    def _on_item_expanded(self, item):
        """Update icon to downward triangle when expanded"""
        level = item.data(0, Qt.UserRole + 1)  # Retrieve stored level
        if level is not None:
            icon = self._create_triangle_icon(level, expanded=True)
            item.setIcon(0, icon)
            
    def _on_item_collapsed(self, item):
        """Update icon to right-pointing triangle when collapsed"""
        level = item.data(0, Qt.UserRole + 1)  # Retrieve stored level
        if level is not None:
            icon = self._create_triangle_icon(level, expanded=False)
            item.setIcon(0, icon)

    def _create_triangle_icon(self, level, expanded=False):
        """Create a triangle icon that points right (collapsed) or down (expanded)"""
        size = max(6, 12 - level * 1.5)
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        base_color = QColor(52, 152, 219)
        factor = max(80, 150 - level * 10)
        color = base_color.lighter(int(factor))

        cx = 8.0  # center x
        cy = 8.0  # center y
        half = size / 2

        path = QPainterPath()

        if expanded:
            # ▼ Downward-pointing triangle
            path.moveTo(cx - half, cy - half * 0.5)
            path.lineTo(cx + half, cy - half * 0.5)
            path.lineTo(cx, cy + half * 0.5)
        else:
            # ▶ Right-pointing triangle
            path.moveTo(cx - half * 0.5, cy - half)
            path.lineTo(cx + half * 0.5, cy)
            path.lineTo(cx - half * 0.5, cy + half)

        path.closeSubpath()
        painter.fillPath(path, color)
        painter.end()

        return QIcon(pixmap)      

    def _add_placeholder_item(self, text, level):
        """Add a placeholder item when no content is available"""
        item = QTreeWidgetItem([text, ""])
        item.setData(0, Qt.UserRole, None)
        item.setData(0, Qt.UserRole + 1, level)  # ✅ Store level
        icon = self._create_triangle_icon(level, expanded=False)
        item.setIcon(0, icon)
        self.addTopLevelItem(item)

    def parse_latex_structure(self, content):
        """Parse LaTeX content and build tree structure"""
        lines = content.split('\n')

        structure_patterns = [
            (r'\\part\*?{([^}]*)}', 'Part', 0),
            (r'\\chapter\*?{([^}]*)}', 'Chapter', 1),
            (r'\\section\*?{([^}]*)}', 'Section', 2),
            (r'\\subsection\*?{([^}]*)}', 'Subsection', 3),
            (r'\\subsubsection\*?{([^}]*)}', 'Subsubsection', 4),
            (r'\\paragraph\*?{([^}]*)}', 'Paragraph', 5),
        ]

        import re
        stack = []

        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('%'):
                continue

            for pattern, item_type, level in structure_patterns:
                match = re.search(pattern, line)
                if match:
                    title = match.group(1) or item_type
                    display_text = title

                    item = QTreeWidgetItem([display_text, str(line_num)])
                    item.setData(0, Qt.UserRole, line_num)        # line number
                    item.setData(0, Qt.UserRole + 1, level)       # ✅ Store level

                    # Set initial icon (collapsed = right-pointing)
                    icon = self._create_triangle_icon(level, expanded=False)
                    item.setIcon(0, icon)

                    if level > 2:
                        indent_prefix = "  " * (level - 2)
                        item.setText(0, indent_prefix + display_text)

                    # Handle hierarchy
                    while stack and stack[-1][1] >= level:
                        stack.pop()

                    if stack:
                        stack[-1][0].addChild(item)
                    else:
                        self.addTopLevelItem(item)

                    stack.append((item, level))
                    break

        if self.topLevelItemCount() == 0:
            self._add_placeholder_item("No document structure found", 0)
        else:
            # ✅ Expand all and then update icons to show downward triangles
            self.expandAll()
            self._update_all_icons_after_expand()
            self.resizeColumnToContents(0)
            self.resizeColumnToContents(1)

    def _update_all_icons_after_expand(self):
        """Update all item icons after expandAll to show correct triangle direction"""
        def update_item(item):
            level = item.data(0, Qt.UserRole + 1)
            if level is not None:
                has_children = item.childCount() > 0
                is_expanded = item.isExpanded()
                icon = self._create_triangle_icon(
                    level,
                    expanded=(has_children and is_expanded)
                )
                item.setIcon(0, icon)

            for i in range(item.childCount()):
                update_item(item.child(i))

        for i in range(self.topLevelItemCount()):
            update_item(self.topLevelItem(i))

    def refresh_tree(self):
        """Refresh the tree with current document structure"""
        self.clear()
        if not hasattr(self.main_window, 'editor_manager'):
            self._add_placeholder_item("No editor manager available", 0)
            return

        current_editor = self.main_window.editor_manager.get_current_editor()
        if not current_editor:
            self._add_placeholder_item("No document open", 0)
            return

        try:
            content = current_editor.toPlainText()
            if not content.strip():
                self._add_placeholder_item("Document is empty", 0)
                return
            self.parse_latex_structure(content)
        except Exception as e:
            self._add_placeholder_item(f"Error parsing document: {str(e)}", 0)
###################            
    def _on_item_clicked(self, item, column):
        """Handle single click - navigate on Line column, expand/collapse on Structure column"""
        if column == 1:
            # Clicked on "Line" column - always navigate
            self.go_to_line(item, column)
        elif column == 0:
            # Clicked on "Structure" column - navigate AND toggle expand
            # The tree already handles expand/collapse automatically,
            # so we just navigate to the line as well
            self.go_to_line(item, column)
    
    
    def _create_section_icon(self, section_type, level):
        """Create specific icons for different section types"""
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        try:
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Define colors and symbols for different section types
            type_config = {
                'Part': ('P', Qt.darkRed, 14),
                'Chapter': ('C', Qt.darkBlue, 12),
                'Section': ('§', Qt.darkGreen, 11),
                'Subsection': ('s', Qt.blue, 10),
                'Subsubsection': ('ss', Qt.darkCyan, 9),
                'Paragraph': ('¶', Qt.darkMagenta, 8),
                'Environment': ('{ }', Qt.darkGray, 8),
                'Label': ('L', Qt.darkYellow, 8)
            }
            
            if section_type in type_config:
                symbol, color, font_size = type_config[section_type]
                
                # Draw background circle
                painter.setBrush(QBrush(color))
                painter.setPen(QPen(color.lighter(150), 1))
                painter.drawEllipse(1, 1, 14, 14)
                
                # Draw symbol
                font = QFont()
                font.setPointSize(font_size)                        
                font.setBold(True)
                painter.setFont(font)
                painter.setPen(QPen(Qt.white))
                painter.drawText(2, 2, 12, 12, Qt.AlignCenter, symbol)
            else:
                # Default triangle for unknown types
                return self._create_triangle_icon(level)
        finally:
            painter.end()
        return QIcon(pixmap)
    
    
    def go_to_line(self, item, column):
        """Go to the line number when item is double-clicked - precise version"""
        line_number = item.data(0, Qt.UserRole)
        if line_number and hasattr(self.main_window, 'editor_manager'):
            current_editor = self.main_window.editor_manager.get_current_editor()
            if current_editor:
                from PyQt5.QtGui import QTextCursor
                # More precise line navigation
                cursor = current_editor.textCursor()
                cursor.movePosition(QTextCursor.Start)
                for _ in range(line_number - 1):
                    cursor.movePosition(QTextCursor.NextBlock)
                current_editor.setTextCursor(cursor)
                current_editor.ensureCursorVisible()  # Ensure cursor is visible
                current_editor.setFocus()
                
                
                # Update status bar - FIXED
                lang = self.main_window.menu_language
                translations = self.main_window.translations
                status_template = translations[lang].get("status_go_to_line", "Go to line: {line}")
                status_msg = status_template.format(line=line_number)
                if hasattr(self.main_window, 'update_status_bar'):
                    self.main_window.update_status_bar(status_msg)

                # lang = getattr(self.main_window, 'menu_language', 'en')
                # if lang == "ar":
                    # status_msg = f"الانتقال إلى السطر: {line_number}"
                # else:
                    # status_msg = f"Go to line: {line_number}"
                # if hasattr(self.main_window, 'update_status_bar'):
                    # self.main_window.update_status_bar(status_msg)

class BookmarkItem:
    """Represents a single bookmark"""
    
    def __init__(self, line_number, text_snippet, editor_file_path=None):
        self.line_number = line_number
        self.text_snippet = text_snippet.strip()[:60]  # Limit snippet length
        self.editor_file_path = editor_file_path
        self.file_name = self._extract_file_name(editor_file_path)
        self.timestamp = None  # Could add timestamp if needed
    
    def _extract_file_name(self, file_path):
        """Extract just the filename from full path"""
        if not file_path:
            return "Untitled"
        import os
        return os.path.basename(file_path)
    
    def __str__(self):
        return f"Line {self.line_number}: {self.text_snippet}"

class BookmarksWidget(QWidget):
    """Widget containing the bookmarks list and controls"""

    bookmark_clicked = pyqtSignal(int, str)  # Signal emitted when bookmark is clicked
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.bookmarks = {}  # Dictionary: line_number -> BookmarkItem
        self.setup_ui()
        # ✅ Apply UI font after setup
        self.update_font()
        
    def setup_ui(self):
        """Setup the bookmarks widget UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Header with title and controls
        header_layout = QHBoxLayout()

        # ✅ Get UI font
        ui_font = self._get_ui_font()

        
        # Title
        
        title_label = QLabel(self.tr("bookmarks"))
        title_font = QFont(ui_font)           # ✅ Use UI font family
        title_font.setPointSize(ui_font.pointSize() + 2)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Clear all button
        clear_btn = QPushButton(self.tr("clear_all"))
        clear_btn.setMaximumWidth(80)
        clear_btn.setFont(ui_font)            
        clear_btn.clicked.connect(self.clear_all_bookmarks)
        header_layout.addWidget(clear_btn)
        
        layout.addLayout(header_layout)
        
        # Bookmarks tree (replacing simple list)
        from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem
        self.bookmarks_tree = QTreeWidget()
        self.bookmarks_tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.bookmarks_tree.setAlternatingRowColors(True)
        self.bookmarks_tree.setHeaderLabels(["File / Mark", "Line"])
        self.bookmarks_tree.setFont(ui_font)           # ✅ Tree content
        self.bookmarks_tree.header().setFont(ui_font)  # ✅ Tree header        
        self.bookmarks_tree.itemClicked.connect(self.on_bookmark_clicked)
        self.bookmarks_tree.setRootIsDecorated(True)
        self.bookmarks_tree.setIndentation(20)
        
        # ✅ Theme-aware stylesheet (replaces the hardcoded one)
        self.refresh_theme()        
        
        layout.addWidget(self.bookmarks_tree)
        

        # Instructions label
        instructions = QLabel(
            "Click line numbers or press F11 to toggle bookmarks\n"
            "Click bookmarks to navigate to file and line"
        )
        instructions.setFont(ui_font)  # ✅
        instructions.setStyleSheet("color: #666; font-size: 10px; font-style: italic;")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)


    def refresh_theme(self):
        from style_manager import get_tree_widget_style, get_settings_panel_style
        s  = get_tree_widget_style()
        sp = get_settings_panel_style()

        if hasattr(self, 'bookmarks_tree'):
            self.bookmarks_tree.setStyleSheet(
                _build_tree_stylesheet(s, obj_name="bookmarks_tree")  # ← ID-qualified
            )
            # Force Qt to re-evaluate the new sheet immediately
            self.bookmarks_tree.style().unpolish(self.bookmarks_tree)
            self.bookmarks_tree.style().polish(self.bookmarks_tree)
            self.bookmarks_tree.update()

        for label in self.findChildren(QLabel):
            if "font-style: italic" in (label.styleSheet() or ""):
                label.setStyleSheet(
                    f"color: {sp['help_color']}; font-size: 10px; font-style: italic;"
                )

    def tr(self, key, default=None):
        self.main_window = getattr(self, "main_window", None)

        if self.main_window is None:
            return default or key

        lang = getattr(self.main_window, "menu_language", "en")
        translations = getattr(self.main_window, "translations", {})

        return translations.get(lang, {}).get(key, default or key)

    def _get_ui_font(self):
        """Get the current UI font"""
        if hasattr(self.main_window, 'get_current_font_settings'):
            fonts = self.main_window.get_current_font_settings()
            family = fonts.get('ui_font_family', 'Arial')
            size = fonts.get('toolbar_font_size', 10)
            return QFont(family, size)
        return QFont('Arial', 10)
    
    def update_font(self):
        """Update bookmarks widget font to match interface font"""
        if hasattr(self.main_window, 'get_current_font_settings'):
            current_fonts = self.main_window.get_current_font_settings()
            ui_font_family = current_fonts.get('ui_font_family', 'Arial')
            ui_font_size = current_fonts.get('toolbar_font_size', 10)
        else:
            ui_font_family = getattr(self.main_window, 'ui_font_family', 'Arial')
            ui_font_size = getattr(self.main_window, 'toolbar_font_size', 10)

        ui_font = QFont(ui_font_family, ui_font_size)

        # Apply to tree widget
        if hasattr(self, 'bookmarks_tree'):
            self.bookmarks_tree.setFont(ui_font)
            self.bookmarks_tree.header().setFont(ui_font)

        # Apply to all labels and buttons
        for child in self.findChildren(QLabel):
            child.setFont(ui_font)
        for child in self.findChildren(QPushButton):
            child.setFont(ui_font)        
            
    def get_current_file_path(self):
        """Get current file path from editor manager"""
        if hasattr(self.main_window, 'editor_manager'):
            current_editor = self.main_window.editor_manager.get_current_editor()
            if current_editor:
                # Try to get file path from editor
                if hasattr(current_editor, 'file_path') and current_editor.file_path:
                    return current_editor.file_path
                # Try to get from editor manager's current file tracking
                if hasattr(self.main_window.editor_manager, 'current_file') and self.main_window.editor_manager.current_file:
                    return self.main_window.editor_manager.current_file
                # Try to get from editor manager's file tracking
                if hasattr(self.main_window.editor_manager, 'get_current_file_path'):
                    file_path = self.main_window.editor_manager.get_current_file_path()
                    if file_path:
                        return file_path
        return None

    def _extract_file_name(self, file_path):
        """Extract just the filename from full path"""
        if not file_path:
            return "Untitled"
        import os
        return os.path.basename(file_path)
        
    
    def add_bookmark(self, line_number, text_snippet, editor_file_path=None):
        """Add a bookmark at the specified line for specific file"""
        if not editor_file_path:
            editor_file_path = self.get_current_file_path() or "Untitled"
        
        # Initialize file entry if it doesn't exist
        if editor_file_path not in self.bookmarks:
            self.bookmarks[editor_file_path] = {}
        
        # Check if bookmark already exists
        if line_number in self.bookmarks[editor_file_path]:
            return  # Bookmark already exists
        
        bookmark = BookmarkItem(line_number, text_snippet, editor_file_path)
        self.bookmarks[editor_file_path][line_number] = bookmark
        self.refresh_bookmarks_tree()
        
        # Update line number area color
        self._update_editor_line_colors()
    
            
    
    def refresh_bookmarks_tree(self):
        """Refresh the bookmarks tree widget organized by files"""
        self.bookmarks_tree.clear()
        
        # Sort files alphabetically
        sorted_files = sorted(self.bookmarks.keys())
        
        for file_path in sorted_files:
            file_bookmarks = self.bookmarks[file_path]
            if not file_bookmarks:
                continue
            
            # Create file node
            file_name = BookmarkItem._extract_file_name(None, file_path)
            file_item = QTreeWidgetItem([file_name, f"({len(file_bookmarks)} bookmarks)"])
            file_item.setData(0, Qt.UserRole, {'type': 'file', 'file_path': file_path})
            
            # Style file node
            file_font = file_item.font(0)
            file_font.setBold(True)
            file_item.setFont(0, file_font)
            file_item.setIcon(0, self._create_file_icon())
            
            # Add bookmark children sorted by line number
            sorted_bookmarks = sorted(file_bookmarks.values(), key=lambda b: b.line_number)
            
            for bookmark in sorted_bookmarks:
                bookmark_text = f"Line {bookmark.line_number}: {bookmark.text_snippet}"
                bookmark_item = QTreeWidgetItem([bookmark_text, str(bookmark.line_number)])
                bookmark_item.setData(0, Qt.UserRole, {
                    'type': 'bookmark',
                    'line_number': bookmark.line_number,
                    'file_path': file_path
                })
                
                # Style bookmark node
                bookmark_item.setToolTip(0, f"File: {file_name}\nLine {bookmark.line_number}\nDouble-click to navigate")
                bookmark_item.setIcon(0, self._create_bookmark_icon())
                
                file_item.addChild(bookmark_item)
            
            self.bookmarks_tree.addTopLevelItem(file_item)
            file_item.setExpanded(True)  # Expand by default
        
        # Resize columns to content
        self.bookmarks_tree.resizeColumnToContents(0)
        self.bookmarks_tree.resizeColumnToContents(1)

        
    def _create_file_icon(self):
        """Create a simple file icon"""
        from PyQt5.QtGui import QPixmap, QPainter, QIcon
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw file icon
        painter.setBrush(QColor("#2196F3"))
        painter.setPen(QColor("#1976D2"))
        painter.drawRect(2, 2, 10, 12)
        painter.drawRect(4, 4, 6, 2)
        painter.drawRect(4, 7, 6, 2)
        painter.drawRect(4, 10, 4, 2)
        
        painter.end()
        return QIcon(pixmap)
        
    def _create_bookmark_icon(self):
        """Create a simple bookmark icon"""
        from PyQt5.QtGui import QPixmap, QPainter, QIcon
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw bookmark icon
        painter.setBrush(QColor("#FFC107"))
        painter.setPen(QColor("#FF8F00"))
        painter.drawRect(4, 2, 8, 12)
        # Draw bookmark notch
        points = [QPoint(8, 10), QPoint(6, 12), QPoint(10, 12)]
        painter.drawPolygon(points)
        
        painter.end()
        return QIcon(pixmap)

    def remove_bookmark(self, line_number, editor_file_path=None):
        """Remove bookmark at the specified line for specific file"""
        if not editor_file_path:
            editor_file_path = self.get_current_file_path() or "Untitled"
        
        if editor_file_path in self.bookmarks and line_number in self.bookmarks[editor_file_path]:
            del self.bookmarks[editor_file_path][line_number]
            
            # Remove file entry if no bookmarks remain
            if not self.bookmarks[editor_file_path]:
                del self.bookmarks[editor_file_path]
            
            self.refresh_bookmarks_tree()
            self._update_editor_line_colors()

    def toggle_bookmark(self, line_number, text_snippet, editor_file_path=None):
        """Toggle bookmark at the specified line for specific file"""
        if not editor_file_path:
            editor_file_path = self.get_current_file_path() or "Untitled"
        
        if (editor_file_path in self.bookmarks and 
            line_number in self.bookmarks[editor_file_path]):
            self.remove_bookmark(line_number, editor_file_path)
            return False  # Bookmark was removed
        else:
            self.add_bookmark(line_number, text_snippet, editor_file_path)
            return True  # Bookmark was added
    
    def on_bookmark_clicked(self, item, column):
        """Handle bookmark tree item click"""
        item_data = item.data(0, Qt.UserRole)
        if not item_data:
            return
        
        if item_data['type'] == 'bookmark':
            line_number = item_data['line_number']
            file_path = item_data['file_path']
            
            # Switch to the file first, then navigate to line
            self.switch_to_file_and_navigate(file_path, line_number)
        elif item_data['type'] == 'file':
            # Toggle file node expansion
            item.setExpanded(not item.isExpanded())
            
    def switch_to_file_and_navigate(self, file_path, line_number):
        """Switch to specific file and navigate to line"""
        if not hasattr(self.main_window, 'editor_manager'):
            return
        # First, try to switch to the file if it's already open
        if hasattr(self.main_window.editor_manager, '_switch_to_existing_file'):
            try:
                self.main_window.editor_manager._switch_to_existing_file(file_path)
                self.go_to_line(line_number)
            except Exception as e:
                print(f"Error opening file {file_path}: {e}")
                return
        
        else:
            # Fallback: just navigate to line if file is current
            self.go_to_line(line_number)
        
        # Emit signal for external handling
        self.bookmark_clicked.emit(line_number, file_path)
    
    def go_to_line(self, line_number):
        """Navigate to the specified line in the current editor"""
        if not hasattr(self.main_window, 'editor_manager'):
            return
        
        current_editor = self.main_window.editor_manager.get_current_editor()
        if not current_editor:
            return
        
        # Go to the specified line
        cursor = current_editor.textCursor()
        cursor.movePosition(QTextCursor.Start)
        for _ in range(line_number - 1):
            cursor.movePosition(QTextCursor.NextBlock)
        
        current_editor.setTextCursor(cursor)
        current_editor.ensureCursorVisible()
        current_editor.setFocus()
        
        status_msg = self.tr("status_go_to_line").format(line=line_number)
        if hasattr(self.main_window, 'update_status_bar'):
            self.main_window.update_status_bar(status_msg)
        
            
    def clear_all_bookmarks(self):
        """Clear all bookmarks for all files - ENHANCED to clear ALL editor styles"""
        # Clear bookmarks in widget
        self.bookmarks.clear()
        self.refresh_bookmarks_tree()
        
        editors_cleared = 0
        
        if hasattr(self.main_window, "editor_manager"):
            # MAIN APPROACH: Access through editor_files dictionary (your structure)
            if hasattr(self.main_window.editor_manager, 'editor_files'):
                #print(f"Found editor_files with {len(self.main_window.editor_manager.editor_files)} entries")
                for file_path, editor_data in self.main_window.editor_manager.editor_files.items():
                    editor = None
                    
                    # Your structure uses editor_data as a dictionary with 'editor' key
                    if isinstance(editor_data, dict) and 'editor' in editor_data:
                        editor = editor_data['editor']
                    elif hasattr(editor_data, 'editor'):
                        editor = editor_data.editor
                    elif hasattr(editor_data, '__dict__'):
                        # Search for editor-like objects in the data
                        for attr_name, attr_value in editor_data.__dict__.items():
                            if hasattr(attr_value, 'bookmarked_lines') and hasattr(attr_value, 'lineNumberArea'):
                                editor = attr_value
                                break
                    
                    if editor and hasattr(editor, 'bookmarked_lines'):
                        editor.bookmarked_lines.clear()
                        if hasattr(editor, 'lineNumberArea'):
                            editor.lineNumberArea.update()
                        editors_cleared += 1
                        #print(f"Cleared bookmarks from editor: {os.path.basename(file_path)}")
            
            # APPROACH 2: Access through editor_tabs (based on your structure analysis)
            if hasattr(self.main_window.editor_manager, 'editor_tabs'):
                editor_tabs = self.main_window.editor_manager.editor_tabs
                
                # Handle tabbed mode (single QTabWidget)
                if isinstance(editor_tabs, QTabWidget):
                    for i in range(editor_tabs.count()):
                        widget = editor_tabs.widget(i)
                        if widget and hasattr(widget, 'bookmarked_lines'):
                            widget.bookmarked_lines.clear()
                            if hasattr(widget, 'lineNumberArea'):
                                widget.lineNumberArea.update()
                            editors_cleared += 1
                            #print(f"Cleared bookmarks from tab {i}")
                
                # Handle H/V mode (list of QTabWidgets)
                elif isinstance(editor_tabs, list):
                    for tab_widget_index, tab_widget in enumerate(editor_tabs):
                        if hasattr(tab_widget, 'count'):
                            for tab_index in range(tab_widget.count()):
                                widget = tab_widget.widget(tab_index)
                                if widget and hasattr(widget, 'bookmarked_lines'):
                                    widget.bookmarked_lines.clear()
                                    if hasattr(widget, 'lineNumberArea'):
                                        widget.lineNumberArea.update()
                                    editors_cleared += 1
                                    #print(f"Cleared bookmarks from tab widget {tab_widget_index}, tab {tab_index}")
            
            # APPROACH 3: Clear current editor (fallback)
            current_editor = self.main_window.editor_manager.get_current_editor()
            if current_editor and hasattr(current_editor, 'bookmarked_lines'):
                current_editor.bookmarked_lines.clear()
                if hasattr(current_editor, 'lineNumberArea'):
                    current_editor.lineNumberArea.update()
                editors_cleared += 1
                #print(f"Cleared bookmarks from current editor")
            
            # APPROACH 4: Find ALL BookmarksManager widgets via QApplication
            from PyQt5.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                for widget in app.allWidgets():
                    # Check for your specific BookmarksManager class
                    if (hasattr(widget, 'bookmarked_lines') and 
                        hasattr(widget, 'lineNumberArea') and
                        hasattr(widget, 'textCursor') and
                        type(widget).__name__ in ['BookmarksManager', 'AutoCompletion']):
                        widget.bookmarked_lines.clear()
                        widget.lineNumberArea.update()
                        editors_cleared += 1
                        #print(f"Cleared bookmarks from widget: {type(widget).__name__}")
        
        # Fallback for single editor
        elif hasattr(self.main_window, "editor"):
            if hasattr(self.main_window.editor, 'bookmarked_lines'):
                self.main_window.editor.bookmarked_lines.clear()
                if hasattr(self.main_window.editor, 'lineNumberArea'):
                    self.main_window.editor.lineNumberArea.update()
                editors_cleared += 1
        
        # Update status bar with count of editors cleared
        status_msg = self.tr("status_editors_cleared").format(editors=editors_cleared)
        if hasattr(self.main_window, 'update_status_bar'):
            self.main_window.update_status_bar(status_msg)
        
        #print(f"Successfully cleared bookmarks from {editors_cleared} editors")


    def save_bookmarks_to_config(self):
        """Save bookmarks to configuration - FIXED VERSION"""
        try:
            if not hasattr(self.main_window, 'config_manager'):
                print("No config_manager available for saving bookmarks")
                return False
            
            # Ensure bookmarks section exists
            if not self.main_window.config_manager.config.has_section('bookmarks'):
                self.main_window.config_manager.config.add_section('bookmarks')
            
            bookmarks_data = {}
            
            # Convert bookmarks to serializable format
            for file_path, file_bookmarks in self.bookmarks.items():
                if file_bookmarks:  # Only save non-empty bookmark sets
                    bookmarks_data[file_path] = {}
                    for line_number, bookmark in file_bookmarks.items():
                        bookmarks_data[file_path][str(line_number)] = {
                            'line_number': bookmark.line_number,
                            'text_snippet': bookmark.text_snippet,
                            'file_path': bookmark.editor_file_path or file_path
                        }
            
            # Save to config as JSON string
            import json
            bookmarks_json = json.dumps(bookmarks_data, indent=2, ensure_ascii=False)
            self.main_window.config_manager.config.set('bookmarks', 'saved_bookmarks', bookmarks_json)
            
            # Force save the config
            self.main_window.config_manager.save_config()
            
            bookmark_count = sum(len(fb) for fb in bookmarks_data.values())
            #print(f"Successfully saved {bookmark_count} bookmarks for {len(bookmarks_data)} files")
            return True
            
        except Exception as e:
            print(f"Error saving bookmarks to config: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def load_bookmarks_from_config(self):
        """Load bookmarks from configuration - FIXED VERSION"""
        try:
            if not hasattr(self.main_window, 'config_manager'):
                #print("No config_manager available for loading bookmarks from load_bookmarks_from_config")
                return False
            
            # Ensure bookmarks section exists
            if not self.main_window.config_manager.config.has_section('bookmarks'):
                print("No bookmarks section in config, creating empty one")
                self.main_window.config_manager.config.add_section('bookmarks')
                self.main_window.config_manager.save_config()
                return True
            
            # Get bookmarks JSON from config
            bookmarks_json = self.main_window.config_manager.config.get('bookmarks', 'saved_bookmarks', fallback='{}')
            
            if not bookmarks_json or bookmarks_json.strip() == '{}':
                #print("No saved bookmarks found in config")
                return True
            
            # Parse JSON data
            import json
            bookmarks_data = json.loads(bookmarks_json)
            
            # Clear existing bookmarks
            self.bookmarks.clear()
            loaded_count = 0
            
            # Load bookmarks from data
            for file_path, file_bookmarks in bookmarks_data.items():
                if file_bookmarks:
                    self.bookmarks[file_path] = {}
                    for line_str, bookmark_data in file_bookmarks.items():
                        try:
                            line_number = int(line_str)
                            bookmark = BookmarkItem(
                                bookmark_data['line_number'],
                                bookmark_data['text_snippet'],
                                bookmark_data.get('file_path', file_path)
                            )
                            self.bookmarks[file_path][line_number] = bookmark
                            loaded_count += 1
                        except (ValueError, KeyError) as e:
                            print(f"Error loading bookmark {line_str} for {file_path}: {e}")
            
            # Refresh display
            self.refresh_bookmarks_tree()
            
            # Update current editor's bookmarks display
            self._update_editor_line_colors()
            
            #print(f"Successfully loaded {loaded_count} bookmarks for {len(self.bookmarks)} files")
            return True
            
        except Exception as e:
            print(f"Error loading bookmarks from config: {e}")
            import traceback
            traceback.print_exc()
            self.bookmarks.clear()
            return False

            
    def clear_file_bookmarks(self, file_path):
        """Clear all bookmarks for a specific file"""
        if file_path in self.bookmarks:
            del self.bookmarks[file_path]
            self.refresh_bookmarks_tree()
            self._update_editor_line_colors()
    
    def has_bookmark(self, line_number, editor_file_path=None):
        """Check if a bookmark exists at the specified line for specific file"""
        if not editor_file_path:
            editor_file_path = self.get_current_file_path() or "Untitled"
        
        return (editor_file_path in self.bookmarks and 
                line_number in self.bookmarks[editor_file_path])
    
    def get_bookmarks_count(self):
        """Get the total number of bookmarks across all files"""
        total = 0
        for file_bookmarks in self.bookmarks.values():
            total += len(file_bookmarks)
        return total
    
    def get_file_bookmarks_count(self, file_path):
        """Get number of bookmarks for specific file"""
        return len(self.bookmarks.get(file_path, {}))
    
    def get_current_file_bookmarks(self):
        """Get bookmarks for currently active file"""
        current_file = self.get_current_file_path()
        if current_file and current_file in self.bookmarks:
            return set(self.bookmarks[current_file].keys())
        return set()
    
    def _update_editor_line_colors(self):
        """Update editor line number colors to show bookmarks"""
        if hasattr(self.main_window, 'editor_manager'):
            current_editor = self.main_window.editor_manager.get_current_editor()
            if current_editor and hasattr(current_editor, 'lineNumberArea'):
                # Update the editor's bookmark tracking
                if hasattr(current_editor, 'sync_bookmarks_with_widget'):
                    current_editor.sync_bookmarks_with_widget(self)
                current_editor.lineNumberArea.update()
