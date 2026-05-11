# ============================================================================
# FILE: plugins/lineplot_plugin.py
# ============================================================================
import matplotlib.pyplot as plt
import numpy as np
from typing import Any, Dict, List, Tuple
from tikz_plotter_tab import PlotPlugin


class LinePlotPlugin(PlotPlugin):
    """Simple line plot plugin"""
    
    name = "Line Plot"
    version = "1.0.0"
    category = "basic"
    description = "Create a simple line plot"
    
    def get_plugin_name(self) -> str:
        return "Line Plot"
    
    def get_user_options(self) -> Dict[str, Dict[str, Any]]:
        return {
            "color": {
                "type": "str",
                "default": "blue",
                "label": "Line Color"
            },
            "linewidth": {
                "type": "float",
                "default": 2.0,
                "label": "Line Width",
                "min": 0.5,
                "max": 10.0
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
            },
            "markers": {
                "type": "bool",
                "default": False,
                "label": "Show Markers"
            }
        }
    
    def validate_data(self, data: Any) -> Tuple[bool, str]:
        try:
            arr = np.array(data)
            if arr.ndim == 1:
                return True, ""
            elif arr.ndim == 2 and arr.shape[1] == 2:
                return True, ""
            return False, "Data must be 1D or 2D array with 2 columns"
        except Exception:
            return False, "Invalid data format"
    
    def plot(self, data: Any, options: Dict[str, Any]):
        fig, ax = plt.subplots(figsize=(10, 8))
        
        arr = np.array(data)
        if arr.ndim == 1:
            x = np.arange(len(arr))
            y = arr
        else:
            x = arr[:, 0]
            y = arr[:, 1]
        
        marker = 'o' if options.get('markers', False) else ''
        ax.plot(x, y, color=options.get('color', 'blue'), 
                linewidth=options.get('linewidth', 2.0),
                marker=marker, markersize=4)
        
        ax.set_xlabel(options.get('xlabel', 'x'))
        ax.set_ylabel(options.get('ylabel', 'y'))
        ax.grid(True, alpha=0.3)
        
        return fig
    
    def generate_tikz(self, data: Any, options: Dict[str, Any]) -> str:
        arr = np.array(data)
        if arr.ndim == 1:
            x = np.arange(len(arr))
            y = arr
        else:
            x = arr[:, 0]
            y = arr[:, 1]
        
        # Generate coordinate pairs
        coords = "\n".join([f"        ({x[i]:.3f},{y[i]:.3f})" for i in range(len(x))])
        
        marker_str = "mark=*,mark size=1pt," if options.get('markers', False) else ""
        
        tikz_code = f"""\\begin{{tikzpicture}}
\\begin{{axis}}[
    xlabel={{{options.get('xlabel', 'x')}}},
    ylabel={{{options.get('ylabel', 'y')}}},
    grid=major,
    width=10cm,
    height=8cm
]
\\addplot[
    color={options.get('color', 'blue')},
    line width={options.get('linewidth', 2.0)}pt,
    {marker_str}
] coordinates {{
{coords}
}};
\\end{{axis}}
\\end{{tikzpicture}}"""
        
        return tikz_code
