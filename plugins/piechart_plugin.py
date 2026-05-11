# ============================================================================
# FILE: plugins/piechart_plugin.py
# ============================================================================

import matplotlib.pyplot as plt
from typing import Any, Dict, List, Tuple
from tikz_plotter_tab import PlotPlugin


class PieChartPlugin(PlotPlugin):
    """Pie chart plugin"""
    
    name = "Pie Chart"
    version = "1.0.0"
    category = "basic"
    description = "Create a pie chart"
    
    def get_plugin_name(self) -> str:
        return "Pie Chart"
    
    def get_user_options(self) -> Dict[str, Dict[str, Any]]:
        return {
            "explode": {
                "type": "float",
                "default": 0.0,
                "label": "Explode Factor",
                "min": 0.0,
                "max": 0.5
            },
            "show_percentages": {
                "type": "bool",
                "default": True,
                "label": "Show Percentages"
            },
            "shadow": {
                "type": "bool",
                "default": False,
                "label": "Show Shadow"
            },
            "startangle": {
                "type": "int",
                "default": 90,
                "label": "Start Angle",
                "min": 0,
                "max": 360
            }
        }
    
    def validate_data(self, data: Any) -> Tuple[bool, str]:
        try:
            if isinstance(data, dict):
                if all(isinstance(v, (int, float)) and v >= 0 for v in data.values()):
                    return True, ""
            return False, "Data must be dict {label: value} with non-negative values"
        except Exception:
            return False, "Invalid data format"
    
    def plot(self, data: Any, options: Dict[str, Any]):
        fig, ax = plt.subplots(figsize=(10, 8))
        
        labels = list(data.keys())
        sizes = list(data.values())
        
        explode_val = options.get('explode', 0.0)
        explode = [explode_val] * len(labels)
        
        autopct = '%1.1f%%' if options.get('show_percentages', True) else None
        
        ax.pie(sizes, explode=explode, labels=labels, autopct=autopct,
               shadow=options.get('shadow', False),
               startangle=options.get('startangle', 90))
        ax.axis('equal')
        
        return fig
    
    def generate_tikz(self, data: Any, options: Dict[str, Any]) -> str:
        labels = list(data.keys())
        sizes = list(data.values())
        total = sum(sizes)
        
        colors = ['red', 'blue', 'green', 'orange', 'purple', 'cyan', 'magenta', 'yellow']
        
        slices = []
        for i, (label, size) in enumerate(zip(labels, sizes)):
            percentage = (size / total) * 100
            color = colors[i % len(colors)]
            if options.get('show_percentages', True):
                slices.append(f"    {percentage:.1f}/{label} ({percentage:.1f}\\%)/{color}")
            else:
                slices.append(f"    {percentage:.1f}/{label}/{color}")
        
        slices_str = ",\n".join(slices)
        
        tikz_code = f"""\\begin{{tikzpicture}}
\\pie[
    text=legend,
    radius=3,
    rotate={options.get('startangle', 90)}
]{{
{slices_str}
}}
\\end{{tikzpicture}}"""
        
        return tikz_code
    
    def get_tikz_libraries(self) -> List[str]:
        return ["pgfplots", "pgf-pie"]