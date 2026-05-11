# context_menu.py
"""
Unified Context Menu System for LaTeX Editor
Replaces default Qt context menu with custom LaTeX-aware menu
"""

from PyQt5.QtWidgets import (QMenu, QAction, QApplication)
from PyQt5.QtGui import QTextCursor
from PyQt5.QtCore import Qt
import os


class ContextMenuManager:
    """
    Centralized context menu manager that replaces the default Qt menu.
    """
    def __init__(self, main_window):
        self.main_window = main_window
        self._installed_editors = set()

    @property
    def spell_checker(self):
        return getattr(self.main_window, 'spell_checker', None)

    @property
    def editor_manager(self):
        return getattr(self.main_window, 'editor_manager', None)

    @property
    def icons_manager(self):
        return getattr(self.main_window, 'icons_manager', None)

    def _apply_icon(self, action, icon_name):
        if self.icons_manager and hasattr(self.icons_manager, 'apply_icon_to_action'):
            self.icons_manager.apply_icon_to_action(action, icon_name)

    def install_context_menu(self, editor):
        editor_id = id(editor)
        if editor_id in self._installed_editors:
            return
        self._installed_editors.add(editor_id)
        editor.setContextMenuPolicy(Qt.CustomContextMenu)
        try:
            editor.customContextMenuRequested.disconnect()
        except TypeError:
            pass
        editor.customContextMenuRequested.connect(
            lambda pos, e=editor: self.show_unified_menu(e, pos)
        )
        editor._unified_menu_installed = True



    def show_unified_menu(self, editor, position):
        if hasattr(editor, '_context_menu_active'):
            editor._context_menu_active = True
        if hasattr(editor, '_cwl_completer') and editor._cwl_completer:
            try:
                editor._cwl_completer.hide_popup()
            except:
                pass

        menu = QMenu(editor)
        # ✅ Apply theme stylesheet
        menu.setStyleSheet(self._get_menu_stylesheet())


        # SECTION 0: Title
        title_action = QAction("Context Menu", menu)
        title_action.setEnabled(False)          # inactive – cannot be triggered
        font = title_action.font()
        font.setBold(True)
        title_action.setFont(font)
        menu.addAction(title_action)
        menu.addSeparator()



        cursor = editor.textCursor()
        has_selection = cursor.hasSelection()

        word_cursor = editor.cursorForPosition(position)
        word_cursor.select(QTextCursor.WordUnderCursor)
        word = word_cursor.selectedText().strip()

   
        # SECTION 1: SPELL CHECK
        spell_section_added = self._add_spell_check_section(menu, word, word_cursor, editor)
        if spell_section_added:
            menu.addSeparator()

        # SECTION 2: UNDO/REDO
        undo_action = QAction("Undo", menu)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.setEnabled(editor.document().isUndoAvailable())
        undo_action.triggered.connect(editor.undo)
        self._apply_icon(undo_action, "undo")
        menu.addAction(undo_action)

        redo_action = QAction("Redo", menu)
        redo_action.setShortcut("Ctrl+Y")
        redo_action.setEnabled(editor.document().isRedoAvailable())
        redo_action.triggered.connect(editor.redo)
        self._apply_icon(redo_action, "redo")
        menu.addAction(redo_action)
        menu.addSeparator()

        # SECTION 3: CLIPBOARD
        if has_selection:
            cut_action = QAction("Cut", menu)
            cut_action.setShortcut("Ctrl+X")
            cut_action.triggered.connect(editor.cut)
            self._apply_icon(cut_action, "cut")
            menu.addAction(cut_action)

            copy_action = QAction("Copy", menu)
            copy_action.setShortcut("Ctrl+C")
            copy_action.triggered.connect(editor.copy)
            self._apply_icon(copy_action, "copy")
            menu.addAction(copy_action)

        paste_action = QAction("Paste", menu)
        paste_action.setShortcut("Ctrl+V")
        paste_action.setEnabled(bool(QApplication.clipboard().text()))
        paste_action.triggered.connect(editor.paste)
        self._apply_icon(paste_action, "paste")
        menu.addAction(paste_action)

        if has_selection:
            delete_action = QAction("Delete", menu)
            delete_action.triggered.connect(lambda: editor.textCursor().removeSelectedText())
            self._apply_icon(delete_action, "delete")
            menu.addAction(delete_action)

        menu.addSeparator()

        select_all_action = QAction("Select All", menu)
        select_all_action.setShortcut("Ctrl+A")
        select_all_action.triggered.connect(editor.selectAll)
        self._apply_icon(select_all_action, "select_all")
        menu.addAction(select_all_action)
        menu.addSeparator()

        # SECTION 4: SELECTION-BASED LATEX ACTIONS
        if has_selection:
            self._add_selection_actions(menu, editor)
            menu.addSeparator()

        # ═══════════════════════════════════════════════════════════
        # SECTION 4.5: AI ASSISTANT SUBMENU (NEW)
        # ═══════════════════════════════════════════════════════════
        if has_selection:
            self._add_ai_assistant_submenu(menu, editor)
            menu.addSeparator()

        # SECTION 5: LATEX QUICK COMMANDS
        self._add_latex_commands(menu, editor)
        menu.addSeparator()

        # SECTION 6: ADDITIONAL FEATURES
        self._add_additional_features(menu, editor)

        menu.exec_(editor.mapToGlobal(position))

        if hasattr(editor, '_context_menu_active'):
            editor._context_menu_active = False

    def _add_ai_assistant_submenu(self, menu, editor):
        """Add AI Assistant submenu with text processing actions."""
        ai_menu = menu.addMenu("🤖 AI Assistant")

        ai_actions = [
            ("✍ Rewrite for clarity", "Rewrite for clarity"),
            ("📝 Simplify the language", "Simplify the language"),
            ("🔢 Convert to numbered list", "Convert to numbered list"),
            ("📖 Expand", "Expand"),
            ("📋 Summarize", "Summarize"),
            ("✂ Shorten", "Shorten"),
            ("💡 Explain", "Explain"),
            ("✅ Check grammar/spelling", "Check grammar/spelling"),
            ("🌐 Translate Arabic/English", "Translate Arabic/English"),
        ]

        for label, action_name in ai_actions:
            action = QAction(label, ai_menu)
            action.triggered.connect(
                lambda checked, name=action_name, e=editor:
                    self._handle_ai_context_action(name, e)
            )
            ai_menu.addAction(action)

    def _handle_ai_context_action(self, action_name, editor):
        """Route AI context menu action to the AI Assistant widget."""
        cursor = editor.textCursor()
        if not cursor.hasSelection():
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(editor, "No Selection",
                "Please select text first to use AI Assistant.")
            return

        selected_text = cursor.selectedText()

        # Find or create AI assistant widget
        ai_widget = self._get_ai_widget()
        if ai_widget is None:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(editor, "AI Assistant Not Available",
                "Please open the AI Assistant tab first\n"
                "(Tools → AI Assistant or Ctrl+I)")
            return

        # Delegate to the AI widget
        ai_widget.handle_context_menu_action(action_name, selected_text, editor)

    def _get_menu_stylesheet(self):
        """Return a theme-aware stylesheet for context menus."""
        from style_manager import get_welcome_style, _current_theme
        
        # Use per-theme colors directly
        _MENU_STYLES = {
            "default": {
                "bg": "#ffffff",         "color": "#2d2d30",
                "border": "#aaaaaa",     "selected_bg": "#e6f3ff",
                "selected_color": "#1e1e1e", "disabled_color": "#aaaaaa",
                "separator": "#dddddd",
            },
            "dark": {
                "bg": "#3c3f41",         "color": "#bbbbbb",
                "border": "#555759",     "selected_bg": "#4b6eaf",
                "selected_color": "#ffffff", "disabled_color": "#656565",
                "separator": "#555759",
            },
            "light": {
                "bg": "#fafafa",         "color": "#1a1a1a",
                "border": "#c0c0c0",     "selected_bg": "#e3f0ff",
                "selected_color": "#000000", "disabled_color": "#aaaaaa",
                "separator": "#cccccc",
            },
            "midnight": {
                "bg": "#161b22",         "color": "#c9d1d9",
                "border": "#30363d",     "selected_bg": "#1f6feb",
                "selected_color": "#ffffff", "disabled_color": "#484f58",
                "separator": "#30363d",
            },
        }

        s = _MENU_STYLES.get(_current_theme, _MENU_STYLES["default"])

        return f"""
            QMenu {{
                background-color: {s['bg']};
                color: {s['color']};
                border: 1px solid {s['border']};
                padding: 4px 0px;
            }}
            QMenu::item {{
                padding: 5px 28px 5px 20px;
                background-color: transparent;
            }}
            QMenu::item:selected {{
                background-color: {s['selected_bg']};
                color: {s['selected_color']};
            }}
            QMenu::item:disabled {{
                color: {s['disabled_color']};
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {s['separator']};
                margin: 3px 8px;
            }}
            QMenu::indicator {{
                width: 14px;
                height: 14px;
            }}
            QMenu::icon {{
                padding-left: 14px;
            }}
        """

    def _get_ai_widget(self):
        """Get the active AI Assistant widget, or None."""
        # Check existing AI tabs
        if hasattr(self.main_window, '_ai_tabs') and self.main_window._ai_tabs:
            for widget in self.main_window._ai_tabs:
                try:
                    # Verify widget is still valid
                    if widget and widget.isVisible():
                        return widget
                    # Even if not visible, it may still be functional
                    if widget:
                        return widget
                except RuntimeError:
                    continue  # Widget was deleted

        # Try to auto-open AI tab
        try:
            if hasattr(self.main_window, 'open_ai_tab'):
                self.main_window.open_ai_tab()
                # Check again after opening
                if hasattr(self.main_window, '_ai_tabs') and self.main_window._ai_tabs:
                    return self.main_window._ai_tabs[-1]
        except Exception as e:
            print(f"Could not auto-open AI tab: {e}")

        return None

    def _add_spell_check_section(self, menu, word, word_cursor, editor):
        if not self.spell_checker or not word:
            return False
        if not getattr(self.spell_checker, 'enabled', False):
            if getattr(self.spell_checker, 'dictionaries_loaded', False):
                return False
            return False
        if not hasattr(self.spell_checker, 'is_word_correct'):
            return False
        if not getattr(self.spell_checker, 'dictionaries_loaded', False):
            return False
        try:
            if self.spell_checker.is_word_correct(word):
                return False
        except Exception:
            return False

        try:
            suggestions = self.spell_checker.get_suggestions(word)
        except:
            suggestions = []

        if suggestions:
            header = QAction(f"Suggestions for '{word}':", menu)
            header.setEnabled(False)
            menu.addAction(header)
            for suggestion in suggestions[:5]:
                action = QAction(f"  → {suggestion}", menu)
                action.triggered.connect(
                    lambda checked, s=suggestion, c=word_cursor:
                    self._replace_word(editor, c, s)
                )
                menu.addAction(action)

        add_action = QAction(f"Add '{word}' to dictionary", menu)
        add_action.triggered.connect(lambda: self._add_to_dictionary(word))
        menu.addAction(add_action)
        return True

    def _set_spell_language(self, lang):
        sc = self.spell_checker
        if sc is not None:
            sc.set_language(lang)

    def _disable_spell_check(self):
        sc = self.spell_checker
        if sc is not None and sc.enabled:
            sc._disable_all("Spell check disabled")

    def _add_spell_check_submenu(self, menu):
        """Add a spell checking submenu with language selection (like menu_manager)."""
        if not self.spell_checker:
            return

        # Main spell check submenu
        spell_menu = menu.addMenu("Spell Checking")

        # Language submenu (Arabic/English)
        lang_menu = spell_menu.addMenu("Spell checking language")

        arabic_action = QAction("Arabic", lang_menu)
        arabic_action.setCheckable(True)
        arabic_action.triggered.connect(lambda: self._set_spell_language('ar'))
        lang_menu.addAction(arabic_action)

        english_action = QAction("English", lang_menu)
        english_action.setCheckable(True)
        english_action.triggered.connect(lambda: self._set_spell_language('en'))
        lang_menu.addAction(english_action)

        # Keep checkmarks in sync when submenu opens
        def update_lang_checks():
            sc = self.spell_checker
            if sc is None:
                return
            active = getattr(sc, 'active_language', None)
            enabled = getattr(sc, 'enabled', False)
            english_action.setChecked(enabled and active == 'en')
            arabic_action.setChecked(enabled and active == 'ar')

        lang_menu.aboutToShow.connect(update_lang_checks)
        spell_menu.aboutToShow.connect(update_lang_checks)

        spell_menu.addSeparator()

        # Disable spell check action
        disable_action = QAction("Disable spell check", spell_menu)
        disable_action.setEnabled(False)   # initially, will be updated on show
        disable_action.triggered.connect(self._disable_spell_check)

        def update_disable_action():
            sc = self.spell_checker
            if sc:
                disable_action.setEnabled(getattr(sc, 'enabled', False))

        spell_menu.aboutToShow.connect(update_disable_action)
        spell_menu.addAction(disable_action)

        # Optional: Dictionary statistics (like in menu_manager)
        spell_menu.addSeparator()
        info_action = QAction("Dictionary statistics", spell_menu)

        def show_dict_info():
            sc = self.spell_checker
            if not sc or not getattr(sc, 'dictionaries_loaded', False):
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.information(
                    self.main_window,
                    "Dictionary Statistics",
                    "No dictionary loaded yet.\n\nSelect a language to enable spell check."
                )
                return
            stats = sc.get_dictionary_stats()
            info = []
            total = 0
            for lang_key, count in stats.items():
                info.append(f"{lang_key.upper()}: {count:,} words")
                total += count
            if hasattr(sc, 'personal_words') and sc.personal_words:
                info.append(f"Personal: {len(sc.personal_words)} words")
            info.append(f"\nTotal: {total:,} words")
            if hasattr(sc, 'word_sets'):
                cached = sum(len(w) for w in sc.word_sets.values())
                info.append(f"Memory usage: {cached:,} words in dictionary")
            if hasattr(sc, '_suggestion_cache'):
                info.append(f"Suggestion cache: {len(sc._suggestion_cache):,} entries")
            active = getattr(sc, 'active_language', None)
            enabled = getattr(sc, 'enabled', False)
            status = f"{'Enabled' if enabled else 'Disabled'}"
            if enabled and active:
                status += f" ({active.upper()})"
            info.append(f"\nStatus: {status}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(self.main_window, "Dictionary Statistics", "\n".join(info))

        info_action.triggered.connect(show_dict_info)
        spell_menu.addAction(info_action)

    def _add_selection_actions(self, menu, editor):
        comment_menu = menu.addMenu("Comments")
        if self.editor_manager:
            if hasattr(self.editor_manager, 'toggle_latex_comments'):
                action = QAction("Toggle Comments (Ctrl+D)", comment_menu)
                action.triggered.connect(self.editor_manager.toggle_latex_comments)
                comment_menu.addAction(action)
            if hasattr(self.editor_manager, 'comment_latex_lines'):
                action = QAction("Comment Lines (Ctrl+/)", comment_menu)
                action.triggered.connect(self.editor_manager.comment_latex_lines)
                comment_menu.addAction(action)
            if hasattr(self.editor_manager, 'uncomment_latex_lines'):
                action = QAction("Uncomment Lines (Ctrl+Shift+/)", comment_menu)
                action.triggered.connect(self.editor_manager.uncomment_latex_lines)
                comment_menu.addAction(action)

        format_menu = menu.addMenu("Format Selection")
        quick_formats = [
            ("Bold", r"\textbf{%s}"),
            ("Italic", r"\emph{%s}"),
            ("Underline", r"\underline{%s}"),
            ("Typewriter", r"\texttt{%s}"),
            ("Math Mode", r"$%s$"),
        ]
        for label, template in quick_formats:
            action = QAction(label, format_menu)
            action.triggered.connect(
                lambda checked, t=template: self._wrap_selection(editor, t)
            )
            format_menu.addAction(action)

    def _add_latex_commands(self, menu, editor):
        latex_menu = menu.addMenu("LaTeX Commands")
        categories = {
            "Text Formatting": [
                ("Bold", r"\textbf{•}", "bold"),
                ("Italic", r"\emph{•}", "italic"),
                ("Underline", r"\underline{•}", "underline"),
                ("Small Caps", r"\textsc{•}", "format"),
                ("Typewriter", r"\texttt{•}", "code"),
            ],
            "Text Color": [
                ("Red", r"\textcolor{red}{•}", "color_red"),
                ("Blue", r"\textcolor{blue}{•}", "color_blue"),
                ("Green", r"\textcolor{green}{•}", "color_green"),
                ("Magenta", r"\textcolor{magenta}{•}", "color_magenta"),
                ("Cyan", r"\textcolor{cyan}{•}", "color_cyan"),
            ],            
            "Text Alignment": [
                ("Center", "\\begin{center}\n•\n\\end{center}", "align_center"),
                ("Flush Left", "\\begin{flushleft}\n•\n\\end{flushleft}", "align_left"),
                ("Flush Right", "\\begin{flushright}\n•\n\\end{flushright}", "align_right"),
            ],
            "Math": [
                ("Inline Math", r"$•$", "math_inline"),
                ("Display Math", r"\[•\]", "math"),
                ("Fraction", r"\frac{•}{•}", "fraction"),
                ("Square Root", r"\sqrt{•}", "sqrt"),
                ("Superscript", r"^{•}", "superscript"),
                ("Subscript", r"_{•}", "subscript"),
            ],
            "Font Size": [
                ("Tiny", r"{\tiny •}", "font_tiny"),
                ("Small", r"{\small •}", "font_small"),
                ("Normal", r"{\normalsize •}", "font_normal"),
                ("Large", r"{\large •}", "font_large"),
                ("Huge", r"{\huge •}", "font_huge"),
            ],
            "Environments": [
                ("Itemize", "\\begin{itemize}\n\\item •\n\\end{itemize}", "list_itemize"),
                ("Enumerate", "\\begin{enumerate}\n\\item •\n\\end{enumerate}", "list_enumerate"),
                ("Equation", "\\begin{equation}\n•\n\\end{equation}", "math"),
                ("Figure", "\\begin{figure}[htbp]\n\\centering\n\\includegraphics[width=0.8\\textwidth]{•}\n\\caption{•}\n\\label{fig:•}\n\\end{figure}", "image"),
                ("Table", "\\begin{table}[htbp]\n\\centering\n\\begin{tabular}{|c|c|}\n\\hline\n• & • \\\\\n\\hline\n\\end{tabular}\n\\caption{•}\n\\label{tab:•}\n\\end{table}", "table"),
            ],
        }

        for category, commands in categories.items():
            category_menu = latex_menu.addMenu(category)
            for label, latex_code, icon_name in commands:
                action = QAction(label, category_menu)
                self._apply_icon(action, icon_name)
                action.triggered.connect(
                    lambda checked, code=latex_code:
                    self._insert_latex(editor, code)
                )
                category_menu.addAction(action)


    def _add_additional_features(self, menu, editor):
        if hasattr(editor, 'toggle_current_line_bookmark'):
            bookmark_action = QAction("Toggle Bookmark (Ctrl+B)", menu)
            bookmark_action.triggered.connect(editor.toggle_current_line_bookmark)
            self._apply_icon(bookmark_action, "bookmark")
            menu.addAction(bookmark_action)

        # REPLACED: old toggle action with new spell check submenu
        if self.spell_checker:
            self._add_spell_check_submenu(menu)

        if hasattr(editor, 'toggle_fold_at_cursor'):
            fold_action = QAction("Toggle Fold", menu)
            fold_action.triggered.connect(editor.toggle_fold_at_cursor)
            menu.addAction(fold_action)

    # HELPER METHODS

    def _replace_word(self, editor, cursor, new_word):
        cursor.beginEditBlock()
        cursor.removeSelectedText()
        cursor.insertText(new_word)
        cursor.endEditBlock()
        editor.setTextCursor(cursor)

    def _add_to_dictionary(self, word):
        if self.spell_checker and hasattr(self.spell_checker, 'add_word_to_personal_dictionary'):
            self.spell_checker.add_word_to_personal_dictionary(word)

    def _wrap_selection(self, editor, template):
        cursor = editor.textCursor()
        if cursor.hasSelection():
            selected_text = cursor.selectedText()
            new_text = template % selected_text
            cursor.beginEditBlock()
            cursor.insertText(new_text)
            cursor.endEditBlock()

    def _insert_latex(self, editor, latex_code):
        cursor = editor.textCursor()
        if cursor.hasSelection():
            selected_text = cursor.selectedText()
            latex_code = latex_code.replace('•', selected_text, 1)
        placeholder_pos = latex_code.find('•')
        clean_code = latex_code.replace('•', '')
        cursor.beginEditBlock()
        cursor.insertText(clean_code)
        cursor.endEditBlock()
        if placeholder_pos != -1:
            new_pos = cursor.position() - len(clean_code) + placeholder_pos
            cursor.setPosition(new_pos)
            editor.setTextCursor(cursor)

    def _toggle_spell_check(self):
        if self.spell_checker:
            if hasattr(self.spell_checker, 'toggle_spell_check'):
                self.spell_checker.toggle_spell_check()
            elif hasattr(self.spell_checker, 'enabled'):
                self.spell_checker.enabled = not self.spell_checker.enabled

    def cleanup_editor(self, editor):
        editor_id = id(editor)
        if editor_id in self._installed_editors:
            self._installed_editors.remove(editor_id)