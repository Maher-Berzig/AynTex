# latex_completer_manager.py
"""
Unified LaTeX Completer Manager
Handles CWL command completion and \ref{}, \cite{} completion
"""
import re
import os
from PyQt5.QtWidgets import QCompleter, QListView, QStyledItemDelegate, QStyle
from PyQt5.QtCore import Qt, QStringListModel, QTimer, QSize, QObject, QEvent
from PyQt5.QtGui import QFont, QFontMetrics
from style_manager import get_completer_stylesheet



class CWLCompleter:
    """CWL-based LaTeX command completer"""
    
    def __init__(self, editor, cwl_manager):
        self.editor = editor
        self.cwl_manager = cwl_manager
        self.completer = QCompleter()
        self.completer.setWidget(editor)
        self.completer.setCompletionMode(QCompleter.PopupCompletion)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchContains)
        
        # Style the popup
        popup = self.completer.popup()        
        popup.setStyleSheet(get_completer_stylesheet("cwl"))

        
        self.completer.activated.connect(self.insert_completion)
        self.model = QStringListModel()
        self.completer.setModel(self.model)
        self.prefix = ""
        self._enabled = True  # instance-level on/off switch

    def enable(self):
        """Enable this completer instance."""
        self._enabled = True

    def disable(self):
        """Disable this completer instance and hide any open popup."""
        self._enabled = False
        self.hide_popup()

    def is_popup_visible(self):
        return self.completer.popup().isVisible()
    
    def hide_popup(self):
        self.completer.popup().hide()
    
    def refresh(self):
        """Refresh completions from CWL manager"""
        try:
            if self.cwl_manager:
                commands = self.cwl_manager.get_all_commands()
                if commands:
                    # Ensure all items are strings
                    str_commands = []
                    for c in commands:
                        if isinstance(c, str):
                            str_commands.append(c)
                        else:
                            str_commands.append(str(c))
                    self.model.setStringList(str_commands)
        except Exception as e:
            print(f"❌ Error in CWL refresh: {e}")
    
    def handle_keypress(self):
        """Called after key press to potentially show completions"""
        if not self._enabled:
            return
        if not self.cwl_manager or not self.cwl_manager.is_completion_enabled():
            return
        
        cursor = self.editor.textCursor()
        text_before = self.editor.toPlainText()[:cursor.position()]
        
        # ═══════════════════════════════════════════════════════════
        # Check for \begin{ or \end{ environment completion FIRST
        # ═══════════════════════════════════════════════════════════
        env_match = re.search(r'\\(begin|end)\{([a-zA-Z*]*)$', text_before)
        if env_match:
            env_prefix = env_match.group(2)  # What's typed after {
            self.prefix = env_prefix
            self._completing_environment = True
            
            # Get environment completions
            completions = self.cwl_manager.get_environment_completions(env_prefix)
            
            if completions:
                self.model.setStringList(completions)
                self.completer.setCompletionPrefix(env_prefix)
                
                rect = self.editor.cursorRect()
                rect.setWidth(300)
                self.completer.complete(rect)
            else:
                self.hide_popup()
            return
        
        # ═══════════════════════════════════════════════════════════
        # Regular command completion (e.g., \frac, \textbf)
        # ═══════════════════════════════════════════════════════════
        self._completing_environment = False
        match = re.search(r'\\([a-zA-Z]*)$', text_before)
        if match:
            prefix = match.group(0)  # Include backslash
            self.prefix = prefix
            
            if len(prefix) >= 2:  # At least \ + one letter
                completions = self.cwl_manager.get_completions_as_strings(prefix)
                
                if completions:
                    self.model.setStringList(completions)
                    self.completer.setCompletionPrefix(prefix)
                    
                    rect = self.editor.cursorRect()
                    rect.setWidth(300)
                    self.completer.complete(rect)
                else:
                    self.hide_popup()
            else:
                self.hide_popup()
        else:
            self.hide_popup()

        
    
    def insert_completion(self, completion):
        """Insert the selected completion"""
        cursor = self.editor.textCursor()
        text_before = self.editor.toPlainText()[:cursor.position()]
        
        # ═══════════════════════════════════════════════════════════
        # Handle environment completion (\begin{...} / \end{...})
        # ═══════════════════════════════════════════════════════════
        if getattr(self, '_completing_environment', False):
            # Find what was typed after \begin{ or \end{
            env_match = re.search(r'\\(begin|end)\{([a-zA-Z*]*)$', text_before)
            if env_match:
                typed_part = env_match.group(2)
                # Delete the typed part
                for _ in range(len(typed_part)):
                    cursor.deletePreviousChar()
                
                # Insert environment name + closing brace
                cursor.insertText(completion + '}')
                
                # If it was \begin{}, also add \end{}
                if env_match.group(1) == 'begin':
                    # Add newline and \end{envname}
                    cursor.insertText('\n\n\\end{' + completion + '}')
                    # Position cursor on the middle line
                    cursor.movePosition(cursor.Up)
                    cursor.movePosition(cursor.EndOfLine)
                    self.editor.setTextCursor(cursor)
                
                self.hide_popup()
                return
        
        # ═══════════════════════════════════════════════════════════
        # Handle regular command completion
        # ═══════════════════════════════════════════════════════════
        match = re.search(r'\\[a-zA-Z]*$', text_before)
        if match:
            # Delete what was typed
            for _ in range(len(match.group(0))):
                cursor.deletePreviousChar()
        
        # Get insert text from CWL command if available
        insert_text = completion
        if self.cwl_manager and hasattr(self.cwl_manager, 'commands'):
            cmd = self.cwl_manager.commands.get(completion)
            if cmd and hasattr(cmd, 'get_insert_text'):
                insert_text = cmd.get_insert_text()
        
        # Insert the completion
        cursor.insertText(insert_text)
        
        # Position cursor inside first {} if present
        if '{' in insert_text:
            full_text = self.editor.toPlainText()
            insert_pos = cursor.position() - len(insert_text)
            brace_pos = insert_text.find('{')
            if brace_pos != -1:
                new_pos = insert_pos + brace_pos + 1
                cursor.setPosition(new_pos)
                self.editor.setTextCursor(cursor)
        
        self.hide_popup()
    


class _RefCiteKeyFilter(QObject):
    def __init__(self, ref_completer, parent):
        super().__init__(parent)
        self._ref = ref_completer

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            key = event.key()

            if key in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab):
                index = obj.currentIndex()
                if not index.isValid():
                    index = obj.model().index(0, 0)

                if index.isValid():
                    text = index.data()
                    if text:
                        self._ref.insert_completion(text)
                        return True

            elif key == Qt.Key_Escape:
                obj.hide()
                return True

        return False


class RefCiteCompleter:
    """Completer for \ref{}, \cite{}, \label{} etc."""
    
    def __init__(self, editor, main_window):
        self.editor = editor
        self.main_window = main_window
        self.completer = QCompleter()
        self.completer.setWidget(editor)
        self.completer.setCompletionMode(QCompleter.PopupCompletion)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchContains)
        
        # Style popup
        popup = self.completer.popup()
        popup.setStyleSheet(get_completer_stylesheet("ref"))

        
        self.completer.activated.connect(self.insert_completion)
        self.model = QStringListModel()
        self.completer.setModel(self.model)
        
        # Cache
        self._labels_cache = []
        self._citations_cache = []
        self._cache_valid = False
        
        # Current completion context
        self._current_type = None  # 'ref', 'cite', 'label', etc.
        self._prefix_start = 0

        # Install the keyboard event filter. Qt parents it to editor so
        # its C++ lifetime is managed automatically; we also keep a Python
        # reference to prevent the wrapper being garbage-collected.
        #self._key_filter = _RefCiteKeyFilter(self, editor)
        self._key_filter = _RefCiteKeyFilter(self, self.completer.popup())
        self.completer.popup().installEventFilter(self._key_filter)
    
    def is_popup_visible(self):
        return self.completer.popup().isVisible()
    
    def hide_popup(self):
        self.completer.popup().hide()
    
    def invalidate_cache(self):
        """Invalidate the cache when document changes"""
        self._cache_valid = False
    
    def _get_all_labels(self):
        """Extract all \\label{...} from open documents"""
        if self._cache_valid and self._labels_cache:
            return self._labels_cache
        
        labels = set()
        
        if not hasattr(self.main_window, 'editor_manager'):
            return list(labels)
        
        em = self.main_window.editor_manager
        
        # Scan all open files
        if hasattr(em, 'editor_files') and em.editor_files:
            for file_path, editor_data in em.editor_files.items():
                editor = editor_data.get('editor') if isinstance(editor_data, dict) else None
                if editor:
                    try:
                        text = editor.toPlainText()
                        # Find all \label{...}
                        for match in re.finditer(r'\\label\{([^}]+)\}', text):
                            labels.add(match.group(1))
                    except Exception as e:
                        print(f"⚠️ Error scanning labels in {file_path}: {e}")
        
        self._labels_cache = sorted(labels)
        #print(f"✅ Found {len(self._labels_cache)} labels")
        return self._labels_cache
    
        
    def _get_all_citations(self):
        """Extract citations from .bib files AND \\bibitem{} entries in .tex files"""
        # Check cache first
        if self._cache_valid and self._citations_cache:
            return self._citations_cache
        
        citations = set()
        
        if not hasattr(self.main_window, 'editor_manager'):
            return list(citations)
        
        em = self.main_window.editor_manager
        
        # ═══════════════════════════════════════════════════════════
        # STEP 1: Scan all open .tex files for \bibitem{} entries
        # ═══════════════════════════════════════════════════════════
        directories_to_scan = set()
        
        if hasattr(em, 'editor_files') and em.editor_files:
            for file_path, editor_data in em.editor_files.items():
                editor = editor_data.get('editor') if isinstance(editor_data, dict) else None
                if not editor:
                    continue
                
                try:
                    text = editor.toPlainText()
                    
                    # Find \bibitem{key} or \bibitem[label]{key}
                    # Pattern handles: \bibitem{key} and \bibitem[optional]{key}
                    for match in re.finditer(r'\\bibitem(?:\s*\[[^\]]*\])?\s*\{([^}]+)\}', text):
                        citation_key = match.group(1).strip()
                        if citation_key:
                            citations.add(citation_key)
                    
                    # Track directory for .bib file scanning
                    if file_path and os.path.exists(file_path):
                        directories_to_scan.add(os.path.dirname(file_path))
                        
                except Exception as e:
                    print(f"⚠️ Error scanning {file_path}: {e}")
        
        # ═══════════════════════════════════════════════════════════
        # STEP 2: Also scan .bib files (for biblatex/bibtex users)
        # ═══════════════════════════════════════════════════════════
        bib_files = set()
        
        # Check for \bibliography{} or \addbibresource{} in open .tex files
        if hasattr(em, 'editor_files'):
            for file_path, editor_data in em.editor_files.items():
                if not str(file_path).lower().endswith('.tex'):
                    continue
                
                editor = editor_data.get('editor') if isinstance(editor_data, dict) else None
                if not editor:
                    continue
                
                try:
                    text = editor.toPlainText()
                    file_dir = os.path.dirname(file_path) if file_path and os.path.exists(file_path) else ""
                    
                    if not file_dir:
                        continue
                    
                    # \bibliography{file1,file2}
                    for match in re.finditer(r'\\bibliography\{([^}]+)\}', text):
                        bib_refs = match.group(1)
                        for bib_name in bib_refs.split(','):
                            bib_name = bib_name.strip()
                            if not bib_name.endswith('.bib'):
                                bib_name += '.bib'
                            bib_path = os.path.join(file_dir, bib_name)
                            if os.path.exists(bib_path):
                                bib_files.add(bib_path)
                    
                    # \addbibresource{file.bib}
                    for match in re.finditer(r'\\addbibresource\{([^}]+)\}', text):
                        bib_name = match.group(1).strip()
                        if not bib_name.endswith('.bib'):
                            bib_name += '.bib'
                        bib_path = os.path.join(file_dir, bib_name)
                        if os.path.exists(bib_path):
                            bib_files.add(bib_path)
                except:
                    pass
        
        # Scan directories for .bib files
        for directory in directories_to_scan:
            try:
                for f in os.listdir(directory):
                    if f.lower().endswith('.bib'):
                        bib_path = os.path.join(directory, f)
                        bib_files.add(bib_path)
            except:
                pass
        
        # Parse .bib files
        for bib_path in bib_files:
            try:
                with open(bib_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    # Find @article{key, @book{key, etc.
                    for match in re.finditer(r'@\w+\s*\{\s*([^,\s\}]+)', content):
                        citation_key = match.group(1).strip()
                        if citation_key:
                            citations.add(citation_key)
            except:
                pass
        
        self._citations_cache = sorted(citations)
        return self._citations_cache
    
    
    def handle_keypress(self):
        """Check if we should show ref/cite completions"""
        cursor = self.editor.textCursor()
        pos = cursor.position()
        text = self.editor.toPlainText()
        text_before = text[:pos]
        
        # Check for \ref{, \cite{, \eqref{, \pageref{, etc.
        patterns = [
            (r'\\ref\{([^}]*)$', 'ref', self._get_all_labels),
            (r'\\eqref\{([^}]*)$', 'eqref', self._get_all_labels),
            (r'\\pageref\{([^}]*)$', 'pageref', self._get_all_labels),
            (r'\\autoref\{([^}]*)$', 'autoref', self._get_all_labels),
            (r'\\cref\{([^}]*)$', 'cref', self._get_all_labels),
            (r'\\Cref\{([^}]*)$', 'Cref', self._get_all_labels),
            (r'\\cite\{([^}]*)$', 'cite', self._get_all_citations),
            (r'\\citep\{([^}]*)$', 'citep', self._get_all_citations),
            (r'\\citet\{([^}]*)$', 'citet', self._get_all_citations),
            (r'\\citealp\{([^}]*)$', 'citealp', self._get_all_citations),
            (r'\\parencite\{([^}]*)$', 'parencite', self._get_all_citations),
            (r'\\textcite\{([^}]*)$', 'textcite', self._get_all_citations),
        ]
        
        for pattern, comp_type, getter in patterns:
            match = re.search(pattern, text_before)
            if match:
                # prefix = match.group(1)
                # self._current_type = comp_type
                # self._prefix_start = pos - len(prefix)
###
                full_text_inside = match.group(1)

                # Split by comma → last token is current prefix
                parts = full_text_inside.split(',')
                prefix = parts[-1].strip()

                self._current_type = comp_type
                self._prefix_start = pos - len(parts[-1])

###             
                
                # Get completions
                all_items = getter()
                
                # Filter by prefix
                if prefix:
                    filtered = [item for item in all_items 
                               if prefix.lower() in item.lower()]
                else:
                    filtered = all_items
                
                if filtered:
                    self.model.setStringList(filtered)
                    self.completer.setCompletionPrefix(prefix)
                    
                    rect = self.editor.cursorRect()
                    rect.setWidth(300)
                    self.completer.complete(rect)
                else:
                    self.hide_popup()
                return
        
        # No pattern matched
        self.hide_popup()
    
    def insert_completion(self, completion):
        cursor = self.editor.textCursor()
        
        # Delete current prefix
        chars_to_delete = cursor.position() - self._prefix_start
        for _ in range(chars_to_delete):
            cursor.deletePreviousChar()
        
        # Insert completion
        cursor.insertText(completion)
        
        # ✅ Always ensure closing brace
        pos = cursor.position()
        text = self.editor.toPlainText()
        
        if pos >= len(text) or text[pos] != '}':
            cursor.insertText('}')
        
        self.hide_popup()

class LaTeXCompleterManager:
    """Manager that installs and coordinates completers on editors"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.installed_editors = set()
    
    @property
    def cwl_manager(self):
        return getattr(self.main_window, 'cwl_manager', None)
    
    def install(self, editor):
        """Install completers on an editor"""
        editor_id = id(editor)
        if editor_id in self.installed_editors:
            return
        
        self.installed_editors.add(editor_id)
        
        # Install CWL completer
        if self.cwl_manager:
            cwl_completer = CWLCompleter(editor, self.cwl_manager)
            editor._cwl_completer = cwl_completer
            #print(f"✅ Installed CWL completer on editor {editor_id}")
        #else:
        #    print(f"⚠️ No CWL manager available")
        
        # Install ref/cite completer
        refcite_completer = RefCiteCompleter(editor, self.main_window)
        editor._refcite_completer = refcite_completer
        #print(f"✅ Installed ref/cite completer on editor {editor_id}")
        
        # Connect to text changes for ref/cite (with safety check)
        try:
            editor.textChanged.connect(lambda e=editor: self._on_text_changed(e))
        except Exception as e:
            print(f"⚠️ Could not connect textChanged: {e}")
    
    def _on_text_changed(self, editor):
        """Handle text changes - trigger ref/cite completion"""
        try:
            refcite = getattr(editor, '_refcite_completer', None)
            if not refcite:
                return
            
            # Use timer to avoid too frequent updates
            if not hasattr(editor, '_refcite_timer'):
                editor._refcite_timer = QTimer()
                editor._refcite_timer.setSingleShot(True)
                editor._refcite_timer.timeout.connect(
                    lambda: self._safe_handle_keypress(editor)
                )
            editor._refcite_timer.start(50)
        except Exception:
            pass
            
    def _safe_handle_keypress(self, editor):
        """Safely call handle_keypress"""
        try:
            refcite = getattr(editor, '_refcite_completer', None)
            if refcite:
                refcite.handle_keypress()
        except Exception:
            pass
    
    def invalidate_refcite_cache(self):
        """Invalidate ref/cite cache in all editors"""
        try:
            if not hasattr(self.main_window, 'editor_manager'):
                return
            
            em = self.main_window.editor_manager
            if not hasattr(em, 'editor_files') or not em.editor_files:
                return
            
            for file_path, editor_data in em.editor_files.items():
                editor = editor_data.get('editor') if isinstance(editor_data, dict) else None
                refcite = getattr(editor, '_refcite_completer', None) if editor else None
                if refcite:
                    refcite.invalidate_cache()
        except Exception:
            pass
    
    def refresh_cwl(self):
        """Refresh CWL completions in all editors"""
        try:
            if not hasattr(self.main_window, 'editor_manager'):
                return
            
            em = self.main_window.editor_manager
            if not hasattr(em, 'editor_files') or not em.editor_files:
                return
            
            for file_path, editor_data in em.editor_files.items():
                editor = editor_data.get('editor') if isinstance(editor_data, dict) else None
                cwl = getattr(editor, '_cwl_completer', None) if editor else None
                if cwl:
                    cwl.refresh()
        except Exception as e:
            print(f"⚠️ Error refreshing CWL: {e}")
    
    def uninstall(self, editor):
        """Remove completers from editor"""
        editor_id = id(editor)
        self.installed_editors.discard(editor_id)
        
        if hasattr(editor, '_cwl_completer'):
            editor._cwl_completer = None
        if hasattr(editor, '_refcite_completer'):
            editor._refcite_completer = None