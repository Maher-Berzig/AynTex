# main_window.py
"""
Main Window Class - Core window setup 
"""
import os
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QPlainTextEdit, QVBoxLayout, QSplitter, QTabWidget, QTextEdit, QMessageBox, 
    QScrollArea, QLabel, QApplication, QMenu, QToolBar, QPushButton, QShortcut, QAction, QTextBrowser
)
from PyQt5.QtCore import QObject, QEvent, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QKeySequence, QTextCursor, QTextCharFormat, QIcon


from editor_manager import EditorManager
from pdf_manager import PDFManager
from toolbar_manager import ToolbarManager, BookmarksWidget
from menu_manager import MenuManager
from layout_manager import LayoutManager
from config_manager import ConfigManager
from settings_manager import SettingsManager 
from settings_manager import SettingsDialog as sd 
from translations import translations
from icons_manager import IconsManager
from compilation_manager import CompilationManager
from search_replace_dialog import SearchReplaceDialog
from side_panel import SidePanel
from backmatter_compile import BackmatterCompile

from latex_highlighter import LaTeXHighlighter
from ai_tab import AIAssistantWidget
from todo_list import should_auto_open_todo
from cwl_manager import CWLManager
from completion_settings_widget import CompletionSettingsWidget
from tip_day import create_tip_dialog




class MainWindow(QMainWindow):
    output_tabs_visibility_changed = pyqtSignal(bool)
    def __init__(self):
        super().__init__()
        self.initializing = True
        self.is_rtl = False
        self.is_pdf_toolbar_visible = True
        self._session_loaded = False 
        

        # DO NOT instantiate SpellChecker here — defer until the window
        # is fully constructed so all UI components it may reference exist.
        self.spell_checker = None
        
        QTimer.singleShot(0, self._init_spell_checker)
        
        # THEN initialize context menu manager
        from context_menu import ContextMenuManager
        self.context_menu_manager = ContextMenuManager(self)        
        
        self.icons_manager = IconsManager()

        self.init_application()        
        # Setup main window and UI       
        self.setup_main_window()        
        # Creates layout, adds to central widget        
        self.setup_ui()           
        
        # Post-init setup after UI is stable
        self._post_init_setup()        

        # Create a global shortcut
        self.setup_keyboard_shortcuts()
        self.initializing = False
        self.sync_all_tab_states() 
               
        self.init_cwl_manager()
    
        # ✅ ADD THIS: Create the completer manager
        from latex_completer_manager import LaTeXCompleterManager
        self.latex_completer_manager = LaTeXCompleterManager(self)
        

        from context_menu import TabContextMenu
        self.tab_context_menu = TabContextMenu(self)
        self.tab_context_menu.install()        
        
        # Install on existing editors
        self._install_completers_on_existing_editors()
        
        # After UI is set up, install context menu on any existing editors
        self._install_context_menus_on_existing_editors()
       
        QTimer.singleShot(500, self.apply_saved_visibility_settings)

    def _init_spell_checker(self):
        """Instantiate the spell checker after the event loop has started."""
        from spell_checker import SpellChecker
        self.spell_checker = SpellChecker(self)
        
        
    def init_application(self):
        """Complete application initialization sequence"""
        
        # Core settings - Initialize ALL required attributes first
        self.menu_language = "en"
        self.translations = translations        
        self.latex_engine = "Pdflatex"
        self.backmatter_engine = "Bibtex"
        self.output_encoding = "utf-8"
        
        
        self.side_panel_visible = True
        self.side_panel_on_left = True

        self.menus_initialized = False
        self.search_replace_dialog = None
        
        self._is_closing = False
        
        # Create output widgets ONCE at startup
        self.output_text = QTextBrowser()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Consolas", 10))
        self.output_text.setOpenLinks(False)
        self.output_text.setOpenExternalLinks(False)  
        self.output_text.anchorClicked.connect(self._handle_link)        

        self.errors_text = QTextEdit()
        self.errors_text.setReadOnly(True)
        self.errors_text.setFont(QFont("Consolas", 10))
        #self.errors_text.setStyleSheet("background-color: #ffecec;")
        self._apply_error_text_style()
        
        self.output_tabs_visible = True
        self.symbols_tab_visible = False
        self.commands_tab_visible = False
        self.tree_tab_visible = False
        self.bookmarks_tab_visible = False
        self.terminal_tab_visible = False

        # After all UI components are created
        self.config_manager = ConfigManager(self)
        self.bookmarks_widget = BookmarksWidget(self)

        # Load bookmarks AFTER widget exists
        self.load_bookmarks_from_config()
       
        if hasattr(self, 'config_manager'):
            saved_position = self.config_manager.get_config_value('ui', 'side_panel_on_left', 'True')
            self.side_panel_on_left = str(saved_position).strip().lower() == 'true'
        
              
        # Set up text handler after editor_manager exists
        if hasattr(self, 'editor_manager'):            
            # Set the callback for side panel
            self.latex_insert_callback = self.insert_latex_command
            
        # Install on any existing editors
        if hasattr(self, 'editor_manager') and hasattr(self.editor_manager, 'editor_files'):
            for file_path, editor_data in self.editor_manager.editor_files.items():
                editor = editor_data.get('editor')
                if editor:
                    self.context_menu_manager.install_context_menu(editor)    
            
        # In MainWindow.__init__(), after config_manager
        if hasattr(self, 'config_manager'):
            saved_engine = self.config_manager.get_config_value('latex', '_engine', 'bibtex')
            self.backmatter_engine = saved_engine
            
        if hasattr(self, 'config_manager'):
            numbers_visible = str(self.config_manager.get_config_value('ui', 'is_line_numbers_visible', 'True')).lower() == 'true'
            self.is_line_numbers_visible = numbers_visible
    
        if hasattr(self, 'config_manager'):
            markers_visible = str(self.config_manager.get_config_value('ui', 'is_fold_markers_visible', 'True')).lower() == 'true'
            self.is_fold_markers_visible = markers_visible
    
            
        # If you have a settings manager class somewhere:
        if not hasattr(self, 'settings_manager'):
            self.settings_manager = SettingsManager(self)

        # Sync language to Knowledge Database if open
        if hasattr(self, '_knowledge_db_instances'):
            for kb in self._knowledge_db_instances:
                if kb and hasattr(kb, 'refresh_language'):
                    try:
                        kb.refresh_language()
                    except Exception:
                        pass
            
        output_tabs_visible = str(self.config_manager.get_config_value('layout', 'output_tabs_visible', 'True')).lower() == 'true'
       
        # Load UI settings from config
        self.load_ui_settings_from_config()
        
        # Initialize core managers
        self.init_managers()       
        
        # ✅ Storage for PDF info captured before cleanup
        self._captured_pdf_files = {}
              
        # Check if todo list should auto-open
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(500, self._check_auto_open_todo)
        

    def _handle_link(self, url):
        path = url.toLocalFile()

        if not path:
            import urllib.parse
            path = urllib.parse.unquote(url.toString())

        path = os.path.normpath(path)

        #print("Resolved path:", path)

        if os.path.isfile(path):
            self._open_log_in_editor(path)
        else:
            #print("File does not exist!")
            pass
        
    def _open_log_in_editor(self, href: str):
        """Open the log file carried by *href* in the editor."""
        path = os.path.normpath(href)
        if os.path.isfile(path):
            self.editor_manager.open_specific_file(path)
        else:
            QMessageBox.warning(
                self,
                "File Not Found",
                f"Cannot open log file:\n{path}",
            )


    def _apply_error_text_style(self):
        from style_manager import get_error_style
        style = get_error_style()
        self.errors_text.setStyleSheet(
            f"background-color: {style['bg']}; color: {style['color']};"
        )

    def show_tip_of_the_day(self, force=True):
        existing = getattr(self, "tip_dialog", None)
        if existing is not None:
            try:
                existing.isVisible()
                existing.show(); existing.raise_(); existing.activateWindow()
                return
            except RuntimeError:
                self.tip_dialog = None

        dialog = create_tip_dialog(parent=self, main_window=self, force=force)   # <-- use force parameter

        if dialog is None:
            return

        self.tip_dialog = dialog
        self.tip_dialog.setAttribute(Qt.WA_DeleteOnClose)
        self.tip_dialog.destroyed.connect(lambda: setattr(self, "tip_dialog", None))
        self.tip_dialog.show()
        self.tip_dialog.raise_()
        self.tip_dialog.activateWindow()


    def showEvent(self, event):
        super().showEvent(event)
        if not hasattr(self, "_tip_shown"):
            self._tip_shown = True
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(1000, lambda: self.show_tip_of_the_day(force=False))
            
    
    def _check_auto_open_todo(self):
        """Check and auto-open todo list if enabled"""
        try:
            from todo_list import should_auto_open_todo
            if should_auto_open_todo():
                self.open_todo_list_tab()  # <-- DIRECT CALL, no extra timer
                #print("✅ Auto-opened Todo List")
        except Exception as e:
            pass
            #print(f"Error checking auto-open todo: {e}")


    def setup_keyboard_shortcuts(self):
        """Create global shortcuts safely"""
        from PyQt5.QtWidgets import QShortcut
        from PyQt5.QtGui import QKeySequence
        
       
        # for action in self.findChildren(QAction):
            # if action.shortcut().toString():
                # print(action.text(), action.shortcut().toString())


        try:
            if hasattr(self, 'editor_manager') and self.editor_manager:
                
                # Zoom the editor
                zoom_in_shortcut = QShortcut(QKeySequence("Ctrl++"), self)
                zoom_in_shortcut.activated.connect(self.zoom_in)   # ✅ fixed

                zoom_out_shortcut = QShortcut(QKeySequence("Ctrl+-"), self)
                zoom_out_shortcut.activated.connect(self.zoom_out) # ✅ fixed
                
                # Go to line
                go_to_line_shortcut = QShortcut(QKeySequence("Ctrl+G"), self)
                go_to_line_shortcut.activated.connect(self.editor_manager.go_to_line)
                
                # Delete auxiliary files
                delete_aux_action_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Del"), self)
                delete_aux_action_shortcut.activated.connect(self.editor_manager.delete_auxiliary_files)                
                
                # Toggle symbols tab: Alt+S
                symbols_shortcut = QShortcut(QKeySequence("Alt+S"), self)
                symbols_shortcut.activated.connect(self.toggle_symbols_tab)
                
                # Toggle commands tab: Alt+C
                commands_shortcut = QShortcut(QKeySequence("Alt+C"), self)
                commands_shortcut.activated.connect(self.toggle_commands_tab)
                
                # Toggle tree tab: Alt+R
                tree_shortcut = QShortcut(QKeySequence("Alt+R"), self)
                tree_shortcut.activated.connect(self.toggle_tree_tab)
                
                # Toggle bookmarks tab: Alt+M
                bookmarks_shortcut = QShortcut(QKeySequence("Alt+M"), self)
                bookmarks_shortcut.activated.connect(self.toggle_bookmarks_tab)
                
                # Toggle terminal tab: Alt+N
                terminal_shortcut = QShortcut(QKeySequence("Alt+N"), self)
                terminal_shortcut.activated.connect(self.toolbar_manager.toggle_terminal_tab)
                
                # ✅ NEW: LaTeX environment selection shortcuts
                select_env_forward = QShortcut(QKeySequence("Ctrl+Shift+Up"), self)
                select_env_forward.activated.connect(
                    lambda: self._select_latex_environment('forward')
                )
                #print("Created Ctrl+Shift+Up shortcut")
                select_env_backward = QShortcut(QKeySequence("Ctrl+Shift+Down"), self)
                select_env_backward.activated.connect(
                    lambda: self._select_latex_environment('backward')
                )
                #print("Created Ctrl+Shift+Down shortcut")
        

            # ✅ NEW: PDF navigation shortcuts (Alt+Left and Alt+Right)
            # Navigate back in PDF link history
            pdf_back_shortcut = QShortcut(QKeySequence("Alt+Left"), self)
            pdf_back_shortcut.activated.connect(self._pdf_navigate_back)
            
            # Navigate forward in PDF link history
            pdf_forward_shortcut = QShortcut(QKeySequence("Alt+Right"), self)
            pdf_forward_shortcut.activated.connect(self._pdf_navigate_forward)
            
            # Side panel shortcuts (Ctrl+1..Ctrl+9, Ctrl+0)
            for i in range(1, 11):
                key = "Ctrl+0" if i == 10 else f"Ctrl+{i}"
                shortcut = QShortcut(QKeySequence(key), self)
                # Capture the index (1‑based) in a closure
                shortcut.activated.connect(lambda idx=i: self._activate_side_panel_button(idx))
                shortcut.setContext(Qt.ApplicationShortcut)   # works even if side panel not focused

            # Quick-jump popup for all side panel buttons
            quick_jump_shortcut = QShortcut(QKeySequence("Ctrl+Space"), self)
            quick_jump_shortcut.activated.connect(self.side_panel.show_quick_jump)
            quick_jump_shortcut.setContext(Qt.ApplicationShortcut)
    
        except Exception as e:
            print(f"Warning: Could not create shortcuts: {e}")


    def _activate_side_panel_button(self, one_based_index):
        """Activate the side panel button at the given 1-based index."""
        # Set the flag HERE — after the shortcut fired, before the spurious char arrives
        if not hasattr(self, 'side_panel'):
            return
        idx = one_based_index - 1
        if 0 <= idx < len(self.side_panel.buttons):
            self.side_panel.buttons[idx].click()    
            
    def _register_side_panel_shortcuts(self):
        """Register per-button custom shortcuts from side panel config."""
        # Clear previously registered shortcuts
        if not hasattr(self, '_side_panel_custom_shortcuts'):
            self._side_panel_custom_shortcuts = []
        for sc in self._side_panel_custom_shortcuts:
            sc.setEnabled(False)
            sc.deleteLater()
        self._side_panel_custom_shortcuts.clear()

        for i, cmd in enumerate(self.side_panel.commands):
            key = cmd.get("shortcut", "").strip()
            if not key:
                continue
            try:
                sc = QShortcut(QKeySequence(key), self)
                sc.activated.connect(lambda idx=i: self._activate_side_panel_button_by_cmd_index(idx))
                sc.setContext(Qt.ApplicationShortcut)
                self._side_panel_custom_shortcuts.append(sc)
            except Exception as e:
                print(f"Invalid shortcut '{key}': {e}")

    def _activate_side_panel_button_by_cmd_index(self, cmd_index):
        """Click the side panel button corresponding to command at cmd_index."""
        btn_index = 0
        for i, cmd in enumerate(self.side_panel.commands):
            if not cmd.get("label", "").strip() or not cmd.get("latex", "").strip():
                continue
            if i == cmd_index:
                if btn_index < len(self.side_panel.buttons):
                    self.side_panel.buttons[btn_index].click()
                return
            btn_index += 1            
            
            
    def _select_latex_environment(self, direction):
        """Select LaTeX environment - optimized with caching"""
        import re
        from PyQt5.QtGui import QTextCursor
        
        editor = self.editor_manager.get_current_editor()
        if editor is None:
            return
        
        current_file = self.editor_manager.get_current_file_path()
        if not (current_file and current_file.lower().endswith('.tex')):
            return
        
        cursor = editor.textCursor()
        text = editor.toPlainText()
        current_pos = cursor.position()
        text_len = len(text)
        
        # ✅ Cache key based on text hash and length
        cache_key = (hash(text[:1000]) if text_len > 1000 else hash(text), text_len)
        
        # ✅ Use cached environments if available
        if not hasattr(self, '_env_cache') or self._env_cache.get('key') != cache_key:
            self._env_cache = {
                'key': cache_key,
                'envs': self._parse_environments_fast(text)
            }
        
        all_envs = self._env_cache['envs']
        
        if not all_envs:
            return
        
        # Find environments containing cursor
        containing = [env for env in all_envs 
                      if env['begin_pos'] <= current_pos <= env['end_pos']]
        containing.sort(key=lambda x: x['end_pos'] - x['begin_pos'])
        
        try:
            if direction == 'forward':
                if not containing:
                    # Find next environment after cursor
                    for env in all_envs:
                        if env['begin_pos'] >= current_pos:
                            self._select_environment(editor, cursor, env)
                            return
                    return
                
                # Check current selection level
                if cursor.hasSelection():
                    sel_start = cursor.selectionStart()
                    sel_end = cursor.selectionEnd()
                    
                    for i, env in enumerate(containing):
                        if env['begin_pos'] == sel_start and env['end_pos'] == sel_end:
                            # Move to outer level
                            if i < len(containing) - 1:
                                self._select_environment(editor, cursor, containing[i + 1])
                            return
                
                # Select innermost
                self._select_environment(editor, cursor, containing[0])
                
            else:  # backward
                if not containing:
                    # Find previous environment before cursor
                    for env in reversed(all_envs):
                        if env['end_pos'] <= current_pos:
                            self._select_environment(editor, cursor, env)
                            return
                    return
                
                # Check current selection level
                if cursor.hasSelection():
                    sel_start = cursor.selectionStart()
                    sel_end = cursor.selectionEnd()
                    
                    for i, env in enumerate(containing):
                        if env['begin_pos'] == sel_start and env['end_pos'] == sel_end:
                            # Move to inner level
                            if i > 0:
                                self._select_environment(editor, cursor, containing[i - 1])
                            return
                
                # Select innermost
                self._select_environment(editor, cursor, containing[0])
                
        except Exception as e:
            print(f"Error selecting LaTeX environment: {e}")

    def _select_environment(self, editor, cursor, env):
        """Helper to select an environment"""
        from PyQt5.QtGui import QTextCursor
        cursor.setPosition(env['begin_pos'])
        cursor.setPosition(env['end_pos'], QTextCursor.KeepAnchor)
        editor.setTextCursor(cursor)

    def _parse_environments_fast(self, text):
        """Fast environment parser with early termination"""
        import re
        
        # Combined pattern for both begin and end
        pattern = re.compile(r'\\(begin|end)\{([^}]+)\}')
        
        stack = []
        matched = []
        
        for match in pattern.finditer(text):
            cmd_type = match.group(1)
            env_name = match.group(2)
            
            if cmd_type == 'begin':
                stack.append({
                    'name': env_name,
                    'pos': match.start(),
                    'end_pos': match.end()
                })
            else:  # 'end'
                # Find matching begin (last one with same name)
                for i in range(len(stack) - 1, -1, -1):
                    if stack[i]['name'] == env_name:
                        begin_item = stack.pop(i)
                        matched.append({
                            'name': env_name,
                            'begin_pos': begin_item['pos'],
                            'end_pos': match.end()
                        })
                        break
        
        # Sort by begin position for binary search potential
        matched.sort(key=lambda x: x['begin_pos'])
        return matched
    

    def setup_main_window(self):
        """Setup main window properties"""
        self.setWindowTitle(self.translations[self.menu_language]["window_title"])

        screen = QApplication.primaryScreen().availableGeometry()
        screen_width = screen.width()
        screen_height = screen.height()

        # Define ratios instead of fixed values
        window_width = int(screen_width * 0.8)   # 80% of screen width
        window_height = int(screen_height * 0.8) # 80% of screen height

        # Add maximum/minimum constraints
        window_width = min(window_width, 1280)
        window_height = min(window_height, 720)

        self.resize(window_width, window_height)
        self.setMinimumSize(800, 400)
    
    def load_ui_settings_from_config(self):
        """Load UI settings from configuration file"""
        self.menu_language = self.config_manager.get_config_value('ui', 'menu_language', 'en')

        # Editor font
        self.editor_font_family = self.config_manager.get_config_value(
            'ui', 'editor_font_family', 'Consolas'
        )
        self.editor_font_size = int(self.config_manager.get_config_value(
            'ui', 'editor_font_size', '11'
        ))

        # UI font
        self.ui_font_family = self.config_manager.get_config_value(
            'ui', 'ui_font_family', 'Arial'
        )
        self.toolbar_font_size = int(self.config_manager.get_config_value(
            'ui', 'toolbar_font_size', '10'
        ))

        # ✅ Load toolbar text visibility
        self._toolbar_text_visible = self.config_manager.get_config_value(
            'ui', 'toolbar_text_visible', 'True'
        ).lower() == 'true'

        # ✅ Load tooltips visibility
        self._tooltips_visible = self.config_manager.get_config_value(
            'ui', 'tooltips_visible', 'True'
        ).lower() == 'true'   
        # Apply fonts after loading
        if hasattr(self, 'editor_manager') and self.editor_manager:
            self.editor_manager.update_editor_font(self.editor_font_family, self.editor_font_size)
        self.update_ui_fonts()        
 


    def _apply_initial_visibility_settings(self):
        """Apply loaded visibility settings to UI components"""        
        # Sync menu checkboxes
        if hasattr(self, 'menu_manager'):
            mm = self.menu_manager
            if hasattr(mm, 'line_numbers_action'):
                mm.line_numbers_action.setChecked(self.is_line_numbers_visible)
            if hasattr(mm, 'fold_markers_action'):
                mm.fold_markers_action.setChecked(self.is_fold_markers_visible)
            if hasattr(mm, 'folding_menu'):
                mm.folding_menu.setEnabled(self.is_fold_markers_visible)
        
        # Apply to editors
        if hasattr(self, 'editor_manager') and hasattr(self.editor_manager, 'get_all_editors'):
            for editor in self.editor_manager.get_all_editors():
                if hasattr(editor, 'set_line_numbers_visible'):
                    editor.set_line_numbers_visible(self.is_line_numbers_visible)
                if hasattr(editor, 'set_fold_markers_visible'):
                    editor.set_fold_markers_visible(self.is_fold_markers_visible)        


    
    def init_managers(self):
        """Initialize all manager classes"""
        # Icons
        self.icons_manager = IconsManager()
        self.load_rtl_setting()
        
        # Initialize managers
        self.editor_manager = EditorManager(self)
        self.pdf_manager = PDFManager(self)
        self.menu_manager = MenuManager(self)
        self.toolbar_manager = ToolbarManager(self)
        self.layout_manager = LayoutManager(self)

        # NEW: Initialize toolbar with extended functionality
        self.toolbar_manager = ToolbarManager(self)
        self.toolbar_manager.icons_manager = self.icons_manager
        
        self.compilation_manager = CompilationManager(self)
        self.backmatter_compile = BackmatterCompile(self)

        # Initialize side panel first
        self.side_panel = SidePanel(self)  
        # Load side panel commands from config
        self.load_side_panel_commands()

        
        # Then initialize settings manager
        self.settings_manager = SettingsManager(self)        
        
        #self.sd = sd(self)
        
        # Setup manager UIs — MUST be BEFORE setup_ui()
        self.editor_manager.setup_ui()   # ← Creates editor_tabs
        self.pdf_manager.setup_ui()      # ← Creates pdf_tabs
       
        
                
    def _post_init_setup(self):
        """Complete initialization after UI is stable"""
        try:
            # Setup manager UIs (creates editor_tabs, pdf_tabs)
            self.editor_manager.setup_ui()
            self.pdf_manager.setup_ui()   
          
            # Auto-open last file
            self.auto_open_last_file()
            
            # Open recent files        
            self.load_session_on_startup()
            
            # NEW: Restore PDF zoom factor after a delay
            QTimer.singleShot(500, self._restore_pdf_zoom_factor)
            
            # Apply saved toolbar text visibility
            if not getattr(self, '_toolbar_text_visible', True):
                if hasattr(self, 'toolbar_manager') and self.toolbar_manager.main_toolbar:
                    self.toolbar_manager.main_toolbar.setToolButtonStyle(Qt.ToolButtonIconOnly)

            # Apply saved tooltip visibility
            if not getattr(self, '_tooltips_visible', True):
                from menu_manager import TooltipBlockFilter
                self._tooltip_filter = TooltipBlockFilter(self)
                QApplication.instance().installEventFilter(self._tooltip_filter)     

            
        except Exception as e:
            print(f"Error in post-init setup: {e}")
            import traceback
            traceback.print_exc()


        
    def setup_ui(self):
        if getattr(self, 'ui_setup_done', False):
            return
        self.ui_setup_done = True        
       
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(5,5,5,5) # Default(5, 5, 5, 5)
        self.main_layout.setSpacing(5) # Default 5
        
        # Create menu bar FIRST (before any layout setup)        
        self.menu_manager.create_menu_bar()
        self.restore_menubar_state() 
        # Create toolbar SECOND        
        self.toolbar_manager.create_main_toolbar()
        self.restore_toolbar_state()
        
        # Setup layout manager and get main splitter THIRD                
        if not hasattr(self, 'main_splitter'):
            self.main_splitter = self.layout_manager.setup_layout()            

     
        # Add main splitter to layout
        self.main_layout.addWidget(self.main_splitter)
        
        # In setup_ui, replace the entire status bar block with:
        self.status_bar = self.statusBar()
        self.status_bar.setVisible(True)
        self.status_bar.setSizeGripEnabled(True)
        self.position_label = QLabel("Ln 1, Col 1")
        self.status_bar.addPermanentWidget(self.position_label)
        QTimer.singleShot(10300, lambda: self.update_status_bar(timeout=0, show_extras=False))

      
        # Force initial layout arrangement
        self.layout_manager._arrange_containers()

        # Update UI language
        self.update_ui_language
        
        # Restore menu bar visibility from config
        if hasattr(self, 'config_manager'):
            try:
                menubar_visible = self.config_manager.get_config_value('ui', 'menubar_visible', default=True)
                self.menuBar().setVisible(menubar_visible)
                
                # Update action state
                if hasattr(self, 'toggle_menubar_action'):
                    self.toggle_menubar_action.setChecked(menubar_visible)
            except:
                pass
                
        self._apply_initial_visibility_settings()     

    # Add these methods to your MainWindow class

    def zoom_in(self):
        """Increase font size of the current editor."""
        editor = self._get_current_editor()
        if editor is None:
            return
        font = editor.font()
        size = font.pointSize()
        if size < 72:   # upper bound
            font.setPointSize(size + 1)
            editor.setFont(font)

    def zoom_out(self):
        """Decrease font size of the current editor."""
        editor = self._get_current_editor()
        if editor is None:
            return
        font = editor.font()
        size = font.pointSize()
        if size > 6:    # lower bound
            font.setPointSize(size - 1)
            editor.setFont(font)

    def _get_current_editor(self):
        """Helper to get the currently active editor widget."""
        if hasattr(self, 'editor_manager') and self.editor_manager:
            return self.editor_manager.get_current_editor()
        return None
        
    def _restore_pdf_zoom_factor(self):
        """Restore PDF zoom factor from config"""
        try:
            # if not hasattr(self, 'config_manager'):
                # print("⚠️ No config_manager for restoring zoom")
                # return
            
            # if not hasattr(self, 'pdf_manager'):
                # print("⚠️ No pdf_manager for restoring zoom")
                # return
            
            # Get saved zoom factor
            zoom = self.config_manager.get_pdf_zoom_factor(default=1.0)
            #print(f"📊 Restoring PDF zoom factor: {zoom}")
            
            # Only apply if not default
            if zoom != 1.0:
                # Check if there are any PDF viewers to apply zoom to
                if hasattr(self.pdf_manager, 'pdf_files') and self.pdf_manager.pdf_files:
                    self.pdf_manager.set_zoom_factor(zoom)
                    #print(f"✅ PDF zoom factor restored to: {zoom}")
                else:
                    # Store for later application when PDFs are opened
                    self.pdf_manager.current_zoom_factor = zoom
                    #print(f"📊 Stored zoom factor for later: {zoom}")
            else:
                pass
                #print("📊 Zoom is default (1.0), no restoration needed")
                
        except Exception as e:
            pass

            
    def update_ui_language(self):
        """Update all UI elements with current language"""
        lang = self.menu_language
        t = self.translations[lang]
        
        # Update window title
        self.setWindowTitle(t["window_title"])
        self.layout_manager.retranslate_output_tabs()
        
        # Update menu
        if hasattr(self, 'menu_manager') and hasattr(self.menu_manager, 'update_language'):
            self.menu_manager.update_language()
        
        # Update toolbar
        if hasattr(self, 'toolbar_manager'):
            self.toolbar_manager.update_language()
        
                   
    def load_highlighting_colors(self):
        """Load highlighting colors from config and apply to editor"""
        if hasattr(self, 'editor') and self.editor and hasattr(self.editor, 'highlighter'):
            highlighter = self.editor.highlighter
            if highlighter:
                # Load colors from config
                highlighter.load_colors_from_config()
                # Rebuild highlighting rules
                highlighter.highlighting_rules = []
                highlighter.setup_highlighting_rules()
                # Force rehighlight
                highlighter.rehighlight()


    def update_status_bar(self, message=None, timeout=3000, show_extras=True):
        """Update status bar with current state"""
        
        if not hasattr(self, 'status_bar'):
            return

        self.status_bar.setVisible(True)

        lang = self.menu_language

        # Layout status
        layout_status = ""
        if hasattr(self, 'layout_manager'):
            layout_status = self.layout_manager.get_layout_status()

        # File status
        editor_status = ""
        if hasattr(self, 'editor_manager'):
            editor_status = (
                self.translations[lang]["status_no_tex_file"]
                if not self.editor_manager.editor_files else ""
            )

        pdf_status = ""
        if hasattr(self, 'pdf_manager'):
            pdf_status = (
                self.translations[lang]["status_no_pdf_file"]
                if not hasattr(self.pdf_manager, 'pdf_files') or not self.pdf_manager.pdf_files
                else ""
            )

        # Other info
        text_direction = (
            self.translations[lang]["status_text_rtl"]
            if self.is_rtl else
            self.translations[lang]["status_text_ltr"]
        )

        menu_language = (
            self.translations[lang]["status_menu_ar"]
            if self.menu_language == "ar" else
            self.translations[lang]["status_menu_en"]
        )

        output_status = (
            self.translations[lang]["status_output_shown"]
            if self.output_tabs_visible else
            self.translations[lang]["status_output_hidden"]
        )

        # Build message
        if message:
            status_text = message
        else:
            status_text = self.translations[lang]["status_ready"]

        # Add extras
        extras = [layout_status, editor_status, pdf_status, text_direction, menu_language, output_status]
        extras = [e for e in extras if e]

        if show_extras:
            extras = [layout_status, editor_status, pdf_status, text_direction, menu_language, output_status]
            extras = [e for e in extras if e]

            if extras:
                status_text += " | " + " | ".join(extras)

        # ✅ Final display (NO recursion)
        self.status_bar.showMessage(status_text, timeout)
        
    def update_position(self):
        """Update cursor position in status bar"""
        if not hasattr(self, 'position_label'):
            return
        editor = None
        if hasattr(self, 'editor_manager'):
            editor = self.editor_manager.get_current_editor()
        
        # Check if editor has textCursor method (excludes tool widgets)
        if editor and hasattr(editor, 'textCursor'):
            cursor = editor.textCursor()
            line = cursor.blockNumber() + 1
            col = cursor.columnNumber() + 1
            self.position_label.setText(f"Ln {line}, Col {col}")
        else:
            self.position_label.setText("Ln 1, Col 1")
            
   

    def update_title(self):
        """Update window title to show full path and filename"""
        try:
            lang = self.menu_language
            t = self.translations[lang]
            app_name = t.get("app_name", "AynTeX")
            
            if hasattr(self, 'editor_manager') and self.editor_manager:
                current_file = self.editor_manager.current_file
                
                if current_file and current_file in self.editor_manager.editor_files:
                    # Get full path
                    full_path = os.path.abspath(current_file)
                    filename = os.path.basename(current_file)
                    
                    # Check if modified
                    is_modified = self.editor_manager.editor_files[current_file].get('modified', False)
                    modified_marker = "*" if is_modified else ""
                    
                    # Show full path in title
                    self.setWindowTitle(f"{full_path} - {app_name}")
                else:
                    self.setWindowTitle(f"{app_name}")
            else:
                self.setWindowTitle(f"{app_name}")
                
        except Exception as e:
            print(f"❌ Error updating title: {e}")
            self.setWindowTitle("AynTeX")        

    def closeEvent(self, event):         
        """Handle window close event with save prompt"""
        # Set the closing flag at the start
        self._is_closing = True
        """Handle window close event with save prompt"""
        try:
            # ========== ADD THIS SECTION AT THE BEGINNING ==========
            # Save splitter sizes before closing
            if hasattr(self, 'layout_manager') and self.layout_manager:
                #print("💾 Saving splitter sizes on close...")
                self.layout_manager.save_current_splitter_sizes()
            
            # Save PDF zoom factor before closing
            if hasattr(self, 'pdf_manager') and self.pdf_manager:
                #print("💾 Saving PDF zoom factor on close...")
                self.pdf_manager.save_current_zoom_factor()
            # ========== END OF NEW SECTION ==========
            
            # Check if any editor tab is modified
            modified_files = []
            if hasattr(self, 'editor_manager'):
                for path, data in self.editor_manager.editor_files.items():
                    if data.get('modified', False):
                        filename = os.path.basename(path)
                        modified_files.append(filename)

            # Only show prompt if there are modified files
            if modified_files:
                from PyQt5.QtWidgets import QMessageBox
                reply = QMessageBox.question(
                    self,
                    "Save Changes?",
                    f"The following files have unsaved changes:\n\n{', '.join(modified_files)}\n\nDo you want to save them before exiting?",
                    QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                    QMessageBox.Save
                )

                if reply == QMessageBox.Save:
                    # Try to save all modified files
                    for path, data in self.editor_manager.editor_files.items():
                        if data.get('modified', False):
                            # Switch to tab if needed
                            if self.editor_manager.editor_layout_mode == "tabbed":
                                if data['index'] < self.editor_manager.editor_tabs.count():
                                    self.editor_manager.editor_tabs.setCurrentIndex(data['index'])
                                    data['editor'].setFocus()

                            # Save the file
                            if not self.editor_manager.save_file():
                                # Save was canceled or failed
                                event.ignore()
                                return

                elif reply == QMessageBox.Cancel:
                    event.ignore()  # Cancel exit
                    return
    

            # ✅ Count saved/opened .tex files
            saved_file_count = 0
            if hasattr(self, 'editor_manager'):
                for path in self.editor_manager.editor_files.keys():
                    # Count only real, saved files (not untitled)
                    if path and os.path.exists(path) and not path.startswith("untitled_"):
                        saved_file_count += 1

            # ✅ Save to config
            if hasattr(self, 'config_manager'):
                self.config_manager.set_config_value('ui', 'last_open_file_count', str(saved_file_count))

                # Also save window geometry
                self.config_manager.set_config_value('window', 'x', str(self.x()))
                self.config_manager.set_config_value('window', 'y', str(self.y()))
                self.config_manager.set_config_value('window', 'width', str(self.width()))
                self.config_manager.set_config_value('window', 'height', str(self.height()))
                self.config_manager.set_config_value('window', 'maximized', str(self.isMaximized()))

                # Save config
                self.config_manager.save_config()

            # Cleanup
            if hasattr(self, 'pdf_manager'):
                self.pdf_manager.cleanup()

            event.accept()

        except Exception as e:
            print(f"Error during close: {e}")
            import traceback
            traceback.print_exc()
            event.accept()

        try:
            # Step 1: Save bookmarks first (NEW)
            if hasattr(self, 'bookmarks_widget'):
                try:
                    #print("💾 Saving bookmarks...")
                    success = self.bookmarks_widget.save_bookmarks_to_config()
                    # if success:
                        # print("✅ Bookmarks saved successfully")
                    # else:
                        # pass
                        #print("⚠️ Bookmark saving failed")
                except Exception as e:
                    print(f"❌ Error saving bookmarks: {e}")
            
            # Step 2: Capture PDF files before any cleanup (EXISTING)
            self.pdf_manager.capture_pdf_files_before_cleanup()
            
            # Step 3: Handle editor files session saving (EXISTING)
            if hasattr(self, 'editor_manager') and hasattr(self, 'config_manager'):
                # Try to get file paths using the new method
                if hasattr(self.editor_manager, 'get_all_open_file_paths'):
                    full_paths = self.editor_manager.get_all_open_file_paths()
                else:
                    # Fallback method
                    filename_keys = list(self.editor_manager.editor_files.keys())
                    full_paths = []
                    if filename_keys:
                        base_dir = None
                        if hasattr(self.editor_manager, 'current_file') and self.editor_manager.current_file:
                            base_dir = os.path.dirname(self.editor_manager.current_file)
                        for filename in filename_keys:
                            if base_dir:
                                full_path = os.path.join(base_dir, filename)
                                if os.path.exists(full_path):
                                    full_paths.append(full_path)
                
                # Save session files
                if full_paths:
                    self.config_manager.save_session_files(full_paths)
                else:
                    pass
                    #print("Warning: No valid file paths found, preserving existing session")
            
            # Step 4: Handle captured PDF files (EXISTING)
            if hasattr(self, '_captured_pdf_files') and self._captured_pdf_files:
                for pdf_path, data in self._captured_pdf_files.items():
                    pdf_type = data.get('pdf_type', 'external')
                    exists = data.get('exists', os.path.exists(pdf_path))
                    
                    # Only add external PDFs to recent files
                    if pdf_type == 'external' and exists:
                        if hasattr(self, 'config_manager'):
                            self.config_manager.add_recent_pdf_file(pdf_path)
            
            # Step 5: Save configuration (EXISTING)
            if hasattr(self, 'config_manager'):
                if hasattr(self, 'editor_manager') and hasattr(self.editor_manager, 'editor_files'):
                    file_count = len(self.editor_manager.editor_files)
                    self.config_manager.config.set('ui', 'last_open_file_count', str(file_count))
                if hasattr(self, 'editor_manager') and hasattr(self.editor_manager, 'current_file') and self.editor_manager.current_file:
                    self.config_manager.config.set('ui', 'last_active_file', self.editor_manager.current_file)
                self.config_manager.save_config()
            
            # Step 6: Save editor session (EXISTING)
            if hasattr(self, 'editor_manager'):
                self.editor_manager.save_session_on_close()
            
            # Step 7: Save current settings (EXISTING)
            if hasattr(self, 'config_manager'):
                self.config_manager.save_current_settings()
            
            #print("Session saved successfully")
            
        except Exception as e:
            print(f"Error saving session on close: {e}")
            import traceback
            traceback.print_exc()
        
        # Call parent closeEvent
        super().closeEvent(event)


    def auto_open_last_file(self):
        """Open only the files that were open at last session"""                
        try:
            # if not hasattr(self, 'config_manager') or not hasattr(self, 'editor_manager'):
                # print("config_manager or editor_manager not available")
                # return
            
            #Check if auto-load is enabled
            auto_load = self.config_manager.get_config_value('ui', 'auto_load_last_file', 'True')
            if auto_load != 'True':
                return

            #Read session files
            session_files_str = self.config_manager.get_config_value('session', 'open_files', '')
            if not session_files_str:
                return

            session_files = session_files_str.split('||')
            opened_count = 0

            for file_path in session_files:
                file_path = file_path.strip()
                if not file_path:
                    continue
                if file_path.endswith(".tex") and os.path.exists(file_path):
                    try:
                        self.editor_manager.open_specific_file(file_path)
                        opened_count += 1
                    except Exception as e:
                        pass
                        #print(f"Failed to restore {file_path}: {e}")

            if opened_count > 0:
                lang = self.menu_language
                tr = self.translations[lang]
                message = tr["status_restored_files"].format(opened_count=opened_count)
                self.update_status_bar(message)                
                

        except Exception as e:            
            print(f"Error restoring session: {e}")

    def update_ui_fonts(self):
        """Update fonts for all UI elements"""
        if not hasattr(self, 'ui_font_family') or not hasattr(self, 'toolbar_font_size'):
            return

        ui_font = QFont(self.ui_font_family, self.toolbar_font_size)

        # Update menu bar via menu_manager
        if hasattr(self, 'menu_manager') and self.menu_manager:
            self.menu_manager.update_menu_font()

        # Update toolbar via toolbar_manager
        if hasattr(self, 'toolbar_manager') and self.toolbar_manager:
            self.toolbar_manager.update_toolbar_font(self.ui_font_family, self.toolbar_font_size)

        # ✅ Update side panel
        if hasattr(self, 'side_panel') and self.side_panel:
            self.side_panel.update_font()

        # ✅ Update output tabs (EnhancedTabWidget)
        if hasattr(self, 'layout_manager') and self.layout_manager:
            output_container = self.layout_manager.output_container
            if output_container and hasattr(output_container, 'update_font'):
                output_container.update_font()

        # ✅ Update bookmarks widget if it exists
        if hasattr(self, 'bookmarks_widget') and self.bookmarks_widget:
            if hasattr(self.bookmarks_widget, 'update_font'):
                self.bookmarks_widget.update_font()

        # Status bar
        if hasattr(self, 'status_bar') and self.status_bar:
            self.status_bar.setFont(ui_font)
            for child in self.status_bar.findChildren(QLabel):
                child.setFont(ui_font)

        # Tab bars
        if hasattr(self, 'editor_manager'):
            editor_tabs = getattr(self.editor_manager, 'editor_tabs', None)
            if editor_tabs and hasattr(editor_tabs, 'tabBar'):
                editor_tabs.tabBar().setFont(ui_font)

        if hasattr(self, 'pdf_manager'):
            pdf_tabs = getattr(self.pdf_manager, 'pdf_tabs', None)
            if pdf_tabs and hasattr(pdf_tabs, 'tabBar'):
                pdf_tabs.tabBar().setFont(ui_font)

        #print(f"UI fonts updated: {self.ui_font_family}, size {self.toolbar_font_size}")
            
            
            
    def apply_font_settings(self, settings):
        """Apply font settings from settings dialog"""
        #print(f"Received font settings: {settings}")
        
        # Update editor font settings
        self.editor_font_family = settings.get('editor_font_family', 'Consolas')
        self.editor_font_size = max(6, min(72, int(settings.get('editor_font_size', 11))))
        
        # Update UI font settings
        self.ui_font_family = settings.get('ui_font_family', 'Arial')
        self.toolbar_font_size = max(6, min(72, int(settings.get('toolbar_font_size', 10))))
        
        #print(f"Applying fonts: Editor={self.editor_font_family}/{self.editor_font_size}, UI={self.ui_font_family}/{self.toolbar_font_size}")
        
        # CRITICAL: Update editor fonts (this was commented out!)
        if hasattr(self, 'editor_manager') and self.editor_manager:
            self.editor_manager.update_editor_font(self.editor_font_family, self.editor_font_size)
        
        # Update UI fonts (menus, toolbars, status bar)
        self.update_ui_fonts()

    def get_current_font_settings(self):
        """Get current font settings for the settings dialog"""
        return {
            'editor_font_family': getattr(self, 'editor_font_family', 'Consolas'),
            'ui_font_family': getattr(self, 'ui_font_family', 'Arial'),
            'editor_font_size': getattr(self, 'editor_font_size', 11),
            'toolbar_font_size': getattr(self, 'toolbar_font_size', 10)
        }


    def load_side_panel_commands(self):
        """Load side panel commands from configuration"""
        if hasattr(self, 'side_panel') and hasattr(self, 'config_manager'):
            self.side_panel.load_from_config()
            self._register_side_panel_shortcuts()

    def save_side_panel_commands(self):
        """Save current side panel commands to configuration"""
        if hasattr(self, 'config_manager') and hasattr(self, 'side_panel'):
            self.config_manager.save_side_panel_commands(self.side_panel.get_commands())
            
    def toggle_side_panel_position(self):
        """Toggle side panel between left and right positions"""
        if self.side_panel_visible:
            self.side_panel_on_left = not getattr(self, 'side_panel_on_left', True)
            
            # Save to config
            if hasattr(self, 'config_manager'):
                self.config_manager.set_config_value('ui', 'side_panel_on_left', str(self.side_panel_on_left))
                self.config_manager.save_config()
            
            # Update side panel position property
            if hasattr(self, 'side_panel'):
                self.side_panel.set_position("left" if self.side_panel_on_left else "right")
            
            # Rebuild layout to reflect position change
            if hasattr(self, 'layout_manager'):
                self.layout_manager._arrange_containers()
            
            # Update status bar
            side_pos = "left" if self.side_panel_on_left else "right"
            lang = self.menu_language
            tr = self.translations[lang]
            message = tr["status_side_panel_moved"].format(side_pos=side_pos)
            self.update_status_bar(message)                                      
            
        else:
            QMessageBox.warning(self, "Warning", "Please display the side panel first.")

    # def switch(self):
        # """Switch method that toggles side panel position"""
        # self.toggle_side_panel_position()
     
        
    def reset_side_panel_to_default(self):
        """Reset side panel to default configuration"""
        if hasattr(self, 'side_panel'):
            self.side_panel.reset_to_default()
            lang = self.menu_language
            tr = self.translations[lang]
            message = tr["status_side_panel_reset"]
            self.update_status_bar(message)                                   
            
         
    def toggle_menu_language(self):
        """Toggle between Arabic and English menu language"""
        self.menu_language = "ar" if self.menu_language == "en" else "en"
        
        # Save to config
        if hasattr(self, 'config_manager'):
            self.config_manager.set_config_value('ui', 'language', self.menu_language)
        
        # Update UI
        self.update_ui_language()
        
        self.update_title()
        
        self.layout_manager.retranslate_output_tabs()
        
        # ── Refresh Search/Replace dialog if it exists ──
        if hasattr(self, 'search_replace_dialog') and self.search_replace_dialog is not None:
            self.search_replace_dialog.refresh_translations()    
        
        # ── Sync language to Knowledge Database if open ──
        if hasattr(self, '_knowledge_db_instances'):
            for kb in self._knowledge_db_instances:
                if kb is not None and hasattr(kb, 'refresh_language'):
                    try:
                        kb.refresh_language()
                    except Exception as e:
                        print(f"Warning: Failed to sync KB language: {e}")        


    def refresh_search_dialog_language(self):
        """Update the search/replace dialog UI to the current language."""
        if hasattr(self, 'search_replace_dialog') and self.search_replace_dialog is not None:
            self.search_replace_dialog.refresh_translations()
        
    def get_search_replace_dialog(self):
        if self.search_replace_dialog is None:
            self.search_replace_dialog = SearchReplaceDialog(self, self.editor_manager)
        return self.search_replace_dialog

    def show_find_dialog(self):
        lang = self.menu_language
        tr = self.translations[lang]                            
        
        current_editor = self.editor_manager.get_current_editor()
        current_file = self.editor_manager.get_current_file_path()
        
        if not current_editor or not current_file:
            self.editor_manager.show_error(tr["no_file_open"], tr["open_a_latex_file"])
            return

        dialog = self.get_search_replace_dialog()
        editor = self.editor_manager.get_current_editor()
        if editor and editor.textCursor().hasSelection():
            selected = editor.textCursor().selectedText()
            if '\n' not in selected:
                dialog.set_search_text(selected)
        dialog.show_for_search()

    def show_replace_dialog(self):
        dialog = self.get_search_replace_dialog()
        editor = self.editor_manager.get_current_editor()
        if editor and editor.textCursor().hasSelection():
            selected = editor.textCursor().selectedText()
            if '\n' not in selected:
                dialog.set_search_text(selected)
        dialog.show_for_replace()

    def find_next(self):
        dialog = self.get_search_replace_dialog()
        if dialog.search_line_edit.text():
            dialog.find_next()
        else:
            self.show_find_dialog()

    def find_previous(self):
        dialog = self.get_search_replace_dialog()
        if dialog.search_line_edit.text():
            dialog.find_previous()
        else:
            self.show_find_dialog()
            
              
           
    def save_current_settings_fixed(self):
        """Fixed save method that properly references main window"""
        try:
            # Ensure we have the config sections
            if not self.config_manager.config.has_section('ui'):
                self.config_manager.config.has_section('ui')
            
            # FIXED: Use self.main_window instead of just self
            self.config_manager.config.set('ui', 'is_rtl', str(self.is_rtl))
            self.config_manager.config.set('ui', 'menu_language', str(self.menu_language))
            
            # Save other UI settings
            if hasattr(self, 'editor_font_size'):
                self.config_manager.config.set('ui', 'editor_font_size', str(self.editor_font_size))
            if hasattr(self, 'toolbar_font_size'):
                self.config_manager.config.set('ui', 'toolbar_font_size', str(self.toolbar_font_size))
            
            # Save compiler settings
            if not self.config_manager.config.has_section('compiler'):
                self.config.has_section('compiler')
            self.config_manager.config.set('compiler', 'latex_engine', str(self.latex_engine))
            self.config_manager.config.set('compiler', 'backmatter_engine', str(self.backmatter_engine))
            
            # Write to file
            self.config_manager.save_config()
            #print("Settings saved successfully")
            
        except Exception as e:
            print(f"Error saving settings: {e}")
            import traceback
            traceback.print_exc()

        
    def toggle_text_direction(self):
        """Toggle text direction with proper button behavior"""
        
        lang = self.menu_language
        tr = self.translations[lang]                            
        
        current_editor = self.editor_manager.get_current_editor()
        current_file = self.editor_manager.get_current_file_path()
        
        if not current_editor or not current_file:
            self.editor_manager.show_error(tr["no_file_open"], tr["open_a_latex_file"])
            return

        #print(f"Toggle called: RTL was {self.is_rtl}")
        
        # Toggle state
        self.is_rtl = not self.is_rtl
        
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            # Apply to all editors
            alignment = Qt.AlignRight if self.is_rtl else Qt.AlignLeft
            if hasattr(self, 'editor_manager') and self.editor_manager:
                for filename, editor_data in self.editor_manager.editor_files.items():
                    editor = editor_data.get('editor')
                    if editor and hasattr(editor, 'setAlignment'):
                        editor.setAlignment(alignment)
            
            # Update button text to show what it will do NEXT
            if hasattr(self, 'text_dir_action'):
                if self.is_rtl:
                    self.text_dir_action.setText("Switch to LTR")
                    self.text_dir_action.setToolTip(tr["tooltip_currently_rtl"])
                else:
                    self.text_dir_action.setText("Switch to RTL") 
                    self.text_dir_action.setToolTip(tr["tooltip_currently_ltr"])
            
            # Update status bar
            lang = self.menu_language
            t = self.translations[lang]
            direction = t.get("status_text_rtl", "RTL") if self.is_rtl else t.get("status_text_ltr", "LTR")
            message = t["status_text_direction_set"].format(direction=direction)
            self.update_status_bar(message)                                   
            
            
            # Save setting
            if hasattr(self, 'config_manager'):
                self.config_manager.save_current_settings()
            
            #print(f"Toggle complete: RTL now {self.is_rtl}")
        finally:
            # Always restore cursor
            QApplication.restoreOverrideCursor()

            
    def toggle_output_tabs(self, force_state=None):
        """Toggle output tabs visibility with proper state management"""
        current_actual_state = True
        if hasattr(self.layout_manager, 'output_container') and self.layout_manager.output_container:
            current_actual_state = self.layout_manager.output_container.isVisible()
        
        if force_state is None:
            self.output_tabs_visible = not current_actual_state
        else:
            self.output_tabs_visible = bool(force_state)
                   
        # Update container visibility
        if hasattr(self.layout_manager, 'output_container') and self.layout_manager.output_container:            
            self.layout_manager.output_container.setVisible(self.output_tabs_visible)
        
        # Save to configuration
        if hasattr(self, 'config_manager'):
            self.config_manager.set_config_value(
                'layout',
                'output_tabs_visible',
                str(self.output_tabs_visible)
            )
        
        # Update menu action
        if hasattr(self, 'menu_manager'):
            self.menu_manager._update_output_toggle_action()
        
        # Emit signal for settings dialog or other listeners
        self.output_tabs_visibility_changed.emit(self.output_tabs_visible)
        
        # Force widget update
        self.update()
    
    def get_actual_output_state(self):
        """Get the actual current state of output visibility from the UI"""
        # Check multiple sources to get the real state
        ui_state = True  # default
        
        # Method 1: Check the actual widget visibility
        if (hasattr(self, 'layout_manager') and 
            hasattr(self.layout_manager, 'output_container') and 
            self.layout_manager.output_container):
            ui_state = self.layout_manager.output_container.isVisible()
            #print(f"  UI widget state: {ui_state}")
        
        # Method 2: Check the stored attribute
        attr_state = getattr(self, 'output_tab_visible', True)
        #print(f"  Stored attribute state: {attr_state}")
        
        # Use UI state as primary source of truth if available
        actual_state = ui_state
        #print(f"  Using actual state: {actual_state}")
        
        # Sync the attribute with reality
        self.output_tabs_visible = actual_state
        
        return actual_state
        
        
    def load_session_on_startup(self):
        """Load session files when the application starts - CONSOLIDATED VERSION"""
        if self._session_loaded:
            #print("Session already loaded, skipping")
            return

        try:
        
            # Apply to main editor
            if hasattr(self, 'editor_manager') and self.editor_manager:
                self.load_highlighting_colors()
            
            #If you have multiple editors or tabs, apply to all of them
            # Example for tab-based editors:
            for i in range(self.editor_manager.editor_tabs.count()):
                editor = self.editor_manager.editor_tabs.widget(i)
                if hasattr(editor, 'highlighter'):
                    editor.highlighter.load_colors_from_config()
                    editor.highlighter.highlighting_rules = []
                    editor.highlighter.setup_highlighting_rules()
                    editor.highlighter.rehighlight()    

            #self.test_color_application()
            if not hasattr(self, 'config_manager') or not hasattr(self, 'editor_manager'):
                #print("⚠️  Config or editor manager not available")
                return
            
            # Check if auto-load is enabled
            auto_load = str(self.config_manager.get_config_value('ui', 'auto_load_last_file', 'True')).lower() == 'true'
            if not auto_load:
                #print("❌ Auto-load disabled, skipping session restore")
                return
            
            # Get the last open file count
            last_count = self.config_manager.config.getint('ui', 'last_open_file_count', fallback=0)
            #print(f"🔄 Loading {last_count} session files on startup...")
            
            if last_count == 0:
                #print("ℹ️  No session files to load")
                return
            
            # Get session files
            session_files = self.config_manager.get_session_files(last_count)
            #print(f"📋 Session files to load: {session_files}")
            
            # Load each file (they will be opened in order)
            loaded_count = 0
            for file_path in session_files:
                try:
                    if os.path.exists(file_path) and os.path.isfile(file_path):
                        #print(f"📂 Loading: {os.path.basename(file_path)}")
                        self.editor_manager.open_specific_file(file_path)
                        loaded_count += 1
                    else:
                        pass
                        #print(f"⚠️  File no longer exists: {file_path}")
                except Exception as e:
                    pass
                    #print(f"❌ Error loading ... {file_path}: {e}")
            
            #print(f"✅ Loaded {loaded_count} files from session")
            
            from PyQt5.QtCore import QTimer
            bookmark_timer = QTimer()
            bookmark_timer.timeout.connect(self.load_bookmarks_on_startup)
            bookmark_timer.setSingleShot(True)
            bookmark_timer.start(1000)  # Load after 1 second to ensure all components are ready

            
            # Set the last active file as current (after all files are loaded)
            last_active = self.config_manager.config.get('ui', 'last_active_file', fallback='')
            if last_active and last_active in self.editor_manager.editor_files:
                # Use the robust switching method
                if self.editor_manager._switch_to_existing_file(last_active):
                    self.editor_manager.current_file = last_active
                    self.update_title()
                    #print(f"📌 Set active file to: {os.path.basename(last_active)}")
                else:
                    pass
                    #print(f"⚠️  Could not switch to last active file: {last_active}")
            elif last_active:
                pass
                #print(f"⚠️  Last active file not in loaded files: {last_active}")
                
            

            """Load tab visibility from saved session"""
            symbols_tab_visible = str(self.config_manager.get_config_value(
                'layout', 'symbols_tab_visible', 'True')).lower() == 'true'
            commands_tab_visible = str(self.config_manager.get_config_value(
                'layout', 'commands_tab_visible', 'True')).lower() == 'true'
            tree_tab_visible = str(self.config_manager.get_config_value(
                'layout', 'tree_tab_visible', 'True')).lower() == 'true'
            bookmarks_tab_visible = str(self.config_manager.get_config_value(
                'layout', 'bookmarks_tab_visible', 'True')).lower() == 'true'
            terminal_tab_visible = str(self.config_manager.get_config_value(
                'layout', 'terminal_tab_visible', 'True')).lower() == 'true'
            
            
            # Apply the loaded states
            self.toggle_symbols_tab(symbols_tab_visible)
            self.toggle_commands_tab(commands_tab_visible)
            self.toggle_tree_tab(tree_tab_visible)  # Fixed: was using commands_tab_visible
            self.toggle_bookmarks_tab(bookmarks_tab_visible)  # Fixed: was using commands_tab_visible
            self.toggle_terminal_tab(terminal_tab_visible)  # Fixed: was using commands_tab_visible
            
            from PyQt5.QtCore import QTimer
            startup_timer = QTimer()
            startup_timer.singleShot(1000, self.sync_all_editors_on_startup)  # 1 second delay
                
        except Exception as e:
            print(f"❌ Error loading session on startup: {e}")
            import traceback
            traceback.print_exc()

 
    def load_rtl_setting(self):
        """Load and apply RTL setting from config on startup"""
        try:
            if hasattr(self, 'config_manager') and self.config_manager:
                config = self.config_manager.config
                
                if config.has_section('ui') and config.has_option('ui', 'is_rtl'):
                    rtl_saved = config.getboolean('ui', 'is_rtl')
                    
                    # Apply the RTL setting
                    if hasattr(self, 'rtl_action') and hasattr(self.rtl_action, 'setChecked'):
                        self.rtl_action.setChecked(rtl_saved)
                    
                    # Apply RTL to the editor if it exists
                    if hasattr(self, 'editor_manager') and self.editor_manager:
                        self.editor_manager.set_rtl_mode(rtl_saved)
                        
                    return rtl_saved
                else:
                    return False
                    
        except Exception as e:
            return False

    def get_actual_output_state(self):
        """Get the actual current state of output visibility from the UI"""
        if (hasattr(self, 'layout_manager') and 
            hasattr(self.layout_manager, 'output_container') and 
            self.layout_manager.output_container):
            actual_state = self.layout_manager.output_container.isVisible()
        else:
            actual_state = getattr(self, 'output_tab_visible', True)
        
        # Keep attribute synced
        self.output_tab_visible = actual_state
        return actual_state

    def get_actual_symbols_state(self):
        """Get the actual current state of symbols tab visibility"""
        # Check toolbar manager state first (most reliable)
        if (hasattr(self, 'toolbar_manager') and 
            hasattr(self.toolbar_manager, 'symbols_tab_visible')):
            actual_state = self.toolbar_manager.symbols_tab_visible
        elif (hasattr(self, 'layout_manager') and 
              hasattr(self.layout_manager, 'symbols_tab') and 
              self.layout_manager.symbols_tab):
            actual_state = self.layout_manager.symbols_tab.isVisible()
        else:
            actual_state = getattr(self, 'symbols_tab_visible', False)
        
        # Keep all states synchronized
        self.symbols_tab_visible = actual_state
        if hasattr(self, 'toolbar_manager'):
            self.toolbar_manager.symbols_tab_visible = actual_state
        return actual_state

    def get_actual_commands_state(self):
        """Get the actual current state of commands tab visibility"""
        # Check toolbar manager state first (most reliable)
        if (hasattr(self, 'toolbar_manager') and 
            hasattr(self.toolbar_manager, 'commands_tab_visible')):
            actual_state = self.toolbar_manager.commands_tab_visible
        elif (hasattr(self, 'layout_manager') and 
              hasattr(self.layout_manager, 'commands_tab') and 
              self.layout_manager.commands_tab):
            actual_state = self.layout_manager.commands_tab.isVisible()
        else:
            actual_state = getattr(self, 'commands_tab_visible', False)
        
        # Keep all states synchronized
        self.commands_tab_visible = actual_state
        if hasattr(self, 'toolbar_manager'):
            self.toolbar_manager.commands_tab_visible = actual_state
        return actual_state

    def get_actual_tree_state(self):
        """Get the actual current state of tree tab visibility"""
        # Check toolbar manager state first (most reliable)
        if (hasattr(self, 'toolbar_manager') and 
            hasattr(self.toolbar_manager, 'tree_tab_visible')):
            actual_state = self.toolbar_manager.tree_tab_visible
        elif (hasattr(self, 'layout_manager') and 
              hasattr(self.layout_manager, 'tree_tab') and 
              self.layout_manager.tree_tab):
            actual_state = self.layout_manager.tree_tab.isVisible()
        else:
            actual_state = getattr(self, 'tree_tab_visible', False)
        
        # Keep all states synchronized
        self.tree_tab_visible = actual_state
        if hasattr(self, 'toolbar_manager'):
            self.toolbar_manager.tree_tab_visible = actual_state
        return actual_state

    def get_actual_terminal_state(self):
        """Get the actual current state of tree tab visibility"""
        # Check toolbar manager state first (most reliable)
        if (hasattr(self, 'toolbar_manager') and 
            hasattr(self.toolbar_manager, 'terminal_tab_visible')):
            actual_state = self.toolbar_manager.terminal_tab_visible
        elif (hasattr(self, 'layout_manager') and 
              hasattr(self.layout_manager, 'terminal_tab') and 
              self.layout_manager.terminal_tab):
            actual_state = self.layout_manager.terminal_tab.isVisible()
        else:
            actual_state = getattr(self, 'terminal_tab_visible', False)
        
        # Keep all states synchronized
        self.terminal_tab_visible = actual_state
        if hasattr(self, 'toolbar_manager'):
            self.toolbar_manager.terminal_tab_visible = actual_state
        return actual_state


    def get_actual_bookmarks_state(self):
        """Get the actual current state of bookmarks tab visibility"""
        actual_state = False
        
        # Method 1: Check if tab exists in the output container tab widget
        if (hasattr(self, 'layout_manager') and 
            hasattr(self.layout_manager, 'output_container') and 
            self.layout_manager.output_container):
            
            # Look for QTabWidget inside output container
            tab_widget = None
            for child in self.layout_manager.output_container.findChildren(QTabWidget):
                if child:
                    tab_widget = child
                    break
            
            if tab_widget:
                # Check if any tab has "Bookmarks" in its title
                for i in range(tab_widget.count()):
                    if "Bookmarks" in tab_widget.tabText(i) or "إشارات" in tab_widget.tabText(i):
                        actual_state = True
                        break
        
        # Method 2: Check toolbar manager state as fallback
        if not actual_state and (hasattr(self, 'toolbar_manager') and 
            hasattr(self.toolbar_manager, 'bookmarks_tab_visible')):
            actual_state = self.toolbar_manager.bookmarks_tab_visible
        
        # Method 3: Check stored attribute as last resort
                                                 
        if not actual_state:
             
            actual_state = getattr(self, 'bookmarks_tab_visible', False)
        
        # Keep all states synchronized
        self.bookmarks_tab_visible = actual_state
        if hasattr(self, 'toolbar_manager'):
            self.toolbar_manager.bookmarks_tab_visible = actual_state
        
        return actual_state
        
    def sync_all_tab_states(self):
        """Synchronize all tab states between MainWindow, ToolbarManager, and actual UI"""
        #print("=== SYNCING ALL TAB STATES ===")
        
        # First, get the actual UI states (what's really visible)
        actual_output = self.get_actual_output_state()
        actual_symbols = self.get_actual_symbols_state()
        actual_commands = self.get_actual_commands_state()
        actual_tree = self.get_actual_tree_state()
        actual_bookmarks = self.get_actual_bookmarks_state()
        actual_terminal = self.get_actual_terminal_state()
        
        #print(f"Actual UI states - Output: {actual_output}, Symbols: {actual_symbols}, Commands: {actual_commands}, Tree: {actual_tree}, Bookmarks: {actual_bookmarks}, Terminal: {actual_terminal}")
        
        # Update MainWindow attributes to match reality
        self.output_tab_visible = actual_output
        self.symbols_tab_visible = actual_symbols
        self.commands_tab_visible = actual_commands
        self.tree_tab_visible = actual_tree
        self.bookmarks_tab_visible = actual_bookmarks
        self.terminal_tab_visible = actual_terminal
        
        # Sync ToolbarManager states
        if hasattr(self, 'toolbar_manager'):
            self.toolbar_manager.symbols_tab_visible = actual_symbols
            self.toolbar_manager.commands_tab_visible = actual_commands
            self.toolbar_manager.tree_tab_visible = actual_tree
            self.toolbar_manager.bookmarks_tab_visible = actual_bookmarks
            self.toolbar_manager.terminal_tab_visible = actual_terminal
            
            # Update toolbar button states
            if hasattr(self.toolbar_manager, 'symbols_action'):
                self.toolbar_manager.symbols_action.setChecked(actual_symbols)
            if hasattr(self.toolbar_manager, 'commands_action'):
                self.toolbar_manager.commands_action.setChecked(actual_commands)
            if hasattr(self.toolbar_manager, 'tree_action'):
                self.toolbar_manager.tree_action.setChecked(actual_tree)
            if hasattr(self.toolbar_manager, 'bookmarks_action'):
                self.toolbar_manager.bookmarks_action.setChecked(actual_bookmarks)
            if hasattr(self.toolbar_manager, 'terminal_action'):
                self.toolbar_manager.terminal_action.setChecked(actual_terminal)
        #print("Tab states synchronized")


    def toggle_symbols_tab(self, force_state=None):
        """Toggle symbols tab visibility"""
        if force_state is not None:
            self.symbols_tab_visible = force_state
        else:
            self.symbols_tab_visible = not self.symbols_tab_visible
        
        # Update toolbar manager state and button
        if hasattr(self, 'toolbar_manager'):
            self.toolbar_manager.symbols_tab_visible = self.symbols_tab_visible
            # Check if symbols_action exists before using it
            if hasattr(self.toolbar_manager, 'symbols_action') and self.toolbar_manager.symbols_action:
                self.toolbar_manager.symbols_action.setChecked(self.symbols_tab_visible)
            

            # Actually perform the tab add/remove operation
            output_container = self.layout_manager.output_container if hasattr(self, 'layout_manager') else None
            if output_container:
                if self.symbols_tab_visible:
                    # Ensure output container is visible first
                    if not output_container.isVisible():
                        output_container.setVisible(True)
                        self.output_tab_visible = True
                    # Check if the method exists before calling
                    if hasattr(self.toolbar_manager, '_add_symbols_tab'):
                        self.toolbar_manager._add_symbols_tab(output_container)
                    if hasattr(self.toolbar_manager, '_focus_tab'):
                        self.toolbar_manager._focus_tab(output_container, "Symbols")
                else:
                    # Check if the method exists before calling
                    if hasattr(self.toolbar_manager, '_remove_symbols_tab'):
                        self.toolbar_manager._remove_symbols_tab(output_container)
        
        self.update_output_tabs()

    def toggle_commands_tab(self, force_state=None):
        """Toggle commands tab visibility"""
        if force_state is not None:
            self.commands_tab_visible = force_state
        else:
            self.commands_tab_visible = not self.commands_tab_visible
        
        # Update toolbar manager state and button
        if hasattr(self, 'toolbar_manager'):
            self.toolbar_manager.commands_tab_visible = self.commands_tab_visible
            # Check if commands_action exists before using it
            if hasattr(self.toolbar_manager, 'commands_action') and self.toolbar_manager.commands_action:
                self.toolbar_manager.commands_action.setChecked(self.commands_tab_visible)
            
            # Actually perform the tab add/remove operation
            output_container = self.layout_manager.output_container if hasattr(self, 'layout_manager') else None
            if output_container:
                if self.commands_tab_visible:
                    # Ensure output container is visible first
                    if not output_container.isVisible():
                        output_container.setVisible(True)
                        self.output_tab_visible = True
                    # Check if the method exists before calling
                    if hasattr(self.toolbar_manager, '_add_commands_tab'):
                        self.toolbar_manager._add_commands_tab(output_container)
                    if hasattr(self.toolbar_manager, '_focus_tab'):
                        self.toolbar_manager._focus_tab(output_container, "Commands")
                else:
                    # Check if the method exists before calling
                    if hasattr(self.toolbar_manager, '_remove_commands_tab'):
                        self.toolbar_manager._remove_commands_tab(output_container)
        
        self.update_output_tabs()

    def toggle_tree_tab(self, force_state=None):
        """Toggle tree tab visibility"""
        if force_state is not None:
            self.tree_tab_visible = force_state
        else:
            self.tree_tab_visible = not self.tree_tab_visible
        
        # Update toolbar manager state and button
        if hasattr(self, 'toolbar_manager'):
            self.toolbar_manager.tree_tab_visible = self.tree_tab_visible
            # Check if tree_action exists before using it
            if hasattr(self.toolbar_manager, 'tree_action') and self.toolbar_manager.tree_action:
                self.toolbar_manager.tree_action.setChecked(self.tree_tab_visible)
            
            # Actually perform the tab add/remove operation
            output_container = self.layout_manager.output_container if hasattr(self, 'layout_manager') else None
            if output_container:
                if self.tree_tab_visible:
                    # Ensure output container is visible first
                    if not output_container.isVisible():
                        output_container.setVisible(True)
                        self.output_tab_visible = True
                    # Check if the method exists before calling
                    if hasattr(self.toolbar_manager, '_add_tree_tab'):
                        self.toolbar_manager._add_tree_tab(output_container)
                    if hasattr(self.toolbar_manager, '_focus_tab'):
                        self.toolbar_manager._focus_tab(output_container, "Tree")
                else:
                    # Check if the method exists before calling
                    if hasattr(self.toolbar_manager, '_remove_tree_tab'):
                        self.toolbar_manager._remove_tree_tab(output_container)
        
        self.update_output_tabs()

    def toggle_terminal_tab(self, force_state=None):
        """Toggle tree tab visibility"""
        if force_state is not None:
            self.terminal_tab_visible = force_state
        else:
            self.terminal_tab_visible = not self.terminal_tab_visible
        
        
        # Update toolbar manager state and button
        if hasattr(self, 'toolbar_manager'):
            self.toolbar_manager.terminal_tab_visible = self.terminal_tab_visible
            # Check if terminal_action exists before using it
            if hasattr(self.toolbar_manager, 'terminal_action') and self.toolbar_manager.terminal_action:
                self.toolbar_manager.terminal_action.setChecked(self.terminal_tab_visible)
            
            # Actually perform the tab add/remove operation
            output_container = self.layout_manager.output_container if hasattr(self, 'layout_manager') else None
            if output_container:
                if self.terminal_tab_visible:
                    # Ensure output container is visible first
                    if not output_container.isVisible():
                        output_container.setVisible(True)
                        self.output_tab_visible = True
                    # Check if the method exists before calling
                    if hasattr(self.toolbar_manager, '_add_terminal_tab'):
                        self.toolbar_manager._add_tree_tab(output_container)
                    if hasattr(self.toolbar_manager, '_focus_tab'):
                        self.toolbar_manager._focus_tab(output_container, "Terminal")
                else:
                    # Check if the method exists before calling
                    if hasattr(self.toolbar_manager, '_remove_terminal_tab'):
                        self.toolbar_manager._remove_terminal_tab(output_container)
        
        self.update_output_tabs()


    def toggle_bookmarks_tab(self, force_state=None):
        """Toggle bookmarks tab visibility"""
        if force_state is not None:
            self.bookmarks_tab_visible = force_state
        else:
            self.bookmarks_tab_visible = not self.bookmarks_tab_visible
        
        # Update toolbar manager state and button
        if hasattr(self, 'toolbar_manager'):
            self.toolbar_manager.bookmarks_tab_visible = self.bookmarks_tab_visible
            # Check if bookmarks_action exists before using it
            if hasattr(self.toolbar_manager, 'bookmarks_action') and self.toolbar_manager.bookmarks_action:
                self.toolbar_manager.bookmarks_action.setChecked(self.bookmarks_tab_visible)
            
            # Actually perform the tab add/remove operation
            output_container = self.layout_manager.output_container if hasattr(self, 'layout_manager') else None
            if output_container:
                if self.bookmarks_tab_visible:
                    # Ensure output container is visible first
                    if not output_container.isVisible():
                        output_container.setVisible(True)
                        self.output_tab_visible = True
                    # Check if the method exists before calling
                    if hasattr(self.toolbar_manager, '_add_bookmarks_tab'):
                        self.toolbar_manager._add_bookmarks_tab(output_container)
                    if hasattr(self.toolbar_manager, '_focus_tab'):
                        self.toolbar_manager._focus_tab(output_container, "Bookmarks")
                else:
                    # Check if the method exists before calling
                    if hasattr(self.toolbar_manager, '_remove_bookmarks_tab'):
                        self.toolbar_manager._remove_bookmarks_tab(output_container)
        
        self.update_output_tabs()


    def load_bookmarks_on_startup(self):
        """Load bookmarks during application startup"""
        try:
            if hasattr(self, 'bookmarks_widget'):
                # Ensure config section exists
                if hasattr(self, 'config_manager'):
                    if not self.config_manager.config.has_section('bookmarks'):
                        self.config_manager.config.add_section('bookmarks')
                        self.config_manager.save_config()
                
                # Load bookmarks
                self.bookmarks_widget.load_bookmarks_from_config()
                
                # Refresh current editor's bookmark display
                if hasattr(self, 'editor_manager'):
                    current_editor = self.editor_manager.get_current_editor()
                    if current_editor and hasattr(current_editor, 'sync_bookmarks_with_widget'):
                        current_editor.sync_bookmarks_with_widget(self.bookmarks_widget)
                
        except Exception as e:
            print(f"Error loading bookmarks on startup: {e}")

    def update_output_tabs(self):
        """Update the visibility of output tabs"""
        if hasattr(self, 'layout_manager') and self.layout_manager.output_container:
            # This will be handled by toolbar_manager toggle methods
            self.layout_manager.retranslate_output_tabs()
            
                
    def toggle_editor_expand_width(self):
        """Toggle Editor expand to full width by hiding/showing PDF viewer and side panel"""
        try:
            if not hasattr(self, 'layout_manager'):
                return
            
            is_editor_expanded = getattr(self, '_editor_expanded', False)
            is_pdf_expanded = getattr(self, '_pdf_expanded', False)
            
            if is_editor_expanded:
                # Editor is currently expanded - restore normal view
                self._restore_normal_view()
                self._editor_expanded = False
                #print("✅ Editor restored to normal size")
            else:
                # Editor is not expanded
                if is_pdf_expanded:
                    # PDF is currently expanded - restore first, then expand editor
                    self._restore_normal_view()
                    self._pdf_expanded = False
                
                # Now expand editor
                self._expand_editor_view()
                self._editor_expanded = True
                #print("✅ Editor expanded to full width")
            
            self.layout_manager.main_splitter.update()
            QApplication.processEvents()
            
        except Exception as e:
            print(f"❌ Error in toggle_editor_expand_width: {e}")
            import traceback
            traceback.print_exc()


    def toggle_pdf_expand_width(self):
        """Toggle PDF viewer expand to full width by hiding/showing Editor and side panel"""
        try:
            if not hasattr(self, 'layout_manager'):
                return
            
            is_editor_expanded = getattr(self, '_editor_expanded', False)
            is_pdf_expanded = getattr(self, '_pdf_expanded', False)
            
            if is_pdf_expanded:
                # PDF is currently expanded - restore normal view
                self._restore_normal_view()
                self._pdf_expanded = False
                #print("✅ PDF viewer restored to normal size")
            else:
                # PDF is not expanded
                if is_editor_expanded:
                    # Editor is currently expanded - restore first, then expand PDF
                    self._restore_normal_view()
                    self._editor_expanded = False
                
                # Now expand PDF
                self._expand_pdf_view()
                self._pdf_expanded = True
                #print("✅ PDF viewer expanded to full width")
            
            self.layout_manager.main_splitter.update()
            QApplication.processEvents()
            
        except Exception as e:
            print(f"❌ Error in toggle_pdf_expand_width: {e}")
            import traceback
            traceback.print_exc()

    def _restore_normal_view(self):
        """Helper to restore normal view with all panels visible"""
        try:
            # Show editor container
            if hasattr(self.layout_manager, 'editor_container') and self.layout_manager.editor_container:
                self.layout_manager.editor_container.show()
            
            # Show PDF container
            if hasattr(self.layout_manager, 'pdf_container') and self.layout_manager.pdf_container:
                self.layout_manager.pdf_container.show()
            
            # Restore side panel if it was visible before any expansion
            should_show = getattr(self, '_side_panel_was_visible_before_expand', True)
            if hasattr(self, 'side_panel') and self.side_panel:
                if should_show:
                    self.side_panel.show()
                    self.side_panel.setFixedWidth(80)
                    self.side_panel_visible = True
                else:
                    self.side_panel.hide()
                    self.side_panel_visible = False
            
            # Restore saved sizes or use default arrangement
            if hasattr(self, '_expand_saved_sizes'):
                self.layout_manager.main_splitter.setSizes(self._expand_saved_sizes)
                delattr(self, '_expand_saved_sizes')
            else:
                self.layout_manager._arrange_containers()
                
        except Exception as e:
            print(f"❌ Error in _restore_normal_view: {e}")

    def is_pdf_comparator_open(self):
        if hasattr(self, 'pdf_manager') and hasattr(self.pdf_manager, 'pdf_tabs'):
            tab_widget = self.pdf_manager.pdf_tabs
            for i in range(tab_widget.count()):
                if tab_widget.tabText(i) == "PDF Comparison":
                    return True
        return False

    def set_side_panel_visible(self, visible: bool):
        lang = self.menu_language
        tr = self.translations[lang]                            

        if visible and self.is_pdf_comparator_open():
            self.side_panel.setVisible(False)
            self.menu_manager.toggle_visibility_action.setChecked(False)
            #visible = not visible
            
        current_editor = self.editor_manager.get_current_editor()
        current_file = self.editor_manager.get_current_file_path()
        
        if visible and (not current_editor or not current_file):
            self.editor_manager.show_error(tr["no_file_open"], tr["open_a_latex_file"])
            return

        is_pdf_expanded = getattr(self, '_pdf_expanded', False)
        if is_pdf_expanded:
            QMessageBox.warning(self, "Warning", "Bring the LaTeX editor to the foreground")
            return
        
        self.side_panel_visible = visible

        if hasattr(self, 'side_panel') and self.side_panel:
            self.side_panel.setVisible(visible)

        action = getattr(self.menu_manager, "toggle_visibility_action", None)
        if action and action.isChecked() != visible:
            action.blockSignals(True)
            action.setChecked(visible)
            action.blockSignals(False)

    def _expand_editor_view(self):
        """Helper to expand editor to full width"""
        try:
            # Save current splitter sizes (only if not already saved)
            if not hasattr(self, '_expand_saved_sizes'):
                self._expand_saved_sizes = self.layout_manager.main_splitter.sizes()
            
            # Save side panel state before first expansion
            if not hasattr(self, '_side_panel_was_visible_before_expand'):
                self._side_panel_was_visible_before_expand = getattr(self, 'side_panel_visible', True)
            
            # Hide side panel
            if hasattr(self, 'side_panel') and self.side_panel:
                #self.side_panel.hide()
                #self.side_panel_visible = False               
                self.set_side_panel_visible(False)
            
            # Hide PDF container
            if hasattr(self.layout_manager, 'pdf_container') and self.layout_manager.pdf_container:
                self.layout_manager.pdf_container.hide()
            
            # Make sure editor container is visible
            if hasattr(self.layout_manager, 'editor_container') and self.layout_manager.editor_container:
                self.layout_manager.editor_container.show()
            
            # Give all space to editor
            splitter = self.layout_manager.main_splitter
            total_size = sum(splitter.sizes())
            if total_size == 0:
                total_size = splitter.width()
            
            new_sizes = []
            for i in range(splitter.count()):
                widget = splitter.widget(i)
                if widget and hasattr(widget, 'objectName') and widget.objectName() == 'editor_container':
                    new_sizes.append(total_size)
                else:
                    new_sizes.append(0)
            
            if new_sizes:
                splitter.setSizes(new_sizes)
                
        except Exception as e:
            print(f"❌ Error in _expand_editor_view: {e}")

    def _expand_pdf_view(self):
        """Helper to expand PDF to full width"""
        try:
            # Save current splitter sizes (only if not already saved)
            if not hasattr(self, '_expand_saved_sizes'):
                self._expand_saved_sizes = self.layout_manager.main_splitter.sizes()
            
            # Save side panel state before first expansion
            if not hasattr(self, '_side_panel_was_visible_before_expand'):
                self._side_panel_was_visible_before_expand = getattr(self, 'side_panel_visible', True)
            
            # Hide side panel
            if hasattr(self, 'side_panel') and self.side_panel:
                #self.side_panel.hide()
                #self.side_panel_visible = False
                self.set_side_panel_visible(False)
            
            # Hide Editor container
            if hasattr(self.layout_manager, 'editor_container') and self.layout_manager.editor_container:
                self.layout_manager.editor_container.hide()
            
            # Make sure PDF container is visible
            if hasattr(self.layout_manager, 'pdf_container') and self.layout_manager.pdf_container:
                self.layout_manager.pdf_container.show()
            
            # Give all space to PDF
            splitter = self.layout_manager.main_splitter
            total_size = sum(splitter.sizes())
            if total_size == 0:
                total_size = splitter.width()
            
            new_sizes = []
            for i in range(splitter.count()):
                widget = splitter.widget(i)
                if widget and hasattr(widget, 'objectName') and widget.objectName() == 'pdf_container':
                    new_sizes.append(total_size)
                else:
                    new_sizes.append(0)
            
            if new_sizes:
                splitter.setSizes(new_sizes)
                
        except Exception as e:
            print(f"❌ Error in _expand_pdf_view: {e}")


    def split_window_width(self):
        """Split window - restore all panels to balanced sizes"""
        try:
            if not hasattr(self, 'layout_manager') or not hasattr(self.layout_manager, 'main_splitter'):
                return
            
            # Reset expanded states
            self._editor_expanded = False
            self._pdf_expanded = False
            
            # Restore normal view
            self._restore_normal_view()
            
            # Clear the saved side panel state
            if hasattr(self, '_side_panel_was_visible_before_expand'):
                self.set_side_panel_visible(self._side_panel_was_visible_before_expand)
                delattr(self, '_side_panel_was_visible_before_expand')
            
            self.side_panel.setVisible(True)

            self.menu_manager.toggle_visibility_action.setChecked(False)

                    
            
            #print("✅ Window split into balanced panels")
            
        except Exception as e:
            print(f"❌ Error in split_window_width: {e}")
            import traceback
            traceback.print_exc()
        
    def open_latex_comparator(self):
        """Open LaTeX file comparison tool inside the editor container."""
        from latex_comparator import LaTeXComparatorWidget
        lang = self.menu_language
        tr = self.translations[lang]                    
        
        # Ensure editor container exists
        if not hasattr(self.layout_manager, 'editor_container'):
            self._create_editor_container()
        
        tab_widget = self.editor_manager.editor_tabs
        
        # Check if comparator tab already exists - don't open duplicate        
        possible_labels = {
            tr["comparator"] for tr in translations.values()
        }                        
        
        for i in range(tab_widget.count()):
            if tab_widget.tabText(i) in possible_labels:
                # Already exists - just switch to it
                tab_widget.setCurrentIndex(i)
                #print("✅ LaTeX Comparator already open - switching to existing tab")
                return
        
        # Create the comparator widget
        comparator = LaTeXComparatorWidget(self)
        
        # Add it as a new tab in the existing editor container
        tab_name = tr.get("comparator")
        tab_index = tab_widget.addTab(comparator, tab_name)
        tab_widget.tabBar().setTabData(tab_index, "comparator")           
        
        # ✅ Set SVG icon properly
        icon = QIcon("icons/compare_tex.svg")
        tab_widget.setTabIcon(tab_index, icon)        
        
        tab_widget.setCurrentIndex(tab_index)
        
        # Make sure tabs are closable
        tab_widget.setTabsClosable(True)
        
        # Use a more robust close connection
        # Disconnect any existing connection first to avoid duplicates
        try:
            tab_widget.tabCloseRequested.disconnect(self._close_tab)
        except (TypeError, RuntimeError):
            pass  # Not connected yet
        
        # Connect with fresh handler
        tab_widget.tabCloseRequested.connect(self._close_tab)
    

    def _close_tab(self, index):
        """Remove tab and clean up widget - FIXED to show welcome if needed."""
        tab_widget = self.editor_manager.editor_tabs
        widget = tab_widget.widget(index)
        
        # Get tab name before removing
        tab_name = tab_widget.tabText(index) if index < tab_widget.count() else ""
        
        if widget is not None:
            widget.deleteLater()
        tab_widget.removeTab(index)
        
        # Restore editor width if it was expanded for comparator
        if getattr(self, '_editor_expanded', False):
            self.toggle_editor_expand_width()
        
        # Check if we need to show welcome tab
        # Count real editor files (not tool tabs)
        real_files_count = len(self.editor_manager.editor_files)
        
        # Also check remaining tabs for any real content
        remaining_real_tabs = 0
        tool_tab_names = ["⚡ File Comparison",  "Latex Comparator", "Comparator", "Welcome", "LaTeX Editor"]
        for i in range(tab_widget.count()):
            if tab_widget.tabText(i) not in tool_tab_names:
                remaining_real_tabs += 1
        
        # Show welcome if no real files/tabs remain
        if real_files_count == 0 and remaining_real_tabs == 0:
            if hasattr(self, 'layout_manager'):
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(50, self.layout_manager._recreate_editor_container)
            #print("✅ Restored editor welcome tab after closing comparator")

        
    def open_tools_tab(self):
        """Open tools tab in PDF viewer"""
        try:
            if hasattr(self, 'pdf_manager'):
                self.pdf_manager._remove_welcome_tab_if_exists()

            from tools_tab import add_tools_tab_to_pdf_viewer
            add_tools_tab_to_pdf_viewer(self)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open tools tab:\n{str(e)}")
            import traceback
            traceback.print_exc

    def open_djvu_tab(self):
        """Open DjVu viewer tab in PDF viewer"""
        try:
            if hasattr(self, 'pdf_manager'):
                self.pdf_manager._remove_welcome_tab_if_exists()
            from djvu_tab import add_djvu_tab_to_pdf_viewer
            add_djvu_tab_to_pdf_viewer(self)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open DjVu viewer tab:\n{str(e)}")

    def open_knowledge_database(self):
        """Open knowledge database manager"""
        try:
            if hasattr(self, 'pdf_manager'):
                self.pdf_manager._remove_welcome_tab_if_exists()

            from knowledge_database_integration import add_knowledge_database_to_pdf_viewer
            add_knowledge_database_to_pdf_viewer(self)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open knowledge database:\n{str(e)}")

    def open_insert_character_tab(self):
        """Open Insert Character tab in PDF viewer"""
        try:
            if hasattr(self, 'pdf_manager'):
                self.pdf_manager._remove_welcome_tab_if_exists()
            from insert_character import add_insert_character_tab_to_pdf_viewer
            add_insert_character_tab_to_pdf_viewer(self)
        except Exception as e:
            QMessageBox.critical(self, "Error",
                f"Failed to open Insert Character tab:\n{str(e)}")
            import traceback
            traceback.print_exc()
            
    def open_spreadsheet_tab(self):
        """Open spreadsheet tab in PDF viewer"""
        try:
            if hasattr(self, 'pdf_manager'):
                self.pdf_manager._remove_welcome_tab_if_exists()

            from spreadsheet_tab import add_spreadsheet_tab_to_pdf_viewer
            add_spreadsheet_tab_to_pdf_viewer(self)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open spreadsheet tab:\n{str(e)}")
            import traceback
            traceback.print_exc()
        
    def open_todo_list_tab(self):
        """Open todo list tab in PDF viewer"""
        try:
            if hasattr(self, 'pdf_manager'):
                self.pdf_manager._remove_welcome_tab_if_exists()
            from todo_list import add_todo_tab_to_pdf_viewer
            add_todo_tab_to_pdf_viewer(self)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open todo list tab:\n{str(e)}")
            import traceback
            traceback.print_exc()
            
    def open_bibtex_manager_tab(self):
        """Open BibTeX Manager tab in PDF viewer"""
        try:
            if hasattr(self, 'pdf_manager'):
                self.pdf_manager._remove_welcome_tab_if_exists()
            from bibtex_manager import add_bibtex_manager_tab_to_pdf_viewer
            add_bibtex_manager_tab_to_pdf_viewer(self)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open BibTeX Manager tab:\n{str(e)}")
        
    def open_latex_wizard_tab(self):
        """Open LaTeX Document Wizard tab in PDF viewer"""
        try:
            if hasattr(self, 'pdf_manager'):
                self.pdf_manager._remove_welcome_tab_if_exists()

            from latex_document_wizard import add_latex_wizard_tab_to_pdf_viewer
            add_latex_wizard_tab_to_pdf_viewer(self)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open LaTeX wizard:\n{str(e)}")

    def open_ai_tab(self):
        """Open AI Assistant tab in PDF viewer"""
        try:
            if hasattr(self, 'pdf_manager'):
                self.pdf_manager._remove_welcome_tab_if_exists()
            
            from ai_tab import add_ai_tab_to_pdf_viewer
            add_ai_tab_to_pdf_viewer(self)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open AI Assistant:\n{str(e)}")
        

            
    def tikz_plotter_tab(self):
        """Open TikZ Plotter tab in PDF viewer"""
        try:
            if hasattr(self, 'pdf_manager'):
                self.pdf_manager._remove_welcome_tab_if_exists()
            
            from tikz_plotter_tab import add_tikz_plotter_tab_to_pdf_viewer
            add_tikz_plotter_tab_to_pdf_viewer(self)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open TikZ Plotter tab:\n{str(e)}")

    def load_bookmarks_from_config(self):
        """Load bookmarks from config after UI initialization"""
        try:
            if not hasattr(self, 'bookmarks_widget'):
                #print("Bookmarks widget not initialized yet")
                return False
                
            # Load bookmarks into the widget
            self.bookmarks_widget.load_bookmarks_from_config()
            
            # Sync all existing editors with loaded bookmarks
            def sync_all_editors():
                if not hasattr(self, 'editor_manager'):
                    return
                    
                synced_count = 0
                if hasattr(self.editor_manager, 'editor_files'):
                    for file_path, editor_data in self.editor_manager.editor_files.items():
                        editor = None
                        if isinstance(editor_data, dict) and 'editor' in editor_data:
                            editor = editor_data['editor']
                        elif hasattr(editor_data, 'editor'):
                            editor = editor_data.editor
                        
                        if editor and hasattr(editor, 'sync_bookmarks_with_widget'):
                            editor.file_path = file_path
                            editor.sync_bookmarks_with_widget(self.bookmarks_widget)
                            synced_count += 1
                
                #print(f"Synced bookmarks with {synced_count} editors")
            
            # Delay sync to ensure all editors are loaded
            QTimer.singleShot(1000, sync_all_editors)
            return True
            
        except Exception as e:
            return False        
        
    def sync_all_editors_on_startup(self):
        """Sync all existing editors with loaded bookmarks"""
        if not hasattr(self, 'editor_manager'):
            return
        
        editor_manager = self.editor_manager
        bookmarks_widget = self.bookmarks_widget
        synced_count = 0
        
        # Sync through editor_files (your main structure)
        if hasattr(editor_manager, 'editor_files'):
            for file_path, editor_data in editor_manager.editor_files.items():
                editor = None
                if isinstance(editor_data, dict) and 'editor' in editor_data:
                    editor = editor_data['editor']
                elif hasattr(editor_data, 'editor'):
                    editor = editor_data.editor
                
                if editor and hasattr(editor, 'sync_bookmarks_with_widget'):
                    # Set the file_path attribute so sync works correctly
                    editor.file_path = file_path
                    editor.sync_bookmarks_with_widget(bookmarks_widget)
                    synced_count += 1
                    #print(f"Synced bookmarks for editor: {os.path.basename(file_path)}")
                   
    # ✅ NEW: Add these helper methods to your main window class
    def _pdf_navigate_back(self):
        """Navigate back in PDF link history"""
        pdf_viewer = self._get_active_pdf_viewer()
        if pdf_viewer:
            pdf_viewer.navigate_back()
        #else:
        #    print("No active PDF viewer found")


    def _pdf_navigate_forward(self):
        """Navigate forward in PDF link history"""
        pdf_viewer = self._get_active_pdf_viewer()
        if pdf_viewer:
            pdf_viewer.navigate_forward()
        #else:
        #    print("No active PDF viewer found")

    def _get_active_pdf_viewer(self):
        """Get the currently active/visible PDF viewer
        
        Returns:
            PDFViewer instance or None
        """
        from PyQt5.QtWidgets import QApplication
        from time import time
        import os
        
        # Check if we're in H/V mode with multiple viewers
        if hasattr(self, 'pdf_manager') and hasattr(self.pdf_manager, 'pdf_layout_mode'):
            mode = self.pdf_manager.pdf_layout_mode
            
            if mode in ["horizontal", "vertical"]:
                #print(f"🔍 _get_active_pdf_viewer: H/V mode detected ({mode})")
                
                # Method 1: Check focused widget and walk up to find PDFViewer
                focused = QApplication.focusWidget()
                if focused:
                    #print(f"   Focused widget: {focused.__class__.__name__}")
                    
                    widget = focused
                    depth = 0
                    while widget and depth < 20:
                        # Check if this is a PDFViewer
                        if 'PDFViewer' in widget.__class__.__name__:
                            if hasattr(widget, 'pdf_document') and widget.pdf_document:
                                pdf_path = getattr(widget, 'pdf_path', 'unknown')
                                #print(f"   ✅ Found focused PDFViewer: {os.path.basename(pdf_path) if pdf_path != 'unknown' else 'unknown'}")
                                return widget
                        
                        # Check if widget contains a PDFViewer
                        if hasattr(widget, 'findChildren'):
                            try:
                                from pdf_viewer import PDFViewer
                                viewers = widget.findChildren(PDFViewer)
                                for v in viewers:
                                    if v.isVisible() and hasattr(v, 'pdf_document') and v.pdf_document:
                                        pdf_path = getattr(v, 'pdf_path', 'unknown')
                                        #print(f"   ✅ Found PDFViewer in focused widget children: {os.path.basename(pdf_path) if pdf_path != 'unknown' else 'unknown'}")
                                        return v
                            except:
                                pass
                        
                        widget = widget.parent()
                        depth += 1
                
                # Method 2: Check which viewer was clicked most recently
                if hasattr(self.pdf_manager, 'pdf_files') and self.pdf_manager.pdf_files:
                    #print(f"   Checking {len(self.pdf_manager.pdf_files)} viewers for recent clicks...")
                    
                    candidates = []
                    for pdf_path, data in self.pdf_manager.pdf_files.items():
                        if isinstance(data, dict):
                            viewer = data.get('viewer')
                            if viewer and viewer.isVisible():
                                click_time = getattr(viewer, '_last_click_time', 0)
                                if click_time > 0:
                                    candidates.append((click_time, viewer, pdf_path))
                                    #print(f"      {os.path.basename(pdf_path)}: {click_time}")
                    
                    if candidates:
                        candidates.sort(reverse=True, key=lambda x: x[0])
                        most_recent_time, viewer, pdf_path = candidates[0]
                        age = time() - most_recent_time
                        
                        #print(f"   Most recent click: {os.path.basename(pdf_path)} ({age:.1f}s ago)")
                        
                        if age < 120.0:  # 2 minute window
                            #print(f"   ✅ Using most recently clicked viewer")
                            return viewer
                        else:
                            pass
                            #print(f"   ⏰ Most recent click too old ({age:.1f}s ago)")
                
                # Method 3: Fallback to first visible viewer in H/V mode
                if hasattr(self.pdf_manager, 'pdf_files'):
                    #print(f"   Fallback: using first visible viewer...")
                    for pdf_path, data in self.pdf_manager.pdf_files.items():
                        if isinstance(data, dict):
                            viewer = data.get('viewer')
                            if viewer and viewer.isVisible():
                                #print(f"   ⚠️ Using first visible: {os.path.basename(pdf_path)}")
                                return viewer
                
                #print(f"   ❌ No viewer found in H/V mode")
                return None
        
        # Method 1: Check if pdf_manager has a current viewer
        if hasattr(self, 'pdf_manager') and self.pdf_manager:
            if hasattr(self.pdf_manager, 'get_current_viewer'):
                viewer = self.pdf_manager.get_current_viewer()
                if viewer:
                    #print(f"   ✅ Got viewer from pdf_manager.get_current_viewer()")
                    return viewer
            
            # Try to get viewer from pdf_manager's viewer dictionary or list
            if hasattr(self.pdf_manager, 'viewers'):
                viewers = self.pdf_manager.viewers
                if isinstance(viewers, dict) and len(viewers) > 0:
                    viewer = list(viewers.values())[0]
                    #print(f"   ✅ Got viewer from pdf_manager.viewers dict")
                    return viewer
                elif isinstance(viewers, list) and len(viewers) > 0:
                    #print(f"   ✅ Got viewer from pdf_manager.viewers list")
                    return viewers[0]
            
            # Check for single viewer attribute
            if hasattr(self.pdf_manager, 'viewer') and self.pdf_manager.viewer:
                #print(f"   ✅ Got viewer from pdf_manager.viewer")
                return self.pdf_manager.viewer
            
            if hasattr(self.pdf_manager, 'pdf_viewer') and self.pdf_manager.pdf_viewer:
                #print(f"   ✅ Got viewer from pdf_manager.pdf_viewer")
                return self.pdf_manager.pdf_viewer
        
        # Method 2: Search in main splitter for PDFViewer widgets
        if hasattr(self, 'main_splitter'):
            from pdf_viewer import PDFViewer
            
            # Search recursively in splitter
            def find_pdf_viewer(widget):
                if isinstance(widget, PDFViewer):
                    return widget
                
                # Check children
                if hasattr(widget, 'findChildren'):
                    viewers = widget.findChildren(PDFViewer)
                    if viewers:
                        return viewers[0]
                
                # Check QTabWidget
                if hasattr(widget, 'count') and hasattr(widget, 'widget'):
                    for i in range(widget.count()):
                        child = widget.widget(i)
                        if child:
                            result = find_pdf_viewer(child)
                            if result:
                                return result
                
                # Check layout
                if hasattr(widget, 'layout') and widget.layout():
                    layout = widget.layout()
                    for i in range(layout.count()):
                        item = layout.itemAt(i)
                        if item and item.widget():
                            result = find_pdf_viewer(item.widget())
                            if result:
                                return result
                
                return None
            
            for i in range(self.main_splitter.count()):
                widget = self.main_splitter.widget(i)
                if widget:
                    viewer = find_pdf_viewer(widget)
                    if viewer:
                        #print(f"   ✅ Found viewer in main_splitter")
                        return viewer
        
        # Method 3: Check for direct pdf_viewer attribute
        if hasattr(self, 'pdf_viewer') and self.pdf_viewer:
            #print(f"   ✅ Got viewer from self.pdf_viewer")
            return self.pdf_viewer
        
        #print(f"   ❌ No viewer found")
        return None
                        

    def toggle_pdf_toolbars(self, checked: bool):
        """Toggle PDF toolbars visibility for all open PDFs"""
        if not hasattr(self, 'pdf_manager'):
            return
        
        # Find the first (or current) PDF viewer and its data
        first_viewer = None
        first_data = None
        if hasattr(self.pdf_manager, 'pdf_files'):
            for path, data in self.pdf_manager.pdf_files.items():
                if isinstance(data, dict) and data.get('viewer'):
                    first_viewer = data['viewer']
                    first_data = data
                    break
        
        # Bring that PDF tab to the foreground (if found)
        if first_viewer and first_data:
            self.pdf_manager._bring_pdf_to_foreground(first_viewer, first_data)
        
        
        self.pdf_manager.set_toolbar_visible_state(checked)
        self.is_pdf_toolbar_visible = checked
        # Now toggle all PDF toolbars (this affects all open PDFs)
        self.pdf_manager.toggle_all_pdf_toolbars()


        # ✅ Update the main menu action (if it exists) – block signals to avoid recursion
        if hasattr(self, 'menu_pdf_toolbar_toggle_action'):
            action = self.menu_pdf_toolbar_toggle_action
            action.blockSignals(True)
            action.setChecked(checked)
            action.blockSignals(False)
        
        # # Update the state for future PDFs
        # if first_viewer:
            # new_state = first_viewer.is_toolbar_visible()
            # self.pdf_manager.set_toolbar_visible_state(new_state)
            
            # # Update menu checkmark
            # if hasattr(self, 'menu_pdf_toolbar_toggle_action'):
                # self.menu_pdf_toolbar_toggle_action.setChecked(new_state)

    def _bring_djvu_to_foreground(self):
        """Bring the DjVu tab to the foreground if it exists."""
        if not hasattr(self, 'pdf_manager') or not self.pdf_manager:
            return False
        tab_widget = self.pdf_manager.pdf_tabs
        if not tab_widget:
            return False
        
        # Find the DjVu tab by checking each widget for the 'toggle_toolbar' method
        for i in range(tab_widget.count()):
            widget = tab_widget.widget(i)
            if widget and hasattr(widget, 'toggle_toolbar'):  # DjvuTab has this
                tab_widget.setCurrentIndex(i)
                widget.setFocus()
                return True
        return False

    def toggle_djvu_toolbar(self):
        """Toggle DjVu viewer toolbar visibility for the current DjVu tab."""
        # First, bring DjVu tab to foreground if it exists
        if not self._bring_djvu_to_foreground():
            return  # No DjVu tab open
        
        # Now get the current (now active) tab
        if not hasattr(self, 'pdf_manager') or not self.pdf_manager:
            return
        tab_widget = self.pdf_manager.pdf_tabs
        if not tab_widget:
            return
        current = tab_widget.currentWidget()
        if current and hasattr(current, 'toggle_toolbar'):
            current.toggle_toolbar()
            # Sync menu checkmark
            if hasattr(self, 'menu_djvu_toolbar_toggle_action'):
                self.menu_djvu_toolbar_toggle_action.setChecked(current.toolbar_visible)

                
    def restore_menubar_state(self):
        """Restore menu bar visibility from config"""
        if hasattr(self, 'config_manager'):
            try:
                menubar_visible = self.config_manager.get_config_value('ui', 'menubar_visible', default=True)
                self.menuBar().setVisible(menubar_visible)
                
                # Update action state
                if hasattr(self, 'toggle_menubar_action'):
                    self.toggle_menubar_action.setChecked(menubar_visible)
            except:
                pass
    def restore_toolbar_state(self):
        """Restore main toolbar visibility from config"""
        if hasattr(self, 'config_manager') and hasattr(self, 'toolbar_manager'):
            try:
                toolbar_visible = self.config_manager.get_config_value('ui', 'main_toolbar_visible', default=True)
                
                if self.toolbar_manager.main_toolbar:
                    self.toolbar_manager.main_toolbar.setVisible(toolbar_visible)
                
                # Update action state
                if hasattr(self, 'toggle_toolbar_action'):
                    self.toggle_toolbar_action.setChecked(toolbar_visible)
            except:
                pass
            
    def contextMenuEvent(self, event):
        """Show context menu - include option to show menu bar if hidden"""
        menu = QMenu(self)
        
        # If menu bar is hidden, add option to show it
        if not self.menuBar().isVisible():
            show_menubar_action = QAction("Show Menu Bar (F11)", self)
            show_menubar_action.triggered.connect(lambda: self.menu_manager.toggle_menu_bar())
            menu.addAction(show_menubar_action)
            menu.addSeparator()
        
        # Add other context menu items here if needed
        
        # Show menu at cursor position
        if not menu.isEmpty():
            menu.exec_(event.globalPos())
            
    def keyPressEvent(self, event):
        """Handle global keyboard shortcuts"""
        # F11: Toggle menu bar
        if event.key() == Qt.Key_F11:
            if hasattr(self, 'menu_manager') and hasattr(self.menu_manager, 'toggle_menu_bar'):
                self.menu_manager.toggle_menu_bar()
            event.accept()
            return      
        # ✅ F12: Toggle main toolbar
        if event.key() == Qt.Key_F10:
            if hasattr(self, 'menu_manager') and hasattr(self.menu_manager, 'toggle_main_toolbar'):
                self.menu_manager.toggle_main_toolbar()
            event.accept()
            return
    
        # Call parent implementation for other keys
        super().keyPressEvent(event)


    def init_cwl_manager(self):
        """Initialize CWL manager with async loading"""
        from cwl_manager import CWLManager
        
        self.cwl_manager = CWLManager()
        
        # Initialize signals for progress updates (optional but nice)
        signals = self.cwl_manager.init_signals()
        
        # Connect signals for UI feedback
        signals.loading_started.connect(self._on_cwl_loading_started)
        signals.loading_progress.connect(self._on_cwl_loading_progress)
        signals.loading_finished.connect(self._on_cwl_loading_finished)
        signals.error_occurred.connect(self._on_cwl_error)
        
        # Load settings from config
        if hasattr(self, 'config_manager'):
            enabled_str = self.config_manager.get_config_value('cwl_completion', 'enabled_files', '')
            if enabled_str:
                enabled_files = [f.strip() for f in enabled_str.split(',') if f.strip()]
                self.cwl_manager.set_enabled_files(enabled_files, async_load=False)  # Don't load yet
            
            # Check if completion is enabled
            completion_enabled = self.config_manager.get_config_value(
                'cwl_completion', 'enabled', 'True'
            ).lower() == 'true'
            self.cwl_manager.set_completion_enabled(completion_enabled)
        
        # Start async loading
        self.cwl_manager.load_async(callback=self._on_cwl_ready)

    def _on_cwl_loading_started(self):
        """Called when CWL loading starts"""
        pass
        
    def _on_cwl_loading_progress(self, current, total):
        """Called during CWL loading"""
        lang = self.menu_language
        tr = self.translations[lang]
        message = tr["status_loading_completions"].format(current=current,total=total)
        self.update_status_bar(message)                               

    def _on_cwl_loading_finished(self, command_count):
        """Called when CWL loading completes"""
        lang = self.menu_language
        tr = self.translations[lang]
        message = tr["status_cwl_loading_complete"].format(command_count=command_count)
        self.update_status_bar(message)                               

    def _on_cwl_error(self, error_msg):
        """Called if CWL loading fails"""
        lang = self.menu_language
        tr = self.translations[lang]
        message = tr["status_error_loading_completions"]
        self.update_status_bar(message)                               

    def _on_cwl_ready(self):
        """Called when CWL is ready to use"""
        try:
            # Install LaTeX completer manager
            from latex_completer_manager import LaTeXCompleterManager
            
            self.latex_completer_manager = LaTeXCompleterManager(self)
            
            # Install on existing editors
            if hasattr(self, 'editor_manager') and hasattr(self.editor_manager, 'editor_files'):
                for file_path, editor_data in self.editor_manager.editor_files.items():
                    editor = editor_data.get('editor')
                    if editor:
                        self.latex_completer_manager.install(editor)
            
            # Refresh CWL completions
            self.latex_completer_manager.refresh_cwl()
            
            #print(f"✅ LaTeX completer ready with {self.cwl_manager.get_command_count()} commands")
            
        except Exception as e:
            print(f"❌ Error in _on_cwl_ready: {e}")
            import traceback
            traceback.print_exc()

            
    def _install_context_menus_on_existing_editors(self):
        """Install context menu on all existing editors"""
        if hasattr(self, 'editor_manager') and hasattr(self.editor_manager, 'editor_files'):
            for file_path, editor_data in self.editor_manager.editor_files.items():
                editor = editor_data.get('editor')
                if editor:
                    self.context_menu_manager.install_context_menu(editor)
        
        
    def _install_completers_on_existing_editors(self):
        """Install completers on all existing editors"""
        if hasattr(self, 'editor_manager') and hasattr(self.editor_manager, 'editor_files'):
            for file_path, editor_data in self.editor_manager.editor_files.items():
                editor = editor_data.get('editor')
                if editor:
                    self.latex_completer_manager.install(editor)



    def apply_text_direction_to_editors(self):
        """Apply text direction change to all open editors"""
        try:
            if (hasattr(self.main_window, 'editor_manager') and 
                hasattr(self.main_window.editor_manager, 'editor_files')):
                
                alignment = Qt.AlignRight if self.main_window.is_rtl else Qt.AlignLeft
                updated_count = 0
                
                for file_path, data in self.main_window.editor_manager.editor_files.items():
                    editor = data.get('editor')
                    if editor and hasattr(editor, 'setAlignment'):
                        editor.setAlignment(alignment)
                        updated_count += 1
                
                #print(f"↔️ Applied text direction (RTL: {self.main_window.is_rtl}) to {updated_count} editors")
        except Exception as e:
            print(f"❌ Error applying text direction: {e}")


    def apply_saved_visibility_settings(self):
        """Apply saved visibility settings after startup"""
        # Get saved values
       
        line_visible = getattr(self, 'is_line_numbers_visible', True)
        fold_visible = getattr(self, 'is_fold_markers_visible', True)
        
        #print(f"Applying saved visibility: line_numbers={line_visible}, fold_markers={fold_visible}")
        
        # Apply via menu_manager (this updates everything)
        if hasattr(self, 'menu_manager'):
            self.menu_manager.toggle_line_numbers(line_visible)
            self.menu_manager.toggle_fold_markers(fold_visible)
