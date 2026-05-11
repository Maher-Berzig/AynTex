# spell_checker.py
import re
import os
import sys
from collections import defaultdict
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QTextCharFormat, QColor, QTextCursor
from PyQt5.QtWidgets import QMenu, QAction, QMessageBox, QProgressDialog, QApplication
from spellchecker import SpellChecker as PySpellChecker

# Async spell-check worker (QRunnable + coordinator)
from spell_worker import SpellCheckCoordinator

class SpellChecker:
    """Spell checker using pyspellchecker with personal dictionary support"""

    def __init__(self, main_window):
        self.main_window = main_window
        self.enabled = False          # Start disabled
        self.dictionaries_loaded = False
        self.check_timer = QTimer()
        self.check_timer.setSingleShot(True)
        self.check_timer.timeout.connect(self.check_spelling_delayed)
        self.current_editor = None
        self.personal_words = set()
        self.connected_editors = set()

        # pyspellchecker instances per language
        self.spell_checkers = {}      # {lang: PySpellChecker}
        self.word_sets = {}           # for statistics (cached)

        # LaTeX command pattern to ignore
        self.latex_pattern = re.compile(r'\\[a-zA-Z*]+|%.*$|\{[^}]*\}|\[[^\]]*\]', re.MULTILINE)

        # Path for personal dictionary
        self.personal_dict_path = self._get_personal_dict_path()

        # Initialize caches here so they always exist
        self._suggestion_cache = {}
        self._word_result_cache = {}

        # ── Async coordinator registry ─────────────────────────────────────
        # Maps editor widget → SpellCheckCoordinator
        self._coordinators = {}

        self.load_personal_dictionary()

    # ------------------------------------------------------------------
    # Personal dictionary handling (stored in config directory)
    # ------------------------------------------------------------------
    def _get_personal_dict_path(self):
        """Return the personal dictionary path in the standard config directory."""
        app_name = "Ayntex"
        system = sys.platform.lower()

        if system.startswith('win'):
            appdata = os.environ.get('APPDATA')
            if appdata:
                config_dir = os.path.join(appdata, app_name)
            else:
                config_dir = os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', app_name)
        elif system.startswith('darwin'):
            config_dir = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', app_name)
        else:
            xdg = os.environ.get('XDG_CONFIG_HOME')
            if xdg:
                config_dir = os.path.join(xdg, app_name)
            else:
                config_dir = os.path.join(os.path.expanduser('~'), '.config', app_name)

        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, "personal_dict.txt")
    
###
    def load_single_language(self, lang):
        """Load a single language dictionary."""
        from PyQt5.QtWidgets import QProgressDialog, QApplication
        from PyQt5.QtCore import Qt

        progress = QProgressDialog(
            f"Loading {lang.upper()} dictionary...", "Cancel", 0, 100,
            self.main_window
        )
        
        progress.setWindowTitle("Spell Checker")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setMinimumWidth(400)
        progress.show()
        QApplication.processEvents()

        try:
            progress.setValue(20)
            QApplication.processEvents()

            sc = PySpellChecker(language=lang)

            progress.setValue(60)
            QApplication.processEvents()

            if hasattr(sc, 'word_frequency') and hasattr(sc.word_frequency, 'words'):
                words = set(sc.word_frequency.words())
            else:
                words = set(sc.known([w for w in sc.word_frequency.dictionary.keys()]))

            progress.setValue(80)
            QApplication.processEvents()

            # Add personal words
            for word in self.personal_words:
                sc.word_frequency.add(word)

            self.spell_checkers[lang] = sc
            self.word_sets[lang] = words
            #print(f"Loaded {lang}: {len(words):,} words")

        except Exception as e:
            print(f"Failed to load {lang} dictionary: {e}")
            QMessageBox.warning(
                self.main_window, "Spell Checker",
                f"Failed to load {lang.upper()} dictionary:\n{e}"
            )
            progress.close()
            return False

        progress.setValue(100)
        progress.close()
        return True


    def set_language(self, lang):
        if (self.enabled
                and getattr(self, 'active_language', None) == lang
                and lang in self.spell_checkers):
            for editor in list(self.connected_editors):
                if self.is_editor_valid(editor):
                    coord = self._get_or_create_coordinator(editor)
                    coord.schedule_initial()
            return

        self.spell_checkers.clear()
        self.word_sets.clear()
        self._suggestion_cache.clear()
        self._word_result_cache.clear()

        success = self.load_single_language(lang)
        if not success:
            return

        self.dictionaries_loaded = True
        self.active_language     = lang
        self.enabled             = True

        for editor in list(self.connected_editors):
            if not self.is_editor_valid(editor):
                continue
            if hasattr(editor, 'highlighter') and editor.highlighter:
                editor.highlighter.spell_checker = self
                editor.highlighter.spell_map     = {}
            coord = self._get_or_create_coordinator(editor)
            # Editor already open and rendered — fire immediately
            coord.schedule_initial()

        if hasattr(self.main_window, 'statusBar'):
            lang_label = "English" if lang == "en" else "Arabic"
            self.main_window.statusBar().showMessage(
                f"Spell check language set to {lang_label}", 2000)

    def _rehighlight_all_visible(self):
        """Schedule an async check for all connected editors (visible range)."""
        for editor in list(self.connected_editors):
            if self.is_editor_valid(editor):
                self._schedule_async(editor)
###


    def load_personal_dictionary(self):
        """Load personal dictionary from file"""
        if os.path.exists(self.personal_dict_path):
            try:
                with open(self.personal_dict_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        word = line.strip().lower()
                        if word:
                            self.personal_words.add(word)
                #print(f"Loaded {len(self.personal_words)} personal words")
            except Exception as e:
                print(f"Failed to load personal dictionary: {e}")

    def save_personal_dictionary(self):
        """Save personal dictionary to file"""
        try:
            with open(self.personal_dict_path, 'w', encoding='utf-8') as f:
                for word in sorted(self.personal_words):
                    f.write(f"{word}\n")
        except Exception as e:
            print(f"Failed to save personal dictionary: {e}")


    def add_word_to_personal_dictionary(self, word):
        clean_word = word.strip().lower()
        if clean_word in self.personal_words:
            return
        self.personal_words.add(clean_word)
        self.save_personal_dictionary()
        for sc in self.spell_checkers.values():
            sc.word_frequency.add(clean_word)
        # Clear both caches
        if hasattr(self, '_suggestion_cache'):
            self._suggestion_cache.clear()
        if hasattr(self, '_word_result_cache'):        # ← add this
            self._word_result_cache.pop((self.active_language, clean_word), None)
        QTimer.singleShot(0, self._rehighlight_all_editors)


    def _rehighlight_all_editors(self):
        """Schedule an async spell check on every connected editor."""
        for editor in list(self.connected_editors):
            if not self.is_editor_valid(editor):
                self.connected_editors.discard(editor)
                continue
            self._schedule_async(editor)

    def _rehighlight_incremental(self, highlighter, block=None, chunk=30):
        """
        Rehighlight `chunk` blocks at a time, yielding to the event loop
        between chunks so the UI stays responsive.
        """
        if block is None:
            block = highlighter.document().begin()

        processed = 0
        while block.isValid() and processed < chunk:
            highlighter.rehighlightBlock(block)
            block = block.next()
            processed += 1

        if block.isValid():
            # Schedule next chunk — 0 ms lets the event loop breathe
            QTimer.singleShot(0, lambda b=block: self._rehighlight_incremental(highlighter, b, chunk))
        else:
            if hasattr(self.main_window, 'statusBar'):
                self.main_window.statusBar().showMessage(
                    f"Spell check ready ({self.active_language.upper()})", 2000
                )


    # ------------------------------------------------------------------
    # Dictionary loading with progress dialog
    # ------------------------------------------------------------------
    def load_dictionaries_with_progress(self):
        """Load pyspellchecker dictionaries with progress dialog"""
        progress = QProgressDialog("Loading spell check dictionaries...", "Cancel", 0, 100, self.main_window)
        progress.setWindowTitle("Spell Checker")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setMinimumWidth(400)
        progress.show()
        QApplication.processEvents()

        languages = ['en', 'ar']   # add more if needed
        total = len(languages)
        self.spell_checkers.clear()
        self.word_sets.clear()

        for i, lang in enumerate(languages):
            if progress.wasCanceled():
                progress.close()
                return
            progress.setLabelText(f"Loading {lang.upper()} dictionary...")
            progress.setValue(int((i / total) * 80))
            QApplication.processEvents()

            try:
                sc = PySpellChecker(language=lang)
                # Obtain word set for statistics
                if hasattr(sc, 'word_frequency') and hasattr(sc.word_frequency, 'words'):
                    words = set(sc.word_frequency.words())
                else:
                    words = set(sc.known([w for w in sc.word_frequency.dictionary.keys()]))
                self.word_sets[lang] = words
                self.spell_checkers[lang] = sc
                #print(f"Loaded {lang}: {len(words):,} words")
            except Exception as e:
                print(f"Failed to load {lang} dictionary: {e}")
                QMessageBox.warning(self.main_window, "Spell Checker",
                                    f"Failed to load {lang} dictionary: {e}")

        # Add personal words to all checkers
        for sc in self.spell_checkers.values():
            for word in self.personal_words:
                sc.word_frequency.add(word)

        progress.setValue(100)
        self.dictionaries_loaded = True
        progress.close()


        # At the end of load_dictionaries_with_progress, after setting dictionaries_loaded = True
        if self.enabled:
            # Immediately highlight current editor
            if self.current_editor:
                self.highlight_misspelled_words(self.current_editor)
                
    # ------------------------------------------------------------------
    # Language detection and core checking
    # ------------------------------------------------------------------
    def get_current_language(self):
        """Get currently active spell check language."""
        # Prefer explicitly set language over UI setting
        if hasattr(self, 'active_language') and self.active_language in self.spell_checkers:
            return self.active_language
        lang = getattr(self.main_window, 'menu_language', 'en')
        lang_map = {'english': 'en', 'arabic': 'ar', 'en': 'en', 'ar': 'ar'}
        mapped = lang_map.get(lang.lower(), 'en')
        return mapped if mapped in self.spell_checkers else (
            list(self.spell_checkers.keys())[0] if self.spell_checkers else 'en'
        )

    def is_word_correct(self, word, lang=None):
        """Check if word is correct using pyspellchecker"""
        if not word or len(word.strip()) < 2:
            return True
        clean_word = word.strip().lower()
        if clean_word.isdigit() or any(c.isdigit() for c in clean_word):
            return True
        if clean_word in self.personal_words:
            return True
        if lang is None:
            lang = self.get_current_language()
        sc = self.spell_checkers.get(lang)
        if not sc:
            return True
        return bool(sc.known([clean_word]))

    def get_suggestions(self, word, lang=None, max_suggestions=6):
        """Get spelling suggestions using pyspellchecker"""
        if not word or len(word) < 2:
            return []
        clean_word = word.strip().lower()
        if lang is None:
            lang = self.get_current_language()
        sc = self.spell_checkers.get(lang)
        if not sc:
            return []
        suggestions = sc.candidates(clean_word)
        if suggestions is None:
            return []
        # Filter out the original word and limit
        result = [s for s in suggestions if s != clean_word][:max_suggestions]
        return result

    def get_dictionary_stats(self):
        """Return dictionary statistics for the menu"""
        stats = {}
        for lang, words in self.word_sets.items():
            stats[lang] = len(words)
        return stats

    # ------------------------------------------------------------------
    # Text processing and highlighting
    # ------------------------------------------------------------------
    def extract_text_words(self, text):
        """Extract words from text, ignoring LaTeX commands"""
        if len(text) > 100000:
            text = text[:50000] + text[-50000:]
        clean_text = self.latex_pattern.sub(' ', text)
        word_pattern = re.compile(r'[a-zA-Z\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]+')
        words = []
        for match in word_pattern.finditer(text):
            word = match.group()
            if 1 < len(word) <= 20:
                words.append({
                    'word': word,
                    'start': match.start(),
                    'end': match.end()
                })
        return words

    def highlight_misspelled_words(self, editor):
        """Highlight misspelled words with optimizations"""
        if not self.enabled or not editor or not self.spell_checkers:
            return
        if not self.is_editor_valid(editor):
            return
        try:
            document = editor.document()
            text = document.toPlainText()
            if len(text) > 50000:      # skip very long documents for performance
                return
            # Clear existing highlights
            cursor = QTextCursor(document)
            cursor.select(QTextCursor.Document)
            fmt = QTextCharFormat()
            cursor.setCharFormat(fmt)

            words = self.extract_text_words(text)
            if len(words) > 1000:
                words = words[:1000]

            current_lang = self.get_current_language()
            error_format = QTextCharFormat()
            error_format.setUnderlineStyle(QTextCharFormat.SpellCheckUnderline)
            error_format.setUnderlineColor(QColor(255, 0, 0))

            misspelled = 0
            for w in words:
                if not self.is_word_correct(w['word'], current_lang):
                    cursor = QTextCursor(document)
                    cursor.setPosition(w['start'])
                    cursor.setPosition(w['end'], QTextCursor.KeepAnchor)
                    cursor.setCharFormat(error_format)
                    misspelled += 1

            if misspelled > 0 and hasattr(self.main_window, 'statusBar'):
                self.main_window.statusBar().showMessage(
                    f"Spell check ({current_lang}): {misspelled} issues", 2000)
        except RuntimeError as e:
            if "wrapped C/C++ object" in str(e) or "has been deleted" in str(e):
                if self.current_editor == editor:
                    self.current_editor = None
                return
            else:
                raise e

    # ------------------------------------------------------------------
    # Editor integration and delayed checking
    # ------------------------------------------------------------------
    def _rehighlight_visible(self, editor, start_block=None, remaining=0, skip_spell_check=False):
        """
        Rehighlight visible blocks in chunks.
        If skip_spell_check=True, underlines will NOT be drawn (used during scrolling).
        """

        if not self.is_editor_valid(editor) or not self.enabled:
            return
        highlighter = editor.highlighter
        if not highlighter or highlighter.spell_checker is not self:
            if highlighter:
                highlighter.set_spell_checker_no_rehighlight(self)
            else:
                return

        # First call: compute visible range
        if start_block is None:
            try:
                viewport = editor.viewport()
                top_cursor = editor.cursorForPosition(viewport.rect().topLeft())
                bottom_cursor = editor.cursorForPosition(viewport.rect().bottomRight())
                top_block = top_cursor.block()
                bottom_block = bottom_cursor.block()
                for _ in range(5):
                    prev = top_block.previous()
                    if prev.isValid():
                        top_block = prev
                start_block = top_block
                total_blocks = (bottom_block.blockNumber() - top_block.blockNumber()) + 1 + 10
                remaining = min(total_blocks, 25)
            except Exception as e:
                print(f"Error computing visible range: {e}")
                return

        chunk_size = 5
        processed = 0
        block = start_block
        while block.isValid() and processed < chunk_size and remaining > 0:
            highlighter._skip_spell_check = skip_spell_check
            highlighter.rehighlightBlock(block)
            # Reset flag for next block (in case different)
            highlighter._skip_spell_check = False
            block = block.next()
            processed += 1
            remaining -= 1

        if remaining > 0 and block.isValid():
            QTimer.singleShot(0, lambda: self._rehighlight_visible(editor, block, remaining, skip_spell_check))
        
    # ------------------------------------------------------------------
    # Async coordinator helpers
    # ------------------------------------------------------------------
    def _get_or_create_coordinator(self, editor):
        coord = self._coordinators.get(editor)
        if coord is None:
            coord = SpellCheckCoordinator(editor, self, self.main_window)
            self._coordinators[editor] = coord
        return coord

    def _schedule_async(self, editor, scroll=False):
        if not self.is_editor_valid(editor):
            return
        coord = self._get_or_create_coordinator(editor)
        if scroll:
            coord.schedule_scroll()
        else:
            coord.schedule()
        

    def setup_spell_check_for_editor(self, editor):
        if editor in self.connected_editors:
            if self.enabled and hasattr(editor, 'highlighter') and editor.highlighter:
                editor.highlighter.spell_checker = self
                editor.highlighter.spell_map     = {}
                coord = self._get_or_create_coordinator(editor)
                coord.schedule_initial()
            return

        self.connected_editors.add(editor)

        def on_text_changed():
            if not self.is_editor_valid(editor) or not self.enabled:
                return
            try:
                hl = getattr(editor, 'highlighter', None)
                if hl is not None and hasattr(hl, 'spell_map'):
                    block_no = editor.textCursor().block().blockNumber()
                    if block_no in hl.spell_map:
                        hl.spell_map.pop(block_no, None)
                        block = editor.document().findBlockByNumber(block_no)
                        if block.isValid():
                            hl.rehighlightBlock(block)   # synchronous — removes underline immediately
            except Exception:
                pass
            self._schedule_async(editor)

        editor.textChanged.connect(on_text_changed)

        scrollbar = editor.verticalScrollBar()
        if scrollbar:
            def on_scroll(_val):
                if self.enabled and self.is_editor_valid(editor):
                    self._schedule_async(editor, scroll=True)
            scrollbar.valueChanged.connect(on_scroll)

        def _on_editor_destroyed(_obj=None, sc=self, ed_id=id(editor)):
            stale = [e for e in sc.connected_editors if id(e) == ed_id]
            for e in stale:
                sc.connected_editors.discard(e)
            if sc.current_editor is not None and id(sc.current_editor) == ed_id:
                sc.current_editor = None
            for e in list(sc._coordinators):
                if id(e) == ed_id:
                    del sc._coordinators[e]
                    break
            sc._word_result_cache.clear()
            sc._suggestion_cache.clear()
            if sc.enabled:
                sc._disable_all("Spell check disabled (file closed)")

        try:
            editor.destroyed.connect(_on_editor_destroyed)
        except Exception:
            pass

        if self.enabled and hasattr(editor, 'highlighter') and editor.highlighter:
            editor.highlighter.spell_checker = self
            editor.highlighter.spell_map     = {}
            coord = self._get_or_create_coordinator(editor)
            coord.schedule_initial()

    def _wait_then_check(self, editor, attempts=0):
        if not self.is_editor_valid(editor) or not self.enabled:
            return
        try:
            doc = editor.document()
            # firstVisibleBlock() exists on QPlainTextEdit only — not QTextEdit
            if hasattr(editor, 'firstVisibleBlock'):
                block_valid = editor.firstVisibleBlock().isValid()
            else:
                block_valid = doc.begin().isValid()
            ready = (
                doc.blockCount() > 1
                and block_valid
                and editor.viewport().height() > 0
            )
        except Exception:
            ready = False   # keep trying — don't bail out

        if ready:
            coord = self._get_or_create_coordinator(editor)
            coord.schedule_initial()
        elif attempts < 50:   # up to 5 seconds
            QTimer.singleShot(
                100, lambda: self._wait_then_check(editor, attempts + 1))

    def _clear_underlines(self, editor):
        if not self.is_editor_valid(editor):
            return
        coord = self._coordinators.get(editor)
        if coord is not None:
            coord.cancel()
            coord.clear_underlines()
        try:
            if hasattr(editor, 'highlighter') and editor.highlighter:
                editor.highlighter.spell_checker = None
                editor.highlighter.spell_map     = {}
        except RuntimeError:
            pass

        
    def _disable_all(self, status_msg="Spell check disabled"):
        """
        Central disable routine. Clears underlines from every open editor,
        cancels all coordinators, resets state.
        """
        self.enabled = False
        self.active_language = None

        for editor, coord in list(self._coordinators.items()):
            coord.cancel()
            coord.clear_underlines()
            try:
                if hasattr(editor, 'highlighter') and editor.highlighter:
                    editor.highlighter.set_spell_checker_no_rehighlight(None)
            except RuntimeError:
                pass

        self._coordinators.clear()
        self._word_result_cache.clear()
        self._suggestion_cache.clear()

        try:
            self.main_window.statusBar().showMessage(status_msg, 2000)
        except Exception:
            pass

        

        
    def cleanup_editor(self, editor):
        """
        Called from close_editor_tab BEFORE the widget is destroyed.
        Cancels the coordinator but does NOT clear underlines or disable —
        _on_editor_destroyed handles that after Qt destroys the widget.
        """
        self.connected_editors.discard(editor)
        if self.current_editor is editor:
            self.current_editor = None

        coord = self._coordinators.pop(editor, None)
        if coord is not None:
            coord.cancel()
            # Clear underlines now while the widget is still alive
            coord.clear_underlines()

        for attr in ('_spell_timer', '_scroll_spell_timer'):
            try:
                timer = getattr(editor, attr, None)
                if timer is not None:
                    timer.stop()
            except RuntimeError:
                pass
            except Exception:
                pass

        # If this was the last editor or spell check is active,
        # disable now (don't wait for destroyed which may not fire
        # if deleteLater is used)
        if self.enabled:
            # Clear underlines on all remaining open editors
            for open_editor in list(self.connected_editors):
                coord = self._coordinators.get(open_editor)
                if coord is not None:
                    coord.cancel()
                    coord.clear_underlines()
                try:
                    if hasattr(open_editor, 'highlighter') and open_editor.highlighter:
                        open_editor.highlighter.set_spell_checker_no_rehighlight(None)
                except RuntimeError:
                    pass
            self._coordinators.clear()
            self.enabled = False
            self.active_language = None
            self._word_result_cache.clear()
            self._suggestion_cache.clear()
            try:
                self.main_window.statusBar().showMessage(
                    "Spell check disabled (file closed)", 2000)
            except Exception:
                pass


    def schedule_spell_check(self, editor):
        """Schedule a delayed spell check"""
        self.current_editor = editor
        self.check_timer.stop()
        self.check_timer.start(1500)

    def check_spelling_delayed(self):
        """Perform delayed spell check with safety checks"""
        if not self.current_editor:
            return
        try:
            if not self.is_editor_valid(self.current_editor):
                self.current_editor = None
                return
            self.highlight_misspelled_words(self.current_editor)
        except RuntimeError as e:
            if "wrapped C/C++ object" in str(e) or "has been deleted" in str(e):
                self.current_editor = None
                return
            else:
                raise e
        except Exception as e:
            print(f"Spell check error: {e}")
            self.current_editor = None

    def is_editor_valid(self, editor):
        """Check if editor widget is still valid"""
        try:
            _ = editor.document()
            _ = editor.isVisible()
            return True
        except RuntimeError:
            return False
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Context menu support (used by ContextMenuManager)
    # ------------------------------------------------------------------
    def _add_spell_check_section(self, menu, word, word_cursor, editor):
        """
        Add spell check suggestions if word is misspelled.
        Returns True if section was added.
        """
        if not self.enabled or not word:
            return False
        if not self.dictionaries_loaded:
            return False

        # Strip non-alpha characters but keep hyphens for hyphenated words
        import re
        clean_word = re.sub(r"[^a-zA-Z\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF-]", "", word)
        clean_word = clean_word.strip('-')   # remove leading/trailing hyphens
        if len(clean_word) < 2:
            return False

        # Check if correct (for hyphenated words, check each part)
        parts = clean_word.split('-')
        all_correct = all(
            self.is_word_correct(p.lower()) for p in parts if len(p) > 1
        )
        if all_correct:
            return False

        # Gather suggestions
        # For hyphenated words, collect suggestions for each incorrect part
        suggestions = []
        if len(parts) > 1:
            bad_parts = [p for p in parts if len(p) > 1 and not self.is_word_correct(p.lower())]
            for part in bad_parts:
                part_suggestions = self.get_suggestions(part.lower())
                if part_suggestions:
                    suggestions.extend(part_suggestions)
        else:
            suggestions = self.get_suggestions(clean_word.lower())

        # ── Header ────────────────────────────────────────────────────────
        if suggestions:
            header = QAction(f"Suggestions for '{clean_word}':", menu)
            header.setEnabled(False)
            menu.addAction(header)
            for suggestion in suggestions[:6]:
                action = QAction(f"  → {suggestion}", menu)
                action.triggered.connect(
                    lambda checked, s=suggestion, c=word_cursor:
                    self._replace_word(editor, c, s)
                )
                menu.addAction(action)
        else:
            # No suggestions — likely a proper noun or domain term
            header = QAction(f"No suggestions for '{clean_word}'", menu)
            header.setEnabled(False)
            menu.addAction(header)

        menu.addSeparator()

        # ── Always show "Add to dictionary" ───────────────────────────────
        # For hyphenated words, add the whole word (users expect that)
        add_action = QAction(f"Add '{clean_word}' to dictionary", menu)
        add_action.triggered.connect(
            lambda: self.add_word_to_personal_dictionary(clean_word)
        )
        menu.addAction(add_action)

        return True

    def _replace_word(self, editor, cursor, new_word):
        """
        Replace word. on_text_changed fires automatically:
        - clears spell_map for the edited block
        - schedules a fresh async check
        The revision guard in _on_result_ready discards any stale
        queued results so they cannot repopulate spell_map.
        """
        cursor.beginEditBlock()
        cursor.removeSelectedText()
        cursor.insertText(new_word)
        cursor.endEditBlock()
        editor.setTextCursor(cursor)

    def replace_word(self, editor, cursor, replacement):
        """Public wrapper for replace_word"""
        self._replace_word(editor, cursor, replacement)

    # ------------------------------------------------------------------
    # Toggle spell check (lazy loading)
    # ------------------------------------------------------------------
    def toggle_spell_check(self):
        """Toggle spell check off (language selection re-enables it)."""
        if not self.enabled:
            # If toggling on with no language set, default to English
            if not self.dictionaries_loaded:
                self.set_language('en')
                return

        self.enabled = not self.enabled

        if hasattr(self, '_suggestion_cache'):
            self._suggestion_cache.clear()

        for editor in list(self.connected_editors):
            if not self.is_editor_valid(editor):
                continue
            if hasattr(editor, 'highlighter') and editor.highlighter:
                editor.highlighter.set_spell_checker(self if self.enabled else None)
            if self.enabled:
                # Kick off an async check for each editor
                self._schedule_async(editor)
            else:
                # Cancel any in-flight or pending async checks
                coord = self._coordinators.get(editor)
                if coord is not None:
                    coord.cancel()

        status = "enabled" if self.enabled else "disabled"
        if hasattr(self.main_window, 'statusBar'):
            self.main_window.statusBar().showMessage(f"Spell check {status}", 2000)

    # ------------------------------------------------------------------
    # Compatibility alias for context menu toggle
    # ------------------------------------------------------------------
    def _toggle_spell_check(self):
        self.toggle_spell_check()

# ================================================================
# Integration functions (compatibility with main window)
# ================================================================

def setup_fast_spell_checker(main_window):
    """Initialize fast spell checker (compatibility wrapper)"""
    main_window.spell_checker = SpellChecker(main_window)
    main_window.spell_checker.load_personal_dictionary()
    return main_window.spell_checker

def add_spell_check_menu(main_window, tools_menu):
    """Add spell check menu to a tools menu (compatibility wrapper)"""
    if not hasattr(main_window, 'spell_checker'):
        return
    spell_menu = tools_menu.addMenu("Spell Check")
    toggle_action = QAction("Enable Spell Check", main_window)
    toggle_action.setCheckable(True)
    toggle_action.setChecked(main_window.spell_checker.enabled)
    toggle_action.triggered.connect(main_window.spell_checker.toggle_spell_check)
    spell_menu.addAction(toggle_action)
    spell_menu.addSeparator()
    info_action = QAction("Dictionary Info", main_window)

    def show_info():
        checker = main_window.spell_checker
        info = []
        total = 0
        for lang, words in checker.word_sets.items():
            count = len(words)
            info.append(f"{lang.upper()}: {count:,} words")
            total += count
        if checker.personal_words:
            info.append(f"Personal: {len(checker.personal_words)} words")
        info.append(f"\nTotal: {total:,} words")
        QMessageBox.information(main_window, "Dictionary Info", "\n".join(info))

    info_action.triggered.connect(show_info)
    spell_menu.addAction(info_action)