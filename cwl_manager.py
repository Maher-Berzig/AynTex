# cwl_manager.py
"""
CWL Manager - Handles LaTeX completion word list files
Enhanced with async loading to prevent UI freezes
"""
import os
import re
import sys
import threading
from pathlib import Path
from typing import Dict, Set, List, Optional, Tuple, Callable
from PyQt5.QtCore import QObject, pyqtSignal, QTimer


class CWLCommand:
    """Represents a parsed CWL command with metadata"""
    __slots__ = ['raw', 'command', 'arguments', 'is_math_only', 
                 'is_text_only', 'is_tabular', 'is_environment', 'tooltip']
    
    def __init__(self, raw_line: str):
        self.raw = raw_line
        self.command = ""
        self.arguments = []
        self.is_math_only = False
        self.is_text_only = False
        self.is_tabular = False
        self.is_environment = False
        self.tooltip = ""
        self._parse(raw_line)
    
    def _parse(self, line: str):
        """Parse a CWL line into command and metadata"""
        if not line or line.startswith('#'):
            return
        
        parts = line.split('#')
        self.command = parts[0].strip()
        
        # Parse flags after #
        if len(parts) > 1:
            flags = parts[1].strip()
            self.is_math_only = 'm' in flags
            self.is_text_only = 't' in flags
            self.is_tabular = 'array' in flags or '\\array' in flags
            self.is_environment = '\\' in flags and ('begin' in self.command.lower() or 'end' in self.command.lower())
        
        # Extract arguments for placeholder display
        self._extract_arguments()
    
    def _extract_arguments(self):
        """Extract argument placeholders from command"""
        arg_patterns = [
            r'\{%<([^%>]+)%>\}',  # {%<arg%>}
            r'\{([^{}]+)\}',       # {arg}
            r'\[([^\[\]]+)\]',     # [arg]
        ]
        for pattern in arg_patterns:
            matches = re.findall(pattern, self.command)
            for match in matches:
                if match and not match.startswith('\\'):
                    self.arguments.append(match)
    
    def get_display_text(self) -> str:
        """Get display text for completion popup"""
        return self.command
    
    def get_insert_text(self) -> str:
        """Get text to insert with placeholders"""
        text = self.command
        text = re.sub(r'\{%<[^%>]+%>\}', '{•}', text)
        return text
    
    def get_tooltip(self) -> str:
        """Get tooltip text"""
        parts = []
        if self.is_math_only:
            parts.append("Math mode only")
        if self.is_text_only:
            parts.append("Text mode only")
        if self.is_tabular:
            parts.append("Tabular/Array")
        if self.arguments:
            parts.append(f"Args: {', '.join(self.arguments)}")
        return " | ".join(parts) if parts else self.command


class CWLManagerSignals(QObject):
    """Signals for CWL Manager async operations"""
    loading_started = pyqtSignal()
    loading_progress = pyqtSignal(int, int)  # current, total
    loading_finished = pyqtSignal(int)  # command count
    file_loaded = pyqtSignal(str, int)  # filename, command count
    error_occurred = pyqtSignal(str)  # error message


class CWLManager:
    """Manages CWL files and provides completion data with async loading"""
    
    def __init__(self, cwl_dir: str = None):
        self.cwl_dir = cwl_dir or self._get_default_cwl_dir()
        self.enabled_files: Set[str] = set()
        self.commands: Dict[str, CWLCommand] = {}
        self._file_commands: Dict[str, Set[str]] = {}
        self._include_cache: Dict[str, Set[str]] = {}
        
        # Async loading support
        self._loading = False
        self._loaded = False
        self._load_thread: Optional[threading.Thread] = None
        self._stop_loading = False
        
        # Thread-safe lock for commands dict
        self._lock = threading.RLock()
        
        # Signals for UI updates (optional - can be None)
        self.signals: Optional[CWLManagerSignals] = None
        
        # Completion enabled state
        self._completion_enabled = True
    
    def init_signals(self):
        """Initialize Qt signals - call from main thread"""
        self.signals = CWLManagerSignals()
        return self.signals
    
    def _get_default_cwl_dir(self) -> str:
        """Get default CWL directory - always beside the main script"""
        if getattr(sys, 'frozen', False):
            app_dir = os.path.dirname(sys.executable)
        else:
            app_dir = os.path.dirname(os.path.abspath(__file__))
        
        cwl_path = os.path.join(app_dir, 'cwl')
        
        if not os.path.exists(cwl_path):
            try:
                os.makedirs(cwl_path)
                #print(f"Created CWL directory: {cwl_path}")
            except Exception as e:
                print(f"Could not create CWL directory: {e}")
        
        return cwl_path
    
    def set_cwl_directory(self, path: str):
        """Set the CWL directory path"""
        self.cwl_dir = path
        self._reload_async()
    
    def set_completion_enabled(self, enabled: bool):
        """Enable or disable completion globally"""
        self._completion_enabled = enabled
    
    def is_completion_enabled(self) -> bool:
        """Check if completion is enabled"""
        return self._completion_enabled
    
    def available_files(self) -> List[str]:
        """Get list of available CWL files"""
        if not os.path.exists(self.cwl_dir):
            return []
        try:
            return sorted(f for f in os.listdir(self.cwl_dir) if f.endswith('.cwl'))
        except Exception as e:
            print(f"Error listing CWL files: {e}")
            return []
    
    def enable_file(self, filename: str, async_load: bool = True):
        """Enable a CWL file for completion"""
        if filename not in self.enabled_files:
            self.enabled_files.add(filename)
            if async_load:
                self._load_file_async(filename)
            else:
                self._load_file(filename)
    
    def disable_file(self, filename: str):
        """Disable a CWL file"""
        if filename in self.enabled_files:
            self.enabled_files.discard(filename)
            self._unload_file(filename)
    
    def is_enabled(self, filename: str) -> bool:
        """Check if a file is enabled"""
        return filename in self.enabled_files
    
    def set_enabled_files(self, filenames: List[str], async_load: bool = True):
        """Set the list of enabled files"""
        self.enabled_files = set(filenames)
        if async_load:
            self._reload_async()
        else:
            self._reload()
    
    def is_loading(self) -> bool:
        """Check if files are currently being loaded"""
        return self._loading
    
    def is_loaded(self) -> bool:
        """Check if initial loading is complete"""
        return self._loaded
    # ═══════════════════════════════════════════════════════════
    # ASYNC LOADING METHODS
    # ═══════════════════════════════════════════════════════════
    
    def load_async(self, callback: Callable[[], None] = None):
        """Load all enabled CWL files asynchronously"""
        if self._loading:
            #print("CWL loading already in progress")
            return
        
        self._loading = True
        self._stop_loading = False
        
        if self.signals:
            self.signals.loading_started.emit()
        
        def load_thread():
            try:
                self._do_load_all()
            except Exception as e:
                print(f"Error in CWL loading thread: {e}")
                if self.signals:
                    # Schedule signal emission on main thread
                    QTimer.singleShot(0, lambda: self.signals.error_occurred.emit(str(e)))
            finally:
                self._loading = False
                self._loaded = True
                
                if self.signals:
                    count = len(self.commands)
                    QTimer.singleShot(0, lambda: self.signals.loading_finished.emit(count))
                
                if callback:
                    QTimer.singleShot(0, callback)
        
        self._load_thread = threading.Thread(target=load_thread, daemon=True)
        self._load_thread.start()
    
    def _reload_async(self):
        """Reload all enabled files asynchronously"""
        # Stop any current loading
        self._stop_loading = True
        if self._load_thread and self._load_thread.is_alive():
            self._load_thread.join(timeout=1.0)
        
        # Clear and reload
        with self._lock:
            self.commands.clear()
            self._file_commands.clear()
        
        self.load_async()
    
    def _load_file_async(self, filename: str):
        """Load a single file asynchronously"""
        def load_single():
            self._load_file(filename)
            if self.signals:
                count = len(self._file_commands.get(filename, set()))
                QTimer.singleShot(0, lambda: self.signals.file_loaded.emit(filename, count))
        
        thread = threading.Thread(target=load_single, daemon=True)
        thread.start()
    
    def _do_load_all(self):
        """Internal method to load all enabled files (runs in thread)"""
        enabled_copy = list(self.enabled_files)
        total = len(enabled_copy)
        
        for i, filename in enumerate(enabled_copy):
            if self._stop_loading:
                #print("CWL loading stopped")
                break
            
            self._load_file(filename)
            
            if self.signals:
                QTimer.singleShot(0, lambda curr=i+1, tot=total: 
                                  self.signals.loading_progress.emit(curr, tot))
            
            # Small yield to prevent blocking
            if i % 5 == 0:
                import time
                time.sleep(0.001)
    
    # ═══════════════════════════════════════════════════════════
    # SYNCHRONOUS LOADING METHODS (for internal use)
    # ═══════════════════════════════════════════════════════════
    
    def _reload(self):
        """Reload all enabled files (synchronous)"""
        with self._lock:
            self.commands.clear()
            self._file_commands.clear()
        
        enabled_copy = list(self.enabled_files)
        for filename in enabled_copy:
            self._load_file(filename)
    
    def _load_file(self, filename: str):
        """Load commands from a CWL file (thread-safe)"""
        path = os.path.join(self.cwl_dir, filename)
        if not os.path.exists(path):
            return
        
        file_commands = set()
        new_commands = {}
        includes_to_load = []
        
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    
                    # Handle #include directives
                    if line.startswith('#include:'):
                        include_file = line.replace('#include:', '').strip()
                        if not include_file.endswith('.cwl'):
                            include_file += '.cwl'
                        include_path = os.path.join(self.cwl_dir, include_file)
                        if include_file not in self.enabled_files and os.path.exists(include_path):
                            includes_to_load.append(include_file)
                        continue
                    
                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse command
                    cmd = CWLCommand(line)
                    if cmd.command and cmd.command.startswith('\\'):
                        new_commands[cmd.command] = cmd
                        file_commands.add(cmd.command)
            
            # Update shared data structures under lock
            with self._lock:
                self._file_commands[filename] = file_commands
                self.commands.update(new_commands)
            
            # Load includes (after releasing lock)
            for include_file in includes_to_load:
                self.enabled_files.add(include_file)
                self._load_file(include_file)
                
        except Exception as e:
            print(f"Error loading CWL file {filename}: {e}")
    
    def _unload_file(self, filename: str):
        """Unload commands from a specific file (thread-safe)"""
        with self._lock:
            if filename in self._file_commands:
                for cmd in self._file_commands[filename]:
                    # Check if command is defined in other files
                    other_files = [f for f in self._file_commands 
                                   if f != filename and cmd in self._file_commands[f]]
                    if not other_files and cmd in self.commands:
                        del self.commands[cmd]
                del self._file_commands[filename]
    
    # ═══════════════════════════════════════════════════════════
    # COMPLETION METHODS
    # ═══════════════════════════════════════════════════════════

    def get_all_commands(self) -> List[str]:
        """Get all command names as strings"""
        with self._lock:
            return sorted(self.commands.keys())

    def get_completions_as_strings(self, prefix: str = "") -> List[str]:
        """Get completion command names as strings (for QCompleter)"""
        if not self._completion_enabled:
            return []
        
        results = []
        prefix_lower = prefix.lower()
        
        with self._lock:
            for cmd_text in self.commands.keys():
                if not prefix:
                    results.append(cmd_text)
                elif cmd_text.lower().startswith(prefix_lower):
                    results.append(cmd_text)
                elif prefix_lower.lstrip('\\') in cmd_text.lower():
                    results.append(cmd_text)
        
        return sorted(results)[:100]

    def get_environment_completions(self, prefix: str = "") -> List[str]:
        """Get environment names for \\begin{} and \\end{} completion"""
        if not self._completion_enabled:
            return []
        
        environments = set()
        prefix_lower = prefix.lower()
        
        # Extract environments from loaded CWL commands
        with self._lock:
            for cmd_text in self.commands.keys():
                # Match \begin{envname} patterns
                match = re.match(r'\\begin\{([^}]+)\}', cmd_text)
                if match:
                    env_name = match.group(1)
                    if not prefix or env_name.lower().startswith(prefix_lower):
                        environments.add(env_name)
        
        # Add common environments (in case not in CWL files)
        common_envs = [
            # Document structure
            'document', 'abstract',
            # Math environments
            'equation', 'equation*', 'align', 'align*', 'aligned',
            'gather', 'gather*', 'multline', 'multline*',
            'split', 'cases', 'dcases',
            'matrix', 'pmatrix', 'bmatrix', 'Bmatrix', 'vmatrix', 'Vmatrix',
            'smallmatrix',
            # Floats
            'figure', 'figure*', 'table', 'table*',
            'subfigure', 'subtable',
            # Tables
            'tabular', 'tabular*', 'tabularx', 'tabulary',
            'array', 'longtable', 'supertabular',
            # Lists
            'itemize', 'enumerate', 'description',
            'compactitem', 'compactenum',
            # Text formatting
            'center', 'flushleft', 'flushright',
            'quote', 'quotation', 'verse',
            'verbatim', 'verbatim*',
            # Theorems (common names)
            'theorem', 'lemma', 'proposition', 'corollary',
            'definition', 'example', 'remark', 'proof',
            # Graphics
            'tikzpicture', 'pgfpicture', 'pspicture',
            'circuitikz',
            # Code
            'lstlisting', 'minted', 'algorithm', 'algorithmic',
            # Other
            'minipage', 'frame', 'block',
            'thebibliography', 'filecontents',
            'appendix', 'appendices',
        ]
        
        for env in common_envs:
            if not prefix or env.lower().startswith(prefix_lower):
                environments.add(env)
        
        return sorted(environments)
    

    def get_completions(self, prefix: str = "", math_mode: bool = False, 
                        text_mode: bool = True) -> List[CWLCommand]:
        """Get completion CWLCommand objects filtered by prefix and mode"""
        if not self._completion_enabled:
            return []
        
        results = []
        prefix_lower = prefix.lower()
        
        with self._lock:
            for cmd_text, cmd in self.commands.items():
                if prefix and not cmd_text.lower().startswith(prefix_lower):
                    continue
                if math_mode and cmd.is_text_only:
                    continue
                if text_mode and cmd.is_math_only:
                    continue
                results.append(cmd)
        
        results.sort(key=lambda c: c.command.lower())
        return results

    def get_command(self, command_name: str) -> Optional[CWLCommand]:
        """Get a specific CWLCommand by name"""
        with self._lock:
            return self.commands.get(command_name)

    def get_fuzzy_completions(self, query: str, limit: int = 50) -> List[Tuple[CWLCommand, int]]:
        """Get fuzzy-matched completions with scores"""
        if not self._completion_enabled:
            return []
        
        if not query:
            with self._lock:
                return [(cmd, 100) for cmd in list(self.commands.values())[:limit]]
        
        results = []
        query_lower = query.lower()
        
        with self._lock:
            for cmd_text, cmd in self.commands.items():
                score = self._fuzzy_score(query_lower, cmd_text.lower())
                if score > 0:
                    results.append((cmd, score))
        
        results.sort(key=lambda x: (-x[1], x[0].command.lower()))
        return results[:limit]

    def _fuzzy_score(self, query: str, text: str) -> int:
        """Calculate fuzzy match score"""
        if query in text:
            if text.startswith(query):
                return 100
            return 80
        
        query_idx = 0
        score = 0
        consecutive = 0
        
        for char in text:
            if query_idx < len(query) and char == query[query_idx]:
                query_idx += 1
                consecutive += 1
                score += consecutive * 10
            else:
                consecutive = 0
        
        if query_idx == len(query):
            return score
        return 0

    def get_command_count(self) -> int:
        """Get total number of loaded commands"""
        with self._lock:
            return len(self.commands)

    def get_enabled_file_count(self) -> int:
        """Get number of enabled files"""
        return len(self.enabled_files)