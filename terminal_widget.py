"""
Terminal Widget for LaTeX Editor
Save this as: terminal_widget.py in your project directory
"""

import os
import sys
import platform
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                             QLineEdit, QPushButton, QLabel)
from PyQt5.QtCore import Qt, QProcess, pyqtSignal
from PyQt5.QtGui import QTextCursor, QFont, QColor


class TerminalWidget(QWidget):
    """A terminal widget that runs in the current LaTeX file's directory"""
    
    command_executed = pyqtSignal(str, int)  # command, exit_code
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.current_dir = os.path.expanduser("~")  # Start in home directory
        self.process = None
        self.command_history = []
        self.history_index = -1
        
        self._setup_ui()
        self._setup_process()
        self._update_prompt()
    
    def _show_help(self):
        """Display help for built-in commands"""
        help_text = """
╔════════════════════════════════════════════════════════════╗
║              TERMINAL BUILT-IN COMMANDS                    ║
╚════════════════════════════════════════════════════════════╝

📁 NAVIGATION:
  cd <dir>          Change directory
  cd                Go to home directory
  pwd               Print working directory

📄 PDF VIEWER:
  pdfviewer <file>  Open PDF in app's PDF viewer
                    Example: pdfviewer document.pdf

📝 TEX EDITOR:
  texedit <file>    Open TEX file in app's editor
                    Example: texedit document.tex

🔧 UTILITIES:
  clear, cls        Clear terminal output
  help, ?           Show this help message

📝 LATEX COMPILATION:
  # Quick PDF compilation
  pdflatex -interaction=nonstopmode myfile.tex
  pdfviewer myfile.pdf

  # Traditional workflow (TEX → DVI → PDF)
  latex myfile.tex
  dvipdf myfile.dvi myfile.pdf
  pdfviewer myfile.pdf

⌨️  SHORTCUTS:
  ↑/↓ Arrow         Navigate command history
  Tab               Autocomplete file/directory names
  Enter             Execute command

════════════════════════════════════════════════════════════

"""
        self._append_output(help_text, "#4ec9b0")
        self._update_prompt()
    
    def _handle_autocomplete(self):
        """Handle Tab key for file/directory autocompletion"""
        text = self.input_line.text()
        cursor_pos = self.input_line.cursorPosition()
        
        # Get the part before cursor
        text_before_cursor = text[:cursor_pos]
        
        # Parse the command and arguments
        parts = text_before_cursor.split()
        
        if not parts:
            return
        
        # Determine what to autocomplete
        if len(parts) == 1 and not text_before_cursor.endswith(' '):
            # Completing command name
            prefix = parts[0]
            matches = self._get_command_matches(prefix)
        else:
            # Completing filename/path
            if text_before_cursor.endswith(' '):
                prefix = ""
            else:
                prefix = parts[-1]
            
            matches = self._get_path_matches(prefix)
        
        if not matches:
            return
        
        # Check if we're cycling through matches
        if (self._completion_prefix == prefix and 
            self._completion_matches == matches and 
            len(matches) > 1):
            # Cycle to next match
            self._completion_index = (self._completion_index + 1) % len(matches)
            completion = matches[self._completion_index]
        else:
            # New completion
            self._completion_matches = matches
            self._completion_prefix = prefix
            self._completion_index = 0
            
            if len(matches) == 1:
                completion = matches[0]
            else:
                # Multiple matches - find common prefix
                common_prefix = self._get_common_prefix(matches)
                if common_prefix and len(common_prefix) > len(prefix):
                    completion = common_prefix
                else:
                    # Show all matches
                    self._append_output("\n", "#d4d4d4")
                    
                    # Display matches in columns if possible
                    if len(matches) <= 50:  # Reasonable number to display
                        # Show matches in a nice format
                        max_len = max(len(m) for m in matches) + 2
                        cols = max(1, 80 // max_len)  # Fit in ~80 char width
                        
                        for i, match in enumerate(matches):
                            # Color directories differently
                            if match.endswith(os.path.sep):
                                color = "#4ec9b0"  # Cyan for directories
                            else:
                                color = "#569cd6"  # Blue for files
                            
                            self._append_output(f"{match:<{max_len}}", color)
                            
                            # New line after each row
                            if (i + 1) % cols == 0 or i == len(matches) - 1:
                                self._append_output("\n", "#d4d4d4")
                    else:
                        # Too many matches, just list them
                        self._append_output(f"  {len(matches)} matches. Type more characters to narrow down.\n", "#ce9178")
                    
                    self._append_output("\n", "#d4d4d4")
                    self._update_prompt()
                    return
        
        # Replace the prefix with completion
        if len(parts) == 1 and not text_before_cursor.endswith(' '):
            # Replace command
            new_text = completion + text[cursor_pos:]
            new_cursor_pos = len(completion)
        else:
            # Replace filename
            if text_before_cursor.endswith(' '):
                new_text = text_before_cursor + completion + text[cursor_pos:]
                new_cursor_pos = len(text_before_cursor) + len(completion)
            else:
                # Remove the partial prefix
                before_prefix = text[:cursor_pos - len(prefix)]
                new_text = before_prefix + completion + text[cursor_pos:]
                new_cursor_pos = len(before_prefix) + len(completion)
        
        self.input_line.setText(new_text)
        self.input_line.setCursorPosition(new_cursor_pos)
    
    def _get_command_matches(self, prefix):
        """Get matching command names"""
        commands = ['cd', 'pwd', 'clear', 'cls', 'help', 'pdfviewer', 'texedit']
        matches = [cmd for cmd in commands if cmd.startswith(prefix)]
        return sorted(matches)
    
    def _get_path_matches(self, prefix):
        """Get matching file/directory paths"""
        try:
            # Determine directory and filename prefix
            if os.path.sep in prefix or (platform.system() == 'Windows' and '/' in prefix):
                # Path includes directory
                dir_path = os.path.dirname(prefix)
                file_prefix = os.path.basename(prefix)
                
                if not dir_path:
                    search_dir = self.current_dir
                elif os.path.isabs(dir_path):
                    search_dir = dir_path
                else:
                    search_dir = os.path.join(self.current_dir, dir_path)
            else:
                # Just filename
                search_dir = self.current_dir
                file_prefix = prefix
                dir_path = ""
            
            # Normalize path
            search_dir = os.path.normpath(search_dir)
            
            if not os.path.isdir(search_dir):
                return []
            
            # Get matching files/directories
            matches = []
            try:
                # Use os.scandir for better Unicode handling
                with os.scandir(search_dir) as entries:
                    for entry in entries:
                        try:
                            entry_name = entry.name
                            
                            # Check if it matches the prefix
                            if entry_name.startswith(file_prefix) or file_prefix == "":
                                # Build the completion string
                                if dir_path:
                                    completion = os.path.join(dir_path, entry_name)
                                else:
                                    completion = entry_name
                                
                                # Add separator for directories
                                if entry.is_dir():
                                    completion += os.path.sep
                                
                                matches.append(completion)
                        except (UnicodeDecodeError, OSError):
                            # Skip entries with encoding issues
                            continue
                            
            except PermissionError:
                return []
            except Exception as e:
                return []
            
            return sorted(matches, key=lambda x: (not x.endswith(os.path.sep), x.lower()))
            
        except Exception as e:
            return []
    
    def _get_common_prefix(self, strings):
        """Get the common prefix of multiple strings"""
        if not strings:
            return ""
        
        # Find common prefix
        prefix = strings[0]
        for s in strings[1:]:
            while not s.startswith(prefix):
                prefix = prefix[:-1]
                if not prefix:
                    return ""
        
        return prefix
        
    def _setup_ui(self):
        """Setup the terminal UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Output display (terminal output)
        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)
        self.output_display.setLineWrapMode(QTextEdit.NoWrap)
        
        # Use monospace font
        font = QFont("Courier New", 9)
        if platform.system() == "Darwin":  # macOS
            font = QFont("Monaco", 10)
        elif platform.system() == "Linux":
            font = QFont("Monospace", 9)
        
        self.output_display.setFont(font)
        self.output_display.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3e3e3e;
            }
        """)
        
        # Input line
        input_layout = QHBoxLayout()
        
        self.prompt_label = QLabel()
        self.prompt_label.setFont(font)
        self.prompt_label.setStyleSheet("color: #4ec9b0; background-color: #1e1e1e;")
        
        self.input_line = QLineEdit()
        self.input_line.setFont(font)
        self.input_line.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3e3e3e;
                padding: 2px 5px;
            }
        """)
        self.input_line.returnPressed.connect(self._execute_command)
        self.input_line.installEventFilter(self)
        
        # Autocompletion state
        self._completion_matches = []
        self._completion_index = 0
        self._completion_prefix = ""
        
        # Clear button
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear_output)
        clear_btn.setMaximumWidth(60)
        
        input_layout.addWidget(self.prompt_label)
        input_layout.addWidget(self.input_line)
        input_layout.addWidget(clear_btn)
        
        layout.addWidget(self.output_display)
        layout.addLayout(input_layout)
        
    def _setup_process(self):
        """Setup the QProcess for running commands"""
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._handle_output)
        self.process.finished.connect(self._process_finished)
        
    def _update_prompt(self):
        """Update the prompt to show current directory"""
        # Get shortened path
        home = os.path.expanduser("~")
        display_dir = self.current_dir.replace(home, "~")
        
        if platform.system() == "Windows":
            prompt = f"{display_dir}> "
        else:
            prompt = f"{display_dir}$ "
            
        self.prompt_label.setText(prompt)
        
    def _append_output(self, text, color=None):
        """Append text to output display"""
        cursor = self.output_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        if color:
            format = cursor.charFormat()
            format.setForeground(QColor(color))
            cursor.setCharFormat(format)
            
        cursor.insertText(text)
        self.output_display.setTextCursor(cursor)
        self.output_display.ensureCursorVisible()
        
    def _execute_command(self):
        """Execute the command entered by user"""
        command = self.input_line.text().strip()
        if not command:
            return
            
        # Add to history
        if not self.command_history or self.command_history[-1] != command:
            self.command_history.append(command)
        self.history_index = len(self.command_history)
        
        # Display command
        prompt = self.prompt_label.text()
        self._append_output(f"{prompt}{command}\n", "#d4d4d4")
        
        # Clear input
        self.input_line.clear()
        
        # Handle built-in commands
        if command.startswith("cd "):
            self._change_directory(command[3:].strip())
            return
        elif command == "cd":
            self._change_directory(os.path.expanduser("~"))
            return
        elif command in ["clear", "cls"]:
            self._clear_output()
            return
        elif command == "pwd":
            self._append_output(f"{self.current_dir}\n", "#d4d4d4")
            self._update_prompt()
            return
        elif command.startswith("pdfviewer "):
            # Custom command to open PDF in the app's PDF viewer
            self._open_in_pdfviewer(command[10:].strip())
            return
        elif command.startswith("texedit "):
            # Custom command to open TEX file in the app's editor
            self._open_in_texeditor(command[8:].strip())
            return
        elif command in ["help", "?"]:
            self._show_help()
            return
            
        # Execute external command
        self._run_command(command)
        
    def _change_directory(self, path):
        """Change current directory"""
        try:
            # Expand ~ and make absolute
            if path.startswith("~"):
                path = os.path.expanduser(path)
            elif not os.path.isabs(path):
                path = os.path.join(self.current_dir, path)
                
            # Normalize path - handles Unicode properly
            path = os.path.normpath(path)
            path = os.path.abspath(path)
            
            if os.path.isdir(path):
                self.current_dir = path
                self._update_prompt()
            else:
                self._append_output(f"cd: no such directory: {path}\n", "#f48771")
        except Exception as e:
            self._append_output(f"cd: error: {str(e)}\n", "#f48771")
            
    def _run_command(self, command):
        """Run an external command"""
        if self.process.state() != QProcess.NotRunning:
            self._append_output("A command is already running. Please wait...\n", "#f48771")
            return
            
        # Set working directory
        self.process.setWorkingDirectory(self.current_dir)
        
        # Platform-specific shell
        if platform.system() == "Windows":
            self.process.start("cmd.exe", ["/c", command])
        else:
            self.process.start("/bin/sh", ["-c", command])
            
    def _handle_output(self):
        """Handle process output"""
        data = self.process.readAllStandardOutput()
        # Try multiple encodings
        try:
            text = bytes(data).decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = bytes(data).decode(sys.getfilesystemencoding())
            except UnicodeDecodeError:
                text = bytes(data).decode("utf-8", errors="replace")
        self._append_output(text, "#d4d4d4")
        
    def _process_finished(self, exit_code, exit_status):
        """Handle process completion"""
        if exit_code != 0:
            self._append_output(f"\nProcess exited with code {exit_code}\n", "#f48771")
        self._update_prompt()
        self.command_executed.emit(self.input_line.text(), exit_code)
        
    def _clear_output(self):
        """Clear the output display"""
        self.output_display.clear()
    
    def _open_in_pdfviewer(self, filename):
        """Open a PDF file in the app's PDF viewer"""
        # Handle relative and absolute paths
        if not filename:
            self._append_output("Usage: pdfviewer <filename.pdf>\n", "#f48771")
            self._append_output("Example: pdfviewer document.pdf\n", "#d4d4d4")
            return
        
        try:
            # Handle quotes if present
            filename = filename.strip('"').strip("'")
            
            # Resolve path
            if os.path.isabs(filename):
                pdf_path = filename
            else:
                pdf_path = os.path.join(self.current_dir, filename)
            
            # Normalize path - handle Unicode properly
            pdf_path = os.path.normpath(pdf_path)
            
            # Convert to absolute path to avoid issues
            pdf_path = os.path.abspath(pdf_path)
            
            # Check if file exists
            if not os.path.exists(pdf_path):
                self._append_output(f"Error: File not found: {pdf_path}\n", "#f48771")
                return
            
            # Check if it's a PDF file
            if not pdf_path.lower().endswith('.pdf'):
                self._append_output(f"Warning: File does not have .pdf extension: {pdf_path}\n", "#ce9178")
                # Continue anyway in case it's a PDF with wrong extension
            
            # Open in PDF viewer
            if hasattr(self.main_window, 'pdf_manager') and self.main_window.pdf_manager:
                try:
                    # Use the absolute path with proper encoding
                    self.main_window.pdf_manager.load_pdf_in_viewer(pdf_path)
                    
                    # Get display name (handle Unicode for display)
                    display_name = os.path.basename(pdf_path)
                    self._append_output(f"✓ Opened in PDF viewer: {display_name}\n", "#6a9955")
                    
                    # Show path if it's different from just the filename
                    if os.path.dirname(pdf_path) != self.current_dir:
                        self._append_output(f"  Path: {pdf_path}\n", "#d4d4d4")
                        
                except Exception as e:
                    error_msg = str(e)
                    self._append_output(f"Error opening PDF: {error_msg}\n", "#f48771")
                    # Try to provide helpful info
                    self._append_output(f"File path: {pdf_path}\n", "#d4d4d4")
                    self._append_output(f"File exists: {os.path.exists(pdf_path)}\n", "#d4d4d4")
            else:
                self._append_output("Error: PDF viewer not available\n", "#f48771")
        
        except Exception as e:
            error_msg = str(e)
            self._append_output(f"Error processing file: {error_msg}\n", "#f48771")
        
        self._update_prompt()
    
    def _open_in_texeditor(self, filename):
        """Open a TEX file in the app's editor"""
        # Handle relative and absolute paths
        if not filename:
            self._append_output("Usage: texedit <filename.tex>\n", "#f48771")
            self._append_output("Example: texedit document.tex\n", "#d4d4d4")
            return
        
        try:
            # Handle quotes if present
            filename = filename.strip('"').strip("'")
            
            # Resolve path
            if os.path.isabs(filename):
                tex_path = filename
            else:
                tex_path = os.path.join(self.current_dir, filename)
            
            # Normalize path - handle Unicode properly
            tex_path = os.path.normpath(tex_path)
            
            # Convert to absolute path to avoid issues
            tex_path = os.path.abspath(tex_path)
            
            # Check if file exists
            if not os.path.exists(tex_path):
                self._append_output(f"Error: File not found: {tex_path}\n", "#f48771")
                self._append_output(f"Create it? (y/n): ", "#ce9178")
                # For now, just report error - could add file creation later
                return
            
            # Check if it's a TEX file
            if not tex_path.lower().endswith('.tex'):
                self._append_output(f"Warning: File does not have .tex extension: {tex_path}\n", "#ce9178")
                # Continue anyway in case it's a TEX file with wrong extension
            
            # Open in editor
            if hasattr(self.main_window, 'editor_manager') and self.main_window.editor_manager:
                try:
                    # Use the editor manager's method to open the file
                    self.main_window.editor_manager.open_specific_file(tex_path)
                    
                    # Get display name (handle Unicode for display)
                    display_name = os.path.basename(tex_path)
                    self._append_output(f"✓ Opened in editor: {display_name}\n", "#6a9955")
                    
                    # Show path if it's different from just the filename
                    if os.path.dirname(tex_path) != self.current_dir:
                        self._append_output(f"  Path: {tex_path}\n", "#d4d4d4")
                        
                except Exception as e:
                    error_msg = str(e)
                    self._append_output(f"Error opening TEX file: {error_msg}\n", "#f48771")
                    # Try to provide helpful info
                    self._append_output(f"File path: {tex_path}\n", "#d4d4d4")
                    self._append_output(f"File exists: {os.path.exists(tex_path)}\n", "#d4d4d4")
            else:
                self._append_output("Error: Editor not available\n", "#f48771")
        
        except Exception as e:
            error_msg = str(e)
            self._append_output(f"Error processing file: {error_msg}\n", "#f48771")
        
        self._update_prompt()
        
    def eventFilter(self, obj, event):
        """Handle key events for command history and autocompletion"""
        if obj == self.input_line and event.type() == event.KeyPress:
            if event.key() == Qt.Key_Up:
                # Previous command
                if self.command_history and self.history_index > 0:
                    self.history_index -= 1
                    self.input_line.setText(self.command_history[self.history_index])
                return True
            elif event.key() == Qt.Key_Down:
                # Next command
                if self.command_history and self.history_index < len(self.command_history) - 1:
                    self.history_index += 1
                    self.input_line.setText(self.command_history[self.history_index])
                elif self.history_index >= len(self.command_history) - 1:
                    self.history_index = len(self.command_history)
                    self.input_line.clear()
                return True
            elif event.key() == Qt.Key_Tab:
                # Autocomplete filename
                self._handle_autocomplete()
                return True
                
        return super().eventFilter(obj, event)
        
    def set_working_directory(self, path):
        """Set the working directory (called when switching LaTeX files)"""
        try:
            if os.path.isfile(path):
                path = os.path.dirname(path)
            
            # Normalize and make absolute
            path = os.path.normpath(path)
            path = os.path.abspath(path)
                
            if os.path.isdir(path):
                self.current_dir = path
                self._update_prompt()
                
                # Get display path (handle Unicode)
                display_path = path
                try:
                    # Try to get a nice display version
                    home = os.path.expanduser("~")
                    if path.startswith(home):
                        display_path = path.replace(home, "~")
                except:
                    pass
                
                self._append_output(f"\n--- Changed directory to: {display_path} ---\n\n", "#4ec9b0")
        except Exception as e:
            self._append_output(f"Error setting directory: {str(e)}\n", "#f48771")
            
    def compile_current_file(self, tex_file):
        """Quick compile the current LaTeX file (pdflatex direct to PDF)"""
        if not tex_file or not os.path.isfile(tex_file):
            self._append_output("No LaTeX file to compile.\n", "#f48771")
            return
            
        # Change to file directory
        file_dir = os.path.dirname(tex_file)
        file_name = os.path.basename(tex_file)
        
        if file_dir != self.current_dir:
            self.set_working_directory(file_dir)
            
        # Run pdflatex in non-stop mode (never prompts for input)
        command = f"pdflatex -interaction=nonstopmode -halt-on-error {file_name}"
        self._append_output(f"\n--- Compiling: {file_name} ---\n", "#4ec9b0")
        self._run_command(command)
    
    def compile_tex_dvi_pdf(self, tex_file):
        """Compile LaTeX file through TEX -> DVI -> PDF workflow and open in viewer"""
        if not tex_file or not os.path.isfile(tex_file):
            self._append_output("No LaTeX file to compile.\n", "#f48771")
            return
            
        # Change to file directory
        file_dir = os.path.dirname(tex_file)
        file_name = os.path.basename(tex_file)
        base_name = os.path.splitext(file_name)[0]
        
        if file_dir != self.current_dir:
            self.set_working_directory(file_dir)
        
        self._append_output(f"\n{'='*60}\n", "#4ec9b0")
        self._append_output(f"Starting TEX → DVI → PDF compilation workflow\n", "#4ec9b0")
        self._append_output(f"File: {file_name}\n", "#4ec9b0")
        self._append_output(f"{'='*60}\n\n", "#4ec9b0")
        
        # Store compilation info for callback
        self._compilation_workflow = {
            'file_dir': file_dir,
            'base_name': base_name,
            'tex_file': tex_file,
            'stage': 'tex',
            'total_stages': 3
        }
        
        # Step 1: TEX to DVI
        self._append_output("Step 1/3: Compiling TEX to DVI...\n", "#569cd6")
        command = f"latex -interaction=nonstopmode {file_name}"
        
        # Disconnect old signal and connect new workflow signal
        try:
            self.process.finished.disconnect()
        except:
            pass
        self.process.finished.connect(self._handle_workflow_step)
        
        self._run_command(command)
    
    def _handle_workflow_step(self, exit_code, exit_status):
        """Handle each step of the TEX -> DVI -> PDF workflow"""
        workflow = getattr(self, '_compilation_workflow', None)
        if not workflow:
            # Restore normal process handler
            try:
                self.process.finished.disconnect()
            except:
                pass
            self.process.finished.connect(self._process_finished)
            self._process_finished(exit_code, exit_status)
            return
        
        stage = workflow['stage']
        base_name = workflow['base_name']
        file_dir = workflow['file_dir']
        
        # Check if current stage failed
        if exit_code != 0:
            self._append_output(f"\n❌ Error: {stage.upper()} compilation failed with exit code {exit_code}\n", "#f48771")
            self._append_output("Workflow aborted.\n", "#f48771")
            self._append_output(f"{'='*60}\n\n", "#f48771")
            
            # Restore normal handler
            try:
                self.process.finished.disconnect()
            except:
                pass
            self.process.finished.connect(self._process_finished)
            delattr(self, '_compilation_workflow')
            return
        
        # Proceed to next stage
        if stage == 'tex':
            # Step 2: DVI to PDF using dvipdf or dvipdfm
            dvi_file = os.path.join(file_dir, f"{base_name}.dvi")
            if not os.path.exists(dvi_file):
                self._append_output(f"\n❌ Error: DVI file not found: {dvi_file}\n", "#f48771")
                self._append_output("Workflow aborted.\n", "#f48771")
                self._append_output(f"{'='*60}\n\n", "#f48771")
                
                try:
                    self.process.finished.disconnect()
                except:
                    pass
                self.process.finished.connect(self._process_finished)
                delattr(self, '_compilation_workflow')
                return
            
            self._append_output(f"✓ TEX to DVI completed successfully\n\n", "#6a9955")
            self._append_output("Step 2/3: Converting DVI to PDF...\n", "#569cd6")
            
            # Update workflow stage
            workflow['stage'] = 'dvi'
            
            # Use dvipdf (Ghostscript-based, more common) or dvipdfm
            if platform.system() == "Windows":
                command = f"dvipdf {base_name}.dvi {base_name}.pdf"
            else:
                command = f"dvipdf {base_name}.dvi {base_name}.pdf"
            
            self._run_command(command)
            
        elif stage == 'dvi':
            # Final step: Open PDF in viewer
            pdf_file = os.path.join(file_dir, f"{base_name}.pdf")
            
            if not os.path.exists(pdf_file):
                self._append_output(f"\n❌ Error: PDF file not found: {pdf_file}\n", "#f48771")
                self._append_output("Workflow aborted.\n", "#f48771")
                self._append_output(f"{'='*60}\n\n", "#f48771")
            else:
                self._append_output(f"✓ DVI to PDF completed successfully\n\n", "#6a9955")
                self._append_output("Step 3/3: Opening PDF in viewer...\n", "#569cd6")
                
                # Open in PDF viewer using internal command
                self._open_in_pdfviewer(f"{base_name}.pdf")
                
                self._append_output(f"\n{'='*60}\n", "#4ec9b0")
                self._append_output("✓ Compilation workflow completed successfully!\n", "#4ec9b0")
                self._append_output(f"{'='*60}\n\n", "#4ec9b0")
            
            # Restore normal handler
            try:
                self.process.finished.disconnect()
            except:
                pass
            self.process.finished.connect(self._process_finished)
            delattr(self, '_compilation_workflow')
            self._update_prompt()
