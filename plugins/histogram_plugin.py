# ============================================================================
# FILE: plugins/histogram_plugin.py
# ============================================================================

import matplotlib.pyplot as plt
import numpy as np
from typing import Any, Dict, List, Tuple
from tikz_plotter_tab import PlotPlugin


class HistogramPlugin(PlotPlugin):
    """Histogram plugin"""
    
    name = "Histogram"
    version = "1.0.0"
    category = "statistical"
    description = "Create a histogram"
    
    def get_plugin_name(self) -> str:
        return "Histogram"
    
    def get_user_options(self) -> Dict[str, Dict[str, Any]]:
        return {
            "bins": {
                "type": "int",
                "default": 10,
                "label": "Number of Bins",
                "min": 5,
                "max": 100
            },
            "color": {
                "type": "str",
                "default": "steelblue",
                "label": "Bar Color"
            },
            "xlabel": {
                "type": "str",
                "default": "Value",
                "label": "X-axis Label"
            },
            "ylabel": {
                "type": "str",
                "default": "Frequency",
                "label": "Y-axis Label"
            }
        }
    
    def validate_data(self, data: Any) -> Tuple[bool, str]:
        try:
            arr = np.array(data)
            if arr.ndim == 1:
                return True, ""
            return False, "Data must be 1D array"
        except Exception:
            return False, "Invalid data format"
    
    def plot(self, data: Any, options: Dict[str, Any]):
        fig, ax = plt.subplots(figsize=(10, 8))
        
        arr = np.array(data)
        ax.hist(arr, bins=options.get('bins', 10), 
                color=options.get('color', 'steelblue'),
                edgecolor='black', alpha=0.7)
        
        ax.set_xlabel(options.get('xlabel', 'Value'))
        ax.set_ylabel(options.get('ylabel', 'Frequency'))
        ax.grid(True, alpha=0.3, axis='y')
        
        return fig
    
    def generate_tikz(self, data: Any, options: Dict[str, Any]) -> str:
        arr = np.array(data)
        bins = options.get('bins', 10)
        
        # Calculate histogram
        counts, bin_edges = np.histogram(arr, bins=bins)
        
        # Generate coordinates for bar chart
        coords = []
        for i in range(len(counts)):
            bin_center = (bin_edges[i] + bin_edges[i+1]) / 2
            coords.append(f"        ({bin_center:.3f},{counts[i]})")
        
        coords_str = "\n".join(coords)
        
        tikz_code = f"""\\begin{{tikzpicture}}
\\begin{{axis}}[
    ybar,
    bar width=15pt,
    xlabel={{{options.get('xlabel', 'Value')}}},
    ylabel={{{options.get('ylabel', 'Frequency')}}},
    grid=major,
    width=10cm,
    height=8cm,
    ymajorgrids=true
]
\\addplot[
    fill={options.get('color', 'blue')},
    draw=black
] coordinates {{
{coords_str}
}};
\\end{{axis}}
\\end{{tikzpicture}}"""
        
        return tikz_code