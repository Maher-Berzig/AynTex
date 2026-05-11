# config_manager.py
"""
Configuration Manager - Enhanced with Arabic Commands and Auto-Save Features
"""
import configparser
import os
import sys
from pathlib import Path
import json
from collections import OrderedDict
from settings_manager import SettingsDialog as sd
from completion_settings_widget import CompletionSettingsWidget
from cwl_manager import CWLManager
import app_info

class ConfigManager:    
    def __init__(self, main_window):
        self.main_window = main_window
        self.app_name = app_info.APP_NAME
        self.config_filename = app_info.APP_CONFIG_FILE

        # Get the appropriate config directory for the current OS
        self.config_dir = self._get_config_directory()
        self.config_file = os.path.join(self.config_dir, self.config_filename)
        
        # Ensure the config directory exists
        self._ensure_config_directory()
        
        # Initialize ConfigParser
        self.config = configparser.ConfigParser(interpolation=None)       

        # Some limits
        self.recent_files_limit = 100
        self.recent_pdf_files_limit = 100
        self.arabic_commands_limit = 20
        self.config = configparser.ConfigParser(interpolation=None)
        # Default command options
        self.default_options = {
            'pdflatex_option': 'pdflatex -synctex=1 -interaction=nonstopmode -shell-escape',
            'xelatex_option': 'xelatex -synctex=1 -interaction=nonstopmode -shell-escape', 
            'lualatex_option': 'lualatex -synctex=1 -interaction=nonstopmode -shell-escape',
            'bibtex_option': 'bibtex',
            'makeindex_option': 'makeindex',
            'makeglossaries_option': 'makeglossaries'
        }

        # Canonical engine keys — never translated, always ASCII
        self.VALID_LATEX_ENGINES      = {'pdflatex', 'xelatex', 'lualatex', 'custom'}
        self.VALID_BACKMATTER_ENGINES = {'bibtex', 'biber', 'makeindex', 'xindy',
                                     'makeglossaries', 'custom'}
        # ── Theme-aware colour palettes (mirrors SettingsDialog) ──────────────
        self.LIGHT_COLORS = {
            'command':         '#ff00008b',
            'environment':     '#ff8b008b',
            'inline_math':     '#ff006400',
            'display_math':    '#ff008000',
            'brace':           '#ff8b0000',
            'paren':           '#ff0000b4',
            'parameter':       '#ffff8c00',
            'optional':        '#ffb8860b',
            'comment':         '#ff808080',
            'special':         '#ff800080',
            'reference':       '#ff191970',
            'inline_math_bg':  '#00000000',
            'display_math_bg': '#00000000',
        }

        self.DARK_COLORS = {
            'command':         '#ffadd8ff',   # light blue
            'environment':     '#ffdda0dd',   # plum
            'inline_math':     '#ff90ee90',   # light green
            'display_math':    '#ff00ff00',   # lime
            'brace':           '#ffffc1cb',   # light pink  (was ffb6c1, adjusted for HexArgb)
            'paren':           '#ff46c8c8',   # teal
            'parameter':       '#ffffa500',   # orange
            'optional':        '#ffdaa520',   # goldenrod
            'comment':         '#ffa9a9a9',   # dark grey
            'special':         '#ffda70d6',   # orchid
            'reference':       '#ff87cefa',   # light sky blue
            'inline_math_bg':  '#00000000',
            'display_math_bg': '#00000000',
        }


        self.load_config()

        # Ensure all required sections exist        
        required_sections = ['compiler', 'layout', 'window', 'ui', 'encoding', 'favorites', 'session_files', 'recent_pdf_files', 'bookmarks', 'recent_files']
        for section in required_sections:
            if not self.config.has_section(section):
                self.config.add_section(section)
                
        # Initialize default colors if not present
        self._initialize_default_colors()
        


    def _safe_latex_engine(self, value, default='pdflatex'):
        """Return value if it is a known engine key, otherwise return default."""
        return value if value in self.VALID_LATEX_ENGINES else default

    def _safe_backmatter_engine(self, value, default='bibtex'):
        """Return value if it is a known engine key, otherwise return default."""
        return value if value in self.VALID_BACKMATTER_ENGINES else default        
        
########
    # Add these methods to your ConfigManager class

    def _initialize_cwl_settings(self):
        """Initialize CWL completion settings section"""
        if not self.config.has_section('cwl_completion'):
            self.config.add_section('cwl_completion')
        
        defaults = {
            'enabled': 'True',
            'enabled_files': 'amsmath.cwl,amssymb.cwl,latex-document.cwl',
            'fuzzy_matching': 'True',
            'min_prefix_length': '2',
            'auto_enable_includes': 'True',
            'show_mode_indicators': 'True'
        }
        
        for key, value in defaults.items():
            if not self.config.has_option('cwl_completion', key):
                self.config.set('cwl_completion', key, value)
            

    def get_cwl_directory(self) -> str:
        """Get the CWL files directory"""
        return self.get_config_value('cwl_completion', 'cwl_directory', '')

    def set_cwl_directory(self, path: str):
        """Set the CWL files directory"""
        self.set_config_value('cwl_completion', 'cwl_directory', path)
        self.save_config()

    def get_enabled_cwl_files(self) -> list:
        """Get list of enabled CWL files"""
        files_str = self.get_config_value('cwl_completion', 'enabled_files', '')
        if not files_str:
            return []
        return [f.strip() for f in files_str.split(',') if f.strip()]


    def save_cwl_settings(self, cwl_manager):
        """Save all CWL settings from manager"""
        if not self.config.has_section('cwl_completion'):
            self.config.add_section('cwl_completion')
        
        self.config.set('cwl_completion', 'cwl_directory', cwl_manager.cwl_dir)
        self.config.set('cwl_completion', 'enabled_files', ','.join(cwl_manager.enabled_files))
        self.save_config()

    def load_cwl_settings(self, cwl_manager):
        """Load CWL settings into manager"""
        cwl_dir = self.get_cwl_directory()
        if cwl_dir:
            cwl_manager.set_cwl_directory(cwl_dir)
        
        enabled_files = self.get_enabled_cwl_files()
        if enabled_files:
            cwl_manager.set_enabled_files(enabled_files)
########
    def _is_dark_theme(self):
            """Return True when the currently configured theme is dark."""
            theme = self.config.get('ui', 'app_theme', fallback='default') \
                    if self.config.has_section('ui') else 'default'
            # Also check live attribute in case it was set after load
            theme = getattr(self.main_window, 'app_theme', theme)
            return theme in ('dark', 'midnight')

    @property
    def default_colors(self):
        """Return the colour palette that matches the active theme."""
        return self.DARK_COLORS if self._is_dark_theme() else self.LIGHT_COLORS

    def _initialize_default_colors(self):
        """Initialize default color settings if they don't exist"""
        if not self.config.has_section('colors'):
            self.config.add_section('colors')
        
        # Set defaults only if not already set
        for key, value in self.default_colors.items():
            if not self.config.has_option('colors', key):
                self.config.set('colors', key, value)

    def set_color(self, key, color_value):
        """Set a color in config"""
        if not self.config.has_section('colors'):
            self.config.add_section('colors')
        self.config.set('colors', key, color_value)

    def get_all_colors(self):
        """Get all color settings as a dictionary"""
        colors = {}
        if self.config.has_section('colors'):
            for key in self.config.options('colors'):
                colors[key] = self.config.get('colors', key)
        
        # Fill in any missing colors with defaults
        for key, default_value in self.default_colors.items():
            if key not in colors:
                colors[key] = default_value
        
        return colors

    def reset_colors_to_default(self):
        """Reset all colors to default values"""
        if not self.config.has_section('colors'):
            self.config.add_section('colors')
        
        for key, value in self.default_colors.items():
            self.config.set('colors', key, value)
        
        self.save_config()
                
    def _get_config_directory(self):
        """Get the appropriate configuration directory for the current OS"""
        system = sys.platform.lower()
        
        if system.startswith('win'):
            # Windows: %APPDATA%\Ayntex
            appdata = os.environ.get('APPDATA')
            if appdata:
                return os.path.join(appdata, self.app_name)
            else:
                # Fallback if APPDATA is not available
                return os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', self.app_name)
        
        elif system.startswith('darwin'):
            # macOS: ~/Library/Application Support/Ayntex
            return os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', self.app_name)
        
        else:
            # Linux and other Unix-like systems: ~/.config/Ayntex
            # Follow XDG Base Directory Specification
            xdg_config_home = os.environ.get('XDG_CONFIG_HOME')
            if xdg_config_home:
                return os.path.join(xdg_config_home, self.app_name)
            else:
                return os.path.join(os.path.expanduser('~'), '.config', self.app_name)
    
    def _ensure_config_directory(self):
        """Create the config directory if it doesn't exist"""
        try:
            Path(self.config_dir).mkdir(parents=True, exist_ok=True)
            #print(f"Config directory: {self.config_dir}")
        except Exception as e:
            print(f"Error creating config directory {self.config_dir}: {e}")
            # Fallback to current directory
            self.config_dir = os.getcwd()
            self.config_file = os.path.join(self.config_dir, self.config_filename)
            print(f"Fallback to current directory: {self.config_dir}")
                
                    
    def load_config(self):
        """Load configuration from INI file"""
        try:
            if os.path.exists(self.config_file):
                self.config.read(self.config_file, encoding='utf-8')
                #print(f"Config loaded from {self.config_file}")
            else:
                #print("No config file found, creating default config")
                self.config = self.get_default_config()
                self.save_config()  # Save default config
            
            # Ensure all required sections exist
            self.ensure_required_sections()
            self.apply_config_to_window()
            
        except Exception as e:
            print(f"Error loading config: {e}")
            self.config = self.get_default_config()
            self.ensure_required_sections()
            self.apply_config_to_window()

###            
    def ensure_required_sections(self):
        """Ensure all required config sections exist"""
        # Add missing sections
        required_sections = ['compiler', 'layout', 'window', 'ui', 'encoding', 'favorites', 'session_files', 'recent_pdf_files', 'bookmarks', 'recent_files',  'cwl_completion' ]
        for section in required_sections:
            if not self.config.has_section(section):
                self.config.add_section(section)
        # Ensure compiler section has all required options
        compiler_defaults = {
        'latex_engine': 'pdflatex',
        'backmatter_engine': 'bibtex',
        'output_encoding': 'utf-8',
        'pdflatex_option': self.default_options['pdflatex_option'],
        'xelatex_option': self.default_options['xelatex_option'],
        'lualatex_option': self.default_options['lualatex_option'],
        'bibtex_option': self.default_options['bibtex_option'],
        'makeindex_option': self.default_options['makeindex_option'],
        'makeglossaries_option': self.default_options['makeglossaries_option']
        }
        
        for key, default_value in compiler_defaults.items():
            if not self.config.has_option('compiler', key):
                self.config.set('compiler', key, default_value)

        if not self.config.has_section('ui'):
            self.config.add_section('ui')
            self.config.set('ui', 'auto_load_last_file', 'True')
            self.config.set('ui', 'last_open_file_count', '0')
            self.config.set('ui', 'last_active_file', '')
            self.config.set('ui', 'menu_language', 'en')
            self.config.set('ui', 'is_rtl', 'False')  # Default to LTR
            self.config.set('ui', '_line_numbers_visible', 'True') 
            self.config.set('ui', '_fold_markers_visible', 'True') 
            
        # ADD: Initialize CWL settings
        self._initialize_cwl_settings()     


        # ── Heal any translated engine names written by older versions ──
        if self.config.has_section('compiler'):
            raw_latex = self.config.get('compiler', 'latex_engine', fallback='pdflatex')
            if raw_latex not in self.VALID_LATEX_ENGINES:
                self.config.set('compiler', 'latex_engine', 'pdflatex')

            raw_bm = self.config.get('compiler', 'backmatter_engine', fallback='bibtex')
            if raw_bm not in self.VALID_BACKMATTER_ENGINES:
                self.config.set('compiler', 'backmatter_engine', 'bibtex')

            # Remove any stray translated-name_option keys
            for key in list(self.config.options('compiler')):
                if key.endswith('_option') and key not in self.default_options:
                    self.config.remove_option('compiler', key)
        
    
    def get_default_config(self):
        """Create default configuration"""
        # Add default side panel commands if not present
        if not self.config.has_section('ui'):
            self.config.add_section('ui')
        
        if not self.config.has_option('ui', 'side_panel_commands'):
            default_commands = [
                {"label": "α",        "latex": r"\alpha"},
                {"label": "β",        "latex": r"\beta"},
                {"label": "a/b",      "latex": r"\frac{cursor}{#}"},
                {"label": "a^b",      "latex": r"^{cursor}"},
                {"label": "a_b",      "latex": r"_{cursor}"},
                {"label": "√",        "latex": r"\sqrt{cursor}"},
                {"label": "∑",        "latex": r"\sum_{cursor}^{#}"},
                {"label": "∫",        "latex": r"\int_{cursor}^{#}"},
                {"label": "→",        "latex": r"\to"},
                {"label": "∞",        "latex": r"\infty"},
                {"label": "≠",        "latex": r"\neq"},
                {"label": "≤",        "latex": r"\leq"},
                {"label": "π",        "latex": r"\pi"},
                {"label": "section",  "latex": r"\section{cursor}"},
                {"label": "eqref",    "latex": r"\eqref{cursor}"},
                {"label": "cite",     "latex": r"\cite{cursor}"},
                {"label": "item",     "latex": r"\item cursor"}
            ]
            self.set_config_value('ui', 'side_panel_commands', json.dumps(default_commands))
        
        # Set default side panel position
        if not self.config.has_option('ui', 'side_panel_on_left'):
            self.set_config_value('ui', 'side_panel_on_left', 'True')

        """Create default ConfigParser with all sections and keys"""
        config = configparser.ConfigParser(interpolation=None)

        config['compiler'] = {
            'latex_engine': 'pdflatex',
            'backmatter_engine': 'bibtex',
            'output_encoding': 'utf-8',
            'pdflatex_option': self.default_options['pdflatex_option'],
            'xelatex_option': self.default_options['xelatex_option'],
            'lualatex_option': self.default_options['lualatex_option'],
            'bibtex_option': self.default_options['bibtex_option'],
            'makeindex_option': self.default_options['makeindex_option'],
            'makeglossaries_option': self.default_options['makeglossaries_option']
        }
        
        # ADD this section:
        config['cwl_completion'] = {
            'cwl_directory': '',
            'enabled_files': 'amsmath.cwl,amssymb.cwl,latex-document.cwl',
            'fuzzy_matching': 'True',
            'min_prefix_length': '2',
            'auto_enable_includes': 'True',
            'show_mode_indicators': 'True'
        }


        config['layout'] = {
            'switch_mode': 'editor_left',
            'editor_layout_mode': 'tabbed',
            'pdf_layout_mode': 'tabbed',            
            'output_tabs_visible': 'True',
            'symbols_tab_visible': 'False',
            'commands_tab_visible': 'False',
            'tree_tab_visible': 'False',
            'bookmarks_tab_visible': 'False',
            'terminal_tab_visible': 'False',
            'main_splitter_sizes': '',
            'editor_vertical_splitter_sizes': '',
            'pdf_zoom_factor': '1.0'
        }

        config['window'] = {
            'x': '100',
            'y': '100',
            'width': '1280',
            'height': '720',
            'maximized': 'True',
            'splitter_sizes': '600,150'
        }

        config['ui'] = {
            'menu_language': 'en',
            'is_rtl': 'False',
            'is_line_numbers_visible': 'True',
            'is_fold_markers_visible': 'True',
            'editor_font_size': '11',
            'toolbar_font_size': '9',
            'auto_load_last_file': 'True',
            'editor_font_family': 'Consolas',
            'ui_font_family': 'Calibri',
            'side_panel_visible': 'True',
            'app_theme': 'default',          
            'side_panel_commands': '[{"label": "Bold", "latex": "\\textbf{cursor}"}, {"label": "Italic", "latex": "\\textit{cursor}"}, {"label": "Math", "latex": "$cursor$"}, {"label": "Equation", "latex": "\\begin{equation}\\n    cursor\\n\\end{equation}"}, {"label": "Itemize", "latex": "\\n    \\- cursor\\n"}, {"label": "Section", "latex": "\\section{cursor}"}, {"label": "Include", "latex": "\\includegraphics{cursor}"}]',
            'language': 'en'
        }

        config['encoding'] = {
            'output_encoding': 'utf-8'
        }

        config['favorites'] = {
            'math_symbols': '\\alpha,\\beta,\\gamma,\\sum,\\int,\\frac{}{},\\sqrt{}',
            'arabic_commands': '\\textarabic{},\\foreignlanguage{arabic}{}'
        }
        
        return config
    
    def apply_config_to_window(self):
        """Apply configuration settings to main window"""
        try:
            # Basic compiler settings
            #self.main_window.latex_engine = self.config.get('compiler', 'latex_engine', fallback='xelatex')
            #self.main_window.backmatter_engine = self.config.get('compiler', 'backmatter_engine', fallback='bibtex')
            self.main_window.latex_engine = self._safe_latex_engine(
                self.config.get('compiler', 'latex_engine', fallback='pdflatex'))
            self.main_window.backmatter_engine = self._safe_backmatter_engine(
                self.config.get('compiler', 'backmatter_engine', fallback='bibtex'))

            # Encoding
            self.main_window.output_encoding = self.config.get('encoding', 'output_encoding', fallback='utf-8')

            # ✅ FIX: Define layout variable BEFORE using it
            layout = self.config['layout'] if 'layout' in self.config else None

            # Layout - now safe to use
            if layout:
                self.main_window.symbols_tab_visible = layout.getboolean('symbols_tab_visible', fallback=False)
                self.main_window.commands_tab_visible = layout.getboolean('commands_tab_visible', fallback=False)
                self.main_window.tree_tab_visible = layout.getboolean('tree_tab_visible', fallback=False)
                self.main_window.bookmarks_tab_visible = layout.getboolean('bookmarks_tab_visible', fallback=False)
                self.main_window.terminal_tab_visible = layout.getboolean('terminal_tab_visible', fallback=False)
                self.main_window.output_tabs_visible = layout.getboolean('output_tabs_visible', fallback=True)

                if hasattr(self.main_window, 'layout_manager') and self.main_window.layout_manager:
                    self.main_window.layout_manager.current_layout = layout.get('switch_mode', 'editor_left')
                    self.main_window.layout_manager.orientation = layout.get('main_layout_orientation', 'side_by_side')

                if hasattr(self.main_window, 'editor_manager') and self.main_window.editor_manager:
                    self.main_window.editor_manager.editor_layout_mode = layout.get('editor_layout_mode', 'tabbed')

                if hasattr(self.main_window, 'pdf_manager') and self.main_window.pdf_manager:
                    self.main_window.pdf_manager.pdf_layout_mode = layout.get('pdf_layout_mode', 'tabbed')
            else:
                # Set defaults when no layout section exists
                self.main_window.symbols_tab_visible = False
                self.main_window.commands_tab_visible = False
                self.main_window.tree_tab_visible = False
                self.main_window.bookmarks_tab_visible = False
                self.main_window.terminal_tab_visible = False
                self.main_window.output_tabs_visible = True

            # UI
            if 'ui' in self.config:
                ui = self.config['ui']
                self.main_window.menu_language = ui.get('menu_language', 'en')
                self.main_window.is_rtl = ui.getboolean('is_rtl', fallback=False)

                # Visibility settings
                is_line_numbers_visible = ui.getboolean('is_line_numbers_visible', fallback=True)
                is_fold_markers_visible = ui.getboolean('is_fold_markers_visible', fallback=True)
                self.main_window.is_line_numbers_visible = is_line_numbers_visible
                self.main_window.is_fold_markers_visible = is_fold_markers_visible
                #print(f"Config applied - Line numbers: {is_line_numbers_visible}, Fold markers: {is_fold_markers_visible}")

                # Apply RTL to existing editors if they exist
                if hasattr(self.main_window, 'editor_manager') and self.main_window.editor_manager:
                    self.apply_rtl_to_existing_editors()

                # Font settings
                self.main_window.editor_font_family = ui.get('editor_font_family', 'Consolas')
                self.main_window.editor_font_size = int(ui.get('editor_font_size', '11'))
                self.main_window.ui_font_family = ui.get('ui_font_family', 'Calibri')
                self.main_window.toolbar_font_size = int(ui.get('toolbar_font_size', '9'))
                
                # Theme — apply once at startup
                self.main_window.app_theme = ui.get('app_theme', 'default')
                from PyQt5.QtWidgets import QApplication
                from style_manager import apply_theme
                app = QApplication.instance()
                if app:
                    success = apply_theme(app, self.main_window.app_theme)
                    if not success:
                        #print(f"Theme '{self.main_window.app_theme}' requires qdarkstyle: pip install qdarkstyle")
                        self.main_window.app_theme = 'default'
                        apply_theme(app, 'default')                

                # Delayed visibility application
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(500, self._apply_visibility_to_editors)
            else:
                # Set UI defaults
                self.main_window.menu_language = 'en'
                self.main_window.is_rtl = False
                self.main_window.is_line_numbers_visible = True
                self.main_window.is_fold_markers_visible = True
                self.main_window.editor_font_family = 'Consolas'
                self.main_window.editor_font_size = 11
                self.main_window.ui_font_family = 'Calibri'
                self.main_window.toolbar_font_size = 9

            # Load command options
            for option_name in self.default_options.keys():
                option_value = self.config.get('compiler', option_name, fallback=self.default_options[option_name])
                setattr(self.main_window, option_name, option_value)

            # Window geometry
            if 'window' in self.config:
                try:
                    splitter_sizes = self.config.get('window', 'splitter_sizes', fallback='')
                    if hasattr(self.main_window, 'horizontal_splitter') and ',' in splitter_sizes:
                        sizes = [int(s.strip()) for s in splitter_sizes.split(',') if s.strip().isdigit()]
                        if len(sizes) == 2:
                            self.main_window.horizontal_splitter.setSizes(sizes)
                except Exception as e:
                    print(f"Error restoring window geometry: {e}")

            # Favorites
            if 'favorites' in self.config:
                fav = self.config['favorites']
                self.main_window.favorite_math_symbols = [
                    s.strip() for s in fav.get('math_symbols', '').split(',') if s.strip()
                ]
                self.main_window.favorite_arabic_commands = [
                    s.strip() for s in fav.get('arabic_commands', '').split(',') if s.strip()
                ]

            # Recent Files
            self._load_recent_files_from_config()

        except Exception as e:
            print(f"Error applying config: {e}")
            import traceback
            traceback.print_exc()
            # Set safe defaults on failure
            self.main_window.latex_engine = 'pdflatex'
            self.main_window.backmatter_engine = 'bibtex'
            self.main_window.output_encoding = 'utf-8'
            self.main_window.editor_font_family = 'Consolas'
            self.main_window.editor_font_size = 11
            self.main_window.ui_font_family = 'Calibri'
            self.main_window.toolbar_font_size = 9
            for option_name, default_value in self.default_options.items():
                setattr(self.main_window, option_name, default_value)
            
    def _apply_visibility_to_editors(self):
        """Apply line number and fold marker visibility to all editors"""
        try:
            if not hasattr(self.main_window, 'editor_manager'):
                return
            
            line_visible = getattr(self.main_window, 'is_line_numbers_visible', True)
            fold_visible = getattr(self.main_window, 'is_fold_markers_visible', True)
            
            #print(f"Applying visibility to editors - Line: {line_visible}, Fold: {fold_visible}")
            
            # Apply to all editors
            if hasattr(self.main_window.editor_manager, 'get_all_editors'):
                for editor in self.main_window.editor_manager.get_all_editors():
                    if hasattr(editor, 'set_line_numbers_visible'):
                        editor.set_line_numbers_visible(line_visible)
                    if hasattr(editor, 'set_fold_markers_visible'):
                        editor.set_fold_markers_visible(fold_visible)
            
            # Update menu checkboxes
            if hasattr(self.main_window, 'menu_manager'):
                if hasattr(self.main_window.menu_manager, 'line_numbers_action'):
                    self.main_window.menu_manager.line_numbers_action.setChecked(line_visible)
                if hasattr(self.main_window.menu_manager, 'fold_markers_action'):
                    self.main_window.menu_manager.fold_markers_action.setChecked(fold_visible)
                if hasattr(self.main_window.menu_manager, 'folding_menu'):
                    self.main_window.menu_manager.folding_menu.setEnabled(fold_visible)
                    
        except Exception as e:
            print(f"Error applying visibility to editors: {e}")
    
    def apply_rtl_to_existing_editors(self):
        """Apply RTL setting to all existing editors"""
        try:
            if hasattr(self.main_window, 'editor_manager') and self.main_window.editor_manager:
                editor_manager = self.main_window.editor_manager
                if hasattr(editor_manager, 'editor_files'):
                    alignment = Qt.AlignRight if self.main_window.is_rtl else Qt.AlignLeft
                    for filename, editor_data in editor_manager.editor_files.items():
                        editor = editor_data.get('editor')
                        if editor and hasattr(editor, 'setAlignment'):
                            editor.setAlignment(alignment)
                            #print(f"Applied RTL={self.main_window.is_rtl} to editor: {filename}")
        except Exception as e:
            print(f"Error applying RTL to existing editors: {e}")
    
    def save_current_settings(self):
        """Save current main window settings to config"""
        try:
            # Update config with current settings
            if not self.config.has_section('ui'):
                self.config.add_section('ui')
            
            # Save RTL setting
            rtl_value = False
            if hasattr(self, 'rtl_action'):
                # Check if rtl_action is a QAction with isChecked method
                if hasattr(self.rtl_action, 'isChecked'):
                    rtl_value = self.rtl_action.isChecked()
                elif hasattr(self.rtl_action, 'is_rtl'):
                    rtl_value = self.rtl_action.is_rtl
                #else:
                #    print(f"⚠️ rtl_action type: {type(self.rtl_action)}")
            
            
            self.config.set('ui', 'is_rtl', str(self.main_window.is_rtl))
            self.config.set('ui', 'is_line_numbers_visible', str(self.main_window.is_line_numbers_visible))
            self.config.set('ui', 'is_fold_markers_visible', str(self.main_window.is_fold_markers_visible))
            self.config.set('ui', 'menu_language', self.main_window.menu_language)
            
            if hasattr(self.main_window, 'editor_font_size'):
                self.config.set('ui', 'editor_font_size', str(self.main_window.editor_font_size))
            if hasattr(self.main_window, 'toolbar_font_size'):
                self.config.set('ui', 'toolbar_font_size', str(self.main_window.toolbar_font_size))
            
            # Save basic compiler settings
            if not self.config.has_section('compiler'):
                self.config.add_section('compiler')
            
            #self.config.set('compiler', 'latex_engine', self.main_window.latex_engine)
            #self.config.set('compiler', 'backmatter_engine', self.main_window.backmatter_engine)
            self.config.set('compiler', 'latex_engine',
                self._safe_latex_engine(self.main_window.latex_engine))
            self.config.set('compiler', 'backmatter_engine',
                self._safe_backmatter_engine(self.main_window.backmatter_engine))
            
            
            self.config.set('compiler', 'output_encoding', getattr(self.main_window, 'output_encoding', 'utf-8'))
            
            
            self.config.set('layout', 'symbols_tab_visible', str(self.main_window.symbols_tab_visible))
            self.config.set('layout', 'commands_tab_visible', str(self.main_window.commands_tab_visible))
            self.config.set('layout', 'tree_tab_visible', str(self.main_window.tree_tab_visible))
            self.config.set('layout', 'bookmarks_tab_visible', str(self.main_window.bookmarks_tab_visible))
            self.config.set('layout', 'terminal_tab_visible', str(self.main_window.terminal_tab_visible))
            

            
            
            # Save command options
            #for option_name in self.default_options.keys():
            #    option_value = getattr(self.main_window, option_name, self.default_options[option_name])
            #    self.config.set('compiler', option_name, option_value)
            for option_name in self.default_options.keys():
                option_value = getattr(self.main_window, option_name, self.default_options[option_name])
                self.config.set('compiler', option_name, str(option_value))
            
            if hasattr(self, 'current_file') and self.current_file:
                self.config.set('ui', 'last_file', self.current_file)
        
            
            # Save the config file
            self.save_config()
            #print("Settings saved to config file")
            
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def save_config(self):
        """Save current configuration to INI file"""
        try:
            # Ensure all sections exist
            sections = ['compiler', 'layout', 'window', 'ui', 'encoding', 'favorites', 'session_files', 'recent_pdf_files', 'bookmarks', 'recent_files']
            for section in sections:
                if not self.config.has_section(section):
                    self.config.add_section(section)
                    
                    
            # --- Bookmarks section - FIXED to avoid ConfigParser interpolation issues
            try:
                bookmarks_saved = False
                
                # Try to get bookmarks from bookmarks_widget (correct attribute name)
                if hasattr(self.main_window, 'bookmarks_widget'):
                    bookmarks_manager = self.main_window.bookmarks_widget
                    bookmarks_data = {}
                    
                    for file_path, file_bookmarks in bookmarks_manager.bookmarks.items():
                        if file_bookmarks:
                            bookmarks_data[file_path] = {}
                            for line_number, bookmark in file_bookmarks.items():
                                bookmarks_data[file_path][str(line_number)] = {
                                    'line_number': bookmark.line_number,
                                    'text_snippet': bookmark.text_snippet,
                                    'file_path': bookmark.editor_file_path or file_path
                                }
                    
                    # Save bookmarks using RawConfigParser to avoid interpolation
                    import json
                    import configparser
                    
                    if bookmarks_data:
                        bookmarks_json = json.dumps(bookmarks_data, indent=None, ensure_ascii=False)
                        # Escape problematic characters for INI format
                        escaped_json = bookmarks_json.replace('%', '%%')
                    else:
                        escaped_json = "{}"
                    
                    # Use a temporary RawConfigParser for the bookmarks section
                    temp_config = configparser.RawConfigParser()
                    temp_config.read(self.config_file, encoding='utf-8')
                    
                    if not temp_config.has_section('bookmarks'):
                        temp_config.add_section('bookmarks')
                    
                    temp_config.set('bookmarks', 'saved_bookmarks', escaped_json)
                    
                    # Write the temp config to get the bookmarks section right
                    with open(self.config_file + '.tmp', 'w', encoding='utf-8') as f:
                        temp_config.write(f)
                    
                    bookmarks_saved = True
                    #print(f"Bookmarks saved: {len(bookmarks_data)} files with bookmarks")
                
                # Fallback: set empty bookmarks if no bookmarks_widget
                if not bookmarks_saved:
                    # Use RawConfigParser for this too
                    import configparser
                    temp_config = configparser.RawConfigParser()
                    temp_config.read(self.config_file, encoding='utf-8')
                    
                    if not temp_config.has_section('bookmarks'):
                        temp_config.add_section('bookmarks')
                    
                    temp_config.set('bookmarks', 'saved_bookmarks', '{}')
                    
                    with open(self.config_file + '.tmp', 'w', encoding='utf-8') as f:
                        temp_config.write(f)
                    
                    #print("No bookmarks to save - set empty bookmarks section")
                    
            except Exception as be:
                print(f"Error while saving bookmarks: {be}")
                import traceback
                traceback.print_exc()
            
            # --- Save all other sections with regular ConfigParser
            # Remove bookmarks section from regular config to avoid conflicts
            if self.config.has_section('bookmarks'):
                self.config.remove_section('bookmarks')
            
            # Write the main config (without bookmarks)
            with open(self.config_file + '.main', 'w', encoding='utf-8') as f:
                self.config.write(f)
            
            # --- Merge the two files
            try:
                # Read both files and merge them
                import configparser
                
                # Read main config
                main_config = configparser.ConfigParser()
                if os.path.exists(self.config_file + '.main'):
                    main_config.read(self.config_file + '.main', encoding='utf-8')
                
                # Read bookmarks config
                bookmarks_config = configparser.RawConfigParser()
                if os.path.exists(self.config_file + '.tmp'):
                    bookmarks_config.read(self.config_file + '.tmp', encoding='utf-8')
                
                # Write final merged config
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    # Write main sections first
                    main_config.write(f)
                    
                    # Add bookmarks section manually
                    if bookmarks_config.has_section('bookmarks'):
                        f.write('\n[bookmarks]\n')
                        for option in bookmarks_config.options('bookmarks'):
                            value = bookmarks_config.get('bookmarks', option)
                            f.write(f'{option} = {value}\n')
                
                # Clean up temp files
                if os.path.exists(self.config_file + '.tmp'):
                    os.remove(self.config_file + '.tmp')
                if os.path.exists(self.config_file + '.main'):
                    os.remove(self.config_file + '.main')
                    
            except Exception as merge_error:
                print(f"Error merging config files: {merge_error}")
                # Fallback: just write main config without bookmarks
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    self.config.write(f)
            
            #print("Configuration saved successfully")

            
            # Update values
            self.config['encoding']['output_encoding'] = getattr(self.main_window, 'output_encoding', 'utf-8')
            
            # Update compiler section with current values
            if 'compiler' in self.config:
                comp = self.config['compiler']
                #comp['latex_engine'] = getattr(self.main_window, 'latex_engine', 'pdflatex')
                #comp['backmatter_engine'] = getattr(self.main_window, 'backmatter_engine', 'bibtex')
                comp['latex_engine'] = self._safe_latex_engine(
                    getattr(self.main_window, 'latex_engine', 'pdflatex'))
                comp['backmatter_engine'] = self._safe_backmatter_engine(
                    getattr(self.main_window, 'backmatter_engine', 'bibtex'))
                
                comp['output_encoding'] = getattr(self.main_window, 'output_encoding', 'utf-8')
                
                # Save command options
                # for option_name in self.default_options.keys():
                    # option_value = getattr(self.main_window, option_name, self.default_options[option_name])
                    # comp[option_name] = option_value
                    
                for option_name in self.default_options.keys():
                    option_value = getattr(self.main_window, option_name, self.default_options[option_name])
                    comp[option_name] = str(option_value)    
            
           
            if 'layout' in self.config:
                layout = self.config['layout']
                if hasattr(self.main_window, 'layout_manager'):
                    layout['switch_mode'] = getattr(self.main_window.layout_manager, 'current_layout', 'editor_left')
                    layout['main_layout_orientation'] = getattr(self.main_window.layout_manager, 'orientation', 'side_by_side')
                    layout['symbols_tab_visible'] = str(getattr(self.main_window, 'symbols_tab_visible', False))
                    layout['commands_tab_visible'] = str(getattr(self.main_window, 'commands_tab_visible', False))
                    layout['tree_tab_visible'] = str(getattr(self.main_window, 'tree_tab_visible', False))
                    layout['bookmarks_tab_visible'] = str(getattr(self.main_window, 'bookmarks_tab_visible', False))
                    layout['terminal_tab_visible'] = str(getattr(self.main_window, 'terminal_tab_visible', False))

                else:
                    layout['switch_mode'] = 'editor_left'
                    layout['main_layout_orientation'] = 'side_by_side'
                    layout['symbols_tab_visible'] = 'False'
                    layout['commands_tab_visible'] = 'False'
                    layout['bookmarks_tab_visible'] = 'False'
                    layout['terminal_tab_visible'] = 'False'
                    
                
                if hasattr(self.main_window, 'editor_manager'):
                    layout['editor_layout_mode'] = getattr(self.main_window.editor_manager, 'editor_layout_mode', 'tabbed')
                else:
                    layout['editor_layout_mode'] = 'tabbed'
                
                if hasattr(self.main_window, 'pdf_manager'):
                    layout['pdf_layout_mode'] = getattr(self.main_window.pdf_manager, 'pdf_layout_mode', 'tabbed')
                else:
                    layout['pdf_layout_mode'] = 'tabbed'
                
                layout['output_tabs_visible'] = str(getattr(self.main_window, 'output_tabs_visible', True))
            
            # Update window values
            if 'window' in self.config:
                win = self.config['window']
                geom = self.main_window.geometry()
                win['x'] = str(geom.x())
                win['y'] = str(geom.y())
                win['width'] = str(geom.width())
                win['height'] = str(geom.height())
                win['maximized'] = str(self.main_window.isMaximized())
                
                if hasattr(self.main_window, 'horizontal_splitter'):
                    sizes = self.main_window.horizontal_splitter.sizes()
                    win['splitter_sizes'] = f"{sizes[0]},{sizes[1]}"
            
            # Update UI values
            if 'ui' in self.config:
                ui = self.config['ui']
                ui['menu_language'] = getattr(self.main_window, 'menu_language', 'en')
                ui['is_rtl'] = str(getattr(self.main_window, 'is_rtl', False))
                ui['is_line_numbers_visible'] = str(getattr(self.main_window, 'is_line_numbers_visible', True))
                ui['is_fold_markers_visible'] = str(getattr(self.main_window, 'is_fold_markers_visible', True))
                ui['editor_font_size'] = str(getattr(self.main_window, 'editor_font_size', 11))
                ui['toolbar_font_size'] = str(getattr(self.main_window, 'toolbar_font_size', 10))
                ui['auto_load_last_file'] = str(getattr(self.main_window, 'auto_load_last_file', True))
                ui['app_theme'] = getattr(self.main_window, 'app_theme', 'default')
            
            # Update favorites
            if 'favorites' in self.config and hasattr(self.main_window, 'favorite_math_symbols'):
                fav = self.config['favorites']
                fav['math_symbols'] = ','.join(getattr(self.main_window, 'favorite_math_symbols', []))
                fav['arabic_commands'] = ','.join(getattr(self.main_window, 'favorite_arabic_commands', []))
            
            # Write to file
            with open(self.config_file, 'w', encoding='utf-8') as f:
                self.config.write(f)
                
        except Exception as e:
            print(f"Error saving config: {e}")

                
    def save_session_files(self, file_paths):
        """Save session files to config (keep last 100 files only)"""
        try:
            if not self.config.has_section('session_files'):
                self.config.add_section('session_files')

            # ✅ Keep only the LAST 100 files
            max_files = 100
            file_paths = file_paths[-max_files:]

            # Clear existing session files
            for i in range(1, max_files + 1):
                if self.config.has_option('session_files', f'file_{i}'):
                    self.config.remove_option('session_files', f'file_{i}')

            # Save new file list
            for i, file_path in enumerate(file_paths, 1):
                self.config.set('session_files', f'file_{i}', file_path)

            # Save count
            self.config.set('session_files', 'count', str(len(file_paths)))

            self.save_config()

        except Exception as e:
            print(f"❌ Error saving session files: {e}")                
            
    def get_session_files(self, count):
        """Get session files for restoration on startup"""
        session_files = []
        if 'session_files' in self.config:
            for i in range(1, count + 1):
                key = f'file_{i}'
                path = self.config.get('session_files', key, fallback='').strip()
                if path and os.path.exists(path) and os.path.isfile(path):
                    path = os.path.abspath(path)
                    session_files.append(path)
        return session_files
        
    
    def _load_recent_files_from_config(self):
        """Load recent files from INI into memory (for Recent Files menu)"""
        recent_files = []
        if 'recent_files' in self.config:
            for i in range(1, self.recent_files_limit + 1):
                key = f'file_{i}'
                path = self.config.get('recent_files', key, fallback='').strip()
                if path and os.path.exists(path) and os.path.isfile(path):
                    path = os.path.abspath(path)
                    if path not in recent_files:
                        recent_files.append(path)
        return recent_files
        
    def get_recent_files(self, max_count=100):
        """Get list of recent files, up to max_count"""
        recent_files = []
        try:
            for i in range(1, max_count + 1):
                key = f'recent_file_{i}'
                if self.config.has_option('recent_files', key):
                    file_path = self.config.get('recent_files', key).strip()
                    if file_path and os.path.exists(file_path):
                        recent_files.append(file_path)
                else:
                    break  # No more recent files
        except Exception as e:
            print(f"❌ Error getting recent files: {e}")
        return recent_files
        
 
    def save_session_on_close(self):
        """Save session when closing - FIXED"""
        try:
            if hasattr(self.main_window, 'config_manager'):
                config_manager = self.main_window.config_manager
                
                # Get list of currently open files
                open_files = list(self.editor_files.keys())
                
                # Save using the correct method
                if hasattr(config_manager, 'save_session_files'):
                    config_manager.save_session_files(open_files)
                    #print(f"💾 Session saved on close with {len(open_files)} files")
                #else:
                #    print("⚠️  save_session_files method not found")
        except Exception as e:
            print(f"❌ Error saving session on close: {e}")
            # Don't try the problematic add_recent_file call
            
    def add_recent_file(self, file_path):
        """Add file to top of recent files list, maintaining max 100 files"""
        try:
            if not file_path or not os.path.exists(file_path):
                return
            
            # ✅ FIX: Get the actual case-preserved path from the file system
            abs_path = self._get_case_preserved_path(file_path)
            #print(f"🔄 Adding to recent files: {abs_path}")
            
            # Ensure recent_files section exists
            if not self.config.has_section('recent_files'):
                self.config.add_section('recent_files')
            
            # Get current recent files
            current_recent = self.get_recent_files(101)
            
            # Remove file if it already exists (to avoid duplicates)
            # Compare case-insensitively but preserve case
            current_recent_lower = [f.lower() for f in current_recent]
            if abs_path.lower() in current_recent_lower:
                idx = current_recent_lower.index(abs_path.lower())
                current_recent.pop(idx)
                #print(f"🗑️  Removed duplicate from recent files")
            
            # Add to top
            current_recent.insert(0, abs_path)
            
            # Keep only first 101
            current_recent = current_recent[:101]
            
            # Clear existing recent files
            if self.config.has_section('recent_files'):
                self.config.remove_section('recent_files')
            self.config.add_section('recent_files')
            
            # Save updated list
            for i, path in enumerate(current_recent, 1):
                self.config.set('recent_files', f'recent_file_{i}', path)
            
            # Save config
            self.save_config()
            #print(f"✅ Successfully added to recent files. Total count: {len(current_recent)}")
            
        except Exception as e:
            print(f"❌ Error adding recent file: {e}")
            import traceback
            traceback.print_exc()

    def _get_case_preserved_path(self, path):
        """Get the actual case-preserved path by walking the directory tree"""
        try:
            import os
            from pathlib import Path
            
            # Use pathlib which preserves case better on Windows
            path_obj = Path(path).resolve()
            
            # Check if the path exists
            if not path_obj.exists():
                return str(path_obj)
            
            # On Windows, use os.listdir to get the actual case
            if os.name == 'nt':  # Windows
                # Start from the root and rebuild the path with correct case
                parts = path_obj.parts
                current = Path(parts[0])  # Start with drive letter (e.g., 'C:')
                
                for part in parts[1:]:
                    if current.exists():
                        # List directory contents and find matching name (case-insensitive)
                        try:
                            contents = list(current.iterdir())
                            matched = None
                            for item in contents:
                                if item.name.lower() == part.lower():
                                    matched = item.name
                                    break
                            
                            if matched:
                                current = current / matched
                            else:
                                current = current / part
                        except (PermissionError, OSError):
                            current = current / part
                    else:
                        current = current / part
                
                return str(current)
            else:
                return str(path_obj)
                
        except Exception as e:
            print(f"⚠️  Error getting case-preserved path: {e}")
            return os.path.abspath(path)

    def remove_recent_file(self, file_path):
        try:
            if not self.config.has_section('recent_files'):
                return
            if file_path:
                file_path = os.path.abspath(file_path)
            else:
                return

            # Get current list using the correct key format
            current_files = self.get_recent_files(max_count=101)

            # Remove the target file (case-insensitive comparison)
            current_files = [
                f for f in current_files
                if os.path.abspath(f).lower() != file_path.lower()
            ]

            # Rewrite the section from scratch using the correct key format
            self.config.remove_section('recent_files')
            self.config.add_section('recent_files')
            for i, path in enumerate(current_files, 1):
                self.config.set('recent_files', f'recent_file_{i}', path)  # ✅ correct key

            self.save_config()
            if hasattr(self.main_window, 'menu_manager'):
                self.main_window.menu_manager.update_recent_files_menu()

        except Exception as e:
            print(f"Error removing recent file: {e}")
            import traceback
            traceback.print_exc()
        
    def clear_recent_files(self):
        """Clear all recent files"""
        try:
            if self.config.has_section('recent_files'):
                self.config.remove_section('recent_files')
                self.save_config()
                #print("🗑️  Cleared all recent files")
        except Exception as e:
            print(f"❌ Error clearing recent files: {e}")
    
    def save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                self.config.write(f)
            #print("Config saved to latex_editor_config.ini")
        except Exception as e:
            print(f"❌ Error saving config: {e}")
        

        
    def get_side_panel_commands(self):
        """Load side panel commands from configuration"""
        try:
            commands_json = self.get_config_value('ui', 'side_panel_commands', None)
            if commands_json:
                commands = json.loads(commands_json)
                # Validate commands structure
                valid_commands = []
                for cmd in commands:
                    if isinstance(cmd, dict) and 'label' in cmd and 'latex' in cmd:
                        valid_commands.append(cmd)
                return valid_commands
        except (json.JSONDecodeError, Exception) as e:
            print(f"Error loading side panel commands: {e}")
        return None

    def save_side_panel_commands(self, commands=None):
        """Save side panel commands to configuration
        
        Args:
            commands: List of command dicts. If None, gets from side_panel.
        """
        try:
            # If no commands provided, get from side panel
            if commands is None:
                if hasattr(self.main_window, 'side_panel'):
                    commands = self.main_window.side_panel.get_commands()
                else:
                    #print("No commands provided and no side_panel available")
                    return False
            
            # Validate commands
            if not isinstance(commands, list):
                #print(f"Invalid commands type: {type(commands)}")
                return False
            
            # Ensure we don't exceed max buttons (100)
            commands = commands[:100]
            
            # Convert to JSON and save
            commands_json = json.dumps(commands, ensure_ascii=False)
            self.set_config_value('ui', 'side_panel_commands', commands_json)
            self.save_config()
            
            #print(f"Saved {len(commands)} side panel commands to config")
            return True
            
        except Exception as e:
            print(f"Error saving side panel commands: {e}")
            import traceback
            traceback.print_exc()
            return False

    
    def get_custom_arabic_commands(self):
        """Get list of custom Arabic commands"""
        return []
    
    # def add_recent_arabic_command(self, display_name, command_template):
        # """Add a recently used Arabic command and auto-save"""
        # pass
    
    def get_recent_arabic_commands(self):
        """Get list of recent Arabic commands"""
        return []
    
    def get_config_value(self, section, key, default_value=""):
        """Get config value with proper error handling"""
        try:
            if self.config.has_section(section) and self.config.has_option(section, key):
                return self.config.get(section, key)
            return default_value
        except Exception as e:
            print(f"Error getting config value [{section}][{key}]: {e}")
            return default_value
    
    def set_config_value(self, section, key, value):
        """Set config value with proper error handling"""
        try:
            if not self.config.has_section(section):
                self.config.add_section(section)
            self.config.set(section, key, str(value))
        except Exception as e:
            print(f"Error setting config value [{section}][{key}]: {e}")
    
    def get_recent_pdf_files(self, max_count=10):
        """Get list of recent PDF files, up to max_count (default 10)"""
        recent_pdf_files = []
        try:
            section = 'recent_pdf_files'  # ✅ Use consistent section name
            if not self.config.has_section(section):
                return recent_pdf_files  # Return empty list if section doesn't exist
                
            for i in range(1, max_count + 1):
                key = f'recent_pdf_file_{i}'
                if self.config.has_option(section, key):
                    file_path = self.config.get(section, key).strip()
                    if file_path:  # We don't check os.path.exists here, let the menu handle missing files
                        recent_pdf_files.append(file_path)
                else:
                    break
        except Exception as e:
            print(f"❌ Error getting recent PDF files: {e}")
        return recent_pdf_files

    def _save_recent_pdf_files(self, file_list):
        """Save the list of recent PDF files to the config INI file."""
        try:
            section = 'recent_pdf_files'  # ✅ Use dedicated section
            # Ensure the section exists
            if not self.config.has_section(section):
                self.config.add_section(section)

            # Clear existing recent PDF entries
            for i in range(1, self.recent_pdf_files_limit + 1):
                key = f'recent_pdf_file_{i}'
                if self.config.has_option(section, key):
                    self.config.remove_option(section, key)

            # Write the new list
            for i, file_path in enumerate(file_list, start=1):
                key = f'recent_pdf_file_{i}'
                self.config.set(section, key, file_path)

            # Save the config file
            self.save_config()

        except Exception as e:
            print(f"❌ Error saving recent PDF files: {e}")

    def add_recent_pdf_file(self, file_path):
        """Add a PDF file to the top of the recent PDF files list."""
        if not file_path:
            return
        
        try:
            # ✅ Use case-preserved path
            abs_path = self._get_case_preserved_path(file_path)
            
            # Get current list
            current_files = self.get_recent_pdf_files(max_count=100)
            
            # Remove duplicates (case-insensitive comparison)
            current_files_lower = [f.lower() for f in current_files]
            if abs_path.lower() in current_files_lower:
                idx = current_files_lower.index(abs_path.lower())
                current_files.pop(idx)
            
            # Add to the top
            current_files.insert(0, abs_path)
            
            # Save back to config
            self._save_recent_pdf_files(current_files[:self.recent_pdf_files_limit])
            
        except Exception as e:
            print(f"❌ Error adding recent PDF file: {e}")



    def remove_recent_pdf_file(self, file_path):
        """Remove a specific PDF file from the recent list."""
        if not file_path:
            return
        try:
            abs_path = os.path.abspath(file_path)
            current_files = self.get_recent_pdf_files(max_count=100)
            if abs_path in current_files:
                current_files.remove(abs_path)
                self._save_recent_pdf_files(current_files[:self.recent_pdf_files_limit])
        except Exception as e:
            print(f"❌ Error removing recent PDF file: {e}")

    def clear_recent_pdf_files(self):
        """Clear all recent PDF files from the list."""
        try:
            section = 'recent_pdf_files'
            if self.config.has_section(section):
                # Remove all keys in the section
                keys = list(self.config.options(section))  # ✅ Already correct
                for key in keys:
                    if key.startswith('recent_pdf_file_'):
                        self.config.remove_option(section, key)
            self.save_config()
            #print("✅ Recent PDF files cleared successfully")
        except Exception as e:
            print(f"❌ Error clearing recent PDF files: {e}")
            import traceback
            traceback.print_exc()
        

    def save_splitter_sizes(self, splitter_name, sizes):
        """Save splitter sizes to config
        
        Args:
            splitter_name: 'main_splitter' or 'editor_vertical_splitter'
            sizes: list of integers representing widget sizes
        """
        try:
            if not self.config.has_section('layout'):
                self.config.add_section('layout')
            
            # Convert sizes list to comma-separated string
            sizes_str = ','.join(str(s) for s in sizes)
            key = f'{splitter_name}_sizes'
            self.config.set('layout', key, sizes_str)
            self.save_config()
            #print(f"💾 Saved {splitter_name} sizes: {sizes_str}")
        except Exception as e:
            print(f"❌ Error saving splitter sizes: {e}")

    def get_splitter_sizes(self, splitter_name, default=None):
        """Get splitter sizes from config
        
        Args:
            splitter_name: 'main_splitter' or 'editor_vertical_splitter'
            default: default sizes if not found
        
        Returns:
            list of integers or default value
        """
        try:
            key = f'{splitter_name}_sizes'
            sizes_str = self.get_config_value('layout', key, '')
            
            if sizes_str:
                sizes = [int(s.strip()) for s in sizes_str.split(',') if s.strip().isdigit()]
                if sizes:
                    #print(f"📖 Loaded {splitter_name} sizes: {sizes}")
                    return sizes
            
            return default
        except Exception as e:
            print(f"❌ Error getting splitter sizes: {e}")
            return default

    def save_pdf_zoom_factor(self, zoom_factor):
        """Save PDF zoom factor to config
        
        Args:
            zoom_factor: float representing the zoom level (e.g., 1.0 = 100%)
        """
        try:
            if not self.config.has_section('layout'):
                self.config.add_section('layout')
            
            self.config.set('layout', 'pdf_zoom_factor', str(zoom_factor))
            self.save_config()
            #print(f"💾 Saved PDF zoom factor: {zoom_factor}")
        except Exception as e:
            print(f"❌ Error saving PDF zoom factor: {e}")

    def get_pdf_zoom_factor(self, default=1.0):
        """Get PDF zoom factor from config
        
        Args:
            default: default zoom factor if not found
        
        Returns:
            float representing zoom level
        """
        try:
            zoom_str = self.get_config_value('layout', 'pdf_zoom_factor', str(default))
            zoom = float(zoom_str)
            #print(f"📖 Loaded PDF zoom factor: {zoom}")
            return zoom
        except (ValueError, Exception) as e:
            print(f"❌ Error getting PDF zoom factor: {e}")
            return default
        