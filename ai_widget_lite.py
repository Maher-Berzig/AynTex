# ai_widget_lite.py
"""
AI Assistant Widget (Lite Version) - No External Dependencies
Fallback version with rule-based LaTeX assistance
Save this as: ai_widget_lite.py

Use this if llama-cpp-python doesn't work on your system.
Provides basic LaTeX help through pattern matching and templates.
"""
import os
import re
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                             QPushButton, QLabel, QGroupBox, QMessageBox,
                             QSplitter, QListWidget)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QTextCursor, QFont, QColor, QTextCharFormat
from online_ai_provider import OnlineAIProvider, OnlineAIThread

class LaTeXAssistantLite:
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
            r'\\label': {
                'name': 'Label',
                'description': 'Creates a label for cross-referencing',
                'example': r'\label{sec:intro}',
                'tips': 'Convention: sec: for sections, fig: for figures, tab: for tables'
            },
        }
    
    def _load_common_errors(self):
        """Common LaTeX errors and solutions"""
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
            {
                'pattern': r'file .* not found',
                'cause': 'Missing file (image, bibliography, etc.)',
                'solution': 'Check file path and ensure file exists',
                'example': r'Use relative paths: \includegraphics{images/photo.jpg}'
            },
            {
                'pattern': r'runaway argument',
                'cause': 'Missing closing brace }',
                'solution': 'Check all { have matching }',
                'example': r'Correct: \textbf{text} Not: \textbf{text'
            },
        ]
    
    def _load_templates(self):
        """LaTeX code templates"""
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
        Row 1 Col 1 & Row 1 Col 2 & Row 1 Col 3 \\
        Row 2 Col 1 & Row 2 Col 2 & Row 2 Col 3 \\
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
    \item Third item
\end{itemize}'''
            },
            'enumerate': {
                'name': 'Numbered List',
                'code': r'''\begin{enumerate}
    \item First item
    \item Second item
    \item Third item
\end{enumerate}'''
            },
        }
    
    def explain_code(self, code):
        """Explain LaTeX code"""
        explanations = []
        
        # Find matching commands
        for pattern, info in self.latex_help.items():
            if re.search(pattern, code, re.IGNORECASE):
                explanations.append(f"**{info['name']}**: {info['description']}")
                explanations.append(f"Example: `{info['example']}`")
                explanations.append(f"💡 Tip: {info['tips']}\n")
        
        if not explanations:
            return "I can help explain common LaTeX commands. Try selecting code with \\section, \\textbf, \\cite, etc."
        
        return "\n".join(explanations)
    
    def improve_text(self, text):
        """Suggest text improvements"""
        suggestions = []
        
        # Check for common issues
        if text.isupper():
            suggestions.append("📝 Consider using sentence case instead of all caps")
        
        if len(text) > 200 and '.' not in text:
            suggestions.append("📝 Long paragraph - consider breaking into shorter sentences")
        
        if text.count('very') > 2:
            suggestions.append("📝 Try replacing 'very' with stronger adjectives")
        
        # Check for LaTeX formatting opportunities
        if re.search(r'\b(important|key|crucial|critical)\b', text, re.IGNORECASE):
            suggestions.append(r"💡 Consider emphasizing key terms with \textbf{} or \emph{}")
        
        if re.search(r'\d+', text):
            suggestions.append(r"💡 For large numbers, consider using siunitx package: \num{1000000}")
        
        if not suggestions:
            suggestions.append("✓ Text looks good! No major issues detected.")
        
        return "\n".join(suggestions)
    
    def fix_errors(self, error_text):
        """Suggest fixes for errors"""
        suggestions = []
        
        for error in self.common_errors:
            if re.search(error['pattern'], error_text, re.IGNORECASE):
                suggestions.append(f"**{error['pattern']}**")
                suggestions.append(f"Cause: {error['cause']}")
                suggestions.append(f"Solution: {error['solution']}")
                suggestions.append(f"Example: `{error['example']}`\n")
        
        if not suggestions:
            suggestions.append("💡 General troubleshooting:")
            suggestions.append("1. Check for missing packages in preamble")
            suggestions.append("2. Ensure all { } are balanced")
            suggestions.append("3. Verify file paths for images/references")
            suggestions.append("4. Look for special characters that need escaping: & % $ # _ { } ~ ^")
        
        return "\n".join(suggestions)
    
    def get_template(self, template_name):
        """Get a code template"""
        if template_name in self.templates:
            template = self.templates[template_name]
            return f"**{template['name']}**\n\n{template['code']}"
        return None
    
    def answer_question(self, question):
        """Answer common LaTeX questions"""
        question_lower = question.lower()
        
        # Question patterns
        if 'how' in question_lower and 'image' in question_lower:
            return """**How to insert an image:**

1. Add package in preamble:
   `\\usepackage{graphicx}`

2. Insert image:
   ```latex
   \\begin{figure}[h]
       \\centering
       \\includegraphics[width=0.8\\textwidth]{image.png}
       \\caption{My image}
       \\label{fig:myimage}
   \\end{figure}
   ```

3. Reference it: `See Figure \\ref{fig:myimage}`"""
        
        elif 'how' in question_lower and 'table' in question_lower:
            return self.get_template('table')
        
        elif 'how' in question_lower and ('equation' in question_lower or 'math' in question_lower):
            return """**How to write equations:**

Inline math: `$x^2 + y^2 = z^2$`

Display math:
```latex
\\[
    E = mc^2
\\]
```

Numbered equation:
```latex
\\begin{equation}
    F = ma
    \\label{eq:newton}
\\end{equation}
```

Multiple aligned equations:
```latex
\\begin{align}
    x &= 1 \\\\
    y &= 2
\\end{align}
```"""
        
        elif 'bibliography' in question_lower or 'citation' in question_lower:
            return """**How to add citations:**

1. Create .bib file (references.bib):
   ```bibtex
   @article{author2023,
       author = {John Doe},
       title = {Amazing Research},
       journal = {Journal Name},
       year = {2023}
   }
   ```

2. In your .tex file:
   ```latex
   \\cite{author2023}
   
   \\bibliographystyle{plain}
   \\bibliography{references}
   ```

3. Compile: pdflatex → bibtex → pdflatex → pdflatex"""
        
        elif 'package' in question_lower:
            return """**Essential LaTeX packages:**

```latex
% Graphics and colors
\\usepackage{graphicx}
\\usepackage{xcolor}

% Math
\\usepackage{amsmath, amssymb, amsthm}

% Better tables
\\usepackage{booktabs}

% Hyperlinks
\\usepackage{hyperref}

% Better fonts
\\usepackage{lmodern}

% Code listings
\\usepackage{listings}
```"""
        
        return "I can help with:\n• Explaining LaTeX commands\n• Inserting images, tables, equations\n• Citations and bibliography\n• Common packages\n• Fixing errors"


class AIWidgetLite(QWidget):
    """Lightweight AI assistant without external dependencies"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.assistant = LaTeXAssistantLite()
        self.conversation_history = []
        
        self._setup_ui()
        self._add_welcome_message()
        self.online_ai = OnlineAIProvider()
        self.online_mode = False
        self.ai_thread = None

    
    def _setup_ui(self):
        """Setup the UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Info banner
        info_label = QLabel("💡 Lite Mode - Rule-based LaTeX Assistant (No AI model required)")
        info_label.setStyleSheet("""
            background-color: #264f78;
            color: white;
            padding: 8px;
            border-radius: 4px;
        """)
        layout.addWidget(info_label)
        
        # Main content splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Left: Chat
        chat_widget = QWidget()
        chat_layout = QVBoxLayout(chat_widget)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        
        # Chat display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        font = QFont("Segoe UI", 10)
        self.chat_display.setFont(font)
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3e3e3e;
                padding: 8px;
            }
        """)
        chat_layout.addWidget(self.chat_display)
        
        # Input area
        self.input_text = QTextEdit()
        self.input_text.setMaximumHeight(80)
        self.input_text.setPlaceholderText("Ask about LaTeX... (Enter to send)")
        self.input_text.setFont(font)
        self.input_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3e3e3e;
                padding: 5px;
            }
        """)
        self.input_text.installEventFilter(self)
        chat_layout.addWidget(self.input_text)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self._send_message)
        btn_layout.addWidget(self.send_btn)
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self._clear_chat)
        btn_layout.addWidget(self.clear_btn)
        
        self.copy_btn = QPushButton("Copy Response")
        self.copy_btn.clicked.connect(self._copy_last_response)
        btn_layout.addWidget(self.copy_btn)
        
        btn_layout.addStretch()
        chat_layout.addLayout(btn_layout)
        
        splitter.addWidget(chat_widget)
        
        # Right: Quick Actions & Templates
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Quick Actions
        actions_group = QGroupBox("Quick Actions")
        actions_layout = QVBoxLayout()
        
        self.explain_btn = QPushButton("📖 Explain Selection")
        self.explain_btn.clicked.connect(self._explain_selection)
        actions_layout.addWidget(self.explain_btn)
        
        self.improve_btn = QPushButton("✨ Improve Text")
        self.improve_btn.clicked.connect(self._improve_selection)
        actions_layout.addWidget(self.improve_btn)
        
        self.fix_errors_btn = QPushButton("🔧 Fix LaTeX Errors")
        self.fix_errors_btn.clicked.connect(self._fix_latex_errors)
        actions_layout.addWidget(self.fix_errors_btn)
        
        actions_group.setLayout(actions_layout)
        right_layout.addWidget(actions_group)
        
        # Templates
        templates_group = QGroupBox("LaTeX Templates")
        templates_layout = QVBoxLayout()
        
        self.template_list = QListWidget()
        self.template_list.addItems([
            "Figure with Image",
            "Basic Table",
            "Numbered Equation",
            "Bullet List",
            "Numbered List"
        ])
        self.template_list.itemDoubleClicked.connect(self._insert_template)
        templates_layout.addWidget(self.template_list)
        
        insert_template_btn = QPushButton("Insert Template")
        insert_template_btn.clicked.connect(self._insert_template)
        templates_layout.addWidget(insert_template_btn)
        
        templates_group.setLayout(templates_layout)
        right_layout.addWidget(templates_group)
        
        # Quick Help
        help_group = QGroupBox("Quick Help")
        help_layout = QVBoxLayout()
        
        help_topics = QListWidget()
        help_topics.addItems([
            "How to insert images",
            "How to create tables",
            "How to write equations",
            "How to add citations",
            "Essential packages"
        ])
        help_topics.itemDoubleClicked.connect(self._show_quick_help)
        help_layout.addWidget(help_topics)
        
        help_group.setLayout(help_layout)
        right_layout.addWidget(help_group)
        
        splitter.addWidget(right_widget)
        
        # Set splitter sizes (70% chat, 30% sidebar)
        splitter.setSizes([700, 300])
        
        layout.addWidget(splitter)
    
    def _add_welcome_message(self):
        """Add welcome message"""
        self._add_system_message(
            "Welcome to LaTeX Assistant (Lite Mode)! 🚀\n\n"
            "I'm a rule-based assistant that can help with:\n"
            "• Explaining LaTeX commands and syntax\n"
            "• Providing code templates\n"
            "• Fixing common compilation errors\n"
            "• Suggesting text improvements\n\n"
            "Try the quick actions on selected text, or ask me questions!"
        )
    
    def _add_system_message(self, text):
        """Add system message to chat"""
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        format = QTextCharFormat()
        format.setForeground(QColor("#4ec9b0"))
        cursor.setCharFormat(format)
        cursor.insertText(f"💡 {text}\n\n")
        
        self.chat_display.setTextCursor(cursor)
        self.chat_display.ensureCursorVisible()
    
    def _add_user_message(self, text):
        """Add user message to chat"""
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        format = QTextCharFormat()
        format.setForeground(QColor("#569cd6"))
        cursor.setCharFormat(format)
        cursor.insertText("You: ")
        
        format.setForeground(QColor("#d4d4d4"))
        cursor.setCharFormat(format)
        cursor.insertText(f"{text}\n\n")
        
        self.chat_display.setTextCursor(cursor)
        self.chat_display.ensureCursorVisible()
    
    def _add_assistant_message(self, text):
        """Add assistant message to chat"""
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        format = QTextCharFormat()
        format.setForeground(QColor("#ce9178"))
        cursor.setCharFormat(format)
        cursor.insertText("Assistant: ")
        
        format.setForeground(QColor("#d4d4d4"))
        cursor.setCharFormat(format)
        cursor.insertText(f"{text}\n\n")
        
        self.chat_display.setTextCursor(cursor)
        self.chat_display.ensureCursorVisible()
        
        # Save to history
        self.conversation_history.append({
            'role': 'User',
            'content': text
        })
    
    def _send_message(self):
        """Send user message"""
        user_input = self.input_text.toPlainText().strip()
        if not user_input:
            return
        
        self._add_user_message(user_input)
        self.input_text.clear()
        
        # Get response from assistant
        response = self.assistant.answer_question(user_input)
        self._add_assistant_message(response)

    # def _get_selection(self):
        # """Helper to safely get selection from editor"""
        # try:
            # if hasattr(self.main_window, 'editor_manager'):
                # editor = self.main_window.editor_manager.get_current_editor()
                # if editor:
                    # cursor = editor.textCursor()
                    # if cursor.hasSelection():
                        # return cursor.selectedText()
        # except Exception as e:
            # print(f"Error getting selection: {e}")
        # return None
        
    
    def _explain_selection(self):
        """Explain selected LaTeX code"""
        try:
            editor = self.main_window.editor_manager.get_current_editor()
            if editor:
                cursor = editor.textCursor()
                if cursor.hasSelection():
                    selected_text = cursor.selectedText()
                    self._add_user_message(f"Explain: {selected_text[:100]}...")
                    
                    response = self.assistant.explain_code(selected_text)
                    self._add_assistant_message(response)
                else:
                    QMessageBox.information(self, "No Selection", "Please select some LaTeX code first")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not get selection: {str(e)}")
    
    def _improve_selection(self):
        """Improve selected text"""
        try:
            editor = self.main_window.editor_manager.get_current_editor()
            if editor:
                cursor = editor.textCursor()
                if cursor.hasSelection():
                    selected_text = cursor.selectedText()
                    self._add_user_message(f"Improve: {selected_text[:100]}...")
                    
                    response = self.assistant.improve_text(selected_text)
                    self._add_assistant_message(response)
                else:
                    QMessageBox.information(self, "No Selection", "Please select some text first")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not get selection: {str(e)}")
    
    def _fix_latex_errors(self):
        """Fix LaTeX errors"""
        try:
            # Get errors from terminal/output
            error_text = self._get_latex_errors()
            if error_text:
                self._add_user_message("Fix these errors...")
                
                response = self.assistant.fix_errors(error_text)
                self._add_assistant_message(response)
            else:
                self._add_system_message("No errors detected. Compile your document to see errors.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not get errors: {str(e)}")
    
    def _get_latex_errors(self):
        """Get LaTeX error messages"""
        try:
            if hasattr(self.main_window, 'terminal_widget'):
                terminal_text = self.main_window.terminal_widget.output_display.toPlainText()
                lines = terminal_text.split('\n')
                errors = [line for line in lines if 'error' in line.lower() or '!' in line]
                return '\n'.join(errors[-20:])
        except:
            pass
        return None
    
    def _insert_template(self, item=None):
        """Insert selected template"""
        if not item:
            item = self.template_list.currentItem()
        
        if not item:
            return
        
        template_name = item.text().lower().replace(' ', '_')
        
        # Map display names to template keys
        template_map = {
            'figure_with_image': 'figure',
            'basic_table': 'table',
            'numbered_equation': 'equation',
            'bullet_list': 'itemize',
            'numbered_list': 'enumerate'
        }
        
        template_key = template_map.get(template_name)
        if not template_key:
            return
        
        template_code = self.assistant.get_template(template_key)
        
        if template_code:
            # Show in chat
            self._add_system_message(f"Template: {item.text()}")
            self._add_assistant_message(template_code)
            
            # Try to insert into editor
            try:
                editor = self.main_window.editor_manager.get_current_editor()
                if editor:
                    cursor = editor.textCursor()
                    # Extract just the code part
                    code = template_code.split('\n\n', 1)[1] if '\n\n' in template_code else template_code
                    cursor.insertText(code)
                    self._add_system_message("✓ Template inserted into editor!")
            except:
                self._add_system_message("💡 Copy the template from above and paste it into your document.")
    
    def _show_quick_help(self, item):
        """Show quick help for topic"""
        topic = item.text()
        self._add_user_message(topic)
        
        response = self.assistant.answer_question(topic)
        self._add_assistant_message(response)
    
    def _clear_chat(self):
        """Clear chat history"""
        self.chat_display.clear()
        self.conversation_history.clear()
        self._add_welcome_message()
    
    def _copy_last_response(self):
        """Copy last assistant response"""
        text = self.chat_display.toPlainText()
        lines = text.split('\n\n')
        
        # Find last "Assistant:" message
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].startswith('Assistant:'):
                response_text = lines[i].replace('Assistant: ', '')
                
                from PyQt5.QtWidgets import QApplication
                QApplication.clipboard().setText(response_text)
                self._add_system_message("✓ Response copied to clipboard!")
                return
        
        QMessageBox.information(self, "No Response", "No assistant response to copy yet")
    
    def eventFilter(self, obj, event):
        """Handle key events"""
        if obj == self.input_text and event.type() == event.KeyPress:
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                if event.modifiers() != Qt.ShiftModifier:
                    self._send_message()
                    return True
        return super().eventFilter(obj, event)


    # def _show_settings(self):
        # """Show online AI settings dialog"""
        # from PyQt5.QtWidgets import QDialog, QFormLayout, QComboBox, QLineEdit, QDialogButtonBox, QCheckBox
        
        # dialog = QDialog(self)
        # dialog.setWindowTitle("AI Settings")
        # dialog.setMinimumWidth(400)
        
        # layout = QFormLayout(dialog)
        
        # # Online mode toggle
        # online_check = QCheckBox("Use Online AI (requires internet)")
        # online_check.setChecked(self.online_mode)
        # layout.addRow("Mode:", online_check)
        
        # # Provider selection
        # provider_combo = QComboBox()
        # for key, info in self.online_ai.available_providers.items():
            # label = f"{info['name']} ({'Free' if info['free'] else 'Paid'})"
            # provider_combo.addItem(label, key)
        # current_idx = list(self.online_ai.available_providers.keys()).index(self.online_ai.provider)
        # provider_combo.setCurrentIndex(current_idx)
        # layout.addRow("Provider:", provider_combo)
        
        # # API Key
        # api_key_input = QLineEdit()
        # api_key_input.setEchoMode(QLineEdit.Password)
        # if self.online_ai.api_key:
            # api_key_input.setText(self.online_ai.api_key)
        # api_key_input.setPlaceholderText("Enter API key (if required)")
        # layout.addRow("API Key:", api_key_input)
        
        # # Model selection
        # model_combo = QComboBox()
        
        def update_models():
            provider_key = provider_combo.currentData()
            models = self.online_ai.available_providers[provider_key]["models"]
            model_combo.clear()
            model_combo.addItems(models)
        
        provider_combo.currentIndexChanged.connect(update_models)
        update_models()
        layout.addRow("Model:", model_combo)
        
        # Info label
        info_label = QLabel("💡 Groq offers free API keys at: console.groq.com")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #0078d4; padding: 10px;")
        layout.addRow(info_label)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        
        if dialog.exec_() == QDialog.Accepted:
            self.online_mode = online_check.isChecked()
            provider_key = provider_combo.currentData()
            api_key = api_key_input.text().strip()
            model = model_combo.currentText()
            
            self.online_ai.set_provider(provider_key, api_key if api_key else None, model)
            
            # Update info label
            if self.online_mode:
                provider_name = self.online_ai.available_providers[provider_key]["name"]
                info_label.setText(f"Online Mode: {provider_name}")
                self._add_system_message(f"✓ Switched to online AI: {provider_name}")
            else:
                self._add_system_message("✓ Switched to offline mode")


    def _send_message(self):
        """Modified send message to support online AI"""
        user_input = self.input_text.toPlainText().strip()
        if not user_input:
            return
        
        self._add_user_message(user_input)
        self.input_text.clear()
        
        # Check if online mode
        if self.online_mode and self.online_ai.is_configured():
            self._send_online_query(user_input)
        else:
            # Use local assistant
            response = self.assistant.answer_question(user_input)
            self._add_assistant_message(response)


    def _send_online_query(self, user_input):
        """Send query to online AI"""
        # Build context
        system_prompt = """Be concise and helpful."""
        
        full_prompt = f"{system_prompt}\n\nUser: {user_input}\n\nAssistant:"
        
        # Show loading
        self._add_system_message("🌐 Querying online AI...")
        self.send_btn.setEnabled(False)
        
        # Create thread
        self.ai_thread = OnlineAIThread(
            self.online_ai,
            full_prompt,
            max_tokens=512,
            temperature=0.7
        )
        self.ai_thread.response_ready.connect(self._on_online_response)
        self.ai_thread.error_occurred.connect(self._on_online_error)
        self.ai_thread.start()


    def _on_online_response(self, response):
        """Handle online AI response"""
        self._add_assistant_message(response)
        self.send_btn.setEnabled(True)


    def _on_online_error(self, error):
        """Handle online AI error"""
        self._add_system_message(f"❌ Error: {error}")
        self._add_system_message("💡 Falling back to offline mode...")
        self.send_btn.setEnabled(True)



# Usage example for integration
if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget
    
    app = QApplication(sys.argv)
    
    # Create main window
    main_window = QMainWindow()
    main_window.setWindowTitle("LaTeX Editor with Lite AI")
    main_window.resize(1000, 700)
    
    # Create tab widget
    tabs = QTabWidget()
    
    # Add AI widget
    ai_widget = AIWidgetLite(main_window)
    tabs.addTab(ai_widget, "AI Assistant")
    
    main_window.setCentralWidget(tabs)
    main_window.show()
    
    sys.exit(app.exec_())