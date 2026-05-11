# ============================================================================
# FILE: plugins/barplot_plugin.py
# ============================================================================
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, 
    QPushButton, QTextEdit, QGridLayout
)
from PyQt5.QtCore import Qt
import matplotlib.pyplot as plt
import numpy as np
import json
from typing import Any, Dict, List, Tuple
from tikz_plotter_tab import PlotPlugin


class BarPlotPlugin(PlotPlugin):
    """Bar plot plugin for categorical data with multi-series support"""
    
    name = "Bar Plot"
    version = "2.0.0"
    category = "basic"
    description = "Create a bar plot for categorical data with support for multiple data sources"
    requires_custom_ui = True  # Use custom UI for sample buttons
    
    # Default color schemes for multi-series
    COLOR_SCHEMES = {
        'default': ['steelblue', 'coral', 'mediumseagreen', 'gold', 'mediumpurple'],
        'vibrant': ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8'],
        'professional': ['#2C3E50', '#E74C3C', '#3498DB', '#2ECC71', '#F39C12'],
        'pastel': ['#FFB3BA', '#BAFFC9', '#BAE1FF', '#FFFFBA', '#E0BBE4'],
        'ocean': ['#006994', '#0582CA', '#00A6FB', '#0CB0EA', '#66D9EF']
    }
    
    # Sample data definitions
    SAMPLE_1D = {
        "Category A": 25,
        "Category B": 40,
        "Category C": 30,
        "Category D": 45,
        "Category E": 35
    }
    
    SAMPLE_2D = [
        ["Jan", 100],
        ["Feb", 120],
        ["Mar", 110],
        ["Apr", 130],
        ["May", 125],
        ["Jun", 140]
    ]
    
    SAMPLE_1D_MULTI = {
        "Series A": {"Cat A": 25, "Cat B": 40, "Cat C": 30, "Cat D": 45, "Cat E": 35},
        "Series B": {"Cat A": 30, "Cat B": 35, "Cat C": 42, "Cat D": 38, "Cat E": 40},
        "Series C": {"Cat A": 20, "Cat B": 45, "Cat C": 35, "Cat D": 50, "Cat E": 32}
    }
    
    SAMPLE_2D_MULTI = [
        {
            "name": "2023",
            "data": {"Jan": 100, "Feb": 120, "Mar": 110, "Apr": 130, "May": 125, "Jun": 140}
        },
        {
            "name": "2024",
            "data": {"Jan": 115, "Feb": 135, "Mar": 125, "Apr": 145, "May": 140, "Jun": 160}
        },
        {
            "name": "2025 Target",
            "data": {"Jan": 130, "Feb": 150, "Mar": 140, "Apr": 165, "May": 155, "Jun": 180}
        }
    ]
    
    SAMPLE_MULTI_SERIES = {
        "Product A": {"Q1": 100, "Q2": 120, "Q3": 110, "Q4": 140},
        "Product B": {"Q1": 80, "Q2": 95, "Q3": 105, "Q4": 115},
        "Product C": {"Q1": 60, "Q2": 70, "Q3": 85, "Q4": 90}
    }
    
    SAMPLE_GROUPED = [
        {
            "name": "2023 Sales",
            "data": {"North": 1000, "South": 850, "East": 920, "West": 1100}
        },
        {
            "name": "2024 Sales",
            "data": {"North": 1200, "South": 950, "East": 1050, "West": 1300}
        },
        {
            "name": "2025 Target",
            "data": {"North": 1400, "South": 1100, "East": 1200, "West": 1500}
        }
    ]
    
    SAMPLE_STACKED = {
        "Hardware": {"Q1 2024": 45000, "Q2 2024": 52000, "Q3 2024": 48000, "Q4 2024": 61000},
        "Software": {"Q1 2024": 38000, "Q2 2024": 42000, "Q3 2024": 45000, "Q4 2024": 50000},
        "Services": {"Q1 2024": 22000, "Q2 2024": 25000, "Q3 2024": 28000, "Q4 2024": 32000}
    }
    
    def __init__(self):
        super().__init__()
        # Data storage
        self.current_data = None
        
        # UI references
        self.custom_ui_widget = None
        self.data_text = None
    
    def get_plugin_name(self) -> str:
        return "Bar Plot"
    
    def get_user_options(self) -> Dict[str, Dict[str, Any]]:
        return {
            "color": {
                "type": "str",
                "default": "steelblue",
                "label": "Bar Color (single series)"
            },
            "color_scheme": {
                "type": "str",
                "default": "default",
                "label": "Color Scheme (multi): default, vibrant, professional, pastel, ocean"
            },
            "edgecolor": {
                "type": "str",
                "default": "black",
                "label": "Edge Color"
            },
            "xlabel": {
                "type": "str",
                "default": "Category",
                "label": "X-axis Label"
            },
            "ylabel": {
                "type": "str",
                "default": "Value",
                "label": "Y-axis Label"
            },
            "horizontal": {
                "type": "bool",
                "default": False,
                "label": "Horizontal Bars"
            },
            "group_mode": {
                "type": "str",
                "default": "grouped",
                "label": "Multi-series Mode: grouped or stacked"
            },
            "bar_width": {
                "type": "float",
                "default": 0.8,
                "label": "Bar Width",
                "min": 0.1,
                "max": 2.0
            },
            "show_legend": {
                "type": "bool",
                "default": True,
                "label": "Show Legend"
            }
        }
    
    def create_custom_ui(self, parent):
        """Create custom UI with sample buttons and data input"""
        # Reset UI references
        self.custom_ui_widget = None
        self.data_text = None
        
        self.custom_ui_widget = QWidget(parent)
        layout = QVBoxLayout(self.custom_ui_widget)
        layout.setSpacing(8)
        
        # === SAMPLE BUTTONS ===
        samples_group = QGroupBox("Sample Data")
        samples_layout = QGridLayout(samples_group)
        
        # Row 0: Basic single series
        btn_1d = QPushButton("Sample 1D")
        btn_1d.setToolTip("Single series - Dictionary format\n5 categories")
        btn_1d.clicked.connect(lambda: self.load_sample("1d"))
        samples_layout.addWidget(btn_1d, 0, 0)
        
        btn_2d = QPushButton("Sample 2D")
        btn_2d.setToolTip("Single series - List of pairs\nMonthly sales data")
        btn_2d.clicked.connect(lambda: self.load_sample("2d"))
        samples_layout.addWidget(btn_2d, 0, 1)
        
        # Row 1: Multi-series variants
        btn_1d_multi = QPushButton("Sample 1D (m)")
        btn_1d_multi.setToolTip("Multi-series - Nested dictionary\n3 series across 5 categories")
        btn_1d_multi.clicked.connect(lambda: self.load_sample("1d_multi"))
        samples_layout.addWidget(btn_1d_multi, 1, 0)
        
        btn_2d_multi = QPushButton("Sample 2D (m)")
        btn_2d_multi.setToolTip("Multi-series - List format\n3 years of monthly data")
        btn_2d_multi.clicked.connect(lambda: self.load_sample("2d_multi"))
        samples_layout.addWidget(btn_2d_multi, 1, 1)
        
        # Row 2: Advanced samples
        btn_multi = QPushButton("Multi-Series")
        btn_multi.setToolTip("Product comparison\n3 products across 4 quarters")
        btn_multi.clicked.connect(lambda: self.load_sample("multi"))
        samples_layout.addWidget(btn_multi, 2, 0)
        
        btn_grouped = QPushButton("Grouped")
        btn_grouped.setToolTip("Regional comparison\n3 years across 4 regions")
        btn_grouped.clicked.connect(lambda: self.load_sample("grouped"))
        samples_layout.addWidget(btn_grouped, 2, 1)
        
        btn_stacked = QPushButton("Stacked")
        btn_stacked.setToolTip("Revenue breakdown\n3 categories stacked")
        btn_stacked.clicked.connect(lambda: self.load_sample("stacked"))
        samples_layout.addWidget(btn_stacked, 3, 0)
        
        layout.addWidget(samples_group)
        
        # === DATA INPUT ===
        data_group = QGroupBox("Data (JSON Format)")
        data_layout = QVBoxLayout(data_group)
        
        self.data_text = QTextEdit()
        self.data_text.setPlaceholderText("Enter data in JSON format or click a sample button above...")
        self.data_text.setMinimumHeight(200)
        data_layout.addWidget(self.data_text)
        
        # Help text
        help_label = QLabel(
            "<b>Supported formats:</b><br>"
            "• Single series dict: {\"A\": 10, \"B\": 20}<br>"
            "• Single series list: [[\"A\", 10], [\"B\", 20]]<br>"
            "• Multi-series dict: {\"Series1\": {\"A\": 10, \"B\": 20}, \"Series2\": {...}}<br>"
            "• Multi-series list: [{\"name\": \"Series1\", \"data\": {\"A\": 10, ...}}, ...]"
        )
        help_label.setWordWrap(True)
        help_label.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")
        data_layout.addWidget(help_label)
        
        layout.addWidget(data_group)
        
        # Load default sample
        self.load_sample("1d")
        
        return self.custom_ui_widget
    
    def load_sample(self, sample_type):
        """Load sample data based on type"""
        samples = {
            "1d": self.SAMPLE_1D,
            "2d": self.SAMPLE_2D,
            "1d_multi": self.SAMPLE_1D_MULTI,
            "2d_multi": self.SAMPLE_2D_MULTI,
            "multi": self.SAMPLE_MULTI_SERIES,
            "grouped": self.SAMPLE_GROUPED,
            "stacked": self.SAMPLE_STACKED
        }
        
        data = samples.get(sample_type, self.SAMPLE_1D)
        self.current_data = data
        
        # Update text display
        if self.data_text:
            formatted_json = json.dumps(data, indent=2)
            self.data_text.setPlainText(formatted_json)
    
    def get_custom_ui_data(self):
        """Get data from custom UI"""
        # Try to parse JSON from text area
        if self.data_text:
            try:
                text = self.data_text.toPlainText().strip()
                if text:
                    data = json.loads(text)
                    self.current_data = data
            except json.JSONDecodeError:
                pass  # Use current_data as fallback
        
        return self.current_data if self.current_data is not None else self.SAMPLE_1D
    
    def validate_data(self, data: Any) -> Tuple[bool, str]:
        """
        Validate data format. Supports:
        1. Single series: dict {category: value} or list of [category, value] pairs
        2. Multiple series: dict {series_name: {category: value}} or list of dicts
        """
        try:
            if data is None:
                return False, "Data is None"
            
            # Single series - dict format
            if isinstance(data, dict):
                if len(data) == 0:
                    return False, "Data dictionary is empty"
                
                # Check if it's single series (values are numbers)
                if all(isinstance(v, (int, float)) for v in data.values()):
                    return True, ""
                # Check if it's multi-series (values are dicts)
                if all(isinstance(v, dict) for v in data.values()):
                    # Validate nested dicts have numeric values
                    for series_data in data.values():
                        if not all(isinstance(v, (int, float)) for v in series_data.values()):
                            return False, "Multi-series data must contain numeric values"
                    return True, ""
                # Mixed types
                return False, "Dictionary values must be either all numbers (single series) or all dicts (multi-series)"
            
            # Single series - list of pairs
            if isinstance(data, list):
                if len(data) == 0:
                    return False, "Data list is empty"
                
                # Check for list of [category, value] pairs
                if all(isinstance(x, (list, tuple)) and len(x) == 2 for x in data):
                    # Validate values are numeric
                    if not all(isinstance(x[1], (int, float)) for x in data):
                        return False, "Values in [category, value] pairs must be numeric"
                    return True, ""
                
                # Multi-series - list of dicts with 'name' and 'data'
                if all(isinstance(x, dict) and 'name' in x and 'data' in x for x in data):
                    # Validate nested data
                    for item in data:
                        if not isinstance(item['data'], dict):
                            return False, "Multi-series 'data' field must be a dictionary"
                        if not all(isinstance(v, (int, float)) for v in item['data'].values()):
                            return False, "Multi-series data values must be numeric"
                    return True, ""
                
                return False, "List must contain [category, value] pairs or {'name': ..., 'data': {...}} dicts"
            
            return False, "Data must be dict {category: value}, list of [category, value] pairs, " \
                         "or multi-series format: dict {series: {category: value}} or " \
                         "list of {'name': series_name, 'data': {category: value}}"
        except Exception as e:
            return False, f"Invalid data format: {str(e)}"
    
    def _is_multi_series(self, data: Any) -> bool:
        """Check if data contains multiple series"""
        if isinstance(data, dict):
            return any(isinstance(v, dict) for v in data.values())
        if isinstance(data, list):
            if len(data) > 0:
                return all(isinstance(x, dict) and 'name' in x and 'data' in x for x in data)
        return False
    
    def _get_colors(self, options: Dict[str, Any], n_series: int, is_multi: bool) -> List[str]:
        """Get color list based on options"""
        if is_multi:
            scheme_name = options.get('color_scheme', 'default')
            colors = self.COLOR_SCHEMES.get(scheme_name, self.COLOR_SCHEMES['default']).copy()
            while len(colors) < n_series:
                colors.extend(colors)
            return colors[:n_series]
        else:
            return [options.get('color', 'steelblue')]
    
    def _parse_data(self, data: Any) -> Tuple[List[str], Dict[str, List[float]]]:
        """
        Parse data into categories and series.
        Returns: (categories, {series_name: [values]})
        """
        if self._is_multi_series(data):
            if isinstance(data, dict):
                # Format: {series_name: {category: value}}
                all_categories = set()
                for series_data in data.values():
                    if isinstance(series_data, dict):
                        all_categories.update(series_data.keys())
                categories = sorted(list(all_categories))
                
                series = {}
                for series_name, series_data in data.items():
                    if isinstance(series_data, dict):
                        series[str(series_name)] = [series_data.get(cat, 0) for cat in categories]
                
                return categories, series
            else:
                # Format: [{'name': series_name, 'data': {category: value}}]
                all_categories = set()
                for item in data:
                    all_categories.update(item['data'].keys())
                categories = sorted(list(all_categories))
                
                series = {}
                for item in data:
                    series[item['name']] = [item['data'].get(cat, 0) for cat in categories]
                
                return categories, series
        else:
            # Single series
            if isinstance(data, dict):
                categories = list(data.keys())
                values = list(data.values())
            else:
                categories = [str(x[0]) for x in data]
                values = [x[1] for x in data]
            
            return categories, {"Data": values}
    
    def plot(self, data: Any, options: Dict[str, Any]):
        fig, ax = plt.subplots(figsize=(10, 8))
        
        categories, series = self._parse_data(data)
        n_series = len(series)
        is_multi = n_series > 1
        
        # Get colors
        colors = self._get_colors(options, n_series, is_multi)
        
        edgecolor = options.get('edgecolor', 'black')
        bar_width = options.get('bar_width', 0.8)
        horizontal = options.get('horizontal', False)
        group_mode = options.get('group_mode', 'grouped')
        
        if horizontal:
            y_pos = np.arange(len(categories))
            
            if is_multi and group_mode == 'grouped':
                bar_height = bar_width / n_series
                for i, (series_name, values) in enumerate(series.items()):
                    offset = (i - n_series/2 + 0.5) * bar_height
                    ax.barh(y_pos + offset, values, bar_height,
                           label=series_name, color=colors[i], edgecolor=edgecolor)
            elif is_multi and group_mode == 'stacked':
                left = np.zeros(len(categories))
                for i, (series_name, values) in enumerate(series.items()):
                    ax.barh(y_pos, values, bar_width, left=left,
                           label=series_name, color=colors[i], edgecolor=edgecolor)
                    left += np.array(values)
            else:
                values = list(series.values())[0]
                ax.barh(y_pos, values, bar_width,
                       color=colors[0], edgecolor=edgecolor)
            
            ax.set_yticks(y_pos)
            ax.set_yticklabels(categories)
            ax.set_xlabel(options.get('ylabel', 'Value'))
            ax.set_ylabel(options.get('xlabel', 'Category'))
            ax.grid(True, alpha=0.3, axis='x')
        else:
            x_pos = np.arange(len(categories))
            
            if is_multi and group_mode == 'grouped':
                bar_width_adj = bar_width / n_series
                for i, (series_name, values) in enumerate(series.items()):
                    offset = (i - n_series/2 + 0.5) * bar_width_adj
                    ax.bar(x_pos + offset, values, bar_width_adj,
                          label=series_name, color=colors[i], edgecolor=edgecolor)
            elif is_multi and group_mode == 'stacked':
                bottom = np.zeros(len(categories))
                for i, (series_name, values) in enumerate(series.items()):
                    ax.bar(x_pos, values, bar_width, bottom=bottom,
                          label=series_name, color=colors[i], edgecolor=edgecolor)
                    bottom += np.array(values)
            else:
                values = list(series.values())[0]
                ax.bar(x_pos, values, bar_width,
                      color=colors[0], edgecolor=edgecolor)
            
            ax.set_xticks(x_pos)
            ax.set_xticklabels(categories, rotation=45, ha='right')
            ax.set_xlabel(options.get('xlabel', 'Category'))
            ax.set_ylabel(options.get('ylabel', 'Value'))
            ax.grid(True, alpha=0.3, axis='y')
        
        # Add legend for multi-series
        if is_multi and options.get('show_legend', True):
            ax.legend(loc='best')
        
        plt.tight_layout()
        return fig
    
    def generate_tikz(self, data: Any, options: Dict[str, Any]) -> str:
        categories, series = self._parse_data(data)
        n_series = len(series)
        is_multi = n_series > 1
        
        # Get colors (simplified for TikZ)
        if is_multi:
            colors = ['blue', 'red', 'green', 'orange', 'purple', 'cyan', 'magenta']
            while len(colors) < n_series:
                colors.extend(colors)
            colors = colors[:n_series]
        else:
            color_map = {
                'steelblue': 'blue',
                'coral': 'red!70!yellow',
                'mediumseagreen': 'green!70!black'
            }
            single_color = options.get('color', 'blue')
            colors = [color_map.get(single_color, single_color)]
        
        bar_dir = "xbar" if options.get('horizontal', False) else "ybar"
        group_mode = options.get('group_mode', 'grouped')
        
        # Build plot commands
        plot_commands = []
        for i, (series_name, values) in enumerate(series.items()):
            coords = "\n".join([f"        ({cat},{val})" for cat, val in zip(categories, values)])
            legend_entry = f"\\addlegendentry{{{series_name}}}" if is_multi else ""
            
            plot_commands.append(f"""\\addplot[
    fill={colors[i]},
    draw={options.get('edgecolor', 'black')}
] coordinates {{
{coords}
}};
{legend_entry}""")
        
        tikz_code = f"""\\begin{{tikzpicture}}
\\begin{{axis}}[
    {bar_dir},
    bar width=15pt,
    xlabel={{{options.get('xlabel', 'Category')}}},
    ylabel={{{options.get('ylabel', 'Value')}}},
    symbolic x coords={{{','.join(categories)}}},
    xtick=data,
    x tick label style={{rotate=45, anchor=east}},
    grid=major,
    width=12cm,
    height=8cm,
    {"legend pos=north west," if is_multi else ""}
    {"ybar" if group_mode == 'grouped' and not options.get('horizontal') else ""}
]
{chr(10).join(plot_commands)}
\\end{{axis}}
\\end{{tikzpicture}}"""
        return tikz_code
    
    def get_tikz_libraries(self) -> List[str]:
        return ["pgfplots"]