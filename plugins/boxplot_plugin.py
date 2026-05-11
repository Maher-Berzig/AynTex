# ============================================================================
# FILE: plugins/boxplot_plugin.py
# ============================================================================

import matplotlib.pyplot as plt
import numpy as np
from typing import Any, Dict, List, Tuple
from tikz_plotter_tab import PlotPlugin


class BoxPlotPlugin(PlotPlugin):
    """Box plot plugin for statistical visualization"""
    
    name = "Box Plot"
    version = "1.0.0"
    category = "statistical"
    description = "Create a box plot for statistical analysis"
    
    def get_plugin_name(self) -> str:
        return "Box Plot"
    
    def get_user_options(self) -> Dict[str, Dict[str, Any]]:
        return {
            "color": {
                "type": "str",
                "default": "lightblue",
                "label": "Box Color"
            },
            "show_outliers": {
                "type": "bool",
                "default": True,
                "label": "Show Outliers"
            },
            "show_means": {
                "type": "bool",
                "default": False,
                "label": "Show Mean"
            },
            "xlabel": {
                "type": "str",
                "default": "Group",
                "label": "X-axis Label"
            },
            "ylabel": {
                "type": "str",
                "default": "Value",
                "label": "Y-axis Label"
            },
            "notch": {
                "type": "bool",
                "default": False,
                "label": "Notched Boxes"
            }
        }
    
    def validate_data(self, data: Any) -> Tuple[bool, str]:
        try:
            if isinstance(data, dict):
                for v in data.values():
                    arr = np.array(v)
                    if arr.ndim != 1:
                        return False, "Each group must be a 1D array"
                return True, ""
            if isinstance(data, list):
                arr = np.array(data)
                if arr.ndim == 1 or arr.ndim == 2:
                    return True, ""
            return False, "Data must be dict {group: values} or list/2D array"
        except Exception:
            return False, "Invalid data format"
    
    def plot(self, data: Any, options: Dict[str, Any]):
        fig, ax = plt.subplots(figsize=(10, 8))
        
        if isinstance(data, dict):
            labels = list(data.keys())
            plot_data = [data[k] for k in labels]
        else:
            arr = np.array(data)
            if arr.ndim == 1:
                labels = ['Data']
                plot_data = [arr]
            else:
                labels = [f'Group {i+1}' for i in range(arr.shape[1])]
                plot_data = [arr[:, i] for i in range(arr.shape[1])]
        
        bp = ax.boxplot(plot_data, labels=labels, 
                        patch_artist=True,
                        notch=options.get('notch', False),
                        showfliers=options.get('show_outliers', True),
                        showmeans=options.get('show_means', False))
        
        for patch in bp['boxes']:
            patch.set_facecolor(options.get('color', 'lightblue'))
        
        ax.set_xlabel(options.get('xlabel', 'Group'))
        ax.set_ylabel(options.get('ylabel', 'Value'))
        ax.grid(True, alpha=0.3, axis='y')
        
        return fig
    
    def generate_tikz(self, data: Any, options: Dict[str, Any]) -> str:
        if isinstance(data, dict):
            labels = list(data.keys())
            all_data = [np.array(data[k]) for k in labels]
        else:
            arr = np.array(data)
            if arr.ndim == 1:
                labels = ['Data']
                all_data = [arr]
            else:
                labels = [f'Group {i+1}' for i in range(arr.shape[1])]
                all_data = [arr[:, i] for i in range(arr.shape[1])]
        
        box_plots = []
        for i, (label, d) in enumerate(zip(labels, all_data)):
            q1, median, q3 = np.percentile(d, [25, 50, 75])
            iqr = q3 - q1
            lower_whisker = max(d.min(), q1 - 1.5 * iqr)
            upper_whisker = min(d.max(), q3 + 1.5 * iqr)
            
            box_plots.append(f"""\\addplot+[
    boxplot prepared={{
        median={median:.3f},
        upper quartile={q3:.3f},
        lower quartile={q1:.3f},
        upper whisker={upper_whisker:.3f},
        lower whisker={lower_whisker:.3f}
    }},
] coordinates {{}};""")
        
        box_plots_str = "\n".join(box_plots)
        
        tikz_code = f"""\\begin{{tikzpicture}}
\\begin{{axis}}[
    boxplot/draw direction=y,
    xlabel={{{options.get('xlabel', 'Group')}}},
    ylabel={{{options.get('ylabel', 'Value')}}},
    xtick={{{','.join(str(i+1) for i in range(len(labels)))}}},
    xticklabels={{{','.join(labels)}}},
    width=12cm,
    height=8cm
]
{box_plots_str}
\\end{{axis}}
\\end{{tikzpicture}}"""
        
        return tikz_code