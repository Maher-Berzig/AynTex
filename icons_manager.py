# icons_manager.py
"""
Icons Manager - Enhanced icon management with fallback support
Handles icon loading with configuration-aware themes
"""

import os
import re
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QBrush, QPen, QFont
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtWidgets import QStyle
from PyQt5.QtSvg import QSvgRenderer

#symbol_colors = ["#1976d2", "#f57c00", "#7b1fa2", "#388e3c", "#d32f2f"]
#command_colors = ["#7b1fa2", "#388e3c", "#d32f2f", "#f57c00", "#1976d2"]
class IconsManager:
    """
    Complete unified icons manager supporting:
    - UI icons (toolbars, menus)
    - Math symbols (300+ LaTeX symbols)
    - LaTeX commands (100+ commands)
    With priority loading: .svg -> .png -> .ico
    """
    
    def __init__(self, icons_folder="icons"):
        self.icons_folder = icons_folder
        self.icon_cache = {}
        self.icon_directories = [
            icons_folder,
            "icons",
            "assets/icons",
            "resources/icons",
            os.path.join(os.path.dirname(__file__), "icons")
        ]
        
        # UI icon mapping (unchanged from original)
        self.icon_map = {
            "new": ["new.svg", "new.png", "new.ico"],
            "open": ["open.svg", "open.png", "open.ico"],
            "save": ["save.svg", "save.png", "save.ico"],
            "save_all": ["save_all.svg", "save_all.png", "save_all.ico"],
            "save_as": ["save_as.svg", "save_as.png", "save_as.ico"],
            "close_tex": ["close_tex.svg", "close_tex.png", "close_tex.ico"],
            "close_all_tex": ["close_all_tex.svg", "close_all_tex.png", "close_all_tex.ico"],
            "close_pdf": ["close_pdf.svg", "close_pdf.png", "close_pdf.ico"],
            "close_all_pdf": ["close_all_pdf.svg", "close_all_pdf.png", "close_all_pdf.ico"],
            "find": ["find.svg", "find.png", "find.ico"],
            "pdf": ["pdf.svg", "pdf.png", "pdf.ico"],
            "exit": ["exit.svg", "exit.png", "exit.ico"],
            "undo": ["undo.svg", "undo.png", "undo.ico"],
            "redo": ["redo.svg", "redo.png", "redo.ico"],
            "cut": ["cut.svg", "cut.png", "cut.ico"],
            "copy": ["copy.svg", "copy.png", "copy.ico"],
            "copy_s": ["copy_s.svg", "copy_s.png", "copy_s.ico"],
            "copy_p": ["copy_p.svg", "copy_p.png", "copy_p.ico"],
            "paste": ["paste.svg", "paste.png", "paste.ico"],
            "checked": ["checked.svg", "checked.png", "checked.ico"],
            "unchecked": ["unchecked.svg", "unchecked.png", "unchecked.ico"],
            "side_panel": ["side_panel.svg", "side_panel.png", "side_panel.ico"],
            "jump_in_pdf": ["jump_in_pdf.svg", "jump_in_pdf.png", "jump_in_pdf.ico"],
            "compile": ["compile.svg", "compile.png", "compile.ico"],
            "backmatter_compile": ["backmatter_compile.svg", "backmatter_compile.png", "backmatter_compile.ico"],
            "stop": ["stop.svg", "stop.png", "stop.ico"],
            "refresh": ["refresh.svg", "refresh.png", "refresh.ico"],
            "switch_layout": ["switch.svg", "switch.png", "switch.ico"],
            "toggle_layout": ["toggle.svg", "toggle.png", "toggle.ico"],
            "editor_layout": ["tex.svg", "tex.png", "tex.ico"],
            "direction": ["direction.svg", "direction.png", "direction.ico"],
            "bilingual": ["bilingual.svg", "bilingual.png", "bilingual.ico"],
            #"direction_rl": ["direction_rl.svg", "direction_rl.png", "direction_rl.ico"],
            "pdf_layout": ["pdf_layout.svg", "pdf_layout.png", "pdf_layout.ico"],
            "hide_output": ["hide.svg", "hide.png", "hide.ico"],
            "show_output": ["show.svg", "show.png", "show.ico"],
            "switch_side_panel": ["switch_side_panel.svg", "switch_side_panel.png", "switch_side_panel.ico"],            
            "settings": ["settings.svg", "settings.png", "settings.ico"],
            "language": ["language.svg", "language.png", "language.ico"],
            "help": ["help.svg", "help.png", "help.ico"],
            "arabic": ["arabic.svg", "arabic.png", "arabic.ico"],
            "symbols": ["symbols.svg", "symbols.png", "symbols.ico"],
            "latex_commands": ["latex_commands.svg", "latex_commands.png", "latex_commands.ico"],
            "first_page_btn": ["first_page_btn.svg", "first_page_btn.png", "first_page_btn.ico"],
            "last_page_btn": ["last_page_btn.svg", "last_page_btn.png", "last_page_btn.ico"],
            "prev_page_btn":["prev_page_btn.svg", "prev_page_btn.png", "prev_page_btn.ico"],
            "next_page_btn":["next_page_btn.svg", "next_page_btn.png", "next_page_btn.ico"],
            "zoom_in": ["zoom_in.svg", "zoom_in.png", "zoom_in.ico"],
            "zoom_out": ["zoom_out.svg", "zoom_out.png", "zoom_out.ico"],
            "select_text": ["select_text.svg", "select_text.png", "select_text.ico"],
            "select_t": ["select_t.svg", "select_t.png", "select_t.ico"],
            "select_p": ["select_p.svg", "select_p.png", "select_p.ico"],
            "fit_width": ["fit_width.svg", "fit_width.png", "fit_width.ico"],
            "fit_text_width": ["fit_text_width.svg", "fit_text_width.png", "fit_text_width.ico"],
            "fit_page": ["fit_page.svg", "fit_page.png", "fit_page.ico"],
            "print_pdf": ["print_pdf.svg", "print_pdf.png", "print_pdf.ico"],
            "open_external": ["open_external.svg", "open_external.png", "open_external.ico"],
            "back_nav": ["back_nav.svg", "back_nav.png", "back_nav.ico"],
            "forward_nav": ["forward_nav.svg", "forward_nav.png", "forward_nav.ico"],
            "tooltip_toggle": ["tooltip_toggle.svg","tooltip_toggle.png", "tooltip_toggle.ico"],
            "annotations":["annotations.svg", "annotations.png", "annotations.ico"],
            "reverse": ["reverse.svg", "reverse.png", "reverse.ico"],
            "expand_width": ["expand_width.svg", "expand_width.png", "expand_width.ico"],
            "collapse_width": ["collapse_width.svg", "collapse_width.png", "collapse_width.ico"],
            "search": ["search.svg", "search.png", "search.ico"],
            "eraser": ["eraser.svg", "eraser.png", "eraser.ico"],
            "clear_page": ["clear_page.svg", "clear_page.png", "clear_page.ico"],
            "tree": ["tree.svg", "tree.png", "tree.ico"],
            "bookmarks": ["bookmarks.svg", "bookmarks.png", "bookmarks.ico"],
            "terminal": ["terminal.svg", "terminal.png", "terminal.ico"],
            "replace": ["replace.svg", "replace.png", "replace.ico"],
            "help": ["ayntexlogo.svg"],
        }
        
        # Symbol and command mappings (LaTeX code -> filename base)
        self.symbol_mappings = {}
        self.command_mappings = {}
        self.symbol_icons = {}
        self.command_icons = {}
        
        # Ensure icons folder exists
        if not os.path.exists(self.icons_folder):
            os.makedirs(self.icons_folder)
        
        # Load all symbol and command mappings
        self._initialize_symbol_mappings()
        self._initialize_command_mappings()
        self._load_all_symbol_icons()
        self._load_all_command_icons()
    
    # ==================== UI ICONS ====================   
    def get_icon_path(self, icon_name):
        """Get the full path to an icon file with priority: svg -> png -> ico"""
        if icon_name in self.icon_map:
            icon_variants = self.icon_map[icon_name]
            for directory in self.icon_directories:
                if os.path.exists(directory):
                    for variant in icon_variants:
                        icon_path = os.path.join(directory, variant)
                        if os.path.exists(icon_path):
                            return icon_path
        return None
    
    def load_icon(self, icon_name, size=None):
        """Load a UI icon by name with caching and size support"""
        cache_key = f"ui_{icon_name}_{size}" if size else f"ui_{icon_name}"
        
        if cache_key in self.icon_cache:
            return self.icon_cache[cache_key]
        
        icon = None
        icon_path = self.get_icon_path(icon_name)
        
        if icon_path:
            icon = QIcon(icon_path)
            if size and not icon.isNull():
                pixmap = icon.pixmap(size, size)
                icon = QIcon(pixmap)
        
        # Fallback to system theme icons
        if not icon or icon.isNull():
            if icon_name in self.icon_map:
                for variant in reversed(self.icon_map[icon_name]):
                    if variant.count('-') > 0:
                        theme_icon = QIcon.fromTheme(variant)
                        if not theme_icon.isNull():
                            icon = theme_icon
                            break
        
        # Final fallback
        if not icon or icon.isNull():
            icon = self.create_fallback_icon(icon_name, size or 16)
        
        self.icon_cache[cache_key] = icon
        return icon
    
    def create_fallback_icon(self, icon_name, size=16):
        """Create a simple fallback icon when no file is found"""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        try: 
            rect = pixmap.rect().adjusted(2, 2, -2, -2)
            if icon_name in ["new", "open", "save", "save_as"]:
                painter.setBrush(QBrush(Qt.white))
                painter.setPen(QPen(Qt.black, 1))
                rect = pixmap.rect().adjusted(2, 2, -2, -2)
                painter.drawRect(rect)
                if icon_name == "new":
                    painter.drawLine(rect.left() + 3, rect.center().y(), rect.right() - 3, rect.center().y())
                    painter.drawLine(rect.center().x(), rect.top() + 3, rect.center().x(), rect.bottom() - 3)
            elif icon_name in ["compile", "refresh"]:
                painter.setBrush(QBrush(Qt.green))
                painter.setPen(QPen(Qt.darkGreen, 1))
                from PyQt5.QtGui import QPolygon
                from PyQt5.QtCore import QPoint
                points = [(size//4, size//4), (3*size//4, size//2), (size//4, 3*size//4)]
                polygon = QPolygon([QPoint(x, y) for x, y in points])
                painter.drawPolygon(polygon)
            elif icon_name == "stop":
                painter.setBrush(QBrush(Qt.red))
                painter.setPen(QPen(Qt.darkRed, 1))
                rect = pixmap.rect().adjusted(4, 4, -4, -4)
                painter.drawRect(rect)
            # ---------- TEXT FORMATTING ----------
            elif icon_name == "bold":
                font = QFont()
                font.setBold(True)
                font.setPointSize(int(size * 0.6))
                painter.setFont(font)
                painter.drawText(rect, Qt.AlignCenter, "B")

            elif icon_name == "italic":
                font = QFont()
                font.setItalic(True)
                font.setPointSize(int(size * 0.6))
                painter.setFont(font)
                painter.drawText(rect, Qt.AlignCenter, "I")

            elif icon_name == "underline":
                font = QFont()
                font.setUnderline(True)
                font.setPointSize(int(size * 0.6))
                painter.setFont(font)
                painter.drawText(rect, Qt.AlignCenter, "U")

            elif icon_name == "code":
                painter.setPen(QPen(Qt.darkGray, 1))
                painter.drawRect(rect)
                painter.drawText(rect, Qt.AlignCenter, "{}")

            elif icon_name == "format":
                painter.drawText(rect, Qt.AlignCenter, "Aa")

            # ---------- COLORS ----------
            elif icon_name.startswith("color_"):
                color_map = {
                    "color_red": Qt.red,
                    "color_blue": Qt.blue,
                    "color_green": Qt.green,
                    "color_magenta": Qt.magenta,
                    "color_cyan": Qt.cyan,
                }
                painter.setBrush(QBrush(color_map.get(icon_name, Qt.gray)))
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(rect.center(), size // 3, size // 3)
            # ---------- ALIGN ----------
            elif icon_name.startswith("align_"):
                painter.setPen(QPen(Qt.black, 2))

                y_step = rect.height() // 4
                line_lengths = [0.6, 0.8, 0.5]  # varying lengths for realism

                for i, factor in enumerate(line_lengths):
                    y = rect.top() + (i + 1) * y_step
                    line_width = int(rect.width() * factor)

                    if icon_name == "align_left":
                        x_start = rect.left()
                        x_end = rect.left() + line_width

                    elif icon_name == "align_center":
                        x_start = rect.center().x() - line_width // 2
                        x_end = rect.center().x() + line_width // 2

                    elif icon_name == "align_right":
                        x_start = rect.right() - line_width
                        x_end = rect.right()

                    else:
                        continue

                    painter.drawLine(x_start, y, x_end, y)
            # ---------- MATH ----------
            elif icon_name == "math_inline":
                painter.drawText(rect, Qt.AlignCenter, "⍺")

            elif icon_name == "math":
                painter.drawText(rect, Qt.AlignCenter, "∑")


            elif icon_name == "fraction":
                painter.drawText(rect, Qt.AlignCenter, "½")

            elif icon_name == "sqrt":
                painter.drawText(rect, Qt.AlignCenter, "√")

            elif icon_name == "superscript":
                painter.drawText(rect, Qt.AlignCenter, "x²")

            elif icon_name == "subscript":
                painter.drawText(rect, Qt.AlignCenter, "x₂")


            # ---------- FONT SIZE ----------
            elif icon_name.startswith("font_"):
                # Map icon to relative scale
                scale_map = {
                    "font_tiny": 0.35,
                    "font_small": 0.5,
                    "font_normal": 0.65,
                    "font_large": 0.8,
                    "font_huge": 1.0,
                }

                scale = scale_map.get(icon_name, 0.65)

                font = QFont()
                font.setBold(True)
                font.setPointSizeF(rect.height() * scale)

                painter.setFont(font)
                painter.setPen(Qt.black)

                painter.drawText(rect, Qt.AlignCenter, "A")

            # ---------- LIST ----------
            elif icon_name == "list_itemize":
                painter.setPen(QPen(Qt.black, 1))
                painter.setBrush(Qt.black)

                y_step = rect.height() // 4

                for i in range(3):
                    y = rect.top() + (i + 1) * y_step

                    # Bullet
                    painter.drawEllipse(rect.left(), y - 2, 2, 2)

                    # Line
                    painter.drawLine(rect.left() + 6, y, rect.right()+10, y)


            elif icon_name == "list_enumerate":
                painter.setPen(QPen(Qt.black, 1))

                y_step = rect.height() // 4

                font = QFont()
                font.setPointSizeF(rect.height() * 0.25)
                painter.setFont(font)

                for i in range(3):
                    y = rect.top() + (i + 1) * y_step

                    # Numbers: 1, 2, 3
                    text = str(i + 1)
                    painter.drawText(rect.left(), y + 3, text)

                    # Line
                    painter.drawLine(rect.left() + 6, y, rect.right() +10, y)                    

            # ---------- IMAGE ----------
            elif icon_name == "image":
                painter.setPen(QPen(Qt.darkGray, 1))
                painter.drawRect(rect)
                painter.drawLine(rect.left(), rect.bottom(),
                                 rect.center().x(), rect.top())
                painter.drawLine(rect.center().x(), rect.top(),
                                 rect.right(), rect.bottom())

            # ---------- TABLE ----------
            elif icon_name == "table":
                painter.setPen(QPen(Qt.black, 1))
                rows, cols = 3, 3
                w = rect.width() // cols
                h = rect.height() // rows
                for r in range(rows):
                    for c in range(cols):
                        painter.drawRect(rect.left() + c*w,
                                         rect.top() + r*h,
                                         w, h)

            # ---------- DEFAULT ----------
            else:
                painter.setBrush(QBrush(Qt.lightGray))
                painter.setPen(QPen(Qt.darkGray, 1))
                rect = pixmap.rect().adjusted(3, 3, -3, -3)
                painter.drawEllipse(rect)
###                


        finally:
            painter.end()
        return QIcon(pixmap)
    
    def apply_icon_to_action(self, action, icon_name, size=None):
        """Apply an icon to a QAction"""
        if not action:
            return
        icon = self.load_icon(icon_name, size)
        if icon:
            action.setIcon(icon)
    
    def apply_icon_to_button(self, button, icon_name, size=None):
        """Apply an icon to a QPushButton"""
        if not button:
            return
        icon = self.load_icon(icon_name, size)
        if icon:
            button.setIcon(icon)
            if size:
                button.setIconSize(QSize(size, size))
                
    def apply_icon_to_action_rotated(self, action, icon_name, angle, size=None):
        """Apply a rotated icon to a QAction (works with SVG files)"""
        if not action:
            return
        icon_path = self.get_icon_path(icon_name)
        if not icon_path:
            self.apply_icon_to_action(action, icon_name, size)
            return

        px_size = size if size else 32

        if icon_path.endswith('.svg'):
            from PyQt5.QtSvg import QSvgRenderer
            renderer = QSvgRenderer(icon_path)
            pixmap = QPixmap(px_size, px_size)
            pixmap.fill(Qt.transparent)
            svg_painter = QPainter(pixmap)
            renderer.render(svg_painter)
            svg_painter.end()
        else:
            icon = self.load_icon(icon_name, size)
            pixmap = icon.pixmap(px_size, px_size)

        # Rotate the pixmap
        rotated = QPixmap(pixmap.size())
        rotated.fill(Qt.transparent)
        painter = QPainter(rotated)
        try: 
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            painter.translate(pixmap.width() / 2, pixmap.height() / 2)
            painter.rotate(angle)
            painter.translate(-pixmap.width() / 2, -pixmap.height() / 2)
            painter.drawPixmap(0, 0, pixmap)
        finally:
            painter.end()

        action.setIcon(QIcon(rotated))

    def apply_icon_to_action_mirrored(self, action, icon_name, size=None):
        """Apply a vertically mirrored (axial symmetry) icon to a QAction"""
        if not action:
            return

        icon_path = self.get_icon_path(icon_name)
        if not icon_path:
            self.apply_icon_to_action(action, icon_name, size)
            return

        px_size = size if size else 32

        # Load pixmap (same as your code)
        if icon_path.endswith('.svg'):
            from PyQt5.QtSvg import QSvgRenderer
            renderer = QSvgRenderer(icon_path)
            pixmap = QPixmap(px_size, px_size)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
        else:
            icon = self.load_icon(icon_name, size)
            pixmap = icon.pixmap(px_size, px_size)

        # Create mirrored pixmap
        mirrored = QPixmap(pixmap.size())
        mirrored.fill(Qt.transparent)

        painter = QPainter(mirrored)
        try:
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)

            # Flip horizontally (vertical axis symmetry)
            painter.translate(pixmap.width(), 0)
            painter.scale(-1, 1)

            painter.drawPixmap(0, 0, pixmap)
        finally:
            painter.end()

        action.setIcon(QIcon(mirrored))
    
    # ==================== SYMBOL MAPPINGS ====================
    
    def _initialize_symbol_mappings(self):
        """Initialize complete symbol mappings: LaTeX code -> SVG filename"""
        
        # Greek Letters (lowercase)
        greek_lowercase = {
            r"\alpha": "alpha.svg", r"\beta": "beta.svg", r"\gamma": "gamma.svg",
            r"\delta": "delta.svg", r"\epsilon": "epsilon.svg", r"\varepsilon": "varepsilon.svg",
            r"\zeta": "zeta.svg", r"\eta": "eta.svg", r"\theta": "theta.svg",
            r"\vartheta": "vartheta.svg", r"\iota": "iota.svg", r"\kappa": "kappa.svg",
            r"\lambda": "lambda.svg", r"\mu": "mu.svg", r"\nu": "nu.svg",
            r"\xi": "xi.svg", r"\pi": "pi.svg", r"\varpi": "varpi.svg",
            r"\rho": "rho.svg", r"\varrho": "varrho.svg", r"\sigma": "sigma.svg",
            r"\varsigma": "varsigma.svg", r"\tau": "tau.svg", r"\upsilon": "upsilon.svg",
            r"\phi": "phi.svg", r"\varphi": "varphi.svg", r"\chi": "chi.svg",
            r"\psi": "psi.svg", r"\omega": "omega.svg"
        }
        
        # Greek Letters (uppercase)
        greek_uppercase = {
            r"\Gamma": "gamma_uppercase.svg", r"\Delta": "delta_uppercase.svg", r"\Theta": "theta_uppercase.svg",
            r"\Lambda": "lambda_uppercase.svg", r"\Xi": "xi_uppercase.svg", r"\Pi": "pi_uppercase.svg",
            r"\Sigma": "sigma_uppercase.svg", r"\Upsilon": "upsilon_uppercase.svg", r"\Phi": "phi_uppercase.svg",
            r"\Psi": "psi_uppercase.svg", r"\Omega": "omega_uppercase.svg"
        }

        # Binary Operations
        binary_operations = {
            "+": "plus.svg", "-": "minus.svg", r"\pm": "pm.svg", r"\mp": "mp.svg",
            r"\times": "times.svg", r"\div": "div.svg", r"\cdot": "cdot.svg",
            r"\ldots": "ldots.svg", r"\cdots": "cdots.svg", r"\ddotd": "ddots.svg",
            r"\ast": "ast.svg", r"\star": "star.svg", r"\circ": "circ.svg",
            r"\bullet": "bullet.svg", r"\diamond": "diamond.svg", r"\uplus": "uplus.svg",
            r"\cap": "cap.svg", r"\cup": "cup.svg", r"\sqcap": "sqcap.svg",
            r"\sqcup": "sqcup.svg", r"\vee": "vee.svg", r"\wedge": "wedge.svg",r"\lor": "vee.svg", r"\land": "wedge.svg",
            r"\setminus": "setminus.svg", r"\wr": "wr.svg", r"\triangle": "triangle.svg",
            r"\triangleleft": "triangleleft.svg", r"\triangleright": "triangleright.svg", r"\triangledown": "triangledown.svg",
            r"\oplus": "oplus.svg", r"\ominus": "ominus.svg", r"\oslash": "oslash.svg", r"\otimes": "otimes.svg",
            r"\bigcirc": "bigcirc.svg", r"\odot": "odot.svg", r"\circledcirc": "circledcirc.svg", 
            r"\circleddash": "circleddash.svg", r"\circledast": "circledast.svg",
        }
        
        # Relation Symbols
        relations = {
            "=": "equals.svg", r"\asymp": "asymp.svg", r"\equiv": "equiv.svg",
            r"\doteq": "doteq.svg", "<": "less.svg", ">": "greater.svg",
            r"\leq": "leq.svg", r"\geq": "geq.svg", r"\leqq": "leqq.svg", r"\geqq": "geqq.svg", 
            r"\leqslant": "leqslant.svg", r"\geqslant": "geqslant.svg", 
            r"\eqslantless": "eqslantless.svg", r"\eqslantgtr": "eqslantgtr.svg", 
            
            r"\lessgtr": "lessgtr.svg", r"\gtrless": "gtrless.svg",
            r"\lesseqgtr": "lesseqgtr.svg",  r"\gtreqless": "gtreqless.svg",
            r"\lesseqqgtr": "lesseqqgtr.svg", r"\gtreqqless": "gtreqqless.svg",
            r"\lesssim": "lesssim.svg", r"\gtrsim": "gtrsim.svg",
            r"\lessapprox": "lessapprox.svg", r"\gtrapprox": "gtrapprox.svg", 
            
            r"\prec": "prec.svg", r"\succ": "succ.svg", r"\preceq": "preceq.svg", r"\succeq": "succeq.svg",
            r"\ll": "ll.svg", r"\gg": "gg.svg", r"\lll": "lll.svg", r"\ggg": "ggg.svg", 
            r"\subset": "subset.svg", r"\supset": "supset.svg", 
            r"\subseteq": "subseteq.svg", r"\supseteq": "supseteq.svg",
            
            r"\subseteqq": "subseteqq.svg", r"\supseteqq": "supseteqq.svg",
            r"\Subset": "subsubset.svg", r"\Supset": "supsupset.svg",
            r"\sqsubset": "sqsubset.svg", r"\sqsupset": "sqsupset.svg", 
            r"\sqsubseteq": "sqsubseteq.svg", r"\sqsupseteq": "sqsupseteq.svg",

            r"\lhd": "lhd.svg", r"\rhd": "rhd.svg",
            r"\unlhd": "unlhd.svg", r"\unrhd": "unrhd.svg",
            
            r"\in": "in.svg", r"\ni": "ni.svg", 
            r"\vdash": "vdash.svg", r"\models": "models.svg", r"\top": "top.svg", r"\bot": "bot.svg",
            r"\therefore": "therefore.svg", r"\because": "because.svg",
            r"\propto": "propto.svg", r"\ltimes": "ltimes.svg", r"\sim": "sim.svg", r"\simeq": "simeq.svg",
            r"\approx": "approx.svg", r"\cong": "cong.svg", r"\perp": "perp.svg", r"\parallel": "parallel.svg"
        }
        
        # Negated Relation Symbols (cleaned + completed)
        negated_relations = {
            r"\neq": "neq.svg", r"\nasymp": "nasymp.svg", 
            r"\not\equiv": "nequiv.svg",
            r"\ndoteq": "ndoteq.svg",

            r"\nless": "nless.svg",
            r"\ngtr": "ngtr.svg",
            r"\nleq": "nleq.svg",
            r"\ngeq": "ngeq.svg",
            r"\nleqq": "nleqq.svg",
            r"\ngeqq": "ngeqq.svg",
            r"\nleqslant": "nleqslant.svg",
            r"\ngeqslant": "ngeqslant.svg",

            r"\nlessgtr": "nlessgtr.svg",
            r"\ngtrless": "ngtrless.svg",
            #r"\nlesseqgtr": "nlesseqgtr.svg",
            #r"\ngtreqless": "ngtreqless.svg",

            r"\lnsim": "lnsim.svg",
            r"\gnsim": "gnsim.svg",
            r"\nlessapprox": "nlessapprox.svg",
            r"\ngtrapprox": "ngtrapprox.svg",

            #r"\nll": "nll.svg",
            #r"\ngg": "ngg.svg",

            r"\nprec": "nprec.svg",
            r"\nsucc": "nsucc.svg",
            r"\npreceq": "npreceq.svg",
            r"\nsucceq": "nsucceq.svg",

            r"\napprox": "napprox.svg",
            r"\ncong": "ncong.svg",
            r"\nsim": "nsim.svg",
            #r"\nsimeq": "nsimeq.svg",
            r"\not\propto": "npropto.svg",

            r"\nsubset": "nsubset.svg",
            r"\nsupset": "nsupset.svg",
            r"\nsubseteq": "nsubseteq.svg",
            r"\nsupseteq": "nsupseteq.svg",
            r"\nsubseteqq": "nsubseteqq.svg",
            r"\nsupseteqq": "nsupseteqq.svg",
            r"\subsetneqq": "subsetneqq.svg",
            r"\supsetneqq": "supsetneqq.svg",
            
            r"\not\Subset": "nsubsubset.svg",
            r"\not\Supset": "nsupsupset.svg",   

            r"\nsqsubseteq": "nsqsubseteq.svg",
            r"\nsqsupseteq": "nsqsupseteq.svg",

            r"\ntrianglelef": "nlhd.svg",
            r"\ntriangleright": "nrhd.svg",
            r"\ntrianglelefteq": "nunlhd.svg",
            r"\ntrianglerighteq": "nunrhd.svg",

            r"\notin": "notin.svg",
            r"\nni": "nni.svg",

            r"\not\perp": "nperp.svg",
            r"\nparallel": "nparallel.svg"
        }
        
        # Arrows
        arrows = {
            r"\leftarrow": "leftarrow.svg", r"\rightarrow": "rightarrow.svg",
            r"\to": "to.svg", r"\leftrightarrow": "leftrightarrow.svg",
            r"\Leftarrow": "DLeftarrow.svg", r"\Rightarrow": "DRightarrow.svg", r"\implies": "DRightarrow.svg",
            r"\Leftrightarrow": "DLeftrightarrow.svg", r"\iff": "DLeftrightarrow.svg", r"\mapsto": "mapsto.svg",
            r"\longleftarrow": "longleftarrow.svg", r"\longrightarrow": "longrightarrow.svg",
            r"\uparrow": "uparrow.svg", r"\downarrow": "downarrow.svg",r"\Uparrow": "DUparrow.svg", r"\Downarrow": "DDownarrow.svg",
            r"\updownarrow": "updownarrow.svg",r"\Updownarrow": "DUpdownarrow.svg", r"\nearrow": "nearrow.svg",
            r"\searrow": "searrow.svg",r"\swarrow": "swarrow.svg", r"\nwarrow": "nwarrow.svg", r"\hookrightarrow": "hookrightarrow.svg",r"\hookleftarrow": "hookleftarrow.svg"
        }
        
        # Miscellaneous Symbols
        miscellaneous = {
            r"\ldots": "ldots.svg", r"\cdots": "cdots.svg", r"\vdots": "vdots.svg",
            r"\ddots": "ddots.svg", r"\aleph": "aleph.svg", r"\prime": "prime.svg",
            r"\forall": "forall.svg", r"\exists": "exists.svg",r"\nexists": "nexists.svg", r"\partial": "partial.svg",
            r"\emptyset": "emptyset.svg", r"\infty": "infty.svg", r"\nabla": "nabla.svg",
            r"\angle": "angle.svg", r"\neg": "neg.svg", r"\ell": "ell.svg", r"\mathscr{L}": "laplace.svg",
        }
        
        # Large Operators
        large_operators = {
            r"\sum_{k=0}^{\infty}": "sum.svg", r"\prod_{k=0}^{\infty}": "prod.svg", r"\coprod_{k=0}^{\infty}": "coprod.svg", r"\lim_{n\to\infty}": "lim.svg",
            r"\int_{a}^{b}{cursor}{\rm d}x": "int.svg", r"\oint": "oint.svg", r"\iint": "iint.svg", r"\iiint": "iiint.svg",
            r"\bigcap": "bigcap.svg", r"\bigcup": "bigcup.svg", r"\bigvee": "bigvee.svg",
            r"\bigwedge": "bigwedge.svg", r"\bigtriangleup": "laplacian.svg",
        }
        
        # Delimiters
        delimiters = {
            "(": "lparen.svg", ")": "rparen.svg", "[": "lbracket.svg", "]": "rbracket.svg",
            r"\{": "lbrace.svg", r"\}": "rbrace.svg", r"\langle": "langle.svg",
            r"\rangle": "rangle.svg", "|": "vert.svg", r"\|": "Vert.svg",
            r"\lfloor": "lfloor.svg", r"\rfloor": "rfloor.svg",
            r"\lceil": "lceil.svg", r"\rceil": "rceil.svg"
        }
        
        # Functions with cursors
        functions = {
            r"\sqrt{cursor}": "sqrt.svg", r"\frac{cursor}{#}": "frac.svg",
            r"^{cursor}": "superscript.svg", r"_{cursor}": "subscript.svg",
            r"\sqrt[3]{cursor}": "sqrt3.svg", r"\sqrt[n]{cursor}": "sqrtn.svg",
            r"\hat{cursor}": "hat.svg", r"\tilde{cursor}": "tilde.svg",
            r"\vec{cursor}": "vec.svg", r"\dot{cursor}": "dot.svg",
            # Further functions
            r"\sin{cursor}": "sin.svg", r"\cos{cursor}": "cos.svg",
            r"\tan{cursor}": "tan.svg", r"\cot{cursor}": "cot.svg",
            r"\sec{cursor}": "sec.svg", r"\csc{cursor}": "csc.svg",
            r"\arcsin{cursor}": "arcsin.svg", r"\arccos{cursor}": "arccos.svg",
            r"\arctan{cursor}": "arctan.svg", r"\arccot{cursor}": "arccot.svg",
            r"\sinh{cursor}": "sinh.svg", r"\cosh{cursor}": "cosh.svg",
            r"\tanh{cursor}": "tanh.svg", r"\coth{cursor}": "coth.svg",
            r"\log{cursor}": "log.svg", r"\ln{cursor}": "ln.svg", r"\exp{cursor}": "exp.svg",
            r"\lim{cursor}": "lim.svg", r"\lim_{n\to\infty}{cursor}": "limit.svg", 
            r"\sup{cursor}": "sup.svg", r"\inf{cursor}": "inf.svg",
            r"\min{cursor}": "min.svg", r"\max{cursor}": "max.svg",
            r"\deg{cursor}": "deg.svg", r"\det{cursor}": "det.svg", 
            r"\ker{cursor}": "ker.svg", r"\dim{cursor}": "dim.svg", 
            r"\hom{cursor}": "hom.svg", r"\arg{cursor}": "arg.svg",
            r"\gcd{cursor}": "gcd.svg", r"\lcm{cursor}": "lcm.svg",
            r"\Pr{cursor}": "Pr.svg", r"\Re{cursor}": "Re.svg", r"\Im{cursor}": "Im.svg",
            
            # Special constructions
            r"\left|{cursor}\right|": "abs.svg",       
            r"\lfloor{cursor}\rfloor": "floor.svg",
            r"\lceil{cursor}\rceil": "ceil.svg",
            
            # Accents / decorations
            r"\widetilde{cursor}": "widetilde.svg",
            r"\widehat{cursor}": "widehat.svg",

            # Over / under symbols
            r"\overleftarrow{cursor}": "overleftarrow.svg",
            r"\overline{cursor}": "overline.svg",
            r"\underline{cursor}": "underline.svg",

            # Braces
            r"\overbrace{cursor}": "overbrace.svg",
            r"\underbrace{cursor}": "underbrace.svg",

            # Arrows
            r"\overleftrightarrow{cursor}": "overleftrightarrow.svg",
            r"\underleftrightarrow{cursor}": "underleftrightarrow.svg",
            r"\underleftarrow{cursor}": "underleftarrow.svg",
            r"\xRightarrow{cursor}": "xrightarrow.svg",

            # Overset / Underset
            r"\overset{cursor}{=}": "overset.svg",
            r"\underset{cursor}{=}": "underset.svg",
            #r"\stackrel{cursor}{{#}}": "stackrel.svg",     
            # Further
            r"\acute{cursor}": "acute.svg",
            r"\grave{cursor}": "grave.svg",
            r"\check{cursor}": "check.svg",
            r"\hat{cursor}": "hat.svg",
            r"\tilde{cursor}": "tilde.svg",
            r"\bar{cursor}": "bar.svg",
            r"\vec{cursor}": "vec.svg",
            r"\breve{cursor}": "breve.svg",
            r"\dot{cursor}": "dot.svg",
            r"\ddot{cursor}": "ddot.svg",
            r"\mathring{cursor}": "mathring.svg",            

        }
        
        # Number Sets
        number_sets = {
            r"\mathbb{N}": "mathbb_N.svg", r"\mathbb{Z}": "mathbb_Z.svg",
            r"\mathbb{Q}": "mathbb_Q.svg", r"\mathbb{R}": "mathbb_R.svg",
            r"\mathbb{C}": "mathbb_C.svg"
        }
        
        # Combine all
        self.symbol_mappings = {
            **greek_lowercase, **greek_uppercase, **binary_operations, 
            **relations, **negated_relations, **arrows, **miscellaneous, **large_operators,
            **delimiters, **functions, **number_sets
        }
    
    def _initialize_command_mappings(self):
        """Initialize complete command mappings: LaTeX code -> SVG filename"""
        
        # Document Structure
        #document_structure = {
        #    r"\documentclass{}": "documentclass.svg",
        #    r"\usepackage{}": "usepackage.svg",
        #    r"\begin{document}": "begin_document.svg",
        #    r"\end{document}": "end_document.svg",
        #    r"\maketitle": "maketitle.svg"
        #}
        
        # Sectioning
        #sectioning = {
        #    r"\part{}": "part.svg", r"\chapter{}": "chapter.svg",
        #    r"\section{}": "section.svg", r"\subsection{}": "subsection.svg",
        #    r"\subsubsection{}": "subsubsection.svg", r"\paragraph{}": "paragraph.svg"
        #}
        
        # Environments
        environments = {
            r"\begin{}": "begin_env.svg", r"\end{}": "end_env.svg",
            r"\begin{equation}": "begin_equation.svg", r"\begin{align}": "begin_align.svg",
            r"\begin{itemize}": "begin_itemize.svg", r"\begin{enumerate}": "begin_enumerate.svg",
            r"\begin{table}": "begin_table.svg", r"\begin{figure}": "begin_figure.svg"
        }
        
        # Text Formatting
        #text_formatting = {
        #    r"\textbf{}": "textbf.svg", r"\textit{}": "textit.svg",
        #    r"\texttt{}": "texttt.svg", r"\emph{}": "emph.svg",
        #    r"\underline{}": "underline_text.svg"
        #}
        
        # Lists
        lists = {
            r"\item": "item.svg", r"\item[]": "item_optional.svg"
        }
        
        # References
        #references = {
        #    r"\label{}": "label.svg", r"\ref{}": "ref.svg",
        #    r"\cite{}": "cite.svg", r"\footnote{}": "footnote.svg"
        #}
        
        # Graphics
        graphics = {
            r"\includegraphics{}": "includegraphics.svg",
            r"\caption{}": "caption.svg"
        }
        
        # Combine all
        self.command_mappings = {
             **environments, # **document_structure, **sectioning
            **lists, **graphics #, **text_formatting, **references
        }
    
    # ==================== SYMBOL & COMMAND ICON LOADING ====================
    
    def _load_all_symbol_icons(self):
        """Load all symbol icons from files or create fallbacks"""
        for latex_code, svg_filename in self.symbol_mappings.items():
            icon = self._load_icon_with_priority(svg_filename, latex_code, "symbol")
            self.symbol_icons[latex_code] = icon
    
    def _load_all_command_icons(self):
        """Load all command icons from files or create fallbacks"""
        for latex_code, svg_filename in self.command_mappings.items():
            icon = self._load_icon_with_priority(svg_filename, latex_code, "command")
            self.command_icons[latex_code] = icon
    
    def _load_icon_with_priority(self, svg_filename, latex_code, icon_type):
        """
        Load icon with priority: .svg -> .png -> .ico -> fallback
        
        Args:
            svg_filename: Base filename like "alpha.svg"
            latex_code: LaTeX code for fallback text
            icon_type: "symbol" or "command"
        """
        # Extract base name without extension
        base_name = svg_filename.replace('.svg', '')
        extensions = ['.svg', '.png', '.ico']
        
        # Try each extension in priority order
        for ext in extensions:
            filename = base_name + ext
            icon_path = os.path.join(self.icons_folder, filename)
            
            if os.path.exists(icon_path):
                icon = self._load_svg_from_file(icon_path) if ext == '.svg' else QIcon(icon_path)
                if icon and not icon.isNull():
                    return icon
        
        # Fallback to text icon
        fallback_text = self._get_fallback_text(latex_code, icon_type)
        font_size = 14 if icon_type == "command" else 16
        return self._create_text_icon(fallback_text, font_size)
    
    def _load_svg_from_file(self, svg_path, size=64):
        """Load SVG icon from file with proper rendering and centering"""
        try:
            from PyQt5.QtSvg import QSvgRenderer
            from PyQt5.QtCore import QRectF
            
            renderer = QSvgRenderer(svg_path)
            
            # Get the SVG's default size
            svg_size = renderer.defaultSize()
            
            # Create pixmap with requested size
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.transparent)
            
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            
            # Calculate centered position maintaining aspect ratio
            if svg_size.width() > 0 and svg_size.height() > 0:
                aspect = svg_size.width() / svg_size.height()
                
                if aspect > 1:  # Wider than tall
                    render_width = size
                    render_height = size / aspect
                else:  # Taller than wide
                    render_width = size * aspect
                    render_height = size
                
                # Center the rendering
                x = (size - render_width) / 2
                y = (size - render_height) / 2
                
                renderer.render(painter, QRectF(x, y, render_width, render_height))
            else:
                # Fallback to full size rendering
                renderer.render(painter)
            
            painter.end()
            return QIcon(pixmap)
        except Exception as e:
            print(f"Error loading SVG {svg_path}: {e}")
            return None
    
    def _get_fallback_text(self, latex_code, icon_type):
        """Get Unicode fallback text for LaTeX code"""
        symbol_fallbacks = {
            r"\alpha": "α", r"\beta": "β", r"\gamma": "γ", r"\delta": "δ",
            r"\pi": "π", r"\sigma": "σ", r"\omega": "ω", r"\Sigma": "Σ",
            r"\pm": "±", r"\times": "×", r"\div": "÷", r"\cdot": "⋅",
            r"\cap": "∩", r"\cup": "∪", r"\neq": "≠", r"\leq": "≤",
            r"\geq": "≥", r"\in": "∈", r"\subset": "⊂", r"\approx": "≈",
            r"\rightarrow": "→", r"\leftarrow": "←", r"\Rightarrow": "⇒",
            r"\infty": "∞", r"\partial": "∂", r"\sum": "∑", r"\int": "∫",
            r"\sqrt{cursor}": "√", r"\frac{cursor}{#}": "⁄"
        }
        
        command_fallbacks = {
            r"\section{}": "§", r"\subsection{}": "Sub", r"\item": "•",
            r"\textbf{}": "B", r"\textit{}": "I", r"\begin{equation}": "Eq"
        }
        
        if icon_type == "symbol":
            return symbol_fallbacks.get(latex_code, "?")
        else:
            return command_fallbacks.get(latex_code, "?")
    
    def _create_text_icon(self, text, font_size=16):
        """Create text-based icon as fallback"""
        try:
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            try:
                painter.setRenderHint(QPainter.Antialiasing)
                
                font = QFont()
                font.setPointSize(font_size)
                font.setBold(True)
                painter.setFont(font)
                painter.setPen(Qt.black)
                painter.drawText(pixmap.rect(), Qt.AlignCenter, text)
            finally:
                painter.end()
            
            return QIcon(pixmap)
        except Exception as e:
            print(f"Error creating text icon: {e}")
            return QIcon()
    
    # ==================== PUBLIC API ====================
    
    def get_math_symbol_icon(self, latex_code, size=24):
        """Get icon for mathematical symbol with specified size"""
        cache_key = f"symbol_{latex_code}_{size}"
        
        if cache_key in self.icon_cache:
            return self.icon_cache[cache_key]
        
        base_icon = self.symbol_icons.get(latex_code)
        if not base_icon or base_icon.isNull():
            return QIcon()
        
        if size != 24:
            pixmap = base_icon.pixmap(size, size)
            icon = QIcon(pixmap)
        else:
            icon = base_icon
        
        self.icon_cache[cache_key] = icon
        return icon
    
    def get_latex_command_icon(self, latex_code, size=24):
        """Get icon for LaTeX command with specified size"""
        cache_key = f"command_{latex_code}_{size}"
        
        if cache_key in self.icon_cache:
            return self.icon_cache[cache_key]
        
        base_icon = self.command_icons.get(latex_code)
        if not base_icon or base_icon.isNull():
            return QIcon()
        
        if size != 24:
            pixmap = base_icon.pixmap(size, size)
            icon = QIcon(pixmap)
        else:
            icon = base_icon
        
        self.icon_cache[cache_key] = icon
        return icon
    
    def get_all_symbol_codes(self):
        """Get list of all available symbol LaTeX codes"""
        return list(self.symbol_mappings.keys())
    
    def get_all_command_codes(self):
        """Get list of all available command LaTeX codes"""
        return list(self.command_mappings.keys())
    
    def print_missing_svg_files(self):
        """Print list of missing icon files for creation"""
        #print("=== MISSING ICON FILES ===")
        #print("\nSymbol icons needed:")
        for latex_code, svg_filename in self.symbol_mappings.items():
            base_name = svg_filename.replace('.svg', '')
            found = False
            for ext in ['.svg', '.png', '.ico']:
                if os.path.exists(os.path.join(self.icons_folder, base_name + ext)):
                    found = True
                    break
            if not found:
                #print(f"  {latex_code} -> {svg_filename}")
                pass
        
        #print("\nCommand icons needed:")
        for latex_code, svg_filename in self.command_mappings.items():
            base_name = svg_filename.replace('.svg', '')
            found = False
            for ext in ['.svg', '.png', '.ico']:
                if os.path.exists(os.path.join(self.icons_folder, base_name + ext)):
                    found = True
                    break
            if not found:
                #print(f"  {latex_code} -> {svg_filename}")
                pass
    
    def create_svg_template_files(self):
        """Create simple SVG template files for common symbols"""
        templates = {
            "alpha.svg": ("α", "#1976d2"),
            "pi.svg": ("π", "#1976d2"),
            "sum.svg": ("Σ", "#f57c00"),
            "int.svg": ("∫", "#f57c00"),
            "section.svg": ("§", "#7b1fa2"),
            "item.svg": ("•", "#388e3c"),
        }
        
        for filename, (symbol, color) in templates.items():
            filepath = os.path.join(self.icons_folder, filename)
            if not os.path.exists(filepath):
                svg_content = self._create_simple_svg_template(symbol, color)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(svg_content)
                print(f"Created template: {filepath}")
    
    def _create_simple_svg_template(self, symbol, color):
        """Create a simple SVG template with given symbol and color"""
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="64" height="64" xmlns="http://www.w3.org/2000/svg">
    <text x="50%" y="50%"
          font-family="DejaVu Sans, Noto Sans, Arial Unicode MS"
          font-size="32"
          font-weight="bold"
          text-anchor="middle"
          dominant-baseline="middle"
          fill="{color}">{symbol}</text>
</svg>"""
    
    def create_all_svg_placeholders(self):
        """Create placeholder SVG files for ALL symbols and commands"""
        symbol_colors = ["#1976d2", "#f57c00", "#7b1fa2", "#388e3c", "#d32f2f"]
        command_colors = ["#7b1fa2", "#388e3c", "#d32f2f", "#f57c00", "#1976d2"]
        
        # Create symbol SVGs
        for i, (latex_code, svg_filename) in enumerate(self.symbol_mappings.items()):
            base_name = svg_filename.replace('.svg', '')
            svg_path = os.path.join(self.icons_folder, svg_filename)
            
            if not os.path.exists(svg_path):
                fallback_text = self._get_fallback_text(latex_code, "symbol")
                color = symbol_colors[i % len(symbol_colors)]
                svg_content = self._create_simple_svg_template(fallback_text, color)
                
                with open(svg_path, 'w', encoding='utf-8') as f:
                    f.write(svg_content)
        
        # Create command SVGs
        for i, (latex_code, svg_filename) in enumerate(self.command_mappings.items()):
            base_name = svg_filename.replace('.svg', '')
            svg_path = os.path.join(self.icons_folder, svg_filename)
            
            if not os.path.exists(svg_path):
                fallback_text = self._get_fallback_text(latex_code, "command")
                color = command_colors[i % len(command_colors)]
                svg_content = self._create_simple_svg_template(fallback_text, color)
                
                with open(svg_path, 'w', encoding='utf-8') as f:
                    f.write(svg_content)
        
        #print(f"Created placeholder SVG files in {self.icons_folder}")
        total_files = len([f for f in os.listdir(self.icons_folder) if f.endswith('.svg')])
        #print(f"Total SVG files: {total_files}")
    
    def get_icon_info(self, icon_name):
        """Get information about a UI icon"""
        info = {
            'name': icon_name,
            'available': False,
            'path': None,
            'variants': self.icon_map.get(icon_name, []),
            'size': None
        }
        
        icon_path = self.get_icon_path(icon_name)
        if icon_path:
            info['available'] = True
            info['path'] = icon_path
            try:
                pixmap = QPixmap(icon_path)
                if not pixmap.isNull():
                    info['size'] = (pixmap.width(), pixmap.height())
            except:
                pass
        
        return info
    
    def get_available_icons(self):
        """Get list of available UI icon names"""
        return list(self.icon_map.keys())
    
    def clear_cache(self):
        """Clear the icon cache"""
        self.icon_cache.clear()
    
    def add_icon_directory(self, directory):
        """Add a custom icon directory"""
        if directory not in self.icon_directories:
            self.icon_directories.insert(0, directory)
    
    def validate_icon_directories(self):
        """Validate and create icon directories if needed"""
        for directory in self.icon_directories:
            if not os.path.exists(directory):
                try:
                    os.makedirs(directory, exist_ok=True)
                except OSError as e:
                    print(f"Could not create icon directory {directory}: {e}")
    
    def create_colored_icon(self, base_icon_name, color, size=16):
        """Create a colored variant of an existing icon"""
        base_icon = self.load_icon(base_icon_name, size)
        if not base_icon or base_icon.isNull():
            return self.create_fallback_icon(base_icon_name, size)
        
        pixmap = base_icon.pixmap(size, size)
        colored_pixmap = QPixmap(pixmap.size())
        colored_pixmap.fill(Qt.transparent)
        
        painter = QPainter(colored_pixmap)
        try:
            painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
            painter.fillRect(colored_pixmap.rect(), color)
            painter.setCompositionMode(QPainter.CompositionMode_DestinationOver)
            painter.drawPixmap(0, 0, pixmap)
        finally:
            painter.end()
        
        return QIcon(colored_pixmap)
    
    # def create_disabled_icon(self, icon_name, size=None):
        # """Create a disabled (grayed out) version of an icon"""
        # return self.create_colored_icon(icon_name, Qt.gray, size or 16)