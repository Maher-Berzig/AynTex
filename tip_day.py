# tip_day.py
import os
import re
import random
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QSizePolicy, QShortcut, QWidget, QFrame
)
from PyQt5.QtGui import QPixmap, QMovie, QKeySequence, QPainter, QImage, QColor
from PyQt5.QtCore import QTimer, Qt, QSize, QFileInfo, QRectF, QCoreApplication
from PyQt5.QtSvg import QSvgWidget, QSvgRenderer


# ── Constants ─────────────────────────────────────────────────────────────────
TIPS_FOLDER             = "tips"
STATIC_DURATION_MS      = 16000
MAX_GIF_DURATION_MS     = 16000
DEFAULT_GIF_FRAME_DELAY = 100
DIALOG_WIDTH            = 400
DIALOG_HEIGHT           = 460          # slightly taller to fit title bar
SPRITE_GRID             = 4
SPRITE_SHEET_SIZE       = 256
SPRITE_DEFAULT_FPS      = 10

FALLBACK_TIPS = [
    "Press Ctrl+O to open a file quickly.",
    "Use Ctrl+S frequently to save your work.",
    "Right-click anywhere for context menu options.",
    "Double-click a tab to rename it.",
    "Use the search bar to find text instantly.",
]

SUPPORTED_EXTENSIONS = {".gif", ".png", ".jpg", ".jpeg", ".bmp", ".svg"}
EXTENSION_PRIORITY   = {".gif": 0, ".png": 1, ".jpg": 2, ".jpeg": 2,
                         ".bmp": 3, ".svg": 4}

# ── Embedded titles (replaces titles.json) ───────────────────────────────────
TITLES_DICT = {
    "en": {
        "tip1": "Complete the environment name",      # key = filename without extension
        "tip2": "Selecting an envirenement",
        "tip3": "Keyboard Shortcuts"
    },
    "ar": {
        "tip1": "إكمال اسم البيئة",
        "tip2": "تحديد بيئة",
        "tip3": "اختصارات لوحة المفاتيح"
    }
}
# ── Theme helper ──────────────────────────────────────────────────────────────
def _get_tip_theme() -> dict:
    try:
        from style_manager import _current_theme
        theme = _current_theme
    except ImportError:
        theme = "default"

    _COLORS = {
        "default": {
            "dialog_bg":     "#ffffff",
            "text":          "#212121",
            "title_bg":      "#e3f2fd",
            "title_border":  "#90caf9",
            "title_text":    "#0d47a1",
            "btn_bg":        "#f0f0f0",
            "btn_border":    "#aaaaaa",
            "btn_text":      "#212121",
            "btn_hover":     "#e0e0e0",
            "checkbox_text": "#333333",
            "dot_active":    "#0057b8",
            "dot_inactive":  "#9a9a9a",
            "content_bg":    "#ffffff",     # background behind the image
            "adapt_images":  False,         # no adaptation needed for light themes
        },
        "dark": {
            "dialog_bg":     "#2b2b2b",
            "text":          "#bbbbbb",
            "title_bg":      "#1e3a4a",
            "title_border":  "#4a7fbf",
            "title_text":    "#90caf9",
            "btn_bg":        "#3c3f41",
            "btn_border":    "#555759",
            "btn_text":      "#bbbbbb",
            "btn_hover":     "#4c5052",
            "checkbox_text": "#bbbbbb",
            "dot_active":    "#4a9fd8",
            "dot_inactive":  "#555555",
            "content_bg":    "#1e1e1e",     # dark bg shown behind the image
            "adapt_images":  False,         # keep images as-is on dark bg
        },
        "light": {
            "dialog_bg":     "#fafafa",
            "text":          "#1a1a1a",
            "title_bg":      "#e8f4fd",
            "title_border":  "#7ab0e8",
            "title_text":    "#1565c0",
            "btn_bg":        "#f5f5f5",
            "btn_border":    "#c0c0c0",
            "btn_text":      "#1a1a1a",
            "btn_hover":     "#e8e8e8",
            "checkbox_text": "#1a1a1a",
            "dot_active":    "#1976d2",
            "dot_inactive":  "#b0b0b0",
            "content_bg":    "#ffffff",
            "adapt_images":  False,
        },
        "midnight": {
            "dialog_bg":     "#0d1117",
            "text":          "#c9d1d9",
            "title_bg":      "#0d1f2d",
            "title_border":  "#388bfd",
            "title_text":    "#58a6ff",
            "btn_bg":        "#21262d",
            "btn_border":    "#30363d",
            "btn_text":      "#c9d1d9",
            "btn_hover":     "#30363d",
            "checkbox_text": "#c9d1d9",
            "dot_active":    "#388bfd",
            "dot_inactive":  "#30363d",
            "content_bg":    "#0d1117",     # image sits on near-black bg
            "adapt_images":  False,
        },
    }
    return _COLORS.get(theme, _COLORS["default"])

def _adapt_pixmap_for_theme(pixmap: QPixmap, theme_bg: str) -> QPixmap:
    """
    For dark themes: replace near-white background pixels with the theme
    background color, leaving the actual content (text, drawings) untouched.
    This avoids the white-on-white problem caused by full color inversion.
    
    Only pixels with lightness > 230 (out of 255) are replaced — this catches
    white/near-white backgrounds without touching light-colored content.
    """
    bg = QColor(theme_bg)
    image = pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
    
    for y in range(image.height()):
        for x in range(image.width()):
            c = QColor(image.pixel(x, y))
            # Replace near-white pixels with theme background
            if c.lightness() > 230 and c.alpha() > 200:
                new_c = QColor(bg.red(), bg.green(), bg.blue(), c.alpha())
                image.setPixel(x, y, new_c.rgba())
    
    return QPixmap.fromImage(image)


def _adapt_pixmap_fast(pixmap: QPixmap, theme_bg: str) -> QPixmap:
    """
    Fast version: composites the image over the theme background color.
    This naturally handles white backgrounds — they blend into the dark bg.
    Fully transparent pixels become the theme background color.
    Works well for SVGs and PNGs with transparent or white backgrounds.
    """
    result = QPixmap(pixmap.size())
    result.fill(QColor(theme_bg))       # fill with theme bg first
    painter = QPainter(result)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    painter.drawPixmap(0, 0, pixmap)    # draw original on top
    painter.end()
    return result

# ── File loading helpers ──────────────────────────────────────────────────────
def load_tip_images(folder=TIPS_FOLDER):
    if not os.path.isdir(folder):
        return []
    groups = {}
    for f in os.listdir(folder):
        name, ext = os.path.splitext(f)
        ext = ext.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            continue
        key      = name.lower()
        priority = EXTENSION_PRIORITY[ext]
        existing = groups.get(key)
        if existing is None or priority < existing[0]:
            groups[key] = (priority, os.path.join(folder, f))
    files = sorted(groups.values(), key=lambda x: (x[0], random.random()))
    return [path for _, path in files]


def estimate_gif_duration(movie: QMovie) -> int:
    frames = max(movie.frameCount(), 1)
    delay  = movie.nextFrameDelay()
    if delay <= 0:
        delay = DEFAULT_GIF_FRAME_DELAY
    return min(frames * delay, MAX_GIF_DURATION_MS)


def parse_sprite_fps(path: str, default: int = SPRITE_DEFAULT_FPS) -> int:
    import re
    stem = os.path.splitext(os.path.basename(path))[0].lower()
    for pattern in (r"(\d+)\s*fps", r"fps\s*(\d+)"):
        m = re.search(pattern, stem)
        if m:
            return max(1, int(m.group(1)))
    return default


def get_svg_viewbox_size(path: str):
    import xml.etree.ElementTree as ET
    try:
        tree = ET.parse(path)
        root = tree.getroot()
        vb = root.get("viewBox")
        if vb:
            parts = vb.replace(",", " ").split()
            if len(parts) == 4:
                return int(round(float(parts[2]))), int(round(float(parts[3])))
    except Exception:
        pass
    return None


# ── Nav dot ───────────────────────────────────────────────────────────────────
class NavDot(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(14, 14)
        self._active = False
        self._refresh_colors()

    def _refresh_colors(self):
        """Cache colors from current theme — call once at init and on theme change."""
        c = _get_tip_theme()
        self._color_active   = c["dot_active"]
        self._color_inactive = c["dot_inactive"]
        # Re-apply current state with new colors
        self._apply_style()

    def setActive(self, active: bool):
        if self._active == active:
            return                  # no-op — avoids triggering unnecessary repaints
        self._active = active
        self._apply_style()

    def _apply_style(self):
        color  = self._color_active if self._active else self._color_inactive
        border = "#003d80" if self._active else "#555555"
        # Use a plain string — no function calls inside setStyleSheet
        self.setStyleSheet(
            f"QPushButton {{"
            f" border-radius: 7px;"
            f" background: {color};"
            f" border: 1px solid {border};"
            f"}}"
        )

# ── Scalable widgets ──────────────────────────────────────────────────────────
class ScaledImageLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.setMinimumSize(1, 1)
        self._source_pixmap = QPixmap()
        self._invert = False


    def setSourcePixmap(self, pixmap: QPixmap):
        self._source_pixmap = pixmap
        self._refresh()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh()

    def _refresh(self):
        if self._source_pixmap.isNull():
            return
        self.setPixmap(
            self._source_pixmap.scaled(
                self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))


class ScaledSvgWidget(QSvgWidget):
    def __init__(self, path: str, parent=None):
        super().__init__(path, parent)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.setMinimumSize(1, 1)

    def sizeHint(self):
        return QSize(1, 1)


class ScaledMovieLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.setMinimumSize(1, 1)
        self._movie = None

    def setMovie(self, movie: QMovie):
        self._movie = movie
        super().setMovie(movie)
        self._rescale()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._rescale()

    def _rescale(self):
        if self._movie:
            self._movie.setScaledSize(self.size())


class SvgSpriteAnimator(QLabel):
    RENDER_SCALE = 4

    def __init__(self, path: str, parent=None,
                 grid: int = SPRITE_GRID, fps: int = SPRITE_DEFAULT_FPS):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.setMinimumSize(1, 1)
        self._grid  = grid
        self._fps   = fps
        self._index = 0

        renderer = QSvgRenderer(path)
        vb = get_svg_viewbox_size(path)
        if vb:
            nat_w, nat_h = vb
        else:
            s = renderer.defaultSize()
            nat_w, nat_h = s.width(), s.height()

        render_w = nat_w * self.RENDER_SCALE
        render_h = nat_h * self.RENDER_SCALE
        sheet = QPixmap(render_w, render_h)
        sheet.fill(Qt.transparent)
        painter = QPainter(sheet)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        renderer.render(painter, QRectF(0, 0, render_w, render_h))
        painter.end()

        fw = render_w // grid
        fh = render_h // grid
        self._frames = [
            sheet.copy((i % grid) * fw, (i // grid) * fh, fw, fh)
            for i in range(grid * grid)
        ]

        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._advance_frame)
        self._anim_timer.start(max(1, int(1000 / self._fps)))

    def _advance_frame(self):
        self._index = (self._index + 1) % len(self._frames)
        self._show_frame()

    def _show_frame(self):
        if not self._frames:
            return
        frame = self._frames[self._index]
        if frame.isNull():
            return
        target = self.size() if not self.size().isEmpty() else frame.size()
        self.setPixmap(
            frame.scaled(target, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.update()

    def showEvent(self, event):
        super().showEvent(event)
        self._show_frame()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._show_frame()

    def stop(self):
        self._anim_timer.stop()


# ── Dialog ────────────────────────────────────────────────────────────────────
class TipOfTheDayDialog(QDialog):
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.main_window    = main_window
        self._lang          = self._get_lang()
        self._tr            = self._get_translations()

        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setWindowTitle(self._tr.get("tip_title", "Tip of the Day"))
        self.resize(DIALOG_WIDTH, DIALOG_HEIGHT)

        self._config_manager = self.main_window.config_manager if self.main_window else None
        
        
        self._image_tips = load_tip_images()
              
        # ── Filter based on theme ─────────────────────────────────────────
        if self._is_dark_theme():
            self._image_tips = [p for p in self._image_tips if "_dark." in p]
        else:
            self._image_tips = [p for p in self._image_tips if "_dark." not in p]
        # ──────────────────────────────────────────────────────────────────
        #self._use_images = bool(self._image_tips)
        #self._tips = self._image_tips if self._use_images else FALLBACK_TIPS        
        
        self._use_images = bool(self._image_tips)
        self._tips       = self._image_tips if self._use_images else FALLBACK_TIPS
        #self._titles     = load_tip_titles(lang=self._lang)
        # Use embedded titles dictionary
        self._titles = TITLES_DICT.get(self._lang, TITLES_DICT.get("en", {}))
        self._index      = 0
        self._movie      = None
        self._sprite     = None

        self._build_ui()
        self._apply_theme()
        self._setup_shortcuts()
        self._setup_timer()
        self._show_tip()

    # ── Language / translation helpers ───────────────────────────────────────
    def _get_lang(self) -> str:
        if self.main_window and hasattr(self.main_window, 'menu_language'):
            return self.main_window.menu_language
        return "en"

    def _get_translations(self) -> dict:
        if (self.main_window
                and hasattr(self.main_window, 'translations')
                and self._lang in self.main_window.translations):
            return self.main_window.translations[self._lang]
        return {}

    def _t(self, key: str, fallback: str = "", **kwargs) -> str:
        """Translate key, formatting with kwargs if provided."""
        text = self._tr.get(key, fallback)
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, ValueError):
                pass
        return text


    def _title_for_index(self, index: int) -> str:
        """Return per-image title if available, else generic 'Tip N of M'."""
        if self._use_images:
            path = self._tips[index]
            base = os.path.splitext(os.path.basename(path))[0].lower()
            
            # Remove known suffixes that are not part of the title key
            base = re.sub(r'_dark$', '', base)      # remove _dark
            base = re.sub(r'_\d+fps$', '', base)    # remove _1fps, _24fps, etc.
            # optional: remove any trailing _number
            base = re.sub(r'_\d+$', '', base)
            
            # DEBUG: see cleaned base
            specific = self._titles.get(base)
            if specific:
                return specific
        return self._t(
            "tip_of",
            fallback=f"Tip {index + 1} of {len(self._tips)}",
            current=index + 1,
            total=len(self._tips),
        )
    

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # ── Title bar ────────────────────────────────────────────────────
        self._title_frame = QFrame()
        self._title_frame.setFixedHeight(36)
        title_layout = QHBoxLayout(self._title_frame)
        title_layout.setContentsMargins(10, 4, 10, 4)

        self._title_label = QLabel()
        self._title_label.setAlignment(Qt.AlignCenter)
        font = self._title_label.font()
        font.setBold(True)
        font.setPointSize(font.pointSize() + 1)
        self._title_label.setFont(font)
        title_layout.addWidget(self._title_label)
        layout.addWidget(self._title_frame)

        # ── Content area ─────────────────────────────────────────────────
        self._content        = QWidget()
        self._content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._content, stretch=1)

        # Persistent reusable widgets
        self._tip_label   = QLabel(wordWrap=True)
        self._tip_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self._tip_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._image_label = ScaledImageLabel()

        # ── Nav dots ─────────────────────────────────────────────────────
        dot_row = QHBoxLayout()
        dot_row.setAlignment(Qt.AlignCenter)
        self._dots = []
        for i in range(len(self._tips)):
            dot = NavDot()
            dot.setToolTip(f"{i + 1} / {len(self._tips)}")
            dot.clicked.connect(lambda _, x=i: self._go_to(x))
            self._dots.append(dot)
            dot_row.addWidget(dot)
        layout.addLayout(dot_row)

        # ── Navigation buttons ───────────────────────────────────────────       
        btn_row = QHBoxLayout()
        self._prev_btn = QPushButton(self._nav_label("prev"))
        self._next_btn = QPushButton(self._nav_label("next"))
        self._close_btn = QPushButton(
            self._t("tip_close", "Close"))
        self._prev_btn.clicked.connect(self._prev)
        self._next_btn.clicked.connect(self._next)
        self._close_btn.clicked.connect(self.close)
        btn_row.addWidget(self._prev_btn)
        btn_row.addWidget(self._next_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._close_btn)
        layout.addLayout(btn_row)

        # ── Startup checkbox ─────────────────────────────────────────────
        self._checkbox = QCheckBox(
            self._t("tip_show_startup", "Show tips at startup"))
            
        # Read initial value from config (default True)
        show_tips = True
        if self._config_manager:
            val = self._config_manager.get_config_value('ui', 'show_tips', 'True')
            show_tips = str(val).strip().lower() == 'true'
        self._checkbox.setChecked(show_tips)

        def save_show_tips(checked: bool):
            if self._config_manager:
                self._config_manager.set_config_value('ui', 'show_tips', str(checked))
                # Optionally force save to disk
                if hasattr(self._config_manager, 'save_config'):
                    self._config_manager.save_config()

        self._checkbox.toggled.connect(save_show_tips)
            
        layout.addWidget(self._checkbox)
        
    def _nav_label(self, key_prev_next: str) -> str:
        """
        Return localised prev/next button text with correctly oriented triangles.
        In RTL (Arabic) the logical direction is reversed:
          'Previous' visually points RIGHT  ▶
          'Next'     visually points LEFT   ◀
        """
        is_rtl = (self._lang == "ar")
        if key_prev_next == "prev":
            arrow = "▶" if is_rtl else "◀"
            label = self._t("tip_prev_text", "Previous")
            return f"{arrow}  {label}" if is_rtl else f"{arrow}  {label}"
        else:
            arrow = "◀" if is_rtl else "▶"
            label = self._t("tip_next_text", "Next")
            return f"{label}  {arrow}"

    # ── Theme application ─────────────────────────────────────────────────────
    def _apply_theme(self):
        c = _get_tip_theme()

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {c['dialog_bg']};
                color: {c['text']};
            }}
            QLabel {{
                color: {c['text']};
                background: transparent;
            }}
        """)

        self._title_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {c['title_bg']};
                border: 1px solid {c['title_border']};
                border-radius: 4px;
            }}
        """)
        self._title_label.setStyleSheet(f"color: {c['title_text']};")

        btn_style = f"""
            QPushButton {{
                background-color: {c['btn_bg']};
                color: {c['btn_text']};
                border: 1px solid {c['btn_border']};
                border-radius: 4px;
                padding: 5px 14px;
                font-size: 9pt;
            }}
            QPushButton:hover {{
                background-color: {c['btn_hover']};
            }}
        """
        for btn in (self._prev_btn, self._next_btn, self._close_btn):
            btn.setStyleSheet(btn_style)

        self._checkbox.setStyleSheet(
            f"QCheckBox {{ color: {c['checkbox_text']}; }}")

        # ✅ Refresh dot colors with new theme — safe because _refresh_colors()
        # does NOT call setStyleSheet inside a paint event
        for dot in self._dots:
            dot._refresh_colors()
        self._update_dots()

    def _is_dark_theme(self) -> bool:
        try:
            from style_manager import _current_theme
            theme_name = _current_theme
        except ImportError:
            theme_name = "default"
        return theme_name in ("dark", "midnight")

    def _get_dark_svg_path(self, original_path: str) -> str:
        """If dark theme is active and a _dark.svg file exists, return its path."""
        if not self._is_dark_theme():
            return original_path
        base, ext = os.path.splitext(original_path)
        dark_path = f"{base}_dark{ext}"
        if os.path.isfile(dark_path):
            return dark_path
        return original_path
    # ── Shortcuts & timer ────────────────────────────────────────────────────
    def _setup_shortcuts(self):
        QShortcut(QKeySequence(Qt.Key_Left),   self, self._prev)
        QShortcut(QKeySequence(Qt.Key_Right),  self, self._next)
        QShortcut(QKeySequence(Qt.Key_Escape), self, self.close)

    def _setup_timer(self):
        self._timer = QTimer(self, singleShot=False)
        self._timer.timeout.connect(self._next)

    # ── Content helpers ───────────────────────────────────────────────────────
    def _clear_content(self):
        if self._sprite:
            self._sprite.stop()
            self._sprite = None
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            w = item.widget()
            if w and w not in (self._tip_label, self._image_label):
                w.deleteLater()

    def _set_content_widget(self, widget: QWidget):
        self._clear_content()
        self._content_layout.addWidget(widget)

    # ── Navigation ────────────────────────────────────────────────────────────
    def _go_to(self, index: int):
        self._stop_movie()
        self._index = index % len(self._tips)
        self._show_tip()

    def _next(self): self._go_to(self._index + 1)
    def _prev(self): self._go_to(self._index - 1)

    # ── Rendering ─────────────────────────────────────────────────────────────
    def _stop_movie(self):
        if self._movie:
            self._movie.stop()
            self._movie = None

    def _show_tip(self):
        self._timer.stop()

        # Update title bar text
        self._title_label.setText(self._title_for_index(self._index))

        if self._use_images:
            self._show_image(self._tips[self._index])
        else:
            self._set_content_widget(self._tip_label)
            self._tip_label.setText(self._tips[self._index])
            self._timer.start(STATIC_DURATION_MS)

        self._update_dots()
        self._update_nav_buttons()

    def _show_image(self, path: str):
        ext = QFileInfo(path).suffix().lower()
        if ext == "gif":
            self._show_gif(path)
        elif ext == "svg":
            self._show_svg(path)
        else:
            self._show_static(path)

    def _should_invert(self) -> bool:
        return _get_tip_theme()["invert_images"]

    def _show_gif(self, path: str):
        label = ScaledMovieLabel()
        self._set_content_widget(label)
        self._movie = QMovie(path)
        label.setMovie(self._movie)
        self._movie.start()
        self._timer.start(estimate_gif_duration(self._movie))

    def _show_svg(self, path: str):
        path = self._get_dark_svg_path(path)   # <-- add this line
        vb = get_svg_viewbox_size(path)
        is_sprite = (vb == (SPRITE_SHEET_SIZE, SPRITE_SHEET_SIZE))
        if is_sprite:
            fps    = parse_sprite_fps(path)
            # ✅ No invert — sprite renders on the content_bg set in _apply_theme
            sprite = SvgSpriteAnimator(path, grid=SPRITE_GRID, fps=fps)
            self._sprite = sprite
            self._set_content_widget(sprite)
            sprite._anim_timer.stop()
            sprite._anim_timer.start(max(1, int(1000 / fps)))
        else:
            # ✅ Plain SVG — just display it; background comes from content_bg
            self._set_content_widget(ScaledSvgWidget(path))
        self._timer.start(STATIC_DURATION_MS)

    def _show_static(self, path: str):
        pixmap = QPixmap(path)
        if pixmap.isNull():
            self._set_content_widget(self._tip_label)
            self._tip_label.setText(
                f"Could not load:\n{os.path.basename(path)}")
        else:
            # ✅ No inversion — image displays as-is on the themed content_bg
            self._image_label.setSourcePixmap(pixmap)
            self._set_content_widget(self._image_label)
        self._timer.start(STATIC_DURATION_MS)
    # ── UI state ──────────────────────────────────────────────────────────────
    def _update_dots(self):
        for i, dot in enumerate(self._dots):
            dot.setActive(i == self._index)

    def _update_nav_buttons(self):
        enabled = len(self._tips) > 1
        self._prev_btn.setEnabled(enabled)
        self._next_btn.setEnabled(enabled)

    # ── Cleanup ───────────────────────────────────────────────────────────────
    def closeEvent(self, event):
        self._timer.stop()
        self._stop_movie()
        if self._sprite:
            self._sprite.stop()
        super().closeEvent(event)


# ── Factory ───────────────────────────────────────────────────────────────────
def create_tip_dialog(parent=None, main_window=None, force=False):
    if force:
        return TipOfTheDayDialog(parent, main_window=main_window)
    if main_window and hasattr(main_window, 'config_manager'):
        cm = main_window.config_manager
        val = cm.get_config_value('ui', 'show_tips', 'True')
        if str(val).strip().lower() == 'true':
            return TipOfTheDayDialog(parent, main_window=main_window)
    else:
        # Fallback: if no config manager, keep old behaviour (show by default)
        return TipOfTheDayDialog(parent, main_window=main_window)
    return None    