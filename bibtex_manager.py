# bibtex_manager.py
import sys
import os
import requests
import json
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFileDialog,
    QTableWidget, QTableWidgetItem, QFormLayout,
    QLineEdit, QVBoxLayout, QHBoxLayout, QPushButton,
    QMessageBox, QSplitter, QComboBox, QToolBar, QInputDialog,
    QProgressDialog, QTabWidget,  QSizePolicy, QScrollArea
)
from PyQt5.QtGui import QColor, QIcon
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import bibtexparser
from bibtexparser.bwriter import BibTexWriter
from bibtexparser.bibdatabase import BibDatabase
# =========================================================
# Entry templates (used when adding new entries)
# =========================================================
ENTRY_TEMPLATES = {
    "article": {
        "author": "",
        "title": "",
        "journal": "",
        "year": "",
        "volume": "",
        "number": "",
        "pages": ""
    },
    "book": {
        "author": "",
        "title": "",
        "publisher": "",
        "year": "",
        "address": ""
    },
    "online": {
        "author": "",
        "title": "",
        "url": "",
        "urldate": ""
    },
}
def create_entry(entry_type):
    fields = ENTRY_TEMPLATES.get(entry_type, {})
    return BibEntry(entry_type=entry_type, key="newkey", fields=dict(fields))
def add_entry(self):
    entry_type = self.editor.type_box.currentText()
    entry = create_entry(entry_type)
    self.db.entries.append(entry)
    self.db.modified = True
    self.table.populate(self.db.entries)
# =========================================================
# BibLaTeX entry type registry
# =========================================================
ENTRY_TYPES = {
    "article": "Article in Journal",
    "periodical": "Complete Issue of a Periodical",
    "suppperiodical": "Supplemental Material in a Periodical",
    "book": "Book",
    "mvbook": "Multi-volume Book",
    "inbook": "Part of a Book With Its Own Title",
    "bookinbook": "Book in Book",
    "suppbook": "Supplemental Material in a Book",
    "booklet": "Booklet",
    "collection": "Single-volume Collection",
    "mvcollection": "Multi-volume Collection",
    "incollection": "Article in a Collection",
    "suppcollection": "Supplemental Material in a Collection",
    "proceedings": "Conference Proceedings",
    "mvproceedings": "Multi-volume Proceedings Entry",
    "inproceedings": "Article in Conference Proceedings",
    "reference": "Reference",
    "mvreference": "Multi-volume Reference Entry",
    "inreference": "Article in a Reference",
    "report": "Report",
    "techreport": "Technical Report",
    "manual": "Manual",
    "standard": "Standard",
    "phdthesis": "PhD Thesis",
    "mastersthesis": "Master's Thesis",
    "thesis": "Thesis",
    "unpublished": "Unpublished",
    "online": "Online Resource",
    "preprint": "Preprint",
    "dataset": "Dataset",
    "software": "Software",
    "presentation": "Presentation",
    "patent": "Patent",
    "case": "Legal Case",
    "map": "Map",
    "artwork": "Artwork",
    "audio": "Audio Recording",
    "video": "Video Recording",
    "misc": "Miscellaneous",
}
# =========================================================
# BibTeX schema (required / optional fields)
# =========================================================
BIBTEX_SCHEMA = {
    "article": {
        "required": ["author", "title", "journal", "year"],
        "optional": ["volume", "number", "pages", "month", "doi", "url", "note", "issn"]
    },
    "book": {
        "required": ["author", "title", "publisher", "year"],
        "optional": ["editor", "volume", "number", "series", "address", "edition", "month", "note", "isbn", "url"]
    },
    "booklet": {
        "required": ["title"],
        "optional": ["author", "howpublished", "address", "month", "year", "note", "url"]
    },
    "inbook": {
        "required": ["author", "title", "chapter", "pages", "publisher", "year"],
        "optional": ["editor", "volume", "number", "series", "type", "address", "edition", "month", "note", "isbn"]
    },
    "incollection": {
        "required": ["author", "title", "booktitle", "publisher", "year"],
        "optional": ["editor", "volume", "number", "series", "type", "chapter", "pages", "address", "edition", "month", "note"]
    },
    "inproceedings": {
        "required": ["author", "title", "booktitle", "year"],
        "optional": ["editor", "volume", "number", "series", "pages", "address", "month", "organization", "publisher", "note", "doi", "url"]
    },
    "conference": {
        "required": ["author", "title", "booktitle", "year"],
        "optional": ["editor", "volume", "number", "series", "pages", "address", "month", "organization", "publisher", "note"]
    },
    "manual": {
        "required": ["title"],
        "optional": ["author", "organization", "address", "edition", "month", "year", "note", "url"]
    },
    "mastersthesis": {
        "required": ["author", "title", "school", "year"],
        "optional": ["type", "address", "month", "note", "url"]
    },
    "phdthesis": {
        "required": ["author", "title", "school", "year"],
        "optional": ["type", "address", "month", "note", "url"]
    },
    "proceedings": {
        "required": ["title", "year"],
        "optional": ["editor", "volume", "number", "series", "address", "month", "publisher", "organization", "note", "isbn"]
    },
    "techreport": {
        "required": ["author", "title", "institution", "year"],
        "optional": ["type", "number", "address", "month", "note", "url"]
    },
    "unpublished": {
        "required": ["author", "title", "note"],
        "optional": ["month", "year", "url"]
    },
    "misc": {
        "required": [],
        "optional": ["author", "title", "howpublished", "year", "month", "note", "url"]
    },
    "online": {
        "required": ["title", "url"],
        "optional": ["author", "organization", "year", "month", "urldate", "note"]
    },
    "patent": {
        "required": ["author", "title", "number", "year"],
        "optional": ["holder", "type", "address", "month", "note", "url"]
    },
    "periodical": {
        "required": ["title", "year"],
        "optional": ["editor", "volume", "number", "series", "month", "organization", "note", "issn"]
    },
    "software": {
        "required": ["title"],
        "optional": ["author", "organization", "version", "year", "month", "url", "note"]
    },
    "dataset": {
        "required": ["author", "title", "year"],
        "optional": ["version", "publisher", "url", "doi", "note"]
    },
    "standard": {
        "required": ["title", "organization", "number"],
        "optional": ["author", "year", "month", "url", "note"]
    },
    # BibLaTeX-specific types
    "mvbook": {
        "required": ["author", "title", "year"],
        "optional": ["editor", "publisher", "volumes", "series", "address", "edition", "month", "note", "isbn"]
    },
    "bookinbook": {
        "required": ["author", "title", "booktitle", "year"],
        "optional": ["editor", "publisher", "volume", "pages", "address", "edition", "month", "note"]
    },
    "suppbook": {
        "required": ["author", "title", "booktitle", "year"],
        "optional": ["editor", "publisher", "volume", "pages", "address", "month", "note"]
    },
    "collection": {
        "required": ["editor", "title", "year"],
        "optional": ["publisher", "volume", "series", "address", "edition", "month", "note", "isbn"]
    },
    "mvcollection": {
        "required": ["editor", "title", "year"],
        "optional": ["publisher", "volumes", "series", "address", "edition", "month", "note"]
    },
    "suppcollection": {
        "required": ["author", "title", "booktitle", "year"],
        "optional": ["editor", "publisher", "volume", "pages", "address", "month", "note"]
    },
    "mvproceedings": {
        "required": ["title", "year"],
        "optional": ["editor", "volumes", "publisher", "organization", "address", "month", "note"]
    },
    "reference": {
        "required": ["editor", "title", "year"],
        "optional": ["publisher", "volume", "series", "address", "edition", "month", "note"]
    },
    "mvreference": {
        "required": ["editor", "title", "year"],
        "optional": ["publisher", "volumes", "series", "address", "edition", "month", "note"]
    },
    "inreference": {
        "required": ["author", "title", "booktitle", "year"],
        "optional": ["editor", "publisher", "volume", "pages", "address", "edition", "month", "note"]
    },
    "report": {
        "required": ["author", "title", "type", "institution", "year"],
        "optional": ["number", "address", "month", "note", "url"]
    },
    "thesis": {
        "required": ["author", "title", "type", "institution", "year"],
        "optional": ["address", "month", "note", "url"]
    },
    "preprint": {
        "required": ["author", "title", "year"],
        "optional": ["eprinttype", "eprint", "eprintclass", "url", "doi", "note"]
    },
    "presentation": {
        "required": ["author", "title", "year"],
        "optional": ["event", "venue", "address", "month", "url", "note"]
    },
    "artwork": {
        "required": ["author", "title"],
        "optional": ["type", "year", "location", "note", "url"]
    },
    "audio": {
        "required": ["author", "title", "year"],
        "optional": ["type", "publisher", "url", "note"]
    },
    "video": {
        "required": ["author", "title", "year"],
        "optional": ["type", "publisher", "url", "note"]
    },
    "map": {
        "required": ["title"],
        "optional": ["author", "publisher", "year", "address", "note", "url"]
    },
    "suppperiodical": {
        "required": ["author", "title", "journaltitle", "year"],
        "optional": ["editor", "volume", "number", "pages", "month", "note"]
    },
    "case": {
        "required": ["title", "number", "court", "year"],
        "optional": ["volume", "reporter", "pages", "month", "note", "url"]
    }
}
DEFAULT_SCHEMA = {
    "required": [],
    "optional": [
        "author", "editor", "title", "year", "month", "note",
        "url", "doi", "publisher", "organization", "institution",
        "journal", "booktitle", "volume", "number", "pages",
        "address", "edition", "series", "howpublished"
    ]
}
# =========================================================
# Data model
# =========================================================
class BibEntry:
    def __init__(self, entry_type="article", key="", fields=None):
        self.entry_type = entry_type
        self.key = key
        self.fields = fields or {}
    def get(self, field):
        return self.fields.get(field, "")
    def set(self, field, value):
        self.fields[field] = value
# =========================================================
# Validation helpers
# =========================================================
def validate_entry(entry: BibEntry):
    schema = BIBTEX_SCHEMA.get(entry.entry_type, DEFAULT_SCHEMA)
    missing = []
    for field in schema["required"]:
        if not entry.fields.get(field, "").strip():
            missing.append(field)
    return missing
def find_duplicate_keys(entries):
    """
    Returns a dictionary: key -> list of entries with that key
    """
    key_map = {}
    for entry in entries:
        key = entry.key.strip()
        if key:
            key_map.setdefault(key, []).append(entry)
    # Keep only duplicates
    duplicates = {k: v for k, v in key_map.items() if len(v) > 1}
    return duplicates
# =========================================================
# BibTeX database logic
# =========================================================
class BibDatabaseModel:
    def __init__(self):
        self.entries = []
        self.file_path = None
        self.modified = False
        # Undo/Redo stacks
        self.undo_stack = []
        self.redo_stack = []
        self.max_history = 50  # Maximum number of undo steps
    def save_state(self):
        """Save current state for undo."""
        # Create a deep copy of current entries
        state = []
        for entry in self.entries:
            state.append(BibEntry(
                entry_type=entry.entry_type,
                key=entry.key,
                fields=dict(entry.fields)
            ))
        self.undo_stack.append(state)
        # Limit stack size
        if len(self.undo_stack) > self.max_history:
            self.undo_stack.pop(0)
        # Clear redo stack when new action is performed
        self.redo_stack.clear()
    def undo(self):
        """Undo last action."""
        if not self.undo_stack:
            return False
        # Save current state to redo stack
        current_state = []
        for entry in self.entries:
            current_state.append(BibEntry(
                entry_type=entry.entry_type,
                key=entry.key,
                fields=dict(entry.fields)
            ))
        self.redo_stack.append(current_state)
        # Restore previous state
        self.entries = self.undo_stack.pop()
        self.modified = True
        return True
    def redo(self):
        """Redo last undone action."""
        if not self.redo_stack:
            return False
        # Save current state to undo stack
        current_state = []
        for entry in self.entries:
            current_state.append(BibEntry(
                entry_type=entry.entry_type,
                key=entry.key,
                fields=dict(entry.fields)
            ))
        self.undo_stack.append(current_state)
        # Restore redo state
        self.entries = self.redo_stack.pop()
        self.modified = True
        return True
    def can_undo(self):
        """Check if undo is available."""
        return len(self.undo_stack) > 0
    def can_redo(self):
        """Check if redo is available."""
        return len(self.redo_stack) > 0
    def load(self, path):
        with open(path, encoding="utf-8") as f:
            db = bibtexparser.load(f)
        self.entries.clear()
        for e in db.entries:
            entry = BibEntry(
                entry_type=e.get("ENTRYTYPE", "article"),
                key=e.get("ID", ""),
                fields={k: v for k, v in e.items()
                        if k not in ("ENTRYTYPE", "ID")}
            )
            self.entries.append(entry)
        self.file_path = path
        self.modified = False
        # Clear undo/redo on load
        self.undo_stack.clear()
        self.redo_stack.clear()
    def save(self, path=None):
        db = BibDatabase()
        db.entries = []
        for e in self.entries:
            entry = {
                "ENTRYTYPE": e.entry_type,
                "ID": e.key,
                **e.fields
            }
            db.entries.append(entry)
        writer = BibTexWriter()
        writer.indent = "  "
        #writer.order_entries_by = ("ID",)
        path = path or self.file_path
        with open(path, "w", encoding="utf-8") as f:
            f.write(writer.write(db))
        self.file_path = path
        self.modified = False
# =========================================================
# DOI Fetch Worker Thread
# =========================================================
class DOIFetchWorker(QThread):
    """Worker thread for fetching DOI metadata."""
    finished = pyqtSignal(object)  # Emits metadata or None
    progress = pyqtSignal(int)  # Progress percentage
    def __init__(self, doi):
        super().__init__()
        self.doi = doi
    def run(self):
        """Fetch metadata in background."""
        self.progress.emit(20)
        metadata = fetch_metadata_from_doi(self.doi)
        self.progress.emit(100)
        self.finished.emit(metadata)
# =========================================================
# Bibliography style formatting
# =========================================================
def format_author_list(authors, style):
    """Format author list according to style."""
    if not authors:
        return ""
    author_list = authors.split(" and ")
    # Abbreviated styles
    if style in ["abbrv.bst", "abbrvnat.bst", "amsalpha.bst"]:
        # Abbreviated: "Last, F. and Last, F."
        abbrev_authors = []
        for author in author_list:
            if "," in author:
                parts = author.split(",")
                last = parts[0].strip()
                first = parts[1].strip() if len(parts) > 1 else ""
                if first:
                    initials = ". ".join([n[0] for n in first.split()]) + "."
                    abbrev_authors.append(f"{last}, {initials}")
                else:
                    abbrev_authors.append(last)
            else:
                abbrev_authors.append(author)
        return " and ".join(abbrev_authors)
    # Alpha/Harvard styles
    elif style in ["alpha.bst", "harvard.bst", "amsalpha.bst"]:
        return " and ".join(author_list)
    # APA/Chicago/Nature styles (author-year)
    elif style in ["apalike.bst", "apa.bst", "chicago.bst", "nature.bst", "abbrvnat.bst", "plainnat.bst", "unsrtnat.bst"]:
        if len(author_list) == 1:
            return author_list[0]
        elif len(author_list) == 2:
            return f"{author_list[0]} and {author_list[1]}"
        else:
            return ", ".join(author_list[:-1]) + f", and {author_list[-1]}"
    # Standard full name styles
    else:  # plain, unsrt, siam, acm, ieeetr, IEEEtran, science, amsplain, etc.
        return " and ".join(author_list)
    return " and ".join(author_list)
def generate_citation_label(entry, style, index):
    """Generate citation label based on style."""
    # Alpha-style labels (e.g., [Knu02])
    if style in ["alpha.bst", "amsalpha.bst"]:
        author = entry.get("author") or "Anon"
        year = entry.get("year") or "00"
        # Get first author's last name
        first_author = author.split(" and ")[0]
        if "," in first_author:
            last_name = first_author.split(",")[0].strip()
        else:
            last_name = first_author.split()[-1]
        # Take first 3 letters of last name
        label = last_name[:3] + year[-2:]
        return label
    # Author-year styles
    elif style in ["apalike.bst", "apa.bst", "chicago.bst", "harvard.bst", "nature.bst", 
                   "abbrvnat.bst", "plainnat.bst", "unsrtnat.bst"]:
        author = entry.get("author") or "Anonymous"
        year = entry.get("year") or "n.d."
        first_author = author.split(" and ")[0]
        if "," in first_author:
            last_name = first_author.split(",")[0].strip()
        else:
            last_name = first_author.split()[-1]
        # Different formats for different styles
        if style in ["nature.bst", "science.bst"]:
            return str(index)  # Nature/Science use numbers
        else:
            return f"{last_name}, {year}"
    # Numbered styles (default)
    else:
        return str(index)
def format_entry_to_bibtex_style(entry, style, index):
    """Format a single entry according to bibliography style."""
    label = generate_citation_label(entry, style, index)
    # Get common fields
    author = format_author_list(entry.get("author") or "", style)
    editor = format_author_list(entry.get("editor") or "", style)
    title = entry.get("title") or ""
    year = entry.get("year") or ""
    # Determine style category
    is_author_year = style in ["apalike.bst", "apa.bst", "chicago.bst", "harvard.bst", 
                                "abbrvnat.bst", "plainnat.bst", "unsrtnat.bst"]
    is_ieee = style in ["ieeetr.bst", "IEEEtran.bst", "acm.bst"]
    is_nature = style in ["nature.bst", "science.bst"]
    # Format based on entry type
    if entry.entry_type == "article":
        journal = entry.get("journal") or ""
        volume = entry.get("volume") or ""
        number = entry.get("number") or ""
        pages = entry.get("pages") or ""
        doi = entry.get("doi") or ""
        if is_author_year:
            result = f"{author}. ({year}). {title}. \\emph{{{journal}}}"
            if volume:
                result += f", \\textbf{{{volume}}}"
            if number:
                result += f"({number})"
            if pages:
                result += f", {pages}"
        elif is_ieee:
            result = f"{author}, \"{title},\" \\emph{{{journal}}}"
            if volume:
                result += f", vol. {volume}"
            if number:
                result += f", no. {number}"
            if pages:
                result += f", pp. {pages}"
            if year:
                result += f", {year}"
        elif is_nature:
            result = f"{author}. {title}. \\emph{{{journal}}} \\textbf{{{volume}}}"
            if pages:
                result += f", {pages}"
            result += f" ({year})"
        else:
            result = f"{author}. {title}. \\emph{{{journal}}}"
            if volume:
                result += f", {volume}"
            if number:
                result += f"({number})"
            if pages:
                result += f":{pages}"
            if year:
                result += f", {year}"
    elif entry.entry_type in ["book", "mvbook"]:
        publisher = entry.get("publisher") or ""
        address = entry.get("address") or ""
        edition = entry.get("edition") or ""
        if is_author_year:
            result = f"{author}. ({year}). \\emph{{{title}}}."
            if edition:
                result += f" {edition} ed."
            if publisher:
                result += f" {publisher}"
        elif is_ieee:
            result = f"{author}, \\emph{{{title}}}."
            if edition:
                result += f" {edition} ed."
            if publisher:
                result += f" {publisher}"
            if year:
                result += f", {year}"
        else:
            result = f"{author}. \\emph{{{title}}}."
            if edition:
                result += f" {edition} edition."
            if publisher:
                result += f" {publisher}"
            if year:
                result += f", {year}"
    elif entry.entry_type in ["inproceedings", "conference"]:
        booktitle = entry.get("booktitle") or ""
        pages = entry.get("pages") or ""
        publisher = entry.get("publisher") or ""
        address = entry.get("address") or ""
        if is_author_year:
            result = f"{author}. ({year}). {title}. In "
            if editor:
                result += f"{editor} (Ed.), "
            result += f"\\emph{{{booktitle}}}"
            if pages:
                result += f" (pp. {pages})"
            if publisher:
                result += f". {publisher}"
        elif is_ieee:
            result = f"{author}, \"{title},\" in \\emph{{{booktitle}}}"
            if year:
                result += f", {year}"
            if pages:
                result += f", pp. {pages}"
        else:
            result = f"{author}. {title}. In \\emph{{{booktitle}}}"
            if pages:
                result += f", pages {pages}"
            if year:
                result += f", {year}"
    elif entry.entry_type in ["phdthesis", "mastersthesis", "thesis"]:
        school = entry.get("school") or entry.get("institution") or ""
        thesis_type = entry.get("type") or ("PhD thesis" if entry.entry_type == "phdthesis" else "Master's thesis")
        if is_author_year:
            result = f"{author}. ({year}). \\emph{{{title}}}. {thesis_type}, {school}"
        else:
            result = f"{author}. \\emph{{{title}}}. {thesis_type}, {school}, {year}"
    elif entry.entry_type == "techreport":
        institution = entry.get("institution") or ""
        number = entry.get("number") or ""
        result = f"{author}. {title}. Technical Report"
        if number:
            result += f" {number}"
        result += f", {institution}"
        if year:
            result += f", {year}"
    elif entry.entry_type in ["incollection", "inbook"]:
        booktitle = entry.get("booktitle") or ""
        publisher = entry.get("publisher") or ""
        pages = entry.get("pages") or ""
        chapter = entry.get("chapter") or ""
        if is_author_year:
            result = f"{author}. ({year}). {title}. In "
            if editor:
                result += f"{editor} (Ed.), "
            result += f"\\emph{{{booktitle}}}"
            if chapter:
                result += f", chapter {chapter}"
            if pages:
                result += f", pp. {pages}"
            if publisher:
                result += f". {publisher}"
        else:
            result = f"{author}. {title}. In "
            if editor:
                result += f"{editor}, editor, "
            result += f"\\emph{{{booktitle}}}"
            if pages:
                result += f", pages {pages}"
            if publisher:
                result += f". {publisher}"
            if year:
                result += f", {year}"
    elif entry.entry_type == "manual":
        organization = entry.get("organization") or ""
        edition = entry.get("edition") or ""
        result = f"\\emph{{{title}}}."
        if author:
            result = f"{author}. " + result
        if edition:
            result += f" {edition} edition."
        if organization:
            result += f" {organization}"
        if year:
            result += f", {year}"
    elif entry.entry_type == "unpublished":
        note = entry.get("note") or ""
        result = f"{author}. {title}."
        if note:
            result += f" {note}"
        if year:
            result += f", {year}"
    elif entry.entry_type in ["online", "software"]:
        url = entry.get("url") or ""
        urldate = entry.get("urldate") or ""
        if is_author_year and year:
            result = f"{author}. ({year}). {title}."
        else:
            result = f"{author}. {title}."
            if year:
                result += f" {year}"
        if url:
            result += f" \\url{{{url}}}"
        if urldate:
            result += f" (accessed {urldate})"
    else:  # misc, dataset, and other types
        howpublished = entry.get("howpublished") or ""
        url = entry.get("url") or ""
        if is_author_year and year:
            result = f"{author}. ({year}). {title}."
        else:
            result = f"{author}. {title}."
            if year:
                result += f" {year}"
        if howpublished:
            result += f" {howpublished}"
        if url:
            result += f" \\url{{{url}}}"
    # Add DOI for science journals
    doi = entry.get("doi") or ""
    if doi and style in ["nature.bst", "science.bst", "springer.bst", "elsevier.bst"]:
        result += f" doi:{doi}"
    result += "."
    # Format with label
    if is_author_year:
        return f"\\bibitem[{label}]{{{entry.key}}}\n{result}\n"
    else:
        return f"\\bibitem{{{entry.key}}}\n{result}\n"
def convert_to_thebibliography(entries, style):
    """Convert entries to LaTeX thebibliography format."""
    # Sort entries based on style
    if style in ["unsrt.bst", "unsrtnat.bst", "ieeetr.bst", "IEEEtran.bst"]:
        # Keep original order (order of appearance)
        sorted_entries = entries
    elif style in ["alpha.bst", "amsalpha.bst"]:
        # Sort by label
        def alpha_key(e):
            author = e.get("author") or "ZZZ"
            year = e.get("year") or "9999"
            first_author = author.split(" and ")[0]
            if "," in first_author:
                last_name = first_author.split(",")[0].strip()
            else:
                last_name = first_author.split()[-1]
            return last_name.lower() + year
        sorted_entries = sorted(entries, key=alpha_key)
    elif style in ["nature.bst", "science.bst"]:
        # Sort by order of appearance (like unsrt)
        sorted_entries = entries
    else:
        # Sort alphabetically by author (default for most styles)
        def author_key(e):
            author = e.get("author") or "ZZZ"
            return author.lower()
        sorted_entries = sorted(entries, key=author_key)
    # Generate bibliography
    output = "\\begin{thebibliography}{99}\n\n"
    for i, entry in enumerate(sorted_entries, 1):
        output += format_entry_to_bibtex_style(entry, style, i)
        output += "\n"
    output += "\\end{thebibliography}"
    return output
# =========================================================
# Utility functions
# =========================================================
def fetch_metadata_from_doi(doi):
    """
    Fetch bibliographic metadata from a DOI using CrossRef API.
    Returns a dictionary with fields suitable for BibEntry, or None on failure.
    """
    doi = doi.strip()
    if not doi:
        return None
    # Clean DOI (remove URL prefix if present)
    if doi.startswith("http"):
        doi = doi.split("doi.org/")[-1]
    try:
        # Use CrossRef API
        url = f"https://api.crossref.org/works/{doi}"
        headers = {"Accept": "application/json"}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None
        data = response.json()
        message = data.get("message", {})
        # Extract fields
        fields = {}
        # Authors
        authors = message.get("author", [])
        if authors:
            author_list = []
            for author in authors:
                given = author.get("given", "")
                family = author.get("family", "")
                if family:
                    author_list.append(f"{family}, {given}" if given else family)
            fields["author"] = " and ".join(author_list)
        # Title
        titles = message.get("title", [])
        if titles:
            fields["title"] = titles[0]
        # Journal/Container
        container = message.get("container-title", [])
        if container:
            fields["journal"] = container[0]
        # Year
        published = message.get("published-print") or message.get("published-online") or message.get("created")
        if published and "date-parts" in published:
            date_parts = published["date-parts"][0]
            if date_parts:
                fields["year"] = str(date_parts[0])
        # Volume, Issue, Pages
        if "volume" in message:
            fields["volume"] = str(message["volume"])
        if "issue" in message:
            fields["number"] = str(message["issue"])
        if "page" in message:
            fields["pages"] = message["page"]
        # DOI
        fields["doi"] = doi
        # URL
        if "URL" in message:
            fields["url"] = message["URL"]
        # Determine entry type
        pub_type = message.get("type", "article")
        if "journal" in pub_type or "article" in pub_type:
            entry_type = "article"
        elif "book" in pub_type:
            entry_type = "book"
        elif "proceedings" in pub_type:
            entry_type = "inproceedings"
        else:
            entry_type = "misc"
        return {"entry_type": entry_type, "fields": fields}
    except Exception as e:
        print(f"Error fetching DOI metadata: {e}")
        return None
def generate_citation_key(author, year, title):
    if not author or not year:
        return "key"
    last = author.split(",")[0].split()[-1]
    first_word = title.split()[0] if title else ""
    return f"{last}{year}{first_word}".lower()
# =========================================================
# UI widgets
# =========================================================
class EntryTable(QTableWidget):
    def __init__(self):
        super().__init__(0, 5)
        self.setHorizontalHeaderLabels(["⚠", "Key", "Author", "Title", "Year"])
        self.setSelectionBehavior(self.SelectRows)
        self.setEditTriggers(self.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.setSortingEnabled(True)
        self.visible_entries = []
        # Set warning column to minimal width
        self.setColumnWidth(0, 30)  # Narrow width for warning icon
        self.horizontalHeader().setStretchLastSection(True)
    # -----------------------
    # Helper to get first author's last name
    # -----------------------
    @staticmethod
    def first_author(entry):
        author = entry.get("author") or ""
        if not author:
            return ""
        parts = author.split(" and ")
        first_author = parts[0]
        if "," in first_author:
            return first_author.split(",")[0].strip()
        return first_author.strip()
    # -----------------------
    # Populate table
    # -----------------------
    def populate(self, entries, sort_by="author"):
        # Disable sorting while populating to prevent display issues
        self.setSortingEnabled(False)
        self.setRowCount(0)
        self.visible_entries = []
        # -----------------------
        # Sort entries safely
        # -----------------------
        if sort_by == "author":
            def author_key(e):
                a = e.get("author") or ""
                return a.lower() if a else "zzz"  # missing authors go last
            sorted_entries = sorted(entries, key=author_key)
        elif sort_by == "year":
            def year_key(e):
                y = e.get("year") or ""
                try:
                    return int(y)
                except:
                    return -1  # missing year goes first or last
            sorted_entries = sorted(entries, key=year_key, reverse=True)
        else:
            sorted_entries = list(entries)  # no sort
        # -----------------------
        # Detect duplicates
        # -----------------------
        key_map = {}
        for entry in sorted_entries:
            k = entry.key.strip() if entry.key else ""
            if k:
                key_map.setdefault(k, []).append(entry)
        duplicates = {k: v for k, v in key_map.items() if len(v) > 1}
        # -----------------------
        # Populate table rows
        # -----------------------
        for entry in sorted_entries:
            row = self.rowCount()
            self.insertRow(row)
            self.visible_entries.append(entry)
            missing = validate_entry(entry)
            dup = entry.key.strip() in duplicates if entry.key else False
            # Warning column
            if missing and dup:
                warn_text = "⚠"
                color = QColor("red")
                tooltip = f"Missing fields: {', '.join(missing)}\nDuplicate key!"
            elif missing:
                warn_text = "⚠"
                color = QColor("red")
                tooltip = "Missing fields: " + ", ".join(missing)
            elif dup:
                warn_text = "⚠"
                color = QColor("darkorange")
                tooltip = "Duplicate key!"
            else:
                warn_text = "✓"
                color = QColor("darkgreen")
                tooltip = "Valid"
            warn_item = QTableWidgetItem(warn_text)
            warn_item.setTextAlignment(Qt.AlignCenter)
            warn_item.setForeground(color)
            warn_item.setToolTip(tooltip)
            self.setItem(row, 0, warn_item)
            # Columns: Key, Author, Title, Year — always safe
            self.setItem(row, 1, QTableWidgetItem(entry.key or ""))
            self.setItem(row, 2, QTableWidgetItem(entry.get("author") or ""))
            self.setItem(row, 3, QTableWidgetItem(entry.get("title") or ""))
            self.setItem(row, 4, QTableWidgetItem(entry.get("year") or ""))
        # Re-enable sorting after all items are added
        self.setSortingEnabled(True)
class EntryEditor(QWidget):
    def __init__(self):
        super().__init__()
        self.current_entry = None
        self.show_optional = False
        self.field_widgets = {}
        self.type_box = QComboBox()
        self.type_box.addItems(sorted(ENTRY_TYPES.keys()))
        self.type_box.setToolTip("BibLaTeX entry type")
        self.type_box.currentTextChanged.connect(self.rebuild_form)
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("Citation key (e.g., Einstein1905)")
        self.key_edit.textChanged.connect(self.validate)
        self.form_layout = QFormLayout()
        self.form_layout.addRow("Type", self.type_box)
        self.form_layout.addRow("Key", self.key_edit)
        self.toggle_optional_btn = QPushButton("Show optional fields")
        self.toggle_optional_btn.clicked.connect(self.toggle_optional_fields)
        layout = QVBoxLayout()
        layout.addLayout(self.form_layout)
        layout.addWidget(self.toggle_optional_btn)
        layout.addStretch()
        self.setLayout(layout)
        self.rebuild_form()
    # ---------------- UI building ----------------
    def rebuild_form(self):
        # Remove all rows except the first one ("Key")
        while self.form_layout.rowCount() > 2:
            self.form_layout.removeRow(2)
        self.field_widgets.clear()
        entry_type = self.type_box.currentText()
        schema = BIBTEX_SCHEMA.get(entry_type, DEFAULT_SCHEMA)
        def add_field(name, required=False):
            edit = QLineEdit()
            if required:
                edit.setPlaceholderText("required")
            edit.textChanged.connect(self.validate)
            self.form_layout.addRow(name.capitalize(), edit)
            self.field_widgets[name] = edit
        # Required fields
        for field in schema["required"]:
            add_field(field, required=True)
        # Optional fields
        if self.show_optional:
            for field in schema["optional"]:
                add_field(field)
        # Reload data
        if self.current_entry:
            for name, widget in self.field_widgets.items():
                widget.setText(self.current_entry.get(name))
        self.validate()
    def toggle_optional_fields(self):
        self.show_optional = not self.show_optional
        self.toggle_optional_btn.setText(
            "Hide optional fields" if self.show_optional else "Show optional fields"
        )
        self.rebuild_form()
    # ---------------- Data sync ----------------
    def load_entry(self, entry: BibEntry):
        self.current_entry = entry
        self.type_box.setCurrentText(entry.entry_type)
        self.key_edit.setText(entry.key)
        for name, widget in self.field_widgets.items():
            widget.setText(entry.get(name))
        self.validate()
    def apply_to_entry(self, entry: BibEntry):
        old_key = entry.key
        entry.entry_type = self.type_box.currentText()
        entry.key = self.key_edit.text().strip()
        for name, widget in self.field_widgets.items():
            value = widget.text().strip()
            if value:
                entry.fields[name] = value
            elif name in entry.fields:
                del entry.fields[name]
    # ---------------- Validation ----------------
    def validate(self):
        if not self.current_entry:
            return True
        schema = BIBTEX_SCHEMA.get(self.type_box.currentText(), DEFAULT_SCHEMA)
        valid = True
        for field, widget in self.field_widgets.items():
            if field in schema["required"] and not widget.text().strip():
                widget.setStyleSheet("border: 2px solid red;")
                valid = False
            else:
                widget.setStyleSheet("")
        return valid
# =========================================================
# Application entry point
# =========================================================
# =========================================================
# Embeddable tab widget (QWidget version of BibTeXManager)
# Keeps full functionality: multi-tab .bib files, undo/redo,
# copy/paste entries, DOI fetch, bibliography conversion.
# =========================================================
class BibTeXManagerWidget(QWidget):
    """Full BibTeX Manager as an embeddable QWidget."""
    def __init__(self, main_window=None, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.tabs_data = {}
        self.clipboard_entry = None
        self.current_entry = None
        # ✅ Allow the widget to resize freely
        self.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )
        self.setMinimumSize(300, 200)
        self._build_ui()
        self.new_file()
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(2, 2, 2, 2)
        root.setSpacing(2)
        # — toolbar row 1: file / undo-redo / doi / convert —
        tb = QHBoxLayout()
        tb.setSpacing(2)
        for label, slot in [
            ("New",      self.new_file),
            ("Open",     self.open_file),
            ("Save",     self.save_file),
            ("Save As",  self.save_file_as),
        ]:
            b = QPushButton(label)
            b.setFixedHeight(28)
            b.clicked.connect(slot)
            tb.addWidget(b)
        self.undo_btn = QPushButton("Undo")
        self.undo_btn.setFixedHeight(28)
        self.undo_btn.setEnabled(False)
        self.undo_btn.clicked.connect(self.undo)
        tb.addWidget(self.undo_btn)
        self.redo_btn = QPushButton("Redo")
        self.redo_btn.setFixedHeight(28)
        self.redo_btn.setEnabled(False)
        self.redo_btn.clicked.connect(self.redo)
        tb.addWidget(self.redo_btn)
        close_btn = QPushButton("Close")
        close_btn.setFixedHeight(28)
        close_btn.clicked.connect(self.close_file)
        tb.addWidget(close_btn)
        tb.addSpacing(8)
        fetch_btn = QPushButton("Fetch DOI")
        fetch_btn.setFixedHeight(28)
        fetch_btn.setMinimumWidth(80)
        fetch_btn.clicked.connect(self.fetch_from_doi)
        tb.addWidget(fetch_btn)
        tb.addSpacing(8)
        convert_btn = QPushButton("Convert")
        convert_btn.setFixedHeight(28)
        convert_btn.clicked.connect(self.convert_to_bibliography)
        tb.addWidget(convert_btn)
        self.style_combo = QComboBox()
        self.style_combo.setFixedHeight(28)
        self.style_combo.addItems([
            "plain.bst", "abbrv.bst", "alpha.bst", "unsrt.bst",
            "siam.bst", "acm.bst", "ieeetr.bst", "apalike.bst",
            "apa.bst", "chicago.bst", "harvard.bst", "nature.bst",
            "science.bst", "amsplain.bst", "amsalpha.bst",
            "abbrvnat.bst", "plainnat.bst", "unsrtnat.bst",
            "kluwer.bst", "IEEEtran.bst", "springer.bst",
            "elsevier.bst",
        ])
        self.style_combo.setToolTip("Select bibliography style")
        tb.addWidget(self.style_combo)
        tb.addStretch()
        root.addLayout(tb)
        # — toolbar row 2: entry operations —
        bar = QHBoxLayout()
        bar.setSpacing(2)
        add_btn = QPushButton("Add Entry")
        copy_btn = QPushButton("Copy Entry")
        paste_btn = QPushButton("Paste Entry")
        del_btn = QPushButton("Delete Entry")
        genkey_btn = QPushButton("Generate Key")
        apply_btn = QPushButton("Apply Changes")
        for b in [add_btn, copy_btn, paste_btn, del_btn, genkey_btn, apply_btn]:
            b.setFixedHeight(28)
        add_btn.clicked.connect(self.add_entry)
        copy_btn.clicked.connect(self.copy_entry)
        paste_btn.clicked.connect(self.paste_entry)
        del_btn.clicked.connect(self.delete_entry)
        genkey_btn.clicked.connect(self.generate_key)
        apply_btn.clicked.connect(self.apply_changes)
        bar.addWidget(add_btn)
        bar.addWidget(copy_btn)
        bar.addWidget(paste_btn)
        bar.addWidget(del_btn)
        bar.addStretch()
        bar.addWidget(genkey_btn)
        bar.addWidget(apply_btn)
        root.addLayout(bar)
        # — main area: inner tab widget | editor inside a scroll area —
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        # ✅ Let the inner tab widget expand
        self.tab_widget.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )
        # ✅ Wrap editor in a scroll area so it works at any size
        self.editor = EntryEditor()
        self.editor.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )
        editor_scroll = QScrollArea()
        editor_scroll.setWidgetResizable(True)
        editor_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        editor_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        editor_scroll.setWidget(self.editor)
        editor_scroll.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )
        # ✅ Use a proper resizable splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self.tab_widget)
        splitter.addWidget(editor_scroll)
        splitter.setSizes([550, 350])
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        # ✅ Let the splitter fill all available space
        splitter.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )
        root.addWidget(splitter, 1)  # ✅ stretch factor 1 so it takes all remaining space
    # ================================================================
    #  Tab management
    # ================================================================
    def get_current_db(self):
        idx = self.tab_widget.currentIndex()
        if idx >= 0 and idx in self.tabs_data:
            return self.tabs_data[idx]['db']
        return None
    def get_current_table(self):
        idx = self.tab_widget.currentIndex()
        if idx >= 0 and idx in self.tabs_data:
            return self.tabs_data[idx]['table']
        return None
    def create_new_tab(self, name="Untitled", db=None):
        table = EntryTable()
        # ✅ Let the table resize
        table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        table.horizontalHeader().setStretchLastSection(True)
        if db is None:
            db = BibDatabaseModel()
        table.itemSelectionChanged.connect(self.on_entry_selected)
        idx = self.tab_widget.addTab(table, name)
        self.tab_widget.setCurrentIndex(idx)
        self.tabs_data[idx] = {'db': db, 'table': table}
        return idx
    def close_tab(self, index):
        if index < 0 or index not in self.tabs_data:
            return
        db = self.tabs_data[index]['db']
        if db.modified:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                f"Tab '{self.tab_widget.tabText(index)}' has unsaved changes. Close anyway?",
                QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.No:
                return
        self.tab_widget.removeTab(index)
        del self.tabs_data[index]
        # Reindex
        new_data = {}
        for i in range(self.tab_widget.count()):
            old_idx = list(self.tabs_data.keys())[i] if i < len(self.tabs_data) else None
            if old_idx is not None:
                new_data[i] = self.tabs_data[old_idx]
        self.tabs_data = new_data
        # ✅ Ensure the tab widget is never empty: create a new Untitled tab if the last one was closed
        if self.tab_widget.count() == 0:
            self.new_file()
        else:
            self.current_entry = None
            self.editor.current_entry = None
            self.editor.key_edit.clear()
            for w in self.editor.field_widgets.values():
                w.clear()
    def on_tab_changed(self, index):
        if index >= 0:
            table = self.get_current_table()
            if table and table.currentRow() >= 0:
                self.on_entry_selected()
            else:
                self.current_entry = None
                self.editor.current_entry = None
                self.editor.key_edit.clear()
                for w in self.editor.field_widgets.values():
                    w.clear()
            self.update_undo_redo_buttons()
    def update_tab_modified_indicator(self):
        idx = self.tab_widget.currentIndex()
        if idx < 0 or idx not in self.tabs_data:
            return
        db = self.tabs_data[idx]['db']
        text = self.tab_widget.tabText(idx).replace(" *", "").replace(" 💾", "")
        if db.modified:
            text += " *"
        self.tab_widget.setTabText(idx, text)
    def update_undo_redo_buttons(self):
        db = self.get_current_db()
        if db:
            self.undo_btn.setEnabled(db.can_undo())
            self.redo_btn.setEnabled(db.can_redo())
        else:
            self.undo_btn.setEnabled(False)
            self.redo_btn.setEnabled(False)
    # ================================================================
    #  Actions
    # ================================================================
    def new_file(self):
        self.create_new_tab("Untitled")
        self.current_entry = None
    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open BibTeX", "", "BibTeX (*.bib)")
        if path:
            db = BibDatabaseModel()
            db.load(path)
            filename = os.path.basename(path)
            name = os.path.splitext(filename)[0]
            idx = self.create_new_tab(name, db)
            self.tabs_data[idx]['table'].populate(db.entries)
    def save_file(self):
        db = self.get_current_db()
        if not db:
            return
        if not db.file_path:
            self.save_file_as()
        else:
            db.save()
            self.update_tab_modified_indicator()
        duplicates = find_duplicate_keys(db.entries)
        if duplicates:
            QMessageBox.warning(
                self, "Duplicate keys detected",
                f"{len(duplicates)} duplicate key(s) found:\n"
                + "\n".join(duplicates.keys()))
            return
    def save_file_as(self):
        db = self.get_current_db()
        if not db:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save BibTeX", "", "BibTeX (*.bib)")
        if path:
            db.save(path)
            filename = os.path.basename(path)
            name = os.path.splitext(filename)[0]
            self.tab_widget.setTabText(self.tab_widget.currentIndex(), name)
        invalid = [e for e in db.entries if validate_entry(e)]
        if invalid:
            QMessageBox.warning(
                self, "Validation errors",
                f"{len(invalid)} entries have missing required fields.\n"
                "They are marked with ⚠ in the table.")
    def close_file(self):
        idx = self.tab_widget.currentIndex()
        if idx >= 0:
            self.close_tab(idx)
    def undo(self):
        db = self.get_current_db()
        table = self.get_current_table()
        if not db or not table:
            return
        if db.undo():
            table.populate(db.entries)
            self.update_tab_modified_indicator()
            self.update_undo_redo_buttons()
            self.current_entry = None
            self.editor.current_entry = None
    def redo(self):
        db = self.get_current_db()
        table = self.get_current_table()
        if not db or not table:
            return
        if db.redo():
            table.populate(db.entries)
            self.update_tab_modified_indicator()
            self.update_undo_redo_buttons()
            self.current_entry = None
            self.editor.current_entry = None
    def add_entry(self):
        db = self.get_current_db()
        table = self.get_current_table()
        if not db or not table:
            return
        db.save_state()
        entry = BibEntry(entry_type="article", key="newkey", fields={})
        db.entries.append(entry)
        db.modified = True
        table.populate(db.entries)
        self.update_tab_modified_indicator()
        self.update_undo_redo_buttons()
        for row, e in enumerate(table.visible_entries):
            if e is entry:
                table.selectRow(row)
                break
    def copy_entry(self):
        table = self.get_current_table()
        db = self.get_current_db()
        if not table or not db:
            return
        row = table.currentRow()
        if row >= 0 and row < len(table.visible_entries):
            entry = table.visible_entries[row]
            self.clipboard_entry = BibEntry(
                entry_type=entry.entry_type,
                key=entry.key,
                fields=dict(entry.fields))
            QMessageBox.information(
                self, "Copied",
                f"Entry '{entry.key}' copied to clipboard.")
        else:
            QMessageBox.warning(
                self, "No Selection",
                "Please select an entry to copy.")
    def paste_entry(self):
        db = self.get_current_db()
        table = self.get_current_table()
        if not db or not table:
            return
        if not self.clipboard_entry:
            QMessageBox.warning(
                self, "Nothing to Paste",
                "No entry in clipboard. Please copy an entry first.")
            return
        db.save_state()
        new_entry = BibEntry(
            entry_type=self.clipboard_entry.entry_type,
            key=self.clipboard_entry.key + "_copy",
            fields=dict(self.clipboard_entry.fields))
        db.entries.append(new_entry)
        db.modified = True
        table.populate(db.entries)
        self.update_tab_modified_indicator()
        self.update_undo_redo_buttons()
        for row, entry in enumerate(table.visible_entries):
            if entry is new_entry:
                table.selectRow(row)
                break
        QMessageBox.information(
            self, "Pasted",
            f"Entry pasted as '{new_entry.key}'.")
    def delete_entry(self):
        table = self.get_current_table()
        db = self.get_current_db()
        if not table or not db:
            return
        row = table.currentRow()
        if row >= 0 and row < len(table.visible_entries):
            db.save_state()
            entry_to_delete = table.visible_entries[row]
            if entry_to_delete in db.entries:
                db.entries.remove(entry_to_delete)
                db.modified = True
                table.populate(db.entries)
                self.current_entry = None
                self.update_tab_modified_indicator()
                self.update_undo_redo_buttons()
    def on_entry_selected(self):
        table = self.get_current_table()
        db = self.get_current_db()
        if not table or not db:
            return
        row = table.currentRow()
        if row >= 0 and row < len(table.visible_entries):
            self.current_entry = table.visible_entries[row]
            self.editor.load_entry(self.current_entry)
    def apply_changes(self):
        db = self.get_current_db()
        table = self.get_current_table()
        if not self.current_entry or not db or not table:
            return
        if not self.editor.validate():
            QMessageBox.warning(
                self, "Invalid entry",
                "Please fill all required fields (marked in red).")
            return
        db.save_state()
        self.editor.apply_to_entry(self.current_entry)
        db.modified = True
        table.populate(db.entries)
        self.update_tab_modified_indicator()
        self.update_undo_redo_buttons()
    def generate_key(self):
        if not self.current_entry:
            return
        author = self.current_entry.get("author")
        year = self.current_entry.get("year")
        title = self.current_entry.get("title")
        key = generate_citation_key(author, year, title)
        self.editor.key_edit.setText(key)
        self.current_entry.key = key
    def fetch_from_doi(self):
        doi, ok = QInputDialog.getText(
            self, "Fetch from DOI",
            "Enter DOI (e.g., 10.1234/example):",
            QLineEdit.Normal, "")
        if not ok or not doi.strip():
            return
        progress = QProgressDialog(
            "Fetching metadata from DOI...", None, 0, 100, self)
        progress.setWindowTitle("Fetching...")
        progress.setMinimumWidth(400)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        self._doi_worker = DOIFetchWorker(doi)
        self._doi_worker.progress.connect(progress.setValue)
        self._doi_worker.finished.connect(
            lambda md: self._on_fetch_complete(md, doi, progress))
        self._doi_worker.start()
    def _on_fetch_complete(self, metadata, doi, progress):
        progress.close()
        db = self.get_current_db()
        table = self.get_current_table()
        if not db or not table:
            return
        if not metadata:
            QMessageBox.warning(
                self, "Fetch Failed",
                f"Could not fetch metadata for DOI: {doi}\n\n"
                "Please check the DOI and try again.")
            return
        if self.current_entry:
            reply = QMessageBox.question(
                self, "Update or Create?",
                "Update the current entry with fetched data?\n\n"
                "Yes → update current entry\nNo  → create a new entry",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            if reply == QMessageBox.Cancel:
                return
            db.save_state()
            if reply == QMessageBox.Yes:
                entry = self.current_entry
            else:
                entry = BibEntry(entry_type=metadata["entry_type"],
                                 key="", fields={})
                db.entries.append(entry)
        else:
            db.save_state()
            entry = BibEntry(entry_type=metadata["entry_type"],
                             key="", fields={})
            db.entries.append(entry)
        entry.entry_type = metadata["entry_type"]
        for field, value in metadata["fields"].items():
            entry.fields[field] = value
        entry.key = generate_citation_key(
            entry.get("author"), entry.get("year"), entry.get("title"))
        db.modified = True
        table.populate(db.entries)
        self.update_tab_modified_indicator()
        self.update_undo_redo_buttons()
        for i, e in enumerate(db.entries):
            if e is entry:
                table.selectRow(i)
                break
        QMessageBox.information(
            self, "Success",
            f"Metadata fetched successfully!\n\nGenerated key: {entry.key}")
    # def convert_to_bibliography(self):
        # db = self.get_current_db()
        # if not db or not db.entries:
            # QMessageBox.warning(
                # self, "No Entries",
                # "No entries to convert. Open or create a bibliography first.")
            # return
        # style = self.style_combo.currentText()
        # result = convert_to_thebibliography(db.entries, style)
        # from PyQt5.QtWidgets import QDialog, QTextEdit, QLabel
        # dialog = QDialog(self)
        # dialog.setWindowTitle(f"Bibliography Conversion - {style}")
        # dialog.resize(700, 500)
        # lay = QVBoxLayout()
        # lay.addWidget(QLabel(
            # f"Converted {len(db.entries)} entries to {style} format:"))
        # te = QTextEdit()
        # te.setPlainText(result)
        # te.setReadOnly(True)
        # te.setFontFamily("Courier")
        # lay.addWidget(te)
        # btn_lay = QHBoxLayout()
        # copy_btn = QPushButton("Copy to Clipboard")
        # copy_btn.clicked.connect(lambda: self._copy_to_clipboard(result))
        # close_btn = QPushButton("Close")
        # close_btn.clicked.connect(dialog.accept)
        # btn_lay.addWidget(copy_btn)
        # btn_lay.addStretch()
        # btn_lay.addWidget(close_btn)
        # lay.addLayout(btn_lay)
        # dialog.setLayout(lay)
        # dialog.exec_()
    def convert_to_bibliography(self):
        db = self.get_current_db()
        if not db or not db.entries:
            QMessageBox.warning(
                self, "No Entries",
                "No entries to convert. Open or create a bibliography first.")
            return
        style = self.style_combo.currentText()
        result = convert_to_thebibliography(db.entries, style)

        from PyQt5.QtWidgets import QDialog, QTextEdit, QLabel, QPushButton, QHBoxLayout, QVBoxLayout
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Bibliography Conversion - {style}")
        dialog.resize(700, 500)
        lay = QVBoxLayout()
        lay.addWidget(QLabel(
            f"Converted {len(db.entries)} entries to {style} format:"))
        te = QTextEdit()
        te.setPlainText(result)
        te.setReadOnly(True)
        te.setFontFamily("Courier")
        lay.addWidget(te)

        btn_lay = QHBoxLayout()
        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.clicked.connect(lambda: self._copy_to_clipboard(result))

        insert_btn = QPushButton("Insert")
        insert_btn.setToolTip("Insert bibliography at cursor in current editor")
        insert_btn.clicked.connect(lambda: self._insert_bibliography_inline(result, dialog))
        insert_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #5cb85c, stop:1 #4cae4c);
                color: white;
                border-style: outset;
                border-width: 2px;
                border-radius: 4px;
                border-color: #3e8e3e;
                font-weight: bold;
                font-size: 8pt;
                padding: 0 10px;
                min-height: 22px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #6ec86e, stop:1 #5cb85c);
                border-color: #4cae4c;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #3e8e3e, stop:1 #4cae4c);
                border-style: inset;
                border-color: #2e6e2e;
                padding-top: 2px;
                padding-bottom: 0px;
            }
            QPushButton:disabled {
                background: #cccccc;
                border-color: #aaaaaa;
                color: #888888;
            }
        """)        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)

        btn_lay.addWidget(copy_btn)
        btn_lay.addWidget(insert_btn)      # placed beside Copy button
        btn_lay.addStretch()
        btn_lay.addWidget(close_btn)
        lay.addLayout(btn_lay)
        dialog.setLayout(lay)
        dialog.exec_()

    def _insert_bibliography_inline(self, latex_code, dialog):
        """Insert the generated bibliography into the active editor and close the dialog."""
        try:
            # Access the main window's editor manager (adapt to your actual structure)
            if hasattr(self, 'main_window') and self.main_window:
                editor_manager = self.main_window.editor_manager
                if editor_manager:
                    active_editor = editor_manager.get_active_editor()
                    if active_editor:
                        cursor = active_editor.textCursor()
                        cursor.insertText(latex_code)
                        active_editor.setTextCursor(cursor)
                        active_editor.setFocus()
                        # Optionally close the dialog after insertion
                        dialog.accept()
                        return
            # Fallback: copy to clipboard if no editor is active
            self._copy_to_clipboard(latex_code)
            QMessageBox.information(self, "Inserted to Clipboard",
                                    "No active editor found.\nCopied to clipboard instead.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to insert: {str(e)}")        
    def _copy_to_clipboard(self, text):
        QApplication.clipboard().setText(text)
        QMessageBox.information(
            self, "Copied",
            "Bibliography has been copied to clipboard!")
# =========================================================
# Integration function (mirrors add_tools_tab_to_pdf_viewer)
# =========================================================
def add_bibtex_manager_tab_to_pdf_viewer(main_window):
    """Add the BibTeX Manager tab to the PDF viewer."""
    try:
        if not hasattr(main_window, 'pdf_manager'):
            QMessageBox.warning(main_window, "Warning",
                                "PDF manager not available!")
            return
        if not hasattr(main_window, 'layout_manager'):
            QMessageBox.warning(main_window, "Warning",
                                "Layout manager not available!")
            return
        layout_manager = main_window.layout_manager
        pdf_manager = main_window.pdf_manager
        # Ensure PDF container exists
        if (not hasattr(layout_manager, 'pdf_container')
                or layout_manager.pdf_container is None):
            layout_manager._recreate_pdf_container()
        # Tabbed mode only
        if pdf_manager.pdf_layout_mode != "tabbed":
            QMessageBox.information(
                main_window, "Info",
                "BibTeX Manager tab is only available in tabbed mode. "
                "Switch to tabbed mode first.")
            return
        # Initialise pdf_tabs if needed
        if (not hasattr(pdf_manager, 'pdf_tabs')
                or pdf_manager.pdf_tabs is None):
            pdf_manager.pdf_tabs = QTabWidget()
            pdf_manager.pdf_tabs.setTabsClosable(True)
            if hasattr(pdf_manager, 'close_pdf_tab'):
                pdf_manager.pdf_tabs.tabCloseRequested.connect(
                    pdf_manager.close_pdf_tab)
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
            QMessageBox.critical(main_window, "Error",
                                 "Could not initialise PDF tabs")
            return
        # Remove placeholder tabs
        for i in reversed(range(tab_widget.count())):
            if tab_widget.tabText(i) in ("Welcome", "No Pdfs", "No PDFs"):
                tab_widget.removeTab(i)
        # If tab already exists, just switch to it
        for i in range(tab_widget.count()):
            if tab_widget.tabText(i) == "BibTeX Manager":
                tab_widget.setCurrentIndex(i)
                return
        # Create the widget
        bib_tab = BibTeXManagerWidget(main_window)
        # Prevent garbage-collection
        if not hasattr(main_window, '_bibtex_tabs'):
            main_window._bibtex_tabs = []
        main_window._bibtex_tabs.append(bib_tab)
        # Add to tab widget
        tab_index = tab_widget.addTab(bib_tab, "BibTeX Manager")
        tab_widget.setCurrentIndex(tab_index)
        tab_widget.setTabsClosable(True)
        # Ensure it is in the layout
        pdf_layout = layout_manager.pdf_container.layout()
        if pdf_layout and pdf_layout.indexOf(tab_widget) == -1:
            while pdf_layout.count():
                item = pdf_layout.takeAt(0)
                if item.widget() and item.widget() != tab_widget:
                    item.widget().setParent(None)
            pdf_layout.addWidget(tab_widget)
        tab_widget.show()
        tab_widget.setVisible(True)
        bib_tab.show()
        layout_manager.pdf_container.update()
        layout_manager.pdf_container.repaint()
        #print(f"✅ BibTeX Manager tab added at index {tab_index}")
    except Exception as e:
        QMessageBox.critical(
            main_window, "Error",
            f"Failed to add BibTeX Manager tab:\n{str(e)}")
        import traceback
        traceback.print_exc()
# =========================================================
# Integration function  (mirrors add_tools_tab_to_pdf_viewer)
# =========================================================
def add_bibtex_manager_tab_to_pdf_viewer(main_window):
    """Add the BibTeX Manager tab to the PDF viewer."""
    lang = main_window.menu_language
    translations = main_window.translations
    tr = translations[lang]    
    try:
        if not hasattr(main_window, 'pdf_manager'):
            QMessageBox.warning(main_window, "Warning",
                                "PDF manager not available!")
            return
        if not hasattr(main_window, 'layout_manager'):
            QMessageBox.warning(main_window, "Warning",
                                "Layout manager not available!")
            return
        layout_manager = main_window.layout_manager
        pdf_manager = main_window.pdf_manager
        # Ensure PDF container exists
        if (not hasattr(layout_manager, 'pdf_container')
                or layout_manager.pdf_container is None):
            layout_manager._recreate_pdf_container()
        # Tabbed mode only
        if pdf_manager.pdf_layout_mode != "tabbed":
            QMessageBox.information(
                main_window, "Info",
                "BibTeX Manager tab is only available in tabbed mode. "
                "Switch to tabbed mode first.")
            return
        # Initialise pdf_tabs if needed
        if (not hasattr(pdf_manager, 'pdf_tabs')
                or pdf_manager.pdf_tabs is None):
            from PyQt5.QtWidgets import QTabWidget
            pdf_manager.pdf_tabs = QTabWidget()
            pdf_manager.pdf_tabs.setTabsClosable(True)
            if hasattr(pdf_manager, 'close_pdf_tab'):
                pdf_manager.pdf_tabs.tabCloseRequested.connect(
                    pdf_manager.close_pdf_tab)
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
            QMessageBox.critical(main_window, "Error",
                                 "Could not initialise PDF tabs")
            return
        # Remove placeholder tabs
        for i in reversed(range(tab_widget.count())):
            if tab_widget.tabText(i) in ("Welcome", "No Pdfs", "No PDFs"):
                tab_widget.removeTab(i)
        # If tab already exists, just switch to it
        possible_labels = {
            tr["bibtex_manager"] for tr in translations.values()
        }                                
        for i in range(tab_widget.count()):
            if tab_widget.tabText(i) in possible_labels:
                tab_widget.setCurrentIndex(i)
                return
        # Create the widget
        bib_tab = BibTeXManagerWidget(main_window)
        # Prevent garbage-collection
        if not hasattr(main_window, '_bibtex_tabs'):
            main_window._bibtex_tabs = []
        main_window._bibtex_tabs.append(bib_tab)
        # Add to tab widget
        tab_name = tr.get("bibtex_manager", "BibTeX Manager")
        tab_index = tab_widget.addTab(bib_tab, tab_name) 
        tab_widget.tabBar().setTabData(tab_index, "bibtex_manager")          
        # ✅ Set SVG icon properly
        icon = QIcon("icons/bibtex.svg")
        tab_widget.setTabIcon(tab_index, icon)        
        tab_widget.setCurrentIndex(tab_index)
        tab_widget.setTabsClosable(True)
        # Ensure it is in the layout
        pdf_layout = layout_manager.pdf_container.layout()
        if pdf_layout and pdf_layout.indexOf(tab_widget) == -1:
            while pdf_layout.count():
                item = pdf_layout.takeAt(0)
                if item.widget() and item.widget() != tab_widget:
                    item.widget().setParent(None)
            pdf_layout.addWidget(tab_widget)
        tab_widget.show()
        tab_widget.setVisible(True)
        bib_tab.show()
        layout_manager.pdf_container.update()
        layout_manager.pdf_container.repaint()
        #print(f"✅ BibTeX Manager tab added at index {tab_index}")
    except Exception as e:
        QMessageBox.critical(
            main_window, "Error",
            f"Failed to add BibTeX Manager tab:\n{str(e)}")
        import traceback
        traceback.print_exc()