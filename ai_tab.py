# ai_tab.py
"""
AI Assistant Tab for PDF Viewer Zone
"""

import html
import json
import re
import os

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel,
    QGroupBox, QMessageBox, QSplitter, QListWidget, QListWidgetItem,
    QFrame, QTabWidget, QComboBox, QCheckBox, QApplication, QMenu, QAction,
    QInputDialog, QLineEdit, QFormLayout, QDialog, QDialogButtonBox
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QTextCursor,QPixmap, QFont, QColor, QIcon
#from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings 

from online_ai_provider import OnlineAIProvider, OnlineAIThread
# Try to import WebEngine early; set flag if it works
HAS_WEBENGINE = False
try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
    HAS_WEBENGINE = True
except ImportError:
    HAS_WEBENGINE = False
    print("⚠ QtWebEngineWidgets not available — using QTextEdit fallback for AI chat.")


class LaTeXAssistant:
    """Rule-based LaTeX assistant - no AI model needed"""
    def __init__(self):
        self.latex_help = self._load_latex_help()
        self.common_errors = self._load_common_errors()
        self.templates = self._load_templates()

    def _load_latex_help(self):
        """LaTeX command explanations"""
        return {
            r'\\documentclass': {
                'name': 'Document Class',
                'description': 'Defines the type of document (article, report, book, etc.)',
                'example': r'\documentclass[12pt,a4paper]{article}',
                'tips': 'Common classes: article, report, book, letter, beamer'
            },
            r'\\usepackage': {
                'name': 'Package Import',
                'description': 'Imports LaTeX packages for additional functionality',
                'example': r'\usepackage{graphicx, amsmath, hyperref}',
                'tips': 'Essential packages: graphicx (images), amsmath (math), hyperref (links)'
            },
            r'\\begin{document}': {
                'name': 'Document Body',
                'description': 'Marks the start of your document content',
                'example': r'\begin{document} ... \end{document}',
                'tips': 'All content must be between begin and end document'
            },
            r'\\section': {
                'name': 'Section Heading',
                'description': 'Creates a numbered section heading',
                'example': r'\section{Introduction}',
                'tips': 'Use section*, subsection, subsubsection for hierarchy'
            },
            r'\\textbf': {
                'name': 'Bold Text',
                'description': 'Makes text bold',
                'example': r'\textbf{important text}',
                'tips': 'For italic use \\textit{}, for underline use \\underline{}'
            },
            r'\\cite': {
                'name': 'Citation',
                'description': 'Inserts a citation reference',
                'example': r'\cite{author2023}',
                'tips': 'Requires bibliography with \\bibliography{} or bibtex'
            },
            r'\\ref': {
                'name': 'Cross Reference',
                'description': 'References a labeled element (figure, table, equation)',
                'example': r'\ref{fig:myimage}',
                'tips': 'Must have corresponding \\label{} in referenced item'
            },
        }

    def _load_common_errors(self):
        return [
            {
                'pattern': r'undefined control sequence',
                'cause': 'Misspelled command or missing package',
                'solution': 'Check command spelling and ensure required package is loaded',
                'example': r'\usepackage{amsmath} % for \align, \equation, etc.'
            },
            {
                'pattern': r'missing \$ inserted',
                'cause': 'Math symbols used outside math mode',
                'solution': 'Wrap math in $ $ or \\[ \\]',
                'example': r'Inline: $x^2$ or Display: \[x^2\]'
            },
            {
                'pattern': r'environment .* undefined',
                'cause': 'Using environment without loading package',
                'solution': 'Load the package that defines the environment',
                'example': r'\usepackage{amsmath} % for align, gather, etc.'
            },
        ]

    def _load_templates(self):
        return {
            'figure': {
                'name': 'Figure with Image',
                'code': r'''\begin{figure}[h]
    \centering
    \includegraphics[width=0.8\textwidth]{image.png}
    \caption{Your caption here}
    \label{fig:mylabel}
\end{figure}'''
            },
            'table': {
                'name': 'Basic Table',
                'code': r'''\begin{table}[h]
    \centering
    \begin{tabular}{|c|c|c|}
        \hline
        Header 1 & Header 2 & Header 3 \\
        \hline
        Row 1 & Data & Data \\
        \hline
    \end{tabular}
    \caption{Table caption}
    \label{tab:mytable}
\end{table}'''
            },
            'equation': {
                'name': 'Numbered Equation',
                'code': r'''\begin{equation}
    E = mc^2
    \label{eq:einstein}
\end{equation}'''
            },
            'itemize': {
                'name': 'Bullet List',
                'code': r'''\begin{itemize}
    \item First item
    \item Second item
\end{itemize}'''
            },
        }

    def explain_code(self, code):
        explanations = []
        for pattern, info in self.latex_help.items():
            if re.search(pattern, code, re.IGNORECASE):
                explanations.append(f"**{info['name']}**")
                explanations.append(f"{info['description']}")
                explanations.append(f"Example: `{info['example']}`")
                explanations.append(f"💡 {info['tips']}\n")
        if not explanations:
            return "Select LaTeX code with common commands (\\section, \\textbf, etc.) for explanation."
        return "\n".join(explanations)

    def improve_text(self, text):
        suggestions = []
        if text.isupper():
            suggestions.append("📝 Consider using sentence case instead of ALL CAPS")
        if len(text) > 200 and '.' not in text:
            suggestions.append("📝 Long paragraph - consider breaking into shorter sentences")
        if re.search(r'\b(important|key|crucial)\b', text, re.IGNORECASE):
            suggestions.append(r"💡 Emphasize key terms with \textbf{} or \emph{}")
        if not suggestions:
            suggestions.append("✓ Text looks good!")
        return "\n".join(suggestions)

    def fix_errors(self, error_text):
        suggestions = []
        for error in self.common_errors:
            if re.search(error['pattern'], error_text, re.IGNORECASE):
                suggestions.append(f"**{error['pattern']}**")
                suggestions.append(f"Cause: {error['cause']}")
                suggestions.append(f"Solution: {error['solution']}")
                suggestions.append(f"Example: `{error['example']}`\n")
        if not suggestions:
            suggestions.append("💡 General troubleshooting:")
            suggestions.append("• Check for missing packages")
            suggestions.append("• Ensure all { } are balanced")
            suggestions.append("• Verify file paths")
        return "\n".join(suggestions)

    def get_template(self, template_name):
        if template_name in self.templates:
            return self.templates[template_name]['code']
        return None

    def answer_question(self, question):
        question_lower = question.lower()
        if 'image' in question_lower or 'figure' in question_lower:
            return """**How to insert an image:**
1. Add package: \\usepackage{graphicx}
2. Insert image:
   \\begin{figure}[h]
       \\centering
       \\includegraphics[width=0.8\\textwidth]{image.png}
       \\caption{My image}
   \\end{figure}
3. Reference: See Figure \\ref{fig:myimage}"""
        elif 'table' in question_lower:
            return self.get_template('table')
        elif 'equation' in question_lower or 'math' in question_lower:
            return """**Math modes:**
Inline: $x^2 + y^2 = z^2$
Display: \\[E = mc^2\\]
Numbered:
\\begin{equation}
    F = ma
\\end{equation}"""
        elif 'citation' in question_lower or 'bibliography' in question_lower:
            return """**Citations:**
1. Create references.bib file
2. In document: \\cite{author2023}
3. At end: \\bibliography{references}
4. Compile: pdflatex → bibtex → pdflatex"""
        return "Ask about: images, tables, equations, citations, or common errors."


class AIAssistantWidget(QWidget):
    """Modern AI Assistant Widget for PDF Viewer Zone"""

    # AI Assistant context menu action definitions
    AI_CONTEXT_ACTIONS = [
        ("Rewrite for clarity", "Rewrite the following text for clarity. Return ONLY the rewritten text:\n\n{text}"),
        ("Simplify the language", "Simplify the language of the following text. Make it easier to understand. Return ONLY the simplified text:\n\n{text}"),
        ("Convert to numbered list", "Convert the following text into a numbered list. Return ONLY the numbered list:\n\n{text}"),
        ("Expand", "Expand the following text with more detail and explanation. Return ONLY the expanded text:\n\n{text}"),
        ("Summarize", "Summarize the following text concisely. Return ONLY the summary:\n\n{text}"),
        ("Shorten", "Shorten the following text while keeping the key meaning. Return ONLY the shortened text:\n\n{text}"),
        ("Explain", "Explain the following text in simple terms. Return ONLY the explanation:\n\n{text}"),
        ("Check grammar/spelling", "Check the following text for grammar and spelling errors. List each error and the correction. Then provide the corrected text:\n\n{text}"),
        ("Translate Arabic/English", None),  # Special handling
    ]

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.assistant = LaTeXAssistant()

        try:
            from online_ai_provider import OnlineAIProvider
            self.online_ai = OnlineAIProvider()
        except ImportError:
            self.online_ai = None

        self.online_mode = False
        self.ai_thread = None
        self.conversation_history = []
        self._current_action = None
        self._pending_replacement = None
        self._pending_translation = None
        self._pending_insert_position = None
        self._last_prompt = None
        self.auto_apply_check = None
        self.mode_indicator = None
        self.pdf_list = None
        self.continue_btn = None
        self.output_to_editor_btn = None
        self.new_topic_btn = None


        self._js_queue = []          # Store (js_code, callback) tuples
        self._web_ready = False      # Flag for page load completion
        self._processing_queue = False        
        
        self._setup_ui()

        QTimer.singleShot(1000, self._add_welcome_message)

    def _setup_ui(self):
        """Setup UI without header bar - mode button in chat controls"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # No header - go straight to splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        chat_widget = self._create_chat_area()
        splitter.addWidget(chat_widget)

        sidebar = self._create_sidebar()
        splitter.addWidget(sidebar)

        splitter.setSizes([700, 300])
        main_layout.addWidget(splitter, 1)

    # def refresh_styles(self):
        # """Rebuild all Qt widget styles and update web view CSS to match current theme."""
        # from style_manager import get_ai_tab_style
        # import json
        # s = get_ai_tab_style()

        # # Update web view via CSS variables (preserves chat history)
        # if self._use_webengine:
            # vars_dict = {
                # '--body-bg':             s['body_bg'],
                # '--body-color':          s['body_color'],
                # '--msg-system-bg':       s['msg_system_bg'],
                # '--msg-system-border':   s['msg_system_border'],
                # '--msg-user-bg':         s['msg_user_bg'],
                # '--msg-user-border':     s['msg_user_border'],
                # '--msg-assistant-bg':    s['msg_assistant_bg'],
                # '--msg-assistant-border':s['msg_assistant_border'],
                # '--label-system':        s['label_system'],
                # '--label-user':          s['label_user'],
                # '--label-assistant':     s['label_assistant'],
                # '--code-bg':             s['code_bg'],
                # '--code-color':          s['code_color'],
                # '--pre-bg':              s['pre_bg'],
                # '--pre-color':           s['pre_color'],
                # '--strong-color':        s['strong_color'],
                # '--blockquote-border':   s['blockquote_border'],
                # '--blockquote-bg':       s['blockquote_bg'],
                # '--blockquote-color':    s['blockquote_color'],
                # '--table-header-bg':     s['table_header_bg'],
                # '--table-border':        s['table_border'],
                # '--scrollbar-track':     s['scrollbar_track'],
                # '--scrollbar-thumb':     s['scrollbar_thumb'],
            # }
            # self._run_js_safe(f'updateTheme({json.dumps(vars_dict)});')
            # self.chat_display.setStyleSheet(
                # f"QWebEngineView {{ background-color: {s['body_bg']};"
                # f" border: 1px solid {s['chat_border']}; border-radius: 8px; }}"
            # )
        # else:
            # self.chat_display.setStyleSheet(
                # f"QTextEdit {{ background-color: {s['body_bg']}; color: {s['body_color']};"
                # f" border: 1px solid {s['chat_border']}; border-radius: 8px; padding: 8px; }}"
            # )

        # # Rebuild all Qt widgets with new theme colors
        # # (simplest: rebuild the entire UI in-place)
        # layout = self.layout()
        # if layout:
            # # Remove the splitter (first item)
            # item = layout.takeAt(0)
            # if item and item.widget():
                # item.widget().deleteLater()

        # self._setup_ui()

    def refresh_styles(self):
        """Update all widget styles to match current theme WITHOUT rebuilding UI."""
        from style_manager import get_ai_tab_style
        import json
        s = get_ai_tab_style()

        # ── 1. Update the web view via CSS variables (preserves chat history) ──
        if self._use_webengine:
            vars_dict = {
                '--body-bg':              s['body_bg'],
                '--body-color':           s['body_color'],
                '--msg-system-bg':        s['msg_system_bg'],
                '--msg-system-border':    s['msg_system_border'],
                '--msg-user-bg':          s['msg_user_bg'],
                '--msg-user-border':      s['msg_user_border'],
                '--msg-assistant-bg':     s['msg_assistant_bg'],
                '--msg-assistant-border': s['msg_assistant_border'],
                '--label-system':         s['label_system'],
                '--label-user':           s['label_user'],
                '--label-assistant':      s['label_assistant'],
                '--code-bg':              s['code_bg'],
                '--code-color':           s['code_color'],
                '--pre-bg':               s['pre_bg'],
                '--pre-color':            s['pre_color'],
                '--strong-color':         s['strong_color'],
                '--blockquote-border':    s['blockquote_border'],
                '--blockquote-bg':        s['blockquote_bg'],
                '--blockquote-color':     s['blockquote_color'],
                '--table-header-bg':      s['table_header_bg'],
                '--table-border':         s['table_border'],
                '--scrollbar-track':      s['scrollbar_track'],
                '--scrollbar-thumb':      s['scrollbar_thumb'],
            }
            self._run_js_safe(f'updateTheme({json.dumps(vars_dict)});')
            self.chat_display.setStyleSheet(
                f"QWebEngineView {{ background-color: {s['body_bg']};"
                f" border: 1px solid {s['chat_border']}; border-radius: 8px; }}"
            )
        else:
            self.chat_display.setStyleSheet(
                f"QTextEdit {{ background-color: {s['body_bg']}; color: {s['body_color']};"
                f" border: 1px solid {s['chat_border']}; border-radius: 8px; padding: 8px; }}"
            )

        # ── 2. Update input frame ──
        if hasattr(self, 'input_text'):
            input_frame = self.input_text.parent()
            if input_frame:
                input_frame.setStyleSheet(
                    f"QFrame#ai_input_frame {{ background-color: {s['input_bg']};"
                    f" border: 2px solid {s['input_border']}; border-radius: 8px; }}"
                )

        # ── 3. Update neutral buttons (Clear, output_to_editor_btn) ──
        neutral_style = (
            f"QPushButton {{ background-color: {s['action_btn_bg']}; color: {s['body_color']};"
            f" border: 1px solid {s['chat_border']}; border-radius: 4px; padding: 8px; }}"
            f"QPushButton:hover {{ background-color: {s['action_btn_hover']}; }}"
        )
        checked_style = (
            f"QPushButton {{ background-color: {s['action_btn_bg']}; color: {s['body_color']};"
            f" border: 1px solid {s['chat_border']}; border-radius: 4px; padding: 8px; }}"
            f"QPushButton:checked {{ background-color: #4caf50; color: white;"
            f" border: 1px solid #45a049; }}"
            f"QPushButton:hover {{ background-color: {s['action_btn_hover']}; }}"
            f"QPushButton:checked:hover {{ background-color: #45a049; }}"
        )

        if hasattr(self, 'clear_btn') and self.clear_btn:
            try:
                self.clear_btn.setStyleSheet(neutral_style)
            except RuntimeError:
                pass

        if hasattr(self, 'output_to_editor_btn') and self.output_to_editor_btn:
            try:
                self.output_to_editor_btn.setStyleSheet(checked_style)
            except RuntimeError:
                pass

        # ── 4. Update mode indicator (keeps its own green/orange colors) ──
        try:
            self._update_mode_indicator()
        except (RuntimeError, AttributeError):
            pass

        # ── 5. Update sidebar action buttons ──
        btn_style = (
            f"QPushButton {{ background-color: {s['action_btn_bg']};"
            f" border: 1px solid {s['action_btn_border']}; color: {s['body_color']};"
            f" border-radius: 4px; padding: 12px 8px; text-align: left; }}"
            f"QPushButton:hover {{ background-color: {s['action_btn_hover']}; }}"
            f"QPushButton:pressed {{ background-color: {s['list_selected']}; }}"
        )
        for btn in self.findChildren(QPushButton):
            try:
                # Skip buttons with intentional fixed colors (green, orange, purple, teal, blue)
                current = btn.styleSheet()
                fixed_colors = ['#4caf50', '#ff9800', '#9c27b0', '#00b7c3', '#0078d4',
                                '#45a049', '#f57c00', '#7b1fa2', '#009da8', '#106ebe']
                if any(c in current for c in fixed_colors):
                    continue
                btn.setStyleSheet(btn_style)
            except RuntimeError:
                pass

        # ── 6. Update group boxes ──
        group_style = (
            f"QGroupBox {{ border: 2px solid {s['group_border']}; border-radius: 6px;"
            f" margin-top: 12px; padding: 10px 8px 8px 8px; font-weight: bold;"
            f" color: {s['body_color']}; }}"
            f"QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 5px;"
            f" color: {s['label_system']}; }}"
        )
        for grp in self.findChildren(QGroupBox):
            try:
                grp.setStyleSheet(group_style)
            except RuntimeError:
                pass

        # ── 7. Update list widgets ──
        list_style = (
            f"QListWidget {{ border: 1px solid {s['chat_border']}; border-radius: 4px;"
            f" background-color: {s['list_bg']}; color: {s['body_color']}; }}"
            f"QListWidget::item {{ padding: 8px; border-bottom: 1px solid {s['chat_border']}; }}"
            f"QListWidget::item:hover {{ background-color: {s['list_hover']}; }}"
            f"QListWidget::item:selected {{ background-color: {s['list_selected']};"
            f" color: {s['list_selected_color']}; }}"
        )
        for lst in self.findChildren(QListWidget):
            try:
                lst.setStyleSheet(list_style)
            except RuntimeError:
                pass

        # ── 8. Update tab widgets inside the sidebar ──
        tab_style = (
            f"QTabWidget::pane {{ border: 2px solid {s['sidebar_border']};"
            f" border-radius: 6px; background: {s['tab_pane_bg']}; }}"
            f"QTabBar::tab {{ background: {s['tab_bg']}; color: {s['tab_color']};"
            f" padding: 8px 12px; margin-right: 2px; border: 1px solid {s['chat_border']};"
            f" border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px; }}"
            f"QTabBar::tab:selected {{ background: {s['tab_selected_bg']};"
            f" color: {s['tab_selected_color']}; font-weight: bold; }}"
            f"QTabBar::tab:hover:!selected {{ background: {s['action_btn_hover']}; }}"
        )
        for tw in self.findChildren(QTabWidget):
            try:
                tw.setStyleSheet(tab_style)
            except RuntimeError:
                pass

        # ── 9. Update checkboxes ──
        if hasattr(self, 'auto_apply_check') and self.auto_apply_check:
            try:
                self.auto_apply_check.setStyleSheet(
                    f"QCheckBox {{ color: {s['body_color']}; margin-left: 3px; border: none; }}"
                )
            except RuntimeError:
                pass
    
    def set_online_mode(self, enabled, provider=None, api_key=None, model=None):
        self.online_mode = enabled
        if provider and api_key and self.online_ai:
            self.online_ai.set_provider(provider, api_key, model)
        try:
            self._update_mode_indicator()
        except (RuntimeError, AttributeError):
            pass
        try:
            if enabled:
                provider_name = self.online_ai.provider if self.online_ai else "Unknown"
                self._add_system_message(f"✓ Online AI enabled: {provider_name}")
            else:
                self._add_system_message("✓ Switched to offline mode")
        except (RuntimeError, AttributeError):
            pass

    def closeEvent(self, event):
        """Properly handle widget closure by stopping threads first."""
        self._stop_ai_thread()
        # Wait a moment for cleanup
        QApplication.processEvents()
        super().closeEvent(event)
        event.accept()

    def _stop_ai_thread(self):
        """Safely stop any running AI thread before starting a new one."""
        if self.ai_thread is not None:
            try:
                # First, disconnect all signals to prevent double-delivery
                try:
                    self.ai_thread.response_ready.disconnect()
                except (TypeError, RuntimeError):
                    pass
                try:
                    self.ai_thread.error_occurred.disconnect()  
                except (TypeError, RuntimeError):
                    pass
                try:
                    self.ai_thread.finished.disconnect()
                except (TypeError, RuntimeError):
                    pass
                
                # Check if thread is actually running
                if self.ai_thread.isRunning():
                    # Request graceful termination
                    self.ai_thread.quit()
                    
                    # Wait for thread to finish gracefully
                    if not self.ai_thread.wait(3000):  # Wait up to 3 seconds
                        #print("Warning: AI thread did not respond to quit(), terminating forcefully")
                        self.ai_thread.terminate()
                        if not self.ai_thread.wait(1000):  # Wait up to 1 more second
                            print("Error: AI thread could not be terminated")
                            
            except Exception as e:
                print(f"Warning: error stopping AI thread: {e}")
            finally:
                # Always schedule for deletion, even if errors occurred
                try:
                    self.ai_thread.deleteLater()
                except (TypeError, RuntimeError):
                    pass
                self.ai_thread = None


    def _update_mode_indicator(self):
        """Update the mode indicator button style"""
        if not hasattr(self, 'mode_indicator') or self.mode_indicator is None:
            return
        try:
            if self.online_mode:
                self.mode_indicator.setText("🌐 Online")
                self.mode_indicator.setStyleSheet("""
                    QPushButton {
                        color: white;
                        background-color: #4caf50;
                        padding: 8px 12px;
                        border-radius: 4px;
                        font-weight: bold;
                        border: none;
                        min-width: 80px;
                    }
                    QPushButton:hover {
                        background-color: #45a049;
                    }
                """)
            else:
                self.mode_indicator.setText("💾 Offline")
                self.mode_indicator.setStyleSheet("""
                    QPushButton {
                        color: white;
                        background-color: #ff9800;
                        padding: 8px 12px;
                        border-radius: 4px;
                        font-weight: bold;
                        border: none;
                        min-width: 80px;
                    }
                    QPushButton:hover {
                        background-color: #f57c00;
                    }
                """)
        except RuntimeError:
            pass

    def _toggle_mode(self):
        """Toggle between online and offline mode"""
        if not self.online_ai:
            QMessageBox.warning(
                self,
                "Online AI Not Available",
                "Online AI provider not installed.\n\n"
                "Please install: pip install requests\n"
                "Then add online_ai_provider.py to your project."
            )
            return

        new_mode = not self.online_mode

        # Check if online mode is configured
        if new_mode and not self.online_ai.is_configured():
            reply = QMessageBox.question(
                self,
                "Configure Online AI",
                "Online AI is not configured yet.\n\n"
                "Do you want to open Settings to configure it now?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self._open_settings_ai_tab()
            return

        # Switch mode
        self.online_mode = new_mode
        self._update_mode_indicator()

        if self.online_mode:
            provider_name = self.online_ai.provider if self.online_ai else "Unknown"
            self._add_system_message(f"✓ Switched to Online Mode ({provider_name})")
        else:
            self._add_system_message("✓ Switched to Offline Mode (rule-based)")

    def _open_settings_ai_tab(self):
        """Open Settings dialog directly on the AI Assistant tab"""
        try:
            # Method 1: Use SettingsManager.open_settings_to_ai_tab if available
            if hasattr(self.main_window, 'settings_manager'):
                sm = self.main_window.settings_manager
                if hasattr(sm, 'open_settings_to_ai_tab'):
                    sm.open_settings_to_ai_tab()
                    return

            # Method 2: Create SettingsDialog directly and switch to AI tab
            from settings_manager import SettingsDialog
            dialog = SettingsDialog(self.main_window)

            # Find the "AI Assistant" tab index
            ai_tab_index = -1
            for i in range(dialog.tab_widget.count()):
                if dialog.tab_widget.tabText(i) == "AI Assistant":
                    ai_tab_index = i
                    break

            if ai_tab_index >= 0:
                dialog.tab_widget.setCurrentIndex(ai_tab_index)

            result = dialog.exec_()
            if result == QDialog.Accepted:
                print("AI Settings applied successfully")
                # Refresh mode after settings change
                ai_mode = self.main_window.config_manager.get_config_value('ai', 'mode', 'offline')
                if ai_mode == 'online':
                    provider = self.main_window.config_manager.get_config_value('ai', 'provider', 'groq')
                    api_key = self.main_window.config_manager.get_config_value('ai', 'api_key', '')
                    model = self.main_window.config_manager.get_config_value('ai', 'model', '')
                    if api_key:
                        self.set_online_mode(True, provider, api_key, model)

        except Exception as e:
            print(f"Error opening settings to AI tab: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.information(
                self,
                "Settings",
                "Please go to Settings → AI Assistant to configure your API key.\n\n"
                "Recommended: Get a free Groq API key from console.groq.com"
            )
        
    def _create_chat_area(self):
        from style_manager import get_ai_tab_style, get_tooltip_qss
        s = get_ai_tab_style()
        t = get_tooltip_qss()

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        global HAS_WEBENGINE
        if HAS_WEBENGINE:
            from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
            self.chat_display = QWebEngineView()
            settings = self.chat_display.page().settings()
            settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
            settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
            self.chat_display.setStyleSheet(
                f"QWebEngineView {{ background-color: {s['body_bg']};"
                f" border: 1px solid {s['chat_border']}; border-radius: 8px; }}"
            )
            self._init_katex_display()
            self._use_webengine = True
        else:
            self.chat_display = QTextEdit()
            self.chat_display.setReadOnly(True)
            self.chat_display.setFont(QFont("Segoe UI", 10))
            self.chat_display.setStyleSheet(
                f"QTextEdit {{ background-color: {s['body_bg']}; color: {s['body_color']};"
                f" border: 1px solid {s['chat_border']}; border-radius: 8px; padding: 8px; }}"
            )
            self._use_webengine = False

        layout.addWidget(self.chat_display, 1)

        # Continue button — keep orange (intentional action color)
        self.continue_btn = QPushButton("⏩ Continue Response")
        self.continue_btn.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.continue_btn.setCursor(Qt.PointingHandCursor)
        self.continue_btn.setVisible(False)
        self.continue_btn.setStyleSheet("""
            QPushButton { background-color: #ff9800; color: white; border: none;
                          border-radius: 4px; padding: 8px 20px; }
            QPushButton:hover { background-color: #f57c00; }
        """)
        self.continue_btn.clicked.connect(self._continue_response)
        layout.addWidget(self.continue_btn)

        # Input frame
        input_frame = QFrame()
        input_frame.setObjectName("ai_input_frame")
        input_frame.setStyleSheet(
            f"QFrame#ai_input_frame {{ background-color: {s['input_bg']};"
            f" border: 2px solid {s['input_border']}; border-radius: 8px; }}"
        )
        input_layout = QVBoxLayout(input_frame)
        input_layout.setContentsMargins(8, 8, 8, 8)
        input_layout.setSpacing(8)

        self.input_text = QTextEdit()
        self.input_text.setMaximumHeight(80)
        self.input_text.setPlaceholderText("Ask about LaTeX... (Ctrl+Enter to send)")
        self.input_text.setFont(QFont("Segoe UI", 10))
        self.input_text.setStyleSheet("QTextEdit { border: none; background: transparent; }")
        self.input_text.installEventFilter(self)
        input_layout.addWidget(self.input_text)

        btn_layout = QHBoxLayout()

        # New Topic — keep purple
        self.new_topic_btn = QPushButton("🆕 Topic")
        self.new_topic_btn.setFixedWidth(80)
        self.new_topic_btn.setFont(QFont("Segoe UI", 9))
        self.new_topic_btn.setCursor(Qt.PointingHandCursor)
        self.new_topic_btn.setToolTip("Start a new conversation (clears history)")
        self.new_topic_btn.setStyleSheet("""
            QPushButton { background-color: #9c27b0; color: white; border: none;
                          border-radius: 4px; padding: 8px; }
            QPushButton:hover { background-color: #7b1fa2; }
        """ + t)
        self.new_topic_btn.clicked.connect(self._start_new_topic)
        self.new_topic_btn.clicked.connect(self._hide_continue_button)
        btn_layout.addWidget(self.new_topic_btn)

        # Output mode toggle — themed neutral
        self.output_to_editor_btn = QPushButton("💬 Chat")
        self.output_to_editor_btn.setFont(QFont("Segoe UI", 9))
        self.output_to_editor_btn.setCursor(Qt.PointingHandCursor)
        self.output_to_editor_btn.setCheckable(True)
        self.output_to_editor_btn.setChecked(False)
        self.output_to_editor_btn.setFixedWidth(80)
        self.output_to_editor_btn.setToolTip("Toggle output to chat or editor")
        self.output_to_editor_btn.clicked.connect(self._toggle_output_mode)
        self.output_to_editor_btn.clicked.connect(self._hide_continue_button)
        self.output_to_editor_btn.setStyleSheet(
            f"QPushButton {{ background-color: {s['action_btn_bg']}; color: {s['body_color']};"
            f" border: 1px solid {s['chat_border']}; border-radius: 4px; padding: 8px; }}"
            f"QPushButton:checked {{ background-color: #4caf50; color: white;"
            f" border: 1px solid #45a049; }}"
            f"QPushButton:hover {{ background-color: {s['action_btn_hover']}; }}"
            f"QPushButton:checked:hover {{ background-color: #45a049; }}"
        )
        btn_layout.addWidget(self.output_to_editor_btn)

        btn_layout.addStretch()

        # Mode indicator — keep green/orange (status colors)
        self.mode_indicator = QPushButton()
        self.mode_indicator.setFont(QFont("Segoe UI", 9))
        self.mode_indicator.setCursor(Qt.PointingHandCursor)
        self.mode_indicator.setToolTip("Click to toggle Online/Offline AI mode")
        self.mode_indicator.clicked.connect(self._toggle_mode)
        self._update_mode_indicator()
        btn_layout.addWidget(self.mode_indicator)

        btn_layout.addStretch()

        # Clear — themed neutral
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setFont(QFont("Segoe UI", 9))
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.setFixedWidth(80)
        self.clear_btn.setToolTip("Clear chat history")
        self.clear_btn.setStyleSheet(
            f"QPushButton {{ background-color: {s['action_btn_bg']}; color: {s['body_color']}; text-align: center;"
            f" border: 1px solid {s['chat_border']}; border-radius: 4px; padding: 8px; }}"
            f"QPushButton:hover {{ background-color: {s['action_btn_hover']}; }}"
        )
        self.clear_btn.clicked.connect(self._clear_chat)
        self.clear_btn.clicked.connect(self._hide_continue_button)
        btn_layout.addWidget(self.clear_btn)

        # Send — keep blue (primary action)
        self.send_btn = QPushButton("Send")
        self.send_btn.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.setFixedWidth(70)
        self.send_btn.setToolTip("Send message (Ctrl+Enter)")
        self.send_btn.setStyleSheet("""
            QPushButton { background-color: #0078d4; color: white; border: none;
                          border-radius: 4px; padding: 8px; }
            QPushButton:hover { background-color: #106ebe; }
        """)
        self.send_btn.clicked.connect(self._send_message)
        self.send_btn.clicked.connect(self._hide_continue_button)
        btn_layout.addWidget(self.send_btn)

        input_layout.addLayout(btn_layout)
        layout.addWidget(input_frame)
        return widget
    
    

    def _hide_continue_button(self):
        if hasattr(self, 'continue_btn') and self.continue_btn:
            self.continue_btn.setVisible(False)

    def _start_new_topic(self):
        if self.conversation_history:
            reply = QMessageBox.question(
                self, "Start New Topic",
                f"Current conversation has {len(self.conversation_history)} messages.\n\n"
                "Starting a new topic will clear the conversation history.\n"
                "Continue?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        self.conversation_history.clear()
        separator_text = "─" * 50
        js_code = f'addMessage("system", "🆕 New Topic Started", "{separator_text}<br>Previous conversation context cleared.<br>{separator_text}");'
        self._run_js_safe(js_code)
        #self.chat_display.page().runJavaScript(js_code)
        self._add_system_message("✓ New topic started. AI memory cleared.")

    def _toggle_output_mode(self):
        if self.output_to_editor_btn.isChecked():
            self.output_to_editor_btn.setText("📝 Editor")
        else:
            self.output_to_editor_btn.setText("💬 Chat")


    def _init_katex_display(self):
        """Initialize chat display with KaTeX support - fixes italic text interpretation"""
        from style_manager import get_ai_tab_style
        s = get_ai_tab_style()

        # Try to load KaTeX inline (base64 embedded)
        katex_css = ""
        katex_js = ""
        autorender_js = ""

        try:
            from katex_loader import load_katex_inline
            katex_css, katex_js, autorender_js = load_katex_inline()
            #print("✅ KaTeX loaded from local files (embedded)")
        except ImportError:
            print("⚠ katex_loader not found, using CDN fallback")
        except Exception as e:
            print(f"⚠ Error loading local KaTeX: {e}, using CDN fallback")

        # Determine if we use embedded or CDN
        if katex_css and katex_js and autorender_js:
            katex_head = f"""
            <style>
            /* KaTeX CSS embedded */
            {katex_css}
            </style>
            """
            katex_scripts = f"""
            <script>
            /* KaTeX JS embedded */
            {katex_js}
            </script>
            <script>
            /* Auto-render JS embedded */
            {autorender_js}
            </script>
            """
        else:
            katex_head = """
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
            """
            katex_scripts = """
            <script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/mhchem.min.js"></script>
            """

        # ── New style block using CSS variables for hot‑swappable themes ──
        theme_style = f"""
            <style>
            :root {{
                --body-bg:            {s['body_bg']};
                --body-color:         {s['body_color']};
                --msg-system-bg:      {s['msg_system_bg']};
                --msg-system-border:  {s['msg_system_border']};
                --msg-user-bg:        {s['msg_user_bg']};
                --msg-user-border:    {s['msg_user_border']};
                --msg-assistant-bg:   {s['msg_assistant_bg']};
                --msg-assistant-border:{s['msg_assistant_border']};
                --label-system:       {s['label_system']};
                --label-user:         {s['label_user']};
                --label-assistant:    {s['label_assistant']};
                --code-bg:            {s['code_bg']};
                --code-color:         {s['code_color']};
                --pre-bg:             {s['pre_bg']};
                --pre-color:          {s['pre_color']};
                --strong-color:       {s['strong_color']};
                --blockquote-border:  {s['blockquote_border']};
                --blockquote-bg:      {s['blockquote_bg']};
                --blockquote-color:   {s['blockquote_color']};
                --table-header-bg:    {s['table_header_bg']};
                --table-border:       {s['table_border']};
                --scrollbar-track:    {s['scrollbar_track']};
                --scrollbar-thumb:    {s['scrollbar_thumb']};
            }}
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                padding: 12px; margin: 0; line-height: 1.7; font-size: 15px;
                background-color: var(--body-bg);
                color: var(--body-color);
            }}
            .message {{
                margin-bottom: 15px; padding: 12px 15px; border-radius: 8px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                animation: fadeIn 0.3s ease;
            }}
            @keyframes fadeIn {{
                from {{ opacity: 0; transform: translateY(10px); }}
                to   {{ opacity: 1; transform: translateY(0); }}
            }}
            .system   {{ background-color: var(--msg-system-bg);
                         border-left: 4px solid var(--msg-system-border); }}
            .user     {{ background-color: var(--msg-user-bg);
                         border-left: 4px solid var(--msg-user-border); }}
            .assistant{{ background-color: var(--msg-assistant-bg);
                         border-left: 4px solid var(--msg-assistant-border); }}
            .label {{
                font-weight: bold; margin-bottom: 8px; font-size: 0.9em;
                padding-bottom: 5px; border-bottom: 1px solid rgba(0,0,0,0.08);
            }}
            .system .label   {{ color: var(--label-system); }}
            .user .label     {{ color: var(--label-user); }}
            .assistant .label{{ color: var(--label-assistant); }}
            .content {{
                margin-top: 8px; word-wrap: break-word; overflow-wrap: break-word;
                white-space: pre-wrap; line-height: 1.8;
            }}
            .content.rtl {{ direction: rtl; text-align: right; unicode-bidi: plaintext; }}
            .content.ltr {{ direction: ltr; text-align: left; }}
            strong, b {{ font-weight: bold; color: var(--strong-color); }}
            em, i     {{ font-style: italic; color: inherit; }}
            u         {{ text-decoration: underline; }}
            code {{
                background-color: var(--code-bg); color: var(--code-color);
                padding: 2px 6px; border-radius: 3px;
                font-family: 'Consolas','Courier New',monospace; font-size: 0.9em;
            }}
            pre {{
                background-color: var(--pre-bg); color: var(--pre-color);
                padding: 12px 15px; border-radius: 6px; overflow-x: auto;
                font-family: 'Consolas','Courier New',monospace;
                font-size: 0.9em; line-height: 1.5;
            }}
            pre code {{ background: none; padding: 0; color: inherit; }}
            ul, ol {{ margin: 10px 0; padding-left: 25px; }}
            .content.rtl ul, .content.rtl ol {{ padding-left: 0; padding-right: 25px; }}
            li {{ margin-bottom: 5px; }}
            h3 {{ color: var(--label-system);    margin: 15px 0 10px; font-size: 1.2em; }}
            h4 {{ color: var(--label-user);      margin: 12px 0 8px;  font-size: 1.1em; }}
            h5 {{ color: var(--label-assistant); margin: 10px 0 6px;  font-size: 1.05em;}}
            table {{ border-collapse: collapse; margin: 15px 0; width: 100%; }}
            td, th {{ border: 1px solid var(--table-border); padding: 8px 12px; text-align: left; }}
            .content.rtl td, .content.rtl th {{ text-align: right; }}
            th {{ background-color: var(--table-header-bg); font-weight: bold; }}
            tr:nth-child(even) {{ background-color: var(--body-bg); }}
            blockquote {{
                margin: 15px 0; padding: 10px 20px;
                border-left: 4px solid var(--blockquote-border);
                background-color: var(--blockquote-bg);
                font-style: italic; color: var(--blockquote-color);
            }}
            .content.rtl blockquote {{ border-left: none; border-right: 4px solid var(--blockquote-border); }}
            ::-webkit-scrollbar       {{ width: 8px; height: 8px; }}
            ::-webkit-scrollbar-track {{ background: var(--scrollbar-track); border-radius: 4px; }}
            ::-webkit-scrollbar-thumb {{ background: var(--scrollbar-thumb); border-radius: 4px; }}
            ::-webkit-scrollbar-thumb:hover {{ filter: brightness(1.2); }}
            /* KaTeX always LTR */
            .katex {{ direction: ltr !important; unicode-bidi: embed;
                      display: inline-block; font-size: 1.1em; }}
            .katex-display {{ direction: ltr !important; text-align: center !important;
                              unicode-bidi: embed; margin: 1em 0 !important;
                              padding: 12px 10px; border-radius: 6px;
                              background-color: rgba(128,128,128,0.06);
                              overflow-x: auto; overflow-y: hidden; }}
            </style>
        """

        html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        {katex_head}
        {theme_style}
    </head>
    <body>
        <div id="chat-content"></div>
        {katex_scripts}
        <script>
            window.isReady = false;
            window.katexLoaded = false;

            function checkKatex() {{
                if (typeof katex !== 'undefined' && typeof renderMathInElement !== 'undefined') {{
                    window.katexLoaded = true;
                    console.log('✅ KaTeX loaded successfully');
                    return true;
                }}
                return false;
            }}

            if (document.readyState === 'loading') {{
                document.addEventListener('DOMContentLoaded', function() {{
                    window.isReady = true;
                    checkKatex();
                }});
            }} else {{
                window.isReady = true;
                checkKatex();
            }}

            setTimeout(checkKatex, 100);
            setTimeout(checkKatex, 500);

            function containsArabic(text) {{
                return /[\\u0600-\\u06FF\\u0750-\\u077F\\u08A0-\\u08FF\\uFB50-\\uFDFF\\uFE70-\\uFEFF]/.test(text);
            }}

            function preprocessLatex(text) {{
                if (!text) return '';
                
                // Convert \\[...\\] to $$...$$
                text = text.replace(/\\\\\\[([\\s\\S]*?)\\\\\\]/g, function(match, p1) {{
                    return '$$' + p1.trim() + '$$';
                }});
                
                // Convert \\(...\\) to $...$
                text = text.replace(/\\\\\\(([\\s\\S]*?)\\\\\\)/g, function(match, p1) {{
                    return '$' + p1.trim() + '$';
                }});
                
                // Convert align/align* to aligned inside $$
                text = text.replace(/\\\\begin\\{{align\\*?\\}}([\\s\\S]*?)\\\\end\\{{align\\*?\\}}/g, function(match, p1) {{
                    if (match.startsWith('$$')) return match;
                    return '$$\\\\begin{{aligned}}' + p1 + '\\\\end{{aligned}}$$';
                }});
                
                // Convert cases to array
                text = text.replace(/\\\\begin\\{{cases\\}}([\\s\\S]*?)\\\\end\\{{cases\\}}/g, function(match, p1) {{
                    return '$$\\\\left\\\\{{\\\\begin{{array}}{{ll}}' + p1 + '\\\\end{{array}}\\\\right.$$';
                }});
                
                return text;
            }}

            function renderMathIn(element) {{
                if (!window.katexLoaded) {{
                    console.warn('KaTeX not loaded yet, retrying...');
                    setTimeout(function() {{ renderMathIn(element); }}, 200);
                    return;
                }}

                try {{
                    // IMPORTANT: Only render math in text nodes, skip HTML elements
                    // This prevents <em>, <strong>, etc. from being interpreted as math
                    renderMathInElement(element, {{
                        delimiters: [
                            {{left: "$$", right: "$$", display: true}},
                            {{left: "$", right: "$", display: false}}
                        ],
                        throwOnError: false,
                        strict: false,
                        trust: true,
                        // CRITICAL: Ignore these tags - don't look for math inside them
                        ignoredTags: [
                            'script', 'noscript', 'style', 'textarea', 'pre', 'code',
                            'em', 'i', 'strong', 'b', 'u', 'a', 'span', 'button'
                        ],
                        ignoredClasses: ['no-math', 'text-only'],
                        macros: {{
                            "\\\\RR": "\\\\mathbb{{R}}",
                            "\\\\NN": "\\\\mathbb{{N}}",
                            "\\\\ZZ": "\\\\mathbb{{Z}}",
                            "\\\\QQ": "\\\\mathbb{{Q}}",
                            "\\\\CC": "\\\\mathbb{{C}}"
                        }}
                    }});

                    // Fix direction for rendered math
                    element.querySelectorAll('.katex').forEach(function(el) {{
                        el.style.direction = 'ltr';
                        el.style.unicodeBidi = 'embed';
                    }});

                    element.querySelectorAll('.katex-display').forEach(function(el) {{
                        el.style.direction = 'ltr';
                        el.style.textAlign = 'center';
                        el.style.marginLeft = 'auto';
                        el.style.marginRight = 'auto';
                    }});

                    console.log('✅ Math rendered in element');
                }} catch(e) {{
                    console.error('KaTeX render error:', e);
                }}
            }}

            function addMessage(type, label, content) {{
                if (!window.isReady) {{
                    setTimeout(function() {{ addMessage(type, label, content); }}, 50);
                    return;
                }}

                var chatContent = document.getElementById('chat-content');
                if (!chatContent) {{
                    console.error('chat-content not found');
                    return;
                }}

                var messageDiv = document.createElement('div');
                messageDiv.className = 'message ' + type;

                var labelDiv = document.createElement('div');
                labelDiv.className = 'label';
                labelDiv.textContent = label;

                var contentDiv = document.createElement('div');
                contentDiv.className = 'content';

                // Check for Arabic content
                var plainText = content.replace(/<[^>]*>/g, '');
                if (containsArabic(plainText)) {{
                    contentDiv.classList.add('rtl');
                    messageDiv.setAttribute('dir', 'rtl');
                }} else {{
                    contentDiv.classList.add('ltr');
                    messageDiv.setAttribute('dir', 'ltr');
                }}

                // Preprocess LaTeX delimiters
                var processedContent = preprocessLatex(content);
                contentDiv.innerHTML = processedContent;

                messageDiv.appendChild(labelDiv);
                messageDiv.appendChild(contentDiv);
                chatContent.appendChild(messageDiv);

                // Render math (will skip ignored tags like <em>, <strong>)
                renderMathIn(contentDiv);

                // Second pass for safety
                setTimeout(function() {{
                    renderMathIn(contentDiv);
                }}, 300);

                // Scroll to bottom
                window.scrollTo(0, document.body.scrollHeight);
            }}

            function updateTheme(vars) {{
                const root = document.documentElement;
                for (const [key, value] of Object.entries(vars)) {{
                    root.style.setProperty(key, value);
                }}
                // Update body background immediately
                if (vars['--body-bg']) document.body.style.backgroundColor = vars['--body-bg'];
            }}

            function clearChat() {{
                var chatContent = document.getElementById('chat-content');
                if (chatContent) {{
                    chatContent.innerHTML = '';
                }}
            }}

            console.log('=== AI Chat KaTeX Display Initialized ===');
        </script>
    </body>
    </html>
        """
        self.chat_display.setHtml(html_template)

        # Connect loadFinished signal to know when the page is ready
        self.chat_display.loadFinished.connect(self._on_web_load_finished)
    
###
    def _on_web_load_finished(self, ok):
        if ok:
            self._web_ready = True
            self._process_js_queue()
            
    def _run_js_safe(self, js_code, callback=None):
        """Queue JavaScript code until page is ready, then execute."""
        if not self._use_webengine:
            return
        self._js_queue.append((js_code, callback))
        self._process_js_queue()

    def _process_js_queue(self):
        """Process queued JS calls if page is ready and not already processing."""
        if not self._use_webengine or self._processing_queue:
            return
        
        if self._web_ready:
            self._processing_queue = True
            # Execute all pending JS calls
            while self._js_queue:
                js_code, callback = self._js_queue.pop(0)
                if callback:
                    self.chat_display.page().runJavaScript(js_code, callback)
                else:
                    self.chat_display.page().runJavaScript(js_code)
            self._processing_queue = False
        else:
            # Page not ready, retry after a short delay
            QTimer.singleShot(100, self._process_js_queue)            
###


    def _auto_wrap_math(self, text):
        """Auto-wrap math-like patterns in $ delimiters - SAFE version"""
        # Don't touch text that already has math delimiters or environments
        if '$' in text or '\\[' in text or '\\(' in text:
            return text
        if '\\begin{' in text or '\\end{' in text:
            return text
        # Only wrap very simple patterns like x^2 or a_i (no backslash commands)
        # This avoids breaking LaTeX environments
        simple_math = r'(?<![\\a-zA-Z])([a-zA-Z0-9]+[\^_][a-zA-Z0-9{}]+)(?![a-zA-Z])'
        if re.search(r'[\^_]', text) and not re.search(r'\\', text):
            text = re.sub(simple_math, lambda m: f'${m.group(0)}$', text)
        return text
    
    def _fix_latex_formatting(self, text):
        text = re.sub(r'([^\n])\\\[', r'\1\n\\[', text)
        text = re.sub(r'\\\]([^\n])', r'\\]\n\1', text)
        text = re.sub(r'([a-zA-Z])\\\(', r'\1 \\(', text)
        text = re.sub(r'\\\)([a-zA-Z])', r'\\) \1', text)
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
        text = re.sub(r'\.([A-Z])', r'. \1', text)
        text = re.sub(r' {2,}', ' ', text)
        return text

    def _add_message_to_display(self, msg_type, label, content):
        """Add a message to the chat display (works with both WebEngine and QTextEdit fallback)"""
        if self._use_webengine:
            # WebEngine mode - use JavaScript
            js_code = f'addMessage({json.dumps(msg_type)}, {json.dumps(label)}, {json.dumps(content)});'
            self._run_js_safe(js_code)
            #self.chat_display.page().runJavaScript(js_code)
        else:
            # QTextEdit fallback mode
            from PyQt5.QtGui import QTextCharFormat, QColor, QTextCursor
            
            cursor = self.chat_display.textCursor()
            cursor.movePosition(QTextCursor.End)
            
            # Define colors for different message types
            colors = {
                'system': {'label': '#0078d4', 'bg': '#e3f2fd'},
                'user': {'label': '#106ebe', 'bg': '#fff9e6'},
                'assistant': {'label': '#00b7c3', 'bg': '#e8f5f3'},
            }
            color_info = colors.get(msg_type, colors['system'])
            
            # Insert label
            label_format = QTextCharFormat()
            label_format.setForeground(QColor(color_info['label']))
            label_format.setFontWeight(QFont.Bold)
            cursor.setCharFormat(label_format)
            cursor.insertText(f"{label}\n")
            
            # Strip HTML tags for plain text display
            plain_content = re.sub(r'<br\s*/?>', '\n', content)
            plain_content = re.sub(r'<[^>]+>', '', plain_content)
            plain_content = html.unescape(plain_content)
            
            # Insert content
            content_format = QTextCharFormat()
            content_format.setForeground(QColor('#333333'))
            cursor.setCharFormat(content_format)
            cursor.insertText(f"{plain_content}\n\n")
            
            self.chat_display.setTextCursor(cursor)
            self.chat_display.ensureCursorVisible()

    def _add_assistant_message(self, text):
        """Add assistant message with proper LaTeX handling"""
        # Check editor mode first
        if hasattr(self, 'output_to_editor_btn') and self.output_to_editor_btn.isChecked():
            self._insert_to_editor(text)
            text_preview = text[:100] + "..." if len(text) > 100 else text
            self.chat_backend.add_message("system", "✓ Inserted to Editor", html.escape(text_preview))
            return
        
        # Preprocess LaTeX content
        processed_text = self._preprocess_latex_for_display(text)
        
        # Send to chat backend
        self.chat_backend.add_message("assistant", "🤖 Assistant", processed_text)
        
    # def _preprocess_latex_for_display(self, text):
        # """Preprocess LaTeX text for KaTeX display - handles environments properly"""
        # if not text:
            # return ""

        # # Step 1: Extract and protect ALL math blocks
        # math_blocks = []

        # def save_math(match):
            # math_blocks.append(match.group(0))
            # return f'\x00MATH{len(math_blocks) - 1}\x00'

        # # Protect math environments first (highest priority)
        # math_envs = (
            # r'equation\*?|align\*?|gather\*?|multline\*?|'
            # r'eqnarray\*?|displaymath|math|flalign\*?|'
            # r'cases|pmatrix|bmatrix|vmatrix|Vmatrix|matrix|'
            # r'split|aligned|gathered'
        # )
        # text = re.sub(
            # rf'\\begin\{{({math_envs})\}}(.*?)\\end\{{\1\}}',
            # save_math, text, flags=re.DOTALL
        # )

        # # Protect display math: $$...$$, \[...\]
        # text = re.sub(r'\$\$(?!\$)(.*?)(?<!\$)\$\$', save_math, text, flags=re.DOTALL)
        # text = re.sub(r'\\\[(.*?)\\\]', save_math, text, flags=re.DOTALL)

        # # Protect inline math: \(...\), $...$
        # text = re.sub(r'\\\((.*?)\\\)', save_math, text, flags=re.DOTALL)
        # text = re.sub(r'(?<!\$)\$(?!\$)(.*?)(?<!\$)\$(?!\$)', save_math, text, flags=re.DOTALL)

        # # Step 2: Process non-math LaTeX commands
        # # Text formatting
        # text = re.sub(r'\\textbf\{([^}]+)\}', r'<strong>\1</strong>', text)
        # text = re.sub(r'\\textit\{([^}]+)\}', r'<em>\1</em>', text)
        # text = re.sub(r'\\emph\{([^}]+)\}', r'<em>\1</em>', text)
        # text = re.sub(r'\\underline\{([^}]+)\}', r'<u>\1</u>', text)
        # text = re.sub(r'\\texttt\{([^}]+)\}', r'<code>\1</code>', text)

        # # Sections
        # text = re.sub(r'\\section\*?\{([^}]+)\}', r'<h3>\1</h3>', text)
        # text = re.sub(r'\\subsection\*?\{([^}]+)\}', r'<h4>\1</h4>', text)
        # text = re.sub(r'\\subsubsection\*?\{([^}]+)\}', r'<h5>\1</h5>', text)

        # # Lists
        # text = re.sub(r'\\begin\{itemize\}', '<ul>', text)
        # text = re.sub(r'\\end\{itemize\}', '</ul>', text)
        # text = re.sub(r'\\begin\{enumerate\}', '<ol>', text)
        # text = re.sub(r'\\end\{enumerate\}', '</ol>', text)
        # text = re.sub(r'\\item\s*', '<li>', text)

        # # Paragraph breaks
        # text = re.sub(r'\\par\b\s*', '<br><br>', text)

        # # Special characters
        # text = text.replace('\\&', '&amp;')
        # text = text.replace('\\%', '%')
        # text = text.replace('\\#', '#')
        # text = text.replace('\\_', '_')
        # text = text.replace('\\{', '{')
        # text = text.replace('\\}', '}')
        # text = text.replace('\\quad', '&nbsp;&nbsp;&nbsp;&nbsp;')
        # text = text.replace('\\qquad', '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;')
        # text = text.replace('~', '&nbsp;')

        # # Step 3: Protect generated HTML tags before escaping
        # html_tags = []

        # def save_tag(match):
            # html_tags.append(match.group(0))
            # return f'\x00TAG{len(html_tags) - 1}\x00'

        # text = re.sub(
            # r'<(?:strong|em|u|code|h[3-5]|ul|ol|li|br|p|blockquote|pre)[^>]*>'
            # r'|</(?:strong|em|u|code|h[3-5]|ul|ol|li|br|p|blockquote|pre)>',
            # save_tag, text
        # )

        # # Escape remaining HTML
        # text = html.escape(text, quote=False)

        # # Restore HTML tags
        # for i, tag in enumerate(html_tags):
            # text = text.replace(f'\x00TAG{i}\x00', tag)

        # # Step 4: Convert newlines to <br>
        # text = text.replace('\n\n', '<br><br>')
        # text = text.replace('\n', '<br>')

        # # Step 5: Restore math blocks with proper KaTeX delimiters
        # for i, block in enumerate(math_blocks):
            # restored = block

            # # Handle \begin{env}...\end{env}
            # env_match = re.match(
                # rf'\\begin\{{({math_envs})\}}(.*?)\\end\{{\1\}}',
                # restored, flags=re.DOTALL
            # )
            # if env_match:
                # env_name = env_match.group(1)
                # env_content = env_match.group(2)

                # # Environments KaTeX supports directly
                # direct_support = [
                    # 'aligned', 'gathered', 'pmatrix', 'bmatrix',
                    # 'vmatrix', 'Vmatrix', 'matrix', 'cases', 'split'
                # ]
                # base_env = env_name.rstrip('*')

                # if base_env in direct_support:
                    # restored = f'$$\\begin{{{env_name}}}{env_content}\\end{{{env_name}}}$$'
                # elif base_env in ('align', 'gather', 'multline', 'flalign', 'eqnarray'):
                    # katex_env = 'aligned' if base_env in ('align', 'flalign', 'eqnarray') else 'gathered'
                    # restored = f'$$\\begin{{{katex_env}}}{env_content}\\end{{{katex_env}}}$$'
                # elif base_env in ('equation', 'displaymath', 'math'):
                    # restored = f'$${env_content}$$'
                # else:
                    # restored = f'$${env_content}$$'
            # elif restored.startswith('\\[') and restored.endswith('\\]'):
                # inner = restored[2:-2].strip()
                # restored = f'$${inner}$$'
            # elif restored.startswith('\\(') and restored.endswith('\\)'):
                # inner = restored[2:-2].strip()
                # restored = f'${inner}$'
            # # $...$ and $$...$$ are already in correct format

            # text = text.replace(f'\x00MATH{i}\x00', restored)

        # # Step 6: Clean up
        # text = re.sub(r'(<br>\s*){3,}', '<br><br>', text)

        # return text
    
    def _preprocess_latex_for_display(self, text):
        if not text:
            return ""

        math_envs_pattern = (
            r'equation\*?|align\*?|gather\*?|multline\*?|'
            r'eqnarray\*?|displaymath|math|flalign\*?|'
            r'cases|pmatrix|bmatrix|vmatrix|Vmatrix|matrix|'
            r'split|aligned|gathered'
        )

        # ── Step 1: Split text into math and non-math segments ──────────────
        # Instead of placeholders, we split the text into a list of segments:
        # each segment is either ('math', raw_latex) or ('text', plain_text)

        segments = []
        remaining = text

        # Patterns in priority order (most specific first)
        math_patterns = [
            # \begin{env}...\end{env}
            re.compile(
                rf'\\begin\{{(?:{math_envs_pattern})\}}.*?\\end\{{(?:{math_envs_pattern})\}}',
                re.DOTALL
            ),
            # $$...$$
            re.compile(r'\$\$(?!\$).*?(?<!\$)\$\$', re.DOTALL),
            # \[...\]
            re.compile(r'\\\[.*?\\\]', re.DOTALL),
            # \(...\)
            re.compile(r'\\\(.*?\\\)', re.DOTALL),
            # $...$  (inline, not $$)
            re.compile(r'(?<!\$)\$(?!\$).+?(?<!\$)\$(?!\$)'),
        ]

        # Build one combined pattern that matches any math
        combined = re.compile(
            r'(\\begin\{(?:' + math_envs_pattern + r')\}.*?\\end\{(?:' + math_envs_pattern + r')\}'
            r'|\$\$(?!\$).*?(?<!\$)\$\$'
            r'|\\\[.*?\\\]'
            r'|\\\(.*?\\\)'
            r'|(?<!\$)\$(?!\$).+?(?<!\$)\$(?!\$))',
            re.DOTALL
        )

        last_end = 0
        for m in combined.finditer(remaining):
            start, end = m.start(), m.end()
            if start > last_end:
                segments.append(('text', remaining[last_end:start]))
            segments.append(('math', remaining[start:end]))
            last_end = end
        if last_end < len(remaining):
            segments.append(('text', remaining[last_end:]))

        # ── Step 2: Process text segments (non-math) ────────────────────────
        def process_text(t):
            # LaTeX text formatting → HTML
            t = re.sub(r'\\textbf\{([^}]+)\}', r'<strong>\1</strong>', t)
            t = re.sub(r'\\textit\{([^}]+)\}', r'<em>\1</em>', t)
            t = re.sub(r'\\emph\{([^}]+)\}', r'<em>\1</em>', t)
            t = re.sub(r'\\underline\{([^}]+)\}', r'<u>\1</u>', t)
            t = re.sub(r'\\texttt\{([^}]+)\}', r'<code>\1</code>', t)
            t = re.sub(r'\\section\*?\{([^}]+)\}', r'<h3>\1</h3>', t)
            t = re.sub(r'\\subsection\*?\{([^}]+)\}', r'<h4>\1</h4>', t)
            t = re.sub(r'\\subsubsection\*?\{([^}]+)\}', r'<h5>\1</h5>', t)
            t = re.sub(r'\\begin\{itemize\}', '<ul>', t)
            t = re.sub(r'\\end\{itemize\}', '</ul>', t)
            t = re.sub(r'\\begin\{enumerate\}', '<ol>', t)
            t = re.sub(r'\\end\{enumerate\}', '</ol>', t)
            t = re.sub(r'\\item\s*', '<li>', t)
            t = re.sub(r'\\par\b\s*', '<br><br>', t)
            t = t.replace('\\&', '&amp;')
            t = t.replace('\\%', '%')
            t = t.replace('\\#', '#')
            t = t.replace('\\_', '_')
            t = t.replace('\\{', '{')
            t = t.replace('\\}', '}')
            t = t.replace('\\quad', '    ')
            t = t.replace('\\qquad', '        ')
            t = t.replace('~', '\u00a0')

            # Save HTML tags we just generated before escaping
            html_tags = []
            def save_tag(m):
                html_tags.append(m.group(0))
                return f'\x00T{len(html_tags)-1}\x00'
            t = re.sub(
                r'<(?:strong|em|u|code|h[3-5]|ul|ol|li|br|p|blockquote|pre)[^>]*>'
                r'|</(?:strong|em|u|code|h[3-5]|ul|ol|li|br|p|blockquote|pre)>',
                save_tag, t
            )

            # Escape remaining HTML chars
            t = html.escape(t, quote=False)

            # Restore saved HTML tags
            for i, tag in enumerate(html_tags):
                t = t.replace(f'\x00T{i}\x00', tag)

            # Newlines → <br>
            t = t.replace('\n\n', '<br><br>')
            t = t.replace('\n', '<br>')
            return t

        # ── Step 3: Process math segments → KaTeX delimiters ────────────────
        def process_math(block):
            direct_support = {
                'aligned', 'gathered', 'pmatrix', 'bmatrix',
                'vmatrix', 'Vmatrix', 'matrix', 'cases', 'split'
            }
            align_envs = {'align', 'gather', 'multline', 'flalign', 'eqnarray'}
            display_envs = {'equation', 'displaymath', 'math'}

            env_match = re.match(
                rf'\\begin\{{({math_envs_pattern})\}}(.*?)\\end\{{\1\}}',
                block, flags=re.DOTALL
            )
            if env_match:
                env_name = env_match.group(1)
                env_content = env_match.group(2)
                base_env = env_name.rstrip('*')
                if base_env in direct_support:
                    return f'$$\\begin{{{env_name}}}{env_content}\\end{{{env_name}}}$$'
                elif base_env in align_envs:
                    katex_env = 'aligned' if base_env in {'align', 'flalign', 'eqnarray'} else 'gathered'
                    return f'$$\\begin{{{katex_env}}}{env_content}\\end{{{katex_env}}}$$'
                else:  # equation, displaymath, math
                    return f'$${env_content}$$'
            elif block.startswith('\\[') and block.endswith('\\]'):
                return f'$${block[2:-2].strip()}$$'
            elif block.startswith('\\(') and block.endswith('\\)'):
                return f'${block[2:-2].strip()}$'
            else:
                return block  # Already $...$ or $$...$$

        # ── Step 4: Reassemble ───────────────────────────────────────────────
        parts = []
        for kind, content in segments:
            if kind == 'math':
                parts.append(process_math(content))
            else:
                parts.append(process_text(content))

        result = ''.join(parts)

        # Clean up excess line breaks
        result = re.sub(r'(<br>\s*){3,}', '<br><br>', result)
        return result
    def _clear_chat(self):
        """Clear chat history"""
        self.conversation_history.clear()
        
        if self._use_webengine:
            self._run_js_safe('clearChat();')
            #self.chat_display.page().runJavaScript('clearChat();')
        else:
            self.chat_display.clear()
        
        QTimer.singleShot(100, self._add_welcome_message)
    
    # def _clear_chat(self):
        # self.conversation_history.clear()
        # self.chat_display.page().runJavaScript('clearChat();')
        # QTimer.singleShot(100, self._add_welcome_message)


    def _add_assistant_message(self, text):
        """Add assistant message with proper LaTeX handling"""
        # Check editor mode first
        if hasattr(self, 'output_to_editor_btn') and self.output_to_editor_btn.isChecked():
            self._insert_to_editor(text)
            text_preview = text[:100] + "..." if len(text) > 100 else text
            self._add_message_to_display("system", "✓ Inserted to Editor", html.escape(text_preview))
            return
        
        # Preprocess LaTeX content
        processed_text = self._preprocess_latex_for_display(text)
        
        # Send to chat display
        self._add_message_to_display("assistant", "🤖 Assistant", processed_text)


    def _add_user_message(self, text):
        """Add user message with math support"""
        text = self._auto_wrap_math(text)

        # Step 1: Extract and protect ALL math (environments, display, inline)
        protected = []

        def protect(match):
            protected.append(match.group(0))
            return f'\x00MATH{len(protected) - 1}\x00'

        # Protect math environments: \begin{equation}...\end{equation}, etc.
        math_envs = (
            r'equation\*?|align\*?|gather\*?|multline\*?|'
            r'eqnarray\*?|displaymath|math|flalign\*?|'
            r'cases|pmatrix|bmatrix|vmatrix|Vmatrix|matrix|'
            r'split|aligned|gathered'
        )
        text = re.sub(
            rf'\\begin\{{({math_envs})\}}(.*?)\\end\{{\1\}}',
            protect, text, flags=re.DOTALL
        )

        # Protect display math: $$...$$, \[...\]
        text = re.sub(r'\$\$(.+?)\$\$', protect, text, flags=re.DOTALL)
        text = re.sub(r'\\\[(.+?)\\\]', protect, text, flags=re.DOTALL)

        # Protect inline math: $...$, \(...\)
        text = re.sub(r'\\\((.+?)\\\)', protect, text, flags=re.DOTALL)
        text = re.sub(r'(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)', protect, text)

        # Step 2: Escape HTML in non-math text
        text = html.escape(text, quote=False)
        text = text.replace('\n', '<br>')

        # Step 3: Restore math blocks, converting delimiters for KaTeX
        for i, block in enumerate(protected):
            restored = block

            # Convert \begin{equation}...\end{equation} → $$...$$
            env_match = re.match(
                rf'\\begin\{{({math_envs})\}}(.*?)\\end\{{\1\}}',
                restored, flags=re.DOTALL
            )
            if env_match:
                env_name = env_match.group(1)
                env_content = env_match.group(2)
                # Some environments KaTeX supports directly inside $$
                direct_support = [
                    'aligned', 'gathered', 'pmatrix', 'bmatrix',
                    'vmatrix', 'Vmatrix', 'matrix', 'cases', 'split'
                ]
                base_env = env_name.rstrip('*')
                if base_env in direct_support:
                    restored = f'$$\\begin{{{env_name}}}{env_content}\\end{{{env_name}}}$$'
                elif base_env in ('align', 'gather', 'multline', 'flalign', 'eqnarray'):
                    # Convert to aligned/gathered inside $$
                    katex_env = 'aligned' if base_env in ('align', 'flalign', 'eqnarray') else 'gathered'
                    restored = f'$$\\begin{{{katex_env}}}{env_content}\\end{{{katex_env}}}$$'
                elif base_env in ('equation', 'displaymath', 'math'):
                    restored = f'$${env_content}$$'
                else:
                    restored = f'$${env_content}$$'
            elif restored.startswith('\\[') and restored.endswith('\\]'):
                inner = restored[2:-2].strip()
                restored = f'$${inner}$$'
            elif restored.startswith('\\(') and restored.endswith('\\)'):
                inner = restored[2:-2].strip()
                restored = f'${inner}$'

            text = text.replace(f'\x00MATH{i}\x00', restored)

        self._add_message_to_display("user", "You", text)
    


    def _add_system_message(self, text):
        """Add system message"""
        safe_text = html.escape(text, quote=False)
        safe_text = safe_text.replace('\n', '<br>')
        self._add_message_to_display("system", "💡 System", safe_text)



    def _add_welcome_message(self):
        welcome_text = """Welcome to AI Assistant! 🚀
    I can help you with:
    - Explaining LaTeX commands
    - Providing code templates
    - Fixing compilation errors
    - Improving your text
    - Translating between Arabic/English
    Try the quick actions or ask me anything!"""
        if self.chat_display.page():
            self._add_system_message(welcome_text)
        else:
            QTimer.singleShot(500, self._add_welcome_message)

    def _create_sidebar(self):
        from style_manager import get_ai_tab_style
        s = get_ai_tab_style()

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        layout.addWidget(self._create_actions_group())

        templates_help_tabs = QTabWidget()
        templates_help_tabs.setStyleSheet(
            f"QTabWidget::pane {{ border: 2px solid {s['sidebar_border']};"
            f" border-radius: 6px; background: {s['tab_pane_bg']}; }}"
            f"QTabBar::tab {{ background: {s['tab_bg']}; color: {s['tab_color']};"
            f" padding: 8px 12px; margin-right: 2px; border: 1px solid {s['chat_border']};"
            f" border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px; }}"
            f"QTabBar::tab:selected {{ background: {s['tab_selected_bg']};"
            f" color: {s['tab_selected_color']}; font-weight: bold; }}"
            f"QTabBar::tab:hover:!selected {{ background: {s['action_btn_hover']}; }}"
        )

        templates_help_tabs.addTab(self._create_templates_tab(), "📄 Templates")
        templates_help_tabs.addTab(self._create_help_tab(), "❓ Help")
        templates_help_tabs.addTab(self._create_pdfs_tab(), "📑 PDFs")
        layout.addWidget(templates_help_tabs, 1)
        return widget


    def _create_actions_group(self):
        from style_manager import get_ai_tab_style, get_tooltip_qss
        s = get_ai_tab_style()
        t = get_tooltip_qss()

        group = QGroupBox("Quick Actions")
        group.setFont(QFont("Segoe UI", 9, QFont.Bold))
        group.setStyleSheet(
            f"QGroupBox {{ border: 2px solid {s['group_border']}; border-radius: 6px;"
            f" margin-top: 12px; padding: 10px 8px 8px 8px; font-weight: bold;"
            f" color: {s['body_color']}; }}"
            f"QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 5px;"
            f" color: {s['label_system']}; }}"
        )
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(5, 5, 5, 5)

        self.auto_apply_check = QCheckBox("Auto-apply changes to editor")
        self.auto_apply_check.setChecked(True)
        self.auto_apply_check.setFont(QFont("Segoe UI", 8))
        self.auto_apply_check.setStyleSheet(
            f"QCheckBox {{ color: {s['body_color']}; margin-left: 3px; border: none; }}"
        )
        layout.addWidget(self.auto_apply_check)

        btn_style = (
            f"QPushButton {{ background-color: {s['action_btn_bg']};"
            f" border: 1px solid {s['action_btn_border']}; color: {s['body_color']};"
            f" border-radius: 4px; padding: 12px 8px; text-align: left; }}"
            f"QPushButton:hover {{ background-color: {s['action_btn_hover']}; }}"
            f"QPushButton:pressed {{ background-color: {s['list_selected']}; }}"
        ) + t

        buttons = [
            ("📖 Explain Selection", self._explain_selection, "Explain selected LaTeX code"),
            ("✨ Improve Text",       self._improve_selection, "Improve and replace selected text"),
            ("🌐 Translate",          self._translate_selection, "Translate between Arabic/English"),
            ("🔧 Fix Errors",         self._fix_latex_errors, "Analyze compilation errors"),
            ("📄 Analyze PDF",        self._analyze_pdf, "Analyze PDF from list"),
        ]
        for text, callback, tooltip in buttons:
            btn = QPushButton(text)
            btn.setFont(QFont("Segoe UI", 9))
            btn.setToolTip(tooltip)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setMinimumHeight(40)
            btn.setStyleSheet(btn_style)
            btn.clicked.connect(callback)
            layout.addWidget(btn)

        layout.addStretch()
        return group


    def _create_templates_tab(self):
        from style_manager import get_ai_tab_style
        s = get_ai_tab_style()

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)

        self.template_list = QListWidget()
        self.template_list.setFont(QFont("Segoe UI", 9))
        self.template_list.setStyleSheet(
            f"QListWidget {{ border: 1px solid {s['chat_border']}; border-radius: 4px;"
            f" background-color: {s['list_bg']}; color: {s['body_color']}; }}"
            f"QListWidget::item {{ padding: 8px; border-bottom: 1px solid {s['chat_border']}; }}"
            f"QListWidget::item:hover {{ background-color: {s['list_hover']}; }}"
            f"QListWidget::item:selected {{ background-color: {s['list_selected']};"
            f" color: {s['list_selected_color']}; }}"
        )
        for template in ["📄 Figure with Image","📊 Basic Table",
                         "🔢 Numbered Equation","• Bullet List"]:
            self.template_list.addItem(template)
        self.template_list.itemDoubleClicked.connect(self._insert_template)
        layout.addWidget(self.template_list)

        insert_btn = QPushButton("Insert Template")
        insert_btn.setFont(QFont("Segoe UI", 9))
        insert_btn.setCursor(Qt.PointingHandCursor)
        # Keep teal — it's a distinct action color
        insert_btn.setStyleSheet("""
            QPushButton { background-color: #00b7c3; color: white;
                          border: none; border-radius: 4px; padding: 8px; }
            QPushButton:hover { background-color: #009da8; }
        """)
        insert_btn.clicked.connect(self._insert_template)
        layout.addWidget(insert_btn)
        return widget


    def _create_help_tab(self):
        from style_manager import get_ai_tab_style
        s = get_ai_tab_style()

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)

        help_list = QListWidget()
        help_list.setFont(QFont("Segoe UI", 9))
        help_list.setStyleSheet(
            f"QListWidget {{ border: 1px solid {s['chat_border']}; border-radius: 4px;"
            f" background-color: {s['list_bg']}; color: {s['body_color']}; }}"
            f"QListWidget::item {{ padding: 6px; }}"
            f"QListWidget::item:hover {{ background-color: {s['list_hover']}; }}"
        )
        for topic in ["❓ How to insert images","❓ How to create tables",
                      "❓ How to write equations","❓ How to add citations"]:
            help_list.addItem(topic)
        help_list.itemDoubleClicked.connect(self._show_quick_help)
        layout.addWidget(help_list)
        return widget


    def _create_pdfs_tab(self):
        from style_manager import get_ai_tab_style
        s = get_ai_tab_style()

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setMaximumHeight(30)
        refresh_btn.setStyleSheet(
            f"QPushButton {{ background-color: {s['action_btn_bg']}; color: {s['body_color']};"
            f" border: 1px solid {s['action_btn_border']}; border-radius: 4px; }}"
            f"QPushButton:hover {{ background-color: {s['action_btn_hover']}; }}"
        )
        refresh_btn.clicked.connect(self._refresh_pdf_list)
        layout.addWidget(refresh_btn)

        self.pdf_list = QListWidget()
        self.pdf_list.setFont(QFont("Segoe UI", 9))
        self.pdf_list.setStyleSheet(
            f"QListWidget {{ border: 1px solid {s['chat_border']}; border-radius: 4px;"
            f" background-color: {s['list_bg']}; color: {s['body_color']}; }}"
            f"QListWidget::item {{ padding: 8px; border-bottom: 1px solid {s['chat_border']}; }}"
            f"QListWidget::item:hover {{ background-color: {s['list_hover']}; }}"
            f"QListWidget::item:selected {{ background-color: {s['list_selected']};"
            f" color: {s['list_selected_color']}; }}"
        )
        layout.addWidget(self.pdf_list, 1)

        analyze_btn = QPushButton("📄 Analyze Selected PDF")
        analyze_btn.setFont(QFont("Segoe UI", 9))
        analyze_btn.setCursor(Qt.PointingHandCursor)
        # Keep orange — intentional action color
        analyze_btn.setStyleSheet("""
            QPushButton { background-color: #ff9800; color: white;
                          border: none; border-radius: 4px; padding: 8px; }
            QPushButton:hover { background-color: #f57c00; }
        """)
        analyze_btn.clicked.connect(self._analyze_selected_pdf)
        layout.addWidget(analyze_btn)

        self._refresh_pdf_list()
        return widget
    def _refresh_pdf_list(self):
        self.pdf_list.clear()
        try:
            if not hasattr(self.main_window, 'pdf_manager'):
                self.pdf_list.addItem("No PDF manager available")
                return
            pdf_manager = self.main_window.pdf_manager
            if hasattr(pdf_manager, 'get_all_open_pdfs'):
                open_pdfs = pdf_manager.get_all_open_pdfs()
                if not open_pdfs:
                    self.pdf_list.addItem("No PDFs currently open")
                    return
                for pdf_info in open_pdfs:
                    pdf_path = pdf_info['path']
                    pdf_name = os.path.basename(pdf_path)
                    pdf_type = pdf_info.get('type', 'unknown')
                    exists = pdf_info.get('exists', False)
                    icon = "📄" if exists else "❌"
                    type_label = f"[{pdf_type}]" if pdf_type != 'unknown' else ""
                    item = QListWidgetItem(f"{icon} {pdf_name} {type_label}")
                    item.setData(Qt.UserRole, pdf_path)
                    item.setToolTip(pdf_path)
                    self.pdf_list.addItem(item)
            else:
                self.pdf_list.addItem("PDF manager not properly initialized")
        except Exception as e:
            self.pdf_list.addItem(f"Error loading PDFs: {str(e)}")

    # ═══════════════════════════════════════════════════════════
    # CONTEXT MENU AI ACTIONS - called from context_menu.py
    # ═══════════════════════════════════════════════════════════

    def handle_context_menu_action(self, action_name, selected_text, editor):
        """Handle an AI action triggered from the editor context menu."""
        if not selected_text or not selected_text.strip():
            QMessageBox.information(self, "No Selection", "Please select text first.")
            return

        if not self.online_mode or not self.online_ai or not self.online_ai.is_configured():
            self._toggle_mode()
            return

        # Prevent multiple rapid context menu actions
        if hasattr(self, 'ai_thread') and self.ai_thread is not None and self.ai_thread.isRunning():
            QMessageBox.information(self, "Please Wait", "Another AI operation is in progress. Please wait for it to complete.")
            return

        # Special handling for translation
        if action_name == "Translate Arabic/English":
            has_arabic = bool(re.search(r'[\u0600-\u06FF]', selected_text))
            if has_arabic:
                source_lang, target_lang = "Arabic", "English"
            else:
                source_lang, target_lang = "English", "Arabic"

            prompt = (
                f"Translate the following text from {source_lang} to {target_lang}. "
                f"Return ONLY the translation without any explanations or additional text.\n\n"
                f"Text to translate:\n{selected_text}"
            )
            self._add_user_message(f"Translate ({source_lang} → {target_lang}):\n{selected_text[:200]}...")

            # Store for auto-apply
            cursor = editor.textCursor()
            self._pending_translation = {
                'editor': editor,
                'position': cursor.selectionEnd(),
                'original': selected_text
            }
            self._send_online_query(prompt, action_type='translate')
            return

        # Find the prompt template for this action
        prompt = None
        for name, template in self.AI_CONTEXT_ACTIONS:
            if name == action_name and template is not None:
                prompt = template.format(text=selected_text)
                break

        if prompt is None:
            self._add_system_message(f"Unknown action: {action_name}")
            return

        self._add_user_message(f"{action_name}:\n{selected_text[:200]}...")

        # For actions that replace text, store replacement info
        replace_actions = ["Rewrite for clarity", "Simplify the language",
                           "Expand", "Shorten"]
        if action_name in replace_actions:
            cursor = editor.textCursor()
            self._pending_replacement = {
                'editor': editor,
                'start': cursor.selectionStart(),
                'end': cursor.selectionEnd(),
                'original': selected_text
            }
            self._send_online_query(prompt, action_type='improve')
        else:
            self._send_online_query(prompt, action_type='chat')

    def _is_thread_busy(self):
        """Check if an AI thread is currently running."""
        return (hasattr(self, 'ai_thread') and 
                self.ai_thread is not None and 
                self.ai_thread.isRunning())
    # ═══════════════════════════════════════════════════════════
    # QUICK ACTIONS
    # ═══════════════════════════════════════════════════════════

    def _translate_selection(self):
        try:
            # Check if thread is busy
            if self._is_thread_busy():
                QMessageBox.information(self, "Please Wait", "Another AI operation is in progress. Please wait for it to complete.")
                return
                
            editor = self.main_window.editor_manager.get_current_editor()
            if not editor:
                QMessageBox.information(self, "No Editor", "No editor is active")
                return
            cursor = editor.textCursor()
            if not cursor.hasSelection():
                QMessageBox.information(self, "No Selection", "Please select text to translate")
                return
            selected_text = cursor.selectedText()
            if not self.online_mode or not self.online_ai or not self.online_ai.is_configured():
                self._toggle_mode()
                return
            has_arabic = bool(re.search(r'[\u0600-\u06FF]', selected_text))
            source_lang = "Arabic" if has_arabic else "English"
            target_lang = "English" if has_arabic else "Arabic"
            self._add_user_message(f"Translate ({source_lang} → {target_lang}):\n{selected_text[:200]}...")
            self._pending_translation = {
                'editor': editor,
                'position': cursor.selectionEnd(),
                'original': selected_text
            }
            prompt = f"""Translate the following text from {source_lang} to {target_lang}.
    Return ONLY the translation without any explanations or additional text.
    Text to translate:
    {selected_text}"""
            self._send_online_query(prompt, action_type='translate')
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def _analyze_selected_pdf(self):
        current_item = self.pdf_list.currentItem()
        if not current_item:
            QMessageBox.information(self, "No Selection", "Please select a PDF from the list")
            return
        pdf_path = current_item.data(Qt.UserRole)
        if not pdf_path or not os.path.exists(pdf_path):
            QMessageBox.warning(self, "Error", "Selected PDF file not found")
            return
        try:
            pdf_text = self._extract_pdf_from_path(pdf_path)
            if not pdf_text:
                QMessageBox.warning(self, "Error", "Could not extract text from PDF")
                return
            max_chars = 4000
            if len(pdf_text) > max_chars:
                pdf_text = pdf_text[:max_chars] + "\n... (truncated)"
            pdf_name = os.path.basename(pdf_path)
            self._add_user_message(f"Analyze PDF: {pdf_name}")
            if self.online_mode and self.online_ai and self.online_ai.is_configured():
                prompt = f"""Analyze this PDF document and provide:
    1. Brief summary
    2. Main topics covered
    3. Document structure
    4. Key findings or arguments
    Document: {pdf_name}
    Text:
    {pdf_text}"""
                self._send_online_query(prompt)
            else:
                self._add_system_message("PDF analysis requires online AI mode.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to analyze PDF:\n{str(e)}")

    def _extract_pdf_from_path(self, pdf_path):
        try:
            import fitz
            doc = fitz.open(pdf_path)
            text = ""
            for page_num in range(min(10, doc.page_count)):
                page = doc[page_num]
                text += page.get_text()
            doc.close()
            return text
        except ImportError:
            self._add_system_message("⚠ Install PyMuPDF for PDF analysis: pip install PyMuPDF")
            return None
        except Exception as e:
            print(f"Error extracting PDF text: {e}")
            return None

    def _insert_to_editor(self, text):
        try:
            editor = self.main_window.editor_manager.get_current_editor()
            if editor:
                cursor = editor.textCursor()
                if hasattr(self, '_pending_insert_position') and self._pending_insert_position is not None:
                    cursor.setPosition(self._pending_insert_position)
                cursor.insertText(f"\n{text}\n")
                editor.setTextCursor(cursor)
                self.main_window.editor_manager.mark_current_file_modified()
                js_code = 'addMessage("system", "✓ Inserted to Editor", "Response inserted at cursor position");'
                #self.chat_display.page().runJavaScript(js_code)
                self._run_js_safe('addMessage("system", "✓ Inserted to Editor", "Response inserted at cursor position");')
            else:
                escaped_text = self._fix_latex_formatting(text)
                js_code = f'addMessage("assistant", "🤖 Assistant", "{escaped_text}");'
                #self.chat_display.page().runJavaScript(js_code)
                self._run_js_safe(f'addMessage("assistant", "🤖 Assistant", "{escaped_text}");')
        except Exception as e:
            print(f"Error inserting to editor: {e}")


    def _send_message(self):
        user_input = self.input_text.toPlainText().strip()
        if not user_input:
            return
        self._add_user_message(user_input)
        self.input_text.clear()
        if hasattr(self, 'output_to_editor_btn') and self.output_to_editor_btn.isChecked():
            try:
                editor = self.main_window.editor_manager.get_current_editor()
                if editor:
                    self._pending_insert_position = editor.textCursor().position()
            except Exception:
                pass
        if self.online_mode and self.online_ai and self.online_ai.is_configured():
            self._send_online_query(user_input)
        else:
            response = self.assistant.answer_question(user_input)
            self._add_assistant_message(response)

    def _send_online_query(self, user_input, action_type='chat'):
        if not self.online_ai or not self.online_ai.is_configured():
            self._add_system_message(
                "❌ API key not configured. Go to Settings → AI Assistant")
            if hasattr(self, 'send_btn'):
                self.send_btn.setEnabled(True)
            return

        # Disable send button to prevent multiple rapid clicks
        if hasattr(self, 'send_btn'):
            self.send_btn.setEnabled(False)

        # ── CRITICAL: Stop any previous thread BEFORE starting a new one ──
        self._stop_ai_thread()
        
        # Small delay to ensure thread cleanup is complete
        QApplication.processEvents()

        self._current_action = action_type

        conversation_context = ""
        if self.conversation_history:
            for msg in self.conversation_history:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                if role == 'user':
                    conversation_context += f"User: {content}\n"
                elif role == 'assistant':
                    conversation_context += f"Assistant: {content}\n"

        if conversation_context:
            enhanced_prompt = (
                f"Previous conversation:\n{conversation_context}\n"
                f"Current question:\n{user_input}\n\n"
                "IMPORTANT: When writing mathematical expressions:\n"
                "- Use proper LaTeX syntax with all parentheses\n"
                "- For display equations, use \\[ \\] on separate lines\n"
                "- Keep regular text separate from math expressions"
            )
        else:
            enhanced_prompt = (
                f"{user_input}\n\n"
                "IMPORTANT: When writing mathematical expressions:\n"
                "- Use proper LaTeX syntax with all parentheses\n"
                "- For display equations, use \\[ \\] on separate lines"
            )

        self._last_prompt = enhanced_prompt
        self.conversation_history.append({'role': 'user', 'content': user_input})

        try:
            from online_ai_provider import OnlineAIThread
            self.ai_thread = OnlineAIThread(
                self.online_ai, enhanced_prompt,
                max_tokens=2048, temperature=0.7
            )
            
            # Connect signals BEFORE starting the thread
            self.ai_thread.response_ready.connect(self._on_online_response)
            self.ai_thread.error_occurred.connect(self._on_online_error)
            self.ai_thread.finished.connect(self._on_thread_finished)
            
            # Start the thread
            self.ai_thread.start()
            
        except Exception as e:
            self._add_system_message(f"❌ Error: {str(e)}")
            if hasattr(self, 'send_btn'):
                self.send_btn.setEnabled(True)

    def _on_thread_finished(self):
        """Called when the thread's run() returns — safe to clean up."""
        if self.ai_thread is not None:
            try:
                self.ai_thread.deleteLater()
            except Exception:
                pass
            self.ai_thread = None

    def _on_online_response(self, response):
        """Handle online AI response"""
        self.conversation_history.append({'role': 'assistant', 'content': response})
        self._add_assistant_message(response)

        if hasattr(self, 'send_btn'):
            self.send_btn.setEnabled(True)

        # Show continue button only if response seems truncated
        response_stripped = response.strip() if response else ""
        if response_stripped:
            ends_ok = any(response_stripped.endswith(e) for e in ['.', '!', '?', '\\]', '$$', '```'])
            if len(response) > 1500 or not ends_ok:
                if hasattr(self, 'continue_btn'):
                    self.continue_btn.setVisible(True)
            else:
                if hasattr(self, 'continue_btn'):
                    self.continue_btn.setVisible(False)
        else:
            if hasattr(self, 'continue_btn'):
                self.continue_btn.setVisible(False)

        # Auto-apply for improve action
        if getattr(self, '_current_action', None) == 'improve':
            if self._pending_replacement and self.auto_apply_check.isChecked():
                try:
                    replacement = self._pending_replacement
                    editor = replacement['editor']
                    cursor = editor.textCursor()
                    cursor.setPosition(replacement['start'])
                    cursor.setPosition(replacement['end'], QTextCursor.KeepAnchor)
                    cursor.insertText(response.strip())
                    self.main_window.editor_manager.mark_current_file_modified()
                    self._add_system_message("✓ Text replaced in editor")
                except Exception as e:
                    self._add_system_message(f"❌ Failed to apply changes: {str(e)}")
                finally:
                    self._pending_replacement = None

        elif getattr(self, '_current_action', None) == 'translate':
            if self._pending_translation and self.auto_apply_check.isChecked():
                try:
                    translation = self._pending_translation
                    editor = translation['editor']
                    cursor = editor.textCursor()
                    cursor.setPosition(translation['position'])
                    cursor.insertText(f"\n{response.strip()}\n")
                    self.main_window.editor_manager.mark_current_file_modified()
                    self._add_system_message("✓ Translation inserted after selected text")
                except Exception as e:
                    self._add_system_message(f"❌ Failed to insert translation: {str(e)}")
                finally:
                    self._pending_translation = None

        self._current_action = None
    

    def _continue_response(self):
        """Continue the previous response with conversation history."""
        if hasattr(self, 'continue_btn'):
            self.continue_btn.setVisible(False)

        if not self.conversation_history:
            self._add_system_message("No conversation history to continue")
            return

        if not self.online_mode or not self.online_ai or not self.online_ai.is_configured():
            self._add_system_message("Continue requires online AI mode.")
            return

        # Disable send button to prevent multiple clicks
        if hasattr(self, 'send_btn'):
            self.send_btn.setEnabled(False)

        # ── CRITICAL: Stop any previous thread BEFORE starting a new one ──
        self._stop_ai_thread()
        
        # Small delay to ensure cleanup is complete
        QApplication.processEvents()

        recent_messages = self.conversation_history[-4:]
        context = ""
        for msg in recent_messages:
            role = msg['role']
            content = msg['content']
            if role == 'user':
                context += f"User: {content}\n"
            else:
                context += f"Assistant: {content}\n"

        continue_prompt = (
            f"{context}\n"
            "Please continue your previous response. Pick up exactly where you left off."
        )

        try:
            from online_ai_provider import OnlineAIThread
            self.ai_thread = OnlineAIThread(
                self.online_ai, continue_prompt,
                max_tokens=2048, temperature=0.7
            )
            
            # Connect signals BEFORE starting
            self.ai_thread.response_ready.connect(self._on_continue_response)
            self.ai_thread.error_occurred.connect(self._on_continue_error)
            self.ai_thread.finished.connect(self._on_thread_finished)
            
            # Start the thread
            self.ai_thread.start()
            
        except Exception as e:
            self._add_system_message(f"❌ Error: {str(e)}")
            if hasattr(self, 'send_btn'):
                self.send_btn.setEnabled(True)

    def _on_continue_response(self, response):
        """Handle continue response - hide button if response is empty or same"""
        if hasattr(self, 'send_btn'):
            self.send_btn.setEnabled(True)

        # Check if we actually got new content
        response_stripped = response.strip() if response else ""

        if not response_stripped:
            # No new content - keep button hidden
            self._add_system_message("Response complete — nothing more to add.")
            return

        # Check if response is just a repetition of the last assistant message
        last_assistant_msg = ""
        for msg in reversed(self.conversation_history):
            if msg.get('role') == 'assistant':
                last_assistant_msg = msg.get('content', '').strip()
                break

        if response_stripped == last_assistant_msg:
            # Same content repeated - keep button hidden
            self._add_system_message("Response complete — no additional content.")
            return

        # We have genuine new content - add it
        self.conversation_history.append({'role': 'assistant', 'content': response})
        self._add_assistant_message(response)

        # Decide whether to show continue button again
        ends_ok = any(response.rstrip().endswith(e) for e in ['.', '!', '?', '\\]', '$$', '```'])
        if len(response) > 1500 or not ends_ok:
            if hasattr(self, 'continue_btn'):
                self.continue_btn.setVisible(True)
        # Otherwise button stays hidden

    def _on_continue_error(self, error):
        """Handle continue error - keep button hidden"""
        if hasattr(self, 'send_btn'):
            self.send_btn.setEnabled(True)

        error_lower = error.lower()
        if '401' in error or 'unauthorized' in error_lower:
            self._add_system_message("❌ Authentication Error — check your API key.")
        elif '429' in error or 'rate limit' in error_lower:
            self._add_system_message("❌ Rate limit reached — wait and try again.")
        else:
            self._add_system_message(f"❌ Error: {error}")
        

    # def _get_provider_dashboard_url(self):
        # if not self.online_ai:
            # return None
        # urls = {
            # 'groq': 'https://console.groq.com/settings/billing',
            # 'openai': 'https://platform.openai.com/account/billing',
            # 'anthropic': 'https://console.anthropic.com/settings/billing',
            # 'deepseek': 'https://platform.deepseek.com/usage',
            # 'qwen': 'https://dashscope.console.aliyun.com'
        # }
        # return urls.get(self.online_ai.provider)

    def _on_online_error(self, error):
        error_lower = error.lower()
        if '401' in error or 'unauthorized' in error_lower:
            self._add_system_message(
                "❌ Authentication Error (401)\nYour API key is invalid or expired.\n"
                "Go to Settings → AI Assistant to verify your API key.")
        elif '429' in error or 'rate limit' in error_lower:
            self._add_system_message(
                "❌ Rate Limit Error (429)\nYou've exceeded the API rate limit.\n"
                "Wait a few minutes and try again.")
        elif 'timeout' in error_lower or 'timed out' in error_lower:
            self._add_system_message("❌ Request Timeout\nTry again with a shorter prompt.")
        elif 'network' in error_lower or 'connection' in error_lower:
            self._add_system_message("❌ Network Error\nCheck your internet connection.")
        else:
            self._add_system_message(f"❌ Error: {error}")
        self._add_system_message("💡 Tip: Switch to Offline Mode for basic LaTeX help without API.")
        if hasattr(self, 'send_btn'):
            self.send_btn.setEnabled(True)

    def _explain_selection(self):
        try:
            editor = self.main_window.editor_manager.get_current_editor()
            if not editor:
                QMessageBox.information(self, "No Editor", "No editor is active")
                return
            cursor = editor.textCursor()
            if not cursor.hasSelection():
                QMessageBox.information(self, "No Selection", "Please select text first")
                return
            selected_text = cursor.selectedText()
            self._add_user_message(f"Explain the content:\n{selected_text[:200]}...")
            if hasattr(self, 'output_to_editor_btn') and self.output_to_editor_btn.isChecked():
                self._pending_insert_position = cursor.selectionEnd()
            if self.online_mode and self.online_ai and self.online_ai.is_configured():
                prompt = f"""Explain the meaning and content of this text in simple terms.
    Focus on what the text is saying, not on the LaTeX formatting or commands.
    If it contains mathematical formulas, explain what they mean mathematically.
    If it's regular text, summarize and explain the key points.
    Always use the same language as the text.
    Text to explain:
    {selected_text}"""
                self._send_online_query(prompt)
            else:
                self._add_assistant_message(
                    f"Selected text preview:\n{selected_text}\n\n"
                    "Online AI required for detailed content explanation.")
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def _improve_selection(self):
        try:
            # Check if thread is busy
            if self._is_thread_busy():
                QMessageBox.information(self, "Please Wait", "Another AI operation is in progress. Please wait for it to complete.")
                return
                
            editor = self.main_window.editor_manager.get_current_editor()
            if not editor:
                QMessageBox.information(self, "No Editor", "No editor is active")
                return
            cursor = editor.textCursor()
            if not cursor.hasSelection():
                QMessageBox.information(self, "No Selection", "Please select text first")
                return
            selected_text = cursor.selectedText()
            self._add_user_message(f"Improve this text:\n{selected_text[:200]}...")
            self._pending_replacement = {
                'editor': editor,
                'start': cursor.selectionStart(),
                'end': cursor.selectionEnd(),
                'original': selected_text
            }
            if self.online_mode and self.online_ai and self.online_ai.is_configured():
                prompt = f"""Improve this text for clarity, grammar, and academic style.
    Return ONLY the improved text without explanations:
    {selected_text}"""
                self._send_online_query(prompt, action_type='improve')
            else:
                response = self.assistant.improve_text(selected_text)
                self._add_assistant_message(response)
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def _fix_latex_errors(self):
        try:
            error_text = self._get_latex_errors()
            if not error_text:
                self._add_system_message("No errors detected in Output tab")
                return
            self._add_user_message("Fix these LaTeX compilation errors")
            if self.online_mode and self.online_ai and self.online_ai.is_configured():
                prompt = f"""Analyze these LaTeX compilation errors and provide solutions:
    {error_text}
    For each error:
    1. Identify the problem
    2. Explain the cause
    3. Provide exact fix"""
                self._send_online_query(prompt)
            else:
                response = self.assistant.fix_errors(error_text)
                self._add_assistant_message(response)
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def _analyze_pdf(self):
        try:
            self._refresh_pdf_list()
            self._add_system_message("📑 Select a PDF from the 'PDFs' tab, then click 'Analyze Selected PDF'")
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def _get_latex_errors(self):
        error_lines = []
        try:
            if hasattr(self.main_window, 'output_text'):
                output_text = self.main_window.output_text.toPlainText()
                lines = output_text.split('\n')
                for i, line in enumerate(lines):
                    if any(keyword in line.lower() for keyword in ['error', '!', 'warning', 'undefined']):
                        context_start = max(0, i - 1)
                        context_end = min(len(lines), i + 2)
                        error_lines.extend(lines[context_start:context_end])
                        error_lines.append("---")
            if hasattr(self.main_window, 'terminal_widget'):
                terminal_text = self.main_window.terminal_widget.output_display.toPlainText()
                lines = terminal_text.split('\n')
                for line in lines:
                    if any(keyword in line.lower() for keyword in ['error', '!']):
                        error_lines.append(line)
            return '\n'.join(error_lines[-50:]) if error_lines else None
        except Exception:
            return None

    def _insert_template(self, item=None):
        if not item:
            item = self.template_list.currentItem()
        if not item:
            return
        template_map = {
            '📄 Figure with Image': 'figure',
            '📊 Basic Table': 'table',
            '🔢 Numbered Equation': 'equation',
            '• Bullet List': 'itemize'
        }
        template_key = template_map.get(item.text())
        if template_key:
            code = self.assistant.get_template(template_key)
            if code:
                self._add_system_message(f"Template: {item.text()}")
                self._add_assistant_message(code)
                try:
                    editor = self.main_window.editor_manager.get_current_editor()
                    if editor:
                        cursor = editor.textCursor()
                        cursor.insertText(code)
                        self._add_system_message("✓ Template inserted!")
                        self.main_window.editor_manager.mark_current_file_modified()
                except Exception:
                    self._add_system_message("💡 Copy and paste into your document")

    def _show_quick_help(self, item):
        topic = item.text().replace("❓ ", "")
        self._add_user_message(topic)
        response = self.assistant.answer_question(topic)
        self._add_assistant_message(response)

    def eventFilter(self, obj, event):
        if obj == self.input_text and event.type() == event.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if event.modifiers() == Qt.ControlModifier:
                    self._send_message()
                    return True
        return super().eventFilter(obj, event)


def add_ai_tab_to_pdf_viewer(main_window):
    """Add AI Assistant tab to PDF viewer"""
    lang = main_window.menu_language
    translations = main_window.translations
    tr = translations[lang]        
    try:
        if not hasattr(main_window, 'pdf_manager'):
            QMessageBox.warning(main_window, "Warning", "PDF manager not available!")
            return
        if not hasattr(main_window, 'layout_manager'):
            QMessageBox.warning(main_window, "Warning", "Layout manager not available!")
            return

        layout_manager = main_window.layout_manager
        pdf_manager = main_window.pdf_manager

        if not hasattr(layout_manager, 'pdf_container') or layout_manager.pdf_container is None:
            layout_manager._recreate_pdf_container()

        if pdf_manager.pdf_layout_mode != "tabbed":
            QMessageBox.information(main_window, "Info",
                "AI Assistant is only available in tabbed mode.")
            return

        # ✅ Initialize pdf_tabs if needed WITHOUT recreating container
        if not hasattr(pdf_manager, 'pdf_tabs') or pdf_manager.pdf_tabs is None:
            from PyQt5.QtWidgets import QTabWidget
            pdf_manager.pdf_tabs = QTabWidget()
            pdf_manager.pdf_tabs.setTabsClosable(True)            
            if hasattr(pdf_manager, 'close_pdf_tab'):
                pdf_manager.pdf_tabs.tabCloseRequested.connect(pdf_manager.close_pdf_tab)
            
            # Add to PDF container layout
            pdf_layout = layout_manager.pdf_container.layout()
            if pdf_layout:
                # Clear existing widgets (welcome tab)
                while pdf_layout.count():
                    item = pdf_layout.takeAt(0)
                    if item.widget():
                        widget = item.widget()
                        widget.setParent(None)
                        widget.deleteLater()
                # Add the new tab widget
                pdf_layout.addWidget(pdf_manager.pdf_tabs)


        tab_widget = pdf_manager.pdf_tabs

        if tab_widget is None:
            QMessageBox.critical(main_window, "Error", "Could not initialize PDF tabs")
            return
        
        # ✅ Remove unwanted tabs (Welcome, No Pdfs, etc.)
        tabs_to_remove = ["Welcome", "No Pdfs", "No PDFs"]
        for i in reversed(range(tab_widget.count())):
            tab_text = tab_widget.tabText(i)
            if tab_text in tabs_to_remove:
                tab_widget.removeTab(i)
                #print(f"DEBUG: Removed '{tab_text}' tab")
        
        # ✅ Check if Tools tab already exists and is valid
        possible_labels = {
            tr["ai_assistant"] for tr in translations.values()
        }                        
        
        existing_tools_index = -1
        for i in range(tab_widget.count()):
            if tab_widget.tabText(i) in possible_labels:
                existing_tools_index = i
                break
        
        if existing_tools_index >= 0:
            # Tools tab exists, just switch to it
            tab_widget.setCurrentIndex(existing_tools_index)
            #print(f"✅ Switched to existing AI Assistant tab at index {existing_tools_index}")
            return


        from ai_tab import AIAssistantWidget
        ai_widget = AIAssistantWidget(main_window)
        
        
        if not hasattr(main_window, '_ai_tabs'):
            main_window._ai_tabs = []
        main_window._ai_tabs.append(ai_widget)

        tab_name = tr.get("ai_assistant", "AI Assistant")
        tab_index = tab_widget.addTab(ai_widget, tab_name)
        tab_widget.tabBar().setTabData(tab_index, "ai_assistant")    
        
        # ✅ Set SVG icon properly
        icon = QIcon("icons/ai.svg")
        tab_widget.setTabIcon(tab_index, icon)                
        
        tab_widget.setCurrentIndex(tab_index)
        tab_widget.setTabsClosable(True)

        pdf_layout = layout_manager.pdf_container.layout()
        if pdf_layout and pdf_layout.indexOf(tab_widget) == -1:
            while pdf_layout.count():
                item = pdf_layout.takeAt(0)
                if item.widget() and item.widget() != tab_widget:
                    item.widget().setParent(None)
            pdf_layout.addWidget(tab_widget)

        tab_widget.show()
        tab_widget.setVisible(True)
        ai_widget.show()
        layout_manager.pdf_container.update()
        layout_manager.pdf_container.repaint()

    except Exception as e:
        QMessageBox.critical(main_window, "Error", f"Failed to add AI Assistant:\n{str(e)}")
        import traceback
        traceback.print_exc()