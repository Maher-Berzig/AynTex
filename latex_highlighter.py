# latex_highlighter.py - Enhanced with dynamic color support

from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QFont, QColor
from PyQt5.QtCore import QRegExp, Qt, QTimer
import re


class LaTeXHighlighter(QSyntaxHighlighter):
    def __init__(self, document, config_manager=None):
        super().__init__(document)
        self.config_manager = config_manager
        self.spell_checker = None
        self.spell_map = {}   # {block_no: [(rel_start, rel_end, color_str)]}
        self._highlight_cache = {} 
        
        # Initialize color map with defaults
        self.color_map = self._get_default_colors()
        
        # Load colors from config if available
        if self.config_manager:
            self.load_colors_from_config()
        
        # Initialize highlighting rules
        self.highlighting_rules = []
        self.setup_highlighting_rules()
        
        # Multi-line states
        self.NORMAL = 0
        self.INLINE_MATH = 1
        self.DISPLAY_MATH = 2
        self.COMMENT = 3
        
 

    def set_spell_checker(self, spell_checker):
        """Attach or detach a spell checker then rehighlight."""
        self.spell_checker = spell_checker
        self.rehighlight_incremental()

    def set_spell_checker_no_rehighlight(self, spell_checker):
        """Attach spell checker without triggering a full rehighlight.
        Used when the caller will schedule its own incremental rehighlight."""
        self.spell_checker = spell_checker
    
    def _get_default_colors(self):
        """Get default color scheme"""
        return {
            'command': QColor(0, 0, 139),  # Dark blue
            'environment': QColor(139, 0, 139),  # Dark magenta
            'inline_math': QColor(0, 100, 0),  # Dark green
            'display_math': QColor(0, 128, 0),  # Green
            'brace': QColor(139, 0, 0),  # Dark red
            'paren': QColor(0, 0, 180),
            'parameter': QColor(255, 140, 0),  # Dark orange
            'optional': QColor(184, 134, 11),  # Dark goldenrod
            'comment': QColor(128, 128, 128),  # Gray
            'special': QColor(128, 0, 128),  # Purple
            'reference': QColor(25, 25, 112),  # Midnight blue
            'inline_math_bg': QColor(0, 0, 0, 0),  # Transparent
            'display_math_bg': QColor(0, 0, 0, 0),  # Transparent
        }
    
    def load_colors_from_config(self):
        """Load colors from config manager"""
        if not self.config_manager:
            return
        
        colors = self.config_manager.get_all_colors()
        for key, color_str in colors.items():
            color = QColor(color_str)
            if color.isValid():
                self.color_map[key] = color
    
    def update_colors(self, color_map):
        """Update colors dynamically"""
        #print(f"🔄 Updating highlighter colors with {len(color_map)} colors")
        
        # Update the color map
        for key, color in color_map.items():
            if isinstance(color, QColor):
                self.color_map[key] = color
            else:
                # If it's a string, convert to QColor
                self.color_map[key] = QColor(color)
        
        # Rebuild highlighting rules with new colors
        self.highlighting_rules = []
        self.setup_highlighting_rules()
        
        #print(f"✅ Highlighter updated with new colors")


    def apply_brace_coloring(self, text):
        """
        Walk the text and color braces, brackets, and parentheses consistently.
        Skips escaped characters: \{ \} \[ \] \( \)
        """
        # Build a set of positions that are preceded by backslash → skip them
        escaped = set()
        i = 0
        while i < len(text):
            if text[i] == '\\' and i + 1 < len(text):
                escaped.add(i + 1)  # the character after \ is escaped
                i += 2
            else:
                i += 1

        # --- Curly braces {} ---
        stack = []
        for i, ch in enumerate(text):
            if i in escaped:
                continue
            if ch == '{':
                stack.append(i)
                self.setFormat(i, 1, self.brace_format)
            elif ch == '}':
                self.setFormat(i, 1, self.brace_format)
                if stack:
                    open_pos = stack.pop()
                    content_start = open_pos + 1
                    content_len = i - content_start
                    if content_len > 0:
                        self.setFormat(content_start, content_len, self.parameter_format)
                    self.setFormat(open_pos, 1, self.brace_format)
                    self.setFormat(i, 1, self.brace_format)

        # --- Square brackets [] ---
        sq_stack = []
        for i, ch in enumerate(text):
            if i in escaped:
                continue
            if ch == '[':
                sq_stack.append(i)
                self.setFormat(i, 1, self.brace_format)
            elif ch == ']':
                self.setFormat(i, 1, self.brace_format)
                if sq_stack:
                    open_pos = sq_stack.pop()
                    content_start = open_pos + 1
                    content_len = i - content_start
                    if content_len > 0:
                        self.setFormat(content_start, content_len, self.optional_format)
                    self.setFormat(open_pos, 1, self.brace_format)
                    self.setFormat(i, 1, self.brace_format)

        # --- Parentheses () ---
        paren_stack = []
        for i, ch in enumerate(text):
            if i in escaped:
                continue
            if ch == '(':
                paren_stack.append(i)
                self.setFormat(i, 1, self.paren_format)
            elif ch == ')':
                self.setFormat(i, 1, self.paren_format)
                if paren_stack:
                    open_pos = paren_stack.pop()
                    self.setFormat(open_pos, 1, self.paren_format)
        
        
    def setup_highlighting_rules(self):
        """Setup all highlighting rules with colors from color_map"""
        # Command format
        command_format = QTextCharFormat()
        command_format.setForeground(self.color_map.get('command', QColor(0, 0, 139)))
        command_format.setFontWeight(QFont.Bold)
        
        command_patterns = [
            r'\\[a-zA-Z]+\*?',
            r'\\[^a-zA-Z\s]',
        ]
        for pattern in command_patterns:
            self.highlighting_rules.append((QRegExp(pattern), command_format))
        
        # Environment format
        environment_format = QTextCharFormat()
        environment_format.setForeground(self.color_map.get('environment', QColor(139, 0, 139)))
        environment_format.setFontWeight(QFont.Bold)
        env_pattern = r'\\(begin|end)\{[^}]*\}'
        self.highlighting_rules.append((QRegExp(env_pattern), environment_format))
        
        # Math mode formats
        inline_math_format = QTextCharFormat()
        inline_math_format.setForeground(self.color_map.get('inline_math', QColor(0, 100, 0)))
        #inline_math_format.setBackground(self.color_map.get('inline_math_bg', QColor(240, 255, 240)))
        inline_math_bg = self.color_map.get('inline_math_bg', QColor(0, 0, 0, 0))
        if inline_math_bg.alpha() > 0:
            inline_math_format.setBackground(inline_math_bg)
        else:
            inline_math_format.clearBackground()
        
        display_math_format = QTextCharFormat()
        display_math_format.setForeground(self.color_map.get('display_math', QColor(0, 128, 0)))
        #display_math_format.setBackground(self.color_map.get('display_math_bg', QColor(235, 255, 235)))
        display_math_format.setFontWeight(QFont.Bold)
        display_math_bg = self.color_map.get('display_math_bg', QColor(0, 0, 0, 0))
        if display_math_bg.alpha() > 0:
            display_math_format.setBackground(display_math_bg)
        else:
            display_math_format.clearBackground()


        
        # Store math formats as instance variables for use in highlight methods
        self.inline_math_format = inline_math_format
        self.display_math_format = display_math_format
        
        # Display math patterns  
        display_math_patterns = [
            r'\\\[[^\]]*\\\]',
            r'\$\$[^$]*\$\$',
        ]
        for pattern in display_math_patterns:
            self.highlighting_rules.append((QRegExp(pattern), display_math_format))
        

        # Parameters and arguments — full span including delimiters 
        parameter_format = QTextCharFormat()
        parameter_format.setForeground(self.color_map.get('parameter', QColor(255, 140, 0)))
        param_pattern = r'\{[^}]*\}'
        self.highlighting_rules.append((QRegExp(param_pattern), parameter_format))
        # Optional parameters
        optional_format = QTextCharFormat()
        optional_format.setForeground(self.color_map.get('optional', QColor(184, 134, 11)))
        optional_pattern = r'\[[^\]]*\]'
        self.highlighting_rules.append((QRegExp(optional_pattern), optional_format))
        # Parentheses — stored as instance variable so apply_brace_coloring()
        # always uses the current color after update_colors() rebuilds the rules.
        paren_format = QTextCharFormat()
        paren_format.setForeground(self.color_map.get('paren', QColor(0, 0, 180)))
        paren_format.setFontWeight(QFont.Bold)        
        # Braces and brackets — LAST so they always repaint the delimiters
        # in brace_color, overriding whatever param/optional colored them.
        brace_format = QTextCharFormat()
        brace_format.setForeground(self.color_map.get('brace', QColor(139, 0, 0)))
        brace_format.setFontWeight(QFont.Bold)
        brace_patterns = [r'[\{\}]', r'[\[\]]']
        for pattern in brace_patterns:
            self.highlighting_rules.append((QRegExp(pattern), brace_format))
        
        # Comments
        comment_format = QTextCharFormat()
        comment_format.setForeground(self.color_map.get('comment', QColor(128, 128, 128)))
        comment_format.setFontItalic(True)
        comment_pattern = r'%.*$'
        self.highlighting_rules.append((QRegExp(comment_pattern), comment_format))
        
        # Special characters
        # special_format = QTextCharFormat()
        # special_format.setForeground(self.color_map.get('special', QColor(128, 0, 128)))
        # special_format.setFontWeight(QFont.Bold)
        # special_patterns = [
            # r'\\&', r'\\\$', r'\\%', r'\\#', 
            # r'\\_', r'\\\^', r'\\~',
        # ]
        # for pattern in special_patterns:
            # self.highlighting_rules.append((QRegExp(pattern), special_format))
        # Special characters
        special_format = QTextCharFormat()
        special_format.setForeground(self.color_map.get('special', QColor(128, 0, 128)))
        special_format.setFontWeight(QFont.Bold)
        special_patterns = [
            r'\\&', r'\\\$', r'\\%', r'\\#',
            r'\\_', r'\\\^', r'\\~',
            r'\\\{', r'\\\}',   # \{ and \}
            r'\\\[', r'\\\]',   # \[ and \]
            r'\\\(', r'\\\)',   # \( and \)
        ]
        for pattern in special_patterns:
            self.highlighting_rules.append((QRegExp(pattern), special_format))

        
        # Labels and references
        ref_format = QTextCharFormat()
        ref_format.setForeground(self.color_map.get('reference', QColor(25, 25, 112)))
        ref_format.setFontWeight(QFont.Bold)
        ref_patterns = [
            r'\\label\{[^}]*\}',
            r'\\ref\{[^}]*\}',
            r'\\eqref\{[^}]*\}',
            r'\\pageref\{[^}]*\}',
            r'\\cite\{[^}]*\}',
            r'\\citep?\{[^}]*\}',
        ]
        for pattern in ref_patterns:
            self.highlighting_rules.append((QRegExp(pattern), ref_format))
        # Store as instance variables for apply_brace_coloring()
        self.brace_format = brace_format
        self.parameter_format = parameter_format
        self.optional_format = optional_format 
        self.paren_format =  paren_format
    
    def highlightBlock(self, text):
        # 1. Regex rules
        for pattern, format_obj in self.highlighting_rules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format_obj)
                index = expression.indexIn(text, index + length)

        # 2. Math highlighting
        self.handle_math_highlighting(text)
        self.handle_multiline_constructs(text)
        # 3. Brace/paren coloring
        self.apply_brace_coloring(text)

        # ── Spell underlines — MUST be last ──────────────────────────────
        # setFormat() here is the ONLY mechanism that survives rehighlight.
        # spell_map is populated by SpellCheckCoordinator off the main thread
        # and read here during every highlightBlock call.
        if self.spell_checker is not None and self.spell_map:
            block_no = self.currentBlock().blockNumber()
            entries  = self.spell_map.get(block_no)
            if entries:
                for (rel_start, rel_end, color_str) in entries:
                    length = rel_end - rel_start
                    if length > 0:
                        fmt = QTextCharFormat()
                        fmt.setUnderlineStyle(
                            QTextCharFormat.SpellCheckUnderline)
                        fmt.setUnderlineColor(QColor(color_str))
                        self.setFormat(rel_start, length, fmt)
                
    def _apply_spell_check(self, text):
        if not self.spell_checker:
            return
        if not self.spell_checker.enabled:
            return
        if not self.spell_checker.dictionaries_loaded:
            return

        # Skip very long lines — likely generated content or data
        if len(text) > 500:
            return

        active_lang = getattr(self.spell_checker, 'active_language', 'en')
        if active_lang == 'ar':
            if not any('\u0600' <= c <= '\u06FF' or
                       '\u0750' <= c <= '\u077F' or
                       '\u08A0' <= c <= '\u08FF' for c in text):
                return
        else:
            if not any(c.isascii() and c.isalpha() for c in text):
                return

        import re

        # ── Word-level result cache on the spell_checker instance ─────────
        # Maps word → ('ok' | 'misspelled' | 'unknown')
        if not hasattr(self.spell_checker, '_word_result_cache'):
            self.spell_checker._word_result_cache = {}
        word_cache = self.spell_checker._word_result_cache

        # ── 1. Build skip ranges ──────────────────────────────────────────
        latex_skip = re.compile(
            r'\\[a-zA-Z*]+'
            r'|\\\\'
            r'|\\\{|\\\}|\\\[|\\\]|\\\(|\\\)'
            r'|\\.'
            r'|\$\$[\s\S]*?\$\$'
            r'|\$[^$\n]*?\$'
            r'|\\\[[\s\S]*?\\\]'
            r'|\\\([\s\S]*?\\\)'
            r'|%[^\n]*'
            r'|\\begin\{[^}]*\}|\\end\{[^}]*\}'
            r'|\{[^}]{0,120}\}'
            r'|\[[^\]]{0,120}\]'
            r'|\d+[\w./]*'
        )
        skip_ranges = []
        for m in latex_skip.finditer(text):
            skip_ranges.append((m.start(), m.end()))
        skip_ranges.sort()
        merged = []
        for s, e in skip_ranges:
            if merged and s <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], e))
            else:
                merged.append([s, e])

        def in_skip_range(start, end):
            lo, hi = 0, len(merged)
            while lo < hi:
                mid = (lo + hi) // 2
                ms, me = merged[mid]
                if end <= ms:
                    hi = mid
                elif start >= me:
                    lo = mid + 1
                else:
                    return True
            return False

        def should_skip_word(word):
            if len(word) <= 1 or len(word) > 30:
                return True
            if word.isupper():
                return True
            if word[0].isupper() and any(c.isupper() for c in word[1:]):
                return True
            if word.isdigit():
                return True
            return False

        # ── 2. Formats ────────────────────────────────────────────────────
        misspell_color    = QColor(255, 0, 0)
        proper_noun_color = QColor(255, 140, 0)

        def apply_underline(start, length, color):
            fmt = QTextCharFormat(self.format(start))
            fmt.setUnderlineStyle(QTextCharFormat.SpellCheckUnderline)
            fmt.setUnderlineColor(color)
            self.setFormat(start, length, fmt)

        def check_word(word):
            """Check word using cache first."""
            key = (active_lang, word)
            if key in word_cache:
                return word_cache[key]
            if self.spell_checker.is_word_correct(word):
                result = 'ok'
            else:
                # Only call get_suggestions if not correct — expensive
                has_sug = bool(self.spell_checker.get_suggestions(word))
                result = 'misspelled' if has_sug else 'unknown'
            # Cap cache size
            if len(word_cache) < 10000:
                word_cache[key] = result
            return result

        # ── 3. English words ──────────────────────────────────────────────
        word_re = re.compile(r"[a-zA-Z]+(?:-[a-zA-Z]+)*")
        for m in word_re.finditer(text):
            word  = m.group()
            start = m.start()
            end   = m.end()
            if in_skip_range(start, end):
                continue
            if should_skip_word(word):
                continue
            if start > 0 and text[start - 1] == '\\':
                continue
            parts = word.split('-')
            if len(parts) > 1:
                part_results = [check_word(p.lower()) for p in parts if p]
                if all(r == 'ok' for r in part_results):
                    continue
                result = 'misspelled' if any(r == 'misspelled' for r in part_results) else 'unknown'
            else:
                result = check_word(word.lower())
            if result == 'ok':
                continue
            color = misspell_color if result == 'misspelled' else proper_noun_color
            apply_underline(start, end - start, color)

        # ── 4. Arabic words ───────────────────────────────────────────────
        arabic_re = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]+")
        for m in arabic_re.finditer(text):
            word  = m.group()
            start = m.start()
            end   = m.end()
            if in_skip_range(start, end) or len(word) <= 1:
                continue
            result = check_word(word)
            if result == 'ok':
                continue
            color = misspell_color if result == 'misspelled' else proper_noun_color
            apply_underline(start, end - start, color)

        def has_suggestions(word):
            """Return True if pyspellchecker can suggest alternatives."""
            cache = self.spell_checker._suggestion_cache
            if word in cache:
                cached_val, is_correct = cache[word]
                # Only use cache for 'correct' words — don't permanently
                # cache 'no suggestions' since dict may have been updated
                if is_correct:
                    return cached_val
            result = bool(self.spell_checker.get_suggestions(word))
            if len(cache) < 5000:
                cache[word] = (result, result)  # (has_suggestions, is_correct)
            return result

        def check_token(token):
            """Return 'ok', 'misspelled', or 'unknown' (proper noun)."""
            if not token or len(token) <= 1:
                return 'ok'
            if self.spell_checker.is_word_correct(token):
                return 'ok'
            return 'misspelled' if has_suggestions(token) else 'unknown'

        # ── 3. Formats ────────────────────────────────────────────────────
        misspell_color    = QColor(255, 0, 0)      # red   — has suggestions
        proper_noun_color = QColor(255, 140, 0)    # orange — no suggestions

        def apply_underline(start, length, color):
            fmt = QTextCharFormat(self.format(start))
            fmt.setUnderlineStyle(QTextCharFormat.SpellCheckUnderline)
            fmt.setUnderlineColor(color)
            self.setFormat(start, length, fmt)

        # ── 4. English words ──────────────────────────────────────────────
        word_re = re.compile(r"[a-zA-Z]+(?:-[a-zA-Z]+)*")
        for m in word_re.finditer(text):
            word  = m.group()
            start = m.start()
            end   = m.end()

            if in_skip_range(start, end):
                continue
            if should_skip_word(word):
                continue
            if start > 0 and text[start - 1] == '\\':
                continue

            parts = word.split('-')
            if len(parts) > 1:
                part_results = [check_token(p.lower()) for p in parts if p]
                if all(r == 'ok' for r in part_results):
                    continue
                result = 'misspelled' if any(r == 'misspelled' for r in part_results) else 'unknown'
            else:
                result = check_token(word.lower())

            if result == 'ok':
                continue

            color = misspell_color if result == 'misspelled' else proper_noun_color
            apply_underline(start, end - start, color)

        # ── 5. Arabic words ───────────────────────────────────────────────
        arabic_re = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]+")
        for m in arabic_re.finditer(text):
            word  = m.group()
            start = m.start()
            end   = m.end()

            if in_skip_range(start, end):
                continue
            if len(word) <= 1:
                continue

            result = check_token(word)
            if result == 'ok':
                continue

            color = misspell_color if result == 'misspelled' else proper_noun_color
            apply_underline(start, end - start, color)
    
    def handle_math_highlighting(self, text):
        """Handle math highlighting with dynamic colors"""
        # Use instance variables for math formats
        inline_math_format = self.inline_math_format
        display_math_format = self.display_math_format
        
        # Handle inline math $...$
        i = 0
        while i < len(text):
            if text[i] == '$':
                if i > 0 and text[i-1] == '\\':
                    i += 1
                    continue
                j = i + 1
                while j < len(text) and text[j] != '$':
                    if text[j] == '\\' and j + 1 < len(text):
                        j += 2
                    else:
                        j += 1
                if j < len(text) and text[j] == '$':
                    if text[j-1] != '\\':
                        length = j - i + 1
                        math_content = text[i+1:j]
                        if math_content.strip() and '\n' not in math_content:
                            self.setFormat(i, length, inline_math_format)
                        i = j + 1
                    else:
                        i = j + 1
                else:
                    i += 1
            else:
                i += 1
        
        # Handle \(...\) math
        i = 0
        while i < len(text) - 1:
            if text[i:i+2] == '\\(':
                j = i + 2
                while j < len(text) - 1:
                    if text[j:j+2] == '\\)':
                        length = j - i + 2
                        self.setFormat(i, length, inline_math_format)
                        i = j + 2
                        break
                    j += 1
                else:
                    i += 1
            else:
                i += 1
        
        # Handle \[...\] on single lines - Check it's not \\[
        i = 0
        while i < len(text) - 1:
            if text[i:i+2] == '\\[':
                # Skip if preceded by backslash (it's \\[)
                if i > 0 and text[i-1] == '\\':
                    i += 2
                    continue
                
                j = i + 2
                while j < len(text) - 1:
                    if text[j:j+2] == '\\]':
                        length = j - i + 2
                        self.setFormat(i, length, display_math_format)
                        i = j + 2
                        break
                    j += 1
                else:
                    i += 1
            else:
                i += 1
        
        # Handle $$...$$ 
        i = 0
        while i < len(text) - 1:
            if text[i:i+2] == '$$':
                j = i + 2
                while j < len(text) - 1:
                    if text[j:j+2] == '$$':
                        length = j - i + 2
                        self.setFormat(i, length, display_math_format)
                        i = j + 2
                        break
                    j += 1
                else:
                    i += 1
            else:
                i += 1

    def handle_multiline_constructs(self, text):
        """Handle multi-line math environments and comments"""
        math_format = self.display_math_format
        
        self.setCurrentBlockState(self.NORMAL)
        
        # Find \[ but not \\[
        start_index = -1
        i = 0
        while i < len(text) - 1:
            if text[i:i+2] == '\\[':
                # Check if it's not \\[
                if i == 0 or text[i-1] != '\\':
                    start_index = i
                    break
            i += 1
        
        # Find \]
        end_index = -1
        if start_index >= 0 or self.previousBlockState() == self.DISPLAY_MATH:
            j = start_index + 2 if start_index >= 0 else 0
            while j < len(text) - 1:
                if text[j:j+2] == '\\]':
                    end_index = j
                    break
                j += 1
        
        if self.previousBlockState() != self.DISPLAY_MATH:
            if start_index >= 0:
                if end_index == -1:
                    self.setCurrentBlockState(self.DISPLAY_MATH)
                    comment_length = len(text) - start_index
                    self.setFormat(start_index, comment_length, math_format)
                else:
                    length = end_index - start_index + 2
                    self.setFormat(start_index, length, math_format)
        else:
            if end_index == -1:
                self.setCurrentBlockState(self.DISPLAY_MATH)
                self.setFormat(0, len(text), math_format)
            else:
                length = end_index + 2
                self.setFormat(0, length, math_format)
        
        self.handle_environments(text)
    
    
    def handle_environments(self, text):
        """Handle multi-line LaTeX environments"""
        math_environments = [
            'equation', 'align', 'gather', 'multline', 'split',
            'eqnarray', 'alignat', 'flalign', 'cases', 'matrix',
            'pmatrix', 'bmatrix', 'vmatrix', 'Vmatrix'
        ]
        
        env_format = QTextCharFormat()
        env_format.setForeground(self.color_map.get('inline_math', QColor(0, 100, 0)))
        env_format.setBackground(self.color_map.get('inline_math_bg', QColor(240, 255, 240)))
        
        for env in math_environments:
            begin_pattern = rf'\\begin\{{{env}[*]?\}}'
            end_pattern = rf'\\end\{{{env}[*]?\}}'
            
            begin_regex = QRegExp(begin_pattern)
            end_regex = QRegExp(end_pattern)
            
            start_index = begin_regex.indexIn(text)
            if start_index >= 0:
                end_index = end_regex.indexIn(text, start_index)
                if end_index >= 0:
                    length = end_index - start_index + end_regex.matchedLength()
                    self.setFormat(start_index, length, env_format)


    def rehighlight_incremental(self, chunk=50, delay=0):
        """Rehighlight document incrementally to avoid blocking UI."""
        block = self.document().begin()
        self._rehighlight_block_incremental(block, chunk, delay)

    def _rehighlight_block_incremental(self, block, chunk=50, delay=0):
        """Process chunk blocks then yield to event loop."""
        processed = 0
        while block.isValid() and processed < chunk:
            self.rehighlightBlock(block)
            block = block.next()
            processed += 1
        if block.isValid():
            QTimer.singleShot(delay, lambda b=block: 
                self._rehighlight_block_incremental(b, chunk, delay))