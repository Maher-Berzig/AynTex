from PyQt5.QtWidgets import QPushButton, QMenu, QAction, QMessageBox, QApplication
from PyQt5.QtCore import QProcess, Qt, QObject, pyqtSignal, QTimer
from PyQt5.QtGui import QIcon, QTextCursor
import os


class BackmatterCompile:
    """Backmatter compilation button using QProcess (no threads)"""
    def __init__(self, main_window):
        self.main_window = main_window
        self.process = None
        self.current_tool = None
        self.all_tools_queue = []
        self.all_output = []


    def get_current_file_path(self):
        try:
            if hasattr(self.main_window, 'editor_manager') and self.main_window.editor_manager:
                current_file = self.main_window.editor_manager.current_file
                if current_file and current_file != "Untitled":
                    return current_file
            return None
        except Exception as e:
            print(f"Error getting current file path: {e}")
            return None
        
    def update_ui_for_backmatter_compilation(self, compiling):
        """Update UI elements during/after compilation"""
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]                                    
        # Update toolbar actions
        if hasattr(self.main_window, 'toolbar_manager'):
            self.main_window.toolbar_manager.update_backmatter_actions(compiling)
        
    def compile_backmatter(self, engine=None):
        """Enhanced backmatter compilation with proper UI integration"""
        current_editor = self.main_window.editor_manager.get_current_editor()
        current_file = self.main_window.editor_manager.get_current_file_path()
        
        if not current_editor or not current_file:
            self.show_error(tr["no_file_open"], tr["open_a_latex_file"])
            return
        
        # Use default engine if none specified
        if engine is None:
            engine = self.main_window.backmatter_engine
        
        # Check if backmatter process is running
        if hasattr(self, 'process') and self.process and self.process.state() == QProcess.Running:
            print("WARNING: Backmatter compilation process is running")
            self.show_error("Compilation in Progress", "Please wait for the current backmatter compilation to finish.")
            return
        
        # CRITICAL: Update toolbar UI to show "Stop" button for backmatter
        if hasattr(self.main_window, 'toolbar_manager'):
            self.main_window.toolbar_manager.update_backmatter_actions(compiling=True)
        
        # Save the file first
        if not self.main_window.editor_manager.save_file():
            # Reset UI on save failure
            if hasattr(self.main_window, 'toolbar_manager'):
                self.main_window.toolbar_manager.update_backmatter_actions(compiling=False)
            return
        
        # Update UI
        self.main_window.editor_manager.update_editor_display(current_file)
        self.main_window.update_title()
        QApplication.processEvents()
        
        # Get the current file path again after saving
        file_path = self.main_window.editor_manager.current_file
        
        # Double-check file exists and is saved
        if file_path and file_path in self.main_window.editor_manager.editor_files:
            if self.main_window.editor_manager.editor_files[file_path].get('modified', False):
                if not self.main_window.editor_manager.save_file():
                    # Reset UI on save failure
                    if hasattr(self.main_window, 'toolbar_manager'):
                        self.main_window.toolbar_manager.update_backmatter_actions(compiling=False)
                    return
        
        if not file_path or not os.path.exists(file_path):
            self.show_error("File Error", "Current file does not exist.")
            # Reset UI on file error
            if hasattr(self.main_window, 'toolbar_manager'):
                self.main_window.toolbar_manager.update_backmatter_actions(compiling=False)
            return
        
        # Store PDF path for later refresh
        self._last_compiled_pdf_path = os.path.splitext(file_path)[0] + ".pdf"
        
        # Clear output/error tabs
        if hasattr(self.main_window, 'output_text'):
            self.main_window.output_text.clear()
        if hasattr(self.main_window, 'errors_text'):
            self.main_window.errors_text.clear()
        
        # Save current file if needed
        if hasattr(self.main_window.editor_manager, 'save_current_file'):
            self.main_window.editor_manager.save_current_file()
        
        # Update UI for compilation start
        self.update_ui_for_backmatter_compilation(True)
        self.main_window.update_status_bar(f"Backmatter compiling with {engine}...")
        
        # Handle "all" engine or single engine
        if engine == "all":
            self.all_tools_queue = ["bibtex", "makeindex", "makeglossaries"]
            self.current_tool_index = 0
            self.all_output = []
            self._run_next_tool(file_path)
        else:
            self._compile_single_tool(file_path, engine)

    # def _on_backmatter_process_finished(self):
        # """Enhanced backmatter process finished handler with UI updates and PDF loading"""
        # if not self.process:
            # return
            
        # exit_code = self.process.exitCode()
        # self.process = None
        
        # print(f"Backmatter process finished with exit code: {exit_code}")
        
        # # CRITICAL: Update toolbar UI to show compile button again
        # if hasattr(self.main_window, 'toolbar_manager'):
            # self.main_window.toolbar_manager.update_backmatter_actions(compiling=False)
        
        # msg = f"{self.current_tool.title()} finished with code {exit_code}\n"
        # if hasattr(self.main_window, 'output_text'):
            # self.main_window.output_text.moveCursor(QTextCursor.End)
            # self.main_window.output_text.insertPlainText(msg)
            # self.main_window.output_text.moveCursor(QTextCursor.End)
        
        # if exit_code == 0:
            # self.main_window.update_status_bar(f"{self.current_tool} completed successfully!")
            # # Load PDF after successful backmatter compilation
            # if not hasattr(self, 'all_tools_queue') or self.current_tool == "makeglossaries":
                # QTimer.singleShot(300, self._auto_refresh_and_load_pdf)
        # else:
            # self.main_window.update_status_bar(f"{self.current_tool} failed!")
        
        # if hasattr(self, 'all_tools_queue') and self.all_tools_queue:
            # self.current_tool_index += 1
            # if self.current_tool_index < len(self.all_tools_queue):
                # current_file = self.get_current_file_path()
                # if current_file:
                    # # Keep UI in "compiling" state for next tool
                    # self._run_next_tool(current_file)
                # else:
                    # self._on_all_tools_completed()
                    # self.update_ui_for_backmatter_compilation(False)
            # else:
                # self._on_all_tools_completed()
                # self.update_ui_for_backmatter_compilation(False)
        # else:
            # self.update_ui_for_backmatter_compilation(False)

    def _auto_refresh_and_load_pdf(self):
        """Refresh and load PDF after backmatter compilation"""
        try:
            current_file = self.main_window.editor_manager.current_file
            if current_file:
                pdf_path = os.path.splitext(current_file)[0] + ".pdf"
                
                if os.path.exists(pdf_path):
                    #print(f"Auto-loading PDF after backmatter compilation: {pdf_path}")
                    pass
                    
                    # Load PDF in viewer with delay to ensure file is fully written
                    QTimer.singleShot(200, lambda: self._load_pdf_safely_backmatter(pdf_path))
                else:
                    #print(f"PDF file not found after backmatter compilation: {pdf_path}")
                    pass
        except Exception as e:
            print(f"Error in backmatter PDF auto-loading: {e}")

    def _load_pdf_safely_backmatter(self, pdf_path):
        """Safely load PDF after backmatter compilation with error handling"""
        try:
            if hasattr(self.main_window, 'pdf_manager'):
                print(f"Loading PDF after backmatter compilation: {pdf_path}")
                self.main_window.pdf_manager.load_pdf_in_viewer(pdf_path)
                self.main_window.update_status_bar(f"Backmatter completed - PDF updated: {os.path.basename(pdf_path)}")
            else:
                print("PDF manager not available for backmatter")
        except Exception as e:
            print(f"Error loading PDF after backmatter compilation: {e}")
            self.main_window.update_status_bar("Backmatter compilation completed")

    def _on_all_tools_completed(self):
        """Enhanced all tools completion with PDF loading"""        
        #print("All backmatter tools completed")
        
        # Show completion message
        QMessageBox.information(
            self.main_window, 
            "Compilation Complete", 
            "All backmatter tools completed successfully!"
        )
        
        # Add output summary if available
        if hasattr(self.main_window, 'output_manager') and hasattr(self, 'all_output') and self.all_output:
            self.main_window.output_manager.add_output("\n".join(self.all_output))
        
        # Load PDF after all tools complete
        current_file = self.main_window.editor_manager.current_file
        if current_file:
            pdf_path = os.path.splitext(current_file)[0] + ".pdf"
            if os.path.exists(pdf_path):
                #print(f"Loading PDF after all backmatter tools completed: {pdf_path}")
                QTimer.singleShot(300, lambda: self._load_pdf_safely_backmatter(pdf_path))

    def _cancel_process(self):
        """Cancel backmatter process with proper UI updates"""
        #print("Cancelling backmatter compilation")
        
        if self.process and self.process.state() != QProcess.NotRunning:
            self.process.terminate()            
            if not self.process.waitForFinished(3000):
                self.process.kill()
            self.process = None
        
        # CRITICAL: Reset toolbar UI
        if hasattr(self.main_window, 'toolbar_manager'):
            self.main_window.toolbar_manager.update_backmatter_actions(compiling=False)
        
        self.update_ui_for_backmatter_compilation(False)
        self.main_window.update_status_bar("Backmatter compilation stopped")

    # # Enhanced toolbar handle methods that work with the compilation states
    # def enhanced_handle_compile_action(self):
        # """Enhanced handle compile action that works with the new compilation manager"""
        # lang = self.main_window.menu_language
        # tr = self.main_window.translations[lang]                                    
        # current_editor = self.main_window.editor_manager.get_current_editor()
        # current_file = self.main_window.editor_manager.get_current_file_path()
        # if not current_editor or not current_file:
            # QMessageBox.warning(self.main_window, tr["no_file_open"], tr["open_a_latex_file"])
            # return
            
        # try:
            # if self._compiling:
                # # Currently compiling, so stop
                # print("User clicked Stop - stopping LaTeX compilation")
                # if hasattr(self.main_window, 'compilation_manager'):
                    # self.main_window.compilation_manager.stop_compilation()
                # # UI will be updated by the compilation manager
            # else:
                # # Not compiling, so start
                # print("User clicked Compile - starting LaTeX compilation")
                # if hasattr(self.main_window, 'compilation_manager'):
                    # self.main_window.compilation_manager.compile_latex()
                # # UI will be updated by the compilation manager
        # except Exception as e:
            # print(f"Error in enhanced_handle_compile_action: {e}")
            # import traceback
            # traceback.print_exc()
            # # Reset state on error
            # self._compiling = False
            # self.update_compile_actions(compiling=False)
        

    def _compile_single_tool(self, file_path, tool):
        self.current_tool = tool
        self._start_process(file_path, tool)

    def _start_process(self, file_path, tool):
        """Enhanced process starter with custom command support"""
        self.current_tool = tool
        
        self.process = QProcess(self.main_window)
        self.process.setWorkingDirectory(os.path.dirname(file_path))
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._on_ready_read)
        self.process.finished.connect(self._on_process_finished)
        self.process.errorOccurred.connect(self._on_process_error)
        
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        file_name = os.path.basename(file_path)
        dir_path = os.path.dirname(file_path)
        
        # Get the command for the current tool
        command_attr = f'backmatter_{tool}_option'
        custom_command = getattr(self.main_window, command_attr, None)
        
        if custom_command:
            # Use custom command with placeholder replacement
            command_str = custom_command
            command_str = command_str.replace('%f', file_name)
            command_str = command_str.replace('%b', base_name)
            command_str = command_str.replace('%d', dir_path)
            
            # Handle command chains (commands separated by &&)
            if ' && ' in command_str:
                # For complex command chains, use shell execution
                import subprocess
                try:
                    self.process = subprocess.Popen(
                        command_str,
                        shell=True,
                        cwd=os.path.dirname(file_path),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        universal_newlines=True,
                        bufsize=1
                    )
                    self._monitor_subprocess()
                    return
                except Exception as e:
                    QMessageBox.critical(self.main_window, "Error", f"Failed to start command: {str(e)}")
                    return
            else:
                # Simple command, split and use QProcess
                cmd_parts = command_str.split()
                if cmd_parts:
                    cmd = cmd_parts[0]
                    args = cmd_parts[1:] if len(cmd_parts) > 1 else []
                else:
                    QMessageBox.critical(self.main_window, "Error", f"Invalid command: {command_str}")
                    return
        else:
            # Use default commands
            if tool == "bibtex":
                cmd, args = "bibtex", [base_name]
            elif tool == "biber":
                cmd, args = "biber", [base_name]
            elif tool == "makeindex":
                cmd, args = "makeindex", [f"{base_name}.idx"]
            elif tool == "xindy":
                cmd, args = "xindy", ["-M", "texindy", "-L", "english", f"{base_name}.idx"]
            elif tool == "makeglossaries":
                cmd, args = "makeglossaries", [base_name]
            else:
                QMessageBox.critical(self.main_window, "Error", f"Unknown tool: {tool}")
                return
        
        self.process.start(cmd, args)
        if not self.process.waitForStarted():
            self._on_process_error(QProcess.FailedToStart)

    def _monitor_subprocess(self):
        """Monitor subprocess for complex command chains"""
        if hasattr(self.process, 'poll'):
            # This is a subprocess.Popen object
            def check_process():
                if self.process.poll() is None:
                    # Process is still running, read output
                    try:
                        output = self.process.stdout.readline()
                        if output:
                            if hasattr(self.main_window, 'output_text'):
                                self.main_window.output_text.moveCursor(QTextCursor.End)
                                self.main_window.output_text.insertPlainText(output)
                                self.main_window.output_text.moveCursor(QTextCursor.End)
                        QTimer.singleShot(100, check_process)  # Check again in 100ms
                    except:
                        pass
                else:
                    # Process finished
                    exit_code = self.process.returncode
                    self._handle_subprocess_completion(exit_code)
            
            check_process()

    def _handle_subprocess_completion(self, exit_code):
        """Handle completion of subprocess command chains"""
        msg = f"{self.current_tool.title()} finished with code {exit_code}\n"
        if hasattr(self.main_window, 'output_text'):
            self.main_window.output_text.moveCursor(QTextCursor.End)
            self.main_window.output_text.insertPlainText(msg)
            self.main_window.output_text.moveCursor(QTextCursor.End)
        
        if exit_code == 0:
            self.main_window.update_status_bar(f"{self.current_tool} completed successfully!")
            QTimer.singleShot(300, self._auto_refresh_pdf)
        else:
            self.main_window.update_status_bar(f"{self.current_tool} failed!")
        
        # Continue with queue processing if applicable
        if hasattr(self, 'all_tools_queue') and self.all_tools_queue:
            self.current_tool_index += 1
            if self.current_tool_index < len(self.all_tools_queue):
                current_file = self.get_current_file_path()
                if current_file:
                    self._run_next_tool(current_file)
                else:
                    self._on_all_tools_completed()
                    self.update_ui_for_backmatter_compilation(False)
            else:
                self._on_all_tools_completed()
                self.update_ui_for_backmatter_compilation(False)
        else:
            self.update_ui_for_backmatter_compilation(False)


    # def _cancel_process(self):
        # if self.process and self.process.state() != QProcess.NotRunning:
            # self.process.terminate()            
            # if not self.process.waitForFinished(3000):
                # self.process.kill()
            # self.process = None
            
        # # ✅ FIX: Update UI state when canceling
        # self.update_ui_for_backmatter_compilation(False)
        
        # # Update status
        # self.main_window.update_status_bar("Backmatter compilation stopped")

    def _run_next_tool(self, file_path):
        if self.current_tool_index >= len(self.all_tools_queue):
            self._on_all_tools_completed()
            return

        tool = self.all_tools_queue[self.current_tool_index]
        self.current_tool = tool        
        self._start_process(file_path, tool)

    def _on_all_tools_completed(self):        
        QMessageBox.information(
            self.main_window, 
            "Compilation Complete", 
            "All backmatter tools completed successfully!"
        )
        if hasattr(self.main_window, 'output_manager') and self.all_output:
            self.main_window.output_manager.add_output("\n".join(self.all_output))
        
    # def _show_success_message(self, tool):
        # QMessageBox.information(self.main_window, "Success", f"{tool.title()} compilation succeeded!")
        
    def _on_ready_read(self):
        """Append output to Output tab"""
        if self.process:
            text = self.process.readAllStandardOutput().data().decode('utf-8', errors='replace')
            if text.strip():
                # Append to Output tab
                if hasattr(self.main_window, 'output_text'):
                    self.main_window.output_text.moveCursor(QTextCursor.End)
                    self.main_window.output_text.insertPlainText(text)
                    self.main_window.output_text.moveCursor(QTextCursor.End)
                    
    def _on_process_error(self, error):
        """Append error to Errors tab"""
        if hasattr(self.main_window, 'errors_text'):
            if error == QProcess.FailedToStart:
                error_msg = f"{self.current_tool} failed to start. Is it installed?"
            else:
                error_msg = f"{self.current_tool} crashed or failed."
            self.main_window.errors_text.moveCursor(QTextCursor.End)
            self.main_window.errors_text.insertPlainText(f"ERROR: {error_msg}\n")
            self.main_window.errors_text.moveCursor(QTextCursor.End)
            
    def _on_process_finished(self):
        """Handle process end"""
        if not self.process:
            return
            
        exit_code = self.process.exitCode()
        self.process = None
        
        # Always show completion in Output
        msg = f"{self.current_tool.title()} finished with code {exit_code}\n"
        if hasattr(self.main_window, 'output_text'):
            self.main_window.output_text.moveCursor(QTextCursor.End)
            self.main_window.output_text.insertPlainText(msg)
            self.main_window.output_text.moveCursor(QTextCursor.End)
        
        # Show success/failure in status bar
        if exit_code == 0:
            self.main_window.update_status_bar(f"{self.current_tool} completed successfully!")
            # If this was the last tool in "All", refresh PDF
            if not hasattr(self, 'all_tools_queue') or self.current_tool == "makeglossaries":
                QTimer.singleShot(300, self._auto_refresh_pdf)
        else:
            self.main_window.update_status_bar(f"{self.current_tool} failed!")
        
        # Handle "All" mode
        if hasattr(self, 'all_tools_queue') and self.all_tools_queue:
            self.current_tool_index += 1
            if self.current_tool_index < len(self.all_tools_queue):
                # Get current file path for next tool
                current_file = self.get_current_file_path()
                if current_file:
                    self._run_next_tool(current_file)
                else:
                    # If we can't get file path, finish compilation
                    self._on_all_tools_completed()
                    self.update_ui_for_backmatter_compilation(False)
            else:
                # All tools completed
                self._on_all_tools_completed()
                # ✅ CRITICAL FIX: Always reset UI when all tools complete
                self.update_ui_for_backmatter_compilation(False)
        else:
            # ✅ CRITICAL FIX: Single tool completed - always reset UI
            self.update_ui_for_backmatter_compilation(False)

        
    def _auto_refresh_pdf(self):
        """Refresh PDF after backmatter compilation"""
        current_file = self.main_window.editor_manager.current_file
        if current_file:
            pdf_path = os.path.splitext(current_file)[0] + ".pdf"
            if os.path.exists(pdf_path):
                self.main_window.pdf_manager.reload_pdf(pdf_path)
                
    def show_error(self, title, message):
        """Show error message dialog"""
        QMessageBox.critical(self.main_window, title, message)
         
                
