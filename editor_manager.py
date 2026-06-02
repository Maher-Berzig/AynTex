# editor_manager.py
"""
Editor Manager - Handles text editor creation, management, and operations
"""
import re
import os
from PyQt5.QtWidgets import (
    QPlainTextEdit, QTabWidget, QVBoxLayout, QWidget, QLabel, QSizePolicy,QProgressDialog,
    QTextEdit, QPushButton, QListWidget, QSplitter, QMenu, QAction, QInputDialog, 
    QMessageBox, QFileDialog, QApplication, QDialog, QHBoxLayout, QDialogButtonBox
)
from PyQt5.QtCore import Qt, QTimer, QRect, QPoint, pyqtSignal
from PyQt5.QtGui import QFont, QTextCursor, QColor, QPolygon, QPen, QBrush
     

class EditorManager:
    def __init__(self, main_window):
        self.main_window = main_window
        self.editor_files = {}  # {path: {editor, pdf_path, modified, saved_content, index, tab_widget_index, label}}
        self.current_file = None
        self.is_modified = False
        self.editor_layout_mode = "tabbed"  # tabbed, horizontal, vertical
        self.current_sizes = {"editor": []}
        self._loading_file = False

        # UI components (will be set by layout manager)
        self.editor_layout_mode = "tabbed"
        self.tab_order = []  # Add this!
        self.editor_tabs = None  # QTabWidget (tabbed) or list of QTabWidgets (horizontal/vertical)
        self.editor_splitter = None  # For horizontal/vertical mode
        
        self._active_tab_widget_index = 0  # Track active tab widget in H/V mode
        
        from PyQt5.QtCore import QTimer
        bookmark_timer = QTimer()
        bookmark_timer.timeout.connect(self.main_window.load_bookmarks_on_startup)
        bookmark_timer.setSingleShot(True)
        bookmark_timer.start(1000)  # Load after 1 second to ensure all components are ready
        
        
        # Load colors from config
        self.main_window.load_highlighting_colors()

        from file_watcher import FileWatcher
        self.file_watcher = FileWatcher(self)


    def setup_ui(self):
        """Create editor UI once"""
        if self.editor_tabs is None:
            self.editor_tabs = QTabWidget()
            self.editor_tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.editor_tabs.setTabsClosable(True)
            self.editor_tabs.tabCloseRequested.connect(self.close_editor_tab)
            self.editor_tabs.setMinimumSize(300, 200)
###
    def _get_relative_path(self, target_path, base_path):
        """Return relative path from base_path's directory to target_path."""
        if not base_path:
            return target_path
        base_dir = os.path.dirname(base_path)
        try:
            rel = os.path.relpath(target_path, base_dir)
            # Use forward slashes for LaTeX
            rel = rel.replace('\\', '/')
            return rel
        except ValueError:
            return target_path
    def insert_figure_at_cursor(self, editor, image_path):
        """Insert LaTeX figure environment with \includegraphics at cursor position."""
        if not editor or not image_path:
            return

        # Get current file path to compute relative path
        current_file = self.get_current_file_path()
        rel_path = self._get_relative_path(image_path, current_file)
        
        # Escape underscores and special chars for LaTeX? Not strictly necessary inside braces, but safe.
        # We'll just use the path as is.

        # Get base filename without extension for label
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        # Remove any problematic characters for label (keep letters, numbers, dashes, underscores)
        label_name = re.sub(r'[^a-zA-Z0-9_-]', '', base_name)
        if not label_name:
            label_name = "fig"

        figure_template = r"""\begin{figure}[htbp]
        \centering
        \includegraphics[width=0.8\textwidth]{%s}
        \caption{}
        \label{fig:%s}
    \end{figure}""" % (rel_path, label_name)

        cursor = editor.textCursor()
        cursor.beginEditBlock()
        cursor.insertText(figure_template)
        cursor.endEditBlock()
        
        # Place cursor inside the caption braces
        # Find position after \caption{ and set cursor there
        text = editor.toPlainText()
        cursor_pos = cursor.position()
        # Simple: move cursor back to just after \caption{ (robust enough)
        # We can search backwards from insertion point
        # Alternative: insert with placeholder and move
        # For simplicity, we'll not reposition cursor now.
        editor.setTextCursor(cursor)
        
        # Optionally, set focus
        editor.setFocus()
    

###

    
    def on_tab_changed(self, index):
        """Handle tab change event"""
        if index < 0:
            return

        mode = self.editor_layout_mode
        editor = None

        if mode == "tabbed":
            if self.editor_tabs and isinstance(self.editor_tabs, QTabWidget):
                editor = self.editor_tabs.widget(index)
        else:
            for tab_widget in self.editor_tabs:
                if tab_widget and tab_widget.currentIndex() == index:
                    editor = tab_widget.widget(index)
                    break

        if editor:
            self.update_current_file_from_editor(editor)
            # update_current_file_from_editor already calls _highlight_active_editor(editor)
            self.main_window.update_title()
            
    def _on_hv_tab_bar_clicked(self, index, editor):
        """Handle tab bar click in H/V mode to update active editor border.

        In H/V mode each file has its own single-tab QTabWidget, so
        currentChanged never fires (index is always 0). tabBarClicked
        fires on every click regardless.
        """
        if not editor:
            return
        self.update_current_file_from_editor(editor)
        self.main_window.update_title()
        editor.setFocus()
    
    def _highlight_active_editor(self, active_editor=None):
        """Highlight the active editor with a colored internal border, dim others."""
        ACTIVE_BORDER = "border: 2px solid #3574F0;"      # Blue border
        INACTIVE_BORDER = "border: 2px solid transparent;" # Same width to prevent content shift

        for path, data in self.editor_files.items():
            editor = data.get('editor')
            if not editor:
                continue
            try:
                editor.setStyleSheet(
                    ACTIVE_BORDER if editor is active_editor else INACTIVE_BORDER
                )
            except RuntimeError:
                pass  # Widget was deleted            
########
    def handle_ctrl_click_environment(self, editor, position):
        """
        Handle Ctrl+Click on LaTeX environment names.
        Creates multiple cursors to edit both \begin{env} and \end{env} simultaneously.
        Returns True if handled, False otherwise.
        """
        import re
        from PyQt5.QtGui import QTextCursor, QTextCharFormat, QColor
        from PyQt5.QtCore import Qt
        
        text = editor.toPlainText()
        
        # Find if cursor is inside an environment name in \begin{...} or \end{...}
        # Pattern to find \begin{envname} or \end{envname}
        pattern = re.compile(r'\\(begin|end)\{([^}]+)\}')
        
        clicked_env = None
        clicked_type = None  # 'begin' or 'end'
        env_name_start = None
        env_name_end = None
        
        for match in pattern.finditer(text):
            # Calculate the position of the environment name (inside braces)
            brace_start = match.start() + len(match.group(1)) + 2  # +2 for '\\' and '{'
            brace_end = match.end() - 1  # -1 for '}'
            
            if brace_start <= position <= brace_end:
                clicked_env = match.group(2)
                clicked_type = match.group(1)
                env_name_start = brace_start
                env_name_end = brace_end
                break
        
        if not clicked_env:
            return False
        
        # Now find the matching \begin or \end
        # Parse all environments to find the match
        stack = []
        all_matches = []
        
        for match in pattern.finditer(text):
            all_matches.append({
                'type': match.group(1),
                'name': match.group(2),
                'full_start': match.start(),
                'full_end': match.end(),
                'name_start': match.start() + len(match.group(1)) + 2,
                'name_end': match.end() - 1
            })
        
        # Find the matching pair
        matching_name_start = None
        matching_name_end = None
        
        if clicked_type == 'begin':
            # Find matching \end - search forward
            depth = 0
            found_self = False
            for m in all_matches:
                if m['name_start'] == env_name_start:
                    found_self = True
                    depth = 1
                    continue
                if found_self and m['name'] == clicked_env:
                    if m['type'] == 'begin':
                        depth += 1
                    elif m['type'] == 'end':
                        depth -= 1
                        if depth == 0:
                            matching_name_start = m['name_start']
                            matching_name_end = m['name_end']
                            break
        else:  # clicked_type == 'end'
            # Find matching \begin - search backward
            depth = 0
            found_self = False
            for m in reversed(all_matches):
                if m['name_start'] == env_name_start:
                    found_self = True
                    depth = 1
                    continue
                if found_self and m['name'] == clicked_env:
                    if m['type'] == 'end':
                        depth += 1
                    elif m['type'] == 'begin':
                        depth -= 1
                        if depth == 0:
                            matching_name_start = m['name_start']
                            matching_name_end = m['name_end']
                            break
        
        if matching_name_start is None:
            # No matching pair found
            return False
        
        # Create selections for both environment names
        # We'll use extra selections to highlight both and track them
        
        # Store the positions for synchronized editing
        editor._env_sync_positions = [
            (env_name_start, env_name_end),
            (matching_name_start, matching_name_end)
        ]
        editor._env_sync_active = True
        editor._env_original_name = clicked_env
        
        # Select the clicked environment name
        cursor = editor.textCursor()
        cursor.setPosition(env_name_start)
        cursor.setPosition(env_name_end, QTextCursor.KeepAnchor)
        editor.setTextCursor(cursor)
        
        # Highlight the matching environment name with extra selections
        highlight_format = QTextCharFormat()
        highlight_format.setBackground(QColor(255, 255, 0, 100))  # Light yellow
        highlight_format.setForeground(QColor(0, 0, 200))  # Blue text
        
        extra_cursor = QTextCursor(editor.document())
        extra_cursor.setPosition(matching_name_start)
        extra_cursor.setPosition(matching_name_end, QTextCursor.KeepAnchor)
        
        extra_selection = type('ExtraSelection', (), {})()
        extra_selection.cursor = extra_cursor
        extra_selection.format = highlight_format
        
        # Store as QTextEdit.ExtraSelection
        from PyQt5.QtWidgets import QTextEdit
        selection = QTextEdit.ExtraSelection()
        selection.cursor = extra_cursor
        selection.format = highlight_format
        
        editor.setExtraSelections([selection])
        
        # Connect to text changed to synchronize edits
        if not hasattr(editor, '_env_sync_connected') or not editor._env_sync_connected:
            editor.textChanged.connect(lambda: self._sync_environment_edit(editor))
            editor._env_sync_connected = True
        
        # Connect to cursor position changed to clear sync mode when moving away
        if not hasattr(editor, '_env_cursor_connected') or not editor._env_cursor_connected:
            editor.cursorPositionChanged.connect(lambda: self._check_env_sync_cursor(editor))
            editor._env_cursor_connected = True
        
        return True

    def _sync_environment_edit(self, editor):
        """Synchronize environment name edits between \begin and \end"""
        if not getattr(editor, '_env_sync_active', False):
            return
        
        if getattr(editor, '_env_sync_in_progress', False):
            return
        
        try:
            editor._env_sync_in_progress = True
            
            positions = getattr(editor, '_env_sync_positions', None)
            original_name = getattr(editor, '_env_original_name', None)
            
            if not positions or not original_name:
                self._clear_env_sync(editor)
                return
            
            text = editor.toPlainText()
            cursor = editor.textCursor()
            current_pos = cursor.position()
            
            # Determine which position we're editing
            pos1_start, pos1_end = positions[0]
            pos2_start, pos2_end = positions[1]
            
            # Check if cursor is in the first or second position area
            # Account for text length changes
            original_len = len(original_name)
            
            # Find the current content at first position
            # We need to detect what was typed
            import re
            pattern = re.compile(r'\\(begin|end)\{([^}]*)\}')
            
            matches = list(pattern.finditer(text))
            
            if len(matches) < 2:
                self._clear_env_sync(editor)
                return
            
            # Find which match contains current cursor
            editing_match = None
            other_match = None
            
            for m in matches:
                name_start = m.start() + len(m.group(1)) + 2
                name_end = m.end() - 1
                
                # Check if cursor is near this match (within the env name area)
                if name_start <= current_pos <= name_end + 1:
                    editing_match = m
                    break
            
            if not editing_match:
                # Cursor moved outside, but check if we just finished typing
                # by looking for modified environment names
                return
            
            new_name = editing_match.group(2)
            editing_type = editing_match.group(1)
            
            # Find the matching pair
            for m in matches:
                if m == editing_match:
                    continue
                # Check if this could be our pair
                m_type = m.group(1)
                if editing_type == 'begin' and m_type == 'end':
                    # Check if it's after the begin and was originally matching
                    if m.start() > editing_match.start():
                        other_match = m
                        break
                elif editing_type == 'end' and m_type == 'begin':
                    # Check if it's before the end
                    if m.start() < editing_match.start():
                        other_match = m
            
            if not other_match:
                return
            
            other_name = other_match.group(2)
            
            # If names differ, update the other one
            if new_name != other_name:
                other_name_start = other_match.start() + len(other_match.group(1)) + 2
                other_name_end = other_match.end() - 1
                
                # Replace the other environment name
                doc_cursor = editor.textCursor()
                doc_cursor.setPosition(other_name_start)
                doc_cursor.setPosition(other_name_end, editor.textCursor().KeepAnchor)
                
                # Block signals to prevent recursion
                editor.blockSignals(True)
                doc_cursor.insertText(new_name)
                editor.blockSignals(False)
                
                # Update stored positions
                len_diff = len(new_name) - len(other_name)
                
                # Restore cursor position (adjusted if needed)
                if other_name_start < current_pos:
                    new_cursor = editor.textCursor()
                    new_cursor.setPosition(current_pos + len_diff)
                    editor.setTextCursor(new_cursor)
                
                # Update highlight
                self._update_env_highlight(editor, editing_match, new_name)
                
        except Exception as e:
            print(f"Error in _sync_environment_edit: {e}")
            import traceback
            traceback.print_exc()
            self._clear_env_sync(editor)
        finally:
            editor._env_sync_in_progress = False

    def _update_env_highlight(self, editor, editing_match, new_name):
        """Update the highlight on the paired environment"""
        import re
        from PyQt5.QtGui import QTextCursor, QTextCharFormat, QColor
        from PyQt5.QtWidgets import QTextEdit
        
        text = editor.toPlainText()
        pattern = re.compile(r'\\(begin|end)\{([^}]*)\}')
        
        editing_type = editing_match.group(1)
        
        for m in pattern.finditer(text):
            if m.group(2) == new_name and m.group(1) != editing_type:
                # Found the pair, highlight it
                name_start = m.start() + len(m.group(1)) + 2
                name_end = m.end() - 1
                
                highlight_format = QTextCharFormat()
                highlight_format.setBackground(QColor(255, 255, 0, 100))
                highlight_format.setForeground(QColor(0, 0, 200))
                
                extra_cursor = QTextCursor(editor.document())
                extra_cursor.setPosition(name_start)
                extra_cursor.setPosition(name_end, QTextCursor.KeepAnchor)
                
                selection = QTextEdit.ExtraSelection()
                selection.cursor = extra_cursor
                selection.format = highlight_format
                
                editor.setExtraSelections([selection])
                return

    def _check_env_sync_cursor(self, editor):
        """Check if cursor moved away from environment name, clear sync if so"""
        if not getattr(editor, '_env_sync_active', False):
            return
        
        # Don't check during sync operations
        if getattr(editor, '_env_sync_in_progress', False):
            return
        
        import re
        
        cursor = editor.textCursor()
        
        # If there's no selection and cursor moved significantly, consider clearing
        if not cursor.hasSelection():
            text = editor.toPlainText()
            pos = cursor.position()
            
            # Check if cursor is still in an environment name
            pattern = re.compile(r'\\(begin|end)\{([^}]*)\}')
            in_env = False
            
            for m in pattern.finditer(text):
                name_start = m.start() + len(m.group(1)) + 2
                name_end = m.end() - 1
                if name_start <= pos <= name_end:
                    in_env = True
                    break
            
            # If cursor is outside all env names and user pressed Enter or moved far
            # we might want to clear, but for now let's keep it active

    def _clear_env_sync(self, editor):
        """Clear environment synchronization mode"""
        editor._env_sync_active = False
        editor._env_sync_positions = None
        editor._env_original_name = None
        editor.setExtraSelections([])

    def setup_editor_ctrl_click(self, editor):
        """Setup Ctrl+Click handling for the editor"""
        original_mouse_press = editor.mousePressEvent
        
        def custom_mouse_press(event):
            from PyQt5.QtCore import Qt
            
            # Check for Ctrl+Click
            if event.modifiers() & Qt.ControlModifier and event.button() == Qt.LeftButton:
                # Get position from click
                cursor = editor.cursorForPosition(event.pos())
                position = cursor.position()
                
                # Try to handle as environment click
                if self.handle_ctrl_click_environment(editor, position):
                    event.accept()
                    return
            
            # Fall through to original handler
            original_mouse_press(event)
        
        editor.mousePressEvent = custom_mouse_press
    
########    
    def apply_visibility_settings_to_editor(self, editor):
        """Apply current visibility settings to an editor"""
        # Get settings from main_window
        line_numbers_visible = getattr(self.main_window, 'is_line_numbers_visible', True)
        fold_markers_visible = getattr(self.main_window, 'is_fold_markers_visible', True)
        
        #print(f"Applying visibility to editor: line_numbers={line_numbers_visible}, fold_markers={fold_markers_visible}")
        
        # Apply to editor
        if hasattr(editor, 'set_line_numbers_visible'):
            editor.set_line_numbers_visible(line_numbers_visible)
        elif hasattr(editor, '_show_line_numbers'):
            editor._show_line_numbers = line_numbers_visible
            if hasattr(editor, 'updateLineNumberAreaWidth'):
                editor.updateLineNumberAreaWidth()
            if hasattr(editor, 'lineNumberArea'):
                editor.lineNumberArea.update()
        
        if hasattr(editor, 'set_fold_markers_visible'):
            editor.set_fold_markers_visible(fold_markers_visible)
        elif hasattr(editor, '_show_fold_markers'):
            editor._show_fold_markers = fold_markers_visible
            editor._folding_enabled = fold_markers_visible
            if hasattr(editor, 'updateLineNumberAreaWidth'):
                editor.updateLineNumberAreaWidth()
            if hasattr(editor, 'lineNumberArea'):
                editor.lineNumberArea.update()

    def _on_hv_editor_tab_bar_clicked(self, index, tab_widget):
        """Handle tab bar click in H/V mode to update active editor border.
        
        In H/V mode each file has its own single-tab QTabWidget, so
        currentChanged never fires (index is always 0). tabBarClicked
        fires on every click, allowing us to update the highlight.
        """
        if not tab_widget:
            return
        editor = tab_widget.widget(index)
        if editor:
            self.update_current_file_from_editor(editor)
            self.main_window.update_title()
            editor.setFocus()
            
    def create_new_editor_tab(self, filename="Untitled", pdf_path=None, content=None):
        """Create new editor tab - Fixed for proper file tracking and closure"""
        try:
            # ✅ Check if we need to remove welcome tabs first
            self._remove_welcome_tabs_if_needed()

            # Ensure editor_tabs is initialized
            if self.editor_tabs is None:
                self.setup_ui()
                if self.editor_tabs is None:
                    raise RuntimeError("Failed to create editor_tabs")

            # ✅ FIX: Properly determine full path - preserve original if already absolute
            if os.path.isabs(filename):
                full_path = self.normalize_path(filename)
                # ✅ FIX: Update last_opened_directory from the file's actual location
                self.last_opened_directory = os.path.dirname(full_path)
            else:
                # Only use last_opened_directory for truly new/untitled files
                if hasattr(self, 'last_opened_directory') and self.last_opened_directory:
                    base_dir = self.last_opened_directory
                else:
                    base_dir = os.path.expanduser("~")
                full_path = self.normalize_path(os.path.join(base_dir, filename))

            # Create editor
            from bookmarks_manager import BookmarksManager
            editor = BookmarksManager(self.main_window)
        
            # ✅ Enable drag-and-drop file opening on every editor
            editor.setAcceptDrops(True)

            # Override drag/drop on the editor to route through EditorManager
            original_drag_enter = editor.dragEnterEvent
            original_drag_move = editor.dragMoveEvent
            original_drop = editor.dropEvent

            def custom_drag_enter(event):
                if event.mimeData().hasUrls():
                    for url in event.mimeData().urls():
                        if url.isLocalFile():
                            event.acceptProposedAction()
                            return
                original_drag_enter(event)

            def custom_drag_move(event):
                if event.mimeData().hasUrls():
                    for url in event.mimeData().urls():
                        if url.isLocalFile():
                            event.acceptProposedAction()
                            return
                original_drag_move(event)

            # def custom_drop(event):
                # if event.mimeData().hasUrls():
                    # for url in event.mimeData().urls():
                        # file_path = url.toLocalFile()
                        # if file_path and os.path.isfile(file_path):
                            # # ✅ Open via EditorManager — creates tab, tracks file, etc.
                            # self.open_specific_file(file_path)
                    # event.acceptProposedAction()
                    # return
                # original_drop(event)

            def custom_drop(event):
                if event.mimeData().hasUrls():
                    for url in event.mimeData().urls():
                        file_path = url.toLocalFile()
                        if file_path and os.path.isfile(file_path):
                            ext = os.path.splitext(file_path)[1].lower()
                            if ext in ['.pdf', '.jpg', '.jpeg', '.png', '.bmp', '.ps', '.eps']:
                                self.insert_figure_at_cursor(editor, file_path)
                            elif ext == '.tex':
                                self.open_specific_file(file_path)
                            # Ignore other extensions
                    event.acceptProposedAction()
                    return
                original_drop(event)
    
                
            def on_spell_timeout(e=editor):
                if sc.is_editor_valid(e) and sc.enabled:
                    sc._rehighlight_visible(e, skip_spell_check=False)   # ← add False    

            editor.dragEnterEvent = custom_drag_enter
            editor.dragMoveEvent = custom_drag_move
            editor.dropEvent = custom_drop


###
            # After creating the editor, add:
            self.setup_editor_ctrl_click(editor)

            # Apply visibility settings from main_window
            self.apply_visibility_settings_to_editor(editor)

            
            # FORCE: Ensure no context menu policy interference
            editor.setContextMenuPolicy(Qt.DefaultContextMenu)

            # Install completers on new editor
            if hasattr(self.main_window, 'latex_completer_manager'):
                QTimer.singleShot(100, lambda e=editor: self.main_window.latex_completer_manager.install(e))

            # Apply current text direction BEFORE setting content
            if hasattr(self.main_window, 'is_rtl') and self.main_window.is_rtl:
                editor.setAlignment(Qt.AlignRight)
            else:
                editor.setAlignment(Qt.AlignLeft)

            # Set content after alignment is established
            if content:
                if hasattr(editor, 'setContentSafely'):
                    editor.setContentSafely(content)
                else:
                    editor.setPlainText(content)

            editor.parent_editor_manager = self

            # Setup
            #self.setup_keyboard_shortcuts(editor)

            # Properties
            #font = QFont("Consolas", self.main_window.editor_font_size)
            font_family = getattr(self.main_window, 'editor_font_family', 'Consolas')
            font_size = getattr(self.main_window, 'editor_font_size', 10)

            font = QFont(font_family, font_size)            
            editor.setFont(font)
            editor.setLayoutDirection(Qt.RightToLeft if self.main_window.is_rtl else Qt.LeftToRight)
###
            # Syntax highlighting — wire BEFORE content so it highlights on load
            from latex_highlighter import LaTeXHighlighter
            highlighter = LaTeXHighlighter(
                editor.document(),
                self.main_window.config_manager
            )
            editor.highlighter = highlighter

            # Wire spell checker immediately — setup_spell_check_for_editor waits
            # for the editor's first paintEvent before running the actual check,
            # so there is no risk of blocking the file from opening.
            mw = self.main_window
            def _setup_spell(e=editor, w=mw):
                sc = w.spell_checker
                if sc is not None:
                    sc.setup_spell_check_for_editor(e)

            QTimer.singleShot(1000, _setup_spell)



            # Signals
            editor.document().contentsChanged.connect(self.on_text_changed)
            editor.cursorPositionChanged.connect(self.main_window.update_position)

            # Focus handler
            original_focus_in = editor.focusInEvent

            def make_focus_wrapper(editor_ref, manager_ref, original_handler):
                def focus_in_wrapper(event):
                    try:
                        if not editor_ref or not hasattr(editor_ref, 'document'):
                            original_handler(event)
                            return
                        # Update current file and active tab widget
                        if hasattr(manager_ref, 'update_current_file_from_editor'):
                            manager_ref.update_current_file_from_editor(editor_ref)
                    except RuntimeError as e:
                        print(f"Editor widget deleted during focus event (expected): {e}")
                    except KeyboardInterrupt:
                        print("Focus handler interrupted by user")
                        raise
                    except Exception as e:
                        print(f"⚠️ Warning in focus handler: {e}")
                    finally:
                        try:
                            original_handler(event)
                        except RuntimeError:
                            pass
                        except Exception as e:
                            print(f"⚠️ Error in original focus handler: {e}")
                return focus_in_wrapper

            editor.focusInEvent = make_focus_wrapper(editor, self, original_focus_in)

            # Content — detach highlighter during load so it doesn't
            # fire on every block insertion (very expensive for large files)
            if content is not None:
                self._loading_file = True
                editor.blockSignals(True)

                # Detach highlighter from document during load
                highlighter.setDocument(None)

                cursor = editor.textCursor()
                cursor.beginEditBlock()
                editor.loadFileContent(content)
                cursor.endEditBlock()
                editor.setTextCursor(cursor)

                editor.blockSignals(False)
                self._loading_file = False

                # Reattach highlighter after load — deferred so UI renders first
                def restore_highlighter(h=highlighter, e=editor):
                    h.setDocument(e.document())
                    # Incremental syntax highlight stays on main thread (fast, no I/O)
                    h.rehighlight_incremental(chunk=50, delay=0)
                    # Async spell check — fires from the thread pool, result
                    # applied back on the main thread via QueuedConnection
                    mw = self.main_window
                    QTimer.singleShot(
                        2000,
                        lambda e=editor, w=mw: (
                            w.spell_checker.setup_spell_check_for_editor(e)
                            if w.spell_checker is not None
                            and w.spell_checker.enabled
                            and w.spell_checker.dictionaries_loaded
                            else None
                        )
                    )

                QTimer.singleShot(100, restore_highlighter)                
                
                
                
            # Add to layout
            mode = self.editor_layout_mode
            tab_index = -1
            tab_widget_index = 0

            # ✅ FIX: Use basename for display, but full_path for storage
            display_name = os.path.basename(full_path)

            if mode == "tabbed":
                if not isinstance(self.editor_tabs, QTabWidget):
                    self.editor_tabs = QTabWidget()
                    self.editor_tabs.setTabsClosable(True)
                    self.editor_tabs.tabCloseRequested.connect(self.close_editor_tab)
                    self.editor_tabs.setStyleSheet("""
                        QTabBar::tab {
                            background: white;
                            bottom: -2px;         /* helps the tab sit flush with the pane */
                        }
                    """)
                target_widget = self.editor_tabs
                tab_index = target_widget.addTab(editor, display_name)
                target_widget.setCurrentIndex(tab_index)
                if not hasattr(self, '_tab_change_connected'):
                    target_widget.currentChanged.connect(self.on_tab_changed)
                    self._tab_change_connected = True
            else:
                self._active_tab_widget_index = tab_widget_index
                if not isinstance(self.editor_tabs, list):
                    self.editor_tabs = []

                # Create new tab widget
                target_widget = QTabWidget()
                target_widget.setTabsClosable(True)
                target_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                target_widget.setMinimumSize(200, 150)

                # Connect close handler - use full_path
                def make_close_handler(file_path):
                    def handler(idx):
                        self.close_editor_tab_by_filename(file_path)
                    return handler

                target_widget.tabCloseRequested.connect(make_close_handler(full_path))

                # Add editor with display name
                tab_index = target_widget.addTab(editor, display_name)
                target_widget.setCurrentIndex(tab_index)

                # Add to splitter
                if self.editor_splitter:
                    self.editor_splitter.addWidget(target_widget)

                # Store in editor_tabs list
                tab_widget_index = len(self.editor_tabs)
                self.editor_tabs.append(target_widget)

                # Connect tab change
                attr = f'_tab_change_connected_{tab_widget_index}'
                if not hasattr(self, attr):
                    target_widget.currentChanged.connect(self.on_tab_changed)
                    setattr(self, attr, True)
                # ✅ FIX: Connect tabBarClicked for H/V mode border highlighting
                # (currentChanged won't fire because each tab widget has only one tab)
                target_widget.tabBarClicked.connect(
                    lambda idx, tw=target_widget: self._on_hv_editor_tab_bar_clicked(idx, tw)
                )
            # ✅ FIX: Store data using full normalized path as key
            self.editor_files[full_path] = {
                'editor': editor,
                'pdf_path': pdf_path or (os.path.splitext(full_path)[0] + ".pdf"),
                'modified': False,
                'saved_content': content or "",
                'index': tab_index,
                'tab_widget_index': tab_widget_index,
                'label': None,
                'latex_engine': self.main_window.latex_engine,
                'display_name': display_name,
                'is_new_file': not os.path.exists(full_path)  # ✅ FIX: Check if file actually exists
            }
            
            self.file_watcher.watch(full_path)

            # Manage tab order with full path
            if not hasattr(self, 'tab_order'):
                self.tab_order = []
            if full_path not in self.tab_order:
                self.tab_order.append(full_path)

            # Focus and update
            editor.setFocus()
            self.current_file = full_path
            self.main_window.update_title()

            # Update splitter sizes in H/V mode
            if mode != "tabbed" and hasattr(self.main_window.layout_manager, 'editor_splitter'):
                splitter = self.main_window.layout_manager.editor_splitter
                if splitter and splitter.count() > 0:
                    equal_size = 600 // splitter.count()
                    splitter.setSizes([equal_size] * splitter.count())

            # ✅ FIX: Force fold region parsing for new file
            # Invalidate cache so regions are parsed on first paint
            if hasattr(editor, '_fold_cache_valid'):
                editor._fold_cache_valid = False
            
            self._highlight_active_editor(editor)
            
            # Schedule a delayed update to ensure fold markers appear
            QTimer.singleShot(100, lambda: self._trigger_fold_region_update(editor))
        
            #print(f"✅ Created editor tab for: {display_name} (path: {full_path})")
            return editor

        except Exception as e:
            print(f"❌ Error creating editor tab: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _trigger_fold_region_update(self, editor):
        """Trigger fold region parsing and UI update for an editor"""
        try:
            if editor and hasattr(editor, '_parse_folding_regions'):
                editor._fold_cache_valid = False  # Force re-parse
                editor._parse_folding_regions()
                if hasattr(editor, 'lineNumberArea'):
                    editor.lineNumberArea.update()
                editor.viewport().update()
        except Exception as e:
            print(f"Warning: Could not update fold regions: {e}")
        

    def get_active_editor(self):
        """Get the currently active editor widget - FIXED for H/V mode"""
        try:
            # Use current_file as primary source of truth
            if self.current_file and self.current_file in self.editor_files:
                editor = self.editor_files[self.current_file].get('editor')
                if editor and hasattr(editor, 'textCursor'):
                    return editor
            
            if self.editor_layout_mode == "tabbed":
                if hasattr(self, 'editor_tabs') and self.editor_tabs:
                    current_widget = self.editor_tabs.currentWidget()
                    if hasattr(current_widget, 'textCursor'):
                        return current_widget
            else:
                # H/V mode - use active tab widget index
                if hasattr(self, 'editor_tabs') and isinstance(self.editor_tabs, list):
                    active_index = getattr(self, '_active_tab_widget_index', 0)
                    if 0 <= active_index < len(self.editor_tabs):
                        tab_widget = self.editor_tabs[active_index]
                        if tab_widget and tab_widget.count() > 0:
                            current_widget = tab_widget.currentWidget()
                            if hasattr(current_widget, 'textCursor'):
                                return current_widget
                    
                    # Fallback
                    for tab_widget in self.editor_tabs:
                        if tab_widget and tab_widget.count() > 0:
                            current_widget = tab_widget.currentWidget()
                            if hasattr(current_widget, 'textCursor'):
                                return current_widget
            
            return None
        except Exception as e:
            print(f"Error getting active editor: {e}")
            return None
        
    
    def close_editor_tab(self, index):
        """Close editor tab or widget (including tool tabs like LaTeX Comparator)"""
        try:
            # Get file path before closing
            file_path = None
            is_tool_tab = False
            tool_tab_names = ["LaTeX Comparator", "Comparator", "Welcome"]  # Add other tool tab names here
            
            if self.editor_layout_mode == "tabbed" and hasattr(self, 'editor_tabs'):
                widget = self.editor_tabs.widget(index)
                tab_text = self.editor_tabs.tabText(index)
                
                # Check if this is a tool tab (not a file editor)
                if tab_text in tool_tab_names:
                    is_tool_tab = True
                
                if widget and not is_tool_tab:
                    # Find file path for this widget
                    for path, data in self.editor_files.items():
                        if data.get('editor') == widget:
                            file_path = path
                            break
            
            # Remove bookmarks for this file (only if it's a file, not a tool)
            if file_path and hasattr(self.main_window, 'toolbar_manager'):
                self.main_window.toolbar_manager.remove_bookmarks_tab(file_path)

            mode = self.editor_layout_mode
            editor = None
            filename_to_close = None
            
            # ============================================
            # Handle TOOL TABS (LaTeX Comparator, etc.)
            # ============================================
            if is_tool_tab:
                if mode == "tabbed":
                    if not self.editor_tabs or index >= self.editor_tabs.count():
                        return
                    
                    widget = self.editor_tabs.widget(index)
                    self.editor_tabs.removeTab(index)
                    
                    # Properly cleanup the widget
                    if widget:
                        widget.hide()
                        widget.setParent(None)
                        widget.deleteLater()
                    
                    # Restore editor width if it was expanded for comparator
                    if getattr(self.main_window, '_editor_expanded', False):
                        self.main_window.toggle_editor_expand_width()
                    
                    # Show welcome if no editors remain
                    if len(self.editor_files) == 0 and self.editor_tabs.count() == 0:
                        if hasattr(self.main_window, 'layout_manager'):
                            QTimer.singleShot(50, self.main_window.layout_manager._recreate_editor_container)
                    
                    #print(f"✅ Closed tool tab: {tab_text}")
                    return
            
            # ============================================
            # Handle REGULAR FILE TABS
            # ============================================
            if mode == "tabbed":
                if not self.editor_tabs or index >= self.editor_tabs.count():
                    return
                editor = self.editor_tabs.widget(index)
                
                # Find filename
                for path, data in self.editor_files.items():
                    if data.get('editor') == editor:
                        filename_to_close = path
                        break
            else:
                # ✅ FIXED: Handle H/V mode properly
                if not isinstance(self.editor_tabs, list):
                    return
                
                # Find which tab widget contains the tab at this index
                for tab_widget in self.editor_tabs:
                    if tab_widget and 0 <= index < tab_widget.count():
                        editor = tab_widget.widget(index)
                        # Find filename
                        for path, data in self.editor_files.items():
                            if data.get('editor') == editor:
                                filename_to_close = path
                                break
                        break
            
            if not filename_to_close:
                return

            # Confirm save if modified
            if self.editor_files[filename_to_close].get('modified', False):
                reply = QMessageBox.question(
                    self.main_window,
                    "Unsaved Changes",
                    f"Do you want to save changes to {os.path.basename(filename_to_close)}?",
                    QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
                )
                if reply == QMessageBox.Save:
                    if not self.save_file(filename_to_close):
                        return
                elif reply == QMessageBox.Cancel:
                    return

            # ✅ FIXED: Remove from tab_order
            if hasattr(self, 'tab_order') and filename_to_close in self.tab_order:
                self.tab_order.remove(filename_to_close)

            # Remove from UI and cleanup
            if mode == "tabbed":
                self.editor_tabs.removeTab(index)
            else:
                # Find and remove the tab widget
                for tab_widget in self.editor_tabs[:]:  # ✅ Copy to avoid modification during iteration
                    if tab_widget and tab_widget.indexOf(editor) != -1:
                        tab_widget.setParent(None)
                        try:
                            self.editor_tabs.remove(tab_widget)
                        except ValueError:
                            pass
                        break

            # Cleanup file data
            if filename_to_close in self.editor_files:
                
                # Clean up spell checker resources for this editor
                if hasattr(self.main_window, 'spell_checker') and editor:
                    self.main_window.spell_checker.cleanup_editor(editor)
                
                self.file_watcher.unwatch(filename_to_close)
                
                del self.editor_files[filename_to_close]
                
            if filename_to_close == self.current_file:
                self.current_file = None
                # ✅ FIXED: Set current_file to remaining editor if any
                if self.editor_files:
                    self.current_file = next(iter(self.editor_files.keys()))
                self.main_window.update_title()

            # ✅ FIXED: Show welcome only if no editors remain
            if len(self.editor_files) == 0:
                # Also check for remaining tool tabs
                remaining_tool_tabs = False
                if mode == "tabbed" and self.editor_tabs:
                    for i in range(self.editor_tabs.count()):
                        if self.editor_tabs.tabText(i) in tool_tab_names:
                            remaining_tool_tabs = True
                            break
                
                # Only show welcome if no tool tabs remain either
                if not remaining_tool_tabs:
                    if mode == "tabbed":
                        if hasattr(self.main_window, 'layout_manager'):
                            QTimer.singleShot(50, self.main_window.layout_manager._recreate_editor_container)
                    else:
                        # Clear all widgets and show single welcome
                        if hasattr(self, 'editor_splitter') and self.editor_splitter:
                            for i in reversed(range(self.editor_splitter.count())):
                                widget = self.editor_splitter.widget(i)
                                widget.setParent(None)
                        self._add_single_welcome_tab(self.editor_splitter, mode)
            
        except Exception as e:
            print(f"Error closing editor tab: {e}")
            import traceback
            traceback.print_exc()
        

#########
    def _apply_welcome_tab_theme(self, widget):
        """Re-style the welcome widget in place without rebuilding it."""
        from style_manager import get_welcome_style
        w = get_welcome_style()
        widget.setStyleSheet(f"background-color: {w['outer_bg']};")
        # Walk children and update labels/buttons as needed
        for child in widget.findChildren(QLabel):
            child.setStyleSheet(f"color: {w.get('text_color', '')};")
            
    def _create_editor_welcome_widget(self):
        """Create a Krita-style welcome widget for the LaTeX editor"""
        from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                                      QScrollArea, QFrame, QSizePolicy)
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QCursor, QFont
        
        # Main container
        welcome_widget = QWidget()
        welcome_widget.setObjectName("editor_welcome_widget")
        
        
        
        main_layout = QVBoxLayout(welcome_widget)
        main_layout.setContentsMargins(50, 50, 50, 50)
        main_layout.setSpacing(15)
        
        # Add stretch at top for vertical centering
        main_layout.addStretch(1)
        
        # Actions container (centered)
        actions_container = QWidget()
        actions_container.setMaximumWidth(400)
        actions_layout = QVBoxLayout(actions_container)
        actions_layout.setSpacing(12)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        
        # Get icons manager
        icons_manager = None
        if hasattr(self.main_window, 'menu_manager') and hasattr(self.main_window.menu_manager, 'icons_manager'):
            icons_manager = self.main_window.menu_manager.icons_manager
        
        # Item 1: New File
        new_file_item = self._create_welcome_action_item(
            icons_manager, "new", 
            "New File", "Ctrl+N",
            self.new_file
        )
        actions_layout.addWidget(new_file_item)
        
        # Item 2: Open File
        open_file_item = self._create_welcome_action_item(
            icons_manager, "open",
            "Open File", "Ctrl+O", 
            self.open_file
        )
        actions_layout.addWidget(open_file_item)
        
        # Separator line
        actions_layout.addSpacing(10)
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #ccc; max-height: 1px;")
        actions_layout.addWidget(separator)
        actions_layout.addSpacing(5)
        
        # Item 3: Recent Files header (bold)
        recent_header = QLabel("<b>Recent Files:</b>")
        recent_header.setStyleSheet("font-size: 13px; color: #333; padding-left: 5px;")
        actions_layout.addWidget(recent_header)
        
        # Recent files list (scrollable)
        recent_scroll = self._create_editor_recent_files_list()
        actions_layout.addWidget(recent_scroll)
        
        # Center the actions container horizontally
        h_layout = QHBoxLayout()
        h_layout.addStretch(1)
        h_layout.addWidget(actions_container)
        h_layout.addStretch(1)
        main_layout.addLayout(h_layout)
        
        # Add stretch at bottom for vertical centering
        main_layout.addStretch(1)
        
        welcome_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        return welcome_widget


    def _create_welcome_action_item(self, icons_manager, icon_name, text, shortcut, callback):
        """Create a clickable action item with icon, underlined text, and shortcut"""
        from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QCursor
        
        item_widget = QWidget()
        item_widget.setCursor(QCursor(Qt.PointingHandCursor))
        item_widget.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border-radius: 4px;
                padding: 5px;
            }
            QWidget:hover {
                background-color: #e8f4fc;
            }
        """)
        
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(8, 6, 8, 6)
        item_layout.setSpacing(10)
        
        # Icon
        icon_label = QLabel()
        icon_label.setFixedSize(20, 20)
        if icons_manager:
            icon = False # icons_manager.load_icon(icon_name)
            if icon and not icon.isNull():
                pixmap = icon.pixmap(20, 20)
                icon_label.setPixmap(pixmap)
        item_layout.addWidget(icon_label)
        
        # Text (underlined, clickable style)
        text_label = QLabel(f'<a style="color: #0066cc; text-decoration: underline;">{text}</a>')
        text_label.setStyleSheet("font-size: 13px;")
        item_layout.addWidget(text_label)
        
        # Shortcut (grayed)
        shortcut_label = QLabel(f"({shortcut})")
        shortcut_label.setStyleSheet("font-size: 11px; color: #888;")
        item_layout.addWidget(shortcut_label)
        
        item_layout.addStretch()
        
        # Make entire widget clickable
        def on_click(event):
            callback()
        item_widget.mousePressEvent = on_click
        
        return item_widget

    
    def _create_editor_recent_files_list(self):
        """Create a scrollable list of recent .tex files - simple styling"""
        from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea, QHBoxLayout, QFrame
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QCursor
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(180)
        scroll_area.setMinimumHeight(80)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")
        
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(4)
        
        # Get recent files
        recent_files = []
        if hasattr(self.main_window, 'config_manager'):
            recent_files = self.main_window.config_manager.get_recent_files()[:101]
        
        if not recent_files:
            no_files_label = QLabel("No recent files")
            no_files_label.setStyleSheet("color: #888; font-style: italic; background-color: transparent;")
            layout.addWidget(no_files_label)
        else:
###

            for file_path in recent_files:
                if not os.path.exists(file_path):
                    continue

                row = QWidget()
                row.setStyleSheet("background-color: transparent;")
                row_layout = QHBoxLayout(row)
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.setSpacing(4)

                file_label = QLabel(f'<a href="#" style="color: #0066cc;">{os.path.basename(file_path)}</a>')
                file_label.setCursor(QCursor(Qt.PointingHandCursor))
                file_label.setToolTip(file_path)
                file_label.setStyleSheet("background-color: transparent;")

                def make_click_handler(path):
                    def handler(event):
                        self.main_window.editor_manager.open_specific_file(path)
                    return handler

                file_label.mousePressEvent = make_click_handler(file_path)

                remove_btn = QPushButton("⨉")
                remove_btn.setFlat(True)
                remove_btn.setCursor(QCursor(Qt.PointingHandCursor))
                remove_btn.setToolTip("Remove from recent files")
                remove_btn.setFixedSize(18, 18)
                remove_btn.setStyleSheet(
                    "QPushButton { color: #999; background: transparent; border: none; font-size: 11px; }"
                    "QPushButton:hover { color: #cc0000; }"
                )

                def make_remove_handler(path, r):
                    def handler():
                        if hasattr(self.main_window, 'config_manager'):
                            self.main_window.config_manager.remove_recent_file(path)
                        # Rebuild the panel
                        parent = r.parentWidget()
                        if parent:
                            parent.layout().removeWidget(r)
                            r.deleteLater()
                    return handler

                remove_btn.clicked.connect(make_remove_handler(file_path, row))

                row_layout.addWidget(file_label)
                row_layout.addStretch()
                row_layout.addWidget(remove_btn)
                layout.addWidget(row)                
                
###        
        layout.addStretch()
        scroll_area.setWidget(container)
        return scroll_area

    def _add_single_welcome_tab(self, tab_widget, mode):
        """Add a single Krita-style welcome tab to the editor"""
        if not tab_widget:
            return
            
        # Remove any existing welcome tabs first
        for i in reversed(range(tab_widget.count())):
            if tab_widget.tabText(i) in ["Welcome", "Latex Editor"]:
                tab_widget.removeTab(i)
        
        # Create the Krita-style welcome widget
        welcome_widget = self.main_window.layout_manager._create_editor_welcome_content()
        welcome_widget.setObjectName("editor_welcome_widget")
        
        # Add with new title "Latex Editor"
        tab_widget.addTab(welcome_widget, "Latex Editor")
        tab_widget.setTabsClosable(False)
        tab_widget.setCurrentIndex(tab_widget.count() - 1)

    def _remove_welcome_tabs_if_needed(self):
        """Remove welcome tabs when adding real content"""
        try:
            mode = self.editor_layout_mode
            if mode == "tabbed":
                if isinstance(self.editor_tabs, QTabWidget):
                    for i in reversed(range(self.editor_tabs.count())):
                        tab_text = self.editor_tabs.tabText(i)
                        # Check for both old and new welcome tab names
                        if tab_text in ["Welcome", "Latex Editor"]:
                            self.editor_tabs.removeTab(i)
                            self.editor_tabs.setTabsClosable(True)  # Enable closing for real tabs
            else:
                if isinstance(self.editor_tabs, list):
                    for tab_widget in self.editor_tabs[:]:  # Copy list
                        if tab_widget and isinstance(tab_widget, QTabWidget):
                            welcome_only = True
                            for j in range(tab_widget.count()):
                                tab_text = tab_widget.tabText(j)
                                if tab_text not in ["Welcome", "Latex Editor"]:
                                    welcome_only = False
                                    break
                            if welcome_only:
                                tab_widget.setParent(None)
                                try:
                                    self.editor_tabs.remove(tab_widget)
                                except ValueError:
                                    pass
                            else:
                                # Remove only welcome tabs from mixed widgets
                                for j in reversed(range(tab_widget.count())):
                                    tab_text = tab_widget.tabText(j)
                                    if tab_text in ["Welcome", "Latex Editor"]:
                                        tab_widget.removeTab(j)
        except Exception as e:
            print(f"Error removing welcome tabs: {e}")
        

    def update_current_file_from_editor(self, editor):
        """Update current file when editor gets focus - FIXED for H/V mode"""
        for path, data in self.editor_files.items():
            if data['editor'] == editor:
                old_current = self.current_file
                self.current_file = path
                
                # In H/V mode, update active tab widget index
                if self.editor_layout_mode != "tabbed":
                    tab_widget_index = data.get('tab_widget_index', 0)
                    self._active_tab_widget_index = tab_widget_index
                    
                # ✅ Highlight the active editor border
                self._highlight_active_editor(editor)                
                
                # ✅ FIX: Only update title if file actually changed
                if old_current != path:
                    self.main_window.update_title()
                return

    
    def get_current_editor(self):
        """Get current editor widget - FIXED for H/V mode"""
        if self.editor_layout_mode == "tabbed":
            if self.editor_tabs and not isinstance(self.editor_tabs, list):
                return self.editor_tabs.currentWidget()
        else:
            # H/V mode - use current_file to find the correct editor
            if self.current_file and self.current_file in self.editor_files:
                data = self.editor_files[self.current_file]
                editor = data.get('editor')
                if editor and hasattr(editor, 'toPlainText'):
                    return editor
            
            # Fallback: use active tab widget index
            if isinstance(self.editor_tabs, list):
                active_index = getattr(self, '_active_tab_widget_index', 0)
                if 0 <= active_index < len(self.editor_tabs):
                    tab_widget = self.editor_tabs[active_index]
                    if tab_widget and tab_widget.count() > 0:
                        current_widget = tab_widget.currentWidget()
                        if hasattr(current_widget, 'toPlainText'):
                            return current_widget
                
                # Final fallback
                for tab_widget in self.editor_tabs:
                    if tab_widget and tab_widget.currentWidget():
                        current_widget = tab_widget.currentWidget()
                        if hasattr(current_widget, 'toPlainText'):
                            return current_widget
        
        return None
    


    def open_file(self):
        """Open a LaTeX file - with consistent path handling"""
        try:
            lang = self.main_window.menu_language
            translations = self.main_window.translations[lang]
            title = translations.get("open", "Open LaTeX File")
            
            # ✅ FIX: Get the directory of the current file using proper method
            default_dir = ""
            current_file = self.get_current_file_path()  # Use the proper method
            if current_file and os.path.exists(current_file):
                default_dir = os.path.dirname(current_file)
                #print(f"📁 Opening dialog in current file's directory: {default_dir}")
            elif hasattr(self, 'last_opened_directory') and self.last_opened_directory:
                default_dir = self.last_opened_directory
                #print(f"📁 Opening dialog in last opened directory: {default_dir}")
            else:
                default_dir = os.path.expanduser("~")
                #print(f"📁 Opening dialog in home directory: {default_dir}")
            
            paths, _ = QFileDialog.getOpenFileNames(
                self.main_window,
                title,
                default_dir,
                "LaTeX Files (*.tex);;All Files (*)"
            )

            if not paths:
                return


            # Create progress dialog only if multiple files
            progress = None
            
            if len(paths) > 3:
                progress = QProgressDialog(
                    "Opening files...",
                    "Cancel",
                    0,
                    len(paths),
                    self.main_window
                )
                progress.setWindowTitle("Opening files, please wait...")                
                progress.setMinimumWidth(400)
                progress.setWindowModality(Qt.WindowModal)
                progress.show()
                
            opened_count = 0

            
            for i, path in enumerate(paths):
                if progress and progress.wasCanceled():
                    break
            
                path = self.normalize_path(path)
                #print(f"🔍 Opening file: {path}")

               
                try: 
                    # Check if already open
                    existing_path = self._find_open_file(path)

                    if existing_path:
                        if self._switch_to_existing_file(existing_path):
                            self.current_file = existing_path
                    else:
                        # Open new file
                        self._open_new_file(path)
                        
                    opened_count += 1
                    
                    if progress:
                        progress.setValue(i + 1)
                        progress.setLabelText(f"Opening {os.path.basename(path)}")
                        QApplication.processEvents()  # 👈 IMPORTANT                
                
                except Exception as e:
                    print(f"❌ Error opening {path}: {e}") 
                    
                # Update history/session
                self._add_to_recent_files(path)
                self._add_to_session_files(path)

            if progress:
                progress.close()

            # Final UI update
            if opened_count > 0:
                self.main_window.update_title()

            self.main_window.update_title()
            
        except Exception as e:
            print(f"❌ Error opening file: {e}")
            QMessageBox.critical(self.main_window, "Error", f"Could not open file: {str(e)}")


    def open_specific_file(self, path):
        """Open a specific file - with consistent path handling and proper tracking"""
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import Qt

        if not path:
            return

        # Show wait cursor immediately
        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()

        try:
            # Use consistent path normalization
            path = self.normalize_path(path)
            
            # Store the directory for future new files
            self.last_opened_directory = os.path.dirname(path)
            
            # Ensure editor_tabs is initialized
            self._ensure_editor_tabs_initialized()
            
            # Check if already open
            existing_path = self._find_open_file(path)
            if existing_path:
                if self._switch_to_existing_file(existing_path):
                    self.current_file = existing_path
                    self.main_window.update_title()
                    self._add_to_recent_files(path)
                    self._add_to_session_files(path)
                    return
            
            # Open new file
            self._open_new_file(path)
            
            if self.editor_layout_mode != "tabbed" and path in self.editor_files:
                self._active_tab_widget_index = self.editor_files[path].get('tab_widget_index', 0)
        finally:
            # Always restore cursor, even if an error occurs
            QApplication.restoreOverrideCursor()        

        
    def _ensure_editor_tabs_initialized(self):
        """Ensure editor_tabs is properly initialized based on layout mode"""
        if self.editor_tabs is not None:
            return  # Already initialized
        
        #print(f"🔧 Initializing editor_tabs for mode: {self.editor_layout_mode}")
        
        if self.editor_layout_mode == "tabbed":
            # Create single QTabWidget for tabbed mode
            self.editor_tabs = QTabWidget()
            self.editor_tabs.setTabsClosable(True)
            self.editor_tabs.tabCloseRequested.connect(self.close_editor_tab)
            
            # Optional: Add context menu, drag-drop, etc.
            if hasattr(self, 'setup_tab_features'):
                self.setup_tab_features(self.editor_tabs)
            
            #print("✅ Initialized tabbed mode editor_tabs")
            
        elif self.editor_layout_mode in ["horizontal", "vertical"]:
            # Create list of QTabWidgets for H/V split mode
            self.editor_tabs = [None, None]  # Two panes for split mode
            
            # You might want to create the actual tab widgets here
            # depending on your implementation
            for i in range(2):
                tab_widget = QTabWidget()
                tab_widget.setTabsClosable(True)
                tab_widget.tabCloseRequested.connect(
                    lambda index, pane=i: self.close_editor_tab(index, pane)
                )
                self.editor_tabs[i] = tab_widget
            
            #print(f"✅ Initialized {self.editor_layout_mode} mode editor_tabs")
            
        else:
            # Unknown mode, default to tabbed
            #print(f"⚠️ Unknown layout mode '{self.editor_layout_mode}', defaulting to tabbed")
            self.editor_layout_mode = "tabbed"
            self.editor_tabs = QTabWidget()
            self.editor_tabs.setTabsClosable(True)
            self.editor_tabs.tabCloseRequested.connect(self.close_editor_tab)


    @staticmethod
    def _read_file_robust(path: str) -> str:
        """Read a file trying UTF-8, then UTF-8-with-replacement, then Latin-1.
        Raises OSError on real I/O failures; never raises on encoding errors."""
        for encoding, errors in [('utf-8', 'strict'),
                                  ('utf-8', 'replace'),
                                  ('latin-1', 'replace')]:
            try:
                with open(path, 'r', encoding=encoding, errors=errors) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        with open(path, 'rb') as f:
            return f.read().decode('latin-1', errors='replace')

    def _open_new_file(self, path):
        try:
            content = self._read_file_robust(path)

    # def _open_new_file(self, path):
        # try:
            # with open(path, 'r', encoding='utf-8') as f:
                # content = f.read()

            self.last_opened_directory = os.path.dirname(path)
            pdf_path = os.path.splitext(path)[0] + ".pdf"

            editor = self.create_new_editor_tab(path, pdf_path, content)
            if not editor:
                return

            if hasattr(self.main_window, 'is_rtl'):
                alignment = Qt.AlignRight if self.main_window.is_rtl else Qt.AlignLeft
                editor.setAlignment(alignment)

            # Reset cursor and scroll
            cursor = editor.textCursor()
            cursor.movePosition(QTextCursor.Start)
            editor.setTextCursor(cursor)
            editor.verticalScrollBar().setValue(0)
            editor.ensureCursorVisible()

            self.current_file = path
            self.main_window.update_title()
            self._add_to_recent_files(path)

        except Exception as e:
            print(f"❌ Error opening new file: {e}")
            QMessageBox.critical(self.main_window, "Open Error", str(e))

        
    def normalize_path(self, path):
        """Normalize file path for consistent comparison - preserves original case"""
        if not path:
            return path
        
        # Convert to absolute path
        abs_path = os.path.abspath(path)
        
        # Normalize path separators (\ to / or vice versa)
        normalized = os.path.normpath(abs_path)
        
        # ✅ DON'T use os.path.normcase() - it converts to lowercase on Windows
        # We want to preserve the original filename case for display purposes
        # Path comparison should be done case-insensitively in a separate function
        
        return normalized

       
    
    def get_session_files(self, count=100):  # Add default parameter
        """Get session files for restoration on startup"""
        session_files = []
        if 'session_files' in self.main_window.config_manager.config:
            for i in range(1, count + 1):
                key = f'file_{i}'
                path = self.main_window.config_manager.config.get('session_files', key, fallback='').strip()
                if path and os.path.exists(path) and os.path.isfile(path):
                    path = os.path.abspath(path)
                    session_files.append(path)
        return session_files

    
    def _add_to_session_files(self, file_path):
        """Add file to session files with consistent path handling"""
        if not file_path:
            return
        
        # Normalize the path
        normalized_path = self.normalize_path(file_path)
        #print(f"🔄 Adding to session: {normalized_path}")
        
        # Get current session files
        session_files = self.get_session_files(50)
        # Remove existing entry (case-insensitive on Windows)
        session_files = [f for f in session_files 
                        if self.normalize_path(f) != normalized_path]
        
        # Add to front
        session_files.insert(0, normalized_path)
        
        # Limit to max files
        max_session_files = 100  # or whatever your limit is
        session_files = session_files[:max_session_files]
        
        # Save back
        self.main_window.config_manager.save_session_files(session_files)
        #print(f"📋 Updated session files: {len(session_files)} files")
    


        
    def _find_open_file(self, target_path):
        """Find if a file is already open - with consistent path normalization"""
        target_path = self.normalize_path(target_path)
        #print(f"🔍 Looking for: {target_path}")
        #print(f"📁 Open files: {list(self.editor_files.keys())}")
        
        for open_path in self.editor_files:
            normalized_open_path = self.normalize_path(open_path)
            #print(f"  Comparing: {normalized_open_path}")
            
            if normalized_open_path == target_path:
                #print(f"  ✅ Found match!")
                return open_path
        
        #print(f"  ❌ No match found")
        return None

   
    def _switch_to_existing_file(self, existing_path):
        """Switch to an already open file with robust tab switching"""
        try:
            data = self.editor_files[existing_path]
            editor = data['editor']
            
            if self.editor_layout_mode == "tabbed":
                if self.editor_tabs and self.editor_tabs.count() > 0:
                    # Find the actual current index of the editor
                    actual_index = self._find_tab_index_by_editor(self.editor_tabs, editor)
                    if actual_index != -1:
                        self.editor_tabs.setCurrentIndex(actual_index)
                        editor.setFocus()
                        # Update stored index if it was wrong
                        data['index'] = actual_index
                    else:
                        #print(f"⚠️ Could not find tab for editor in tabbed mode")
                        return False
            else:
                # H/V mode: editor_tabs is a list of QTabWidgets
                # Update active tab widget index
                self._active_tab_widget_index = data['tab_widget_index']
                if isinstance(self.editor_tabs, list) and data['tab_widget_index'] < len(self.editor_tabs):
                    tab_widget = self.editor_tabs[data['tab_widget_index']]
                    if tab_widget and tab_widget.count() > 0:
                        # Find actual index in this tab widget
                        actual_index = self._find_tab_index_by_editor(tab_widget, editor)
                        if actual_index != -1:
                            tab_widget.setCurrentIndex(actual_index)
                            editor.setFocus()
                            # Update stored index if it was wrong
                            data['index'] = actual_index
                        else:
                            print(f"⚠️ Could not find tab for editor in H/V mode")
                            return False
            
            return True
        except Exception as e:
            print(f"❌ Error switching to existing file: {e}")
            return False

    def _find_tab_index_by_editor(self, tab_widget, target_editor):
        """Find the actual tab index containing a specific editor"""
        if not tab_widget:
            return -1
            
        for i in range(tab_widget.count()):
            widget = tab_widget.widget(i)
            # Direct comparison
            if widget == target_editor:
                return i
            # If editor is wrapped in another widget, check children
            if hasattr(widget, 'findChild'):
                if widget.findChild(type(target_editor)) == target_editor:
                    return i
        
        return -1
        
   
    
    def _add_to_recent_files(self, file_path):
        """Add file to recent files list and update UI immediately"""
        if not file_path or not hasattr(self.main_window, 'config_manager'):
            return
        
        try:
            # Add to config manager's recent files
            self.main_window.config_manager.add_recent_file(file_path)
            
            # Update any open settings dialogs immediately
            self._update_recent_files_ui()
            
        except Exception as e:
            print(f"❌ Error adding to recent files: {e}")
            import traceback
            traceback.print_exc()
    
    def _update_recent_files_ui(self):
        """Update recent files display in any open settings dialogs"""
        try:
            # Find any open settings dialogs and update their recent files display
            for widget in QApplication.allWidgets():
                if hasattr(widget, 'recent_list') and hasattr(widget, 'load_recent_files_display'):
                    widget.load_recent_files_display()
        except Exception as e:
            print(f"❌ Error updating recent files UI: {e}")

            
    def _find_open_file(self, target_path):
        """Find if a file is already open, return the key if found - NEW METHOD"""
        target_path = os.path.abspath(target_path)
        
        for existing_path in self.editor_files.keys():
            if os.path.abspath(existing_path) == target_path:
                # Verify the editor widget still exists
                data = self.editor_files[existing_path]
                editor = data['editor']
                
                if self.editor_layout_mode == "tabbed":
                    # Check if widget is still in the tab widget
                    if self.editor_tabs.indexOf(editor) >= 0:
                        return existing_path
                    else:
                        #print(f"🗑️ Found orphaned entry for {os.path.basename(existing_path)}")
                        return None  # Will be cleaned up by caller
                else:
                    return existing_path
        
        return None
        
        
    def get_current_file_path(self):
        """Get the currently active file path"""
        try:
            # Method 1: Use stored current_file
            if self.current_file and os.path.exists(self.current_file):
                #print(f"📍 Current file from stored: {self.current_file}")
                return self.current_file
            
            # Method 2: Get from active tab
            if self.editor_layout_mode == "tabbed" and self.editor_tabs:
                if isinstance(self.editor_tabs, QTabWidget) and self.editor_tabs.count() > 0:
                    current_index = self.editor_tabs.currentIndex()
                    current_widget = self.editor_tabs.widget(current_index)
                    
                    # Find the file path for this editor widget
                    for file_path, editor_data in self.editor_files.items():
                        if editor_data.get('editor') == current_widget:
                            #print(f"📍 Current file from active tab: {file_path}")
                            self.current_file = file_path  # Update stored current_file
                            return file_path
            
            # Method 3: Get first available file
            if self.editor_files:
                first_file = list(self.editor_files.keys())[0]
                #print(f"📍 Using first available file as current: {first_file}")
                self.current_file = first_file
                return first_file
            
            #print("📍 No current file found")
            return None
            
        except Exception as e:
            #filename = f"Manuscript-{timestamp}.tex"
            print(f"❌ Error getting current file: {e}")
            return None
    
    
    def new_file(self):
        """Create a new file with timestamp-based naming - triggers Save As on first save"""
        from datetime import datetime
        
        # Generate filename with current timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S.%f")
        base_filename = f"Manuscript-{timestamp}"
        filename = f"{base_filename}.tex"
        
        # Get a directory to use (prefer last opened directory or use home)
        if hasattr(self, 'last_opened_directory') and self.last_opened_directory:
            base_dir = self.last_opened_directory
        else:
            base_dir = os.path.expanduser("~")  # Use home directory
        
        # Create full path (but DON'T create the file on disk yet)
        path = os.path.join(base_dir, filename)
        
        # Ensure unique filename if file already exists
        counter = 1
        while os.path.exists(path) or path in self.editor_files:
            filename = f"{base_filename}-{counter}.tex"
            path = os.path.join(base_dir, filename)
            counter += 1
        
        # Normalize path
        path = self.normalize_path(path)
        
        # Create the editor tab with initial content
        # NOTE: We do NOT create the file on disk - it will be created when user saves
        editor = self.create_new_editor_tab(
            path, 
            None, 
            "\\documentclass{article}\n\\begin{document}\n\n\\end{document}"
        )
        
        if editor:
            # Mark as modified since it's new and unsaved
            self.editor_files[path]['modified'] = True
            self.editor_files[path]['is_new_file'] = True  # Flag to track new files
            self.current_file = path
            self.main_window.update_title()
            self.update_editor_display(path)
            
            #print(f"✅ Created new file (not saved yet): {filename}")

            
    def save_file(self, path=None):
        """Save the current file - triggers Save As for new files"""
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]                            
        
        current_editor = self.get_current_editor()
        current_file = self.get_current_file_path()
        
        if not current_editor or not current_file:
            self.show_error(tr["no_file_open"], tr["open_a_latex_file"])
            return
        
        # Determine which file to save
        if not path:
            path = self.current_file
        
        # Validate path
        if not path:
            #print("❌ No file path specified")
            return self.save_file_as()  # Trigger Save As if no path
        
        # Normalize path
        path = self.normalize_path(path)
        
        # Get editor data
        editor_data = self.editor_files.get(path)
        if not editor_data:
            #print(f"❌ No editor data found for: {path}")
            return self.save_file_as()  # Trigger Save As as fallback
        
        # ✅ FIX: Check if this is explicitly marked as a new file
        is_new_file = editor_data.get('is_new_file', False)
        
        # ✅ FIX: Only trigger Save As if explicitly marked as new file
        # Don't check os.path.exists() here - if we're saving, the path should be valid
        if is_new_file:
            #print(f"📝 New file detected, triggering Save As: {os.path.basename(path)}")
            return self.save_file_as()
        
        editor = editor_data.get('editor')
        if not editor:
            #print(f"❌ No editor widget found for: {path}")
            return False
        
        try:
            # Get content from editor
            content = editor.toPlainText()
            normalized = content.replace('\r\n', '\n').replace('\r', '\n')
            
            # Ensure directory exists
            directory = os.path.dirname(path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)


            self.file_watcher.pause(path)
            # Write file
            with open(path, 'w', encoding='utf-8') as f:
                f.write(normalized)
            self.file_watcher.resume(path)
            
            # Update editor data
            self.editor_files[path]['saved_content'] = normalized
            self.editor_files[path]['modified'] = False
            self.editor_files[path]['is_new_file'] = False  # ✅ Clear flag after first save
            
            # Update PDF path if needed
            if not self.editor_files[path].get('pdf_path'):
                self.editor_files[path]['pdf_path'] = os.path.splitext(path)[0] + ".pdf"
            
            # Update UI
            self.main_window.update_title()
            self.update_editor_display(path)
            self.main_window.update_status_bar(f"Saved: {os.path.basename(path)}")
            
            # Add to recent files
            self._add_to_recent_files(path)
            
            #print(f"✅ Successfully saved: {os.path.basename(path)}")
            return True
            
        except Exception as e:
            print(f"❌ Save error: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self.main_window, "Save Error", str(e))
            return False
        

    def save_file_as(self):
        """Save file with a new name - improved to handle path updates"""
        
        lang = self.main_window.menu_language
        t = self.main_window.translations[lang]                            
        
        current_editor = self.get_current_editor()
        current_file = self.get_current_file_path()
        
        if not current_editor or not current_file:
            self.show_error(t["no_file_open"], t["open_a_latex_file"])
            return
        
        # Get current file path for default location
        default_dir = ""
        if self.current_file and os.path.exists(self.current_file):
            default_dir = os.path.dirname(self.current_file)
        elif hasattr(self, 'last_opened_directory') and self.last_opened_directory:
            default_dir = self.last_opened_directory
        else:
            default_dir = os.path.expanduser("~")
        
        # Get suggested filename
        if self.current_file:
            suggested_name = os.path.basename(self.current_file)
        else:
            suggested_name = "document.tex"
        
        default_path = os.path.join(default_dir, suggested_name)
        
        file_path, _ = QFileDialog.getSaveFileName(
            self.main_window,
            t.get("save_as", "Save As"),
            default_path,
            "TeX files (*.tex);;All files (*.*)"
        )
        
        if not file_path:
            return False
        
        if not file_path.lower().endswith('.tex'):
            file_path += '.tex'
        
        # Normalize the new path
        file_path = self.normalize_path(file_path)
        
        # Store directory for future use
        self.last_opened_directory = os.path.dirname(file_path)
        
        content = current_editor.toPlainText()
        
        try:
            # Ensure directory exists
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            
            # Write file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            QMessageBox.critical(self.main_window, "Save Error", f"Could not save file: {str(e)}")
            return False
        
        # Update editor_files with new path
        old_key = self.current_file
        if old_key and old_key in self.editor_files:
            data = self.editor_files.pop(old_key)
            data['modified'] = False
            data['saved_content'] = content
            data['pdf_path'] = os.path.splitext(file_path)[0] + ".pdf"
            data['display_name'] = os.path.basename(file_path)
            data['is_new_file'] = False  # Clear the new file flag
            self.editor_files[file_path] = data
            
            # Update tab order
            if hasattr(self, 'tab_order') and old_key in self.tab_order:
                idx = self.tab_order.index(old_key)
                self.tab_order[idx] = file_path
            
            # Update tab display name
            mode = self.editor_layout_mode
            if mode == "tabbed":
                if isinstance(self.editor_tabs, QTabWidget):
                    tab_index = self._find_tab_index_by_editor(self.editor_tabs, current_editor)
                    if tab_index >= 0:
                        self.editor_tabs.setTabText(tab_index, os.path.basename(file_path))
            else:
                # H/V mode
                if isinstance(self.editor_tabs, list):
                    tab_widget_index = data.get('tab_widget_index', 0)
                    if 0 <= tab_widget_index < len(self.editor_tabs):
                        tab_widget = self.editor_tabs[tab_widget_index]
                        if tab_widget:
                            tab_index = self._find_tab_index_by_editor(tab_widget, current_editor)
                            if tab_index >= 0:
                                tab_widget.setTabText(tab_index, os.path.basename(file_path))
        
        self.current_file = file_path
        self.main_window.update_title()
        self.update_editor_display(file_path)
        
        if hasattr(self.main_window, 'config_manager'):
            self.main_window.config_manager.add_recent_file(file_path)
        
        self.main_window.update_status_bar(f"Saved as: {os.path.basename(file_path)}")
        print(f"✅ Saved as: {file_path}")
        
        return True    


    def save_copy_as(self):
        """Save a copy of the current document without changing the active file.
        Automatically suggests a name like 'filename_copy1.tex' based on existing copies.
        """
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]                            
        
        current_editor = self.get_current_editor()
        current_file = self.get_current_file_path()
        
        if not current_editor or not current_file:
            self.show_error(tr["no_file_open"], tr["open_a_latex_file"])
            return       
        
        # Determine default directory and base name
        if self.current_file and os.path.exists(self.current_file):
            default_dir = os.path.dirname(self.current_file)
            base_name = os.path.splitext(os.path.basename(self.current_file))[0]
            extension = ".tex"
        else:
            default_dir = getattr(self, 'last_opened_directory', os.path.expanduser("~"))
            base_name = "document"
            extension = ".tex"

        # Find the next available copy number in the same directory
        copy_number = 1
        while True:
            candidate = os.path.join(default_dir, f"{base_name}_copy{copy_number}{extension}")
            if not os.path.exists(candidate):
                break
            copy_number += 1

        # Suggest the new filename
        suggested_name = f"{base_name}_copy{copy_number}{extension}"
        default_path = os.path.join(default_dir, suggested_name)

        file_path, _ = QFileDialog.getSaveFileName(
            self.main_window,
            "Save a Copy As",
            default_path,
            "TeX files (*.tex);;All files (*.*)"
        )

        if not file_path:
            return

        if not file_path.lower().endswith('.tex'):
            file_path += '.tex'

        # Write the copy without touching the current file data
        try:
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)

            content = current_editor.toPlainText()
            normalized = content.replace('\r\n', '\n').replace('\r', '\n')

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(normalized)

            self.main_window.update_status_bar(f"Copy saved as: {os.path.basename(file_path)}")
        except Exception as e:
            QMessageBox.critical(self.main_window, "Save Copy Error", f"Could not save copy:\n{str(e)}")

    def _manage_session_files_manually(self, file_path, session_files_list):
        """Manually manage session files as fallback"""
        try:
            config_manager = self.main_window.config_manager
            
            # Ensure session_files section exists
            if not config_manager.config.has_section('session_files'):
                config_manager.config.add_section('session_files')
            
            # Clear all existing session files
            for i in range(1, 101):  # Based on your current setup (file_1 to file_50)
                config_manager.config.set('session_files', f'file_{i}', '')
            
            # Write the new list
            for i, path in enumerate(session_files_list, start=1):
                if i <= 100:  # Limit to 100 files based on your current setup
                    config_manager.config.set('session_files', f'file_{i}', path)
            
            # Save the config
            config_manager.save_config()
            #print(f"💾 Successfully saved session files manually")
            
        except Exception as e:
            print(f"❌ Error in manual session file management: {e}")
            import traceback
            traceback.print_exc()

    # Also fix the remaining problematic calls in your code:
    def save_session_on_close(self):
        """Save session when closing - FIXED"""
        try:
            # Save bookmarks first
            if hasattr(self.main_window, 'bookmarks_widget'):
                success = self.main_window.bookmarks_widget.save_bookmarks_to_config()
                if not success:
                    #print("Warning: Bookmark saving failed during session close")
                    pass

            if hasattr(self.main_window, 'config_manager'):
                config_manager = self.main_window.config_manager
                
                # Get list of currently open files
                open_files = list(self.editor_files.keys())
                
                # Save using the correct method
                if hasattr(config_manager, 'save_session_files'):
                    config_manager.save_session_files(open_files)
                    #print(f"💾 Session saved on close with {len(open_files)} files")
                else:                    
                    print("ERROR: save_session_files method not found in config_manager")
        except Exception as e:
            print(f"❌ Error saving session on close: {e}")
            print(f"Error saving session on close with bookmarks: {e}")
            # Don't try the problematic add_recent_file call
    
    def update_current_file_tracking(self, file_path):
        """Update current file tracking when switching files"""
        try:
            if file_path and os.path.exists(file_path):
                abs_path = os.path.abspath(file_path)
                self.current_file = abs_path
                #print(f"📍 Updated current file to: {os.path.basename(abs_path)}")
                
                # Also update in config
                if hasattr(self.main_window, 'config_manager'):
                    config = self.main_window.config_manager.config
                    if not config.has_section('ui'):
                        config.add_section('ui')
                    config.set('ui', 'last_active_file', abs_path)
                    
        except Exception as e:
            print(f"❌ Error updating current file tracking: {e}")
            

    
    def get_all_open_file_paths(self):
        """Return all real currently open files (skip untitled) in order"""
        paths = []
        
        try:
            # Debug: Show what we're working with
            #print(f"🔍 DEBUG: editor_files keys: {list(self.editor_files.keys())}")
            
            if self.editor_layout_mode == "tabbed" and hasattr(self, 'editor_tabs') and self.editor_tabs:
                # Get files in tab order
                for i in range(self.editor_tabs.count()):
                    widget = self.editor_tabs.widget(i)
                    if not widget:
                        continue
                        
                    # Find the file path for this widget
                    for path, data in self.editor_files.items():
                        if (data.get('editor') == widget and 
                            path and 
                            not path.startswith("untitled_") and
                            os.path.exists(path)):
                            paths.append(os.path.abspath(path))
                            break
            else:
                # Fallback: get all real files
                for path, data in self.editor_files.items():
                    if (path and 
                        not path.startswith("untitled_") and 
                        os.path.exists(path)):
                        paths.append(os.path.abspath(path))
            
            # Remove duplicates while preserving order
            seen = set()
            unique_paths = []
            for path in paths:
                if path not in seen:
                    seen.add(path)
                    unique_paths.append(path)
            
            #print(f"🔍 DEBUG: Found {len(unique_paths)} open files")
            return unique_paths
            
        except Exception as e:
            print(f"❌ Error in get_all_open_file_paths: {e}")
            import traceback
            traceback.print_exc()
            return []
        

    def mark_current_file_modified(self):
        """Mark current file as modified - can be called directly without signal context"""
        if not self.current_file or self.current_file not in self.editor_files:
            print("⚠️ mark_current_file_modified: No current file")
            return
        
        try:
            data = self.editor_files[self.current_file]
            editor = data.get('editor')
            if not editor:
                return
            
            # Get current and saved content
            current_content = editor.toPlainText()
            saved_content = data.get('saved_content', '')
            
            # Normalize line endings for comparison
            current_normalized = current_content.replace('\r\n', '\n').replace('\r', '\n')
            saved_normalized = saved_content.replace('\r\n', '\n').replace('\r', '\n')
            
            # Check if modified
            is_modified = (current_normalized != saved_normalized)
            old_modified = data.get('modified', False)
            
            if old_modified != is_modified:
                data['modified'] = is_modified
                #print(f"📝 File {os.path.basename(self.current_file)} modified state: {is_modified}")
                
                # Update tab title
                self._update_tab_title(self.current_file, is_modified)
                
                # Update window title
                if hasattr(self.main_window, 'update_title'):
                    self.main_window.update_title()
            
            # Invalidate autocomplete cache
            if hasattr(self.main_window, 'latex_completer_manager'):
                try:
                    self.main_window.latex_completer_manager.invalidate_refcite_cache()
                except:
                    pass
                    
        except Exception as e:
            print(f"❌ Error in mark_current_file_modified: {e}")
        
            
    def on_text_changed(self):
        """Handle text changes - FIXED to prevent name corruption and ensure proper signals"""
        try:
            if self._loading_file:
                return
            
            # Get the document that emitted the signal
            from PyQt5.QtCore import QObject
            
            # Try to get sender from Qt signal context
            sender_obj = self.sender() if hasattr(self, 'sender') else None
            document = None
            
            if sender_obj and hasattr(sender_obj, 'document'):
                # If sender is an editor widget
                document = sender_obj.document()
            elif sender_obj:
                # If sender is the document itself
                document = sender_obj
            else:
                # Fallback: find the currently focused editor
                for filename, data in self.editor_files.items():
                    editor = data.get('editor')
                    if editor and editor.hasFocus():
                        document = editor.document()
                        break
            
            if not document:
                return
                
            editor = None
            target_file = None
            
            # Find the editor that owns this document
            for filename, data in self.editor_files.items():
                if data.get('editor') and data['editor'].document() == document:
                    editor = data['editor']
                    target_file = filename
                    break
                    
            if not editor or not target_file:
                print("Could not find editor for document change")
                return

            # ✅ FIX: Skip modification tracking if editor is in folding operation
            if getattr(editor, '_folding_in_progress', False):
                return
            
            
            # Get current and saved content
            current_content = editor.toPlainText()
            saved_content = self.editor_files[target_file].get('saved_content', '')
            
            # Normalize line endings for comparison
            current_normalized = current_content.replace('\r\n', '\n').replace('\r', '\n')
            saved_normalized = saved_content.replace('\r\n', '\n').replace('\r', '\n')
            
            # Check if modified
            is_modified = (current_normalized != saved_normalized)
            
            # Update if modification state changed
            old_modified = self.editor_files[target_file].get('modified', False)
            if old_modified != is_modified:
                self.editor_files[target_file]['modified'] = is_modified
                #print(f"📝 File {os.path.basename(target_file)} modified state: {is_modified}")
                
                # Update tab title
                self._update_tab_title(target_file, is_modified)
                
                # Update window title if this is the current file
                if target_file == self.current_file:
                    self.main_window.update_title()

            # Notify autocomplete manager of changes
            if hasattr(self.main_window, 'latex_completer_manager'):
                self.main_window.latex_completer_manager.invalidate_refcite_cache()
                # Invalidate ref/cite cache
            try:
                if hasattr(self.main_window, 'latex_completer_manager'):
                    lcm = self.main_window.latex_completer_manager
                    if lcm:
                        lcm.invalidate_refcite_cache()
            except Exception as e:
                pass  # Silently ignore - don't spam console
            
        except Exception as e:
            print(f"❌ Error in on_text_changed: {e}")
            import traceback
            traceback.print_exc()


    def _update_tab_title(self, file_path, is_modified):
        """Update tab title with modified indicator"""
        if not file_path or file_path not in self.editor_files:
            return
        
        try:
            data = self.editor_files[file_path]
            editor = data.get('editor')
            
            if not editor:
                return
            
            # Get display name
            display_name = os.path.basename(file_path)
            if is_modified:
                display_name = "*" + display_name
            
            # Update tab text based on layout mode
            mode = self.editor_layout_mode
            
            if mode == "tabbed":
                if isinstance(self.editor_tabs, QTabWidget):
                    tab_index = self._find_tab_index_by_editor(self.editor_tabs, editor)
                    if tab_index >= 0:
                        self.editor_tabs.setTabText(tab_index, display_name)
                        #print(f"✅ Updated tab title: {display_name}")
            else:
                # H/V mode
                if isinstance(self.editor_tabs, list):
                    tab_widget_index = data.get('tab_widget_index', 0)
                    if 0 <= tab_widget_index < len(self.editor_tabs):
                        tab_widget = self.editor_tabs[tab_widget_index]
                        if tab_widget:
                            tab_index = self._find_tab_index_by_editor(tab_widget, editor)
                            if tab_index >= 0:
                                tab_widget.setTabText(tab_index, display_name)
                                #print(f"✅ Updated tab title: {display_name}")
            
        except Exception as e:
            print(f"⚠️ Error updating tab title: {e}")

    
    def update_editor_display(self, path):
        """Update tab display name with modified indicator"""
        if not path or path not in self.editor_files:
            return
        
        try:
            data = self.editor_files[path]
            is_modified = data.get('modified', False)
            
            # Use the helper method
            self._update_tab_title(path, is_modified)
            
        except Exception as e:
            print(f"⚠️ Error updating editor display: {e}")
            
                
    def load_template(self):
        """Load LaTeX template based on engine"""
        current_editor = self.get_current_editor()
        if not current_editor:
            return

        # Choose template based on engine
        if self.main_window.latex_engine in ["xelatex", "lualatex"]:
            template = r"""\documentclass[a4paper]{article}
\usepackage{fontspec}
\usepackage{polyglossia}
\setmainlanguage{arabic}
\setotherlanguage{english}
\setmainfont{Amiri}
\defaultfontfeatures{Numbers=Arabic}
\renewcommand{\thesection}{\arabic{section}}
\renewcommand{\thesubsection}{\thesection.\arabic{subsection}}
\renewcommand{\theequation}{\arabic{equation}}
\usepackage{amsmath}
\usepackage{amsfonts}
\usepackage{amssymb}
\usepackage{graphicx}
\title{عنوانك هنا}
\author{اسمك}
\date{\today}
\begin{document}
\maketitle
\section{مقدمة}
المحتوى الخاص بك هنا.
\begin{equation}
E = mc^2
\end{equation}
\end{document}"""
        else:
            template = r"""\documentclass{article}
\usepackage[utf8]{inputenc}
\usepackage{amsmath}
\usepackage{amsfonts}
\usepackage{amssymb}
\usepackage{graphicx}
\title{Your Title Here}
\author{Your Name}
\date{\today}
\begin{document}
\maketitle
\section{Introduction}
Your content goes here.
\end{document}"""

        # ✅ Insert template
        current_editor.blockSignals(True)
        current_editor.setPlainText(template)
        current_editor.blockSignals(False)

        # ✅ Apply alignment
        current_editor.setAlignment(Qt.AlignRight if self.main_window.is_rtl else Qt.AlignLeft)

        # ✅ Mark as unmodified
        for data in self.editor_files.values():
            if data['editor'] == current_editor:
                data['modified'] = False
                data['saved_content'] = template
                break

        self.main_window.update_title()        
        
    def update_editor_font(self, font_family, font_size):
        """Update font for all editors only if font has changed"""
        # Avoid unnecessary updates
        if (hasattr(self, '_current_font_family') and 
            self._current_font_family == font_family and
            hasattr(self, '_current_font_size') and 
            self._current_font_size == font_size):
            return

        # Store current values
        self._current_font_family = font_family
        self._current_font_size = font_size

        font = QFont(font_family, font_size)

        for data in self.editor_files.values():
            if data['editor']:
                # Block signals to prevent triggering modified flag
                data['editor'].blockSignals(True)
                data['editor'].setFont(font)
                data['editor'].blockSignals(False)

                # Update label in splitter mode
                if data.get('label'):
                    label_font = QFont(
                        font_family if self.main_window.menu_language != "ar" else "Amiri",
                        font_size
                    )
                    data['label'].setFont(label_font)


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
                    
    def insert_latex(self, latex_code):
        """Insert LaTeX code at cursor position"""
        current_editor = self.main_window.editor_manager.get_current_editor()
        current_file = self.main_window.editor_manager.get_current_file_path()

        lang = self.main_window.menu_language
        translations = self.main_window.translations      
        tr = translations[lang]                                    
        
        if not current_editor or not current_file:
            self.show_error(tr["no_file_open"], tr["open_a_latex_file"])
            return
        
        
        if getattr(self, '_inserting_latex', False):
            return  # ❌ Prevent recursion
        self._inserting_latex = True

        try:
            current_editor = self.get_current_editor()
            if not current_editor:
                return

            cursor = current_editor.textCursor()
            selected_text = cursor.selectedText()

            # Replace cursor placeholder
            if "cursor" in latex_code:
                if selected_text:
                    latex_code = latex_code.replace("cursor", selected_text)
                else:
                    latex_code = latex_code.replace("cursor", "")

            # Mark as modified
            self.on_text_changed()
            
            # Update status
            if selected_text:
                status_template = translations[lang].get(
                    "status_inserted_math_symbol_on",
                    "Inserted math symbol {code} on {selected_text}"
                )
                status_msg = status_template.format(
                    code=latex_code,
                    selected_text=selected_text
                )
            else:
                status_template = translations[lang].get(
                    "status_inserted_math_symbol",
                    "Inserted math symbol {code}"
                )
                status_msg = status_template.format(
                    code=latex_code
                )

            if hasattr(self.main_window, 'update_status_bar'):
                self.main_window.update_status_bar(status_msg)                


            # Handle special cases with cursor positioning
            if "numerator" in latex_code and "denominator" in latex_code:
                # Insert \frac{numerator}{denominator}
                cursor.insertText(latex_code)
                text = current_editor.toPlainText()
                cursor_pos = cursor.position()
                start_pos = text.rfind(r"\frac{", 0, cursor_pos)
                if start_pos != -1:
                    num_start = start_pos + 6
                    num_end = text.find("}", num_start)
                    if num_end != -1:
                        cursor.setPosition(num_start)
                        cursor.setPosition(num_end, cursor.MoveMode.KeepAnchor)
                        current_editor.setTextCursor(cursor)

            elif "{superscript}" in latex_code or "{subscript}" in latex_code or "{x}" in latex_code:
                # Insert ^{superscript} or _{subscript} and place cursor inside
                code = latex_code.replace("{superscript}", "{}").replace("{subscript}", "{}").replace("{x}", "{}")
                cursor.insertText(code)
                cursor.setPosition(cursor.position() - 1)  # Move inside braces
                current_editor.setTextCursor(cursor)

            elif r"\begin{" in latex_code:
                # Insert environment and place cursor in the middle
                cursor.insertText(latex_code)
                lines = latex_code.split('\n')
                if len(lines) >= 3:
                    cursor_pos = cursor.position()
                    middle_line_pos = cursor_pos - len(lines[-1]) - 1
                    cursor.setPosition(middle_line_pos)
                    current_editor.setTextCursor(cursor)

            else:
                # Default: just insert the code
                cursor.insertText(latex_code)

            # Mark as modified
            self.on_text_changed()
            current_editor.setFocus()

        finally:
            self._inserting_latex = False
    

    
    def get_container(self):
        """Return the editor's container widget (tabbed or splitter)"""
        if self.editor_layout_mode == "tabbed":
            return self.editor_tabs
        else:
            return self.editor_splitter
        
    def save_all(self):
        """Save all open files that have been modified"""
        saved_count = 0
        failed_files = []
        
        for path, data in self.editor_files.items():
            if data.get('modified', False):
                old_current = self.current_file
                old_editor = self.get_current_editor()
                
                self.current_file = path
                editor = data['editor']
                if editor:
                    editor.setFocus()
                
                try:
                    if self.save_file():
                        saved_count += 1
                    else:
                        failed_files.append(os.path.basename(path))
                except Exception as e:
                    failed_files.append(f"{os.path.basename(path)} ({str(e)})")
                
                # Restore state
                self.current_file = old_current
                if old_editor:
                    old_editor.setFocus()
        
        # Show status
        lang = self.main_window.menu_language
        t = self.main_window.translations[lang]
        
        if saved_count == 0 and not failed_files:
            self.main_window.update_status_bar(t.get("no_files_to_save", "No files need saving"))
        elif failed_files:
            failed_list = ", ".join(failed_files)
            QMessageBox.warning(
                self.main_window,
                t.get("save_errors", "Save Errors"),
                t.get("failed_to_save", "Failed to save: {files}").format(files=failed_list)
            )
        else:
            self.main_window.update_status_bar(
                t.get("saved_files_count", "Saved {count} files").format(count=saved_count)
            )
        
        return len(failed_files) == 0
    


    def save_all(self):
            """Save all open files that have been modified"""
            saved_count = 0
            failed_files = []

            for path, data in self.editor_files.items():
                if data.get('modified', False):
                    # Temporarily switch to this file for saving
                    old_current = self.current_file
                    old_editor = self.get_current_editor()

                    self.current_file = path

                    # Focus the editor for this file
                    editor = data['editor']
                    if editor:
                        editor.setFocus()

                    try:
                        if self.save_file():
                            saved_count += 1
                        else:
                            failed_files.append(os.path.basename(path))
                    except Exception as e:
                        failed_files.append(f"{os.path.basename(path)} ({str(e)})")

                    # Restore previous state
                    self.current_file = old_current
                    if old_editor:
                        old_editor.setFocus()

            # Show status message
            lang = self.main_window.menu_language
            t = self.main_window.translations[lang]

            if saved_count == 0 and not failed_files:
                self.main_window.update_status_bar(t.get("no_files_to_save", "No files need saving"))
            elif failed_files:
                failed_list = ", ".join(failed_files)
                QMessageBox.warning(
                    self.main_window,
                    t.get("save_errors", "Save Errors"),
                    t.get("failed_to_save", "Failed to save: {files}").format(files=failed_list)
                )
            else:
                self.main_window.update_status_bar(
                    t.get("saved_files_count", "Saved {count} files").format(count=saved_count)
                )

            return len(failed_files) == 0
    
    def close_current_file(self):
        """Close the currently active file"""
        current_editor = self.get_current_editor()
        if not current_editor:
            return True
        
        # Find the index of current editor
        current_index = -1
        if self.editor_layout_mode == "tabbed":
            current_index = self.editor_tabs.currentIndex()
        else:
            # For splitter mode, find the wrapper containing this editor
            for i in range(self.editor_splitter.count()):
                wrapper = self.editor_splitter.widget(i)
                layout = wrapper.layout()
                if layout and layout.count() > 1:
                    editor_widget = layout.itemAt(1).widget()
                    if editor_widget == current_editor:
                        current_index = i
                        break
        
        if current_index >= 0:
            return self.close_editor_tab(current_index)
        
        return False

    def close_all_files(self):
        """Close all open files - FIXED to switch to tabbed mode first in H/V mode"""
        try:
            self.file_watcher.unwatch_all()
            # ✅ Get list of files to close (copy to avoid modification during iteration)
            paths_to_close = list(self.editor_files.keys())
            if not paths_to_close:
                return True
            
            # Check for modified files
            modified_files = [os.path.basename(path) for path, data in self.editor_files.items() 
                             if data.get('modified', False)]
            
            if modified_files:
                lang = self.main_window.menu_language
                t = self.main_window.translations[lang]
                modified_list = ", ".join(modified_files)
                reply = QMessageBox.question(
                    self.main_window,
                    t.get("close_all_confirm", "Close All Files"),
                    t.get("close_all_message", "The following files have unsaved changes:\n{files}\n\nSave all before closing?").format(files=modified_list),
                    QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                    QMessageBox.Save
                )
                
                if reply == QMessageBox.Cancel:
                    return False
                elif reply == QMessageBox.Save:
                    if not self.save_all():
                        return False
            
            # ✅ If in H/V mode, switch to tabbed mode FIRST (before closing)
            was_hv_mode = self.editor_layout_mode in ["horizontal", "vertical"]
            if was_hv_mode:
                #print("DEBUG: Switching from H/V mode to tabbed mode BEFORE closing editors")
                self.editor_layout_mode = "tabbed"
                if hasattr(self.main_window, 'layout_manager') and hasattr(self.main_window.layout_manager, '_recreate_editor_container'):
                    self.main_window.layout_manager._recreate_editor_container()
                if hasattr(self.main_window, 'config_manager'):
                    self.main_window.config_manager.set_config_value('layout', 'editor_layout_mode', "tabbed")
            
            # ✅ Now close all files in tabbed mode (no UI issues!)
            success = True
            
            # Clear ALL bookmarks before closing files
            if hasattr(self.main_window, 'bookmarks_widget'):
                self.main_window.bookmarks_widget.clear_all_bookmarks()
                #print("Cleared all bookmarks before closing all files")
            
            # Close all editors
            for filename in paths_to_close:
                try:
                    if filename in self.editor_files:  # Double-check file still exists
                        editor_data = self.editor_files[filename]
                        editor = editor_data['editor']
                        
                        # Remove from tab_order
                        if hasattr(self, 'tab_order') and filename in self.tab_order:
                            self.tab_order.remove(filename)
                        
                        # Remove from UI (now always tabbed mode)
                        if isinstance(self.editor_tabs, QTabWidget):
                            tab_index = self.editor_tabs.indexOf(editor)
                            if tab_index != -1:
                                self.editor_tabs.removeTab(tab_index)

                        # Clean up spell checker resources for this editor
                        if hasattr(self.main_window, 'spell_checker') and editor:
                            self.main_window.spell_checker.cleanup_editor(editor)  

                        
                        # Clean up editor
                        editor.setParent(None)
                        editor.deleteLater()
                        
                        # Remove from file data
                        del self.editor_files[filename]
                except Exception as e:
                    print(f"Error closing file {filename}: {e}")
                    success = False
            
            # ✅ Clean up and reset state completely
            self.current_file = None
            if hasattr(self, 'tab_order'):
                self.tab_order.clear()
            
            # ✅ Clear editor_tabs (now always QTabWidget)
            if isinstance(self.editor_tabs, QTabWidget):
                while self.editor_tabs.count() > 0:
                    self.editor_tabs.removeTab(0)
            
            # ✅ Force recreation to show welcome tab properly
            if hasattr(self.main_window, 'layout_manager'):
                QTimer.singleShot(50, self.main_window.layout_manager._recreate_editor_container)
            
            self.main_window.update_title()
            return success
            
        except Exception as e:
            print(f"Error in close_all_files: {e}")
            import traceback
            traceback.print_exc()
            return False
        

    def close_current_pdf(self):
        """Close the currently active PDF"""
        if hasattr(self.main_window, 'pdf_manager'):
            return self.main_window.pdf_manager.close_current_pdf()
        return False

    def close_all_pdfs(self):
        """Close all open PDF files"""
        if hasattr(self.main_window, 'pdf_manager'):
            return self.main_window.pdf_manager.close_all_pdfs()
        return False

    def save_as_file(self):
        """Alias for save_file_as() - for menu compatibility"""
        return self.save_file_as()
    
 
    def insert_latex_command(self, latex_code):
        """
        Insert LaTeX command, wrapping selected text if any
        
        Args:
            latex_code (str): The LaTeX command to insert
        """
        current_editor = self.main_window.editor_manager.get_current_editor()
        current_file = self.main_window.editor_manager.get_current_file_path()
        lang = self.main_window.menu_language
        translations = self.main_window.translations        
        tr = translations[lang]      
        
        if not current_editor or not current_file:
            self.show_error(tr["no_file_open"], tr["open_a_latex_file"])
            return

        current_editor = self.get_current_editor()
        if not current_editor:
            return
            
        cursor = current_editor.textCursor()
        selected_text = cursor.selectedText()
        
        # Handle different types of LaTeX commands
        if selected_text:
            # Text is selected - wrap it with the command
            new_text = self._wrap_selected_text(latex_code, selected_text)
            cursor.insertText(new_text)
            
            # Update status
            # status_template = translations[lang].get("status_inserted_math_symbol", "Inserted math symbol: {selected_text}")
            # status_msg = status_template.format(code=selected_text)
            # if hasattr(self.main_window, 'update_status_bar'):
                # self.main_window.update_status_bar(status_msg)            
            # Update status

            status_template = translations[lang].get(
                "status_inserted_math_symbol_on",
                "Inserted math symbol {code} on code = {selected_text}"
            )
            status_msg = status_template.format(
                code=latex_code,
                selected_text=selected_text
            )

        else:
            # No text selected - insert command and position cursor
            new_text, cursor_offset = self._insert_empty_command(latex_code)
            start_position = cursor.position()
            cursor.insertText(new_text)
            
            # Position cursor inside braces/brackets if applicable
            if cursor_offset > 0:
                new_cursor = current_editor.textCursor()
                new_cursor.setPosition(start_position + cursor_offset)
                current_editor.setTextCursor(new_cursor)

            
            # Update status
            status_template = translations[lang].get(
                "status_inserted_math_symbol",
                "Inserted math symbol {code}"
            )
            status_msg = status_template.format(
                code=latex_code
            )

        if hasattr(self.main_window, 'update_status_bar'):
            self.main_window.update_status_bar(status_msg)
                

        # ✅ FIX: Directly mark the file as modified
        if current_file in self.editor_files:
            data = self.editor_files[current_file]
            if not data.get('modified', False):
                data['modified'] = True
                self._update_tab_title(current_file, True)
                if current_file == self.current_file:
                    self.main_window.update_title()

        current_editor.setFocus()
    
    def _wrap_selected_text(self, latex_code, selected_text):
        """Wrap selected text with LaTeX command"""
        
        # Handle cursor placeholder
        if "cursor" in latex_code:
            return latex_code.replace("cursor", selected_text)
        
        # Handle common patterns
        patterns = {
            r'{}': lambda cmd: cmd[:-2] + f"{{{selected_text}}}",
            r'\{ \}': lambda cmd: f"\\{{ {selected_text} \\}}",
            r'\[ \]': lambda cmd: f"\\[ {selected_text} \\]", 
            r'\( \)': lambda cmd: f"\\( {selected_text} \\)",
            '$cursor$': lambda cmd: f"${selected_text}$",
            '$$cursor$$': lambda cmd: f"$${selected_text}$$"
        }
        
        for pattern, handler in patterns.items():
            if pattern in latex_code:
                return handler(latex_code)
        
        # Environment handling
        if latex_code.startswith('\\begin{') and '\\end{' in latex_code:
            lines = latex_code.split('\n')
            if len(lines) > 2:
                return f"{lines[0]}\n    {selected_text}\n{lines[-1]}"
            else:
                env_name = latex_code.split('{')[1].split('}')[0]
                return f"\\begin{{{env_name}}}\n    {selected_text}\n\\end{{{env_name}}}"
        
        # Default: wrap with braces
        return f"{latex_code}{{{selected_text}}}"
    
    def _insert_empty_command(self, latex_code):
        """Insert empty command and return cursor position"""
        
        # Handle cursor placeholder
        if "cursor" in latex_code:
            cursor_pos = latex_code.find("cursor")
            cleaned_code = latex_code.replace("cursor", "")
            return cleaned_code, cursor_pos
        
        # Position cursor inside first empty braces
        if '{}' in latex_code:
            brace_pos = latex_code.find('{}')
            return latex_code.replace('{}', '{}', 1), brace_pos + 1
        
        # Special delimiter positioning
        delim_positions = {
            r'\{ \}': (r'\{ \}', 3),
            r'\[ \]': (r'\[ \]', 3),
            r'\( \)': (r'\( \)', 3),
            '$cursor$': ('$$', 1),
            '$$cursor$$': ('$$$$', 2)
        }
        
        for pattern, (replacement, offset) in delim_positions.items():
            if pattern in latex_code:
                return replacement, offset
        
        # Multi-line environments
        if '\n' in latex_code:
            lines = latex_code.split('\n')
            for i, line in enumerate(lines):
                if not line.strip():
                    offset = sum(len(lines[j]) + 1 for j in range(i))
                    return latex_code, offset
        
        # Position inside first braces if available
        if '{' in latex_code:
            brace_pos = latex_code.find('{') + 1
            return latex_code, brace_pos
        
        # Default: position at end
        return latex_code, len(latex_code)


    # def get_selected_text(self):
        # """Get currently selected text from active editor"""
        # current_editor = self.get_current_editor()
        # if current_editor:
            # return current_editor.textCursor().selectedText()
        # return ""

    def has_selection(self):
        """Check if there is selected text in active editor"""
        current_editor = self.get_current_editor()
        if current_editor:
            return current_editor.textCursor().hasSelection()
        return False


    def go_to_line(self):
        """Show Go to Line dialog"""
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]   
        
        current_editor = self.get_current_editor()
        current_file = self.get_current_file_path()
        
        if not current_editor or not current_file:
            self.show_error("No file open", "Please open a LaTeX file first.")
            return
        
        if not current_editor:
            return

        line_count = current_editor.document().blockCount()
        current_line = current_editor.textCursor().blockNumber() + 1

        line, ok = QInputDialog.getInt(
            self.main_window,
            "Go to Line",
            f"Enter line number (1 - {line_count}):",
            current_line,
            1, line_count, 1
        )

        if ok:
            cursor = current_editor.textCursor()
            cursor.movePosition(QTextCursor.Start)
            for _ in range(line - 1):
                cursor.movePosition(QTextCursor.NextBlock)
            current_editor.setTextCursor(cursor)
            current_editor.ensureCursorVisible()
            
            # Update status bar - FIXED
            lang = self.main_window.menu_language
            translations = self.main_window.translations
            status_template = translations[lang].get("status_go_to_line", "Go to line: {line}")
            status_msg = status_template.format(line=line)
            if hasattr(self.main_window, 'update_status_bar'):
                self.main_window.update_status_bar(status_msg)        
            

    def go_to_line_number(self, line_number):
        """Jump to a specific line number without showing dialog"""
        current_editor = self.get_current_editor()
        if not current_editor:
            return False
        
        line_count = current_editor.document().blockCount()
        
        # Validate line number
        if line_number < 1 or line_number > line_count:
            return False
        
        cursor = current_editor.textCursor()
        cursor.movePosition(QTextCursor.Start)
        for _ in range(line_number - 1):
            cursor.movePosition(QTextCursor.NextBlock)
        
        # Select the entire line for visibility
        cursor.movePosition(QTextCursor.StartOfBlock)
        cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
        
        current_editor.setTextCursor(cursor)
        current_editor.ensureCursorVisible()
        current_editor.setFocus()
        
        # Update status bar - FIXED
        lang = self.main_window.menu_language
        translations = self.main_window.translations
        status_template = translations[lang].get("status_go_to_line", "Go to line: {line}")
        status_msg = status_template.format(line=line_number)
        if hasattr(self.main_window, 'update_status_bar'):
            self.main_window.update_status_bar(status_msg)        
        
        return True

        
    def close_editor_tab_by_filename(self, filename):
        """Close editor by filename - More reliable method"""
        try:
            if filename not in self.editor_files:
                return
                
            # Confirm save if modified
            if self.editor_files[filename].get('modified', False):
                reply = QMessageBox.question(
                    self.main_window,
                    "Unsaved Changes", 
                    f"Do you want to save changes to {os.path.basename(filename)}?",
                    QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
                )
                if reply == QMessageBox.Save:
                    if not self.save_file(filename):
                        return
                elif reply == QMessageBox.Cancel:
                    return
            
            # Get editor and tab widget info
            editor_data = self.editor_files[filename]
            editor = editor_data['editor']
            
            # ✅ FIXED: Remove from tab_order first
            if hasattr(self, 'tab_order') and filename in self.tab_order:
                self.tab_order.remove(filename)
            
            # Remove from UI
            mode = self.editor_layout_mode
            if mode == "tabbed":
                if isinstance(self.editor_tabs, QTabWidget):
                    tab_index = self.editor_tabs.indexOf(editor)
                    if tab_index != -1:
                        self.editor_tabs.removeTab(tab_index)
            else:
                # H/V mode: remove the entire tab widget
                tab_widget = editor_data.get('tab_widget')
                if tab_widget and isinstance(self.editor_tabs, list):
                    try:
                        self.editor_tabs.remove(tab_widget)
                        tab_widget.setParent(None)
                    except ValueError:
                        pass
            
            # Clean up spell checker resources for this editor
            if hasattr(self.main_window, 'spell_checker') and editor:
                self.main_window.spell_checker.cleanup_editor(editor)  

            # ✅ FIXED: Clean up editor properly
            editor.setParent(None)
            editor.deleteLater()
                            
            # Remove from file data
            del self.editor_files[filename]
            
            # ✅ FIXED: Update current_file logic
            if filename == self.current_file:
                if self.editor_files:
                    # Set to the last file in tab_order that still exists
                    for fname in reversed(self.tab_order):
                        if fname in self.editor_files:
                            self.current_file = fname
                            break
                    else:
                        self.current_file = next(iter(self.editor_files.keys()))
                else:
                    self.current_file = None
            
            # ✅ FIXED: Handle different scenarios after closing
            if len(self.editor_files) == 0:
                # No files left - show welcome tab
                if hasattr(self.main_window, 'layout_manager'):
                    QTimer.singleShot(10, self.main_window.layout_manager._recreate_editor_container)
            elif len(self.editor_files) == 1 and mode in ["horizontal", "vertical"]:
                # ✅ NEW FEATURE: Switch to tabbed mode when only 1 file remains in H/V mode
                #print("Only 1 file remaining in H/V mode - switching to tabbed mode")
                self.editor_layout_mode = "tabbed"
                
                # Update config if available
                if hasattr(self.main_window, 'config_manager'):
                    self.main_window.config_manager.set_config_value('layout', 'editor_layout_mode', 'tabbed')
                
                # Force recreation with new mode
                if hasattr(self.main_window, 'layout_manager'):
                    QTimer.singleShot(10, self.main_window.layout_manager._recreate_editor_container)
                    
                # Update status bar
                status_key = "status_editor_tabbed"
                if hasattr(self.main_window, 'translations') and hasattr(self.main_window, 'menu_language'):
                    self.main_window.update_status_bar(
                        self.main_window.translations[self.main_window.menu_language][status_key]
                    )
            else:
                # ✅ Multiple files remain in H/V mode - update splitter sizes
                if mode != "tabbed" and hasattr(self, 'editor_splitter') and self.editor_splitter:
                    if self.editor_splitter.count() > 0:
                        equal_size = 600 // self.editor_splitter.count() 
                        self.editor_splitter.setSizes([equal_size] * self.editor_splitter.count())
            
            self.main_window.update_title()
            #print(f"Closed {filename}, remaining: {list(self.editor_files.keys())}")
            
        except Exception as e:
            print(f"Error in close_editor_tab_by_filename: {e}")
            import traceback
            traceback.print_exc()
            

    def transform_to_lowercase(self):
        """Convert selected text to lowercase"""
        self._transform_text(str.lower)

    def transform_to_uppercase(self):
        """Convert selected text to uppercase"""
        self._transform_text(str.upper)

    def transform_to_title_case(self):
        """Convert selected text to title case (First letter of each word capitalized)"""
        self._transform_text(str.title)

    def transform_to_full_title_case(self):
        """Convert selected text to full title case (Title case with special LaTeX handling)"""
        def full_title(s):
            # Basic title case
            s = s.title()
            # Make small words lowercase (optional enhancement)
            small_words = {'a', 'an', 'and', 'as', 'at', 'but', 'by', 'for', 'if', 'in', 'nor', 'of', 'on', 'or', 'so', 'the', 'to', 'up', 'yet'}
            words = s.split()
            for i, word in enumerate(words):
                if i > 0 and word.lower() in small_words:
                    words[i] = word.lower()
            return ' '.join(words)
        self._transform_text(full_title)

    def _transform_text(self, transform_func):
        """Apply transformation function to selected text with undo support"""
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]   
        
        current_editor = self.get_current_editor()
        current_file = self.get_current_file_path()
        
        if not current_editor or not current_file:
            self.show_error("No file open", "Please open a LaTeX file first.")
            return
        
        if not current_editor:
            return
        
        cursor = current_editor.textCursor()
        if not cursor.hasSelection():
            return
        
        selected_text = cursor.selectedText()
        transformed = transform_func(selected_text)
        
        # ✅ FIXED: Replace only the selected text, not the entire document
        cursor.beginEditBlock()
        cursor.removeSelectedText()  # Remove the selected text first
        cursor.insertText(transformed)  # Insert the transformed text
        cursor.endEditBlock()
        
        # ✅ Mark document as modified
        current_editor.document().setModified(True)
        self.on_text_changed()  # Trigger any UI updates


    def count_selected_words(self):
        """Count words in selected text and show result"""
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]
        current_editor = self.get_current_editor()

        if not current_editor:
            return

        cursor = current_editor.textCursor()

        if not cursor.hasSelection():
            # Status bar feedback
            if hasattr(self.main_window, "update_status_bar"):
                self.main_window.update_status_bar("No text selected")

            # Popup warning
            QMessageBox.information(
                self.main_window,
                "Word Count",
                "Please select some text first."
            )
            return

        selected_text = cursor.selectedText()

        # Fix Qt line separator
        selected_text = selected_text.replace('\u2029', ' ').strip()

        # Better word counting
        words = re.findall(r'\b\w+\b', selected_text)
        word_count = len(words)

        #message = f"Words: {word_count}"
        message = tr["word_count_sentence"].format(count=word_count)

        # ✅ Status bar
        if hasattr(self.main_window, "update_status_bar"):
            self.main_window.update_status_bar(message)

        # ✅ Popup dialog
        QMessageBox.information(
            self.main_window,
            "Word Count",
            message
        )
    
    def comment_latex_lines(self):
        """Comment selected LaTeX text by adding % at the beginning of each line"""
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]   
        
        current_editor = self.get_current_editor()
        current_file = self.get_current_file_path()
        
        if not current_editor or not current_file:
            self.show_error("No file open", "Please open a LaTeX file first.")
            return
            
        def add_comments(text):
            """Add % comment markers to each line"""
            lines = text.split('\u2029')  # Qt uses Unicode paragraph separator
            commented_lines = []
            
            for line in lines:
                if line.strip():  # Only add % to non-empty lines
                    commented_lines.append('% ' + line)
                else:
                    commented_lines.append(line)  # Keep empty lines as-is
            
            return '\u2029'.join(commented_lines)
        
        self._transform_text(add_comments)

    def uncomment_latex_lines(self):
        """Uncomment selected LaTeX text by removing % from the beginning of each line"""
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]   
        
        current_editor = self.get_current_editor()
        current_file = self.get_current_file_path()
        
        if not current_editor or not current_file:
            self.show_error("No file open", "Please open a LaTeX file first.")
            return
            
        def remove_comments(text):
            """Remove % comment markers from each line"""
            lines = text.split('\u2029')  # Qt uses Unicode paragraph separator
            uncommented_lines = []
            
            for line in lines:
                stripped = line.lstrip()
                if stripped.startswith('% '):
                    # Remove '% ' (percent + space)
                    uncommented_lines.append(line.replace('% ', '', 1))
                elif stripped.startswith('%'):
                    # Remove '%' only (no space after)
                    uncommented_lines.append(line.replace('%', '', 1))
                else:
                    # Line is not commented, keep as-is
                    uncommented_lines.append(line)
            
            return '\u2029'.join(uncommented_lines)
        
        self._transform_text(remove_comments)

    def toggle_latex_comments(self):
        """Toggle comments on selected LaTeX text - comment if mostly uncommented, uncomment if mostly commented"""
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]   
        
        current_editor = self.get_current_editor()
        current_file = self.get_current_file_path()
        
        if not current_editor or not current_file:
            self.show_error("No file open", "Please open a LaTeX file first.")
            return
            
        current_editor = self.get_current_editor()
        if not current_editor:
            return
            
        cursor = current_editor.textCursor()
        if not cursor.hasSelection():
            return
        
        selected_text = cursor.selectedText()
        lines = selected_text.split('\u2029')
        
        # Count commented vs uncommented lines (ignore empty lines)
        commented_count = 0
        non_empty_lines = 0
        
        for line in lines:
            stripped = line.lstrip()
            if stripped:  # Non-empty line
                non_empty_lines += 1
                if stripped.startswith('%'):
                    commented_count += 1
        
        # If more than half are commented, uncomment all; otherwise comment all
        if non_empty_lines > 0 and commented_count > non_empty_lines / 2:
            self.uncomment_latex_lines()
        else:
            self.comment_latex_lines()
   
        
  
    def delete_auxiliary_files(self):
        """Open dialog to delete auxiliary files in current document's directory"""
        if not self.current_file:
            QMessageBox.information(self.main_window, "No Document", "Please open a LaTeX document first.")
            return
        # Default extensions
        default_extensions = {
            'log', 'aux', 'lof', 'lot', 'bbl', 'blg', 'bcf', 'ilg', 'ind',
            'idx', 'glo', 'gls', 'toc', 'out', 'fdb_latexmk', 'fls',
            'synctex.gz', 'run.xml', 'mtc', 'mtc0'
        }
        # Load saved extensions
        saved_ext_str = self.main_window.config_manager.get_config_value(
            'ui', 'aux_file_extensions', ','.join(sorted(default_extensions))
        )
        extensions = set(ext.strip().lower() for ext in saved_ext_str.split(',') if ext.strip())
        directory = os.path.dirname(self.current_file)
        base_name = os.path.splitext(os.path.basename(self.current_file))[0]
        # Get initial files to delete
        files_to_delete = self.get_auxiliary_files_to_delete(self.current_file, extensions)
        # Show confirmation dialog
        dialog = QDialog(self.main_window)
        dialog.setWindowTitle(self.main_window.translations[self.main_window.menu_language]["delete_aux_title"])
        layout = QVBoxLayout(dialog)
        # List of files to delete
        file_list = QTextEdit()
        file_list.setPlainText('\n'.join(files_to_delete))
        file_list.setReadOnly(True)
        file_list.setMaximumHeight(150)
        layout.addWidget(QLabel("Files to delete:"))
        layout.addWidget(file_list)
        # Manage extensions button
        btn_layout = QHBoxLayout()
        manage_btn = QPushButton(self.main_window.translations[self.main_window.menu_language]["manage_extensions"])
        def open_manage_extensions():
            self.manage_aux_extensions(extensions, dialog)
            # ✅ Refresh file list after dialog closes
            new_files = self.get_auxiliary_files_to_delete(self.current_file, extensions)
            file_list.setPlainText('\n'.join(new_files))
        manage_btn.clicked.connect(open_manage_extensions)
        btn_layout.addWidget(manage_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec_() == QDialog.Accepted:
            # Final list after possible extension change
            final_files = self.get_auxiliary_files_to_delete(self.current_file, extensions)
            if not final_files:
                QMessageBox.information(self.main_window, "No Files", "No auxiliary files to delete.")
                return
            # Delete files
            deleted = []
            failed = []
            for file in final_files:
                try:
                    os.remove(os.path.join(directory, file))
                    deleted.append(file)
                except Exception as e:
                    failed.append(f"{file} ({str(e)})")
            # Show result
            lang = self.main_window.menu_language
            t = self.main_window.translations[lang]
            if deleted:
                self.main_window.update_status_bar(f"Deleted {len(deleted)} auxiliary file(s)")
            if failed:
                QMessageBox.warning(
                    self.main_window,
                    t.get("delete_errors", "Delete Errors"),
                    t.get("failed_to_delete", "Failed to delete: {files}").format(files=", ".join(failed))
                )
    
    def manage_aux_extensions(self, extensions, parent_dialog):
        """Open dialog to manage auxiliary file extensions"""
        lang = self.main_window.menu_language
        t = self.main_window.translations[lang]
        dialog = QDialog(parent_dialog)
        dialog.setWindowTitle(t["manage_extensions"])
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(t["current_extensions"]))
        list_widget = QListWidget()
        for ext in sorted(extensions):
            list_widget.addItem(ext)
        layout.addWidget(list_widget)
        # Buttons
        btn_layout = QHBoxLayout()
        add_btn = QPushButton(t["add_extension"])
        remove_btn = QPushButton(t["remove_extension"])
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(remove_btn)
        layout.addLayout(btn_layout)
        # ✅ Use QDialogButtonBox
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        # Connect
        add_btn.clicked.connect(lambda: self.add_extension(list_widget))
        remove_btn.clicked.connect(lambda: self.remove_selected_extension(list_widget))
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        # Store for access
        dialog.list_widget = list_widget
        if dialog.exec_() == QDialog.Accepted:
            # Save extensions
            new_extensions = {
                dialog.list_widget.item(i).text().strip().lower()
                for i in range(dialog.list_widget.count())
            }
            if hasattr(self.main_window, 'config_manager'):
                self.main_window.config_manager.set_config_value(
                    'ui', 'aux_file_extensions', ','.join(sorted(new_extensions))
                )
            extensions.clear()
            extensions.update(new_extensions)
    
    def add_extension(self, list_widget):
        """Add a new file extension to the list widget"""
        from PyQt5.QtWidgets import QInputDialog, QMessageBox
        extension, ok = QInputDialog.getText(
            self.main_window,
            "Add Extension",
            "Enter file extension (without dot, e.g., aux, toc):",  # ← Updated hint
            text="new"
        )
        if ok and extension.strip():
            extension = extension.strip().lower()
            # Remove dot if user included it
            if extension.startswith("."):
                extension = extension[1:]
            
            # Avoid duplicates
            for i in range(list_widget.count()):
                if list_widget.item(i).text() == extension:
                    QMessageBox.warning(self.main_window, "Duplicate", f"Extension '{extension}' already exists.")
                    return
            list_widget.addItem(extension)
    
    def remove_selected_extension(self, list_widget):
        """Remove selected extension from the list widget"""
        selected_items = list_widget.selectedItems()
        if not selected_items:
            return
        for item in selected_items:
            list_widget.takeItem(list_widget.row(item))
    
    def get_auxiliary_files_to_delete(self, current_file, extensions):
        """Get list of auxiliary files to delete based on current file and extensions"""
        if not current_file or not os.path.exists(current_file):
            return []
        directory = os.path.dirname(current_file)
        base_name = os.path.splitext(os.path.basename(current_file))[0]
        files_to_delete = []
        try:
            for file in os.listdir(directory):
                file_path = os.path.join(directory, file)
                if not os.path.isfile(file_path):
                    continue
                ext = os.path.splitext(file)[1].lower().lstrip('.')
                if ext in extensions and file != os.path.basename(current_file):
                    if file.startswith(base_name + ".") or ext in ['aux', 'log', 'toc', 'lof', 'lot', 'bbl', 'blg', 'idx', 'ind', 'out', 'fdb_latexmk', 'fls', 'synctex.gz', 'run.xml']:
                        files_to_delete.append(file)
        except Exception as e:
            print(f"Error scanning auxiliary files: {e}")
        return files_to_delete
        
    def set_rtl_mode(self, is_rtl):
        """Apply RTL mode to all open editors"""
        try:
            #print(f"🔄 Applying RTL mode: {is_rtl}")
            
            # Apply to all currently open editors
            for path, data in self.editor_files.items():
                editor = data.get('editor')
                if editor and hasattr(editor, 'setLayoutDirection'):
                    from PyQt5.QtCore import Qt
                    direction = Qt.RightToLeft if is_rtl else Qt.LeftToRight
                    editor.setLayoutDirection(direction)
                    #print(f"✅ Applied RTL={is_rtl} to {os.path.basename(path)}")
            
            # Store the RTL state for new files
            self.rtl_mode = is_rtl
            
        except Exception as e:
            print(f"❌ Error applying RTL mode: {e}")
            import traceback
            traceback.print_exc()

###
    def fold_current_section(self):
        """Fold the current section in the active editor"""
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]   
        
        editor = self.get_current_editor()
        file = self.get_current_file_path()
        
        if not editor or not file:
            self.show_error("No file open", "Please open a LaTeX file first.")
            return      
        
        if editor and hasattr(editor, 'fold_current_section'):
            editor.fold_current_section()

    def unfold_current_section(self):
        """Unfold the current section in the active editor"""
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]   
        
        editor = self.get_current_editor()
        file = self.get_current_file_path()
        
        if not editor or not file:
            self.show_error("No file open", "Please open a LaTeX file first.")
            return

        if editor and hasattr(editor, 'unfold_current_section'):
            editor.unfold_current_section()

    def fold_all_sections(self):
        """Fold all sections in the active editor"""
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]   
        
        editor = self.get_current_editor()
        file = self.get_current_file_path()
        
        if not editor or not file:
            self.show_error(tr["no_file_open"], tr["open_a_latex_file"])
            return

        if editor and hasattr(editor, 'fold_all'):
            editor.fold_all()

    def unfold_all_sections(self):
        """Unfold all sections in the active editor"""
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]   
        
        editor = self.get_current_editor()
        file = self.get_current_file_path()
        
        if not editor or not file:
            self.show_error(tr["no_file_open"], tr["open_a_latex_file"])
            return

        if editor and hasattr(editor, 'unfold_all'):
            editor.unfold_all()

    def fold_to_level(self, level):
        """Fold all sections at or below a specific level"""
        editor = self.get_current_editor()
        file = self.get_current_file_path()
        
        if not editor or not file:
            self.show_error("No file open", "Please open a LaTeX file first.")
            return

        if editor and hasattr(editor, 'fold_level'):
            editor.fold_level(level)

    def fold_preamble(self):
        """Fold the preamble in the active editor"""
        editor = self.get_current_editor()
        if editor and hasattr(editor, 'fold_preamble'):
            editor.fold_preamble()

    def unfold_preamble(self):
        """Unfold the preamble in the active editor"""
        editor = self.get_current_editor()
        if editor and hasattr(editor, 'unfold_preamble'):
            editor.unfold_preamble()

    def fold_document_begin(self):
        """Fold the document begin section in the active editor"""
        editor = self.get_current_editor()
        if editor and hasattr(editor, 'fold_document_begin'):
            editor.fold_document_begin()

    def unfold_document_begin(self):
        """Unfold the document begin section in the active editor"""
        editor = self.get_current_editor()
        if editor and hasattr(editor, 'unfold_document_begin'):
            editor.unfold_document_begin()
            
    def fold_bibliography(self):
        """Fold the bibliography in the active editor"""
        editor = self.get_current_editor()
        if editor and hasattr(editor, 'fold_bibliography'):
            editor.fold_bibliography()

    def unfold_bibliography(self):
        """Unfold the bibliography in the active editor"""
        editor = self.get_current_editor()
        if editor and hasattr(editor, 'unfold_bibliography'):
            editor.unfold_bibliography()

    def toggle_bibliography_fold(self):
        """Toggle bibliography fold in the active editor"""
        editor = self.get_current_editor()
        if editor and hasattr(editor, 'toggle_bibliography_fold'):
            editor.toggle_bibliography_fold()
