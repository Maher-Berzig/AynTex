# help_manager.py
"""
Help Manager - Handles hep  creation and management
"""

from PyQt5.QtWidgets import (
    QWidget, QLabel, QTextEdit, QTabWidget, 
    QDialog, QVBoxLayout,  QScrollArea,
    QTreeWidget, QTreeWidgetItem, QFrame, 
    QPushButton, QHeaderView, QHBoxLayout
)
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtCore import Qt
import style_manager 
import app_info



class ShortcutsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)        
        
        self.main_window = parent   # store reference

        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]

        self.setWindowTitle(tr["keyboard_shortcuts"])
        self.resize(600, 500)

        layout = QVBoxLayout(self)

        # ---- Tree Widget ----
        self.tree = QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.setRootIsDecorated(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.setAnimated(True)
        self.tree.setIndentation(20)

        is_rtl = getattr(self.main_window, "is_rtl", False)

        # Set layout direction
        self.tree.setLayoutDirection(Qt.RightToLeft if is_rtl else Qt.LeftToRight)

        # Set headers and column mapping
        if is_rtl:
            self.tree.setHeaderLabels([tr["action"], tr["shortcut"]])
            self.action_col = 0
            self.shortcut_col = 1
        else:
            self.tree.setHeaderLabels([tr["action"], tr["shortcut"]])
            self.action_col = 0
            self.shortcut_col = 1

        # Column resizing
        header = self.tree.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(self.action_col, header.Stretch)
        header.setSectionResizeMode(self.shortcut_col, header.ResizeToContents)

        # --- Make header labels RTL ---
        if is_rtl:
            header.setDefaultAlignment(Qt.AlignRight | Qt.AlignVCenter)
        else:
            header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        layout.addWidget(self.tree)
        lang = self.main_window.menu_language

        # ---- Data with New Shortcuts Organized ----
        
        shortcuts_data = {
            tr["file"]: [
                (tr["new"], "Ctrl+N"),
                (tr["open"], "Ctrl+O"),
                (tr["open_pdf"], "Ctrl+Shift+O"),
                (tr["save"], "Ctrl+S"),
                (tr["save_as"], "Ctrl+Shift+S"),
                (tr["save_copy_as"], "Ctrl+Shift+C"),                
                (tr["close_tex"], "Ctrl+Q"),
                (tr["close_pdf"], "Ctrl+Shift+Q"),
            ],
            
            tr["edit"]: [
                (tr["select_all"], "Ctrl+A"),
                (tr["select_env_beg"], "Ctrl+Shift+Down"),
                (tr["select_env_end"], "Ctrl+Shift+Up"),
                (tr["multiple_selections"], "Ctrl+ Mouse click"),
                
                (tr["undo"], "Ctrl+Z"),
                (tr["redo"], "Ctrl+Y"),
                (tr["cut"], "Ctrl+X"),
                (tr["copy"], "Ctrl+C"),
                (tr["paste"], "Ctrl+V"),
                
                (tr["find"], "Ctrl+F"),
                (tr["replace"], "Ctrl+H"),
                (tr["find_next"], "F3"),
                (tr["find_previous"], "Shift+F3"),
                
                (tr["lowercase"], "Ctrl+Down"),
                (tr["uppercase"], "Ctrl+Up"),
                (tr["comment"], "\u202ACtrl+/"),
                (tr["uncomment"], "\u202ACtrl+Shift+/"), 
                (tr["toggle_comments"], "Ctrl+D"),
                
                # Folding operations
                (tr["fold_current_section"], "\u202ACtrl+Shift+["),
                (tr["unfold_current_section"], "\u202ACtrl+Shift+]"),
                (tr["fold_all"], "\u202ACtrl+Shift+-"),
                (tr["unfold_all"], "\u202ACtrl+Shift+="),
            ],
            
            tr["view"]: [
                (tr["show_hide_side_panel"], "F9"),
                (tr["show_hide_main_toolbar"], "F10"),
                (tr["show_hide_menu_bar"], "F11"),
                (tr["full_normal_screen"], "F12"),
                (tr["show_hide_pdf_toolbar"], "Ctrl+F7"),
                (tr["direction"], "Ctrl+F8"),
                (tr["switch_side_panel_position"], "Ctrl+F9"),
                (tr["tab_tex"], "Ctrl+F10"),
                (tr["tab_pdf"], "Ctrl+F11"),
                (tr["switch"], "Ctrl+F12"),
                (tr["expand_editor_to_full_width"], "Ctrl+Shift+F9"),
                (tr["expand_pdf_to_full_width"], "Ctrl+Shift+F10"),
                (tr["split_window"], "Ctrl+Shift+F11"),
                (tr["hide_output"], "Ctrl+Shift+F12"),
                (tr["zoom_in"], "\u202ACtrl++"),
                (tr["zoom_out"], "\u202ACtrl+-"),
            ],
            
            tr["navigation"]: [
                (tr["jump"], "F7"),
                (tr["select_from_begin"], "Ctrl+Shift+Up"),
                (tr["select_from_end"], "Ctrl+Shift+Down"),
            ],
            
            tr["tools"]: [
                (tr["latex_document_wizard"], "Ctrl+W"),
                (tr["bibtex_manager"], "Ctrl+M"),
                (tr["tools_tab"], "Ctrl+T"),
                (tr["insert_character"], "Ctrl+R"), 
                (tr["knowledge_database"], "Ctrl+K"),                
                (tr["spreadsheet"], "Ctrl+E"),
                (tr["djvu_viewer"], "Ctrl+J"),
                (tr["todo_list"], "Ctrl+L"),
                (tr["tikz_plotter"], "Ctrl+P"),
                (tr["ai_assistant"], "Ctrl+I"),                
            ],
            
            tr["compilation"]: [
                (tr["compile"], "F5"),
                (tr["refresh"], "F6"),
                (tr["jump_in_pdf"], "F7"),
                (tr["bibtex"], "F8"),
            ],
            
            tr["special_tools"]: [
                (tr["arabic_tool"], "Alt+A"),
                (tr["symbols"], "Alt+S"),
                (tr["commands"], "Alt+C"),
                (tr["tree"], "Alt+R"),                
                (tr["marks"], "Alt+M"),                    
                (tr["terminal"], "Alt+N"),                    
            ],
            
            tr["settings_help"]: [
                (tr["settings"], "F2"),
                (tr["language"], "F4"),
                (tr["about"], "F1"),
            ],
            
            tr["side_panel"]: [
                (tr["button_1_10"], "Ctrl+ (1..9, 0)"),
                (tr["all_buttons"], "Ctrl+Space"),
            ],            
        }

        self.populate_tree(shortcuts_data)
       

        # ---- Bottom Buttons Layout ----
        buttons_layout = QHBoxLayout()

        fold_btn = QPushButton(tr.get("fold_all", "Fold all"))
        fold_btn.clicked.connect(self.tree.collapseAll)

        unfold_btn = QPushButton(tr.get("unfold_all", "Unfold all"))
        unfold_btn.clicked.connect(self.tree.expandAll)

        close_btn = QPushButton(tr.get("close", "Close"))
        close_btn.clicked.connect(self.accept)

        # Add buttons
        buttons_layout.addWidget(fold_btn)
        buttons_layout.addWidget(unfold_btn)

        buttons_layout.addStretch()  # pushes Close to edge

        buttons_layout.addWidget(close_btn)

        layout.addLayout(buttons_layout)


    # -----------------------------------
    def populate_tree(self, data):
        for category, shortcuts in data.items():
            category_item = QTreeWidgetItem([category])
            category_item.setFirstColumnSpanned(True)
            category_item.setExpanded(True)  # default expanded

            self.tree.addTopLevelItem(category_item)

            for action, shortcut in shortcuts:
                child = QTreeWidgetItem([action, shortcut])
                category_item.addChild(child)

        self.tree.expandAll()  # optional


class PluginHelpDialog(QDialog):
    """Dialog showing how to create plugins"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)                
        self.setWindowTitle("How to Make Tikz Plugins")
        #self.setGeometry(150, 150, 900, 700)
        self.resize(900, 600)
        
        layout = QVBoxLayout(self)
        
        # Create tab widget for organized content
        tabs = QTabWidget()
        
        # Tab 1: Overview
        overview_tab = QWidget()
        overview_layout = QVBoxLayout(overview_tab)
        overview_text = QTextEdit()
        overview_text.setReadOnly(True)
        overview_text.setHtml(self.get_overview_html())
        overview_layout.addWidget(overview_text)
        tabs.addTab(overview_tab, "Overview")
        
        # Tab 2: Plugin Interface
        interface_tab = QWidget()
        interface_layout = QVBoxLayout(interface_tab)
        interface_text = QTextEdit()
        interface_text.setReadOnly(True)
        interface_text.setStyleSheet("font-family: monospace;")
        interface_text.setPlainText(self.get_interface_code())
        interface_layout.addWidget(interface_text)
        tabs.addTab(interface_tab, "Plugin Interface")
        
        # Tab 3: Example Plugin
        example_tab = QWidget()
        example_layout = QVBoxLayout(example_tab)
        example_text = QTextEdit()
        example_text.setReadOnly(True)
        example_text.setStyleSheet("font-family: monospace;")
        example_text.setPlainText(self.get_example_plugin())
        example_layout.addWidget(example_text)
        tabs.addTab(example_tab, "Example Plugin")
        
        # Tab 4: Custom UI Plugin
        custom_ui_tab = QWidget()
        custom_ui_layout = QVBoxLayout(custom_ui_tab)
        custom_ui_text = QTextEdit()
        custom_ui_text.setReadOnly(True)
        custom_ui_text.setStyleSheet("font-family: monospace;")
        custom_ui_text.setPlainText(self.get_custom_ui_example())
        custom_ui_layout.addWidget(custom_ui_text)
        tabs.addTab(custom_ui_tab, "Custom UI Example")
        
        # Tab 5: Tips & Best Practices
        tips_tab = QWidget()
        tips_layout = QVBoxLayout(tips_tab)
        tips_text = QTextEdit()
        tips_text.setReadOnly(True)
        tips_text.setHtml(self.get_tips_html())
        tips_layout.addWidget(tips_text)
        tabs.addTab(tips_tab, "Tips & Best Practices")
        
        layout.addWidget(tabs)
        
        # Close button
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)
    
    def get_overview_html(self) -> str:
        return """
        <h2>Creating Plugins for TikZ Plotter</h2>
        
        <h3>Introduction</h3>
        <p>TikZ Plotter uses a modular plugin architecture that allows you to easily extend 
        its functionality. Each plugin is a Python class that inherits from the 
        <code>PlotPlugin</code> base class.</p>
        
        <h3>Plugin Structure</h3>
        <p>Every plugin must implement the following methods:</p>
        <ul>
            <li><b>get_plugin_name()</b> - Returns the display name shown in the UI</li>
            <li><b>get_user_options()</b> - Defines configurable options for the user</li>
            <li><b>validate_data()</b> - Validates input data before plotting</li>
            <li><b>plot()</b> - Creates a matplotlib figure</li>
            <li><b>generate_tikz()</b> - Generates TikZ/PGFPlots LaTeX code</li>
        </ul>
        
        <h3>File Location</h3>
        <p>Save your plugin file in the <code>plugins/</code> directory with a filename 
        ending in <code>_plugin.py</code> (e.g., <code>myplugin_plugin.py</code>). 
        The plugin manager will automatically discover and load it.</p>
        
        <h3>Quick Start</h3>
        <ol>
            <li>Create a new Python file in the <code>plugins/</code> folder</li>
            <li>Import required modules and the PlotPlugin base class</li>
            <li>Create a class that inherits from PlotPlugin</li>
            <li>Implement all required abstract methods</li>
            <li>Restart the application to load your plugin</li>
        </ol>
        """
    
    def get_interface_code(self) -> str:
        return '''# Plugin Interface - All plugins must inherit from this class

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple

class PlotPlugin(ABC):
    """Abstract base class for all plot plugins"""
    
    # Class attributes (optional, provide metadata)
    name: str = "Unnamed Plugin"
    version: str = "1.0.0"
    category: str = "general"
    description: str = ""
    requires_custom_ui: bool = False  # Set True for custom left panel
    
    @abstractmethod
    def get_plugin_name(self) -> str:
        """Return the display name of the plugin"""
        pass
    
    @abstractmethod
    def get_user_options(self) -> Dict[str, Dict[str, Any]]:
        """
        Return options needed from user.
        
        Format:
        {
            "option_name": {
                "type": "int|float|str|bool",  # Widget type
                "default": value,               # Default value
                "label": "Display Label",       # Label shown to user
                "min": min_value,              # Optional: for numeric types
                "max": max_value               # Optional: for numeric types
            }
        }
        """
        pass
    
    @abstractmethod
    def validate_data(self, data: Any) -> Tuple[bool, str]:
        """
        Validate input data.
        
        Args:
            data: The input data to validate
            
        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if data is valid
            - error_message: Description of error if invalid, empty string if valid
        """
        pass
    
    @abstractmethod
    def plot(self, data: Any, options: Dict[str, Any]) -> Any:
        """
        Generate matplotlib figure.
        
        Args:
            data: Validated input data
            options: Dict of option values from get_user_options()
            
        Returns:
            matplotlib Figure object
        """
        pass
    
    @abstractmethod
    def generate_tikz(self, data: Any, options: Dict[str, Any]) -> str:
        """
        Generate TikZ/PGFPlots code.
        
        Args:
            data: Validated input data
            options: Dict of option values
            
        Returns:
            String containing TikZ code
        """
        pass
    
    def get_tikz_libraries(self) -> List[str]:
        """Return required TikZ/LaTeX libraries (override if needed)"""
        return ["pgfplots"]
    
    def create_custom_ui(self, parent) -> Any:
        """Override to provide custom UI widget for left panel"""
        return None
    
    def get_custom_ui_data(self) -> Any:
        """Get data from custom UI (override if using custom UI)"""
        return None
'''
    
    def get_example_plugin(self) -> str:
        return '''# Example: Simple Area Plot Plugin
# Save as: plugins/areaplot_plugin.py

import matplotlib.pyplot as plt
import numpy as np
from typing import Any, Dict, List, Tuple

# Import base class (adjust path as needed)
from core.plugin_interface import PlotPlugin


class AreaPlotPlugin(PlotPlugin):
    """Area plot plugin - fills area under a curve"""
    
    # Plugin metadata
    name = "Area Plot"
    version = "1.0.0"
    category = "basic"
    description = "Create an area plot (filled line plot)"
    
    def get_plugin_name(self) -> str:
        """Return display name for UI"""
        return "Area Plot"
    
    def get_user_options(self) -> Dict[str, Dict[str, Any]]:
        """Define user-configurable options"""
        return {
            "color": {
                "type": "str",
                "default": "skyblue",
                "label": "Fill Color"
            },
            "alpha": {
                "type": "float",
                "default": 0.5,
                "label": "Transparency",
                "min": 0.1,
                "max": 1.0
            },
            "line_color": {
                "type": "str",
                "default": "blue",
                "label": "Line Color"
            },
            "linewidth": {
                "type": "float",
                "default": 2.0,
                "label": "Line Width",
                "min": 0.5,
                "max": 5.0
            },
            "xlabel": {
                "type": "str",
                "default": "x",
                "label": "X-axis Label"
            },
            "ylabel": {
                "type": "str",
                "default": "y",
                "label": "Y-axis Label"
            }
        }
    
    def validate_data(self, data: Any) -> Tuple[bool, str]:
        """Check if data is valid for this plot type"""
        try:
            arr = np.array(data)
            
            # Accept 1D array (y values only)
            if arr.ndim == 1:
                return True, ""
            
            # Accept 2D array with 2 columns (x, y)
            if arr.ndim == 2 and arr.shape[1] == 2:
                return True, ""
            
            return False, "Data must be 1D array or 2D array with 2 columns (x, y)"
        except Exception as e:
            return False, f"Invalid data format: {str(e)}"
    
    def plot(self, data: Any, options: Dict[str, Any]):
        """Create matplotlib figure with area plot"""
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Parse data
        arr = np.array(data)
        if arr.ndim == 1:
            x = np.arange(len(arr))
            y = arr
        else:
            x = arr[:, 0]
            y = arr[:, 1]
        
        # Create area plot
        ax.fill_between(x, y, 
                        color=options.get('color', 'skyblue'),
                        alpha=options.get('alpha', 0.5))
        
        # Add line on top
        ax.plot(x, y, 
                color=options.get('line_color', 'blue'),
                linewidth=options.get('linewidth', 2.0))
        
        # Labels and grid
        ax.set_xlabel(options.get('xlabel', 'x'))
        ax.set_ylabel(options.get('ylabel', 'y'))
        ax.grid(True, alpha=0.3)
        
        return fig
    
    def generate_tikz(self, data: Any, options: Dict[str, Any]) -> str:
        """Generate TikZ code for area plot"""
        arr = np.array(data)
        if arr.ndim == 1:
            x = np.arange(len(arr))
            y = arr
        else:
            x = arr[:, 0]
            y = arr[:, 1]
        
        # Create coordinate string
        coords = "\\n".join([f"        ({x[i]:.3f},{y[i]:.3f})" 
                            for i in range(len(x))])
        
        # Calculate opacity from alpha
        opacity = options.get('alpha', 0.5)
        
        tikz_code = f"""\\\\begin{{tikzpicture}}
\\\\begin{{axis}}[
    xlabel={{{options.get('xlabel', 'x')}}},
    ylabel={{{options.get('ylabel', 'y')}}},
    grid=major,
    width=12cm,
    height=8cm
]
% Filled area
\\\\addplot[
    fill={options.get('color', 'blue')},
    fill opacity={opacity},
    draw={options.get('line_color', 'blue')},
    line width={options.get('linewidth', 2.0)}pt
] coordinates {{
{coords}
}} \\\\closedcycle;
\\\\end{{axis}}
\\\\end{{tikzpicture}}"""
        
        return tikz_code
    
    def get_tikz_libraries(self) -> List[str]:
        """Return required LaTeX packages"""
        return ["pgfplots"]
'''
    
    def get_custom_ui_example(self) -> str:
        return '''# Example: Plugin with Custom UI
# For plugins that need more than simple text/number inputs
# Save as: plugins/customui_plugin.py

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QListWidget,
                             QLineEdit, QGroupBox)
import matplotlib.pyplot as plt
import numpy as np
from typing import Any, Dict, List, Tuple

from core.plugin_interface import PlotPlugin


class MultiSeriesPlugin(PlotPlugin):
    """Plugin with custom UI for multiple data series"""
    
    name = "Multi-Series Plot"
    version = "1.0.0"
    category = "advanced"
    description = "Plot multiple data series with custom UI"
    requires_custom_ui = True  # IMPORTANT: Enable custom UI mode
    
    def __init__(self):
        super().__init__()
        self.custom_ui_widget = None
        self.series_data = []  # Store multiple series
        self.series_list = None
        self.data_input = None
    
    def get_plugin_name(self) -> str:
        return "Multi-Series Plot"
    
    def get_user_options(self) -> Dict[str, Dict[str, Any]]:
        """Options shown below custom UI"""
        return {
            "xlabel": {
                "type": "str",
                "default": "X",
                "label": "X-axis Label"
            },
            "ylabel": {
                "type": "str",
                "default": "Y",
                "label": "Y-axis Label"
            },
            "show_legend": {
                "type": "bool",
                "default": True,
                "label": "Show Legend"
            }
        }
    
    def create_custom_ui(self, parent) -> QWidget:
        """
        Create custom input interface.
        This replaces the standard data input area.
        """
        self.custom_ui_widget = QWidget(parent)
        layout = QVBoxLayout(self.custom_ui_widget)
        
        # Series management group
        series_group = QGroupBox("Data Series")
        series_layout = QVBoxLayout()
        
        # Input for new series
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Series Name:"))
        self.series_name = QLineEdit()
        self.series_name.setPlaceholderText("e.g., Series A")
        input_layout.addWidget(self.series_name)
        series_layout.addLayout(input_layout)
        
        # Data input
        series_layout.addWidget(QLabel("Data (comma-separated):"))
        self.data_input = QLineEdit()
        self.data_input.setPlaceholderText("e.g., 1,2,3,4,5")
        series_layout.addWidget(self.data_input)
        
        # Add button
        btn_add = QPushButton("Add Series")
        btn_add.clicked.connect(self.add_series)
        series_layout.addWidget(btn_add)
        
        # List of added series
        series_layout.addWidget(QLabel("Added Series:"))
        self.series_list = QListWidget()
        series_layout.addWidget(self.series_list)
        
        # Remove button
        btn_remove = QPushButton("Remove Selected")
        btn_remove.clicked.connect(self.remove_series)
        series_layout.addWidget(btn_remove)
        
        # Clear all button
        btn_clear = QPushButton("Clear All")
        btn_clear.clicked.connect(self.clear_all)
        series_layout.addWidget(btn_clear)
        
        series_group.setLayout(series_layout)
        layout.addWidget(series_group)
        
        layout.addStretch()
        return self.custom_ui_widget
    
    def add_series(self):
        """Add a new data series"""
        name = self.series_name.text().strip() or f"Series {len(self.series_data) + 1}"
        data_str = self.data_input.text().strip()
        
        try:
            # Parse comma-separated values
            values = [float(x.strip()) for x in data_str.split(",")]
            self.series_data.append({"name": name, "data": values})
            self.series_list.addItem(f"{name}: {len(values)} points")
            
            # Clear inputs
            self.series_name.clear()
            self.data_input.clear()
        except ValueError:
            pass  # Invalid input, ignore
    
    def remove_series(self):
        """Remove selected series"""
        row = self.series_list.currentRow()
        if row >= 0:
            self.series_data.pop(row)
            self.series_list.takeItem(row)
    
    def clear_all(self):
        """Clear all series"""
        self.series_data.clear()
        self.series_list.clear()
    
    def get_custom_ui_data(self) -> Any:
        """
        Return data collected from custom UI.
        Called when generating plot or TikZ code.
        """
        return {"series": self.series_data.copy()}
    
    def validate_data(self, data: Any) -> Tuple[bool, str]:
        if isinstance(data, dict) and "series" in data:
            if len(data["series"]) > 0:
                return True, ""
            return False, "Add at least one data series"
        return False, "Invalid data format"
    
    def plot(self, data: Any, options: Dict[str, Any]):
        fig, ax = plt.subplots(figsize=(10, 8))
        
        colors = plt.cm.tab10.colors
        
        for i, series in enumerate(data["series"]):
            color = colors[i % len(colors)]
            y = series["data"]
            x = np.arange(len(y))
            ax.plot(x, y, label=series["name"], color=color, linewidth=2)
        
        ax.set_xlabel(options.get('xlabel', 'X'))
        ax.set_ylabel(options.get('ylabel', 'Y'))
        ax.grid(True, alpha=0.3)
        
        if options.get('show_legend', True):
            ax.legend()
        
        return fig
    
    def generate_tikz(self, data: Any, options: Dict[str, Any]) -> str:
        plots = []
        colors = ['blue', 'red', 'green', 'orange', 'purple', 'cyan']
        
        for i, series in enumerate(data["series"]):
            color = colors[i % len(colors)]
            coords = " ".join([f"({j},{v:.3f})" for j, v in enumerate(series["data"])])
            plots.append(f"""\\\\addplot[color={color}, thick] coordinates {{{coords}}};
\\\\addlegendentry{{{series["name"]}}}""")
        
        plots_str = "\\n".join(plots)
        
        return f"""\\\\begin{{tikzpicture}}
\\\\begin{{axis}}[
    xlabel={{{options.get('xlabel', 'X')}}},
    ylabel={{{options.get('ylabel', 'Y')}}},
    legend pos=north west,
    grid=major
]
{plots_str}
\\\\end{{axis}}
\\\\end{{tikzpicture}}"""
'''
    
    def get_tips_html(self) -> str:
        return """
        <h2>Tips & Best Practices</h2>
        
        <h3>Data Validation</h3>
        <p>Always validate input data thoroughly in <code>validate_data()</code>:</p>
        <ul>
            <li>Check data types and dimensions</li>
            <li>Handle edge cases (empty data, single points)</li>
            <li>Provide clear error messages</li>
            <li>Use try/except to catch conversion errors</li>
        </ul>
        
        <h3>User Options</h3>
        <p>Design options carefully for a good user experience:</p>
        <ul>
            <li>Use descriptive labels</li>
            <li>Set sensible default values</li>
            <li>Define appropriate min/max ranges for numeric options</li>
            <li>Keep the number of options manageable</li>
        </ul>
        
        <h3>TikZ Code Generation</h3>
        <p>Tips for generating clean TikZ code:</p>
        <ul>
            <li>Use proper indentation for readability</li>
            <li>Include comments explaining the code</li>
            <li>Specify required packages in <code>get_tikz_libraries()</code></li>
            <li>Test generated code in a LaTeX document</li>
            <li>Handle special characters in labels</li>
        </ul>
        
        <h3>Custom UI Plugins</h3>
        <p>When creating plugins with custom UI:</p>
        <ul>
            <li>Set <code>requires_custom_ui = True</code></li>
            <li>Implement <code>create_custom_ui()</code> to build your interface</li>
            <li>Implement <code>get_custom_ui_data()</code> to return collected data</li>
            <li>Store references to input widgets as instance variables</li>
            <li>Keep the UI intuitive and responsive</li>
        </ul>
        
        <h3>Testing Your Plugin</h3>
        <ol>
            <li>Test with various data inputs</li>
            <li>Verify matplotlib output looks correct</li>
            <li>Compile generated TikZ code in LaTeX</li>
            <li>Test edge cases and error handling</li>
            <li>Check that all options work as expected</li>
        </ol>
        
        <h3>Common Issues</h3>
        <ul>
            <li><b>Plugin not loading:</b> Check filename ends with <code>_plugin.py</code></li>
            <li><b>Import errors:</b> Ensure all dependencies are imported</li>
            <li><b>TikZ compilation errors:</b> Check for special characters and syntax</li>
            <li><b>Custom UI not showing:</b> Set <code>requires_custom_ui = True</code></li>
        </ul>
        """
    


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        lang = self.main_window.menu_language
        tr  = self.main_window.translations[lang]

        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setWindowTitle(tr["about"])        
        self.setMinimumSize(580, 620)    
        self.setModal(True)
        self.setup_ui()

    # ─────────────────────────────────────────────────────────────────────────
    def _theme_colors(self) -> dict:
        """
        Gather every colour we need from style_manager in one place.
        Callers receive a plain dict; no widget touches style_manager directly.
        """
        sp    = style_manager.get_settings_panel_style()  # info/section colours
        panel = style_manager.get_panel_style()           # sidebar bg

        return {
            # backgrounds
            "body_bg":      sp["section_bg"],
            "tab_pane_bg":  sp["section_bg"],
            "tab_rest_bg":  sp["info_bg"],
            "card_bg":      sp["info_bg"],
            "footer_bg":    panel["bg"],
            # borders
            "border":       sp["section_border"],
            "card_border":  sp["info_border"],
            # text
            "text":         sp["info_color"],
            "muted":        sp["help_color"],
            "heading":      sp["header_color"],
            # accent (underlines, links)
            "accent":       sp["link_color"],
        }

    def _section_label(self, html: str, c: dict) -> QLabel:
        """Bold heading with a coloured bottom rule."""
        lbl = QLabel(html)
        lbl.setTextFormat(Qt.RichText)
        lbl.setStyleSheet(f"""
            color: {c['heading']};
            font-size: 9pt;
            font-weight: bold;
            border-bottom: 1px solid {c['accent']};
            padding-bottom: 3px;
            margin-top: 6px;
            background: transparent;
        """)
        return lbl

    def _body_label(self, html: str, c: dict) -> QLabel:
        """Standard body text label (RichText, word-wrapped)."""
        lbl = QLabel(html)
        lbl.setTextFormat(Qt.RichText)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"font-size: 9.5pt; color: {c['text']}; background: transparent;")
        return lbl

    def _license_card(self, name: str, lic_type: str, url: str, c: dict) -> QFrame:
        """One row-card for the License Links tab."""
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet(f"""
            QFrame {{
                background: {c['card_bg']};
                border: 1px solid {c['card_border']};
                border-radius: 5px;
            }}
        """)
        row = QHBoxLayout(card)
        row.setContentsMargins(12, 7, 12, 7)
        row.setSpacing(10)

        name_lbl = QLabel(f"<b>{name}</b>")
        name_lbl.setTextFormat(Qt.RichText)
        name_lbl.setFixedWidth(175)
        name_lbl.setStyleSheet(
            f"background: transparent; border: none; font-size: 9.5pt; color: {c['heading']};"
        )

        type_lbl = QLabel(lic_type)
        type_lbl.setFixedWidth(130)
        type_lbl.setStyleSheet(
            f"background: transparent; border: none; font-size: 8.5pt; color: {c['muted']};"
        )

        link_lbl = QLabel(
            f'<a href="{url}" style="color:{c["accent"]}; text-decoration:none;">{url}</a>'
        )
        link_lbl.setTextFormat(Qt.RichText)
        link_lbl.setOpenExternalLinks(True)
        link_lbl.setWordWrap(True)
        link_lbl.setStyleSheet("background: transparent; border: none; font-size: 8.5pt;")

        row.addWidget(name_lbl)
        row.addWidget(type_lbl)
        row.addWidget(link_lbl, stretch=1)
        return card

    def _styled_tabs(self, c: dict) -> QTabWidget:
        tabs = QTabWidget()

        # Prevent any tab title from being elided (truncated with …)
        tabs.tabBar().setElideMode(Qt.ElideNone)
        # Let each tab be exactly as wide as its text needs, not stretched
        tabs.tabBar().setExpanding(False)

        tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {c['border']};
                border-radius: 5px;
                background: {c['tab_pane_bg']};
                top: -1px;
            }}
            QTabBar::tab {{
                padding: 6px 18px;
                font-size: 9pt;
                color: {c['muted']};
                border: 1px solid transparent;
                border-bottom: none;
                border-radius: 5px 5px 0 0;
                margin-right: 3px;
                background: {c['tab_rest_bg']};
                min-width: 100px;        /* enough room for "License Links" */
            }}
            QTabBar::tab:selected {{
                background: {c['tab_pane_bg']};
                border-color: {c['border']};
                color: {c['heading']};
                font-weight: bold;
            }}
            QTabBar::tab:hover:!selected {{
                background: {c['card_bg']};
                color: {c['text']};
            }}
        """)
        return tabs


    # ─────────────────────────────────────────────────────────────────────────
    def setup_ui(self):
        lang = self.main_window.menu_language
        tr   = self.main_window.translations[lang]
        c    = self._theme_colors()           # all colours, resolved once

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ══════════════════════════════════════════════════════════════════════
        # HEADER BANNER  (fixed branding gradient – looks good on every theme)
        # ══════════════════════════════════════════════════════════════════════
        header = QWidget()
        header.setFixedHeight(150)
        header.setStyleSheet("""
            QWidget {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0   #0d2233,
                    stop:0.5 #1b4f6a,
                    stop:1   #1f7a8c
                );
            }
        """)
        hdr_l = QVBoxLayout(header)
        hdr_l.setContentsMargins(30, 18, 30, 18)
        hdr_l.setSpacing(3)

        app_lbl = QLabel(app_info.APP_NAME if lang == "en" else app_info.APP_NAME_AR)
        app_lbl.setAlignment(Qt.AlignCenter)
        app_lbl.setStyleSheet(
            "background:transparent; color:#ffffff; font-size:26pt;"
            " font-weight:bold; letter-spacing:2px;"
        )

        tagline_lbl = QLabel(
            "A modern LaTeX editor" if lang == "en" else "محرر لاتاك حديث"
        )
        tagline_lbl.setAlignment(Qt.AlignCenter)
        tagline_lbl.setStyleSheet(
            "background:transparent; color:rgba(255,255,255,0.60); font-size:10pt;"
        )

        rule = QFrame()
        rule.setFrameShape(QFrame.HLine)
        rule.setFixedHeight(1)
        rule.setStyleSheet(
            "background:rgba(255,255,255,0.18); border:none; margin:4px 60px;"
        )

        author_name = app_info.APP_AUTHOR if lang == "en" else app_info.APP_AUTHOR_AR
        author_lbl = QLabel(f"© 2026  {author_name}")
        author_lbl.setAlignment(Qt.AlignCenter)
        author_lbl.setStyleSheet(
            "background:transparent; color:rgba(255,255,255,0.42); font-size:8.5pt;"
        )

        for w in (app_lbl, tagline_lbl, rule, author_lbl):
            hdr_l.addWidget(w)
        root.addWidget(header)

        # ══════════════════════════════════════════════════════════════════════
        # BODY
        # ══════════════════════════════════════════════════════════════════════
        body = QWidget()
        body.setStyleSheet(f"background: {c['body_bg']};")
        body_l = QVBoxLayout(body)
        body_l.setContentsMargins(22, 14, 22, 10)
        body_l.setSpacing(10)

        desc_text = (
            f"{app_info.APP_NAME} is a lightweight editor focused on LaTeX productivity, "
            "a clean UI, and efficient workflows."
            if lang == "en" else
            f"{app_info.APP_NAME_AR} هو محرر خفيف يركز على إنتاجية لاتاك، "
            "واجهة سهلة الإستخدام لسير عمل فعّال."
        )
        desc = QLabel(desc_text)
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        desc.setStyleSheet(
            f"color:{c['muted']}; font-size:9.5pt;"
            " padding:0 20px 4px; background:transparent;"
        )
        body_l.addWidget(desc)

        tabs = self._styled_tabs(c)

        # ── Tab 1 : License (app) ─────────────────────────────────────────────
        lic_w = QWidget()
        lic_w.setStyleSheet(f"background: {c['tab_pane_bg']};")
        lic_l = QVBoxLayout(lic_w)
        lic_l.setContentsMargins(14, 12, 14, 12)

        lic_box = QTextEdit()
        lic_box.setReadOnly(True)
        lic_box.setStyleSheet(f"""
            QTextEdit {{
                background: {c['card_bg']};
                border: 1px solid {c['card_border']};
                border-radius: 4px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 9.5pt;
                color: {c['text']};
                padding: 6px;
            }}
        """)
        gpl_en = (
            f"{app_info.APP_NAME} is free software: you can redistribute it and/or\n"
            "modify it under the terms of the GNU General Public License as\n"
            "published by the Free Software Foundation, either version 3 of\n"
            "the License, or (at your option) any later version.\n\n"
            f"{app_info.APP_NAME} is distributed in the hope that it will be useful,\n"
            "but WITHOUT ANY WARRANTY; without even the implied warranty of\n"
            "MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.\n\n"
            "Full license text:\n"
            "https://www.gnu.org/licenses/gpl-3.0.html"
        )
        gpl_ar = (
            f"برنامج {app_info.APP_NAME_AR} برنامج مجاني: يمكنك إعادة توزيعه و/أو تعديله\n"
            "بموجب شروط رخصة جنو العمومية العامة كما نشرتها مؤسسة البرمجيات الحرة،\n"
            "سواء الإصدار 3 من الرخصة، أو (حسب اختيارك) أي إصدار لاحق.\n\n"
            f"يُوزع برنامج {app_info.APP_NAME_AR} على أمل أن يكون مفيدًا،\n"
            "ولكن بدون أي ضمان؛ حتى بدون الضمان الضمني لقابلية التسويق أو لغرض معين.\n\n"
            "نص الرخصة الكامل:\n"
            "https://www.gnu.org/licenses/gpl-3.0.html"
        )
        lic_box.setPlainText(gpl_en if lang == "en" else gpl_ar)
        lic_l.addWidget(lic_box)
        tabs.addTab(lic_w, tr.get("license", "License"))

        # ── Tab 2 : Credits ───────────────────────────────────────────────────────
        cred_outer = QWidget()
        cred_outer.setStyleSheet(f"background: {c['tab_pane_bg']};")
        cred_outer_l = QVBoxLayout(cred_outer)
        cred_outer_l.setContentsMargins(0, 0, 0, 0)
        cred_outer_l.setSpacing(0)

        # Inner widget that holds the actual content — sized by its children,
        # not by the scroll-area viewport, so the scroll bar appears when needed.
        cred_inner = QWidget()
        cred_inner.setStyleSheet(f"background: {c['tab_pane_bg']};")
        cred_l = QVBoxLayout(cred_inner)
        cred_l.setContentsMargins(14, 12, 14, 12)
        cred_l.setSpacing(4)

        cred_l.addWidget(self._section_label("Libraries &amp; Frameworks", c))
        cred_l.addWidget(self._body_label(
            f"&nbsp;&nbsp;• <b>Qt</b> — GUI framework<br>"
            f"&nbsp;&nbsp;• <b>KaTeX</b> — Math rendering in preview<br>"
            f"&nbsp;&nbsp;• <b>Matplotlib</b> — Plotting and figure generation<br>"
            f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
            f"<span style='color:{c['muted']};font-size:8.5pt;'>"
            f"Hunter et al., <i>Computing in Science &amp; Engineering</i>, 2007</span><br>"
            f"&nbsp;&nbsp;• <b>PyMuPDF</b> — PDF rendering and text extraction<br>"
            f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
            f"<span style='color:{c['muted']};font-size:8.5pt;'>"
            f"Open-source under AGPL v3; built on MuPDF by Artifex</span><br>"
            f"&nbsp;&nbsp;• <b>QDarkStyle</b> — Dark/light Qt stylesheet (MIT)<br>"
            f"&nbsp;&nbsp;• <b>pyspellchecker</b> — Offline spell checking (MIT)<br>"
            f"&nbsp;&nbsp;• <b>bibtexparser</b> — BibTeX file parsing (LGPL v3 or BSD)<br>"
            f"&nbsp;&nbsp;• <b>googletrans</b> — Google Translate API wrapper (MIT)<br>"
            f"&nbsp;&nbsp;• <b>DjVuLibre</b> — DjVu document support",
            c,
        ))
        cred_l.addWidget(self._section_label("Completions &amp; Syntax", c))
        cred_l.addWidget(self._body_label(
            f"&nbsp;&nbsp;• <b>TeXstudio</b> — CWL completion word list files<br>"
            f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
            f"<span style='color:{c['muted']};font-size:8.5pt;'>"
            f"Used for LaTeX command auto-completion &middot; GPL v2+</span>",
            c,
        ))

        cred_l.addWidget(self._section_label("Fonts", c))
        cred_l.addWidget(self._body_label(
            f"&nbsp;&nbsp;• <b>STIX Two Math</b> — Mathematical typesetting<br>"
            f"&nbsp;&nbsp;• <b>Font Awesome</b> — Icon font<br>"
            f"&nbsp;&nbsp;• <b>D050000L</b> — TeX/URW font (Ghostscript repository)<br>"
            f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
            f"<span style='color:{c['muted']};font-size:8.5pt;'>"
            f"All three fonts are licensed under the SIL Open Font License, Version 1.1</span>",
            c,
        ))

        cred_l.addStretch()

        scroll_cred = QScrollArea()
        scroll_cred.setWidgetResizable(True)
        scroll_cred.setFrameShape(QFrame.NoFrame)
        scroll_cred.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_cred.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_cred.setStyleSheet(f"background: {c['tab_pane_bg']}; border: none;")
        scroll_cred.setWidget(cred_inner)

        cred_outer_l.addWidget(scroll_cred)
        tabs.addTab(cred_outer, tr.get("credits", "Credits"))
        
        # ── Tab 3 : License Links ─────────────────────────────────────────────────
        links_w = QWidget()
        links_w.setStyleSheet(f"background: {c['tab_pane_bg']};")
        links_l = QVBoxLayout(links_w)
        links_l.setContentsMargins(14, 12, 14, 12)
        links_l.setSpacing(6)

        intro = QLabel("Web locations for the license of each third-party component:")
        intro.setWordWrap(True)
        intro.setStyleSheet(
            f"color:{c['muted']}; font-size:8.5pt; margin-bottom:2px; background:transparent;"
        )
        links_l.addWidget(intro)

        # Pull tree colours from style_manager (already defined for every theme)
        tw = style_manager.get_tree_widget_style()

        tree = QTreeWidget()
        tree.setColumnCount(3)
        tree.setHeaderLabels(["Component", "License", "URL"])
        tree.setRootIsDecorated(False)       # no expand arrow — flat list
        tree.setAlternatingRowColors(True)
        tree.setSelectionMode(QTreeWidget.NoSelection)
        tree.setFocusPolicy(Qt.NoFocus)

        # Resizable columns — user can drag the dividers
        tree.header().setSectionResizeMode(0, QHeaderView.Interactive)
        tree.header().setSectionResizeMode(1, QHeaderView.Interactive)
        tree.header().setSectionResizeMode(2, QHeaderView.Stretch)  # URL fills remainder
        tree.header().setStretchLastSection(True)
        tree.setColumnWidth(0, 170)
        tree.setColumnWidth(1, 130)

        tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {tw['bg']};
                color: {c['text']};
                border: 1px solid {tw['border']};
                alternate-background-color: {tw['item_border']};
                font-size: 9pt;
            }}
            QTreeWidget::item {{
                padding: 4px 4px;
            }}
            QTreeWidget::item:hover {{
                background-color: {tw['hover_bg']};
            }}
            QHeaderView::section {{
                background-color: {tw['header_bg']};
                color: {tw['header_color']};
                border: 1px solid {tw['header_border']};
                padding: 5px 8px;
                font-weight: bold;
                font-size: 8.5pt;
            }}
            QHeaderView::section:horizontal {{
                border-right: 1px solid {tw['header_border']};
            }}
        """)

        license_entries = [
            # ── App license ──────────────────────────────────────────────────────
            ("Qt",                   "LGPL v3 / GPL v3",    "https://doc.qt.io/qt-5/lgpl.html"),
            ("KaTeX",                "MIT",                  "https://github.com/KaTeX/KaTeX/blob/main/LICENSE"),
            ("Matplotlib",           "BSD-compatible (PSF)", "https://matplotlib.org/stable/users/project/license.html"),
            ("PyMuPDF",              "AGPL v3",              "https://github.com/pymupdf/PyMuPDF/blob/main/COPYING"),
            ("QDarkStyle",           "MIT",                  "https://github.com/ColinDuquesnoy/QDarkStyleSheet/blob/master/LICENSE.rst"),
            ("pyspellchecker",       "MIT",                  "https://github.com/barrust/pyspellchecker/blob/master/LICENSE"),
            ("bibtexparser",  "LGPL v3 / BSD", "https://github.com/sciunto-org/python-bibtexparser/blob/master/COPYING"),
            ("googletrans",          "MIT",                  "https://github.com/ssut/py-googletrans/blob/master/LICENSE"),
            ("DjVuLibre",            "GPL v2+",              "https://djvu.sourceforge.net/"),
            # ── Completions ───────────────────────────────────────────────────────
            ("TeXstudio (CWL)",      "GPL v2+",              "https://github.com/texstudio-org/texstudio/blob/master/COPYING"),
            # ── Fonts ─────────────────────────────────────────────────────────────
            ("STIX Two Math",        "SIL OFL 1.1",          "https://www.stixfonts.org/"),
            ("Font Awesome",         "SIL OFL 1.1",          "https://fontawesome.com/license/free"),
            ("D050000L (URW fonts)", "SIL OFL 1.1",          "https://github.com/ArtifexSoftware/urw-base35-fonts"),
        ]
        for name, lic_type, url in license_entries:
            item = QTreeWidgetItem([name, lic_type, url])
            item.setToolTip(2, url)          # show full URL on hover when column is narrow
            tree.addTopLevelItem(item)

        links_l.addWidget(tree, stretch=1)
        tabs.addTab(links_w, tr.get("license_locations", "License Links"))
        body_l.addWidget(tabs, stretch=1)        
        root.addWidget(body, stretch=1)

        # ══════════════════════════════════════════════════════════════════════
        # FOOTER
        # ══════════════════════════════════════════════════════════════════════
        footer = QWidget()
        footer.setFixedHeight(52)
        footer.setStyleSheet(f"""
            QWidget {{
                background: {c['footer_bg']};
                border-top: 1px solid {c['border']};
            }}
        """)
        footer_l = QHBoxLayout(footer)
        footer_l.setContentsMargins(20, 10, 20, 10)
        footer_l.addStretch()

        close_btn = QPushButton(tr.get("close", "Close"))
        close_btn.clicked.connect(self.accept)
        close_btn.setFixedSize(110, 30)
        close_btn.setCursor(Qt.PointingHandCursor)
        # Reuse the app's own themed button style so it matches everywhere
        close_btn.setStyleSheet(style_manager.get_button_style("normal"))

        footer_l.addWidget(close_btn)
        root.addWidget(footer)

    # ─────────────────────────────────────────────────────────────────────────
    def show_about_dialog(self):
        dialog = AboutDialog(self.parent())
        dialog.exec_()
