# knowledge_database_integration.py
"""
Knowledge Database Manager with PyQt5
Bilingual (English/Arabic) — Discipline-Agnostic Entry Types
Features: Live language switching, Search with occurrence highlighting,
          Dynamic entry types, Explanation/Justification system,
          Datetime-based IDs, Optional titles, Sortable columns,
          Clean light UI
"""
import sys
import os
import sqlite3
import logging
import shutil
from datetime import datetime
from typing import Dict, List, Optional
from contextlib import contextmanager
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QTextEdit, QPushButton, QComboBox, QListWidget,
    QListWidgetItem, QDialog, QTableWidget, QTableWidgetItem, QScrollArea,
    QFileDialog, QMessageBox, QTabWidget, QToolBar, QAction, QSplitter,
    QInputDialog, QFrame, QHeaderView, QAbstractItemView, QSizePolicy,
    QStatusBar, QCalendarWidget, QCheckBox, QGridLayout
)
from PyQt5.QtCore import Qt, QSize, QDate, QTime
from PyQt5.QtGui import (
    QFont, QTextCursor, QTextCharFormat, QColor, QBrush, QPixmap,
    QImage, QIcon, QTextOption
)
from googletrans import Translator
from translations_database import TRANSLATIONS

# ============================================================================
# ICON UTILITY
# ============================================================================
def get_safe_icon(icon_path: str, fallback_char: str = "📋") -> QIcon:
    if os.path.exists(icon_path):
        try:
            icon = QIcon(icon_path)
            if not icon.isNull():
                return icon
        except Exception as e:
            logger.warning(f"Failed to load icon {icon_path}: {e}")
    logger.warning(f"Icon not found: {icon_path}, using fallback")
    return QIcon()

# ============================================================================
# PALETTE
# ============================================================================
APP_STYLE = ""

def make_heading(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("heading")
    font = lbl.font()
    font.setBold(True)
    font.setPointSize(font.pointSize() + 1)
    lbl.setFont(font)
    return lbl

def make_sep() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setFrameShadow(QFrame.Sunken)
    return line

class TranslationService:
    def __init__(self):
        self.translator = Translator()
        self._cache = {}

    def translate(self, text: str, src_lang: str = 'en', dest_lang: str = 'ar') -> str:
        if not text or not text.strip():
            return ""
        cache_key = (text.strip(), src_lang, dest_lang)
        if cache_key in self._cache:
            return self._cache[cache_key]
        try:
            result = self.translator.translate(
                text.strip(),
                src_language=src_lang,
                dest_language=dest_lang
            )
            translated = result.get('translated-text', text)
            self._cache[cache_key] = translated
            return translated
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return text

    # def transliterate_to_arabic(self, text: str) -> str:
        # phonetic_map = {
            # 'a': 'ا', 'b': 'ب', 'c': 'ك', 'd': 'د', 'e': 'ي', 'f': 'ف',
            # 'g': 'غ', 'h': 'ه', 'i': 'ي', 'j': 'ج', 'k': 'ك', 'l': 'ل',
            # 'm': 'م', 'n': 'ن', 'o': 'و', 'p': 'پ', 'q': 'ق', 'r': 'ر',
            # 's': 'س', 't': 'ت', 'u': 'و', 'v': 'ف', 'w': 'و', 'x': 'كس',
            # 'y': 'ي', 'z': 'ز', ' ': ' ',
        # }
        # result = ""
        # for char in text.lower():
            # result += phonetic_map.get(char, char)
        # return result

_translator = TranslationService()

# ============================================================================
# LANGUAGE SYSTEM
# ============================================================================
class Languages:
    TRANSLATIONS = TRANSLATIONS

    def __init__(self, lang: str = 'en'):
        self.current_lang = lang if lang in self.TRANSLATIONS else 'en'

    def t(self, key: str, **kwargs) -> str:
        text = self.TRANSLATIONS[self.current_lang].get(key, key)
        if kwargs:
            try:
                return text.format(**kwargs)
            except:
                return text
        return text

    def set_language(self, lang: str) -> bool:
        if lang in self.TRANSLATIONS:
            self.current_lang = lang
            return True
        return False

# ============================================================================
# LOGGING
# ============================================================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============================================================================
# ID GENERATION
# ============================================================================
def generate_id() -> str:
    return datetime.now().strftime("%Y-%m-%d-%H%M%S.%f")

# ============================================================================
# DATABASE RECOVERY
# ============================================================================
class DatabaseRecovery:
    def __init__(self, db_path: str = None):
        if db_path is None:
            config_dir = KnowledgeDB._get_config_directory()
            db_path = os.path.join(config_dir, "knowledge.db")
        self.db_path = db_path
        self.backup_dir = os.path.dirname(db_path)
        if not self.backup_dir:
            self.backup_dir = os.getcwd()
        self.backup_dir = os.path.join(self.backup_dir, "backups")
        Path(self.backup_dir).mkdir(parents=True, exist_ok=True)

    def is_database_corrupt(self) -> bool:
        try:
            conn = sqlite3.connect(self.db_path, timeout=2.0)
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            conn.close()
            return result[0] != 'ok'
        except sqlite3.DatabaseError:
            return True
        except:
            return False

    def create_backup(self) -> Optional[str]:
        try:
            if not os.path.exists(self.db_path):
                return None
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            bp = os.path.join(self.backup_dir, f"knowledge_backup_{ts}.db")
            shutil.copy2(self.db_path, bp)
            return bp
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return None

    def restore_backup(self, backup_path: str) -> bool:
        try:
            if not os.path.exists(backup_path):
                return False
            shutil.copy2(backup_path, self.db_path)
            return True
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False

    def get_latest_backup(self) -> Optional[str]:
        try:
            backups = sorted(
                [f for f in os.listdir(self.backup_dir) if f.startswith('knowledge_backup_')],
                reverse=True
            )
            if backups:
                return os.path.join(self.backup_dir, backups[0])
        except:
            pass
        return None

    def repair_database(self) -> bool:
        try:
            self.create_backup()
            conn = sqlite3.connect(self.db_path, timeout=5.0)
            conn.execute("VACUUM")
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Repair failed: {e}")
            return False

# ============================================================================
# DEFAULT DATA
# ============================================================================
DEFAULT_TYPES = [
    "theorem", "definition", "lemma", "corollary", "proposition",
    "example", "remark", "exercise", "conjecture",
    "concept", "process", "mechanism", "experiment", "observation", "hypothesis",
    "reaction", "compound", "law", "property",
    "principle", "formula", "algorithm", "design_pattern", "procedure",
]

RELATION_TYPES = [
    "uses", "depends_on", "derived_from", "example_of",
    "validates", "contradicts", "generalizes", "related_to",
]

# ============================================================================
# DATABASE
# ============================================================================
class KnowledgeDB:
    def __init__(self, db_path: str = None, lang: 'Languages' = None):
        if db_path is None:
            config_dir = self._get_config_directory()
            Path(config_dir).mkdir(parents=True, exist_ok=True)
            db_path = os.path.join(config_dir, "knowledge.db")
        self.db_path = db_path
        self.lang = lang or Languages()
        self.recovery = DatabaseRecovery(db_path)
        self.conn = None
        self._init_connection()

    @staticmethod
    def _get_config_directory() -> str:
        app_name = "Ayntex"
        system = sys.platform.lower()
        if system.startswith('win'):
            appdata = os.environ.get('APPDATA')
            if appdata:
                return os.path.join(appdata, app_name)
            else:
                return os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', app_name)
        elif system.startswith('darwin'):
            return os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', app_name)
        else:
            xdg_config_home = os.environ.get('XDG_CONFIG_HOME')
            if xdg_config_home:
                return os.path.join(xdg_config_home, app_name)
            else:
                return os.path.join(os.path.expanduser('~'), '.config', app_name)

    def _init_connection(self):
        try:
            if os.path.exists(self.db_path) and self.recovery.is_database_corrupt():
                if not self.recovery.repair_database():
                    latest = self.recovery.get_latest_backup()
                    if latest:
                        self.recovery.restore_backup(latest)
                    else:
                        os.remove(self.db_path)
            self.conn = sqlite3.connect(self.db_path, timeout=10.0, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA foreign_keys = ON")
            self.conn.commit()
        except Exception as e:
            logger.error(f"Connection error: {e}")
            raise

    @contextmanager
    def get_cursor(self):
        try:
            cursor = self.conn.cursor()
            yield cursor
            self.conn.commit()
        except Exception as e:
            logger.error(f"DB error: {e}")
            self.conn.rollback()
            raise
        finally:
            try:
                cursor.close()
            except:
                pass

    def _row_to_dict(self, row) -> Optional[Dict]:
        if row is None:
            return None
        try:
            return dict(row)
        except:
            return row

    def _rows_to_dicts(self, rows) -> List[Dict]:
        return [self._row_to_dict(r) for r in rows if r is not None]

    def init_schema(self):
        try:
            with self.get_cursor() as cursor:
                # NOTE: explanations uses title_en/title_ar/content_en/content_ar
                # to match the bilingual pattern; legacy single-column DBs are
                # migrated below.
                cursor.executescript("""
                    CREATE TABLE IF NOT EXISTS entry_types (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        latex_template TEXT DEFAULT ''
                    );
                    CREATE TABLE IF NOT EXISTS entries (
                        id TEXT PRIMARY KEY,
                        title_en TEXT DEFAULT '',
                        title_ar TEXT DEFAULT '',
                        type TEXT NOT NULL,
                        content_en TEXT NOT NULL,
                        content_ar TEXT DEFAULT '',
                        author_en TEXT DEFAULT '',
                        author_ar TEXT DEFAULT '',
                        author_ar_phonetic TEXT DEFAULT '',
                        date_created TEXT NOT NULL,
                        date_modified TEXT NOT NULL,
                        domain_en TEXT DEFAULT '',
                        domain_ar TEXT DEFAULT '',
                        subdomain_en TEXT DEFAULT '',
                        subdomain_ar TEXT DEFAULT '',
                        doi TEXT DEFAULT '',
                        bibtex TEXT DEFAULT ''
                    );
                    CREATE TABLE IF NOT EXISTS explanations (
                        id TEXT PRIMARY KEY,
                        entry_id TEXT NOT NULL,
                        title_en TEXT DEFAULT '',
                        title_ar TEXT DEFAULT '',
                        content_en TEXT NOT NULL DEFAULT '',
                        content_ar TEXT DEFAULT '',
                        author_en TEXT DEFAULT '',
                        author_ar TEXT DEFAULT '',
                        date_created TEXT NOT NULL,
                        date_modified TEXT NOT NULL,
                        FOREIGN KEY(entry_id) REFERENCES entries(id) ON DELETE CASCADE
                    );
                    CREATE TABLE IF NOT EXISTS links (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        from_id TEXT NOT NULL,
                        to_id TEXT NOT NULL,
                        relation TEXT NOT NULL,
                        FOREIGN KEY(from_id) REFERENCES entries(id) ON DELETE CASCADE,
                        FOREIGN KEY(to_id) REFERENCES entries(id) ON DELETE CASCADE,
                        UNIQUE(from_id, to_id, relation)
                    );
                    CREATE INDEX IF NOT EXISTS idx_entries_domain ON entries(domain_en);
                    CREATE INDEX IF NOT EXISTS idx_entries_type ON entries(type);
                    CREATE INDEX IF NOT EXISTS idx_explanations_entry ON explanations(entry_id);
                    CREATE INDEX IF NOT EXISTS idx_links_from ON links(from_id);
                """)
            # ── Migrate legacy explanations table if columns are missing ──────
            self._migrate_explanations_table()
            with self.get_cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM entry_types")
                if cursor.fetchone()[0] == 0:
                    for t in DEFAULT_TYPES:
                        cursor.execute("INSERT OR IGNORE INTO entry_types (name) VALUES (?)", (t,))
        except Exception as e:
            logger.error(f"Schema error: {e}")
            raise

    def _migrate_explanations_table(self):
        """
        Migrate an old single-language explanations table to the bilingual schema.
        Old schema had: id, entry_id, title, content, author, date_created, date_modified
        New schema has: id, entry_id, title_en, title_ar, content_en, content_ar,
                        author_en, author_ar, date_created, date_modified
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute("PRAGMA table_info(explanations)")
                cols = {row[1] for row in cursor.fetchall()}

            new_cols_needed = {
                'title_en', 'title_ar',
                'content_en', 'content_ar',
                'author_en', 'author_ar',
            }
            has_old_title   = 'title'   in cols
            has_old_content = 'content' in cols
            has_old_author  = 'author'  in cols

            missing = new_cols_needed - cols
            if not missing:
                return  # already up to date

            logger.info(f"Migrating explanations table — adding columns: {missing}")
            with self.get_cursor() as cursor:
                for col in missing:
                    default = "NOT NULL DEFAULT ''" if col == 'content_en' else "DEFAULT ''"
                    cursor.execute(
                        f"ALTER TABLE explanations ADD COLUMN {col} TEXT {default}"
                    )

            # Copy old data into new columns
            if has_old_title or has_old_content or has_old_author:
                with self.get_cursor() as cursor:
                    if has_old_title and 'title_en' in missing:
                        cursor.execute(
                            "UPDATE explanations SET title_en = COALESCE(title, '') "
                            "WHERE title_en IS NULL OR title_en = ''"
                        )
                    if has_old_content and 'content_en' in missing:
                        cursor.execute(
                            "UPDATE explanations SET content_en = COALESCE(content, '') "
                            "WHERE content_en IS NULL OR content_en = ''"
                        )
                    if has_old_author and 'author_en' in missing:
                        cursor.execute(
                            "UPDATE explanations SET author_en = COALESCE(author, '') "
                            "WHERE author_en IS NULL OR author_en = ''"
                        )
            logger.info("Explanations table migration complete.")
        except Exception as e:
            logger.error(f"Explanations migration error: {e}")

    # ── Types ─────────────────────────────────────────────────────────────────
    def get_all_types(self) -> List[Dict]:
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT * FROM entry_types ORDER BY name")
                return self._rows_to_dicts(cursor.fetchall())
        except:
            return []

    def get_type_names(self) -> List[str]:
        return [t['name'] for t in self.get_all_types()]

    def add_type(self, name: str, template: str = "") -> int:
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    "INSERT INTO entry_types (name, latex_template) VALUES (?, ?)",
                    (name.strip(), template)
                )
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            raise ValueError("Type already exists")

    def delete_type(self, name: str):
        with self.get_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM entries WHERE type = ?", (name,))
            if cursor.fetchone()[0] > 0:
                raise ValueError("type_in_use")
        with self.get_cursor() as cursor:
            cursor.execute("DELETE FROM entry_types WHERE name = ?", (name,))

    def get_type_template(self, type_name: str) -> str:
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT latex_template FROM entry_types WHERE name = ?", (type_name,))
                row = cursor.fetchone()
                return row[0] if row and row[0] else ""
        except:
            return ""

    # ── Entries ───────────────────────────────────────────────────────────────
    def add_entry(self, data: Dict) -> str:
        entry_id = generate_id()
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO entries
                    (id, title_en, title_ar, type, content_en, content_ar,
                     author_en, author_ar, author_ar_phonetic, date_created, date_modified,
                     domain_en, domain_ar, subdomain_en, subdomain_ar, doi, bibtex)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entry_id,
                    data.get('title_en', '') or '',
                    data.get('title_ar', '') or '',
                    data['type'],
                    data.get('content_en', ''),
                    data.get('content_ar', '') or '',
                    data.get('author_en', '') or '',
                    data.get('author_ar', '') or '',
                    data.get('author_ar_phonetic', '') or '',
                    entry_id, entry_id,
                    data.get('domain_en', '') or '',
                    data.get('domain_ar', '') or '',
                    data.get('subdomain_en', '') or '',
                    data.get('subdomain_ar', '') or '',
                    data.get('doi', '') or '',
                    data.get('bibtex', '') or '',
                ))
                return entry_id
        except sqlite3.IntegrityError:
            raise ValueError("Entry already exists")

    def update_entry(self, entry_id: str, data: Dict):
        now = generate_id()
        with self.get_cursor() as cursor:
            cursor.execute("""
                UPDATE entries SET
                    title_en=?, title_ar=?, type=?, content_en=?, content_ar=?,
                    author_en=?, author_ar=?, author_ar_phonetic=?,
                    date_modified=?, domain_en=?, domain_ar=?, subdomain_en=?, subdomain_ar=?,
                    doi=?, bibtex=?
                WHERE id=?
            """, (
                data.get('title_en', '') or '',
                data.get('title_ar', '') or '',
                data['type'],
                data.get('content_en', ''),
                data.get('content_ar', '') or '',
                data.get('author_en', '') or '',
                data.get('author_ar', '') or '',
                data.get('author_ar_phonetic', '') or '',
                now,
                data.get('domain_en', '') or '',
                data.get('domain_ar', '') or '',
                data.get('subdomain_en', '') or '',
                data.get('subdomain_ar', '') or '',
                data.get('doi', '') or '',
                data.get('bibtex', '') or '',
                entry_id,
            ))

    def delete_entry(self, entry_id: str):
        with self.get_cursor() as cursor:
            cursor.execute("DELETE FROM entries WHERE id=?", (entry_id,))

    def get_entry(self, entry_id: str) -> Optional[Dict]:
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT * FROM entries WHERE id=?", (entry_id,))
                row = self._row_to_dict(cursor.fetchone())
                if row:
                    row['title'] = row.get('title_en', '') or row.get('title_ar', '')
                    row['content'] = row.get('content_en', '') or row.get('content_ar', '')
                    row['author'] = row.get('author_en', '') or row.get('author_ar', '')
                    row['domain'] = row.get('domain_en', '') or row.get('domain_ar', '')
                    row['subdomain'] = row.get('subdomain_en', '') or row.get('subdomain_ar', '')
                return row
        except:
            return None

    def get_all_entries(self) -> List[Dict]:
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT * FROM entries ORDER BY date_modified DESC")
                return self._rows_to_dicts(cursor.fetchall())
        except:
            return []

    def search(self, query: str) -> List[Dict]:
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM entries
                    WHERE title_en LIKE ? OR title_ar LIKE ?
                       OR content_en LIKE ? OR content_ar LIKE ?
                       OR author_en LIKE ? OR author_ar LIKE ?
                       OR type LIKE ?
                       OR domain_en LIKE ? OR domain_ar LIKE ?
                    ORDER BY date_modified DESC
                """, (f"%{query}%",) * 9)
                return self._rows_to_dicts(cursor.fetchall())
        except:
            return []

    def search_related(self, entry_id: str, relation_type: str) -> List[Dict]:
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    SELECT DISTINCT e.* FROM entries e
                    INNER JOIN links l ON (l.to_id = e.id AND l.from_id = ?)
                                       OR (l.from_id = e.id AND l.to_id = ?)
                    WHERE l.relation = ?
                    ORDER BY e.date_modified DESC
                """, (entry_id, entry_id, relation_type))
                return self._rows_to_dicts(cursor.fetchall())
        except Exception as e:
            logger.error(f"search_related error: {e}")
            return []

    # def get_unique_domains(self) -> List[str]:
        # try:
            # with self.get_cursor() as cursor:
                # cursor.execute("""
                    # SELECT DISTINCT domain_en FROM entries
                    # WHERE domain_en IS NOT NULL AND domain_en != ''
                    # UNION
                    # SELECT DISTINCT domain_ar FROM entries
                    # WHERE domain_ar IS NOT NULL AND domain_ar != ''
                    # ORDER BY 1
                # """)
                # return [r[0] for r in cursor.fetchall() if r[0]]
        # except:
            # return []

    def get_unique_types_in_use(self) -> List[str]:
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT DISTINCT type FROM entries ORDER BY type")
                return [r[0] for r in cursor.fetchall() if r[0]]
        except:
            return []

    # ── Explanations ──────────────────────────────────────────────────────────
    def add_explanation(self, entry_id: str, data: Dict) -> str:
        expl_id = generate_id()
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO explanations
                    (id, entry_id, title_en, title_ar, content_en, content_ar,
                     author_en, author_ar, date_created, date_modified)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                expl_id,
                entry_id,
                data.get('title_en', '') or data.get('title', '') or '',
                data.get('title_ar', '') or '',
                data.get('content_en', '') or data.get('content', '') or '',
                data.get('content_ar', '') or '',
                data.get('author_en', '') or data.get('author', '') or '',
                data.get('author_ar', '') or '',
                expl_id,
                expl_id,
            ))
            return expl_id

    def update_explanation(self, expl_id: str, data: Dict):
        now = generate_id()
        with self.get_cursor() as cursor:
            cursor.execute("""
                UPDATE explanations SET
                    title_en=?, title_ar=?, content_en=?, content_ar=?,
                    author_en=?, author_ar=?, date_modified=?
                WHERE id=?
            """, (
                data.get('title_en', '') or data.get('title', '') or '',
                data.get('title_ar', '') or '',
                data.get('content_en', '') or data.get('content', '') or '',
                data.get('content_ar', '') or '',
                data.get('author_en', '') or data.get('author', '') or '',
                data.get('author_ar', '') or '',
                now,
                expl_id,
            ))

    def delete_explanation(self, expl_id: str):
        with self.get_cursor() as cursor:
            cursor.execute("DELETE FROM explanations WHERE id=?", (expl_id,))

    def get_explanation(self, expl_id: str) -> Optional[Dict]:
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT * FROM explanations WHERE id=?", (expl_id,))
                row = self._row_to_dict(cursor.fetchone())
                if row:
                    # Convenience aliases
                    row['title']   = row.get('title_en', '')   or row.get('title_ar', '')
                    row['content'] = row.get('content_en', '') or row.get('content_ar', '')
                    row['author']  = row.get('author_en', '')  or row.get('author_ar', '')
                return row
        except:
            return None

    def get_explanations_for_entry(self, entry_id: str) -> List[Dict]:
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM explanations WHERE entry_id=? ORDER BY date_created DESC",
                    (entry_id,)
                )
                rows = self._rows_to_dicts(cursor.fetchall())
                for row in rows:
                    row['title']   = row.get('title_en', '')   or row.get('title_ar', '')
                    row['content'] = row.get('content_en', '') or row.get('content_ar', '')
                    row['author']  = row.get('author_en', '')  or row.get('author_ar', '')
                return rows
        except:
            return []

    # ── Links ─────────────────────────────────────────────────────────────────
    def get_links(self, entry_id: str) -> List[Dict]:
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    SELECT l.*, e.title_en as target_title, e.title_ar as target_title_ar,
                           e.type as target_type
                    FROM links l JOIN entries e ON l.to_id = e.id
                    WHERE l.from_id=?
                """, (entry_id,))
                results = self._rows_to_dicts(cursor.fetchall())
                for r in results:
                    r['target_title'] = r.get('target_title', '') or r.get('target_title_ar', '') or '—'
                return results
        except:
            return []

    def add_link(self, from_id: str, to_id: str, relation: str):
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    "INSERT INTO links (from_id, to_id, relation) VALUES (?, ?, ?)",
                    (from_id, to_id, relation)
                )
        except sqlite3.IntegrityError:
            raise ValueError("Link already exists")

    def delete_link(self, link_id: int):
        with self.get_cursor() as cursor:
            cursor.execute("DELETE FROM links WHERE id=?", (link_id,))

    # ── LaTeX ─────────────────────────────────────────────────────────────────
    def generate_latex(self, entry_id: str, include_explanations: bool = True,
                       lang: str = 'en') -> str:
        entry = self.get_entry(entry_id)
        if not entry:
            return ""
        try:
            env_type = entry.get('type', 'theorem')
            alt = 'ar' if lang == 'en' else 'en'
            title  = entry.get(f'title_{lang}', '')  or entry.get(f'title_{alt}', '')  or ''
            author = entry.get(f'author_{lang}', '') or entry.get(f'author_{alt}', '') or ''
            body   = entry.get(f'content_{lang}', '') or entry.get(f'content_{alt}', '') or ''
            template = self.get_type_template(env_type)
            if template:
                latex = (template
                         .replace('{type}', env_type)
                         .replace('{title}', title)
                         .replace('{content}', body))
            else:
                parts = []
                if title:
                    parts.append(title)
                if author:
                    parts.append(f"({author})")
                header = ", ".join(parts)
                if header:
                    latex = f"\\begin{{{env_type}}}[{header}]\n{body}\n\\end{{{env_type}}}%\n"
                else:
                    latex = f"\\begin{{{env_type}}}\n{body}\n\\end{{{env_type}}}%\n"
            if include_explanations:
                for expl in self.get_explanations_for_entry(entry_id):
                    et = expl.get('title', '') or 'Proof'
                    ea = expl.get('author', '') or ''
                    ec = expl.get('content', '')
                    eh = f"{et} ({ea})" if ea else et
                    latex += f"\n\\begin{{proof}}[{eh}]\n{ec}\n\\end{{proof}}%\n"
            return latex
        except Exception as e:
            logger.error(f"LaTeX error: {e}")
            return ""

    def close(self):
        try:
            if self.conn:
                self.conn.close()
        except Exception as e:
            logger.error(f"Close error: {e}")

# ============================================================================
# SORTABLE TABLE
# ============================================================================
class SortableTable(QTableWidget):
    COL_ID     = 0
    COL_TITLE  = 1
    COL_TYPE   = 2
    COL_DOMAIN = 3
    COL_AUTHOR = 4

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sort_col = -1
        self._sort_asc = True
        self._data: List[Dict] = []
        self.horizontalHeader().sectionClicked.connect(self._on_header_clicked)
        self.setSortingEnabled(False)

    def load_data(self, entries: List[Dict]):
        self._data = entries
        self._render()

    def _on_header_clicked(self, col: int):
        if self._sort_col == col:
            self._sort_asc = not self._sort_asc
        else:
            self._sort_col = col
            self._sort_asc = True
        self._render()

    def _sort_key(self, entry: Dict) -> str:
        c = self._sort_col
        if c == self.COL_ID:
            return entry.get('id', '') or ''
        elif c == self.COL_TITLE:
            return (entry.get('title', '') or '').lower()
        elif c == self.COL_TYPE:
            return (entry.get('type', '') or '').lower()
        elif c == self.COL_DOMAIN:
            return (entry.get('domain', '') or '').lower()
        elif c == self.COL_AUTHOR:
            return (entry.get('author', '') or '').lower()
        return ''

    def _render(self):
        entries = list(self._data)
        if self._sort_col >= 0:
            entries.sort(key=self._sort_key, reverse=not self._sort_asc)
        hdr = self.horizontalHeader()
        if self._sort_col >= 0:
            hdr.setSortIndicatorShown(True)
            hdr.setSortIndicator(
                self._sort_col,
                Qt.AscendingOrder if self._sort_asc else Qt.DescendingOrder
            )
        else:
            hdr.setSortIndicatorShown(False)
        self.setRowCount(0)
        for entry in entries:
            row = self.rowCount()
            self.insertRow(row)
            eid = str(entry.get('id', '') or '')
            short_id = eid[:10] if len(eid) >= 10 else eid
            id_item = QTableWidgetItem(short_id)
            id_item.setData(Qt.UserRole, eid)
            id_item.setFont(QFont("Courier New", 9))
            self.setItem(row, self.COL_ID, id_item)
            title = entry.get('title', '') or entry.get('title_en', '') or entry.get('title_ar', '') or ''
            title_item = QTableWidgetItem(title if title else "—")
            if not title:
                f = QFont("Georgia", 11)
                f.setItalic(True)
                title_item.setFont(f)
            self.setItem(row, self.COL_TITLE, title_item)
            self.setItem(row, self.COL_TYPE,   QTableWidgetItem(entry.get('type', '') or ''))
            domain = entry.get('domain', '') or entry.get('domain_en', '') or entry.get('domain_ar', '') or ''
            self.setItem(row, self.COL_DOMAIN, QTableWidgetItem(domain))
            author = entry.get('author', '') or entry.get('author_en', '') or entry.get('author_ar', '') or ''
            self.setItem(row, self.COL_AUTHOR, QTableWidgetItem(author))

# ============================================================================
# DIALOGS
# ============================================================================
class EntryDialog(QDialog):
    def __init__(self, db: KnowledgeDB, entry_id: Optional[str] = None,
                 lang: Languages = None, parent=None):
        super().__init__(parent)
        self.db = db
        self.entry_id = entry_id
        self.lang = lang or Languages()
        self.translator = Translator()
        self.setWindowTitle(self.lang.t('edit_entry' if entry_id else 'add_entry'))
        self.setGeometry(100, 60, 820, 620)
        self.setMinimumHeight(500)
        self._build_ui()
        if entry_id:
            self._load()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(22, 20, 22, 20)
        root.addWidget(make_heading(self.lang.t('edit_entry' if self.entry_id else 'add_entry')))
        root.addWidget(make_sep())
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea { border: none; }
            QScrollBar:vertical { width: 10px; background: transparent; }
            QScrollBar::handle:vertical { background: #ccc; border-radius: 5px; min-height: 20px; }
            QScrollBar::handle:vertical:hover { background: #999; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(8)
        content_layout.setContentsMargins(0, 0, 0, 0)
        type_row = QHBoxLayout()
        type_row.setSpacing(14)
        tv = QVBoxLayout()
        tv.addWidget(QLabel(self.lang.t('type')))
        self.type_combo = QComboBox()
        self.type_combo.addItems(self.db.get_type_names())
        tv.addWidget(self.type_combo)
        type_row.addLayout(tv)
        dv = QVBoxLayout()
        dv.addWidget(QLabel(self.lang.t('doi')))
        self.doi_input = QLineEdit()
        dv.addWidget(self.doi_input)
        type_row.addLayout(dv)
        content_layout.addLayout(type_row)
        self.lang_tabs = QTabWidget()
        self.en_widgets = self._build_lang_tab("English", "en")
        self.ar_widgets = self._build_lang_tab("العربية", "ar")
        self.lang_tabs.addTab(self.en_widgets['tab'], "English")
        self.lang_tabs.addTab(self.ar_widgets['tab'], "العربية")
        content_layout.addWidget(self.lang_tabs)
        translate_row = QHBoxLayout()
        translate_row.setSpacing(8)
        btn_en_to_ar = QPushButton("Translate EN → AR")
        btn_en_to_ar.setMaximumHeight(32)
        btn_en_to_ar.clicked.connect(lambda: self._translate("en", "ar"))
        translate_row.addWidget(btn_en_to_ar)
        btn_ar_to_en = QPushButton("Translate AR → EN")
        btn_ar_to_en.setMaximumHeight(32)
        btn_ar_to_en.clicked.connect(lambda: self._translate("ar", "en"))
        translate_row.addWidget(btn_ar_to_en)
        content_layout.addLayout(translate_row)
        content_layout.addWidget(QLabel(self.lang.t('bibtex')))
        self.bibtex_text = QTextEdit()
        self.bibtex_text.setMaximumHeight(60)
        content_layout.addWidget(self.bibtex_text)
        content_layout.addStretch()
        scroll_area.setWidget(content_widget)
        root.addWidget(scroll_area)
        root.addWidget(make_sep())
        btns = QHBoxLayout()
        btns.addStretch()
        cancel_btn = QPushButton(self.lang.t('cancel'))
        cancel_btn.setMaximumHeight(32)
        cancel_btn.setMinimumWidth(100)
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton(self.lang.t('save'))
        save_btn.setMaximumHeight(32)
        save_btn.setMinimumWidth(100)
        save_btn.clicked.connect(self._save)
        btns.addWidget(cancel_btn)
        btns.addWidget(save_btn)
        root.addLayout(btns)

    def _build_lang_tab(self, label: str, lang_code: str) -> Dict:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(6)
        layout.setContentsMargins(10, 10, 10, 10)
        is_rtl = (lang_code == "ar")
        opt_label = QLabel(f"{self.lang.t('title')} — {self.lang.t('optional')}")
        layout.addWidget(opt_label)
        title_input = QLineEdit()
        title_input.setMaximumHeight(32)
        title_input.setPlaceholderText(self.lang.t('title_placeholder'))
        if is_rtl:
            title_input.setAlignment(Qt.AlignRight)
        layout.addWidget(title_input)
        layout.addWidget(QLabel(self.lang.t('author')))
        author_input = QLineEdit()
        author_input.setMaximumHeight(32)
        if is_rtl:
            author_input.setAlignment(Qt.AlignRight)
        layout.addWidget(author_input)
        ds_row = QHBoxLayout()
        ds_row.setSpacing(12)
        ld = QVBoxLayout()
        ld.addWidget(QLabel(self.lang.t('domain')))
        domain_input = QLineEdit()
        domain_input.setMaximumHeight(32)
        if is_rtl:
            domain_input.setAlignment(Qt.AlignRight)
        ld.addWidget(domain_input)
        rd = QVBoxLayout()
        rd.addWidget(QLabel(self.lang.t('subdomain')))
        subdomain_input = QLineEdit()
        subdomain_input.setMaximumHeight(32)
        if is_rtl:
            subdomain_input.setAlignment(Qt.AlignRight)
        rd.addWidget(subdomain_input)
        ds_row.addLayout(ld)
        ds_row.addLayout(rd)
        layout.addLayout(ds_row)
        layout.addWidget(QLabel(self.lang.t('content')))
        content_text = QTextEdit()
        content_text.setMinimumHeight(120)
        content_text.setMaximumHeight(160)
        if is_rtl:
            content_text.document().setDefaultTextOption(QTextOption(Qt.AlignRight))
        layout.addWidget(content_text)
        layout.addStretch()
        return {
            'tab': tab,
            'title': title_input,
            'author': author_input,
            'domain': domain_input,
            'subdomain': subdomain_input,
            'content': content_text,
        }

    def _get_widgets(self, lang_code: str) -> Dict:
        return self.en_widgets if lang_code == "en" else self.ar_widgets

    def _translate(self, src: str, dest: str):
        src_w = self._get_widgets(src)
        dest_w = self._get_widgets(dest)
        src_lang  = "en" if src  == "en" else "ar"
        dest_lang = "ar" if dest == "ar" else "en"
        fields = [
            ('title',     'text',        'setText'),
            ('author',    'text',        'setText'),
            ('domain',    'text',        'setText'),
            ('subdomain', 'text',        'setText'),
            ('content',   'toPlainText', 'setPlainText'),
        ]
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            for field_name, getter, setter in fields:
                src_widget  = src_w[field_name]
                dest_widget = dest_w[field_name]
                source_text = src_widget.text().strip() if getter == 'text' \
                              else src_widget.toPlainText().strip()
                if not source_text:
                    continue
                if field_name == 'author':
                    translated = self._transliterate_author(source_text, src_lang, dest_lang)
                else:
                    result = self.translator.translate(source_text, src=src_lang, dest=dest_lang)
                    translated = result.text
                if setter == 'setText':
                    dest_widget.setText(translated)
                else:
                    dest_widget.setPlainText(translated)
            QApplication.restoreOverrideCursor()
            QMessageBox.information(
                self, self.lang.t('success'),
                f"Translation {src.upper()} → {dest.upper()} complete."
            )
        except Exception as e:
            QApplication.restoreOverrideCursor()
            logger.error(f"Translation error: {e}")
            QMessageBox.critical(self, self.lang.t('error'), f"Translation failed: {e}")

    def _transliterate_author(self, name: str, src_lang: str, dest_lang: str) -> str:
        try:
            result = self.translator.translate(name, src=src_lang, dest=dest_lang)
            translated = result.text
            if dest_lang == "ar" and result.pronunciation:
                return f"{translated} ({result.pronunciation})"
            if dest_lang == "en" and result.pronunciation:
                return f"{result.pronunciation} ({translated})"
            return translated
        except Exception:
            result = self.translator.translate(name, src=src_lang, dest=dest_lang)
            return result.text

    def _load(self):
        entry = self.db.get_entry(self.entry_id)
        if not entry:
            return
        idx = self.type_combo.findText(entry.get('type', ''))
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)
        self.doi_input.setText(entry.get('doi', '') or '')
        self.bibtex_text.setText(entry.get('bibtex', '') or '')
        self.en_widgets['title'].setText(entry.get('title_en', '') or '')
        self.en_widgets['author'].setText(entry.get('author_en', '') or '')
        self.en_widgets['domain'].setText(entry.get('domain_en', '') or '')
        self.en_widgets['subdomain'].setText(entry.get('subdomain_en', '') or '')
        self.en_widgets['content'].setPlainText(entry.get('content_en', '') or '')
        self.ar_widgets['title'].setText(entry.get('title_ar', '') or '')
        self.ar_widgets['author'].setText(entry.get('author_ar', '') or '')
        self.ar_widgets['domain'].setText(entry.get('domain_ar', '') or '')
        self.ar_widgets['subdomain'].setText(entry.get('subdomain_ar', '') or '')
        self.ar_widgets['content'].setPlainText(entry.get('content_ar', '') or '')

    def _save(self):
        content_en = self.en_widgets['content'].toPlainText().strip()
        content_ar = self.ar_widgets['content'].toPlainText().strip()
        if not content_en and not content_ar:
            QMessageBox.warning(self, self.lang.t('error'), self.lang.t('entry_content_empty'))
            return
        data = {
            'title_en':     self.en_widgets['title'].text().strip(),
            'title_ar':     self.ar_widgets['title'].text().strip(),
            'type':         self.type_combo.currentText(),
            'content_en':   content_en,
            'content_ar':   content_ar,
            'author_en':    self.en_widgets['author'].text().strip(),
            'author_ar':    self.ar_widgets['author'].text().strip(),
            'domain_en':    self.en_widgets['domain'].text().strip(),
            'domain_ar':    self.ar_widgets['domain'].text().strip(),
            'subdomain_en': self.en_widgets['subdomain'].text().strip(),
            'subdomain_ar': self.ar_widgets['subdomain'].text().strip(),
            'doi':          self.doi_input.text().strip(),
            'bibtex':       self.bibtex_text.toPlainText().strip(),
        }
        try:
            if self.entry_id:
                self.db.update_entry(self.entry_id, data)
            else:
                self.db.add_entry(data)
            QMessageBox.information(self, self.lang.t('success'),
                                    self.lang.t('entry_updated' if self.entry_id else 'entry_added'))
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, self.lang.t('error'), str(e))


class ExplanationDialog(QDialog):
    """
    Bilingual explanation/proof dialog.
    No field is required — the user may fill either or both languages.
    """
    def __init__(self, db: KnowledgeDB, entry_id: str,
                 expl_id: Optional[str] = None, lang: Languages = None, parent=None):
        super().__init__(parent)
        self.db = db
        self.entry_id = entry_id
        self.expl_id = expl_id
        self.lang = lang or Languages()
        self.translator = Translator()  # Add translator
        self.setWindowTitle(self.lang.t('edit_proof_dialog' if expl_id else 'add_proof_dialog'))
        self.setGeometry(150, 150, 720, 620)  # Slightly taller to accommodate translation buttons
        self.setStyleSheet(APP_STYLE)
        self._build_ui()
        if expl_id:
            self._load()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(22, 20, 22, 20)
        root.addWidget(make_heading(
            self.lang.t('edit_proof_dialog' if self.expl_id else 'add_proof_dialog')
        ))
        root.addWidget(make_sep())

        # Language tabs (EN / AR)
        self.lang_tabs = QTabWidget()

        # ── English tab ───────────────────────────────────────────────────
        en_tab = QWidget()
        en_layout = QVBoxLayout(en_tab)
        en_layout.setSpacing(6)
        en_layout.setContentsMargins(10, 10, 10, 10)

        en_layout.addWidget(QLabel(f"{self.lang.t('proof_title')} (EN)"))
        self.title_en = QLineEdit()
        self.title_en.setMaximumHeight(32)
        en_layout.addWidget(self.title_en)

        en_layout.addWidget(QLabel(f"{self.lang.t('author')} (EN)"))
        self.author_en = QLineEdit()
        self.author_en.setMaximumHeight(32)
        en_layout.addWidget(self.author_en)

        en_layout.addWidget(QLabel(f"{self.lang.t('proof_content')} (EN)"))
        self.content_en = QTextEdit()
        self.content_en.setMinimumHeight(180)  # Slightly reduced to fit translation buttons
        en_layout.addWidget(self.content_en)
        en_layout.addStretch()

        # ── Arabic tab ────────────────────────────────────────────────────
        ar_tab = QWidget()
        ar_layout = QVBoxLayout(ar_tab)
        ar_layout.setSpacing(6)
        ar_layout.setContentsMargins(10, 10, 10, 10)

        ar_layout.addWidget(QLabel(f"{self.lang.t('proof_title')} (AR)"))
        self.title_ar = QLineEdit()
        self.title_ar.setMaximumHeight(32)
        self.title_ar.setAlignment(Qt.AlignRight)
        ar_layout.addWidget(self.title_ar)

        ar_layout.addWidget(QLabel(f"{self.lang.t('author')} (AR)"))
        self.author_ar = QLineEdit()
        self.author_ar.setMaximumHeight(32)
        self.author_ar.setAlignment(Qt.AlignRight)
        ar_layout.addWidget(self.author_ar)

        ar_layout.addWidget(QLabel(f"{self.lang.t('proof_content')} (AR)"))
        self.content_ar = QTextEdit()
        self.content_ar.setMinimumHeight(180)
        self.content_ar.document().setDefaultTextOption(QTextOption(Qt.AlignRight))
        ar_layout.addWidget(self.content_ar)
        ar_layout.addStretch()

        self.lang_tabs.addTab(en_tab, "English")
        self.lang_tabs.addTab(ar_tab, "العربية")
        root.addWidget(self.lang_tabs)

        # ── Translation buttons (similar to EntryDialog) ──────────────────
        translate_row = QHBoxLayout()
        translate_row.setSpacing(8)
        btn_en_to_ar = QPushButton("Translate EN → AR")
        btn_en_to_ar.setMaximumHeight(32)
        btn_en_to_ar.clicked.connect(lambda: self._translate("en", "ar"))
        translate_row.addWidget(btn_en_to_ar)
        btn_ar_to_en = QPushButton("Translate AR → EN")
        btn_ar_to_en.setMaximumHeight(32)
        btn_ar_to_en.clicked.connect(lambda: self._translate("ar", "en"))
        translate_row.addWidget(btn_ar_to_en)
        root.addLayout(translate_row)

        root.addWidget(make_sep())
        btns = QHBoxLayout()
        btns.addStretch()
        cancel_btn = QPushButton(self.lang.t('cancel'))
        cancel_btn.setMaximumHeight(32)
        cancel_btn.setMinimumWidth(100)
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton(self.lang.t('save'))
        save_btn.setMaximumHeight(32)
        save_btn.setMinimumWidth(100)
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self._save)
        btns.addWidget(cancel_btn)
        btns.addWidget(save_btn)
        root.addLayout(btns)

    def _get_widgets(self, lang_code: str) -> Dict:
        """Helper to get widgets for a specific language."""
        if lang_code == "en":
            return {
                'title': self.title_en,
                'author': self.author_en,
                'content': self.content_en,
            }
        else:
            return {
                'title': self.title_ar,
                'author': self.author_ar,
                'content': self.content_ar,
            }

    def _translate(self, src: str, dest: str):
        """Translate explanation fields from src language to dest language."""
        src_w = self._get_widgets(src)
        dest_w = self._get_widgets(dest)
        src_lang = "en" if src == "en" else "ar"
        dest_lang = "ar" if dest == "ar" else "en"
        
        fields = [
            ('title', 'text', 'setText'),
            ('author', 'text', 'setText'),
            ('content', 'toPlainText', 'setPlainText'),
        ]
        
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            for field_name, getter, setter in fields:
                src_widget = src_w[field_name]
                dest_widget = dest_w[field_name]
                source_text = src_widget.text().strip() if getter == 'text' \
                              else src_widget.toPlainText().strip()
                if not source_text:
                    continue
                
                if field_name == 'author':
                    translated = self._transliterate_author(source_text, src_lang, dest_lang)
                else:
                    result = self.translator.translate(source_text, src=src_lang, dest=dest_lang)
                    translated = result.text
                
                if setter == 'setText':
                    dest_widget.setText(translated)
                else:
                    dest_widget.setPlainText(translated)
                    
            QApplication.restoreOverrideCursor()
            QMessageBox.information(
                self, self.lang.t('success'),
                f"Translation {src.upper()} → {dest.upper()} complete."
            )
        except Exception as e:
            QApplication.restoreOverrideCursor()
            logger.error(f"Translation error: {e}")
            QMessageBox.critical(self, self.lang.t('error'), f"Translation failed: {e}")

    def _transliterate_author(self, name: str, src_lang: str, dest_lang: str) -> str:
        """Handle author name transliteration for better results."""
        try:
            result = self.translator.translate(name, src=src_lang, dest=dest_lang)
            translated = result.text
            if dest_lang == "ar" and result.pronunciation:
                return f"{translated} ({result.pronunciation})"
            if dest_lang == "en" and result.pronunciation:
                return f"{result.pronunciation} ({translated})"
            return translated
        except Exception:
            result = self.translator.translate(name, src=src_lang, dest=dest_lang)
            return result.text

    def _load(self):
        expl = self.db.get_explanation(self.expl_id)
        if not expl:
            return
        self.title_en.setText(expl.get('title_en', '') or '')
        self.title_ar.setText(expl.get('title_ar', '') or '')
        self.author_en.setText(expl.get('author_en', '') or '')
        self.author_ar.setText(expl.get('author_ar', '') or '')
        self.content_en.setPlainText(expl.get('content_en', '') or '')
        self.content_ar.setPlainText(expl.get('content_ar', '') or '')

    def _save(self):
        # No field is required — just save whatever was filled in
        data = {
            'title_en':   self.title_en.text().strip(),
            'title_ar':   self.title_ar.text().strip(),
            'author_en':  self.author_en.text().strip(),
            'author_ar':  self.author_ar.text().strip(),
            'content_en': self.content_en.toPlainText().strip(),
            'content_ar': self.content_ar.toPlainText().strip(),
        }
        try:
            if self.expl_id:
                self.db.update_explanation(self.expl_id, data)
            else:
                self.db.add_explanation(self.entry_id, data)
            QMessageBox.information(self, self.lang.t('success'),
                                    self.lang.t('proof_updated' if self.expl_id else 'proof_added'))
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, self.lang.t('error'), str(e))


class LaTeXDialog(QDialog):
    def __init__(self, latex_code: str, lang: Languages = None, parent=None):
        super().__init__(parent)
        self.lang = lang or Languages()
        self.setWindowTitle(self.lang.t('generated_latex'))
        self.setGeometry(150, 150, 720, 520)
        self.setStyleSheet(APP_STYLE)
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 20)
        root.setSpacing(10)
        root.addWidget(make_heading(self.lang.t('generated_latex')))
        root.addWidget(make_sep())
        self.text_edit = QTextEdit()
        self.text_edit.setText(latex_code)
        self.text_edit.setReadOnly(True)
        root.addWidget(self.text_edit)
        root.addWidget(make_sep())
        btns = QHBoxLayout()
        btns.addStretch()
        copy_btn = QPushButton(self.lang.t('btn_copy'))
        copy_btn.clicked.connect(lambda: self._copy(latex_code))
        save_btn = QPushButton(self.lang.t('btn_save_file'))
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(lambda: self._save(latex_code))
        close_btn = QPushButton(self.lang.t('close'))
        close_btn.clicked.connect(self.reject)
        btns.addWidget(copy_btn)
        btns.addWidget(save_btn)
        btns.addWidget(close_btn)
        root.addLayout(btns)

    def _copy(self, text):
        QApplication.clipboard().setText(text)
        QMessageBox.information(self, self.lang.t('success'), self.lang.t('latex_copied'))

    def _save(self, text):
        fp, _ = QFileDialog.getSaveFileName(self, self.lang.t('btn_save_file'), "", "LaTeX (*.tex)")
        if fp:
            with open(fp, 'w', encoding='utf-8') as f:
                f.write(text)
            QMessageBox.information(self, self.lang.t('success'),
                                    self.lang.t('latex_saved').format(path=fp))


class LinkDialog(QDialog):
    def __init__(self, db: KnowledgeDB, from_id: str, lang: Languages = None, parent=None):
        super().__init__(parent)
        self.db = db
        self.from_id = from_id
        self.lang = lang or Languages()
        self.setWindowTitle(self.lang.t('link_entry'))
        self.setGeometry(150, 150, 520, 460)
        self.setStyleSheet(APP_STYLE)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 20)
        root.setSpacing(10)
        root.addWidget(make_heading(self.lang.t('link_entry')))
        root.addWidget(make_sep())
        root.addWidget(QLabel(self.lang.t('relation_type')))
        self.relation_combo = QComboBox()
        self.relation_combo.addItems(RELATION_TYPES)
        root.addWidget(self.relation_combo)
        root.addWidget(QLabel(self.lang.t('link_to')))
        self.entry_list = QListWidget()
        for entry in self.db.get_all_entries():
            if entry['id'] != self.from_id:
                title = entry.get('title', '') or '—'
                item = QListWidgetItem(f"[{entry['type']}]  {title}")
                item.setData(Qt.UserRole, entry['id'])
                self.entry_list.addItem(item)
        root.addWidget(self.entry_list)
        root.addWidget(make_sep())
        btns = QHBoxLayout()
        btns.addStretch()
        cancel_btn = QPushButton(self.lang.t('cancel'))
        cancel_btn.clicked.connect(self.reject)
        link_btn = QPushButton(self.lang.t('btn_link'))
        link_btn.setObjectName("primary")
        link_btn.clicked.connect(self._create)
        btns.addWidget(cancel_btn)
        btns.addWidget(link_btn)
        root.addLayout(btns)

    def _create(self):
        if not self.entry_list.currentItem():
            QMessageBox.warning(self, self.lang.t('error'), self.lang.t('entry_select'))
            return
        to_id = self.entry_list.currentItem().data(Qt.UserRole)
        try:
            self.db.add_link(self.from_id, to_id, self.relation_combo.currentText())
            QMessageBox.information(self, self.lang.t('success'), self.lang.t('link_created'))
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, self.lang.t('error'), str(e))


class ManageTypesDialog(QDialog):
    def __init__(self, db: KnowledgeDB, lang: Languages = None, parent=None):
        super().__init__(parent)
        self.db = db
        self.lang = lang or Languages()
        self.setWindowTitle(self.lang.t('manage_types_title'))
        self.setGeometry(200, 200, 400, 500)
        self.setStyleSheet(APP_STYLE)
        self._build_ui()
        self._refresh()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 20)
        root.setSpacing(10)
        root.addWidget(make_heading(self.lang.t('manage_types_title')))
        root.addWidget(make_sep())
        root.addWidget(QLabel(self.lang.t('entry_types')))
        self.types_list = QListWidget()
        root.addWidget(self.types_list)
        root.addWidget(make_sep())
        add_row = QHBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(self.lang.t('type_name'))
        self.name_input.returnPressed.connect(self._add)
        add_row.addWidget(self.name_input)
        add_btn = QPushButton(self.lang.t('add_type'))
        add_btn.setObjectName("primary")
        add_btn.clicked.connect(self._add)
        add_row.addWidget(add_btn)
        root.addLayout(add_row)
        del_btn = QPushButton(self.lang.t('delete_type'))
        del_btn.setObjectName("danger")
        del_btn.clicked.connect(self._delete)
        root.addWidget(del_btn)
        root.addStretch()
        close_btn = QPushButton(self.lang.t('close'))
        close_btn.setObjectName("primary")
        close_btn.clicked.connect(self.accept)
        root.addWidget(close_btn)

    def _refresh(self):
        self.types_list.clear()
        for t in self.db.get_all_types():
            self.types_list.addItem(t['name'])

    def _add(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, self.lang.t('error'), self.lang.t('type_name_empty'))
            return
        try:
            self.db.add_type(name)
            self.name_input.clear()
            self._refresh()
        except Exception as e:
            QMessageBox.critical(self, self.lang.t('error'), str(e))

    def _delete(self):
        item = self.types_list.currentItem()
        if not item:
            QMessageBox.warning(self, self.lang.t('error'), self.lang.t('type_select'))
            return
        try:
            self.db.delete_type(item.text())
            self._refresh()
        except ValueError as e:
            if "type_in_use" in str(e):
                QMessageBox.warning(self, self.lang.t('warning'), self.lang.t('type_in_use'))
            else:
                QMessageBox.critical(self, self.lang.t('error'), str(e))


class SearchDialog(QDialog):
    def __init__(self, db: KnowledgeDB, lang: Languages = None, parent=None):
        super().__init__(parent)
        self.db = db
        self.lang = lang or Languages()
        self.setWindowTitle(self.lang.t('search_results_title'))
        self.setGeometry(60, 60, 1100, 700)
        self._results: List[Dict] = []
        self._related_results: List[Dict] = []
        self._occurrences: List[QTextCursor] = []
        self._occ_index = 0
        self._selected_entry_id: Optional[str] = None
        self._build_ui()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        lw = QWidget()
        lw.setFixedWidth(340)
        left = QVBoxLayout(lw)
        left.setContentsMargins(16, 16, 16, 16)
        left.setSpacing(10)
        left.addWidget(make_heading(self.lang.t('search_results_title')))
        sr = QHBoxLayout()
        sr.setSpacing(6)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.lang.t('search_placeholder'))
        self.search_input.returnPressed.connect(self._do_search)
        sr.addWidget(self.search_input)
        go_btn = QPushButton("⏎")
        go_btn.setFixedWidth(36)
        go_btn.clicked.connect(self._do_search)
        sr.addWidget(go_btn)
        left.addLayout(sr)
        self.status_label = QLabel("")
        left.addWidget(self.status_label)
        self.results_list = QListWidget()
        self.results_list.itemClicked.connect(self._on_result_clicked)
        left.addWidget(self.results_list)
        left.addWidget(make_sep())
        left.addWidget(make_heading("Relation Search"))
        self.relation_combo = QComboBox()
        for rt in RELATION_TYPES:
            self.relation_combo.addItem(rt)
        left.addWidget(self.relation_combo)
        self.search_relation_btn = QPushButton("Search by Relation")
        self.search_relation_btn.setEnabled(False)
        self.search_relation_btn.clicked.connect(self._do_relation_search)
        left.addWidget(self.search_relation_btn)
        root.addWidget(lw)
        mw = QWidget()
        mw.setFixedWidth(320)
        mid = QVBoxLayout(mw)
        mid.setContentsMargins(16, 16, 16, 16)
        mid.setSpacing(10)
        mid.addWidget(make_heading("Related Entries"))
        self.related_status_label = QLabel("")
        mid.addWidget(self.related_status_label)
        self.related_list = QListWidget()
        self.related_list.itemClicked.connect(self._on_related_clicked)
        mid.addWidget(self.related_list)
        root.addWidget(mw)
        rw = QWidget()
        right = QVBoxLayout(rw)
        right.setContentsMargins(20, 16, 20, 16)
        right.setSpacing(10)
        top = QHBoxLayout()
        self.entry_title_label = QLabel("")
        self.entry_title_label.setObjectName("entry_title")
        top.addWidget(self.entry_title_label)
        top.addStretch()
        close_btn = QPushButton(self.lang.t('close'))
        close_btn.clicked.connect(self.accept)
        top.addWidget(close_btn)
        right.addLayout(top)
        right.addWidget(make_sep())
        self.content_view = QTextEdit()
        self.content_view.setReadOnly(True)
        right.addWidget(self.content_view)
        nav_w = QWidget()
        nav = QHBoxLayout(nav_w)
        nav.setContentsMargins(12, 6, 12, 6)
        nav.setSpacing(10)
        self.prev_btn = QPushButton("◀  " + self.lang.t('prev'))
        self.prev_btn.clicked.connect(self._prev_occ)
        self.prev_btn.setEnabled(False)
        self.next_btn = QPushButton(self.lang.t('next') + "  ▶")
        self.next_btn.clicked.connect(self._next_occ)
        self.next_btn.setEnabled(False)
        self.occ_label = QLabel("")
        nav.addWidget(self.prev_btn)
        nav.addWidget(self.occ_label)
        nav.addStretch()
        nav.addWidget(self.next_btn)
        right.addWidget(nav_w)
        root.addWidget(rw)

    def _do_search(self):
        query = self.search_input.text().strip()
        if not query:
            return
        self._results = self.db.search(query)
        self.results_list.clear()
        self.related_list.clear()
        self.content_view.clear()
        self.entry_title_label.setText("")
        self.related_status_label.setText("")
        self._occurrences = []
        self._occ_index = 0
        self.occ_label.setText("")
        self.prev_btn.setEnabled(False)
        self.next_btn.setEnabled(False)
        self._selected_entry_id = None
        self.search_relation_btn.setEnabled(False)
        if not self._results:
            self.status_label.setText(self.lang.t('search_no_results', query=query))
            return
        self.status_label.setText(f"{len(self._results)} result(s)")
        for entry in self._results:
            title = entry.get('title', '') or '—'
            item = QListWidgetItem(f"[{entry['type']}]  {title}")
            item.setData(Qt.UserRole, entry['id'])
            self.results_list.addItem(item)

    def _on_result_clicked(self, item: QListWidgetItem):
        entry_id = item.data(Qt.UserRole)
        entry = self.db.get_entry(entry_id)
        if not entry:
            return
        self._selected_entry_id = entry_id
        self.search_relation_btn.setEnabled(True)
        self.related_list.clear()
        self.related_status_label.setText("")
        lang_code = self.lang.current_lang
        if lang_code == 'ar':
            title   = entry.get('title_ar', '')   or entry.get('title_en', '')   or '—'
            content = entry.get('content_ar', '') or entry.get('content_en', '')
        else:
            title   = entry.get('title_en', '')   or entry.get('title_ar', '')   or '—'
            content = entry.get('content_en', '') or entry.get('content_ar', '')
        query = self.search_input.text().strip()
        self.entry_title_label.setText(f"[{entry['type']}]  {title}")
        self.content_view.setPlainText(content)
        self._highlight_all(query)

    def _do_relation_search(self):
        if not self._selected_entry_id:
            return
        relation = self.relation_combo.currentText()
        self._related_results = self.db.search_related(self._selected_entry_id, relation)
        self.related_list.clear()
        if not self._related_results:
            self.related_status_label.setText(f"No '{relation}' links found")
            return
        self.related_status_label.setText(
            f"{len(self._related_results)} entry(ies) via '{relation}'"
        )
        for entry in self._related_results:
            title = entry.get('title', '') or '—'
            item = QListWidgetItem(f"[{entry['type']}]  {title}")
            item.setData(Qt.UserRole, entry['id'])
            self.related_list.addItem(item)

    def _on_related_clicked(self, item: QListWidgetItem):
        entry_id = item.data(Qt.UserRole)
        entry = self.db.get_entry(entry_id)
        if not entry:
            return
        lang_code = self.lang.current_lang
        if lang_code == 'ar':
            title   = entry.get('title_ar', '')   or entry.get('title_en', '')   or '—'
            content = entry.get('content_ar', '') or entry.get('content_en', '')
        else:
            title   = entry.get('title_en', '')   or entry.get('title_ar', '')   or '—'
            content = entry.get('content_en', '') or entry.get('content_ar', '')
        self.entry_title_label.setText(f"[{entry['type']}]  {title}")
        self.content_view.setPlainText(content)
        self._occurrences = []
        self._occ_index = 0
        self.occ_label.setText("")
        self.prev_btn.setEnabled(False)
        self.next_btn.setEnabled(False)
        query = self.search_input.text().strip()
        if query:
            self._highlight_all(query)

    def _highlight_all(self, query: str):
        if not query:
            return
        doc = self.content_view.document()
        self._occurrences = []
        fmt_dim = QTextCharFormat()
        fmt_dim.setBackground(QColor("#FFFF00"))
        fmt_dim.setForeground(QColor("#000000"))
        cursor = QTextCursor(doc)
        while True:
            cursor = doc.find(query, cursor)
            if cursor.isNull():
                break
            cursor.mergeCharFormat(fmt_dim)
            self._occurrences.append(QTextCursor(cursor))
        self._occ_index = 0
        n = len(self._occurrences)
        if n > 0:
            self._jump_to(0)
            self.next_btn.setEnabled(n > 1)
            self.prev_btn.setEnabled(n > 1)
        else:
            self.occ_label.setText("—")

    def _jump_to(self, index: int):
        if not self._occurrences:
            return
        self._occ_index = index % len(self._occurrences)
        fmt_active = QTextCharFormat()
        fmt_active.setBackground(QColor("#FF8C00"))
        fmt_active.setForeground(QColor("#000000"))
        fmt_dim = QTextCharFormat()
        fmt_dim.setBackground(QColor("#FFFF00"))
        fmt_dim.setForeground(QColor("#000000"))
        for i, c in enumerate(self._occurrences):
            c.mergeCharFormat(fmt_active if i == self._occ_index else fmt_dim)
        self.content_view.setTextCursor(self._occurrences[self._occ_index])
        self.content_view.ensureCursorVisible()
        self.occ_label.setText(
            self.lang.t('search_occurrence', n=self._occ_index + 1, total=len(self._occurrences))
        )

    def _next_occ(self):
        self._jump_to(self._occ_index + 1)

    def _prev_occ(self):
        self._jump_to(self._occ_index - 1)


# ============================================================================
# EMBEDDABLE WIDGET (for tab integration)
# ============================================================================
class KnowledgeDBWidget(QWidget):
    """QWidget version of the Knowledge Database Manager for embedding in tabs."""

    def __init__(self, lang: str = 'en', db_path: str = None,
                 main_window=None, parent=None):
        super().__init__(parent)
        self.main_window_ref = main_window
        if main_window and hasattr(main_window, 'menu_language'):
            lang = main_window.menu_language
        self.lang = Languages(lang)
        if db_path is None:
            db_path = os.path.join(KnowledgeDB._get_config_directory(), "knowledge.db")
        self.db = KnowledgeDB(db_path, self.lang)
        self.db.init_schema()
        self.current_entry_id: Optional[str] = None
        self.current_expl_id:  Optional[str] = None
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)
        self._init_ui()
        self.load_entries()

    # ── Status bar helper ─────────────────────────────────────────────────────
    def _set_status(self, message: str):
        """Update the main window's status bar, with graceful fallback."""
        try:
            if self.main_window_ref and hasattr(self.main_window_ref, 'update_status_bar'):
                self.main_window_ref.update_status_bar(message)
        except Exception:
            pass  # silently ignore if main window is gone

    def _change_language(self, index):
        code = self.lang_combo.itemData(index)
        if not code or not self.lang.set_language(code):
            return
        if self.main_window_ref and hasattr(self.main_window_ref, 'menu_language'):
            self.main_window_ref.menu_language = code
        self._rebuild_ui()

    def refresh_language(self):
        if self.main_window_ref and hasattr(self.main_window_ref, 'menu_language'):
            new_lang = self.main_window_ref.menu_language
            if new_lang != self.lang.current_lang:
                self.lang.set_language(new_lang)
                self._rebuild_ui()

    def _init_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Toolbar ───────────────────────────────────────────────────────────
        # NOTE: "Insert LaTeX at Cursor" and "Generate LaTeX" are intentionally
        # omitted here — they live in the bottom-right panel below.
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(14, 14))
        toolbar.setMovable(False)

        def act(icon_char, key, slot):
            a = QAction(f"{icon_char}  {self.lang.t(key)}", self)
            a.triggered.connect(slot)
            return a

        toolbar.addAction(act("＋", 'tb_add',    self._add_entry))
        toolbar.addAction(act("✎",  'tb_edit',   self._edit_entry))
        toolbar.addAction(act("✕",  'tb_delete', self._delete_entry))
        toolbar.addSeparator()
        toolbar.addAction(act("⌕",  'tb_search',       self._open_search))
        toolbar.addAction(act("⊞",  'tb_manage_types', self._manage_types))
        toolbar.addSeparator()
        toolbar.addAction(act("⊙",  'tb_backup',  self._backup_db))
        toolbar.addAction(act("↺",  'tb_restore', self._restore_db))
        toolbar.addAction(act("⚙",  'tb_repair',  self._repair_db))
        toolbar.addSeparator()

        self.lang_combo = QComboBox()
        self.lang_combo.setFixedWidth(130)
        self.lang_combo.addItem("English", "en")
        self.lang_combo.addItem("العربية", "ar")
        idx = self.lang_combo.findData(self.lang.current_lang)
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)
        self.lang_combo.currentIndexChanged.connect(self._change_language)
        toolbar.addWidget(self.lang_combo)
        outer.addWidget(toolbar)

        # ── Splitter ──────────────────────────────────────────────────────────
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(4)
        splitter.setChildrenCollapsible(False)

        # ── Left panel ────────────────────────────────────────────────────────
        left_widget = QWidget()
        left_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left = QVBoxLayout(left_widget)
        left.setContentsMargins(10, 10, 10, 10)
        left.setSpacing(8)

        lhdr = QHBoxLayout()
        lhdr.addWidget(make_heading(self.lang.t('entries')))
        lhdr.addStretch()
        self.count_label = QLabel("0")
        font = self.count_label.font()
        font.setBold(True)
        self.count_label.setFont(font)
        lhdr.addWidget(self.count_label)
        left.addLayout(lhdr)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.lang.t('search_placeholder'))
        self.search_input.textChanged.connect(self._quick_filter)
        left.addWidget(self.search_input)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)
        filter_row.addWidget(QLabel(self.lang.t('type')))
        self.type_filter = QComboBox()
        self.type_filter.addItem(self.lang.t('all'))
        self.type_filter.currentTextChanged.connect(self._apply_filters)
        filter_row.addWidget(self.type_filter)
        filter_row.addWidget(QLabel(self.lang.t('domain')))
        self.domain_filter = QComboBox()
        self.domain_filter.addItem(self.lang.t('all'))
        self.domain_filter.currentTextChanged.connect(self._apply_filters)
        filter_row.addWidget(self.domain_filter)
        left.addLayout(filter_row)

        self.entries_table = SortableTable()
        self.entries_table.setColumnCount(5)
        self.entries_table.setHorizontalHeaderLabels([
            self.lang.t('id_col'),
            self.lang.t('title'),
            self.lang.t('type'),
            self.lang.t('domain'),
            self.lang.t('author'),
        ])
        self.entries_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.entries_table.horizontalHeader().setSortIndicatorShown(True)
        self.entries_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.entries_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.entries_table.verticalHeader().setVisible(False)
        self.entries_table.setColumnWidth(0, 88)
        self.entries_table.setColumnWidth(2, 110)
        self.entries_table.setColumnWidth(3, 100)
        self.entries_table.setColumnWidth(4, 100)
        self.entries_table.cellClicked.connect(self._on_entry_selected)
        left.addWidget(self.entries_table)

        # ── Right panel ───────────────────────────────────────────────────────
        right_widget = QWidget()
        right_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        right = QVBoxLayout(right_widget)
        right.setContentsMargins(10, 10, 10, 10)
        right.setSpacing(8)

        self.detail_header = QLabel(self.lang.t('entry_details'))
        self.detail_header.setObjectName("entry_title")
        font = self.detail_header.font()
        font.setPointSize(font.pointSize() + 2)
        font.setItalic(True)
        self.detail_header.setFont(font)
        right.addWidget(self.detail_header)
        right.addWidget(make_sep())

        self.tabs = QTabWidget()

        # Content tab
        ct = QWidget()
        cl = QVBoxLayout(ct)
        cl.setContentsMargins(0, 8, 0, 0)
        self.content_display = QTextEdit()
        self.content_display.setReadOnly(True)
        cl.addWidget(self.content_display)
        self.tabs.addTab(ct, self.lang.t('content'))

        # Metadata tab
        mt = QWidget()
        ml = QVBoxLayout(mt)
        ml.setContentsMargins(0, 8, 0, 0)
        self.meta_display = QTextEdit()
        self.meta_display.setReadOnly(True)
        ml.addWidget(self.meta_display)
        self.tabs.addTab(mt, self.lang.t('metadata'))

        # Explanations tab
        et = QWidget()
        el = QVBoxLayout(et)
        el.setContentsMargins(0, 8, 0, 0)
        el.setSpacing(8)
        self.expls_list = QListWidget()
        self.expls_list.itemClicked.connect(self._on_expl_selected)
        el.addWidget(self.expls_list)
        expl_btns = QHBoxLayout()
        expl_btns.setSpacing(6)
        for label, slot in [
            (self.lang.t('add_proof'),    self._add_expl),
            (self.lang.t('edit_proof'),   self._edit_expl),
            (self.lang.t('delete_proof'), self._delete_expl),
        ]:
            btn = QPushButton(label)
            btn.clicked.connect(slot)
            expl_btns.addWidget(btn)
        el.addLayout(expl_btns)
        self.expl_display = QTextEdit()
        self.expl_display.setReadOnly(True)
        self.expl_display.setMaximumHeight(140)
        el.addWidget(self.expl_display)
        self.tabs.addTab(et, self.lang.t('proofs'))

        # Links tab
        lt2 = QWidget()
        ll = QVBoxLayout(lt2)
        ll.setContentsMargins(0, 8, 0, 0)
        ll.setSpacing(8)
        self.links_list = QListWidget()
        ll.addWidget(self.links_list)
        link_btns = QHBoxLayout()
        link_btns.setSpacing(6)
        alb = QPushButton(self.lang.t('btn_add_link'))
        alb.clicked.connect(self._add_link)
        dlb = QPushButton(self.lang.t('btn_delete_link'))
        dlb.clicked.connect(self._delete_link)
        link_btns.addWidget(alb)
        link_btns.addWidget(dlb)
        ll.addLayout(link_btns)
        self.tabs.addTab(lt2, self.lang.t('links'))

        right.addWidget(self.tabs)

        # ── LaTeX operations (bottom-right) ───────────────────────────────────
        right.addWidget(make_sep())
        latex_ops_frame = QFrame()
        latex_ops_frame.setFrameShape(QFrame.StyledPanel)
        latex_ops = QVBoxLayout(latex_ops_frame)
        latex_ops.setSpacing(8)

        insert_latex_btn = QPushButton("⬅ Insert LaTeX at Cursor")
        insert_latex_btn.setMinimumHeight(32)
        insert_latex_btn.setToolTip("Insert LaTeX code directly into the editor")
        insert_latex_btn.clicked.connect(self._insert_latex_to_editor)
        latex_ops.addWidget(insert_latex_btn)

        gen_latex_btn = QPushButton("📄 Generate LaTeX")
        gen_latex_btn.setMinimumHeight(32)
        gen_latex_btn.clicked.connect(self._generate_latex_dialog)
        latex_ops.addWidget(gen_latex_btn)

        right.addWidget(latex_ops_frame)

        # ── Add to splitter ───────────────────────────────────────────────────
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        outer.addWidget(splitter)
        # (no status_label — status goes through main window's update_status_bar)

    # ── All methods ───────────────────────────────────────────────────────────
    def load_entries(self):
        entries = self.db.get_all_entries()
        lang_code = self.lang.current_lang
        for entry in entries:
            if lang_code == 'ar':
                entry['title']  = entry.get('title_ar', '')  or entry.get('title_en', '')
                entry['domain'] = entry.get('domain_ar', '') or entry.get('domain_en', '')
            else:
                entry['title']  = entry.get('title_en', '')  or entry.get('title_ar', '')
                entry['domain'] = entry.get('domain_en', '') or entry.get('domain_ar', '')
        types = self.db.get_unique_types_in_use()
        domains = sorted(set(e.get('domain', '') for e in entries if e.get('domain', '')))
        all_lbl = self.lang.t('all')
        self.type_filter.blockSignals(True)
        self.type_filter.clear()
        self.type_filter.addItem(all_lbl)
        self.type_filter.addItems(types)
        self.type_filter.blockSignals(False)
        self.domain_filter.blockSignals(True)
        self.domain_filter.clear()
        self.domain_filter.addItem(all_lbl)
        self.domain_filter.addItems(domains)
        self.domain_filter.blockSignals(False)
        self.entries_table.load_data(entries)
        self.count_label.setText(str(len(entries)))

    def _on_entry_selected(self, row, col):
        item = self.entries_table.item(row, 0)
        if item:
            eid = item.data(Qt.UserRole)
            if eid:
                self.current_entry_id = eid
                self._display_entry()

    def _display_entry(self):
        if not self.current_entry_id:
            return
        entry = self.db.get_entry(self.current_entry_id)
        if not entry:
            return
        lang_code = self.lang.current_lang
        if lang_code == 'ar':
            title     = entry.get('title_ar', '')     or entry.get('title_en', '')     or '—'
            content   = entry.get('content_ar', '')   or entry.get('content_en', '')
            author    = entry.get('author_ar', '')     or entry.get('author_en', '')     or '—'
            domain    = entry.get('domain_ar', '')     or entry.get('domain_en', '')     or '—'
            subdomain = entry.get('subdomain_ar', '') or entry.get('subdomain_en', '') or '—'
        else:
            title     = entry.get('title_en', '')     or entry.get('title_ar', '')     or '—'
            content   = entry.get('content_en', '')   or entry.get('content_ar', '')
            author    = entry.get('author_en', '')     or entry.get('author_ar', '')     or '—'
            domain    = entry.get('domain_en', '')     or entry.get('domain_ar', '')     or '—'
            subdomain = entry.get('subdomain_en', '') or entry.get('subdomain_ar', '') or '—'
        etype = entry.get('type', '')
        self.detail_header.setText(f"[{etype}]  {title}")
        self.content_display.setText(content)
        L = self.lang
        self.meta_display.setText("\n".join([
            f"ID          {entry.get('id', '')}",
            f"{L.t('title')}       {title}",
            f"{L.t('type')}        {etype}",
            f"{L.t('author')}      {author}",
            f"{L.t('domain')}      {domain}",
            f"{L.t('subdomain')}   {subdomain}",
            f"{L.t('doi')}         {entry.get('doi', '') or '—'}",
            f"{L.t('created')}     {entry.get('date_created', '')}",
            f"{L.t('modified')}    {entry.get('date_modified', '')}",
            "",
            f"{L.t('bibtex')}",
            entry.get('bibtex', '') or '—',
            "",
            "─── Alternate Language ───",
            f"EN: {entry.get('title_en', '') or '—'}",
            f"AR: {entry.get('title_ar', '') or '—'}",
        ]))
        self._display_expls()
        self._display_links()
        self._set_status(f"{etype}  ·  {title}  ·  {entry.get('id', '')}")

    def _display_expls(self):
        if not self.current_entry_id:
            return
        self.expls_list.clear()
        self.expl_display.clear()
        self.current_expl_id = None
        expls = self.db.get_explanations_for_entry(self.current_entry_id)
        if not expls:
            ph = QListWidgetItem(self.lang.t('no_proofs'))
            ph.setForeground(QColor(Qt.gray))
            ph.setFlags(ph.flags() & ~Qt.ItemIsSelectable)
            self.expls_list.addItem(ph)
            return
        for expl in expls:
            t = expl.get('title', '') or 'Explanation'
            a = expl.get('author', '') or ''
            item = QListWidgetItem(f"{t}  —  {a}" if a else t)
            item.setData(Qt.UserRole, expl.get('id'))
            self.expls_list.addItem(item)

    def _on_expl_selected(self, item):
        expl_id = item.data(Qt.UserRole)
        if expl_id:
            self.current_expl_id = expl_id
            expl = self.db.get_explanation(expl_id)
            if expl:
                self.expl_display.setText(expl.get('content', ''))

    def _display_links(self):
        if not self.current_entry_id:
            return
        self.links_list.clear()
        for link in self.db.get_links(self.current_entry_id):
            tt = link.get('target_title', '') or '—'
            ty = link.get('target_type', '')
            item = QListWidgetItem(f"{link.get('relation', '')}  →  [{ty}] {tt}")
            item.setData(Qt.UserRole, link.get('id'))
            self.links_list.addItem(item)

    def _quick_filter(self):
        q = self.search_input.text()
        entries = self.db.search(q) if q.strip() else self.db.get_all_entries()
        self._filter_and_display(entries)

    def _apply_filters(self):
        self._filter_and_display(self.db.get_all_entries())

    def _filter_and_display(self, entries):
        all_lbl = self.lang.t('all')
        t = self.type_filter.currentText()
        d = self.domain_filter.currentText()
        if t != all_lbl:
            entries = [e for e in entries if e.get('type') == t]
        if d != all_lbl:
            entries = [e for e in entries if e.get('domain') == d]
        self.entries_table.load_data(entries)
        self.count_label.setText(str(len(entries)))

    def _add_entry(self):
        dlg = EntryDialog(self.db, lang=self.lang, parent=self)
        if dlg.exec_():
            self.load_entries()

    def _edit_entry(self):
        if not self.current_entry_id:
            QMessageBox.warning(self, self.lang.t('error'), self.lang.t('entry_select'))
            return
        dlg = EntryDialog(self.db, self.current_entry_id, lang=self.lang, parent=self)
        if dlg.exec_():
            self.load_entries()
            self._display_entry()

    def _delete_entry(self):
        if not self.current_entry_id:
            QMessageBox.warning(self, self.lang.t('error'), self.lang.t('entry_select'))
            return
        reply = QMessageBox.question(self, self.lang.t('confirm'),
                                     f"{self.lang.t('tb_delete')}?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                self.db.delete_entry(self.current_entry_id)
                self.current_entry_id = None
                self.detail_header.setText(self.lang.t('entry_details'))
                for w in (self.content_display, self.meta_display, self.expl_display):
                    w.clear()
                self.expls_list.clear()
                self.links_list.clear()
                self.load_entries()
            except Exception as e:
                QMessageBox.critical(self, self.lang.t('error'), str(e))

    def _add_expl(self):
        if not self.current_entry_id:
            QMessageBox.warning(self, self.lang.t('error'), self.lang.t('entry_select'))
            return
        dlg = ExplanationDialog(self.db, self.current_entry_id, lang=self.lang, parent=self)
        if dlg.exec_():
            self._display_expls()

    def _edit_expl(self):
        if not self.current_expl_id:
            QMessageBox.warning(self, self.lang.t('error'), self.lang.t('proof_select'))
            return
        dlg = ExplanationDialog(self.db, self.current_entry_id, self.current_expl_id,
                                lang=self.lang, parent=self)
        if dlg.exec_():
            self._display_expls()

    def _delete_expl(self):
        if not self.current_expl_id:
            QMessageBox.warning(self, self.lang.t('error'), self.lang.t('proof_select'))
            return
        reply = QMessageBox.question(self, self.lang.t('confirm'),
                                     f"{self.lang.t('delete_proof')}?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                self.db.delete_explanation(self.current_expl_id)
                self.current_expl_id = None
                self._display_expls()
            except Exception as e:
                QMessageBox.critical(self, self.lang.t('error'), str(e))

    def _add_link(self):
        if not self.current_entry_id:
            QMessageBox.warning(self, self.lang.t('error'), self.lang.t('entry_select'))
            return
        dlg = LinkDialog(self.db, self.current_entry_id, lang=self.lang, parent=self)
        if dlg.exec_():
            self._display_links()

    def _delete_link(self):
        if not self.links_list.currentItem():
            QMessageBox.warning(self, self.lang.t('error'), self.lang.t('link_select'))
            return
        link_id = self.links_list.currentItem().data(Qt.UserRole)
        reply = QMessageBox.question(self, self.lang.t('confirm'),
                                     f"{self.lang.t('btn_delete_link')}?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                self.db.delete_link(link_id)
                self._display_links()
            except Exception as e:
                QMessageBox.critical(self, self.lang.t('error'), str(e))

    def _insert_latex_to_editor(self):
        if not self.current_entry_id:
            QMessageBox.warning(self, self.lang.t('error'), self.lang.t('entry_select'))
            return
        latex = self.db.generate_latex(
            self.current_entry_id, include_explanations=True, lang=self.lang.current_lang
        )
        if not latex:
            QMessageBox.warning(self, self.lang.t('error'), self.lang.t('latex_error'))
            return
        try:
            main_window = self.main_window_ref
            if not main_window:
                parent = self.parent()
                while parent:
                    if hasattr(parent, 'editor_manager'):
                        main_window = parent
                        break
                    parent = parent.parent() if hasattr(parent, 'parent') else None
            if main_window and hasattr(main_window, 'editor_manager'):
                active_editor = main_window.editor_manager.get_active_editor()
                if active_editor:
                    cursor = active_editor.textCursor()
                    cursor.insertText(latex)
                    active_editor.setTextCursor(cursor)
                    active_editor.setFocus()
                    if hasattr(main_window.editor_manager, 'on_text_changed'):
                        main_window.editor_manager.on_text_changed()
                    self._set_status("LaTeX inserted into editor.")
                    QMessageBox.information(self, self.lang.t('success'),
                                            "LaTeX code inserted into editor!")
                    return
            LaTeXDialog(latex, lang=self.lang, parent=self).exec_()
        except Exception as e:
            logger.error(f"Insert LaTeX error: {e}")
            QMessageBox.critical(self, self.lang.t('error'), f"Failed to insert LaTeX:\n{str(e)}")

    def _generate_latex_dialog(self):
        if not self.current_entry_id:
            QMessageBox.warning(self, self.lang.t('error'), self.lang.t('entry_select'))
            return
        latex = self.db.generate_latex(
            self.current_entry_id, include_explanations=True, lang=self.lang.current_lang
        )
        if not latex:
            QMessageBox.warning(self, self.lang.t('error'), self.lang.t('latex_error'))
            return
        LaTeXDialog(latex, lang=self.lang, parent=self).exec_()

    def _open_search(self):
        SearchDialog(self.db, lang=self.lang, parent=self).exec_()

    def _manage_types(self):
        ManageTypesDialog(self.db, lang=self.lang, parent=self).exec_()
        self.load_entries()

    def _backup_db(self):
        path = self.db.recovery.create_backup()
        if path:
            msg = self.lang.t('db_backup_created').format(path=path)
            self._set_status(msg)
            QMessageBox.information(self, self.lang.t('success'), msg)
        else:
            QMessageBox.warning(self, self.lang.t('warning'), self.lang.t('error'))

    def _restore_db(self):
        fp, _ = QFileDialog.getOpenFileName(self, self.lang.t('tb_restore'),
                                            "backups", "Database Files (*.db)")
        if fp:
            if self.db.recovery.restore_backup(fp):
                self.db._init_connection()
                self.load_entries()
                QMessageBox.information(self, self.lang.t('success'), self.lang.t('db_restored'))
            else:
                QMessageBox.critical(self, self.lang.t('error'), self.lang.t('db_recovery_failed'))

    def _repair_db(self):
        if self.db.recovery.repair_database():
            self.db._init_connection()
            self.load_entries()
            QMessageBox.information(self, self.lang.t('success'), self.lang.t('db_recovery_success'))
        else:
            QMessageBox.critical(self, self.lang.t('error'), self.lang.t('db_recovery_failed'))

    def _rebuild_ui(self):
        saved_entry_id = self.current_entry_id
        saved_expl_id  = self.current_expl_id
        old_layout = self.layout()
        if old_layout is not None:
            while old_layout.count():
                item = old_layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.setParent(None)
                    widget.deleteLater()
            QWidget().setLayout(old_layout)
        self._init_ui()
        self.load_entries()
        self.current_entry_id = saved_entry_id
        self.current_expl_id  = saved_expl_id
        if self.current_entry_id:
            self._display_entry()
        self.lang_combo.blockSignals(True)
        idx = self.lang_combo.findData(self.lang.current_lang)
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)
        self.lang_combo.blockSignals(False)


# ============================================================================
# MAIN APPLICATION (standalone)
# ============================================================================
# class KnowledgeDBApp(QMainWindow):
    # def __init__(self, lang: str = 'en', db_path: str = None):
        # super().__init__()
        # self.lang = Languages(lang)
        # if db_path is None:
            # db_path = os.path.join(KnowledgeDB._get_config_directory(), "knowledge.db")
        # self.db = KnowledgeDB(db_path, self.lang)
        # self.current_entry_id: Optional[str] = None
        # self.current_expl_id:  Optional[str] = None
        # self.setWindowTitle(self.lang.t('app_title'))
        # self.setGeometry(40, 40, 1500, 900)
        # self.setMinimumSize(1100, 700)
        # self.setStyleSheet(APP_STYLE)
        # self._init_ui()
        # self.load_entries()

    # def _init_ui(self):
        # self._create_toolbar()
        # self._create_statusbar()
        # central = QWidget()
        # self.setCentralWidget(central)
        # main_layout = QHBoxLayout(central)
        # main_layout.setContentsMargins(0, 0, 0, 0)
        # main_layout.setSpacing(0)
        # splitter = QSplitter(Qt.Horizontal)
        # splitter.setHandleWidth(2)

        # # ── Left panel ────────────────────────────────────────────────────────
        # left_widget = QWidget()
        # left = QVBoxLayout(left_widget)
        # left.setContentsMargins(14, 14, 14, 14)
        # left.setSpacing(8)
        # lhdr = QHBoxLayout()
        # lhdr.addWidget(make_heading(self.lang.t('entries')))
        # lhdr.addStretch()
        # self.count_label = QLabel("0")
        # font = self.count_label.font()
        # font.setBold(True)
        # self.count_label.setFont(font)
        # lhdr.addWidget(self.count_label)
        # left.addLayout(lhdr)
        # self.search_input = QLineEdit()
        # self.search_input.setPlaceholderText(self.lang.t('search_placeholder'))
        # self.search_input.textChanged.connect(self._quick_filter)
        # left.addWidget(self.search_input)
        # filter_row = QHBoxLayout()
        # filter_row.setSpacing(8)
        # filter_row.addWidget(QLabel(self.lang.t('type')))
        # self.type_filter = QComboBox()
        # self.type_filter.addItem(self.lang.t('all'))
        # self.type_filter.currentTextChanged.connect(self._apply_filters)
        # filter_row.addWidget(self.type_filter)
        # filter_row.addWidget(QLabel(self.lang.t('domain')))
        # self.domain_filter = QComboBox()
        # self.domain_filter.addItem(self.lang.t('all'))
        # self.domain_filter.currentTextChanged.connect(self._apply_filters)
        # filter_row.addWidget(self.domain_filter)
        # left.addLayout(filter_row)
        # self.entries_table = SortableTable()
        # self.entries_table.setColumnCount(5)
        # self.entries_table.setHorizontalHeaderLabels([
            # self.lang.t('id_col'), self.lang.t('title'), self.lang.t('type'),
            # self.lang.t('domain'), self.lang.t('author'),
        # ])
        # self.entries_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        # self.entries_table.horizontalHeader().setSortIndicatorShown(True)
        # self.entries_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        # self.entries_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # self.entries_table.verticalHeader().setVisible(False)
        # self.entries_table.setColumnWidth(0, 88)
        # self.entries_table.setColumnWidth(2, 110)
        # self.entries_table.setColumnWidth(3, 100)
        # self.entries_table.setColumnWidth(4, 100)
        # self.entries_table.cellClicked.connect(self._on_entry_selected)
        # left.addWidget(self.entries_table)

        # # ── Right panel ───────────────────────────────────────────────────────
        # right_widget = QWidget()
        # right = QVBoxLayout(right_widget)
        # right.setContentsMargins(18, 14, 18, 14)
        # right.setSpacing(8)
        # self.detail_header = QLabel(self.lang.t('entry_details'))
        # self.detail_header.setObjectName("entry_title")
        # font = self.detail_header.font()
        # font.setPointSize(font.pointSize() + 2)
        # font.setItalic(True)
        # self.detail_header.setFont(font)
        # right.addWidget(self.detail_header)
        # right.addWidget(make_sep())
        # self.tabs = QTabWidget()
        # ct = QWidget()
        # cl = QVBoxLayout(ct)
        # cl.setContentsMargins(0, 8, 0, 0)
        # self.content_display = QTextEdit()
        # self.content_display.setReadOnly(True)
        # cl.addWidget(self.content_display)
        # self.tabs.addTab(ct, self.lang.t('content'))
        # mt = QWidget()
        # ml = QVBoxLayout(mt)
        # ml.setContentsMargins(0, 8, 0, 0)
        # self.meta_display = QTextEdit()
        # self.meta_display.setReadOnly(True)
        # ml.addWidget(self.meta_display)
        # self.tabs.addTab(mt, self.lang.t('metadata'))
        # et = QWidget()
        # el = QVBoxLayout(et)
        # el.setContentsMargins(0, 8, 0, 0)
        # el.setSpacing(8)
        # self.expls_list = QListWidget()
        # self.expls_list.itemClicked.connect(self._on_expl_selected)
        # el.addWidget(self.expls_list)
        # expl_btns = QHBoxLayout()
        # expl_btns.setSpacing(6)
        # for label, slot in [
            # (self.lang.t('add_proof'),    self._add_expl),
            # (self.lang.t('edit_proof'),   self._edit_expl),
            # (self.lang.t('delete_proof'), self._delete_expl),
        # ]:
            # btn = QPushButton(label)
            # btn.clicked.connect(slot)
            # expl_btns.addWidget(btn)
        # el.addLayout(expl_btns)
        # self.expl_display = QTextEdit()
        # self.expl_display.setReadOnly(True)
        # self.expl_display.setMaximumHeight(140)
        # el.addWidget(self.expl_display)
        # self.tabs.addTab(et, self.lang.t('proofs'))
        # lt2 = QWidget()
        # ll = QVBoxLayout(lt2)
        # ll.setContentsMargins(0, 8, 0, 0)
        # ll.setSpacing(8)
        # self.links_list = QListWidget()
        # ll.addWidget(self.links_list)
        # link_btns = QHBoxLayout()
        # link_btns.setSpacing(6)
        # alb = QPushButton(self.lang.t('btn_add_link'))
        # alb.clicked.connect(self._add_link)
        # dlb = QPushButton(self.lang.t('btn_delete_link'))
        # dlb.clicked.connect(self._delete_link)
        # link_btns.addWidget(alb)
        # link_btns.addWidget(dlb)
        # ll.addLayout(link_btns)
        # self.tabs.addTab(lt2, self.lang.t('links'))
        # right.addWidget(self.tabs)
        # right.addWidget(make_sep())
        # latex_ops_frame = QFrame()
        # latex_ops_frame.setFrameShape(QFrame.StyledPanel)
        # latex_ops = QVBoxLayout(latex_ops_frame)
        # latex_ops.setSpacing(8)
        # insert_latex_btn = QPushButton("⬅ Insert LaTeX at Cursor")
        # insert_latex_btn.setMinimumHeight(32)
        # insert_latex_btn.clicked.connect(self._insert_latex_to_editor)
        # latex_ops.addWidget(insert_latex_btn)
        # gen_latex_btn = QPushButton("📄 Generate LaTeX")
        # gen_latex_btn.setMinimumHeight(32)
        # gen_latex_btn.clicked.connect(self._generate_latex_dialog)
        # latex_ops.addWidget(gen_latex_btn)
        # right.addWidget(latex_ops_frame)
        # splitter.addWidget(left_widget)
        # splitter.addWidget(right_widget)
        # splitter.setSizes([680, 800])
        # main_layout.addWidget(splitter)

    # def _create_toolbar(self):
        # toolbar = self.addToolBar("Main")
        # toolbar.setIconSize(QSize(14, 14))
        # toolbar.setMovable(False)

        # def act(icon_char, key, slot):
            # a = QAction(f"{icon_char}  {self.lang.t(key)}", self)
            # a.triggered.connect(slot)
            # return a

        # # NOTE: LaTeX actions omitted — they live in the bottom-right panel.
        # toolbar.addAction(act("＋", 'tb_add',    self._add_entry))
        # toolbar.addAction(act("✎",  'tb_edit',   self._edit_entry))
        # toolbar.addAction(act("✕",  'tb_delete', self._delete_entry))
        # toolbar.addSeparator()
        # toolbar.addAction(act("⌕",  'tb_search',       self._open_search))
        # toolbar.addAction(act("⊞",  'tb_manage_types', self._manage_types))
        # toolbar.addSeparator()
        # toolbar.addAction(act("⊙",  'tb_backup',  self._backup_db))
        # toolbar.addAction(act("↺",  'tb_restore', self._restore_db))
        # toolbar.addAction(act("⚙",  'tb_repair',  self._repair_db))
        # toolbar.addSeparator()
        # self.lang_combo = QComboBox()
        # self.lang_combo.setFixedWidth(130)
        # self.lang_combo.addItem("English", "en")
        # self.lang_combo.addItem("العربية", "ar")
        # idx = self.lang_combo.findData(self.lang.current_lang)
        # if idx >= 0:
            # self.lang_combo.setCurrentIndex(idx)
        # self.lang_combo.currentIndexChanged.connect(self._change_language)
        # toolbar.addWidget(self.lang_combo)

    # def _create_statusbar(self):
        # self.status = QStatusBar()
        # self.setStatusBar(self.status)
        # self.status.showMessage(self.lang.t('app_title'))

    # def load_entries(self):
        # entries = self.db.get_all_entries()
        # lang_code = self.lang.current_lang
        # for entry in entries:
            # if lang_code == 'ar':
                # entry['title']  = entry.get('title_ar', '')  or entry.get('title_en', '')
                # entry['domain'] = entry.get('domain_ar', '') or entry.get('domain_en', '')
            # else:
                # entry['title']  = entry.get('title_en', '')  or entry.get('title_ar', '')
                # entry['domain'] = entry.get('domain_en', '') or entry.get('domain_ar', '')
        # types   = self.db.get_unique_types_in_use()
        # domains = sorted(set(e.get('domain', '') for e in entries if e.get('domain', '')))
        # all_lbl = self.lang.t('all')
        # self.type_filter.blockSignals(True)
        # self.type_filter.clear()
        # self.type_filter.addItem(all_lbl)
        # self.type_filter.addItems(types)
        # self.type_filter.blockSignals(False)
        # self.domain_filter.blockSignals(True)
        # self.domain_filter.clear()
        # self.domain_filter.addItem(all_lbl)
        # self.domain_filter.addItems(domains)
        # self.domain_filter.blockSignals(False)
        # self.entries_table.load_data(entries)
        # self.count_label.setText(str(len(entries)))

    # def _on_entry_selected(self, row: int, col: int):
        # item = self.entries_table.item(row, 0)
        # if item:
            # eid = item.data(Qt.UserRole)
            # if eid:
                # self.current_entry_id = eid
                # self._display_entry()

    # def _display_entry(self):
        # if not self.current_entry_id:
            # return
        # entry = self.db.get_entry(self.current_entry_id)
        # if not entry:
            # return
        # lang_code = self.lang.current_lang
        # if lang_code == 'ar':
            # title     = entry.get('title_ar', '')     or entry.get('title_en', '')     or '—'
            # content   = entry.get('content_ar', '')   or entry.get('content_en', '')
            # author    = entry.get('author_ar', '')     or entry.get('author_en', '')     or '—'
            # domain    = entry.get('domain_ar', '')     or entry.get('domain_en', '')     or '—'
            # subdomain = entry.get('subdomain_ar', '') or entry.get('subdomain_en', '') or '—'
        # else:
            # title     = entry.get('title_en', '')     or entry.get('title_ar', '')     or '—'
            # content   = entry.get('content_en', '')   or entry.get('content_ar', '')
            # author    = entry.get('author_en', '')     or entry.get('author_ar', '')     or '—'
            # domain    = entry.get('domain_en', '')     or entry.get('domain_ar', '')     or '—'
            # subdomain = entry.get('subdomain_en', '') or entry.get('subdomain_ar', '') or '—'
        # etype = entry.get('type', '')
        # self.detail_header.setText(f"[{etype}]  {title}")
        # self.content_display.setText(content)
        # L = self.lang
        # self.meta_display.setText("\n".join([
            # f"ID          {entry.get('id', '')}",
            # f"{L.t('title')}       {title}",
            # f"{L.t('type')}        {etype}",
            # f"{L.t('author')}      {author}",
            # f"{L.t('domain')}      {domain}",
            # f"{L.t('subdomain')}   {subdomain}",
            # f"{L.t('doi')}         {entry.get('doi', '') or '—'}",
            # f"{L.t('created')}     {entry.get('date_created', '')}",
            # f"{L.t('modified')}    {entry.get('date_modified', '')}",
            # "",
            # f"{L.t('bibtex')}",
            # entry.get('bibtex', '') or '—',
            # "",
            # "─── Alternate Language ───",
            # f"EN: {entry.get('title_en', '') or '—'}",
            # f"AR: {entry.get('title_ar', '') or '—'}",
        # ]))
        # self._display_expls()
        # self._display_links()
        # self.status.showMessage(f"{etype}  ·  {title}  ·  {entry.get('id', '')}")

    # def _display_expls(self):
        # if not self.current_entry_id:
            # return
        # self.expls_list.clear()
        # self.expl_display.clear()
        # self.current_expl_id = None
        # expls = self.db.get_explanations_for_entry(self.current_entry_id)
        # if not expls:
            # ph = QListWidgetItem(self.lang.t('no_proofs'))
            # ph.setForeground(QColor(Qt.gray))
            # ph.setFlags(ph.flags() & ~Qt.ItemIsSelectable)
            # self.expls_list.addItem(ph)
            # return
        # for expl in expls:
            # t = expl.get('title', '') or 'Explanation'
            # a = expl.get('author', '') or ''
            # item = QListWidgetItem(f"{t}  —  {a}" if a else t)
            # item.setData(Qt.UserRole, expl.get('id'))
            # self.expls_list.addItem(item)

    # def _on_expl_selected(self, item: QListWidgetItem):
        # expl_id = item.data(Qt.UserRole)
        # if expl_id:
            # self.current_expl_id = expl_id
            # expl = self.db.get_explanation(expl_id)
            # if expl:
                # self.expl_display.setText(expl.get('content', ''))

    # def _display_links(self):
        # if not self.current_entry_id:
            # return
        # self.links_list.clear()
        # for link in self.db.get_links(self.current_entry_id):
            # tt = link.get('target_title', '') or '—'
            # ty = link.get('target_type', '')
            # item = QListWidgetItem(f"{link.get('relation', '')}  →  [{ty}] {tt}")
            # item.setData(Qt.UserRole, link.get('id'))
            # self.links_list.addItem(item)

    # def _quick_filter(self):
        # q = self.search_input.text()
        # entries = self.db.search(q) if q.strip() else self.db.get_all_entries()
        # self._filter_and_display(entries)

    # def _apply_filters(self):
        # self._filter_and_display(self.db.get_all_entries())

    # def _filter_and_display(self, entries):
        # all_lbl = self.lang.t('all')
        # t = self.type_filter.currentText()
        # d = self.domain_filter.currentText()
        # if t != all_lbl:
            # entries = [e for e in entries if e.get('type') == t]
        # if d != all_lbl:
            # entries = [e for e in entries if e.get('domain') == d]
        # self.entries_table.load_data(entries)
        # self.count_label.setText(str(len(entries)))

    # def _add_entry(self):
        # dlg = EntryDialog(self.db, lang=self.lang, parent=self)
        # if dlg.exec_():
            # self.load_entries()

    # def _edit_entry(self):
        # if not self.current_entry_id:
            # QMessageBox.warning(self, self.lang.t('error'), self.lang.t('entry_select'))
            # return
        # dlg = EntryDialog(self.db, self.current_entry_id, lang=self.lang, parent=self)
        # if dlg.exec_():
            # self.load_entries()
            # self._display_entry()

    # def _delete_entry(self):
        # if not self.current_entry_id:
            # QMessageBox.warning(self, self.lang.t('error'), self.lang.t('entry_select'))
            # return
        # reply = QMessageBox.question(self, self.lang.t('confirm'),
                                     # f"{self.lang.t('tb_delete')}?",
                                     # QMessageBox.Yes | QMessageBox.No)
        # if reply == QMessageBox.Yes:
            # try:
                # self.db.delete_entry(self.current_entry_id)
                # self.current_entry_id = None
                # self.detail_header.setText(self.lang.t('entry_details'))
                # for w in (self.content_display, self.meta_display, self.expl_display):
                    # w.clear()
                # self.expls_list.clear()
                # self.links_list.clear()
                # self.load_entries()
            # except Exception as e:
                # QMessageBox.critical(self, self.lang.t('error'), str(e))

    # def _add_expl(self):
        # if not self.current_entry_id:
            # QMessageBox.warning(self, self.lang.t('error'), self.lang.t('entry_select'))
            # return
        # dlg = ExplanationDialog(self.db, self.current_entry_id, lang=self.lang, parent=self)
        # if dlg.exec_():
            # self._display_expls()

    # def _edit_expl(self):
        # if not self.current_expl_id:
            # QMessageBox.warning(self, self.lang.t('error'), self.lang.t('proof_select'))
            # return
        # dlg = ExplanationDialog(self.db, self.current_entry_id, self.current_expl_id,
                                # lang=self.lang, parent=self)
        # if dlg.exec_():
            # self._display_expls()

    # def _delete_expl(self):
        # if not self.current_expl_id:
            # QMessageBox.warning(self, self.lang.t('error'), self.lang.t('proof_select'))
            # return
        # reply = QMessageBox.question(self, self.lang.t('confirm'),
                                     # f"{self.lang.t('delete_proof')}?",
                                     # QMessageBox.Yes | QMessageBox.No)
        # if reply == QMessageBox.Yes:
            # try:
                # self.db.delete_explanation(self.current_expl_id)
                # self.current_expl_id = None
                # self._display_expls()
            # except Exception as e:
                # QMessageBox.critical(self, self.lang.t('error'), str(e))

    # def _add_link(self):
        # if not self.current_entry_id:
            # QMessageBox.warning(self, self.lang.t('error'), self.lang.t('entry_select'))
            # return
        # dlg = LinkDialog(self.db, self.current_entry_id, lang=self.lang, parent=self)
        # if dlg.exec_():
            # self._display_links()

    # def _delete_link(self):
        # if not self.links_list.currentItem():
            # QMessageBox.warning(self, self.lang.t('error'), self.lang.t('link_select'))
            # return
        # link_id = self.links_list.currentItem().data(Qt.UserRole)
        # reply = QMessageBox.question(self, self.lang.t('confirm'),
                                     # f"{self.lang.t('btn_delete_link')}?",
                                     # QMessageBox.Yes | QMessageBox.No)
        # if reply == QMessageBox.Yes:
            # try:
                # self.db.delete_link(link_id)
                # self._display_links()
            # except Exception as e:
                # QMessageBox.critical(self, self.lang.t('error'), str(e))

    # def _insert_latex_to_editor(self):
        # if not self.current_entry_id:
            # QMessageBox.warning(self, self.lang.t('error'), self.lang.t('entry_select'))
            # return
        # latex = self.db.generate_latex(
            # self.current_entry_id, include_explanations=True, lang=self.lang.current_lang
        # )
        # if not latex:
            # QMessageBox.warning(self, self.lang.t('error'), self.lang.t('latex_error'))
            # return
        # try:
            # parent = self.parent()
            # main_window = None
            # while parent:
                # if hasattr(parent, 'editor_manager'):
                    # main_window = parent
                    # break
                # parent = parent.parent() if hasattr(parent, 'parent') else None
            # if main_window and hasattr(main_window, 'editor_manager'):
                # active_editor = main_window.editor_manager.get_active_editor()
                # if active_editor:
                    # cursor = active_editor.textCursor()
                    # cursor.insertText(latex)
                    # active_editor.setTextCursor(cursor)
                    # active_editor.setFocus()
                    # if hasattr(main_window.editor_manager, 'on_text_changed'):
                        # main_window.editor_manager.on_text_changed()
                    # QMessageBox.information(self, self.lang.t('success'),
                                            # "LaTeX code inserted into editor at cursor position!")
                    # return
            # QMessageBox.information(self, "Info",
                                    # "No editor found. Showing LaTeX in dialog instead.")
            # LaTeXDialog(latex, lang=self.lang, parent=self).exec_()
        # except Exception as e:
            # logger.error(f"Insert LaTeX error: {e}")
            # QMessageBox.critical(self, self.lang.t('error'), f"Failed to insert LaTeX:\n{str(e)}")

    # def _generate_latex_dialog(self):
        # if not self.current_entry_id:
            # QMessageBox.warning(self, self.lang.t('error'), self.lang.t('entry_select'))
            # return
        # latex = self.db.generate_latex(
            # self.current_entry_id, include_explanations=True, lang=self.lang.current_lang
        # )
        # if not latex:
            # QMessageBox.warning(self, self.lang.t('error'), self.lang.t('latex_error'))
            # return
        # LaTeXDialog(latex, lang=self.lang, parent=self).exec_()

    # def _open_search(self):
        # SearchDialog(self.db, lang=self.lang, parent=self).exec_()

    # def _manage_types(self):
        # ManageTypesDialog(self.db, lang=self.lang, parent=self).exec_()
        # self.load_entries()

    # def _backup_db(self):
        # path = self.db.recovery.create_backup()
        # if path:
            # self.status.showMessage(self.lang.t('db_backup_created').format(path=path))
            # QMessageBox.information(self, self.lang.t('success'),
                                    # self.lang.t('db_backup_created').format(path=path))
        # else:
            # QMessageBox.warning(self, self.lang.t('warning'), self.lang.t('error'))

    # def _restore_db(self):
        # fp, _ = QFileDialog.getOpenFileName(self, self.lang.t('tb_restore'),
                                            # "backups", "Database Files (*.db)")
        # if fp:
            # if self.db.recovery.restore_backup(fp):
                # self.db._init_connection()
                # self.load_entries()
                # QMessageBox.information(self, self.lang.t('success'), self.lang.t('db_restored'))
            # else:
                # QMessageBox.critical(self, self.lang.t('error'), self.lang.t('db_recovery_failed'))

    # def _repair_db(self):
        # if self.db.recovery.repair_database():
            # self.db._init_connection()
            # self.load_entries()
            # QMessageBox.information(self, self.lang.t('success'), self.lang.t('db_recovery_success'))
        # else:
            # QMessageBox.critical(self, self.lang.t('error'), self.lang.t('db_recovery_failed'))

    # def _change_language(self, index: int):
        # code = self.lang_combo.itemData(index)
        # if code and self.lang.set_language(code):
            # self._rebuild_ui()

    # def _rebuild_ui(self):
        # self.setWindowTitle(self.lang.t('app_title'))
        # for tb in self.findChildren(QToolBar):
            # self.removeToolBar(tb)
        # old = self.centralWidget()
        # if old:
            # old.deleteLater()
        # self._init_ui()
        # self.load_entries()
        # self.lang_combo.blockSignals(True)
        # idx = self.lang_combo.findData(self.lang.current_lang)
        # if idx >= 0:
            # self.lang_combo.setCurrentIndex(idx)
        # self.lang_combo.blockSignals(False)

    # def closeEvent(self, event):
        # try:
            # self.db.close()
        # except Exception as e:
            # logger.error(f"Close error: {e}")
        # event.accept()


# ============================================================================
# HELPERS
# ============================================================================
# def init_db(lang: Languages, db_path: str = None):
    # if db_path is None:
        # db_path = os.path.join(KnowledgeDB._get_config_directory(), "knowledge.db")
    # db = KnowledgeDB(db_path, lang)
    # db.init_schema()
    # db.close()


def add_knowledge_database_to_pdf_viewer(main_window):
    """Add the knowledge database widget tab to the PDF viewer."""
    lang = main_window.menu_language
    translations = main_window.translations
    tr = translations[lang]    
    try:
        if not hasattr(main_window, 'pdf_manager'):
            QMessageBox.warning(main_window, "Warning", "PDF manager not available!")
            return
        if not hasattr(main_window, 'layout_manager'):
            QMessageBox.warning(main_window, "Warning", "Layout manager not available!")
            return
        layout_manager = main_window.layout_manager
        pdf_manager    = main_window.pdf_manager
        if not hasattr(layout_manager, 'pdf_container') or layout_manager.pdf_container is None:
            layout_manager._recreate_pdf_container()
        if pdf_manager.pdf_layout_mode != "tabbed":
            QMessageBox.information(main_window, "Info",
                "Knowledge Database is only available in tabbed mode.")
            return
        if not hasattr(pdf_manager, 'pdf_tabs') or pdf_manager.pdf_tabs is None:
            pdf_manager.pdf_tabs = QTabWidget()
            pdf_manager.pdf_tabs.setTabsClosable(True)
            if hasattr(pdf_manager, 'close_pdf_tab'):
                pdf_manager.pdf_tabs.tabCloseRequested.connect(pdf_manager.close_pdf_tab)
            pdf_layout = layout_manager.pdf_container.layout()
            if pdf_layout:
                while pdf_layout.count():
                    item = pdf_layout.takeAt(0)
                    if item.widget():
                        item.widget().setParent(None)
                        item.widget().deleteLater()
                pdf_layout.addWidget(pdf_manager.pdf_tabs)
        tab_widget = pdf_manager.pdf_tabs
        if tab_widget is None:
            QMessageBox.critical(main_window, "Error", "Could not initialize PDF tabs")
            return
        for i in reversed(range(tab_widget.count())):
            if tab_widget.tabText(i) in ["Welcome", "No Pdfs", "No PDFs"]:
                tab_widget.removeTab(i)

        possible_labels = {
            tr["knowledge_database"] for tr in translations.values()
        }                
            
        for i in range(tab_widget.count()):
            if tab_widget.tabText(i) in possible_labels:
                tab_widget.setCurrentIndex(i)
                return
        lang_code = 'en'
        if hasattr(main_window, 'menu_language'):
            lang_code = main_window.menu_language
        config_dir = KnowledgeDB._get_config_directory()
        db_path    = os.path.join(config_dir, "knowledge.db")
        knowledge_widget = KnowledgeDBWidget(
            lang=lang_code,
            db_path=db_path,
            main_window=main_window
        )
        if not hasattr(main_window, '_knowledge_db_instances'):
            main_window._knowledge_db_instances = []
        main_window._knowledge_db_instances.append(knowledge_widget)
        tab_name = tr.get("knowledge_database", "Knowledge Database")
        tab_index = tab_widget.addTab(knowledge_widget, tab_name)
        tab_widget.tabBar().setTabData(tab_index, "knowledge_database")   
        
        # ── Sync language to Knowledge Database if open ──
        if hasattr(main_window, '_knowledge_db_instances'):
            for kb in main_window._knowledge_db_instances:
                if kb is not None and hasattr(kb, 'refresh_language'):
                    try:
                        kb.refresh_language()
                    except Exception as e:
                        print(f"Warning: Failed to sync KB language: {e}")                
        
        icon_path = "icons/database.svg"
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
            if not icon.isNull():
                tab_widget.setTabIcon(tab_index, icon)
        tab_widget.setCurrentIndex(tab_index)
        tab_widget.setTabsClosable(True)
        pdf_layout = layout_manager.pdf_container.layout()
        if pdf_layout and pdf_layout.indexOf(tab_widget) == -1:
            while pdf_layout.count():
                item = pdf_layout.takeAt(0)
                if item.widget() and item.widget() != tab_widget:
                    item.widget().setParent(None)
            pdf_layout.addWidget(tab_widget)
        tab_widget.show()
        tab_widget.setVisible(True)
        knowledge_widget.show()
        layout_manager.pdf_container.update()
        #print(f"✅ Knowledge Database tab added at index {tab_index}")
        #print(f"✅ Language: {lang_code}, Database: {db_path}")
    except Exception as e:
        QMessageBox.critical(main_window, "Error",
                             f"Failed to add knowledge database:\n{str(e)}")
        import traceback
        traceback.print_exc()