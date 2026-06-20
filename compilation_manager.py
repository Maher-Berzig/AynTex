# compilation_manager.py
"""
Compilation Manager - Enhanced with Configuration Integration
Handles LaTeX compilation with configuration-aware settings
"""
import sys
import os
import subprocess
import threading
from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QProcess
from PyQt5.QtWidgets import QMessageBox, QApplication
from PyQt5.QtGui import QTextCursor
#from silent_process import SilentProcess

class CompilationManager(QObject):    
    
    """Manages LaTeX compilation with configuration integration"""
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.worker = None
        self.worker_process = None
        self.compilation_timer = QTimer()
        self.compilation_timer.timeout.connect(self.update_compilation_status)
        
        # Track compilation output for error detection
        self.compilation_output = ""
        self.compilation_errors = ""

        # Configurable timeouts (in milliseconds)
        self.process_timeout_ms = 600000  # 10 minutes
        self.startup_timeout_ms = 10000   # 10 seconds
        
        # ADD THESE LINES:
        self.current_engine = None  # Track which engine is being used
        self._compilation_in_progress = False  # Track compilation state
        
        # Install click handler for log-file links in the output pane
        if hasattr(self.main_window, 'output_text'):
            #self.main_window.output_text.installEventFilter(self)
            self.main_window.output_text.viewport().installEventFilter(self)

    def eventFilter(self, obj, event):
        from PyQt5.QtCore import QEvent, Qt

        if obj is self.main_window.output_text:
            if event.type() == QEvent.MouseMove:
                if obj.anchorAt(event.pos()):
                    obj.setCursor(Qt.PointingHandCursor)
                else:
                    obj.setCursor(Qt.IBeamCursor)

            elif event.type() == QEvent.MouseButtonRelease:
                #anchor = obj.anchorAt(event.pos())
                anchor = obj.parent().anchorAt(event.pos())
                if anchor:
                    self._open_log_in_editor(anchor)
                    return True

        return super().eventFilter(obj, event)

    # the function  _handle_link is in main_window    
    # def _handle_link(self, url):
        # path = url.toLocalFile()  # ✅ THIS is the key

        # if path:
            # self._open_log_in_editor(path)

    def _append_log_link(self, output: str):
        """Append a clickable log-file link at the bottom of the output pane."""
        import re
        from PyQt5.QtGui import QTextCharFormat, QColor, QFont
        if not hasattr(self.main_window, 'output_text'):
            return
            
        match = re.search(
            r'Transcript written on\s+([^\s\n]+\.log)',
            output,
            re.IGNORECASE,
        )
        if not match:
            return

        log_name = match.group(1).strip().strip('"').strip("'")
        current_file = self.main_window.editor_manager.current_file
        if current_file:
            log_path = os.path.normpath(
                os.path.join(os.path.dirname(current_file), log_name)
            )
        else:
            log_path = log_name

        if not os.path.isfile(log_path):
            return

        ot = self.main_window.output_text
        cursor = ot.textCursor()
        cursor.movePosition(QTextCursor.End)

        # Separator line
        sep_fmt = QTextCharFormat()
        sep_fmt.setForeground(QColor("#888888"))
        cursor.insertText("\n──────────────────────\n📄  ", sep_fmt)

        # Anchor link — setAnchor/setAnchorHref is what charFormat().anchorHref() reads back
        link_fmt = QTextCharFormat()
        link_fmt.setForeground(QColor("#4a90d9"))
        link_fmt.setUnderlineStyle(QTextCharFormat.SingleUnderline)
        link_fmt.setFontWeight(QFont.Bold)
        #link_fmt.setAnchor(True)
        #link_fmt.setAnchorHref(log_path)
        #cursor.insertText(f"Open {os.path.basename(log_path)} in editor", link_fmt)

        from PyQt5.QtCore import QUrl

        url = QUrl.fromLocalFile(log_path)

        cursor.insertHtml(
            f'<a href="{url.toString(QUrl.FullyEncoded)}">'
            f'<b>Open {os.path.basename(log_path)}</b></a>'
        )

        # Reset format for the trailing newline
        cursor.insertText("\n", QTextCharFormat())

        ot.setTextCursor(cursor)
        ot.moveCursor(QTextCursor.End)

    # the function  _open_log_in_editor is in main_window
    # def _open_log_in_editor(self, href: str):
        # """Open the log file carried by *href* in the editor."""
        # path = os.path.normpath(href)
        # if os.path.isfile(path):
            # self.main_window.editor_manager.open_specific_file(path)
        # else:
            # QMessageBox.warning(
                # self.main_window,
                # "File Not Found",
                # f"Cannot open log file:\n{path}",
            # )
            
    def auto_refresh_pdf(self):
        """Automatically refresh PDF after successful compilation"""
        try:
            # ✅ Use the saved path, not current_file
            if hasattr(self, '_last_compiled_pdf_path') and os.path.exists(self._last_compiled_pdf_path):
                pdf_path = self._last_compiled_pdf_path
                #print(f"🔄 Auto-refreshing PDF: {pdf_path}")
                # ✅ Delay slightly to ensure file is fully written
                QTimer.singleShot(400, lambda: self.main_window.pdf_manager.load_pdf_in_viewer(pdf_path))
            #else:
            #    print(f"🟡 PDF not found or path not saved: {getattr(self, '_last_compiled_pdf_path', 'None')}")
        except Exception as e:
            print(f"❌ Error in auto_refresh_pdf: {e}")
            import traceback
            traceback.print_exc()    
            
    def has_compilation_errors(self, output, errors):
        """Check if compilation output contains errors"""
        error_indicators = [
            '! ',  # LaTeX error prefix
            'Error:',
            'Fatal error',
            'Emergency stop',
            'Runaway argument',
            '! Undefined control sequence',
            '! Missing',
            '! Extra',
            '! LaTeX Error',
            'error occurred',
            'failed to compile'
        ]
        
        combined_text = (output + "\n" + errors).lower()
        return any(indicator.lower() in combined_text for indicator in error_indicators)
    
    # Include all other methods from the original CompilationManager...
    def focus_appropriate_tab(self, has_errors):
        """Focus Output tab (always in front), jump to error line if errors exist"""
        try:
            tab_widget = None
            possible_names = [
                'output_tabs', 'output_tab_widget', 'tabs_output', 'tabWidget',
                'outputTabs', 'outputTabWidget', 'tabsOutput', 'tab_widget',
                'main_tabs', 'mainTabs', 'console_tabs', 'consoleTabs',
                'bottom_tabs', 'bottomTabs', 'dock_tabs', 'dockTabs'
            ]
            for name in possible_names:
                if hasattr(self.main_window, name):
                    widget = getattr(self.main_window, name)
                    if hasattr(widget, 'setCurrentIndex'):
                        tab_widget = widget
                        break
            if not tab_widget:
                from PyQt5.QtWidgets import QTabWidget
                tab_widgets = self.main_window.findChildren(QTabWidget)
                for idx, widget in enumerate(tab_widgets):
                    has_output_error_tabs = False
                    for i in range(widget.count()):
                        tab_text = widget.tabText(i).lower()
                        if any(keyword in tab_text for keyword in ['output', 'error', 'console', 'log', 'compile']):
                            has_output_error_tabs = True
                            break
                    if has_output_error_tabs:
                        tab_widget = widget
                        break
                if not tab_widget and tab_widgets:
                    tab_widget = tab_widgets[0]
            if tab_widget:
                output_tab_index = -1
                output_keywords = ['output', 'console', 'log', 'compile', 'result']
                for i in range(tab_widget.count()):
                    tab_text = tab_widget.tabText(i).lower()
                    if any(keyword in tab_text for keyword in output_keywords):
                        output_tab_index = i
                        break
                # Always focus Output tab (it should be in front of Errors)
                if output_tab_index != -1:
                    current_index = tab_widget.currentIndex()
                    if output_tab_index != current_index:
                        tab_widget.setCurrentIndex(output_tab_index)
                        QApplication.processEvents()
                
                # If there are errors, jump to the error line in the editor
                if has_errors:
                    # Use a small delay to ensure UI is updated first
                    QTimer.singleShot(100, self._jump_to_error_line)
            else:
                self._try_alternative_tab_switching(has_errors)
        except Exception as e:
            print(f"Warning: Could not focus output tab: {e}")
            import traceback
            traceback.print_exc()
        
            
    def _try_alternative_tab_switching(self, has_errors):
        try:
            from PyQt5.QtWidgets import QDockWidget, QTabWidget
            dock_widgets = self.main_window.findChildren(QDockWidget)
            for dock in dock_widgets:
                tab_widgets = dock.findChildren(QTabWidget)
                for tab_widget in tab_widgets:
                    self._switch_tabs_in_widget(tab_widget, has_errors)
            from PyQt5.QtWidgets import QSplitter
            splitters = self.main_window.findChildren(QSplitter)
            for splitter in splitters:
                tab_widgets = splitter.findChildren(QTabWidget)
                for tab_widget in tab_widgets:
                    self._switch_tabs_in_widget(tab_widget, has_errors)
        except Exception as e:
            print(f"Alternative tab switching failed: {e}")
    
    def _switch_tabs_in_widget(self, tab_widget, has_errors):
        """Switch to Output tab in widget, jump to error if needed"""
        try:
            output_tab_index = -1
            for i in range(tab_widget.count()):
                tab_text = tab_widget.tabText(i).lower()
                if 'output' in tab_text or 'console' in tab_text:
                    output_tab_index = i
                    break
            
            # Always focus Output tab
            if output_tab_index != -1:
                tab_widget.setCurrentIndex(output_tab_index)
                
                # If errors, jump to error line
                if has_errors:
                    QTimer.singleShot(100, self._jump_to_error_line)
                return True
        except Exception as e:
            print(f"Error in _switch_tabs_in_widget: {e}")
        return False
    
    def _append_log_link(self, output: str):
        """
        Scan *output* for 'Transcript written on <name>.log' and append
        a clickable link at the bottom of the output pane.
        """
        import re
        if not hasattr(self.main_window, 'output_text'):
            return

        # LaTeX always ends a successful run with this line
        match = re.search(
            r'Transcript written on\s+([^\s\n]+\.log)',
            output,
            re.IGNORECASE,
        )
        if not match:
            return

        log_name = match.group(1).strip().strip('"').strip("'")

        # Resolve to an absolute path using the working directory
        current_file = self.main_window.editor_manager.current_file
        if current_file:
            working_dir = os.path.dirname(current_file)
            log_path = os.path.join(working_dir, log_name)
            log_path = os.path.normpath(log_path)
        else:
            log_path = log_name

        if not os.path.isfile(log_path):
            return

        # Append a styled HTML link — works because output_text is a QTextEdit
        ot = self.main_window.output_text
        ot.moveCursor(QTextCursor.End)
        ot.insertHtml(
            f'<br><span style="color:#888;">──────────────────────</span><br>'
            f'📄 &nbsp;'
            f'<a href="{log_path}" '
            f'   style="color:#4a90d9; text-decoration:underline; font-weight:bold;">'
            f'Open {os.path.basename(log_path)} in editor'
            f'</a><br>'
        )
        ot.moveCursor(QTextCursor.End)

    def _open_log_in_editor(self, url):
        """Open the log file whose path is carried by *url* in the editor."""
        from PyQt5.QtCore import QUrl
        path = url.toLocalFile() if isinstance(url, QUrl) else str(url)

        # QUrl.toLocalFile() can return empty string for plain paths
        if not path:
            path = url.toString() if isinstance(url, QUrl) else str(url)

        path = os.path.normpath(path)
        if os.path.isfile(path):
            self.main_window.editor_manager.open_specific_file(path)
        else:
            QMessageBox.warning(
                self.main_window,
                "File Not Found",
                f"Cannot open log file:\n{path}",
            )
            
 
    def on_compilation_finished(self, success, output, error):
        """Handle compilation completion"""
        #print(f"DEBUG: on_compilation_finished called with success={success}")
        #print(f"DEBUG: Output length: {len(output)}, Error length: {len(error)}")
        self.compilation_timer.stop()
        self.update_ui_for_compilation(False)

        # Display output
        if hasattr(self.main_window, 'output_text'):
            self.main_window.output_text.setPlainText(output)
        if hasattr(self.main_window, 'errors_text'):
            self.main_window.errors_text.setPlainText(error)
                
        # Check for errors and focus appropriate tab
        has_errors = self.has_compilation_errors(output, error) or not success
        #print(f"DEBUG: on_compilation_finished - has_errors={has_errors}")
        
        # ALWAYS call focus_appropriate_tab to ensure it runs
        self.focus_appropriate_tab(has_errors)


        # Update status
        engine = self.main_window.latex_engine
        if success and not has_errors:
            self.main_window.update_status_bar(
                self.main_window.translations[self.main_window.menu_language]["status_compile_success"].format(engine)
            )
            # NOTE: PDF auto-load is handled by on_latex_process_finished_with_cleanup
            # via _auto_load_pdf_after_compilation. Do NOT start a second timer here
            # or the two loaders will race and the first compilation may show no PDF.
        else:
            self.main_window.update_status_bar("❌ Compilation failed")
            self.main_window.update_status_bar(
                self.main_window.translations[self.main_window.menu_language]["status_compile_failed"].format(engine)
            )

        # ✅ Clean up
        self.worker = None
        self.worker_process = None  # ← Critical: Reset reference
        
    def update_compilation_status(self):
        if self.worker_process and self.worker_process.isRunning():
            engine = self.main_window.latex_engine
            status_text = self.main_window.translations[self.main_window.menu_language]["status_compiling"].format(engine)
            import time
            dots_count = int(time.time()) % 4
            status_text += "." * dots_count
            self.main_window.update_status_bar(status_text)
    
    def update_ui_for_compilation(self, compiling):
        """Update UI elements during/after compilation"""
        # Update toolbar actions
        if hasattr(self.main_window, 'toolbar_manager'):
            self.main_window.toolbar_manager.update_compile_actions(compiling)
           
    def show_error(self, title, message):
        """Show error message dialog"""
        QMessageBox.critical(self.main_window, title, message)
        
    def show_compilation_notification(self, title, message, error=False):
        """Show compilation result notification"""
        if error:
            QMessageBox.warning(self.main_window, title, message)
        else:
            QMessageBox.information(self.main_window, title, message)
    
    def get_compilation_history(self):
        """Get compilation history"""
        return {
            'last_engine': self.main_window.latex_engine,
            'last_file': self.main_window.editor_manager.current_file,
            'encoding': self.main_window.output_encoding
        }
    
    def is_engine_available(self, engine):
        """Check if a LaTeX engine is available"""
        try:
            # Suppress console window on Windows
            kwargs = {
                'capture_output': True,
                'text': True,
                'timeout': 5
            }
            if os.name == 'nt':
                kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
            
            result = subprocess.run([engine, "--version"], **kwargs)
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def get_available_engines(self):
        engines = ["pdflatex", "xelatex", "lualatex", "custom"]
        available = []
        for engine in engines:
            if self.is_engine_available(engine):
                available.append(engine)
        return available


    def get_latex_command_template(self, engine):
        """Get the command template for the specified engine"""
        if hasattr(self.main_window, 'config_manager'):
            try:
                command = self.main_window.config_manager.get_latex_command(engine)
                # Ensure -halt-on-error is present
                if command and '-halt-on-error' not in command:
                    # Add it after -interaction=nonstopmode
                    if '-interaction=nonstopmode' in command:
                        command = command.replace(
                            '-interaction=nonstopmode',
                            '-interaction=nonstopmode -halt-on-error'
                        )
                return command
            except:
                pass
        
        option_name = f'{engine}_option'
        if hasattr(self.main_window, option_name):
            command = getattr(self.main_window, option_name)
            if command:
                # Ensure -halt-on-error is present
                if '-halt-on-error' not in command:
                    if '-interaction=nonstopmode' in command:
                        command = command.replace(
                            '-interaction=nonstopmode',
                            '-interaction=nonstopmode -halt-on-error'
                        )
                return command
        
        # Updated default commands with -halt-on-error
        default_commands = {
            "pdflatex": "pdflatex -synctex=1 -interaction=nonstopmode -halt-on-error -shell-escape",
            "xelatex": "xelatex -synctex=1 -interaction=nonstopmode -halt-on-error -shell-escape", 
            "lualatex": "lualatex -synctex=1 -interaction=nonstopmode -halt-on-error -shell-escape",
            "custom": ""
        }
        
        return default_commands.get(
            engine, 
            f"{engine} -synctex=1 -interaction=nonstopmode -halt-on-error -shell-escape"
        )
        
    
    def get_latex_command(self, engine=None):
        """Get the custom command for a LaTeX engine"""
        if engine is None:
            engine = self.main_window.latex_engine
        
        option_name = f'{engine}_option'
        
        # First try to get from main_window attributes
        if hasattr(self.main_window, option_name):
            return getattr(self.main_window, option_name)
        
        # Then try to get from config file
        if self.config.has_option('compiler', option_name):
            return self.config.get('compiler', option_name)
        
        # Finally, use default
        return self.default_options.get(option_name, f'{engine} -synctex=1 -interaction=nonstopmode -shell-escape')

    def cleanup_process(self):
        """Safely cleanup the compilation process"""
        if hasattr(self, 'process') and self.process:
            try:
                # Disconnect all signals first to prevent crashes
                self.process.readyReadStandardOutput.disconnect()
                self.process.readyReadStandardError.disconnect()
                self.process.finished.disconnect()
                self.process.errorOccurred.disconnect()
            except:
                pass  # Ignore disconnect errors
            
            # Clean up the process
            if self.process.state() != QProcess.NotRunning:
                self.process.terminate()
                if not self.process.waitForFinished(2000):
                    self.process.kill()
            
            self.process.deleteLater()
            self.process = None   

    def _configure_process_for_silent_execution(self, process):
        """Configure QProcess to suppress console windows on Windows."""
        if os.name != 'nt':
            return

        CREATE_NO_WINDOW = 0x08000000

        # --- Attempt 1: setCreateProcessArgumentsModifier (PyQt5 ≥ 5.15) ---
        modifier_func = getattr(process, 'setCreateProcessArgumentsModifier', None)
        if modifier_func is not None:
            try:
                def _add_no_window_flag(args):
                    # args is QProcess.CreateProcessArguments (C++ struct)
                    args.flags |= CREATE_NO_WINDOW

                modifier_func(_add_no_window_flag)
                #print("DEBUG: Applied CREATE_NO_WINDOW via setCreateProcessArgumentsModifier")
                return   # success
            except (TypeError, AttributeError, OSError) as e:
                print(f"setCreateProcessArgumentsModifier failed: {e}")

        # --- Attempt 2: setProcessEnvironment trick (does NOT hide the
        #     window by itself, but keeps things from breaking) ---
        # No reliable pure-QProcess fallback exists in older PyQt5.
        # Mark that we need the subprocess-based path instead.
        self._qprocess_silent_failed = True
        #print("DEBUG: QProcess silent mode not available — will use subprocess fallback")


    def compile_latex(self, engine=None):
        """Enhanced compile_latex method with proper UI integration"""
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]

        em = self.main_window.editor_manager

        # ── Resolve compile target ────────────────────────────────────────
        # If a master document is set, compile that file regardless of which
        # tab is active.  The master must be open in the editor so unsaved
        # changes are handled correctly via save_file().
        master_file = em.get_master_document() if hasattr(em, 'get_master_document') else None

        if master_file:
            # Make sure the master file is actually open in the editor
            if master_file not in em.editor_files:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self.main_window.window(),
                    tr.get("master_document_not_open", "Master Document Not Open"),
                    tr.get("master_document_not_open_msg",
                           "The master document is not open in the editor:\n{file}\n\n"
                           "Please open it first, or clear the master document setting."
                           ).format(file=master_file)
                )
                return
            current_file   = master_file
            current_editor = em.editor_files[master_file].get('editor')
        else:
            current_editor = em.get_current_editor()
            current_file   = em.get_current_file_path()

        if not current_editor or not current_file:
            self.show_error(tr["no_file_open"], tr["open_a_latex_file"])
            return
            
        if engine is None:
            engine = self.main_window.latex_engine
            
        # STORE THE ENGINE - ADD THIS LINE:
        self.current_engine = engine

        # Check if process is actually running (not just locked)
        if hasattr(self, 'process') and self.process and self.process.state() == QProcess.Running:
            print("WARNING: LaTeX compilation process is actually running - showing user message")
            self.show_error("Compilation in Progress", "Please wait for the current compilation to finish.")
            return
        
        # Reset compilation lock if process is not running
        if hasattr(self, '_compilation_in_progress') and self._compilation_in_progress:
            if not (hasattr(self, 'process') and self.process and self.process.state() == QProcess.Running):
                print("WARNING: LaTeX compilation lock was stuck - resetting it")
                self._compilation_in_progress = False
        
        # Set compilation lock and update UI immediately
        self._compilation_in_progress = True
        
        fw = getattr(self.main_window.editor_manager, 'file_watcher', None)
        if fw:
            fw.set_compilation_active(True)        
        
        # CRITICAL: Update toolbar UI to show "Stop" button
        if hasattr(self.main_window, 'toolbar_manager'):
            self.main_window.toolbar_manager.update_compile_actions(compiling=True)
            self.main_window.toolbar_manager.on_compilation_started()
        
        try:
            if not self.main_window.editor_manager.save_file():
                # Release lock and reset UI on save failure
                self._compilation_in_progress = False
                if hasattr(self.main_window, 'toolbar_manager'):
                    self.main_window.toolbar_manager.update_compile_actions(compiling=False)
                return

            # Save and restore the editor's cursor position so that the
            # processEvents() call below (which can repaint / re-layout the
            # editor) does not cause an unexpected scroll jump.
            _cur_editor = self.main_window.editor_manager.get_current_editor()
            _saved_cursor = _cur_editor.textCursor() if _cur_editor else None
            _saved_scroll = (
                _cur_editor.verticalScrollBar().value() if _cur_editor else 0
            )

            self.main_window.editor_manager.update_editor_display(current_file)
            self.main_window.update_title()
            QApplication.processEvents()

            # Restore cursor/scroll after processEvents
            if _cur_editor and _saved_cursor:
                _cur_editor.setTextCursor(_saved_cursor)
                _cur_editor.verticalScrollBar().setValue(_saved_scroll)

            # Re-resolve compile target: master document takes priority over
            # whatever tab became active during processEvents().
            _master = em.get_master_document() if hasattr(em, 'get_master_document') else None
            current_file = _master if _master else em.current_file
            if current_file and current_file in em.editor_files:
                if em.editor_files[current_file].get('modified', False):
                    if not self.main_window.editor_manager.save_file():
                        # Release lock and reset UI on save failure
                        self._compilation_in_progress = False
                        if hasattr(self.main_window, 'toolbar_manager'):
                            self.main_window.toolbar_manager.update_compile_actions(compiling=False)
                        return
                        
            if not current_file or not os.path.exists(current_file):
                self.show_error("File Error", "Current file does not exist.")
                # Release lock and reset UI on file error
                self._compilation_in_progress = False
                if hasattr(self.main_window, 'toolbar_manager'):
                    self.main_window.toolbar_manager.update_compile_actions(compiling=False)
                return
                
            # Determine expected PDF path
            self._last_compiled_pdf_path = os.path.splitext(current_file)[0] + ".pdf"
            
            self.compilation_output = ""
            self.compilation_errors = ""
            
            if hasattr(self.main_window, 'output_text'):
                self.main_window.output_text.clear()
            if hasattr(self.main_window, 'errors_text'):
                self.main_window.errors_text.clear()
                
            self.update_ui_for_compilation(True)
            self.main_window.update_status_bar(f"Compiling with {engine}...")
            
            self.cleanup_process()
            self.process = QProcess()
            self._configure_process_for_silent_execution(self.process)
            
            
            working_dir = os.path.dirname(current_file)
            tex_filename = os.path.basename(current_file)
            file_basename = os.path.splitext(tex_filename)[0]  # filename without extension
            
            command_template = self.get_latex_command_template(engine)
            
            if engine == "custom":
                # Handle custom commands with placeholders
                if not command_template.strip():
                    self.show_error("Custom Command Error", "Custom compilation command is empty. Please configure it in Settings.")
                    self._compilation_in_progress = False
                    if hasattr(self.main_window, 'toolbar_manager'):
                        self.main_window.toolbar_manager.update_compile_actions(compiling=False)
                    return
                    
                # Replace placeholders in custom command
                custom_command = command_template
                custom_command = custom_command.replace('%f', tex_filename)  # full filename
                custom_command = custom_command.replace('%b', file_basename)  # basename without extension
                custom_command = custom_command.replace('%d', working_dir)    # directory
                
                # For custom commands, we'll use shell execution
                if os.name == 'nt':  # Windows
                    program = 'cmd'
                    arguments = ['/c', custom_command]
                else:  # Unix/Linux/Mac
                    program = 'bash'
                    arguments = ['-c', custom_command]
                pass
            else:
                # Handle standard engines with ENHANCED defaults
                cmd_parts = command_template.split()
                if cmd_parts:
                    # ADD -halt-on-error if not present
                    if '-halt-on-error' not in cmd_parts:
                        # Insert after -interaction=nonstopmode
                        if '-interaction=nonstopmode' in cmd_parts:
                            idx = cmd_parts.index('-interaction=nonstopmode')
                            cmd_parts.insert(idx + 1, '-halt-on-error')
                        else:
                            cmd_parts.insert(1, '-halt-on-error')
                    # Add filename if not already present
                    if tex_filename not in cmd_parts:
                        cmd_parts.append(tex_filename)
                    program = cmd_parts[0]
                    arguments = cmd_parts[1:]
                else:
                    # ENHANCED: Ensure non-interactive mode for fallback
                    program = engine
                    arguments = [
                        "-synctex=1", 
                        "-interaction=nonstopmode",  # Prevent hanging on errors
                        "-halt-on-error",            # Stop immediately on errors  
                        "-shell-escape", 
                        tex_filename
                    ]
            
            self.process.setWorkingDirectory(working_dir)
            
            try:
                self.process.readyReadStandardOutput.connect(self.read_stdout_with_timeout_check)
                self.process.readyReadStandardError.connect(self.read_stderr)
                self.process.finished.connect(self.on_latex_process_finished_with_cleanup)
                self.process.errorOccurred.connect(self._on_process_error)
            except Exception as e:
                print(f"Error connecting process signals: {e}")
                self._compilation_in_progress = False
                if hasattr(self.main_window, 'toolbar_manager'):
                    self.main_window.toolbar_manager.update_compile_actions(compiling=False)
                self.cleanup_process()
                return
                
            # Setup timeout protection
            self.setup_compilation_timeout()
                
            try:
                #print(f"DEBUG: Starting LaTeX compilation - Program: {program}, Arguments: {arguments}")
                self.process.start(program, arguments)
                if not self.process.waitForStarted(self.startup_timeout_ms):
                    self.show_error("Process Error", f"Failed to start {program}")
                    self._compilation_in_progress = False
                    if hasattr(self.main_window, 'toolbar_manager'):
                        self.main_window.toolbar_manager.update_compile_actions(compiling=False)
                    self.cleanup_process_with_timeout()
            except Exception as e:
                print(f"Error starting LaTeX process: {e}")
                self.show_error("Process Error", f"Failed to start compilation: {str(e)}")
                self._compilation_in_progress = False
                if hasattr(self.main_window, 'toolbar_manager'):
                    self.main_window.toolbar_manager.update_compile_actions(compiling=False)
                self.cleanup_process_with_timeout()
        
        except Exception as e:
            # Release compilation lock on any error and reset UI
            self._compilation_in_progress = False
            if hasattr(self.main_window, 'toolbar_manager'):
                self.main_window.toolbar_manager.update_compile_actions(compiling=False)
            raise e

    def on_latex_process_finished_with_cleanup(self, exit_code, exit_status):
        """Enhanced LaTeX process finished handler with proper UI updates and PDF loading"""
        #print(f"LaTeX process finished: exit_code={exit_code}, exit_status={exit_status}")

        # ── Save editor cursor/scroll position before any UI work ──────────
        # focus_appropriate_tab calls processEvents() which can cause Qt to
        # re-layout the editor and scroll it to an arbitrary position.
        # We save state here and restore it at the end of this method.
        _em = getattr(self.main_window, 'editor_manager', None)
        _cur_editor = _em.get_current_editor() if _em else None
        _saved_cursor = _cur_editor.textCursor() if _cur_editor else None
        _saved_scroll = (
            _cur_editor.verticalScrollBar().value() if _cur_editor else 0
        )
        # ───────────────────────────────────────────────────────────────────

        # Clean up timeout timer
        if hasattr(self, 'compilation_timeout_timer'):
            self.compilation_timeout_timer.stop()
        
        # Release compilation lock FIRST
        self._compilation_in_progress = False
        #print("LaTeX compilation lock released - ready for next compilation")
        
        fw = getattr(self.main_window.editor_manager, 'file_watcher', None)
        if fw:
            fw.set_compilation_active(False)        
        
        # CRITICAL: Update toolbar UI to show compile button again
        if hasattr(self.main_window, 'toolbar_manager'):
            self.main_window.toolbar_manager.update_compile_actions(compiling=False)
            self.main_window.toolbar_manager.on_compilation_finished()
        
        # ENHANCED: Check for PDF existence to determine actual success
        pdf_created = False
        if hasattr(self, '_last_compiled_pdf_path') and self._last_compiled_pdf_path:
            pdf_created = os.path.exists(self._last_compiled_pdf_path)
            #print(f"PDF existence check: {self._last_compiled_pdf_path} -> {pdf_created}")
        
        # Call original finished handler with proper arguments
        # But override the result based on PDF creation
        original_result = self.on_process_finished(exit_code, exit_status)
        
        # Override success determination based on PDF existence
        if pdf_created:
            #print("PDF was created - treating compilation as successful despite exit code or warnings")
            # Load PDF in viewer since compilation actually succeeded
            self._auto_load_pdf_after_compilation()
            # Update status to show success
            self.main_window.update_status_bar("Compilation completed successfully - PDF generated")
        else:
            #print("No PDF was created - compilation truly failed")
            # Keep the original error status
            if not hasattr(self.main_window, 'update_status_bar') or "failed" not in self.main_window.statusBar().currentMessage():
                self.main_window.update_status_bar("Compilation failed - no PDF generated")

        # ── Restore editor cursor/scroll position ──────────────────────────
        if _cur_editor and _saved_cursor:
            _cur_editor.setTextCursor(_saved_cursor)
            _cur_editor.verticalScrollBar().setValue(_saved_scroll)
        # ───────────────────────────────────────────────────────────────────

        # Append clickable log link now that all stdout has been collected
        self._append_log_link(self.compilation_output)
        
        # Ensure UI is updated to show compilation is complete
        QTimer.singleShot(100, lambda: self.update_ui_for_compilation(False))

    def _auto_load_pdf_after_compilation(self):
        """Automatically load the compiled PDF in the viewer"""
        try:
            if hasattr(self, '_last_compiled_pdf_path') and self._last_compiled_pdf_path:
                pdf_path = self._last_compiled_pdf_path
                
                # Double-check PDF exists before trying to load it
                if os.path.exists(pdf_path):
                    #print(f"Auto-loading PDF: {pdf_path}")
                    
                    # Get file modification time to ensure it's fresh
                    try:
                        import time
                        mod_time = os.path.getmtime(pdf_path)
                        current_time = time.time()
                        age_seconds = current_time - mod_time
                        
                        if age_seconds < 30:  # PDF is less than 30 seconds old
                            #print(f"PDF is fresh ({age_seconds:.1f}s old) - loading in viewer")
                            QTimer.singleShot(200, lambda: self._load_pdf_safely(pdf_path))
                        else:
                            #print(f"PDF is old ({age_seconds:.1f}s) - may not be from this compilation")
                            # Still load it, but with a note
                            QTimer.singleShot(200, lambda: self._load_pdf_safely(pdf_path))
                    except Exception as e:
                        print(f"Error checking PDF modification time: {e}")
                        # Load anyway
                        QTimer.singleShot(200, lambda: self._load_pdf_safely(pdf_path))
                else:
                    #print(f"PDF file not found: {pdf_path}")
                    # Check for PDF with different name (sometimes LaTeX creates different output names)
                    current_file = self.main_window.editor_manager.current_file
                    if current_file:
                        base_dir = os.path.dirname(current_file)
                        base_name = os.path.splitext(os.path.basename(current_file))[0]
                        
                        # Try common PDF output patterns
                        possible_pdfs = [
                            os.path.join(base_dir, f"{base_name}.pdf"),
                            os.path.join(base_dir, "output.pdf"),
                            os.path.join(base_dir, "document.pdf")
                        ]
                        
                        for pdf_candidate in possible_pdfs:
                            if os.path.exists(pdf_candidate):
                                #print(f"Found alternative PDF: {pdf_candidate}")
                                QTimer.singleShot(200, lambda p=pdf_candidate: self._load_pdf_safely(p))
                                break
            #else:
                #print("No PDF path available for auto-loading")
        except Exception as e:
            print(f"Error in auto PDF loading: {e}")

    def _load_pdf_safely(self, pdf_path):
        """Safely load/reload PDF with error handling.

        Always calls reload_pdf (not load_pdf_in_viewer) so that an existing
        viewer has its *content* refreshed, not just brought to the foreground.
        reload_pdf falls back to load_pdf_in_viewer automatically when no viewer
        exists yet (first compilation).
        """
        try:
            if hasattr(self.main_window, 'pdf_manager'):
                self.main_window.pdf_manager.reload_pdf(pdf_path)
                self.main_window.update_status_bar(f"PDF loaded: {os.path.basename(pdf_path)}")
        except Exception as e:
            print(f"Error loading PDF in viewer: {e}")
            self.main_window.update_status_bar("PDF compilation completed - manual PDF viewing required")

    def stop_compilation(self):
        """Stop LaTeX compilation and update UI properly with complete cleanup"""
        #print("Stopping LaTeX compilation")
        
        # Stop timeout timer immediately
        if hasattr(self, 'compilation_timeout_timer'):
            self.compilation_timeout_timer.stop()
            #print("Stopped compilation timeout timer")
        
        # Handle process termination
        if hasattr(self, 'process') and self.process:
            if self.process.state() == QProcess.Running:
                #print("Terminating LaTeX compilation process")
                
                # Disconnect all signals first to prevent them from firing during cleanup
                try:
                    self.process.readyReadStandardOutput.disconnect()
                    self.process.readyReadStandardError.disconnect() 
                    self.process.finished.disconnect()
                    self.process.errorOccurred.disconnect()
                    #print("Disconnected all process signals")
                except Exception as e:
                    print(f"Error disconnecting signals (expected during cleanup): {e}")
                
                # Terminate the process
                self.process.terminate()
                
                # Wait for graceful termination, then kill if necessary
                if not self.process.waitForFinished(3000):  # 3 second timeout
                    #print("Force killing LaTeX compilation process")
                    self.process.kill()
                    # Wait a bit more for kill to take effect
                    self.process.waitForFinished(1000)
                
                #print(f"Process final state: {self.process.state()}")
            
            # Clean up process object completely
            self.process.deleteLater()
            self.process = None
            #print("Process object cleaned up")
        
        # Force clean up compilation state
        self._compilation_in_progress = False
        #print("Compilation lock released")
        
        fw = getattr(self.main_window.editor_manager, 'file_watcher', None)
        if fw:
            fw.set_compilation_active(False)        
        
        # Clean up any compilation data
        self.compilation_output = ""
        self.compilation_errors = ""
        
        # Update toolbar UI immediately
        if hasattr(self.main_window, 'toolbar_manager'):
            self.main_window.toolbar_manager.update_compile_actions(compiling=False)
            self.main_window.toolbar_manager.on_compilation_finished()
            # Force reset the internal state
            self.main_window.toolbar_manager._compiling = False
            #print("Toolbar UI updated and internal state reset")
        
        # Update other UI elements
        self.update_ui_for_compilation(False)
        
        # Clear status and provide feedback
        self.main_window.update_status_bar("LaTeX compilation stopped by user - ready for new compilation")
        
        # Process any remaining Qt events to ensure UI updates
        QApplication.processEvents()
        
        print("Stop compilation completed - system should be ready for new compilation")

    def is_compilation_ready(self):
        """Enhanced compilation readiness check with forced cleanup if needed"""
        # Check if process is actually running
        process_running = False
        if hasattr(self, 'process') and self.process:
            process_running = (self.process.state() == QProcess.Running)
        
        # Check compilation lock state
        lock_active = (hasattr(self, '_compilation_in_progress') and 
                       self._compilation_in_progress)
        
        # If lock is active but process isn't running, force cleanup
        if lock_active and not process_running:
            #print("DEBUG: Forcing cleanup of stuck compilation state")
            self._compilation_in_progress = False
            
            # Clean up any leftover process
            if hasattr(self, 'process') and self.process:
                try:
                    if self.process.state() != QProcess.NotRunning:
                        self.process.kill()
                    self.process.deleteLater()
                    self.process = None
                    #print("DEBUG: Cleaned up leftover process")
                except Exception as e:
                    print(f"DEBUG: Error cleaning up leftover process: {e}")
            
            # Reset UI
            if hasattr(self.main_window, 'toolbar_manager'):
                self.main_window.toolbar_manager.update_compile_actions(compiling=False)
                self.main_window.toolbar_manager._compiling = False
            
            lock_active = False
        
        ready = not process_running and not lock_active
        #print(f"DEBUG: Compilation ready check - Ready: {ready}, Process running: {process_running}, Lock active: {lock_active}")
        
        return ready

    def setup_compilation_timeout(self):
        """Setup timeout protection for LaTeX compilation"""
        if not hasattr(self, 'compilation_timeout_timer'):
            self.compilation_timeout_timer = QTimer()
            self.compilation_timeout_timer.timeout.connect(self.on_compilation_timeout)
        
        # Set timeout (adjust as needed - 120 seconds for complex documents)
        self.compilation_timeout_ms = 120000  # 2 minutes
        self.compilation_timeout_timer.start(self.compilation_timeout_ms)
        
        # Track last output time to detect hanging
        self.last_output_time = QTimer()
        self.last_output_time.start()

    def on_compilation_timeout(self):
        """Handle compilation timeout"""
        #print("Compilation timeout triggered")
        
        if hasattr(self, 'process') and self.process and self.process.state() == QProcess.Running:
            #print("Killing hung compilation process")
            self.process.kill()
            
            error_msg = "Compilation timed out - process was killed.\n"
            error_msg += "This usually indicates:\n"
            error_msg += "• LaTeX is waiting for user input due to errors\n"
            error_msg += "• Missing files or packages\n"
            error_msg += "• Document has syntax errors\n\n"
            error_msg += "Check your document for errors and ensure all required files exist."
            
            if hasattr(self.main_window, 'errors_text'):
                self.main_window.errors_text.append(f"ERROR: {error_msg}")
            
            self.main_window.update_status_bar("Compilation timed out and was stopped")
            
            # Show user-friendly message
            QMessageBox.warning(
                self.main_window,
                "Compilation Timeout",
                "Compilation was stopped due to timeout.\n\n"
                "This usually happens when LaTeX encounters errors and waits for input.\n"
                "Please check your document for:\n"
                "• Syntax errors\n"
                "• Missing files or images\n"
                "• Missing packages\n\n"
                "Check the Errors tab for details."
            )
        
        self.cleanup_process_with_timeout()

    def read_stdout_with_timeout_check(self):
        """Enhanced stdout reader with hang detection"""
        if not self.process:
            return
        
        if hasattr(self, 'last_output_time'):
            self.last_output_time.start()
        
        text = self.process.readAllStandardOutput().data().decode('utf-8', errors='replace')
        
        if text.strip():
            # Comprehensive list of interactive prompts
            interactive_prompts = [
                "? ",
                "** ",  # Double asterisk - LaTeX waiting
                "(e)dit, (h)elp, (r)un, (q)uit ?",
                "Please type another input file name:",
                "! Emergency stop",
                "Type <return> to proceed",
                "Press any key to continue",
                "*Please type a command or say `\\end':",
                "Enter file name:",
                "* (job aborted, file error in nonstop mode)",
            ]
            
            text_lower = text.lower()
            for prompt in interactive_prompts:
                if prompt.lower() in text_lower:
                    #print(f"⚠️ Interactive prompt detected: '{prompt}'")
                    
                    if self.process and self.process.state() == QProcess.Running:
                        #print("Killing process due to interactive prompt")
                        self.process.kill()
                        
                        error_msg = f"ERROR: Compilation stopped - interactive prompt detected: '{prompt}'\n"
                        error_msg += "LaTeX was waiting for user input. Check your document for errors.\n\n"
                        error_msg += "Common causes:\n"
                        error_msg += "• Missing or incorrect \\begin{document}\n"
                        error_msg += "• Unclosed environments\n"
                        error_msg += "• Missing files or packages\n"
                        error_msg += "• Syntax errors\n"
                        
                        if hasattr(self.main_window, 'errors_text'):
                            self.main_window.errors_text.append(error_msg)
                        
                        self.main_window.update_status_bar(
                            "⚠️ Compilation stopped - interactive prompt detected"
                        )
                        return
            
            # Add to output
            self.compilation_output += text
            if hasattr(self.main_window, 'output_text'):
                self.main_window.output_text.moveCursor(QTextCursor.End)
                self.main_window.output_text.insertPlainText(text)
                self.main_window.output_text.moveCursor(QTextCursor.End)

    def on_process_finished(self, exit_code, exit_status):
        """Enhanced process finished handler with PDF check"""
        if hasattr(self, 'process_timeout'):
            self.process_timeout.stop()
        
        self.compilation_timer.stop()
        self.update_ui_for_compilation(False)
        
        has_errors = self.has_compilation_errors(
            self.compilation_output, 
            self.compilation_errors
        ) or exit_code != 0
        
        if self.compilation_output:
            last_lines = self.compilation_output.split('\n')[-10:]
        
        self.focus_appropriate_tab(has_errors)
        
        pdf_created = False
        if self._last_compiled_pdf_path:
            pdf_created = os.path.exists(self._last_compiled_pdf_path)
            
            if not pdf_created:
                # FIX: Use self.current_engine instead of undefined 'engine'
                if self.current_engine == "custom":
                    working_dir = os.path.dirname(self.main_window.editor_manager.current_file)
                    pdf_files = [f for f in os.listdir(working_dir) if f.endswith('.pdf')]
                    if pdf_files:
                        pdf_files.sort(
                            key=lambda x: os.path.getmtime(os.path.join(working_dir, x)), 
                            reverse=True
                        )
                        found_pdf = os.path.join(working_dir, pdf_files[0])
                        #print(f"DEBUG: Found alternative PDF: {found_pdf}")
                        self._last_compiled_pdf_path = found_pdf
                        pdf_created = True
                
                #print(f"DEBUG: Expected PDF not found: {getattr(self, '_last_compiled_pdf_path', 'None')}")
        
        if pdf_created:
            self.main_window.update_status_bar("Compilation successful")
            # NOTE: PDF reloading is handled by the caller
            # (on_latex_process_finished_with_cleanup → _auto_load_pdf_after_compilation).
            # Do NOT call reload_pdf here — it would trigger a second concurrent reload
            # that can hit the viewer while it is still mid-render from the first call,
            # leading to a crash when the user clicks the viewer.
        else:
            self.main_window.update_status_bar(
                "Compilation completed but no PDF generated - check output"
            )
        
        self.cleanup_process()

    def cleanup_process_with_timeout(self):
        """Enhanced cleanup that includes timeout timer"""
        # Clean up timeout timer
        if hasattr(self, 'compilation_timeout_timer'):
            self.compilation_timeout_timer.stop()
        
        # Clean up process
        self.cleanup_process()
        
        # Update UI
        self.update_ui_for_compilation(False)

                
    def read_stderr(self):
        """Read standard error from compilation process"""
        if self.process:
            try:
                data = self.process.readAllStandardError()
                stderr = bytes(data).decode('utf-8', errors='replace')
                self.compilation_errors += stderr
                if hasattr(self.main_window, 'errors_text'):
                    self.main_window.errors_text.append(stderr)
                
                # If we're getting errors, immediately switch to error tab
                if stderr.strip() and any(indicator in stderr.lower() for indicator in ['error', '!', 'failed']):
                    #print(f"DEBUG: Error detected in stderr, switching to error tab")
                    self.focus_appropriate_tab(True)
            except Exception as e:
                print(f"Error reading stderr: {e}")
                
    def _on_process_error(self, error):
        """Handle process errors"""
        #print(f"DEBUG: Process error occurred: {error}")
        
        self.update_ui_for_compilation(False)
        
        from PyQt5.QtCore import QProcess
        error_messages = {
            QProcess.FailedToStart: "Failed to start compilation process",
            QProcess.Crashed: "Compilation process crashed",
            QProcess.Timedout: "Compilation process timed out",
            QProcess.WriteError: "Write error during compilation",
            QProcess.ReadError: "Read error during compilation",
            QProcess.UnknownError: "Unknown error during compilation"
        }
        
        message = error_messages.get(error, "Unknown compilation error")
        
                
        # For crashes, check if it's likely a compiler issue vs app issue
        if error == QProcess.Crashed:
            # If we have some output, it's probably a compiler issue
            if self.compilation_output or self.compilation_errors:
                #print(f"DEBUG: Compilation crash detected but output present - likely compiler issue")
                # Focus error tab since there might be useful error info
                self.focus_appropriate_tab(True)
                self.main_window.update_status_bar("Compilation terminated - check output for details")
            else:
                # No output suggests app-level issue
                #print(f"DEBUG: Compilation crash with no output - likely app issue")
                self.main_window.update_status_bar(f"Error: {message}")
                self.show_error("Compilation Error", message)
        else:
            self.main_window.update_status_bar(f"Error: {message}")
            if error not in [QProcess.Crashed]:  # Don't show dialog for crashes
                self.show_error("Compilation Error", message)
        
        # Always focus error tab when there's a process error
        self.focus_appropriate_tab(True)
        
        # Cleanup
        self.cleanup_process()

     
    def is_compiling(self):
        """Check if compilation is currently running"""
        return hasattr(self, 'process') and self.process and self.process.state() == QProcess.Running
        
    def validate_custom_command(self, command):
        """Validate a custom compilation command"""
        if not command.strip():
            return False, "Custom command cannot be empty"
        
        # Check for dangerous commands (basic security)
        dangerous_patterns = ['rm -rf', 'del /f', 'format', 'shutdown', 'reboot', 'sudo rm']
        command_lower = command.lower()
        for pattern in dangerous_patterns:
            if pattern in command_lower:
                return False, f"Command contains potentially dangerous operation: {pattern}"
        
        # Check if placeholders are used correctly
        if '%f' not in command and '%b' not in command:
            return False, "Command should contain at least %f (filename) or %b (basename) placeholder"
        
        return True, "Command appears valid"
        
    def get_command_examples(self):
        """Get example custom commands"""
        return [
            "latex %f && dvips %b.dvi && ps2pdf %b.ps",
            "pdflatex %f && bibtex %b && pdflatex %f && pdflatex %f",
            "xelatex %f && makeindex %b.idx && xelatex %f",
            "lualatex -shell-escape %f",
            "platex %f && dvipdfmx %b.dvi"
        ]

    def _extract_error_line(self, output):
        """Extract the first error line number from LaTeX compilation output"""
        import re
        
        # Pattern to match LaTeX error line indicators like "l.414"
        # The pattern looks for "l." followed by digits at the start of a line or after whitespace
        patterns = [
            r'l\.(\d+)',           # Standard LaTeX error: l.414
            r'line\s+(\d+)',       # Alternative: line 414
            r':(\d+):',            # File:line:col format
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, output, re.IGNORECASE)
            if matches:
                try:
                    line_num = int(matches[0])
                    if line_num > 0:
                        return line_num
                except (ValueError, IndexError):
                    continue
        
        return None

    def _jump_to_error_line(self):
        """Jump to the first error line in the editor"""
        try:
            # Combine output and errors for searching
            combined_output = self.compilation_output + "\n" + self.compilation_errors
            
            error_line = self._extract_error_line(combined_output)
            
            if error_line and hasattr(self.main_window, 'editor_manager'):
                success = self.main_window.editor_manager.go_to_line_number(error_line)
                if success:
                    print(f"Jumped to error line: {error_line}")
                    self.main_window.update_status_bar(f"Error at line {error_line}")
                return success
        except Exception as e:
            print(f"Error jumping to error line: {e}")
        
        return False
