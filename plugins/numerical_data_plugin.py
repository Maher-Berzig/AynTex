# ============================================================================
# FILE: plugins/numerical_data_plugin.py
# NEW PLUGIN: Accepts copy/paste numerical data (double column)
# ============================================================================

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QTextEdit,
    QPushButton, QComboBox, QMessageBox, QCheckBox
)
import matplotlib.pyplot as plt
import numpy as np
from typing import Any, Dict, List, Tuple
from tikz_plotter_tab import PlotPlugin


class NumericalDataPlugin(PlotPlugin):
    """Plugin for plotting from pasted numerical data (supports copy/paste from spreadsheets)"""
    
    name = "Numerical Data Plot"
    version = "1.0.0"
    category = "data"
    description = "Plot data from copy/paste (supports tab/space/comma separated values)"
    requires_custom_ui = True
    
    def __init__(self):
        super().__init__()
        self.custom_ui_widget = None
        self.data_text = None
        self.delimiter_combo = None
        self.has_header = None
        self.parsed_data = None
    
    def get_plugin_name(self) -> str:
        return "Numerical Data Plot"
    
    def get_user_options(self) -> Dict[str, Dict[str, Any]]:
        return {
            "plot_type": {
                "type": "str",
                "default": "line",
                "label": "Plot Type (line, scatter, both)"
            },
            "color": {
                "type": "str",
                "default": "blue",
                "label": "Color"
            },
            "linewidth": {
                "type": "float",
                "default": 2.0,
                "label": "Line Width",
                "min": 0.5,
                "max": 5.0
            },
            "marker_size": {
                "type": "float",
                "default": 6.0,
                "label": "Marker Size",
                "min": 1.0,
                "max": 20.0
            },
            "xlabel": {
                "type": "str",
                "default": "X",
                "label": "X-axis Label"
            },
            "ylabel": {
                "type": "str",
                "default": "Y",
                "label": "Y-axis Label"
            }
        }
    
    def create_custom_ui(self, parent):
        """Create custom UI for data paste"""
        self.custom_ui_widget = QWidget(parent)
        layout = QVBoxLayout(self.custom_ui_widget)
        
        # Data input group
        data_group = QGroupBox("Paste Numerical Data")
        data_layout = QVBoxLayout()
        
        # Instructions
        instructions = QLabel(
            "Paste your data below (two columns: X and Y values).\n"
            "Supports tab, space, or comma separated values.\n"
            "You can copy directly from Excel, Google Sheets, or text files."
        )
        instructions.setWordWrap(True)
        data_layout.addWidget(instructions)
        
        # Delimiter selection
        delim_layout = QHBoxLayout()
        delim_layout.addWidget(QLabel("Delimiter:"))
        self.delimiter_combo = QComboBox()
        self.delimiter_combo.addItems(["Auto-detect", "Tab", "Space", "Comma", "Semicolon"])
        delim_layout.addWidget(self.delimiter_combo)
        
        self.has_header = QCheckBox("First row is header")
        delim_layout.addWidget(self.has_header)
        delim_layout.addStretch()
        data_layout.addLayout(delim_layout)
        
        # Text area for data
        self.data_text = QTextEdit()
        self.data_text.setPlaceholderText(
            "Example:\n"
            "1.0    2.5\n"
            "2.0    4.1\n"
            "3.0    5.8\n"
            "4.0    8.2\n"
            "5.0    9.7"
        )
        self.data_text.setMinimumHeight(200)
        data_layout.addWidget(self.data_text)
        
        # Parse button
        btn_layout = QHBoxLayout()
        btn_parse = QPushButton("Parse Data")
        btn_parse.clicked.connect(self.parse_data)
        btn_layout.addWidget(btn_parse)
        
        btn_clear = QPushButton("Clear")
        btn_clear.clicked.connect(self.clear_data)
        btn_layout.addWidget(btn_clear)
        
        btn_sample = QPushButton("Load Sample")
        btn_sample.clicked.connect(self.load_sample)
        btn_layout.addWidget(btn_sample)
        
        data_layout.addLayout(btn_layout)
        
        # Status label
        self.status_label = QLabel("")
        data_layout.addWidget(self.status_label)
        
        data_group.setLayout(data_layout)
        layout.addWidget(data_group)
        
        layout.addStretch()
        return self.custom_ui_widget
    
    def detect_delimiter(self, text: str) -> str:
        """Auto-detect the delimiter used in the data"""
        lines = text.strip().split('\n')
        if not lines:
            return '\t'
        
        first_line = lines[0]
        
        # Check for common delimiters
        if '\t' in first_line:
            return '\t'
        elif ',' in first_line:
            return ','
        elif ';' in first_line:
            return ';'
        else:
            return None  # Use whitespace splitting
    
    def parse_data(self):
        """Parse the pasted data"""
        text = self.data_text.toPlainText().strip()
        if not text:
            self.status_label.setText("No data to parse")
            return
        
        # Get delimiter
        delim_choice = self.delimiter_combo.currentText()
        if delim_choice == "Auto-detect":
            delimiter = self.detect_delimiter(text)
        elif delim_choice == "Tab":
            delimiter = '\t'
        elif delim_choice == "Space":
            delimiter = None
        elif delim_choice == "Comma":
            delimiter = ','
        elif delim_choice == "Semicolon":
            delimiter = ';'
        else:
            delimiter = None
        
        try:
            lines = text.strip().split('\n')
            start_idx = 1 if self.has_header.isChecked() else 0
            
            data = []
            for line in lines[start_idx:]:
                if not line.strip():
                    continue
                if delimiter:
                    parts = line.split(delimiter)
                else:
                    parts = line.split()
                
                if len(parts) >= 2:
                    x = float(parts[0].strip())
                    y = float(parts[1].strip())
                    data.append([x, y])
            
            if len(data) > 0:
                self.parsed_data = data
                self.status_label.setText(f"✓ Parsed {len(data)} data points successfully")
                self.status_label.setStyleSheet("color: green;")
            else:
                self.status_label.setText("✗ No valid data found")
                self.status_label.setStyleSheet("color: red;")
                
        except Exception as e:
            self.status_label.setText(f"✗ Parse error: {str(e)}")
            self.status_label.setStyleSheet("color: red;")
    
    def clear_data(self):
        """Clear the data input"""
        self.data_text.clear()
        self.parsed_data = None
        self.status_label.setText("")
    
    def load_sample(self):
        """Load sample data"""
        sample = """1.0\t2.3
2.0\t4.1
3.0\t5.8
4.0\t8.2
5.0\t10.1
6.0\t12.5
7.0\t14.2
8.0\t16.8
9.0\t18.9
10.0\t21.3"""
        self.data_text.setPlainText(sample)
        self.parse_data()
    
    def get_custom_ui_data(self):
        """Get parsed data"""
        if self.parsed_data is None:
            self.parse_data()
        return self.parsed_data
    
    def validate_data(self, data: Any) -> Tuple[bool, str]:
        if data is None or len(data) == 0:
            return False, "No data available. Please paste and parse data first."
        try:
            arr = np.array(data)
            if arr.ndim == 2 and arr.shape[1] >= 2:
                return True, ""
            return False, "Data must have at least 2 columns (X, Y)"
        except Exception as e:
            return False, f"Invalid data: {str(e)}"
    
    def plot(self, data: Any, options: Dict[str, Any]):
        fig, ax = plt.subplots(figsize=(10, 8))
        
        arr = np.array(data)
        x = arr[:, 0]
        y = arr[:, 1]
        
        plot_type = options.get('plot_type', 'line').lower()
        color = options.get('color', 'blue')
        linewidth = options.get('linewidth', 2.0)
        marker_size = options.get('marker_size', 6.0)
        
        if plot_type == 'line':
            ax.plot(x, y, color=color, linewidth=linewidth)
        elif plot_type == 'scatter':
            ax.scatter(x, y, c=color, s=marker_size**2, edgecolors='black', linewidth=0.5)
        else:  # both
            ax.plot(x, y, color=color, linewidth=linewidth, marker='o', 
                   markersize=marker_size, markerfacecolor=color, markeredgecolor='black')
        
        ax.set_xlabel(options.get('xlabel', 'X'))
        ax.set_ylabel(options.get('ylabel', 'Y'))
        ax.grid(True, alpha=0.3)
        
        return fig
    
    def generate_tikz(self, data: Any, options: Dict[str, Any]) -> str:
        arr = np.array(data)
        x = arr[:, 0]
        y = arr[:, 1]
        
        coords = "\n".join([f"        ({x[i]:.6f},{y[i]:.6f})" for i in range(len(x))])
        
        plot_type = options.get('plot_type', 'line').lower()
        
        if plot_type == 'scatter':
            plot_options = f"only marks, mark=*, mark size={options.get('marker_size', 6.0)/2}pt,"
        elif plot_type == 'both':
            plot_options = f"mark=*, mark size={options.get('marker_size', 6.0)/2}pt,"
        else:
            plot_options = ""
        
        tikz_code = f"""\\begin{{tikzpicture}}
\\begin{{axis}}[
    xlabel={{{options.get('xlabel', 'X')}}},
    ylabel={{{options.get('ylabel', 'Y')}}},
    grid=major,
    width=12cm,
    height=8cm
]
\\addplot[
    color={options.get('color', 'blue')},
    line width={options.get('linewidth', 2.0)}pt,
    {plot_options}
] coordinates {{
{coords}
}};
\\end{{axis}}
\\end{{tikzpicture}}"""
        
        return tikz_code
