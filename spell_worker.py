# spell_worker.py
import re
from PyQt5.QtCore import (
    QObject, QRunnable, QThreadPool, QTimer,
    pyqtSignal, pyqtSlot, Qt
)
from PyQt5.QtGui import QTextCharFormat, QColor, QTextCursor

SPELL_PROP_KEY = 0x100000
SPELL_PROP_VAL = 'sc'


class SpellCheckSignals(QObject):
    result_ready = pyqtSignal(list)
    error        = pyqtSignal(str)


class SpellCheckTask(QRunnable):
    def __init__(self, text, offset, spell_checker, active_language,
                 word_result_cache):
        super().__init__()
        self.setAutoDelete(True)
        self.text              = text
        self.offset            = offset
        self.spell_checker     = spell_checker
        self.active_language   = active_language
        self.word_result_cache = word_result_cache
        self.signals           = SpellCheckSignals()
        self._cancelled        = False

    def cancel(self):
        self._cancelled = True

    _LATEX_SKIP = re.compile(
        r'\\[a-zA-Z*]+'
        r'|\\\\'
        r'|\\[{}[\]()]'
        r'|\\.'
        r'|\$\$[^$]*?\$\$'
        r'|\$[^$\n]*?\$'
        r'|\\\[[\s\S]*?\\\]'
        r'|\\\([\s\S]*?\\\)'
        r'|%[^\n]*'
        r'|\\begin\{[^}]*\}'
        r'|\\end\{[^}]*\}'
        r'|\{[^}]{0,120}\}'
        r'|\[[^\]]{0,120}\]'
        r'|\d+[\w./]*'
    )
    _WORD_EN = re.compile(r'[a-zA-Z]+(?:-[a-zA-Z]+)*')
    _WORD_AR = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]+')

    def _build_skip_ranges(self, text):
        raw = [(m.start(), m.end()) for m in self._LATEX_SKIP.finditer(text)]
        raw.sort()
        merged = []
        for s, e in raw:
            if merged and s <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], e)
            else:
                merged.append([s, e])
        return merged

    def _in_skip(self, start, end, merged):
        lo, hi = 0, len(merged)
        while lo < hi:
            mid = (lo + hi) // 2
            ms, me = merged[mid]
            if end <= ms:     hi = mid
            elif start >= me: lo = mid + 1
            else:             return True
        return False

    @staticmethod
    def _should_skip_word(word):
        if len(word) <= 1 or len(word) > 30: return True
        if word.isupper(): return True
        if word[0].isupper() and any(c.isupper() for c in word[1:]): return True
        return False

    def _check_word(self, word):
        key    = (self.active_language, word)
        cached = self.word_result_cache.get(key)
        if cached is not None:
            return cached
        sc     = self.spell_checker
        result = 'ok' if sc.is_word_correct(word) else (
            'misspelled' if bool(sc.get_suggestions(word)) else 'unknown')
        if len(self.word_result_cache) < 10_000:
            self.word_result_cache[key] = result
        return result

    @pyqtSlot()
    def run(self):
        try:
            underlines = self._find_misspellings()
            if not self._cancelled:
                self.signals.result_ready.emit(underlines)
        except Exception as exc:
            if not self._cancelled:
                self.signals.error.emit(str(exc))

    def _find_misspellings(self):
        text, offset, lang = self.text, self.offset, self.active_language
        results = []
        if lang == 'ar':
            if not any('\u0600' <= c <= '\u06FF' or
                       '\u0750' <= c <= '\u077F' or
                       '\u08A0' <= c <= '\u08FF' for c in text):
                return results
        else:
            if not any(c.isascii() and c.isalpha() for c in text):
                return results
        skip        = self._build_skip_ranges(text)
        red, orange = '#ff0000', '#ff8c00'
        for m in self._WORD_EN.finditer(text):
            if self._cancelled: return []
            word, start, end = m.group(), m.start(), m.end()
            if self._in_skip(start, end, skip):      continue
            if self._should_skip_word(word):         continue
            if start > 0 and text[start-1] == '\\': continue
            parts = word.split('-')
            if len(parts) > 1:
                pr = [self._check_word(p.lower()) for p in parts if p]
                if all(r == 'ok' for r in pr): continue
                result = 'misspelled' if any(
                    r == 'misspelled' for r in pr) else 'unknown'
            else:
                result = self._check_word(word.lower())
            if result == 'ok': continue
            results.append((offset+start, offset+end,
                            red if result == 'misspelled' else orange))
        for m in self._WORD_AR.finditer(text):
            if self._cancelled: return []
            word, start, end = m.group(), m.start(), m.end()
            if self._in_skip(start, end, skip) or len(word) <= 1: continue
            result = self._check_word(word)
            if result == 'ok': continue
            results.append((offset+start, offset+end,
                            red if result == 'misspelled' else orange))
        return results


class SpellCheckCoordinator(QObject):

    TEXT_DEBOUNCE_MS   = 700
    SCROLL_DEBOUNCE_MS = 400

    def __init__(self, editor, spell_checker, main_window, parent=None):
        super().__init__(parent)
        self._editor         = editor
        self._sc             = spell_checker
        self._mw             = main_window
        self._pending_task   = None
        self._pool           = QThreadPool.globalInstance()
        self._full_done      = False
        self._text_cache     = None
        self._text_cache_rev = -1

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._submit_task)

    # ── Public API ────────────────────────────────────────────────────────────
    def schedule_initial(self):
        self._full_done  = False
        self._text_cache = None
        # Phase 1: viewport check fires immediately for instant feedback
        self._submit_task(viewport_only=True)



    def schedule(self, delay_ms=None):
        self._timer.stop()
        self._timer.start(delay_ms if delay_ms is not None
                          else self.TEXT_DEBOUNCE_MS)

    def schedule_scroll(self):
        if not self._full_done:
            return
        self.schedule(self.SCROLL_DEBOUNCE_MS)


            
    def cancel(self):
        self._timer.stop()
        if self._pending_task is not None:
            self._pending_task.cancel()
            self._pending_task = None

    def clear_underlines(self):
        self.cancel()
        self._full_done = False
        try:
            editor = self._editor
            hl     = getattr(editor, 'highlighter', None)
            if hl is None:
                return
            dirty_blocks  = list(hl.spell_map.keys())
            hl.spell_map  = {}
            doc = editor.document()
            for block_no in dirty_blocks:
                block = doc.findBlockByNumber(block_no)
                if block.isValid():
                    hl.rehighlightBlock(block)   # synchronous
        except RuntimeError:
            pass
        except Exception as exc:
            print(f'[Coordinator] clear_underlines: {exc}')

    # ── Text helpers ──────────────────────────────────────────────────────────

    def _plain_text(self):
        try:
            doc = self._editor.document()
            rev = doc.revision()
            if rev != self._text_cache_rev or self._text_cache is None:
                self._text_cache     = doc.toPlainText()
                self._text_cache_rev = rev
            return self._text_cache
        except Exception:
            return ''

    def _full_range(self):
        return self._plain_text(), 0

    def _viewport_range(self):
        try:
            editor    = self._editor
            full      = self._plain_text()
            vp        = editor.viewport()
            top_block = editor.cursorForPosition(
                            vp.rect().topLeft()).block()
            bot_block = editor.cursorForPosition(
                            vp.rect().bottomRight()).block()
            for _ in range(15):
                p = top_block.previous()
                if p.isValid(): top_block = p
            for _ in range(15):
                n = bot_block.next()
                if n.isValid(): bot_block = n
            s = top_block.position()
            e = bot_block.position() + bot_block.length()
            return full[s:e], s
        except Exception:
            return self._plain_text(), 0

    # ── Task submission ───────────────────────────────────────────────────────

    def _submit_task(self, viewport_only=False):
        sc = self._sc
        if not sc.enabled or not sc.dictionaries_loaded:
            return
        if not self._is_editor_valid():
            return
        if self._pending_task is not None:
            self._pending_task.cancel()
            self._pending_task = None

        if viewport_only:
            text, offset = self._viewport_range()
        elif not self._full_done:
            text, offset = self._full_range()
        else:
            text, offset = self._viewport_range()

        if not text:
            return

        lang  = getattr(sc, 'active_language', 'en')
        cache = getattr(sc, '_word_result_cache', {})

        task = SpellCheckTask(text, offset, sc, lang, cache)
        task._is_viewport_precheck = viewport_only
        # Capture document revision at submission time so we can detect
        # stale results in _on_result_ready
        try:
            task._doc_revision = self._editor.document().revision()
        except Exception:
            task._doc_revision = -1

        # Pass task directly via lambda — avoids reading self._pending_task
        # inside _on_result_ready where it has already been nulled
        task.signals.result_ready.connect(
            lambda ul, t=task: self._on_result_ready(ul, t),
            Qt.QueuedConnection)
        task.signals.error.connect(self._on_error, Qt.QueuedConnection)

        self._pending_task = task
        self._pool.start(task)


    def _on_result_ready(self, underlines, task):
        # Clear pending only if this is still the active task
        if self._pending_task is task:
            self._pending_task = None

        if not self._sc.enabled:
            self.clear_underlines()
            return
        if not self._is_editor_valid():
            return

        try:
            doc = self._editor.document()
            hl  = getattr(self._editor, 'highlighter', None)
            if hl is None:
                return

            # ── Stale result guard ────────────────────────────────────────
            # If the document was modified after this task was submitted,
            # its results are stale — discard them entirely.
            # on_text_changed already scheduled a fresh check.
            try:
                current_rev  = doc.revision()
                task_rev     = getattr(task, '_doc_revision', current_rev)
                if current_rev != task_rev:
                    return   # stale — fresh check already queued
            except Exception:
                pass

            is_precheck = task._is_viewport_precheck   # read from task, not self._pending_task

            if not self._full_done and not is_precheck:
                hl.spell_map = {}
            elif is_precheck:
                if underlines:
                    b     = doc.findBlock(underlines[0][0])
                    end_b = doc.findBlock(underlines[-1][1])
                    while b.isValid() and \
                            b.blockNumber() <= end_b.blockNumber():
                        hl.spell_map.pop(b.blockNumber(), None)
                        b = b.next()

            for (abs_start, abs_end, color) in underlines:
                block = doc.findBlock(abs_start)
                if not block.isValid():
                    continue
                block_no  = block.blockNumber()
                block_pos = block.position()
                hl.spell_map.setdefault(block_no, []).append(
                    (abs_start - block_pos, abs_end - block_pos, color))

            try:
                vp     = self._editor.viewport()
                top_no = self._editor.cursorForPosition(
                             vp.rect().topLeft()).block().blockNumber()
                bot_no = self._editor.cursorForPosition(
                             vp.rect().bottomRight()).block().blockNumber()
            except Exception:
                top_no, bot_no = 0, 0

            misspelled = list(hl.spell_map.keys())
            visible    = [n for n in misspelled if top_no <= n <= bot_no]
            invisible  = [n for n in misspelled if n < top_no or n > bot_no]

            for block_no in visible:
                block = doc.findBlockByNumber(block_no)
                if block.isValid():
                    hl.rehighlightBlock(block)

            if is_precheck:
                QTimer.singleShot(0, lambda: self._submit_task(viewport_only=False))
            else:
                self._full_done = True
                self._schedule_invisible(invisible)

        except RuntimeError:
            pass
        except Exception as exc:
            print(f'[Coordinator] _on_result_ready: {exc}')

    # @pyqtSlot(list)
    # def _on_result_ready(self, underlines):
        # self._pending_task = None
        # if not self._sc.enabled:
            # self.clear_underlines()
            # return
        # if not self._is_editor_valid():
            # return

        # try:
            # doc = self._editor.document()
            # hl  = getattr(self._editor, 'highlighter', None)
            # if hl is None:
                # return

            # is_precheck = getattr(
                # self._pending_task, '_is_viewport_precheck', False)

            # # Don't clear the full map on a viewport pre-check
            # if not self._full_done and not is_precheck:
                # hl.spell_map = {}
            # elif is_precheck:
                # # Clear only the viewport range
                # if underlines:
                    # b     = doc.findBlock(underlines[0][0])
                    # end_b = doc.findBlock(underlines[-1][1])
                    # while b.isValid() and \
                            # b.blockNumber() <= end_b.blockNumber():
                        # hl.spell_map.pop(b.blockNumber(), None)
                        # b = b.next()

            # for (abs_start, abs_end, color) in underlines:
                # block = doc.findBlock(abs_start)
                # if not block.isValid():
                    # continue
                # block_no  = block.blockNumber()
                # block_pos = block.position()
                # hl.spell_map.setdefault(block_no, []).append(
                    # (abs_start - block_pos, abs_end - block_pos, color))

            # # Rehighlight visible misspelled blocks synchronously
            # try:
                # vp     = self._editor.viewport()
                # top_no = self._editor.cursorForPosition(
                             # vp.rect().topLeft()).block().blockNumber()
                # bot_no = self._editor.cursorForPosition(
                             # vp.rect().bottomRight()).block().blockNumber()
            # except Exception:
                # top_no, bot_no = 0, 0

            # misspelled = list(hl.spell_map.keys())
            # visible    = [n for n in misspelled if top_no <= n <= bot_no]
            # invisible  = [n for n in misspelled if n < top_no or n > bot_no]

            # for block_no in visible:
                # block = doc.findBlockByNumber(block_no)
                # if block.isValid():
                    # hl.rehighlightBlock(block)

            # if is_precheck:
                # # Phase 1 done — now schedule the full document check
                # # in the background so it doesn't block the UI
                # QTimer.singleShot(0, lambda: self._submit_task(viewport_only=False))
            # else:
                # self._full_done = True
                # # Process invisible blocks in background chunks
                # self._schedule_invisible(invisible)

        # except RuntimeError:
            # pass
        # except Exception as exc:
            # print(f'[Coordinator] _on_result_ready: {exc}')


    def _schedule_invisible(self, block_numbers):
        """Rehighlight off-screen misspelled blocks in chunks via timer."""
        if not block_numbers:
            return
        chunk      = block_numbers[:30]
        remaining  = block_numbers[30:]
        try:
            doc = self._editor.document()
            hl  = getattr(self._editor, 'highlighter', None)
            if hl is None:
                return
            for block_no in chunk:
                block = doc.findBlockByNumber(block_no)
                if block.isValid():
                    hl.rehighlightBlock(block)
        except RuntimeError:
            return
        except Exception:
            return
        if remaining:
            QTimer.singleShot(
                0, lambda: self._schedule_invisible(remaining))
    @pyqtSlot(str)
    def _on_error(self, msg):
        self._pending_task = None
        #print(f'[SpellCheckCoordinator] error: {msg}')

    def _is_editor_valid(self):
        try:
            _ = self._editor.document()
            _ = self._editor.isVisible()
            return True
        except RuntimeError:
            return False