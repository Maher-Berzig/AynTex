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

# ═══════════════════════════════════════════════════════════════════════════════
# Tab Bar Context Menu
# ═══════════════════════════════════════════════════════════════════════════════

from PyQt5.QtCore import QObject, QEvent
from PyQt5.QtWidgets import QTabWidget


class _TabBarFilter(QObject):
    """Event filter installed on a QTabBar.

    Qt does not reliably deliver customContextMenuRequested on tab bars because
    the parent QTabWidget may swallow the right-click before the tab bar sees it.

    IMPORTANT: we use parent=None intentionally.  If we parented to the tab bar,
    Qt would destroy the C++ QObject when the tab widget is destroyed during a
    layout switch — but the Python wrapper would remain in _filters, causing a
    RuntimeError on the next access.  With parent=None the Python list is the
    sole owner; _filters.clear() is the only thing that destroys the filter.
    We remove the event filter explicitly in detach() before the tab bar is
    destroyed, so there is never a dangling installEventFilter reference.
    """
    def __init__(self, tab_bar, slot):
        super().__init__(None)          # NO Qt parent — Python list owns lifetime
        self._slot = slot
        self._tab_bar = tab_bar
        tab_bar.installEventFilter(self)

    def detach(self):
        """Remove the event filter before the tab bar is destroyed."""
        try:
            if self._tab_bar is not None:
                self._tab_bar.removeEventFilter(self)
        except RuntimeError:
            pass   # C++ object already gone — nothing to do
        self._tab_bar = None

    def eventFilter(self, obj, event):
        try:
            if event.type() == QEvent.ContextMenu:
                self._slot(obj, event.pos())
                return True
        except RuntimeError:
            pass   # underlying C++ object was destroyed mid-flight
        return False


class TabContextMenu:
    """
    Installs a right-click context menu on editor and PDF tab bars.

    Usage (call once after the tab widgets are ready, store the instance):
        self.tab_context_menu = TabContextMenu(self)
        self.tab_context_menu.install()

    Call reinstall() after any layout switch that replaces the tab widgets:
        self.tab_context_menu.reinstall()
    """

    def __init__(self, main_window):
        self.main_window = main_window
        # Keep references so the filters aren't garbage-collected
        self._filters = []
        self._pdf_filters = set()   # subset of _filters belonging to PDF tab bars

    # ── public ────────────────────────────────────────────────────────────────

    def install(self):
        """Install context menus on both editor and PDF tab bars."""
        self._install_editor_tabs()
        self._install_pdf_tabs()

    def reinstall(self):
        """Re-install after a layout switch that replaced ALL tab widgets."""
        for f in self._filters:
            f.detach()
        self._filters.clear()
        self._pdf_filters.clear()
        self.install()

    def reinstall_editor(self):
        """Re-install only the editor tab bar filters.

        Use this instead of reinstall() when only editor_tabs changed (e.g.
        inside _recreate_editor_container).  Calling the full reinstall() from
        there is dangerous: _install_pdf_tabs() iterates pdf_files entries whose
        QTabWidget objects may already have been destroyed by a concurrent PDF
        layout switch, causing a RuntimeError on tw.tabBar().
        """
        # Detach and remove only the non-PDF (editor) filters
        surviving = []
        for f in self._filters:
            if f not in self._pdf_filters:
                f.detach()
            else:
                surviving.append(f)
        self._filters = surviving
        # Re-install editor tab bars only
        self._install_editor_tabs()

    def detach_pdf(self):
        """Detach only the PDF tab bar filters (call BEFORE destroying old PDF widgets)."""
        surviving = []
        for f in self._filters:
            if f in self._pdf_filters:
                f.detach()
            else:
                surviving.append(f)
        self._filters = surviving
        self._pdf_filters.clear()

    def reinstall_pdf(self):
        """Install fresh PDF tab bar filters after new PDF widgets are created."""
        self._install_pdf_tabs()

    # ── installation helpers ───────────────────────────────────────────────────

    def _install_editor_tabs(self):
        em = getattr(self.main_window, 'editor_manager', None)
        if not em:
            return
        tabs = getattr(em, 'editor_tabs', None)
        if tabs is None:
            return
        if isinstance(tabs, QTabWidget):
            try:
                self._attach(tabs.tabBar(), self._show_editor_menu)
            except RuntimeError:
                pass   # QTabWidget already destroyed
        elif isinstance(tabs, list):
            for tw in tabs:
                if not isinstance(tw, QTabWidget):
                    continue
                try:
                    self._attach(tw.tabBar(), self._show_editor_menu)
                except RuntimeError:
                    pass   # stale entry — QTabWidget already destroyed

    def _install_pdf_tabs(self):
        pm = getattr(self.main_window, 'pdf_manager', None)
        if not pm:
            return
        attached = set()   # avoid double-attaching the same tab bar

        pdf_tabs = getattr(pm, 'pdf_tabs', None)

        # Tabbed mode: pdf_tabs is a single QTabWidget
        if isinstance(pdf_tabs, QTabWidget):
            try:
                tb = pdf_tabs.tabBar()
                if id(tb) not in attached:
                    self._attach(tb, self._show_pdf_menu, is_pdf=True)
                    attached.add(id(tb))
            except RuntimeError:
                pass   # QTabWidget already destroyed — skip

        # H/V mode: pdf_tabs is [] — each PDF lives in its own QTabWidget
        # stored as pdf_files[path]['tab_widget']
        if hasattr(pm, 'pdf_files'):
            for path, data in pm.pdf_files.items():
                if not isinstance(data, dict):
                    continue
                tw = data.get('tab_widget')
                if not isinstance(tw, QTabWidget):
                    continue
                try:
                    tb = tw.tabBar()   # raises RuntimeError if C++ object gone
                    if id(tb) not in attached:
                        self._attach(tb, self._show_pdf_menu, is_pdf=True)
                        attached.add(id(tb))
                except RuntimeError:
                    pass   # stale entry — QTabWidget already destroyed

    def _attach(self, tab_bar, slot, is_pdf=False):
        """Attach an event-filter-based context menu to *tab_bar*."""
        f = _TabBarFilter(tab_bar, slot)
        self._filters.append(f)     # keep alive
        if is_pdf:
            self._pdf_filters.add(f)

    # ─────────────────────────────────────────────────────────────────────────
    # EDITOR tab context menu
    # ─────────────────────────────────────────────────────────────────────────

    def _show_editor_menu(self, tab_bar, pos):
        from PyQt5.QtWidgets import QMenu, QAction, QTabWidget
        tab_index = tab_bar.tabAt(pos)
        if tab_index < 0:
            return

        # Resolve the tab widget that owns this bar
        tab_widget = tab_bar.parent()
        if not isinstance(tab_widget, QTabWidget):
            return

        # Find the file path for this tab
        file_path = self._file_path_for_tab(tab_widget, tab_index)
        em = self.main_window.editor_manager

        # True when the tab is a welcome/untitled placeholder with no real file
        is_empty = not bool(file_path)

        menu = QMenu(tab_bar)

        # ── header ────────────────────────────────────────────────────────
        if file_path:
            header = QAction(os.path.basename(file_path), menu)
        else:
            header = QAction(tab_widget.tabText(tab_index), menu)
        f = header.font(); f.setBold(True); header.setFont(f)
        header.setEnabled(False)
        menu.addAction(header)
        menu.addSeparator()

        # ── open group ────────────────────────────────────────────────────
        open_act = QAction("Open\tCtrl+O", menu)
        open_act.triggered.connect(lambda: self._editor_open())
        self._icon(open_act, 'open')
        menu.addAction(open_act)
        menu.addSeparator()

        # ── save group ────────────────────────────────────────────────────
        is_modified = False
        if file_path and file_path in em.editor_files:
            is_modified = em.editor_files[file_path].get('modified', False)

        save_act = QAction("Save\tCtrl+S", menu)
        save_act.setEnabled(not is_empty and is_modified)
        save_act.triggered.connect(lambda: self._editor_save(file_path))
        self._icon(save_act, 'save')
        menu.addAction(save_act)

        saveas_act = QAction("Save As…", menu)
        saveas_act.setEnabled(not is_empty)
        saveas_act.triggered.connect(lambda: em.save_as_file())
        self._icon(saveas_act, 'save_as')
        menu.addAction(saveas_act)

        savecopy_act = QAction("Save a Copy As…", menu)
        savecopy_act.setEnabled(not is_empty)
        savecopy_act.triggered.connect(lambda: em.save_copy_as())
        self._icon(savecopy_act, 'save_copy_as')
        menu.addAction(savecopy_act)

        menu.addSeparator()

        # ── close group ───────────────────────────────────────────────────
        close_act = QAction("Close", menu)
        close_act.triggered.connect(
            lambda: self._editor_close_tab(tab_widget, tab_index, file_path)
        )
        self._icon(close_act, 'close_tex')
        menu.addAction(close_act)

        close_others_act = QAction("Close Others", menu)
        close_others_act.setEnabled(not is_empty and tab_widget.count() > 1)
        close_others_act.triggered.connect(
            lambda: self._editor_close_others(tab_widget, tab_index)
        )
        menu.addAction(close_others_act)

        close_all_act = QAction("Close All Tex Files", menu)
        close_all_act.setEnabled(not is_empty and tab_widget.count() > 0)
        close_all_act.triggered.connect(
            lambda: self._editor_close_all(tab_widget)
        )
        self._icon(close_all_act, 'close_all_tex')
        menu.addAction(close_all_act)

        menu.addSeparator()

        # ── file identity ─────────────────────────────────────────────────
        path_menu = menu.addMenu("Copy Path")
        copy_full_act = QAction("Full Path", path_menu)
        copy_full_act.setEnabled(not is_empty)
        copy_full_act.triggered.connect(
            lambda: QApplication.clipboard().setText(file_path or '')
        )
        path_menu.addAction(copy_full_act)

        copy_name_act = QAction("File Name Only", path_menu)
        copy_name_act.setEnabled(not is_empty)
        copy_name_act.triggered.connect(
            lambda: QApplication.clipboard().setText(
                os.path.basename(file_path) if file_path else ''
            )
        )
        path_menu.addAction(copy_name_act)

        copy_dir_act = QAction("Folder Path", path_menu)
        copy_dir_act.setEnabled(not is_empty)
        copy_dir_act.triggered.connect(
            lambda: QApplication.clipboard().setText(
                os.path.dirname(file_path) if file_path else ''
            )
        )
        path_menu.addAction(copy_dir_act)

        open_folder_act = QAction("Open Containing Folder", menu)
        open_folder_act.setEnabled(not is_empty and os.path.exists(file_path))
        open_folder_act.triggered.connect(lambda: self._open_folder(file_path))
        self._icon(open_folder_act, 'folder')
        menu.addAction(open_folder_act)

        open_external_act = QAction("Open in External Editor", menu)
        open_external_act.setEnabled(not is_empty and os.path.exists(file_path))
        open_external_act.triggered.connect(lambda: self._open_external(file_path))
        menu.addAction(open_external_act)

        menu.addSeparator()

        # ── rename ────────────────────────────────────────────────────────
        rename_act = QAction("Rename File…", menu)
        rename_act.setEnabled(not is_empty and os.path.exists(file_path))
        rename_act.triggered.connect(lambda: self._rename_file(file_path, tab_widget, tab_index))
        menu.addAction(rename_act)

        menu.addSeparator()

        # ── print ─────────────────────────────────────────────────────────
        print_act = QAction("Print…", menu)
        print_act.setEnabled(not is_empty)
        print_act.triggered.connect(lambda: self._print_editor_file(file_path))
        self._icon(print_act, 'print')
        menu.addAction(print_act)

        menu.addSeparator()

        # ── view / layout ─────────────────────────────────────────────────
        layout_menu = menu.addMenu("Editor Layout")
        for mode, label in [("tabbed", "Tabbed"), ("horizontal", "Horizontal"), ("vertical", "Vertical")]:
            act = QAction(label, layout_menu)
            act.setCheckable(True)
            act.setChecked(em.editor_layout_mode == mode)
            act.triggered.connect(lambda chk, m=mode: self._set_editor_layout(m))
            layout_menu.addAction(act)

        zoom_in_act = QAction("Zoom In\tCtrl++", menu)
        zoom_in_act.setEnabled(not is_empty)
        zoom_in_act.triggered.connect(lambda: self._editor_zoom(file_path, +1))
        menu.addAction(zoom_in_act)

        zoom_out_act = QAction("Zoom Out\tCtrl+-", menu)
        zoom_out_act.setEnabled(not is_empty)
        zoom_out_act.triggered.connect(lambda: self._editor_zoom(file_path, -1))
        menu.addAction(zoom_out_act)

        menu.addSeparator()

        # ── workflow ──────────────────────────────────────────────────────
        compile_act = QAction("Compile This File\tF5", menu)
        compile_act.setEnabled(not is_empty and file_path.lower().endswith('.tex'))
        compile_act.triggered.connect(lambda: self._compile_file(file_path))
        self._icon(compile_act, 'compile')
        menu.addAction(compile_act)

        menu.addSeparator()

        # ── view toggles ──────────────────────────────────────────────────
        sc = getattr(self.main_window, 'spell_checker', None)
        if sc is not None:
            spell_enabled = getattr(sc, 'enabled', False)
            spell_act = QAction(
                "Disable Spell Check" if spell_enabled else "Enable Spell Check", menu
            )
            spell_act.triggered.connect(
                lambda: sc._disable_all("") if spell_enabled
                else sc.set_language(getattr(sc, 'active_language', 'en') or 'en')
            )
            menu.addAction(spell_act)

        line_num_act = QAction("Toggle Line Numbers", menu)
        line_num_act.setCheckable(True)
        line_num_act.setChecked(getattr(self.main_window, 'is_line_numbers_visible', True))
        line_num_act.triggered.connect(
            lambda chk: self.main_window.menu_manager.toggle_line_numbers(chk)
            if hasattr(self.main_window, 'menu_manager') else None
        )
        menu.addAction(line_num_act)

        fold_act = QAction("Toggle Fold Markers", menu)
        fold_act.setCheckable(True)
        fold_act.setChecked(getattr(self.main_window, 'is_fold_markers_visible', True))
        fold_act.triggered.connect(
            lambda chk: self.main_window.menu_manager.toggle_fold_markers(chk)
            if hasattr(self.main_window, 'menu_manager') else None
        )
        menu.addAction(fold_act)

        menu.addSeparator()

        # ── master document ───────────────────────────────────────────────
        is_master = (
            bool(file_path) and
            hasattr(em, 'get_master_document') and
            em.get_master_document() == file_path
        )
        master_act = QAction(
            "★  This is the Master Document" if is_master else "Set as Master Document",
            menu
        )
        master_act.setEnabled(
            not is_empty and
            file_path.lower().endswith('.tex') and
            not is_master
        )
        master_act.triggered.connect(lambda: self._set_master(file_path))
        self._icon(master_act, 'flag')
        menu.addAction(master_act)

        if hasattr(em, 'get_master_document') and em.get_master_document():
            clear_master_act = QAction(
                f"Clear Master Document  [{os.path.basename(em.get_master_document())}]",
                menu
            )
            clear_master_act.triggered.connect(lambda: em.clear_master_document())
            menu.addAction(clear_master_act)

        menu.addSeparator()

        # ── tab appearance & order ────────────────────────────────────────
        show_full_path_act = QAction("Show Full Path in Tab", menu)
        show_full_path_act.setCheckable(True)
        show_full_path_act.setChecked(
            getattr(self.main_window, '_tabs_show_full_path', False)
        )
        show_full_path_act.triggered.connect(
            lambda chk: self._toggle_full_path_in_tabs(tab_widget, chk)
        )
        menu.addAction(show_full_path_act)

        move_left_act = QAction("Move Tab Left", menu)
        move_left_act.setEnabled(tab_index > 0)
        move_left_act.triggered.connect(
            lambda: tab_widget.tabBar().moveTab(tab_index, tab_index - 1)
        )
        menu.addAction(move_left_act)

        move_right_act = QAction("Move Tab Right", menu)
        move_right_act.setEnabled(tab_index < tab_widget.count() - 1)
        move_right_act.triggered.connect(
            lambda: tab_widget.tabBar().moveTab(tab_index, tab_index + 1)
        )
        menu.addAction(move_right_act)

        # When no file is open, disable everything except Open
        if is_empty:
            self._disable_all_except(menu, open_act)

        menu.exec_(tab_bar.mapToGlobal(pos))

    # ─────────────────────────────────────────────────────────────────────────
    # PDF tab context menu
    # ─────────────────────────────────────────────────────────────────────────

    def _show_pdf_menu(self, tab_bar, pos):
        from PyQt5.QtWidgets import QMenu, QAction, QTabWidget
        tab_index = tab_bar.tabAt(pos)
        if tab_index < 0:
            return

        tab_widget = tab_bar.parent()
        if not isinstance(tab_widget, QTabWidget):
            return

        pm = self.main_window.pdf_manager

        # ── Resolve viewer and pdf_path ───────────────────────────────────
        # In tabbed mode: pdf_tabs is a shared QTabWidget; look up by viewer.
        # In H/V mode: each PDF has its own single-tab QTabWidget stored as
        # pdf_files[path]['tab_widget']; match by object identity.
        pdf_path = None
        viewer   = None

        if hasattr(pm, 'pdf_files'):
            for path, data in pm.pdf_files.items():
                if not isinstance(data, dict):
                    continue
                # H/V mode: match by the tab_widget object itself
                if data.get('tab_widget') is tab_widget:
                    pdf_path = path
                    viewer   = data.get('viewer')
                    break
                # Tabbed mode: match by live indexOf (not stale 'index')
                v = data.get('viewer')
                if v is not None:
                    live_idx = tab_widget.indexOf(v)
                    if live_idx == tab_index:
                        pdf_path = path
                        viewer   = v
                        data['index'] = live_idx   # keep cache in sync
                        break

        # Final fallback: widget at that tab position
        if viewer is None:
            viewer = tab_widget.widget(tab_index)

        menu = QMenu(tab_bar)

        # ── header ────────────────────────────────────────────────────────
        label = os.path.basename(pdf_path) if pdf_path else tab_widget.tabText(tab_index)
        header = QAction(label, menu)
        f = header.font(); f.setBold(True); header.setFont(f)
        header.setEnabled(False)
        menu.addAction(header)
        menu.addSeparator()

        # ── Open PDF (always available, even when welcome tab is shown) ───
        is_welcome = pdf_path is None   # True when the panel is empty / on welcome tab
        open_act = QAction("Open PDF…", menu)
        open_act.triggered.connect(
            lambda: pm.open_pdf_file() if hasattr(pm, 'open_pdf_file') else None
        )
        self._icon(open_act, 'pdf')
        menu.addAction(open_act)
        menu.addSeparator()

        # ── save group ────────────────────────────────────────────────────

        save_as_act = QAction("Save PDF as", menu)
        save_as_act.setEnabled(bool(pdf_path) and os.path.exists(pdf_path))
        save_as_act.triggered.connect(lambda: self._pdf_save_as(pdf_path))
        menu.addAction(save_as_act)
        
        menu.addSeparator()
        
        toggle_pdf_toolbar_act = QAction("Show Pdf Toolbar\tCtrl+F7", menu)
        toggle_pdf_toolbar_act.setCheckable(True)
        toggle_pdf_toolbar_act.setChecked(getattr(self.main_window, 'is_pdf_toolbar_visible', True))
        toggle_pdf_toolbar_act.toggled.connect(
            lambda checked: self.main_window.menu_manager.toggle_pdf_toolbar_action.trigger()
        )

        menu.addAction(toggle_pdf_toolbar_act)

        menu.addSeparator()        


        # ── close group ───────────────────────────────────────────────────
        close_act = QAction("Close", menu)
        close_act.setEnabled(not is_welcome)
        close_act.triggered.connect(
            lambda: pm.close_pdf_tab(tab_index)
            if hasattr(pm, 'close_pdf_tab') else None
        )
        self._icon(close_act, 'close_pdf')
        menu.addAction(close_act)

        close_others_act = QAction("Close Others", menu)
        close_others_act.setEnabled(not is_welcome and tab_widget.count() > 1)
        close_others_act.triggered.connect(
            lambda: self._pdf_close_others(pm, tab_widget, tab_index)
        )
        menu.addAction(close_others_act)

        close_all_act = QAction("Close All PDFs", menu)
        close_all_act.setEnabled(not is_welcome)
        close_all_act.triggered.connect(
            lambda: pm.close_all_pdfs() if hasattr(pm, 'close_all_pdfs') else None
        )
        self._icon(close_all_act, 'close_all_pdf')
        menu.addAction(close_all_act)

        menu.addSeparator()

        # ── file identity ─────────────────────────────────────────────────
        path_menu = menu.addMenu("Copy Path")
        for label_txt, fn in [
            ("Full Path",   lambda: pdf_path or ''),
            ("File Name",   lambda: os.path.basename(pdf_path) if pdf_path else ''),
            ("Folder Path", lambda: os.path.dirname(pdf_path) if pdf_path else ''),
        ]:
            act = QAction(label_txt, path_menu)
            act.setEnabled(bool(pdf_path))
            _fn = fn
            act.triggered.connect(lambda chk, f=_fn: QApplication.clipboard().setText(f()))
            path_menu.addAction(act)

        open_folder_act = QAction("Open Containing Folder", menu)
        open_folder_act.setEnabled(bool(pdf_path) and os.path.exists(str(pdf_path)))
        open_folder_act.triggered.connect(lambda: self._open_folder(pdf_path))
        self._icon(open_folder_act, 'folder')
        menu.addAction(open_folder_act)

        open_external_act = QAction("Open in External Viewer", menu)
        open_external_act.setEnabled(bool(pdf_path) and os.path.exists(str(pdf_path)))
        open_external_act.triggered.connect(lambda: self._open_external(pdf_path))
        menu.addAction(open_external_act)

        menu.addSeparator()

        # ── print ─────────────────────────────────────────────────────────
        print_act = QAction("Print…", menu)
        print_act.setEnabled(not is_welcome and viewer is not None and hasattr(viewer, 'print_pdf'))
        print_act.triggered.connect(lambda: viewer.print_pdf() if viewer else None)
        self._icon(print_act, 'print')
        menu.addAction(print_act)

        menu.addSeparator()

        # ── layout & view ─────────────────────────────────────────────────
        layout_menu = menu.addMenu("PDF Layout")
        for mode, label in [("tabbed", "Tabbed"), ("horizontal", "Horizontal"), ("vertical", "Vertical")]:
            act = QAction(label, layout_menu)
            act.setCheckable(True)
            act.setChecked(getattr(pm, 'pdf_layout_mode', 'tabbed') == mode)
            act.triggered.connect(lambda chk, m=mode: self._set_pdf_layout(m))
            layout_menu.addAction(act)

        zoom_in_act = QAction("Zoom In", menu)
        zoom_in_act.setEnabled(not is_welcome and viewer is not None)
        zoom_in_act.triggered.connect(
            lambda: viewer.zoom_in() if viewer and hasattr(viewer, 'zoom_in') else None
        )
        self._icon(zoom_in_act, 'zoom_in')
        menu.addAction(zoom_in_act)

        zoom_out_act = QAction("Zoom Out", menu)
        zoom_out_act.setEnabled(not is_welcome and viewer is not None)
        zoom_out_act.triggered.connect(
            lambda: viewer.zoom_out() if viewer and hasattr(viewer, 'zoom_out') else None
        )
        self._icon(zoom_out_act, 'zoom_out')
        menu.addAction(zoom_out_act)

        fit_width_act = QAction("Fit to Page Width", menu)
        fit_width_act.setEnabled(not is_welcome and viewer is not None)
        fit_width_act.triggered.connect(
            lambda: viewer.fit_page_width() if viewer and hasattr(viewer, 'fit_page_width') else None
        )
        
        self._icon(fit_width_act, 'fit_width')
        menu.addAction(fit_width_act)

        fit_page_act = QAction("Fit Page to Window", menu)
        fit_page_act.setEnabled(not is_welcome and viewer is not None)
        fit_page_act.triggered.connect(
            lambda: viewer.fit_page_to_window() if viewer and hasattr(viewer, 'fit_page_to_window') else None
        )
        self._icon(fit_page_act, 'fit_page')
        menu.addAction(fit_page_act)

        menu.addSeparator()

        # ── tab order ─────────────────────────────────────────────────────
        move_left_act = QAction("Move Tab Left", menu)
        move_left_act.setEnabled(tab_index > 0)
        move_left_act.triggered.connect(
            lambda: tab_widget.tabBar().moveTab(tab_index, tab_index - 1)
        )
        menu.addAction(move_left_act)

        move_right_act = QAction("Move Tab Right", menu)
        move_right_act.setEnabled(tab_index < tab_widget.count() - 1)
        move_right_act.triggered.connect(
            lambda: tab_widget.tabBar().moveTab(tab_index, tab_index + 1)
        )
        menu.addAction(move_right_act)

        # When no PDF is open (welcome tab), disable everything except Open PDF
        if is_welcome:
            self._disable_all_except(menu, open_act)

        menu.exec_(tab_bar.mapToGlobal(pos))

    # ─────────────────────────────────────────────────────────────────────────
    # Editor action helpers
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _disable_all_except(menu, keep_action):
        """Disable every action in *menu* (and all submenus) except *keep_action*.

        Called when the panel is empty so only the Open item stays active.
        """
        def _walk(m):
            for action in m.actions():
                if action is keep_action:
                    continue
                if action.isSeparator():
                    continue
                if action.menu():
                    _walk(action.menu())
                    action.setEnabled(False)
                else:
                    action.setEnabled(False)
        _walk(menu)

    def _editor_open(self):
        """Open a file via the editor manager's file dialog."""
        em = self.main_window.editor_manager
        if hasattr(em, 'open_file'):
            em.open_file()

    def _editor_save(self, file_path):
        self.main_window.editor_manager.save_file(path=file_path)

    def _editor_close_tab(self, tab_widget, tab_index, file_path):
        em = self.main_window.editor_manager
        if file_path:
            tab_widget.setCurrentIndex(tab_index)
            em.close_current_file()
        else:
            tab_widget.removeTab(tab_index)

    def _editor_close_others(self, tab_widget, keep_index):
        em = self.main_window.editor_manager
        paths_to_close = []
        for i in range(tab_widget.count()):
            if i != keep_index:
                paths_to_close.append(self._file_path_for_tab(tab_widget, i))
        for path in paths_to_close:
            if path and path in em.editor_files:
                idx = self._tab_index_for_path(tab_widget, path)
                if idx >= 0:
                    tab_widget.setCurrentIndex(idx)
                    em.close_current_file()

    def _editor_close_all(self, tab_widget):
        em = self.main_window.editor_manager
        paths = [self._file_path_for_tab(tab_widget, i)
                 for i in range(tab_widget.count())]
        for path in paths:
            if path and path in em.editor_files:
                idx = self._tab_index_for_path(tab_widget, path)
                if idx >= 0:
                    tab_widget.setCurrentIndex(idx)
                    em.close_current_file()

    def _compile_file(self, file_path):
        em = self.main_window.editor_manager
        cm = getattr(self.main_window, 'compilation_manager', None)
        if not cm:
            return
        master = em.get_master_document() if hasattr(em, 'get_master_document') else None
        if master and master != file_path:
            from PyQt5.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self.main_window.window(),
                "Master Document Set",
                f"A master document is set:\n{os.path.basename(master)}\n\n"
                f"Compile the master document instead of\n{os.path.basename(file_path)}?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            if reply == QMessageBox.Cancel:
                return
            if reply == QMessageBox.Yes:
                cm.compile_latex(self.main_window.latex_engine)
                return
        old_current = em.current_file
        em.current_file = file_path
        try:
            cm.compile_latex(self.main_window.latex_engine)
        finally:
            em.current_file = old_current

    def _print_editor_file(self, file_path):
        pdf_path = os.path.splitext(file_path)[0] + '.pdf' if file_path else None
        if pdf_path and os.path.exists(pdf_path):
            pm = getattr(self.main_window, 'pdf_manager', None)
            if pm:
                viewer = self._get_viewer_for_pdf(pm, pdf_path)
                if viewer and hasattr(viewer, 'print_pdf'):
                    viewer.print_pdf()
                    return
        if file_path and os.path.exists(file_path):
            import subprocess, sys
            if sys.platform == 'win32':
                os.startfile(file_path, 'print')
            else:
                subprocess.Popen(['lpr', file_path])

    def _editor_zoom(self, file_path, direction):
        em = self.main_window.editor_manager
        editor = None
        if file_path and file_path in em.editor_files:
            editor = em.editor_files[file_path].get('editor')
        if not editor:
            editor = em.get_current_editor()
        if not editor:
            return
        font = editor.font()
        size = max(6, font.pointSize() + direction)
        font.setPointSize(size)
        editor.setFont(font)

    def _set_editor_layout(self, mode):
        em = self.main_window.editor_manager
        lm = getattr(self.main_window, 'layout_manager', None)
        if not lm or em.editor_layout_mode == mode:
            return
        for _ in range(3):
            if em.editor_layout_mode == mode:
                break
            lm.toggle_editor_layout()

    def _set_pdf_layout(self, mode):
        pm = self.main_window.pdf_manager
        lm = getattr(self.main_window, 'layout_manager', None)
        if not lm or pm.pdf_layout_mode == mode:
            return
        for _ in range(3):
            if pm.pdf_layout_mode == mode:
                break
            lm.toggle_pdf_layout()

    def _rename_file(self, old_path, tab_widget, tab_index):
        from PyQt5.QtWidgets import QInputDialog, QMessageBox
        if not old_path or not os.path.exists(old_path):
            return
        old_name = os.path.basename(old_path)
        new_name, ok = QInputDialog.getText(
            self.main_window.window(), "Rename File",
            "New file name:", text=old_name
        )
        if not ok or not new_name.strip() or new_name == old_name:
            return
        new_path = os.path.join(os.path.dirname(old_path), new_name.strip())
        if os.path.exists(new_path):
            QMessageBox.warning(
                self.main_window.window(), "Rename Failed",
                f"A file named '{new_name}' already exists in that folder."
            )
            return
        try:
            os.rename(old_path, new_path)
        except OSError as e:
            QMessageBox.critical(self.main_window.window(), "Rename Failed", str(e))
            return
        em = self.main_window.editor_manager
        if old_path in em.editor_files:
            em.editor_files[new_path] = em.editor_files.pop(old_path)
        if em.current_file == old_path:
            em.current_file = new_path
        if hasattr(em, 'master_file') and em.master_file == old_path:
            em.master_file = new_path
        tab_widget.setTabText(tab_index, os.path.basename(new_path))
        self.main_window.update_status_bar(f"Renamed to {new_name}")

    def _set_master(self, file_path):
        em = self.main_window.editor_manager
        if hasattr(em, 'set_master_document'):
            try:
                em.set_master_document(file_path)
            except ValueError as e:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self.main_window.window(), "Master Document", str(e))

    def _toggle_full_path_in_tabs(self, tab_widget, show_full):
        self.main_window._tabs_show_full_path = show_full
        em = self.main_window.editor_manager
        for path, data in em.editor_files.items():
            editor = data.get('editor')
            if not editor:
                continue
            idx = self._tab_index_for_editor(tab_widget, editor)
            if idx >= 0:
                is_mod = data.get('modified', False)
                label = path if show_full else os.path.basename(path)
                if is_mod:
                    label = '*' + label
                if hasattr(em, 'master_file') and em.master_file == path:
                    label = '★ ' + label
                tab_widget.setTabText(idx, label)

    # ─────────────────────────────────────────────────────────────────────────
    # PDF action helpers
    # ─────────────────────────────────────────────────────────────────────────
    def _pdf_save_as(self, file_path):
        """Save a copy of the PDF to a user‑selected location."""
        if not file_path or not os.path.exists(file_path):
            return
        from PyQt5.QtWidgets import QFileDialog
        from shutil import copy2
        # Use the full path so the dialog opens in the PDF's own directory
        default_save_path = os.path.join(os.path.dirname(file_path), os.path.basename(file_path))
        save_path, _ = QFileDialog.getSaveFileName(
            self.main_window,
            "Save PDF As",
            default_save_path,
            "PDF Files (*.pdf)"
        )
        if save_path:
            try:
                copy2(file_path, save_path)
                self.main_window.update_status_bar(f"PDF saved as: {save_path}")
            except Exception as e:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.critical(
                    self.main_window,
                    "Save Failed",
                    f"Could not save PDF:\n{str(e)}"
                )
    def _pdf_close_others(self, pm, tab_widget, keep_index):
        for i in range(tab_widget.count() - 1, -1, -1):
            if i != keep_index and hasattr(pm, 'close_pdf_tab'):
                pm.close_pdf_tab(i)

    def _get_viewer_for_pdf(self, pm, pdf_path):
        if not hasattr(pm, 'pdf_files'):
            return None
        entry = pm.pdf_files.get(pdf_path)
        if entry:
            return entry[0] if isinstance(entry, tuple) else entry.get('viewer')
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # Lookup utilities
    # ─────────────────────────────────────────────────────────────────────────

    def _file_path_for_tab(self, tab_widget, tab_index):
        em = self.main_window.editor_manager
        widget = tab_widget.widget(tab_index)
        for path, data in em.editor_files.items():
            if data.get('editor') == widget:
                return path
        return None

    def _tab_index_for_path(self, tab_widget, file_path):
        em = self.main_window.editor_manager
        data = em.editor_files.get(file_path, {})
        editor = data.get('editor')
        if editor:
            return self._tab_index_for_editor(tab_widget, editor)
        return -1

    @staticmethod
    def _tab_index_for_editor(tab_widget, editor):
        for i in range(tab_widget.count()):
            if tab_widget.widget(i) == editor:
                return i
        return -1

    # ─────────────────────────────────────────────────────────────────────────
    # Shared utilities
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _open_folder(path):
        if not path:
            return
        folder = os.path.dirname(path) if os.path.isfile(path) else path
        import subprocess, sys
        if sys.platform == 'win32':
            import subprocess
            subprocess.Popen(['explorer', os.path.normpath(folder)])
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', folder])
        else:
            subprocess.Popen(['xdg-open', folder])

    @staticmethod
    def _open_external(path):
        if not path:
            return
        import subprocess, sys
        if sys.platform == 'win32':
            os.startfile(path)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', '-t', path])
        else:
            subprocess.Popen(['gedit', path])

    def _icon(self, action, name):
        im = getattr(self.main_window, 'icons_manager', None)
        if im and hasattr(im, 'apply_icon_to_action'):
            im.apply_icon_to_action(action, name)

