# katex_loader.py (flat structure)
import os

def load_katex_inline():
    base_dir = os.path.dirname(__file__)
    katex_dir = os.path.join(base_dir, 'katex')
    katex_sub_dir = os.path.join(katex_dir, 'contrib')

    css_path = os.path.join(katex_dir, 'katex.min.css')
    js_path = os.path.join(katex_dir, 'katex.min.js')
    autorender_path = os.path.join(katex_sub_dir, 'auto-render.min.js')

    missing = []
    if not os.path.exists(css_path):
        missing.append(f"CSS: {css_path}")
    if not os.path.exists(js_path):
        missing.append(f"JS: {js_path}")
    if not os.path.exists(autorender_path):
        missing.append(f"Auto-render: {autorender_path}")

    if missing:
        raise FileNotFoundError(f"Missing KaTeX files:\n" + "\n".join(missing))

    with open(css_path, 'r', encoding='utf-8') as f:
        css_content = f.read()
    with open(js_path, 'r', encoding='utf-8') as f:
        js_content = f.read()
    with open(autorender_path, 'r', encoding='utf-8') as f:
        autorender_content = f.read()

    return css_content, js_content, autorender_content