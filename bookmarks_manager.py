# bookmarks_manager.py
"""
Enhanced AutoCompletion class with bookmark support
"""
import os
import sys
import re
from PyQt5.QtWidgets import QWidget, QSizePolicy, QPlainTextEdit, QApplication, QMainWindow, QTextEdit
from PyQt5.QtGui import (QPen, QBrush, QKeySequence, QTextCursor, QPainter, QColor,
                          QFont, QTextFormat, QTextOption, QTextCharFormat)
from PyQt5.QtCore import Qt, QRect, QSize, QPoint, QTimer
from toolbar_manager import BookmarksWidget


class FoldingRegion:
    """Represents a foldable region in the document"""
    def __init__(self, start_line, end_line, level, section_type, title=""):
        self.start_line = start_line  # 1-indexed line number in full document
        self.end_line = end_line      # 1-indexed line number in full document
        self.level = level
        self.section_type = section_type
        self.title = title
        self.is_folded = False
        self.region_type = "section"  # "section", "preamble", "document_begin", "bibliography"


class LineNumberArea(QWidget):
    """Enhanced line number area with folding indicators"""
    FOLD_MARKER_WIDTH = 18

    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
        self._hover_line = -1
        self.setMouseTracking(True)

    def sizeHint(self):
        return QSize(self.editor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.editor.lineNumberAreaPaintEvent(event)

    def mousePressEvent(self, event):
        """Handle clicks on fold markers and bookmarks"""
        if not self.editor._line_numbers_visible and not self.editor._fold_markers_visible:
            event.ignore()
            return

        x_pos = event.pos().x()
        y_pos = event.pos().y()

        if self.editor._fold_markers_visible:
            total_width = self.editor.lineNumberAreaWidth()
            fold_width = LineNumberArea.FOLD_MARKER_WIDTH

            if self.editor.is_rtl_mode:
                # Fold markers are on the LEFT side in RTL mode
                fold_area_start = 0
                fold_area_end = fold_width
                in_fold_area = (x_pos >= fold_area_start and x_pos < fold_area_end)
            else:
                # Fold markers are on the RIGHT side in LTR mode
                fold_area_start = total_width - fold_width
                in_fold_area = (x_pos >= fold_area_start)

            if in_fold_area:
                block = self.editor._get_block_at_y(y_pos)
                if block and block.isValid():
                    line_number = block.blockNumber() + 1
                    if self.editor.toggle_fold_at_line(line_number):
                        event.accept()
                        return

        if self.editor._line_numbers_visible:
            self.editor.toggle_bookmark_at(y_pos)
        event.accept()

    def mouseMoveEvent(self, event):
        """Track mouse for hover effects on fold markers"""
        y_pos = event.pos().y()
        block = self.editor._get_block_at_y(y_pos)
        new_hover_line = (block.blockNumber() + 1) if (block and block.isValid()) else -1
        if new_hover_line != self._hover_line:
            self._hover_line = new_hover_line
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        """Clear hover state when mouse leaves"""
        self._hover_line = -1
        self.update()
        super().leaveEvent(event)


class BookmarksManager(QPlainTextEdit):
    """Enhanced bookmark functionality with visibility-based code folding"""

    SECTION_LEVELS = {
        'part': 0,
        'chapter': 1,
        'section': 2,
        'subsection': 3,
        'subsubsection': 4,
        'paragraph': 5,
        'subparagraph': 6,
    }

    def __init__(self, parent=None):
        super().__init__()
        self.parent_editor_manager = parent
        self.bookmarked_lines = set()
        self.bookmark_color = QColor("#ffeb3b")
        self.bookmarks_widget = BookmarksWidget(self)
        self.spell_highlighter = None

        # === FOLDING SUPPORT ===
        self.folding_regions = []
        self._folding_enabled = True
        self._fold_cache_valid = False
        self._folding_in_progress = False
        self._suppress_fold_reapply = False  # NEW: prevent re-apply during editing

        # Fold marker colors
        self.fold_marker_color = QColor("#505050")
        self.fold_marker_hover_color = QColor("#0066cc")
        self.fold_line_color = QColor("#a0a0a0")

        self._line_numbers_visible = True
        self._fold_markers_visible = True

        from PyQt5.QtWidgets import QShortcut
        from PyQt5.QtGui import QKeySequence

        self.bookmark_shortcut = QShortcut(QKeySequence("Ctrl+B"), self)
        self.bookmark_shortcut.activated.connect(self.toggle_current_line_bookmark)

        #self.fold_shortcut = QShortcut(QKeySequence("Ctrl+Shift+["), self)
        #self.fold_shortcut.activated.connect(self.fold_current_section)

        #self.unfold_shortcut = QShortcut(QKeySequence("Ctrl+Shift+]"), self)
        #self.unfold_shortcut.activated.connect(self.unfold_current_section)

        #self.fold_all_shortcut = QShortcut(QKeySequence("Ctrl+Shift+minus"), self)
        #self.fold_all_shortcut.activated.connect(self.fold_all)

        #self.unfold_all_shortcut = QShortcut(QKeySequence("Ctrl+Shift+plus"), self)
        #self.unfold_all_shortcut.activated.connect(self.unfold_all)

        self.is_rtl_mode = False
        self._current_alignment = Qt.AlignLeft

        self.bracket_pairs = {'(': ')', '[': ']', '{': '}'}
        self.opening_brackets = set(self.bracket_pairs.keys())
        self.closing_brackets = set(self.bracket_pairs.values())
        self.bracket_selections = []

        self.delimiter_pairs = {
            '(': ')', '[': ']', '$': '$', '\\(': '\\)', '\\[': '\\]',
            '{': '}', '\\{': '\\}', '\\|': '\\|', '|': '|', '"': '"'
        }
        self._processing_delimiter = False
        self._backslash_selection_state = None

        self._cwl_completer = None
        self._refcite_completer = None

        self.document().blockCountChanged.connect(self._ensure_block_alignment)

        self.lineNumberArea = LineNumberArea(self)

        self.document().blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.document().contentsChanged.connect(self.updateLineNumberArea)
        self.document().contentsChanged.connect(self._invalidate_fold_cache)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)
        self.cursorPositionChanged.connect(self.highlightMatchingBrackets)
        self.verticalScrollBar().valueChanged.connect(self.updateLineNumberArea)
        self.horizontalScrollBar().valueChanged.connect(self.updateLineNumberArea)

        self.updateLineNumberAreaWidth()
        self.highlightCurrentLine()

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(200, 150)
        self.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        self.setWordWrapMode(QTextOption.WrapAnywhere)

        doc = self.document()
        doc.setMaximumBlockCount(0)
        self.setUndoRedoEnabled(True)

    # ==========================================
    # THEMES COLORS
    # ==========================================
    def _get_theme_colors(self) -> dict:
        """Return all line-number/fold-area colors for the current theme."""
        try:
            from style_manager import _current_theme
            theme = _current_theme
        except ImportError:
            theme = "default"

        _COLORS = {
            "default": {
                # Line number area
                "ln_bg":            "#f0f0f0",
                "ln_text":          "#757575",
                "ln_text_bookmark": "#c62828",
                "ln_bookmark_bg":   "#fff9c4",   # bookmark_color.lighter(150)
                # Fold marker area
                "fold_bg":          "#e3f2fd",
                "fold_separator":   "#d0d0d0",
                # Fold scope lines
                "scope_preamble":   "#ce93d8",
                "scope_doc_begin":  "#ffcc80",
                "scope_biblio":     "#a5d6a7",
                "scope_section":    "#a0a0a0",
                # Fold marker — section (normal / hover)
                "sec_border":       "#6e6e6e",
                "sec_fill":         "#ffffff",
                "sec_symbol":       "#424242",
                "sec_border_h":     "#0078d4",
                "sec_fill_h":       "#cce4f7",
                "sec_symbol_h":     "#0078d4",
                # Fold marker — preamble
                "pre_border":       "#9c27b0",
                "pre_fill":         "#f3e5f5",
                "pre_symbol":       "#7b1fa2",
                "pre_border_h":     "#7b1fa2",
                "pre_fill_h":       "#e1bee7",
                "pre_symbol_h":     "#7b1fa2",
                # Fold marker — document begin
                "doc_border":       "#ff9800",
                "doc_fill":         "#fff3e0",
                "doc_symbol":       "#e65100",
                "doc_border_h":     "#e65100",
                "doc_fill_h":       "#ffe0b2",
                "doc_symbol_h":     "#e65100",
                # Fold marker — bibliography
                "bib_border":       "#4caf50",
                "bib_fill":         "#e8f5e9",
                "bib_symbol":       "#2e7d32",
                "bib_border_h":     "#2e7d32",
                "bib_fill_h":       "#c8e6c9",
                "bib_symbol_h":     "#2e7d32",
                # Current line highlight
                "current_line_bg":  "#fafafa",
            },
            "dark": {
                "ln_bg":            "#2b2b2b",
                "ln_text":          "#858585",
                "ln_text_bookmark": "#ef9a9a",
                "ln_bookmark_bg":   "#4a3800",
                "fold_bg":          "#1e3a4a",
                "fold_separator":   "#444444",
                "scope_preamble":   "#8e44ad",
                "scope_doc_begin":  "#d68910",
                "scope_biblio":     "#1e8449",
                "scope_section":    "#555555",
                "sec_border":       "#777777",
                "sec_fill":         "#3c3f41",
                "sec_symbol":       "#aaaaaa",
                "sec_border_h":     "#4a9fd8",
                "sec_fill_h":       "#1e3a5f",
                "sec_symbol_h":     "#4a9fd8",
                "pre_border":       "#ab47bc",
                "pre_fill":         "#3a1f4a",
                "pre_symbol":       "#ce93d8",
                "pre_border_h":     "#ce93d8",
                "pre_fill_h":       "#4a2060",
                "pre_symbol_h":     "#ce93d8",
                "doc_border":       "#ffa726",
                "doc_fill":         "#3a2800",
                "doc_symbol":       "#ffcc02",
                "doc_border_h":     "#ffcc02",
                "doc_fill_h":       "#4a3400",
                "doc_symbol_h":     "#ffcc02",
                "bib_border":       "#66bb6a",
                "bib_fill":         "#1a3a1a",
                "bib_symbol":       "#a5d6a7",
                "bib_border_h":     "#a5d6a7",
                "bib_fill_h":       "#1e4a1e",
                "bib_symbol_h":     "#a5d6a7",
                "current_line_bg":  "#323232",
            },
            "light": {
                "ln_bg":            "#f5f5f5",
                "ln_text":          "#707070",
                "ln_text_bookmark": "#b71c1c",
                "ln_bookmark_bg":   "#fffde7",
                "fold_bg":          "#e8f4fd",
                "fold_separator":   "#c8c8c8",
                "scope_preamble":   "#ba68c8",
                "scope_doc_begin":  "#ffb74d",
                "scope_biblio":     "#81c784",
                "scope_section":    "#b0b0b0",
                "sec_border":       "#888888",
                "sec_fill":         "#fafafa",
                "sec_symbol":       "#555555",
                "sec_border_h":     "#1976d2",
                "sec_fill_h":       "#bbdefb",
                "sec_symbol_h":     "#1976d2",
                "pre_border":       "#8e24aa",
                "pre_fill":         "#f8e8ff",
                "pre_symbol":       "#6a1b9a",
                "pre_border_h":     "#6a1b9a",
                "pre_fill_h":       "#e8ccff",
                "pre_symbol_h":     "#6a1b9a",
                "doc_border":       "#ef6c00",
                "doc_fill":         "#fff8e1",
                "doc_symbol":       "#bf360c",
                "doc_border_h":     "#bf360c",
                "doc_fill_h":       "#ffe0b2",
                "doc_symbol_h":     "#bf360c",
                "bib_border":       "#388e3c",
                "bib_fill":         "#f1f8e9",
                "bib_symbol":       "#1b5e20",
                "bib_border_h":     "#1b5e20",
                "bib_fill_h":       "#dcedc8",
                "bib_symbol_h":     "#1b5e20",
                "current_line_bg":  "#fafafa",
            },
            "midnight": {
                "ln_bg":            "#0d1117",
                "ln_text":          "#484f58",
                "ln_text_bookmark": "#f85149",
                "ln_bookmark_bg":   "#3d1a00",
                "fold_bg":          "#0d1f2d",
                "fold_separator":   "#21262d",
                "scope_preamble":   "#8957e5",
                "scope_doc_begin":  "#d29922",
                "scope_biblio":     "#3fb950",
                "scope_section":    "#30363d",
                "sec_border":       "#30363d",
                "sec_fill":         "#161b22",
                "sec_symbol":       "#8b949e",
                "sec_border_h":     "#388bfd",
                "sec_fill_h":       "#0d2045",
                "sec_symbol_h":     "#58a6ff",
                "pre_border":       "#8957e5",
                "pre_fill":         "#1a0d35",
                "pre_symbol":       "#d2a8ff",
                "pre_border_h":     "#d2a8ff",
                "pre_fill_h":       "#2a1a50",
                "pre_symbol_h":     "#d2a8ff",
                "doc_border":       "#d29922",
                "doc_fill":         "#1f1600",
                "doc_symbol":       "#e3b341",
                "doc_border_h":     "#e3b341",
                "doc_fill_h":       "#2d2000",
                "doc_symbol_h":     "#e3b341",
                "bib_border":       "#3fb950",
                "bib_fill":         "#0a1f0a",
                "bib_symbol":       "#56d364",
                "bib_border_h":     "#56d364",
                "bib_fill_h":       "#0f2d0f",
                "bib_symbol_h":     "#56d364",
                "current_line_bg":  "#161b22",
            },
        }
        return _COLORS.get(theme, _COLORS["default"])    

    # ==========================================
    # VISIBILITY TOGGLES
    # ==========================================

    def set_line_numbers_visible(self, visible):
        self._line_numbers_visible = bool(visible)
        self._update_line_number_area()

    def set_fold_markers_visible(self, visible):
        self._fold_markers_visible = bool(visible)
        self._folding_enabled = bool(visible)
        self._update_line_number_area()

    def _update_line_number_area(self):
        should_show_area = self._line_numbers_visible or self._fold_markers_visible
        if hasattr(self, 'lineNumberArea'):
            self.lineNumberArea.setVisible(should_show_area)
        self.updateLineNumberAreaWidth()
        if hasattr(self, 'lineNumberArea'):
            self.lineNumberArea.update()
        self.viewport().update()

    def is_line_numbers_visible(self):
        return self._line_numbers_visible

    def is_fold_markers_visible(self):
        return self._fold_markers_visible

    # ==========================================
    # FOLDING METHODS - VISIBILITY BASED
    # ==========================================

    def _invalidate_fold_cache(self):
        """Mark fold cache as invalid when document changes"""
        if not self._folding_in_progress:
            self._fold_cache_valid = False
            if hasattr(self, 'lineNumberArea'):
                self.lineNumberArea.update()
                
    def _parse_folding_regions(self):
        """Parse document to find all foldable sections.
        
        Works on the FULL document (all blocks, visible or not) so that
        line numbers are always the real document line numbers.
        
        IMPORTANT: This method only updates the region list and preserves
        fold states. It does NOT re-apply block visibility — that only
        happens on explicit fold/unfold actions.
        """
        if self._fold_cache_valid:
            return

        doc = self.document()
        total_lines = doc.blockCount()

        if total_lines == 0:
            self.folding_regions = []
            self._fold_cache_valid = True
            return

        # Build list of all lines from the document blocks
        lines = []
        block = doc.begin()
        while block.isValid():
            lines.append(block.text())
            block = block.next()

        section_pattern = re.compile(
            r'\\(part|chapter|section|subsection|subsubsection|paragraph|subparagraph)\*?\s*(?:\[[^\]]*\])?\s*\{',
            re.IGNORECASE
        )

        begin_document_line = None
        end_document_line = None
        documentclass_line = None

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('%'):
                continue
            if r'\documentclass' in line and documentclass_line is None:
                documentclass_line = i + 1
            if r'\begin{document}' in line and begin_document_line is None:
                begin_document_line = i + 1
            if r'\end{document}' in line:
                end_document_line = i + 1

        bibliography_regions = []
        bib_start = None
        bib_type = None
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('%'):
                continue
            if bib_start is None:
                if r'\begin{thebibliography}' in line:
                    bib_start = i + 1
                    bib_type = 'thebibliography'
                elif r'\begin{references}' in line:
                    bib_start = i + 1
                    bib_type = 'references'
                elif r'\begin{biblist}' in line:
                    bib_start = i + 1
                    bib_type = 'biblist'
            else:
                if (bib_type == 'thebibliography' and r'\end{thebibliography}' in line) or \
                   (bib_type == 'references' and r'\end{references}' in line) or \
                   (bib_type == 'biblist' and r'\end{biblist}' in line):
                    bibliography_regions.append((bib_start, i + 1, bib_type))
                    bib_start = None
                    bib_type = None

        sections = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('%'):
                continue
            comment_pos = line.find('%')
            search_line = line if comment_pos == -1 else line[:comment_pos]
            match = section_pattern.search(search_line)
            if match:
                section_type = match.group(1).lower()
                level = self.SECTION_LEVELS.get(section_type, 99)
                title = self._extract_brace_content(line, match.end() - 1)
                sections.append({
                    'line': i + 1,
                    'type': section_type,
                    'title': title,
                    'level': level
                })

        # Build old fold state lookup from current regions
        # Key by start_line for exact match, and by (type, title) for fuzzy match
        old_fold_by_line = {}
        old_fold_by_identity = {}
        for region in self.folding_regions:
            if region.is_folded:
                old_fold_by_line[region.start_line] = True
                old_fold_by_identity[(region.region_type, region.section_type, region.title)] = True

        self.folding_regions = []

        def _was_folded(r):
            """Check if this region was previously folded - prefer line match, then identity"""
            if r.start_line in old_fold_by_line:
                return True
            if (r.region_type, r.section_type, r.title) in old_fold_by_identity:
                return True
            return False

        # === PREAMBLE REGION ===
        if documentclass_line and begin_document_line and begin_document_line > documentclass_line:
            preamble_end = begin_document_line - 1
            r = FoldingRegion(documentclass_line, preamble_end, -10, 'preamble', 'Preamble')
            r.region_type = "preamble"
            r.is_folded = _was_folded(r)
            self.folding_regions.append(r)

        # === DOCUMENT BEGIN REGION ===
        if begin_document_line:
            doc_begin_end = None
            first_content_line = None
            for sec in sections:
                if sec['line'] > begin_document_line:
                    first_content_line = sec['line'] - 1
                    break
            for bib_start_line, _, _ in bibliography_regions:
                if bib_start_line > begin_document_line:
                    if first_content_line is None or bib_start_line - 1 < first_content_line:
                        first_content_line = bib_start_line - 1
                    break
            if first_content_line and first_content_line >= begin_document_line:
                doc_begin_end = first_content_line
            elif end_document_line and end_document_line > begin_document_line:
                doc_begin_end = end_document_line - 1
            if doc_begin_end and doc_begin_end >= begin_document_line:
                r = FoldingRegion(begin_document_line, doc_begin_end, -10, 'document', 'Document Begin')
                r.region_type = "document_begin"
                r.is_folded = _was_folded(r)
                self.folding_regions.append(r)

        # === SECTION REGIONS ===
        for i, section in enumerate(sections):
            start_line = section['line']
            level = section['level']
            end_line = end_document_line if end_document_line else total_lines

            for j in range(i + 1, len(sections)):
                if sections[j]['level'] <= level:
                    end_line = sections[j]['line'] - 1
                    break

            for bib_start_line, bib_end_line, _ in bibliography_regions:
                if start_line < bib_start_line <= end_line:
                    end_line = bib_start_line - 1
                    break

            is_last_top_level = True
            for j in range(i + 1, len(sections)):
                if sections[j]['level'] <= level:
                    is_last_top_level = False
                    break
            has_bib_after = any(bs > start_line for bs, _, _ in bibliography_regions)
            if is_last_top_level and not has_bib_after and end_document_line:
                end_line = end_document_line

            if end_line >= start_line:
                r = FoldingRegion(start_line, end_line, level, section['type'], section['title'])
                r.region_type = "section"
                r.is_folded = _was_folded(r)
                self.folding_regions.append(r)

        # === BIBLIOGRAPHY REGIONS ===
        for idx, (bib_start_line, bib_end_line, bib_type_name) in enumerate(bibliography_regions):
            is_last_bib = (idx == len(bibliography_regions) - 1)
            has_section_after = any(sec['line'] > bib_end_line for sec in sections)
            actual_end = bib_end_line
            if is_last_bib and not has_section_after and end_document_line and end_document_line >= bib_end_line:
                actual_end = end_document_line
            if actual_end >= bib_start_line:
                r = FoldingRegion(bib_start_line, actual_end, -10, 'bibliography', bib_type_name.capitalize())
                r.region_type = "bibliography"
                r.is_folded = _was_folded(r)
                self.folding_regions.append(r)

        self._fold_cache_valid = True
        # NOTE: We do NOT call _apply_all_fold_visibility() here.
        # Visibility is only changed by explicit fold/unfold actions.


    def _set_region_visibility(self, region, folded):
        """Set visibility of blocks in a single region"""
        if self._folding_in_progress:
            return

        self._folding_in_progress = True
        try:
            doc = self.document()
            region.is_folded = folded

            if region.end_line <= region.start_line:
                # Nothing to hide/show
                self.lineNumberArea.update()
                return

            should_hide = folded
            for line_num in range(region.start_line + 1, region.end_line + 1):
                block = doc.findBlockByNumber(line_num - 1)
                if block.isValid():
                    if should_hide:
                        block.setVisible(False)
                    else:
                        # Only make visible if not hidden by another folded region
                        if not self._is_line_hidden_by_other_region(line_num, exclude=region):
                            block.setVisible(True)

            doc.markContentsDirty(0, doc.characterCount() - 1)
            self.viewport().update()
            self.updateLineNumberAreaWidth()
            self.lineNumberArea.update()

            if hasattr(self, 'highlighter') and self.highlighter:
                self.highlighter.rehighlight()
        finally:
            self._folding_in_progress = False

    def _is_line_hidden_by_other_region(self, line_num, exclude=None):
        """Check if line_num is inside another folded region (not exclude)"""
        for region in self.folding_regions:
            if region is exclude:
                continue
            if region.is_folded and region.start_line < line_num <= region.end_line:
                return True
        return False

    def _extract_brace_content(self, line, start_pos):
        """Extract content from braces"""
        if start_pos >= len(line) or line[start_pos] != '{':
            return ""
        depth = 0
        content_start = start_pos + 1
        for i in range(start_pos, len(line)):
            if line[i] == '{':
                depth += 1
            elif line[i] == '}':
                depth -= 1
                if depth == 0:
                    return line[content_start:i]
        return line[content_start:]

    def _get_block_at_y(self, y):
        """Get the QTextBlock at y coordinate"""
        block = self.firstVisibleBlock()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= y:
            if block.isVisible() and bottom >= y:
                return block
            block = block.next()
            if not block.isValid():
                break
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())

        return None

    def _is_foldable_line(self, line_text):
        """Check if a line contains a foldable command"""
        stripped = line_text.strip()
        if not stripped or stripped.startswith('%'):
            return False
        if r'\documentclass' in line_text:
            return True
        if r'\begin{document}' in line_text:
            return True
        if r'\begin{thebibliography}' in line_text:
            return True
        if r'\begin{references}' in line_text:
            return True
        if r'\begin{biblist}' in line_text:
            return True
        section_pattern = re.compile(
            r'\\(part|chapter|section|subsection|subsubsection|paragraph|subparagraph)\*?\s*(\[[^\]]*\])?\s*\{',
            re.IGNORECASE
        )
        if section_pattern.search(line_text):
            return True
        return False


    def _get_region_for_line(self, line_number):
        """Get fold region whose start_line matches line_number"""
        for region in self.folding_regions:
            if region.start_line == line_number:
                return region
        return None

    def toggle_fold_at_line(self, line_number):
        """Toggle fold at the given document line number"""
        block = self.document().findBlockByNumber(line_number - 1)
        if not block.isValid():
            return False

        line_text = block.text()
        if not self._is_foldable_line(line_text):
            return False

        self._parse_folding_regions()
        region = self._get_region_for_line(line_number)
        if region:
            self._set_region_visibility(region, not region.is_folded)
            return True
        return False

    def fold_current_section(self):
        """Fold section at cursor"""
        if self._folding_in_progress:
            return
        cursor = self.textCursor()
        current_line = cursor.blockNumber() + 1

        self._parse_folding_regions()

        target_region = None
        for region in self.folding_regions:
            if not region.is_folded and region.start_line <= current_line <= region.end_line:
                if target_region is None or region.level > target_region.level:
                    target_region = region

        if target_region:
            self._set_region_visibility(target_region, True)

    def unfold_current_section(self):
        """Unfold section at cursor"""
        if self._folding_in_progress:
            return
        cursor = self.textCursor()
        current_line = cursor.blockNumber() + 1

        self._parse_folding_regions()

        for region in self.folding_regions:
            if region.is_folded and region.start_line == current_line:
                self._set_region_visibility(region, False)
                return

    def fold_all(self):
        """Fold ALL regions"""
        main_window = self.get_main_window()
        lang = main_window.menu_language
        tr = main_window.translations[lang]        
        if self._folding_in_progress:
            return
        self._fold_cache_valid = False
        self._parse_folding_regions()

        regions_to_fold = [r for r in self.folding_regions if not r.is_folded]
        if not regions_to_fold:
            main_window = self.get_main_window()
            if main_window and hasattr(main_window, 'update_status_bar'):
                #main_window.update_status_bar("No regions to fold")
                main_window.update_status_bar(
                    tr.get("status_no_region_to_fold", "No regions to fold")
                )
                QTimer.singleShot(
                    2000,
                    lambda: main_window.update_status_bar(
                        tr.get("status_ready", "Ready"),
                        timeout=0
                    )
                )            

            return

        self._folding_in_progress = True
        try:
            doc = self.document()
            folded_count = 0
            for region in regions_to_fold:
                region.is_folded = True
                folded_count += 1
                if region.end_line > region.start_line:
                    for line_num in range(region.start_line + 1, region.end_line + 1):
                        block = doc.findBlockByNumber(line_num - 1)
                        if block.isValid():
                            block.setVisible(False)

            doc.markContentsDirty(0, doc.characterCount() - 1)
            self.viewport().update()
            self.updateLineNumberAreaWidth()
            self.lineNumberArea.update()

            if hasattr(self, 'highlighter') and self.highlighter:
                self.highlighter.rehighlight()
        finally:
            self._folding_in_progress = False

        #main_window = self.get_main_window()
        if main_window and hasattr(main_window, 'update_status_bar'):
            #main_window.update_status_bar(f"Folded {folded_count} regions")
            main_window.update_status_bar(
                tr.get("status_folded_region", "Folded {folded_count} regions").format(folded_count=folded_count)
            )
            QTimer.singleShot(
                2000,
                lambda: main_window.update_status_bar(
                    tr.get("status_ready", "Ready"),
                    timeout=0
                )
            )            


    def unfold_all(self):
        main_window = self.get_main_window()
        lang = main_window.menu_language
        tr = main_window.translations[lang]        
        """Unfold ALL folded regions"""
        if self._folding_in_progress:
            return
        self._parse_folding_regions()

        folded_regions = [r for r in self.folding_regions if r.is_folded]
        if not folded_regions:
            main_window = self.get_main_window()
            if main_window and hasattr(main_window, 'update_status_bar'):
                main_window.update_status_bar("No regions to unfold")
            return

        self._folding_in_progress = True
        try:
            doc = self.document()
            unfolded_count = 0
            for region in folded_regions:
                region.is_folded = False
                unfolded_count += 1

            # Make all blocks visible
            block = doc.begin()
            while block.isValid():
                if not block.isVisible():
                    block.setVisible(True)
                block = block.next()

            doc.markContentsDirty(0, doc.characterCount() - 1)
            self.viewport().update()
            self.updateLineNumberAreaWidth()
            self.lineNumberArea.update()

            if hasattr(self, 'highlighter') and self.highlighter:
                self.highlighter.rehighlight()
        finally:
            self._folding_in_progress = False

        #main_window = self.get_main_window()
        if main_window and hasattr(main_window, 'update_status_bar'):
            #main_window.update_status_bar(f"Unfolded {unfolded_count} regions")
            main_window.update_status_bar(
                tr.get("status_unfolded_region", "Unfolded {unfolded_count} regions").format(unfolded_count=unfolded_count)
            )
            QTimer.singleShot(
                2000,
                lambda: main_window.update_status_bar(
                    tr.get("status_ready", "Ready"),
                    timeout=0
                )
            )            
            

    def fold_level(self, level):
        """Fold sections at or below a specific level"""
        main_window = self.get_main_window()
        lang = main_window.menu_language
        tr = main_window.translations[lang]        
        if self._folding_in_progress:
            return
        self._fold_cache_valid = False
        self._parse_folding_regions()

        sections_to_fold = [r for r in self.folding_regions
                            if r.region_type == "section"
                            and r.level >= level
                            and not r.is_folded]
        if not sections_to_fold:
            main_window = self.get_main_window()
            if main_window and hasattr(main_window, 'update_status_bar'):
                main_window.update_status_bar("No sections to fold at this level")
            return

        self._folding_in_progress = True
        try:
            doc = self.document()
            folded_count = 0
            for region in sections_to_fold:
                region.is_folded = True
                folded_count += 1
                if region.end_line > region.start_line:
                    for line_num in range(region.start_line + 1, region.end_line + 1):
                        block = doc.findBlockByNumber(line_num - 1)
                        if block.isValid():
                            block.setVisible(False)

            doc.markContentsDirty(0, doc.characterCount() - 1)
            self.viewport().update()
            self.updateLineNumberAreaWidth()
            self.lineNumberArea.update()

            if hasattr(self, 'highlighter') and self.highlighter:
                self.highlighter.rehighlight()
        finally:
            self._folding_in_progress = False

        #main_window = self.get_main_window()
        if main_window and hasattr(main_window, 'update_status_bar'):
            level_names = {0: 'parts', 1: 'chapters', 2: 'sections',
                           3: 'subsections', 4: 'subsubsections'}
            level_name = level_names.get(level, f'level {level}')
            #main_window.update_status_bar(f"Folded {folded_count} {level_name}")
            main_window.update_status_bar(
                tr.get("status_folded_level", "Folded {folded_count} {level_name}")
                  .format(folded_count=folded_count, level_name=level_name)
            )

            QTimer.singleShot(
                2000,
                lambda: main_window.update_status_bar(
                    tr.get("status_ready", "Ready"),
                    timeout=0
                )
            )            

    def fold_preamble(self):
        if self._folding_in_progress:
            return
        self._parse_folding_regions()
        for region in self.folding_regions:
            if region.region_type == 'preamble' and not region.is_folded:
                self._set_region_visibility(region, True)
                return

    def unfold_preamble(self):
        if self._folding_in_progress:
            return
        self._parse_folding_regions()
        for region in self.folding_regions:
            if region.region_type == 'preamble' and region.is_folded:
                self._set_region_visibility(region, False)
                return

    def fold_document_begin(self):
        if self._folding_in_progress:
            return
        self._parse_folding_regions()
        for region in self.folding_regions:
            if region.region_type == 'document_begin' and not region.is_folded:
                self._set_region_visibility(region, True)
                return

    def unfold_document_begin(self):
        if self._folding_in_progress:
            return
        self._parse_folding_regions()
        for region in self.folding_regions:
            if region.region_type == 'document_begin' and region.is_folded:
                self._set_region_visibility(region, False)
                return


    def fold_bibliography(self):
        if self._folding_in_progress:
            return
        self._parse_folding_regions()
        for region in self.folding_regions:
            if region.region_type == 'bibliography' and not region.is_folded:
                self._set_region_visibility(region, True)
                return

    def unfold_bibliography(self):
        if self._folding_in_progress:
            return
        self._parse_folding_regions()
        for region in self.folding_regions:
            if region.region_type == 'bibliography' and region.is_folded:
                self._set_region_visibility(region, False)
                return

    def toggle_bibliography_fold(self):
        if self._folding_in_progress:
            return
        self._parse_folding_regions()
        for region in self.folding_regions:
            if region.region_type == 'bibliography':
                self._set_region_visibility(region, not region.is_folded)
                return


    # ==========================================
    # FILE / BOOKMARK METHODS
    # ==========================================

    def set_file_path(self, file_path):
        self.file_path = file_path
        main_window = self.get_main_window()
        if main_window and hasattr(main_window, 'bookmarks_widget'):
            self.sync_bookmarks_with_widget(main_window.bookmarks_widget)


    def get_main_window(self):
        parent = self.parent()
        while parent:
            if hasattr(parent, 'editor_manager'):
                return parent
            parent = parent.parent()
        return None

    def toggle_bookmark_at(self, y):
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())
        while block.isValid() and top <= y:
            if block.isVisible() and bottom >= y:
                line_number = block_number + 1
                text_snippet = block.text()
                main_window = self.get_main_window()
                if main_window and hasattr(main_window, 'bookmarks_widget'):
                    current_file_path = getattr(self, 'file_path', None)
                    was_added = main_window.bookmarks_widget.toggle_bookmark(
                        line_number, text_snippet, current_file_path)
                    if was_added:
                        self.bookmarked_lines.add(line_number)
                    else:
                        self.bookmarked_lines.discard(line_number)
                    self.lineNumberArea.update()
                    if current_file_path:
                        file_name = os.path.basename(current_file_path)
                    else:
                        file_name = "Untitled"
                    status_msg = f"Bookmark {'added' if was_added else 'removed'} at line {line_number} in {file_name}"
                    if hasattr(main_window, 'update_status_bar'):
                        main_window.update_status_bar(status_msg)
                break
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    def toggle_current_line_bookmark(self):
        cursor = self.textCursor()
        line_number = cursor.blockNumber() + 1
        current_block = cursor.block()
        text_snippet = current_block.text()
        current_file_path = getattr(self, 'file_path', None)
        main_window = self.get_main_window()
        if main_window and hasattr(main_window, 'bookmarks_widget'):
            was_added = main_window.bookmarks_widget.toggle_bookmark(
                line_number, text_snippet, current_file_path)
            if was_added:
                self.bookmarked_lines.add(line_number)
            else:
                self.bookmarked_lines.discard(line_number)
            self.lineNumberArea.update()
            if current_file_path:
                file_name = os.path.basename(current_file_path)
            else:
                file_name = "Untitled"
            status_msg = f"Bookmark {'added' if was_added else 'removed'} at line {line_number} in {file_name}"
            if hasattr(main_window, 'update_status_bar'):
                main_window.update_status_bar(status_msg)

    # ==========================================
    # LINE NUMBER AREA PAINTING
    # ==========================================

    def lineNumberAreaPaintEvent(self, event):
        """Paint line numbers with fold markers"""
        painter = QPainter(self.lineNumberArea)
        
        try:
            c = self._get_theme_colors()          # ← single call, all colors from here

            if not self._line_numbers_visible and not self._fold_markers_visible:
                painter.fillRect(event.rect(), QColor(c["ln_bg"]))
                return

            total_width = self.lineNumberAreaWidth()
            fold_width = LineNumberArea.FOLD_MARKER_WIDTH if (
                self._fold_markers_visible and self._folding_enabled) else 0
            number_width = (total_width - fold_width) if self._line_numbers_visible else 0

            if self.is_rtl_mode:
                fold_area_x   = 0
                number_area_x = fold_width
            else:
                fold_area_x   = number_width
                number_area_x = 0

            # ── backgrounds ──────────────────────────────────────────────────────
            if self._line_numbers_visible:
                painter.fillRect(
                    QRect(number_area_x, event.rect().top(), number_width, event.rect().height()),
                    QColor(c["ln_bg"]))

            if fold_width > 0:
                painter.fillRect(
                    QRect(fold_area_x, event.rect().top(), fold_width, event.rect().height()),
                    QColor(c["fold_bg"]))
                painter.setPen(QPen(QColor(c["fold_separator"]), 1))
                sep_x = (fold_area_x + fold_width) if self.is_rtl_mode else fold_area_x
                painter.drawLine(sep_x, event.rect().top(), sep_x, event.rect().bottom())

            if self._fold_markers_visible:
                self._parse_folding_regions()

            region_start_map = {}
            if self._fold_markers_visible:
                for region in self.folding_regions:
                    region_start_map[region.start_line] = region

        
            block = self.firstVisibleBlock()
            if not block.isValid():
                return
            block_number = block.blockNumber()
            top    = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
            bottom = top + int(self.blockBoundingRect(block).height())

            while block.isValid() and top <= event.rect().bottom():
                if block.isVisible() and bottom >= event.rect().top():
                    line_number  = block_number + 1
                    block_height = int(self.blockBoundingRect(block).height())
                    line_text    = block.text()

                    fold_region = region_start_map.get(line_number) if self._fold_markers_visible else None
                    if fold_region and not self._is_foldable_line(line_text):
                        fold_region = None

                    is_fold_start = fold_region is not None
                    is_hover      = (line_number == self.lineNumberArea._hover_line)
                    is_bookmarked = line_number in self.bookmarked_lines

                    # ── line numbers ──────────────────────────────────────────
                    if self._line_numbers_visible:
                        if is_bookmarked:
                            painter.fillRect(
                                QRect(number_area_x, top, number_width, block_height),
                                QColor(c["ln_bookmark_bg"]))

                        font = painter.font()
                        if is_bookmarked:
                            painter.setPen(QColor(c["ln_text_bookmark"]))
                            font.setBold(True)
                        else:
                            painter.setPen(QColor(c["ln_text"]))
                            font.setBold(False)
                        painter.setFont(font)
                        LINE_NUMBER_PADDING = 2
                        
                        text_rect = QRect(number_area_x, top,
                                          number_width, self.fontMetrics().height())
                            
                        #align = Qt.AlignLeft if self.is_rtl_mode else Qt.AlignRight
                        align = Qt.AlignCenter
                        painter.drawText(text_rect, align | Qt.AlignVCenter, str(line_number))

                    # ── fold markers ──────────────────────────────────────────
                    if self._fold_markers_visible and self._folding_enabled:
                        if is_fold_start:
                            self._draw_fold_marker(
                                painter, fold_area_x, top, block_height,
                                fold_region.is_folded, is_hover, fold_region.region_type)
                        else:
                            self._draw_fold_scope_line(
                                painter, line_number,
                                fold_area_x, fold_width, top, bottom)

                block = block.next()
                if not block.isValid():
                    break
                top    = bottom
                bottom = top + int(self.blockBoundingRect(block).height())
                block_number = block.blockNumber()

        except Exception as e:
            print(f"Error in lineNumberAreaPaintEvent: {e}")
            import traceback
            traceback.print_exc()      

        finally:
            painter.end()   # 🔥 guarantees Qt is always safe            

    def _draw_fold_scope_line(self, painter, line_number, fold_area_x, fold_width, top, bottom):
        """Draw vertical line showing fold scope"""
        c = self._get_theme_colors()
        center_x = fold_area_x + fold_width // 2
        for region in self.folding_regions:
            if region.is_folded:
                continue
            if region.start_line < line_number <= region.end_line:
                key = {
                    "preamble":       "scope_preamble",
                    "document_begin": "scope_doc_begin",
                    "bibliography":   "scope_biblio",
                }.get(region.region_type, "scope_section")
                painter.setPen(QPen(QColor(c[key]), 1))
                painter.drawLine(center_x, top, center_x, bottom)
                break


    def _draw_fold_marker(self, painter, x, y, height, is_folded, is_hover, region_type="section"):
        """Draw [+] or [-] fold marker"""
        c = self._get_theme_colors()
        marker_size  = 14
        margin_top   = (height - marker_size) // 2
        marker_x     = x + (LineNumberArea.FOLD_MARKER_WIDTH - marker_size) // 2
        marker_y     = y + margin_top
        rect         = QRect(marker_x, marker_y, marker_size, marker_size)

        prefix = {
            "preamble":       "pre",
            "document_begin": "doc",
            "bibliography":   "bib",
        }.get(region_type, "sec")
        suffix = "_h" if is_hover else ""

        border_color = QColor(c[f"{prefix}_border{suffix}"])
        fill_color   = QColor(c[f"{prefix}_fill{suffix}"])
        symbol_color = QColor(c[f"{prefix}_symbol{suffix}"])

        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(QPen(border_color, 1.5))
        painter.setBrush(QBrush(fill_color))
        painter.drawRoundedRect(rect, 2, 2)

        cx = rect.x() + rect.width()  / 2.0
        cy = rect.y() + rect.height() / 2.0
        half = (marker_size - 4) / 2.0

        pen = QPen(symbol_color, 2.0)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.drawLine(QPoint(int(cx - half), int(cy)),
                         QPoint(int(cx + half), int(cy)))
        if is_folded:
            painter.drawLine(QPoint(int(cx), int(cy - half)),
                             QPoint(int(cx), int(cy + half)))
        painter.setRenderHint(QPainter.Antialiasing, False)

    # ==========================================
    # BOOKMARK SYNC
    # ==========================================

    def sync_bookmarks_with_widget(self, bookmarks_widget):
        current_file_path = getattr(self, 'file_path', None)
        if not current_file_path:
            current_file_path = bookmarks_widget.get_current_file_path() or "Untitled"
        if current_file_path in bookmarks_widget.bookmarks:
            self.bookmarked_lines = set(bookmarks_widget.bookmarks[current_file_path].keys())
        else:
            self.bookmarked_lines = set()
        self.lineNumberArea.update()

    # ==========================================
    # RTL / ALIGNMENT
    # ==========================================

    def updateLineNumberAreaWidth(self):
        line_number_width = self.lineNumberAreaWidth()
        if self.is_rtl_mode:
            self.setViewportMargins(0, 0, line_number_width, 0)
        else:
            self.setViewportMargins(line_number_width, 0, 0, 0)
        self.lineNumberArea.update()
        self.viewport().update()

    def updateLineNumberAreaPosition(self):
        cr = self.contentsRect()
        line_width = self.lineNumberAreaWidth()
        if self.is_rtl_mode:
            self.lineNumberArea.setGeometry(
                QRect(cr.right() - line_width, cr.top(), line_width, cr.height()))
        else:
            self.lineNumberArea.setGeometry(
                QRect(cr.left(), cr.top(), line_width, cr.height()))


    # Padding on each side of the line number text (pixels)
    LINE_NUMBER_PADDING = 0

    def lineNumberAreaWidth(self):
        if not self._line_numbers_visible and not self._fold_markers_visible:
            return 0
        width = 0
        if self._line_numbers_visible:
            max_num = max(1, self.blockCount())
            text_width = self.fontMetrics().horizontalAdvance(str(max_num))
            width += text_width + 2 * self.LINE_NUMBER_PADDING
        if self._fold_markers_visible:
            width += LineNumberArea.FOLD_MARKER_WIDTH
        return width

        
    def updateLineNumberArea(self):
        if not self._folding_in_progress:
            self._fold_cache_valid = False
        self.lineNumberArea.update()
        self.viewport().update()

    def scrollContentsBy(self, dx, dy):
        super().scrollContentsBy(dx, dy)
        self.lineNumberArea.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.updateLineNumberAreaPosition()

    # ==========================================
    # KEY PRESS EVENT
    # ==========================================

    def keyPressEvent(self, event):
        """Handle key events with completion and delimiter support"""
        # ✅ 1. CHECK IF COMPLETION IS ENABLED FIRST
        completion_enabled = True
        main_window = self.get_main_window()
        if main_window and hasattr(main_window, 'config_manager'):
            try:
                completion_enabled = main_window.config_manager.get_config_value(
                    'cwl_completion', 'enabled', 'True'
                ).lower() == 'true'
            except:
                pass

        # ✅ 2. HANDLE CWL COMPLETER POPUP FIRST
        if hasattr(self, '_cwl_completer') and self._cwl_completer:
            if self._cwl_completer.is_popup_visible():
                if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab):
                    popup = self._cwl_completer.completer.popup()
                    index = popup.currentIndex()
                    if index.isValid():
                        self._cwl_completer.insert_completion(index.data(Qt.DisplayRole))
                    self._cwl_completer.hide_popup()
                    event.accept()
                    return
                elif event.key() == Qt.Key_Escape:
                    self._cwl_completer.hide_popup()
                    event.accept()
                    return
                elif event.key() in (Qt.Key_Up, Qt.Key_Down, Qt.Key_PageUp, Qt.Key_PageDown):
                    self._cwl_completer.completer.popup().keyPressEvent(event)
                    return

        # ✅ 3. AVOID RECURSION
        if getattr(self, '_processing_delimiter', False):
            super().keyPressEvent(event)
            return

        # ✅ 4. HANDLE LATEX SHORTCUTS (Ctrl+Shift+Key)
        if event.modifiers() == (Qt.ControlModifier | Qt.ShiftModifier):
            if event.key() == Qt.Key_D:
                self.insert_subscript()
                return
            elif event.key() == Qt.Key_U:
                self.insert_superscript()
                return
            elif event.key() == Qt.Key_F:
                self.insert_fraction()
                return
            elif event.key() == Qt.Key_I:
                self.insert_item()
                return
            elif event.key() == Qt.Key_E:
                self.insert_equation()
                return
            elif event.key() == Qt.Key_M:
                self.insert_math()
                return

        # ✅ 5. HANDLE ALT+ENTER
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and event.modifiers() == Qt.AltModifier:
            self._handle_alt_enter()
            return

        cursor = self.textCursor()
        key_text = event.text()

        # ✅ 6. HANDLE LATEX DELIMITER COMPLETION (backslash + bracket)
        if self._backslash_selection_state and key_text in ['(', '[', '{', '|']:
            if self._complete_latex_delimiter(key_text):
                return

        # ✅ 7. HANDLE DELIMITER WRAPPING FOR SELECTED TEXT
        if cursor.hasSelection():
            if key_text == '\\':
                self._backslash_selection_state = {
                    'start': cursor.selectionStart(),
                    'end': cursor.selectionEnd(),
                    'text': cursor.selectedText()
                }
                super().keyPressEvent(event)
                return
            if key_text in ['(', '[', '$', '{', '|', '"']:
                selected_text = cursor.selectedText()
                pairs = {'(': ')', '[': ']', '$': '$', '{': '}', '|': '|', '"': '"'}
                if key_text in pairs:
                    self._processing_delimiter = True
                    try:
                        right = pairs[key_text]
                        cursor.insertText(key_text + selected_text + right)
                        event.accept()
                        return
                    finally:
                        self._processing_delimiter = False
        else:
            self._backslash_selection_state = None

        # ✅ 8. HANDLE ENTER - auto-unfold if inside/adjacent to folded region
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            current_line = cursor.blockNumber() + 1
            self._auto_unfold_for_edit(current_line)

            current_alignment = getattr(self, '_current_alignment', Qt.AlignLeft)
            is_rtl = getattr(self, 'is_rtl_mode', False)

            # Suppress fold reapply during the edit
            self._suppress_fold_reapply = True
            super().keyPressEvent(event)
            self._suppress_fold_reapply = False

            # Ensure the new block is visible
            new_cursor = self.textCursor()
            new_block = new_cursor.block()
            if new_block.isValid() and not new_block.isVisible():
                new_block.setVisible(True)
                self.document().markContentsDirty(
                    new_block.position(),
                    new_block.position() + new_block.length()
                )

            # Apply alignment
            block_format = new_cursor.blockFormat()
            block_format.setAlignment(current_alignment)
            if is_rtl:
                block_format.setLayoutDirection(Qt.RightToLeft)
            else:
                block_format.setLayoutDirection(Qt.LeftToRight)
            new_cursor.setBlockFormat(block_format)
            return

        # ✅ 9. AUTO-UNFOLD for other typing keys (printable characters, backspace, delete)
        if event.key() in (Qt.Key_Backspace, Qt.Key_Delete) or (key_text and key_text.isprintable()):
            current_line = cursor.blockNumber() + 1
            self._auto_unfold_for_edit(current_line)

        # ✅ 10. DEFAULT BEHAVIOR
        self._suppress_fold_reapply = True
        super().keyPressEvent(event)
        self._suppress_fold_reapply = False

        # Ensure current block is visible after typing
        post_cursor = self.textCursor()
        post_block = post_cursor.block()
        if post_block.isValid() and not post_block.isVisible():
            post_block.setVisible(True)
            self.document().markContentsDirty(
                post_block.position(),
                post_block.position() + post_block.length()
            )
              
        # ✅ 11. TRIGGER CWL COMPLETION AFTER KEY PRESS (only if enabled, typing only)
        _modifier_only = event.key() in (
            Qt.Key_Shift, Qt.Key_Control, Qt.Key_Alt, Qt.Key_Meta,
            Qt.Key_CapsLock, Qt.Key_NumLock, Qt.Key_ScrollLock,
        )
        _is_navigation = event.key() in (
            Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down,
            Qt.Key_Home, Qt.Key_End, Qt.Key_PageUp, Qt.Key_PageDown,
        )
        _has_modifier = bool(event.modifiers() & (
            Qt.ShiftModifier | Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier
        ))
        if completion_enabled and hasattr(self, '_cwl_completer') and self._cwl_completer:
            if not (hasattr(self, '_refcite_completer') and
                    self._refcite_completer and
                    self._refcite_completer.is_popup_visible()):
                if not _modifier_only and not _is_navigation and not _has_modifier:
                    QTimer.singleShot(10, self._cwl_completer.handle_keypress)                

        # Maintain alignment
        if hasattr(self, '_current_alignment'):
            cursor = self.textCursor()
            block_format = cursor.blockFormat()
            if block_format.alignment() != self._current_alignment:
                block_format.setAlignment(self._current_alignment)
                if self.is_rtl_mode:
                    block_format.setLayoutDirection(Qt.RightToLeft)
                else:
                    block_format.setLayoutDirection(Qt.LeftToRight)
                cursor.setBlockFormat(block_format)
                
    def _auto_unfold_for_edit(self, current_line):
        """Auto-unfold any folded region that contains or starts at current_line.
        
        This ensures the user can always type at any visible line, and
        the region they're editing becomes fully visible.
        """
        self._parse_folding_regions()

        regions_to_unfold = []
        for region in self.folding_regions:
            if not region.is_folded:
                continue
            # Unfold if cursor is on the start line (the visible fold header)
            # or if somehow the cursor ended up inside the folded range
            if region.start_line <= current_line <= region.end_line:
                regions_to_unfold.append(region)

        if not regions_to_unfold:
            return

        # Unfold all affected regions
        self._folding_in_progress = True
        try:
            doc = self.document()
            for region in regions_to_unfold:
                region.is_folded = False
                if region.end_line > region.start_line:
                    for line_num in range(region.start_line + 1, region.end_line + 1):
                        block = doc.findBlockByNumber(line_num - 1)
                        if block.isValid() and not block.isVisible():
                            # Only show if not hidden by another still-folded region
                            if not self._is_line_hidden_by_other_region(line_num, exclude=region):
                                block.setVisible(True)

            doc.markContentsDirty(0, doc.characterCount() - 1)
            self.viewport().update()
            self.updateLineNumberAreaWidth()
            self.lineNumberArea.update()
        finally:
            self._folding_in_progress = False
            
    def _complete_latex_delimiter(self, delimiter_char):
        if not self._backslash_selection_state:
            return False
        self._processing_delimiter = True
        try:
            selected_text = self._backslash_selection_state['text']
            start_pos = self._backslash_selection_state['start']
            latex_left = '\\' + delimiter_char
            latex_right = self.delimiter_pairs.get(latex_left)
            if not latex_right:
                self._backslash_selection_state = None
                return False
            cursor = self.textCursor()
            current_pos = cursor.position()
            cursor.setPosition(start_pos)
            cursor.setPosition(current_pos, QTextCursor.KeepAnchor)
            cursor.insertText(latex_left + selected_text + latex_right)
            self._backslash_selection_state = None
            return True
        except Exception as e:
            print(f"Error completing LaTeX delimiter: {e}")
            self._backslash_selection_state = None
            return False
        finally:
            self._processing_delimiter = False

    def _handle_alt_enter(self):
            cursor = self.textCursor()
            text_up_to_cursor = self.toPlainText()[:cursor.position()]
            begins = list(re.finditer(r"\\begin\{([a-zA-Z0-9_*]+)\}", text_up_to_cursor))
            ends = list(re.finditer(r"\\end\{([a-zA-Z0-9_*]+)\}", text_up_to_cursor))
            if not begins:
                return
            stack = [m.group(1) for m in begins]
            for m in ends:
                if m.group(1) in stack[::-1]:
                    stack.reverse()
                    stack.remove(m.group(1))
                    stack.reverse()
            if not stack:
                return
            env_name = stack[-1]
            end_tag = f"\\end{{{env_name}}}"
            cursor.movePosition(QTextCursor.EndOfLine)
            cursor.insertText(f"\n\n{end_tag}")
            cursor.movePosition(QTextCursor.Up)
            cursor.movePosition(QTextCursor.StartOfLine)
            self.setTextCursor(cursor)
    def focusOutEvent(self, event):
        self._backslash_selection_state = None
        super().focusOutEvent(event)

    def mousePressEvent(self, event):
        self._backslash_selection_state = None
        super().mousePressEvent(event)
        if hasattr(self, 'lineNumberArea'):
            self.lineNumberArea.update()

    # ==========================================
    # HIGHLIGHTING
    # ==========================================
        
    def highlightCurrentLine(self):
        extra_selections = []
        if not self.isReadOnly():
            c = self._get_theme_colors()
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(QColor(c["current_line_bg"]))
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        extra_selections.extend(self.bracket_selections)
        self.setExtraSelections(extra_selections)
        self.lineNumberArea.update()        

    def highlightMatchingBrackets(self):
        self.bracket_selections = []
        cursor = self.textCursor()
        text = self.toPlainText()
        pos = cursor.position()
        if pos > 0 and pos <= len(text) and text[pos - 1] in self.opening_brackets:
            opening_pos = pos - 1
            opening_char = text[opening_pos]
            closing_char = self.bracket_pairs[opening_char]
            closing_pos = self.findMatchingBracket(text, opening_pos, opening_char, closing_char, forward=True)
            if closing_pos != -1:
                self.addBracketHighlight(opening_pos, closing_pos)
        elif pos < len(text) and text[pos] in self.closing_brackets:
            closing_pos = pos
            closing_char = text[closing_pos]
            opening_char = next(k for k, v in self.bracket_pairs.items() if v == closing_char)
            opening_pos = self.findMatchingBracket(text, closing_pos, closing_char, opening_char, forward=False)
            if opening_pos != -1:
                self.addBracketHighlight(opening_pos, closing_pos)
        self.highlightCurrentLine()

    def findMatchingBracket(self, text, start_pos, start_char, target_char, forward=True):
        if forward:
            search_range = range(start_pos + 1, len(text))
        else:
            search_range = range(start_pos - 1, -1, -1)
        level = 1
        for pos in search_range:
            char = text[pos]
            if char == start_char:
                level += 1
            elif char == target_char:
                level -= 1
                if level == 0:
                    return pos
        return -1

    def addBracketHighlight(self, opening_pos, closing_pos):
        opening_selection = QTextEdit.ExtraSelection()
        opening_selection.format.setBackground(QColor("#ffeb3b").lighter(160))
        opening_selection.format.setForeground(QColor("#d32f2f"))
        opening_cursor = self.textCursor()
        opening_cursor.setPosition(opening_pos)
        opening_cursor.setPosition(opening_pos + 1, QTextCursor.KeepAnchor)
        opening_selection.cursor = opening_cursor
        self.bracket_selections.append(opening_selection)

        closing_selection = QTextEdit.ExtraSelection()
        closing_selection.format.setBackground(QColor("#ffeb3b").lighter(160))
        closing_selection.format.setForeground(QColor("#d32f2f"))
        closing_cursor = self.textCursor()
        closing_cursor.setPosition(closing_pos)
        closing_cursor.setPosition(closing_pos + 1, QTextCursor.KeepAnchor)
        closing_selection.cursor = closing_cursor
        self.bracket_selections.append(closing_selection)

    # ==========================================
    # CONTENT MANAGEMENT
    # ==========================================

    def setContentSafely(self, content, restore_cursor=False):
        self.blockSignals(True)
        self.document().blockSignals(True)
        try:
            old_cursor_pos = 0
            if restore_cursor:
                old_cursor_pos = self.textCursor().position()
            self.setPlainText(content)
            cursor = self.textCursor()
            if restore_cursor and old_cursor_pos <= len(content):
                cursor.setPosition(old_cursor_pos)
            else:
                cursor.movePosition(QTextCursor.Start)
            self.setTextCursor(cursor)
            if not restore_cursor:
                self.verticalScrollBar().setValue(0)
                self.horizontalScrollBar().setValue(0)
        finally:
            self.document().blockSignals(False)
            self.blockSignals(False)

        # Reset all fold states when content is replaced
        self.folding_regions = []
        self._fold_cache_valid = False
        self.updateLineNumberAreaWidth()
        self.updateLineNumberArea()
        self.highlightCurrentLine()
        self.ensureCursorVisible()


    def loadFileContent(self, content):
        """Load file content - all fold states reset to unfolded"""
        self.setContentSafely(content, restore_cursor=False)
        self._fold_cache_valid = False
        self._parse_folding_regions()
        cursor = self.textCursor()
        if cursor.position() != 0:
            cursor.movePosition(QTextCursor.Start)
            self.setTextCursor(cursor)
        self.verticalScrollBar().setValue(0)
        self.ensureCursorVisible()
        self.lineNumberArea.update()


    def setAlignment(self, alignment):
        self._current_alignment = alignment
        self.is_rtl_mode = (alignment == Qt.AlignRight)
        if self.is_rtl_mode:
            self.setLayoutDirection(Qt.RightToLeft)
        else:
            self.setLayoutDirection(Qt.LeftToRight)
        option = self.document().defaultTextOption()
        if self.is_rtl_mode:
            option.setTextDirection(Qt.RightToLeft)
            option.setAlignment(Qt.AlignRight)
        else:
            option.setTextDirection(Qt.LeftToRight)
            option.setAlignment(Qt.AlignLeft)
        self.document().setDefaultTextOption(option)
        cursor = QTextCursor(self.document())
        cursor.movePosition(QTextCursor.Start)
        block = self.document().firstBlock()
        while block.isValid():
            cursor.setPosition(block.position())
            block_format = cursor.blockFormat()
            block_format.setAlignment(alignment)
            if self.is_rtl_mode:
                block_format.setLayoutDirection(Qt.RightToLeft)
            else:
                block_format.setLayoutDirection(Qt.LeftToRight)
            cursor.setBlockFormat(block_format)
            block = block.next()
        self.updateLineNumberAreaWidth()
        self.updateLineNumberAreaPosition()
        self.update()
        self.viewport().update()
        self.lineNumberArea.update()

    def insertFromMimeData(self, source):
        current_alignment = getattr(self, '_current_alignment', Qt.AlignLeft)
        is_rtl = getattr(self, 'is_rtl_mode', False)
        super().insertFromMimeData(source)
        cursor = self.textCursor()
        start_pos = cursor.selectionStart() if cursor.hasSelection() else cursor.position()
        end_pos = cursor.selectionEnd() if cursor.hasSelection() else cursor.position()
        start_block = self.document().findBlock(start_pos)
        end_block = self.document().findBlock(end_pos)
        block = start_block
        while block.isValid() and block.blockNumber() <= end_block.blockNumber():
            cursor.setPosition(block.position())
            block_format = cursor.blockFormat()
            block_format.setAlignment(current_alignment)
            if is_rtl:
                block_format.setLayoutDirection(Qt.RightToLeft)
            else:
                block_format.setLayoutDirection(Qt.LeftToRight)
            cursor.setBlockFormat(block_format)
            if block.blockNumber() == end_block.blockNumber():
                break
            block = block.next()

    def _ensure_block_alignment(self):
        if not hasattr(self, '_current_alignment'):
            return
        last_block = self.document().lastBlock()
        if last_block.isValid():
            cursor = QTextCursor(last_block)
            block_format = cursor.blockFormat()
            if block_format.alignment() != self._current_alignment:
                block_format.setAlignment(self._current_alignment)
                if self.is_rtl_mode:
                    block_format.setLayoutDirection(Qt.RightToLeft)
                else:
                    block_format.setLayoutDirection(Qt.LeftToRight)
                cursor.setBlockFormat(block_format)

    # ==========================================
    # LATEX INSERTION HELPERS
    # ==========================================

    def insert_subscript(self):
        cursor = self.textCursor()
        if cursor.hasSelection():
            selected_text = cursor.selectedText()
            cursor.insertText(f"_{{{selected_text}}}")
        else:
            cursor.insertText("_{}")
            cursor.movePosition(QTextCursor.Left, QTextCursor.MoveAnchor, 1)
            self.setTextCursor(cursor)

    def insert_superscript(self):
        cursor = self.textCursor()
        if cursor.hasSelection():
            selected_text = cursor.selectedText()
            cursor.insertText(f"^{{{selected_text}}}")
        else:
            cursor.insertText("^{}")
            cursor.movePosition(QTextCursor.Left, QTextCursor.MoveAnchor, 1)
            self.setTextCursor(cursor)

    def insert_fraction(self):
        cursor = self.textCursor()
        if cursor.hasSelection():
            selected_text = cursor.selectedText()
            cursor.insertText(f"\\frac{{{selected_text}}}{{#}}")
            cursor.movePosition(QTextCursor.Left, QTextCursor.MoveAnchor, 2)
            cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, 1)
            self.setTextCursor(cursor)
        else:
            cursor.insertText("\\frac{}{}")
            cursor.movePosition(QTextCursor.Left, QTextCursor.MoveAnchor, 3)
            self.setTextCursor(cursor)

    def insert_item(self):
        cursor = self.textCursor()
        cursor.insertText("\\item ")

    def insert_equation(self):
        cursor = self.textCursor()
        if cursor.hasSelection():
            selected_text = cursor.selectedText()
            equation_text = f"\\begin{{equation*}}\n{selected_text}\n\\end{{equation*}}"
            cursor.insertText(equation_text)
        else:
            cursor.insertText("\\begin{equation*}\n\n\\end{equation*}")
            cursor.movePosition(QTextCursor.Left, QTextCursor.MoveAnchor, 16)
            self.setTextCursor(cursor)

    def insert_math(self):
        cursor = self.textCursor()
        if cursor.hasSelection():
            selected_text = cursor.selectedText()
            cursor.insertText(f"${selected_text}$")
        else:
            cursor.insertText("$ $")
            cursor.movePosition(QTextCursor.Left, QTextCursor.MoveAnchor, 1)
            self.setTextCursor(cursor)

    # ==========================================
    # CONTEXT MENU
    # ==========================================

    def contextMenuEvent(self, event):
        """Forward context menu events to the unified context menu manager."""
        main_window = self.get_main_window()
        if main_window and hasattr(main_window, 'context_menu_manager'):
            # Use the unified manager (spell check, LaTeX commands, bookmarks, etc.)
            main_window.context_menu_manager.show_unified_menu(self, event.pos())
            event.accept()
        else:
            # Fallback – keep base behavior for safety
            super().contextMenuEvent(event)    

    
    def _ctx_insert_latex(self, latex_code):
        from PyQt5.QtGui import QTextCursor
        cursor = self.textCursor()
        if cursor.hasSelection():
            selected_text = cursor.selectedText()
            latex_code = latex_code.replace('•', selected_text, 1)
            latex_code = latex_code.replace('•', '')
            cursor.beginEditBlock()
            cursor.insertText(latex_code)
            cursor.endEditBlock()
        else:
            placeholder_pos = latex_code.find('•')
            clean_code = latex_code.replace('•', '')
            cursor.beginEditBlock()
            start_pos = cursor.position()
            cursor.insertText(clean_code)
            if placeholder_pos != -1:
                cursor.setPosition(start_pos + placeholder_pos)
            cursor.endEditBlock()
        self.setTextCursor(cursor)
        self.setFocus()