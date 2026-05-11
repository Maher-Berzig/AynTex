# latex_commands_menu.py
"""
Latex commands Menu - Comprehensive Latex commands insertion
"""

from PyQt5.QtWidgets import QAction, QMenu
from PyQt5.QtCore import Qt


class LatexCommandsMenu:
    def __init__(self, main_window, insert_callback, language="en"):
        self.main_window = main_window
        self.insert_callback = insert_callback
        self.menu_language = language
        self.build_commands_categories()
        

    def build_commands_categories(self):   
        """Build/rebuild commands categories with current language translations"""
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]        
        # Latex commands organized by category
        # Updated with proper cursor positioning and delimiter handling        
        self.sectionning_categories = {
            "Delimiter": {
                "tr" : tr["commands:delimiters"],
                "commands": [

                    # Basic paired delimiters
                    ("{ }", r"{ cursor }", "Braces", None),
                    ("( )", r"( cursor )", "Parentheses", None),
                    ("[ ]", r"[ cursor ]", "Square brackets", None),
                    ("⟨ ⟩", r"\langle cursor \rangle", "Angle brackets", None),
                    ("| |", r"| cursor |", "Vertical bars", None),
                    ("‖ ‖", r"\| cursor \|", "Double vertical bars", None),
                    ("⌊ ⌋", r"\lfloor cursor \rfloor", "Floor brackets", None),
                    ("⌈ ⌉", r"\lceil cursor \rceil", "Ceiling brackets", None),
                    

                    # Scalable \left...\right... forms
                    ("Left(", r"\left( cursor \right)", "Scalable parentheses", None),
                    ("Left[", r"\left[ cursor \right]", "Scalable brackets", None),
                    ("Left{", r"\left\{ cursor \right\}", "Scalable braces", None),
                    ("Left|", r"\left| cursor \right|", "Scalable bars", None),
                    ("Left‖", r"\left\| cursor \right\|", "Scalable double bars", None),
                    ("Left⟨", r"\left\langle cursor \right\rangle", "Scalable angle brackets", None),
                    ("Left⌊", r"\left\lfloor cursor \right\rfloor", "Scalable floor", None),
                    ("Left⌈", r"\left\lceil cursor \right\rceil", "Scalable ceiling", None),
                    ("/", r"\left/ cursor \right\\", "Forward / backward slash", None),

                    # Invisible / one-sided delimiters
                    ("Null right", r"\left( cursor \right.", "Open delimiter (no right)", None),
                    ("Null left", r"\left. cursor \right)", "Close delimiter (no left)", None),

                    # Fixed-size delimiters
                    ("big()", r"\big( cursor \big)", "Big parentheses", None),
                    ("Big()", r"\Big( cursor \Big)", "Bigger parentheses", None),
                    ("bigg()", r"\bigg( cursor \bigg)", "Bigg parentheses", None),
                    ("Bigg()", r"\Bigg( cursor \Bigg)", "Biggest parentheses", None),

                    ("big[]", r"\big[ cursor \big]", "Big brackets", None),
                    ("Big[]", r"\Big[ cursor \Big]", "Bigger brackets", None),
                    ("bigg[]", r"\bigg[ cursor \bigg]", "Bigg brackets", None),
                    ("Bigg[]", r"\Bigg[ cursor \Bigg]", "Biggest brackets", None),

                    ("big{}", r"\big\{ cursor \big\}", "Big braces", None),
                    ("Big{}", r"\Big\{ cursor \Big\}", "Bigger braces", None),
                    ("bigg{}", r"\bigg\{ cursor \bigg\}", "Bigg braces", None),
                    ("Bigg{}", r"\Bigg\{ cursor \Bigg\}", "Biggest braces", None),

                    ("big⟨⟩", r"\big\langle cursor \big\rangle", "Big angle brackets", None),
                    ("Big⟨⟩", r"\Big\langle cursor \Big\rangle", "Bigger angle brackets", None),
                    ("bigg⟨⟩", r"\bigg\langle cursor \bigg\rangle", "Bigg angle brackets", None),
                    ("Bigg⟨⟩", r"\Bigg\langle cursor \Bigg\rangle", "Biggest angle brackets", None),

                    ("big| |", r"\big| cursor \big|", "Big vertical bars", None),
                    ("Big| |", r"\Big| cursor \Big|", "Bigger vertical bars", None),
                    ("bigg| |", r"\bigg| cursor \bigg|", "Bigg vertical bars", None),
                    ("Bigg| |", r"\Bigg| cursor \Bigg|", "Biggest vertical bars", None),

                    # Special math delimiters
                    ("⎰ ⎱", r"\left\lgroup cursor \right\rgroup", "Group brackets", None),
                    ("⟦ ⟧", r"\left\llbracket cursor \right\rrbracket", "Double brackets", None),
                    ("⟮ ⟯", r"\left\lpar cursor \right\rpar", "Double parentheses", None),
                    ("⟬ ⟭", r"\left\lbrace cursor \right\rbrace", "Curly parentheses", None),
                    ("⟪ ⟫", r"\left\langle\!\left\langle cursor \right\rangle\!\right\rangle", "Double angle brackets", None),

                    # Norms and absolute values
                    ("|x|", r"\lvert cursor \rvert", "Absolute value", None),
                    ("‖x‖", r"\lVert cursor \rVert", "Norm", None),

                ]
            },
            
            "Sectioning": {
                "tr" : tr["commands:sectioning"],
                "commands": [
                    ("\\part{}", r"\part{cursor}", "Part", None),
                    ("\\chapter{}", r"\chapter{cursor}", "Chapter", None),
                    ("\\section{}", r"\section{cursor}", "Section", None),
                    ("\\subsection{}", r"\subsection{cursor}", "Subsection", None),
                    ("\\subsubsection{}", r"\subsubsection{cursor}", "Subsubsection", None),
                    ("\\paragraph{}", r"\paragraph{cursor}", "Paragraph", None),
                    ("\\subparagraph{cursor}", r"\subparagraph{cursor}", "Subparagraph", None),
                    ("\\part*{}", r"\part*{cursor}", "Part (no number)", None),
                    ("\\chapter*{}", r"\chapter*{cursor}", "Chapter (no number)", None),
                    ("\\section*{}", r"\section*{cursor}", "Section (no number)", None),
                    ("\\subsection*{}", r"\subsection*{cursor}", "Subsection (no number)", None),
                    ("\\subsubsection*{}", r"\subsubsection*{cursor}", "Subsubsection (no number)", None),
                    ("\\paragraph*{}", r"\paragraph*{cursor}", "Paragraph (no number)", None),
                    ("\\subparagraph*{}", r"\subparagraph*{cursor}", "Subparagraph (no number)")
                ]
            },
            "Environments": {
                "tr" : tr["commands:environments"],
                "commands": [

                    # Layout & boxes
                    ("minipage", "\\begin{minipage}[t]{0.5\\textwidth}\n" "cursor\n" "\\end{minipage}", "Minipage", None),
                    ("center", "\\begin{center}\n" "cursor\n" "\\end{center}", "Center", None),
                    ("flushleft", "\\begin{flushleft}\n" "cursor\n" "\\end{flushleft}", "Flush left", None),
                    ("flushright", "\\begin{flushright}\n" "cursor\n" "\\end{flushright}", "Flush right", None),

                    # Theorem-like
                    ("theorem", "\\begin{theorem}\n" "cursor\n" "\\end{theorem}", "Theorem", None),
                    ("proposition", "\\begin{proposition}\n" "cursor\n" "\\end{proposition}", "Proposition", None),
                    ("lemma", "\\begin{lemma}\n" "cursor\n" "\\end{lemma}", "Lemma", None),
                    ("corollary", "\\begin{corollary}\n" "cursor\n" "\\end{corollary}", "Corollary", None),
                    ("definition", "\\begin{definition}\n" "cursor\n" "\\end{definition}", "Definition", None),
                    ("example", "\\begin{example}\n" "cursor\n" "\\end{example}", "Example", None),
                    ("remark", "\\begin{remark}\n" "cursor\n" "\\end{remark}", "Remark", None),
                    ("proof", "\\begin{proof}\n" "cursor\n" "\\end{proof}", "Proof", None),

                    # Quotations & text blocks
                    ("quote", "\\begin{quote}\n" "cursor\n" "\\end{quote}", "Quote", None),
                    ("quotation", "\\begin{quotation}\n" "cursor\n" "\\end{quotation}", "Quotation", None),
                    ("verse", "\\begin{verse}\n" "cursor\n" "\\end{verse}", "Verse", None),
                    ("verbatim", "\\begin{verbatim}\n" "cursor\n" "\\end{verbatim}", "Verbatim", None),
                    ("comment", "\\begin{comment}\n" "cursor\n" "\\end{comment}", "Comment (comment pkg)", None),

                    # Figures & tables
                    ("figure",
                     "\\begin{figure}[h]\n"
                     "    \\centering\n"
                     "    % \\includegraphics{cursor}\n"
                     "    \\caption{}\n"
                     "    \\label{fig:}\n"
                     "\\end{figure}",
                     "Figure", None),

                    ("figure*",
                     "\\begin{figure*}[t]\n"
                     "    \\centering\n"
                     "    % \\includegraphics{cursor}\n"
                     "    \\caption{}\n"
                     "    \\label{fig:}\n"
                     "\\end{figure*}",
                     "Wide figure", None),

                    ("table",
                     "\\begin{table}[h]\n"
                     "    \\centering\n"
                     "    \\begin{tabular}{|c|c|c|}\n"
                     "        \\hline\n"
                     "        cursor & B & C \\\\\n"
                     "        \\hline\n"
                     "        1 & 2 & 3 \\\\\n"
                     "        \\hline\n"
                     "    \\end{tabular}\n"
                     "    \\caption{}\n"
                     "    \\label{tab:}\n"
                     "\\end{table}",
                     "Table", None),

                    ("table*",
                     "\\begin{table*}[t]\n"
                     "    \\centering\n"
                     "    \\begin{tabular}{|c|c|c|}\n"
                     "        \\hline\n"
                     "        cursor & B & C \\\\\n"
                     "        \\hline\n"
                     "        1 & 2 & 3 \\\\\n"
                     "        \\hline\n"
                     "    \\end{tabular}\n"
                     "    \\caption{}\n"
                     "    \\label{tab:}\n"
                     "\\end{table*}",
                     "Wide table", None),

                    # Lists
                    ("enumerate",
                     "\\begin{enumerate}\n"
                     "\item cursor\n"
                     "\item \n"
                     "\item \n"
                     "\\end{enumerate}",
                     "Numbered list", None),

                    ("itemize",
                     "\\begin{itemize}\n"
                     "\item cursor\n"
                     "\item \n"
                     "\item \n"
                     "\\end{itemize}",
                     "Bullet list", None),

                    ("description",
                     "\\begin{description}\n"
                     "\item[Term] cursor\n"
                     "\item[Term] Description\n"
                     "\\end{description}",
                     "Description list", None),

                    ("list",
                     "\\begin{list}{}{ }\n"
                     "\item cursor\n"
                     "\item \n"
                     "\item \n"
                     "\\end{list}",
                     "Custom list", None),

                    # Math displays
                    ("equation", "\\begin{equation}\n"  "cursor\n"  "\\end{equation}", "Numbered equation", None),
                    ("equation*", "\\begin{equation*}\n"  "cursor\n"  "\\end{equation*}", "Unnumbered equation", None),

                    ("align",
                     "\\begin{align}\n"
                     "    cursor &= x \\\\\n"
                     "    y &= z\n"
                     "\\end{align}",
                     "Align equations", None),

                    ("align*",
                     "\\begin{align*}\n"
                     "    cursor &= x \\\\\n"
                     "    y &= z\n"
                     "\\end{align*}",
                     "Unnumbered align", None),

                    ("gather",
                     "\\begin{gather}\n"
                     "    cursor = a \\\\\n"
                     "    b = c\n"
                     "\\end{gather}",
                     "Gather equations", None),

                    ("gather*",
                     "\\begin{gather*}\n"
                     "    cursor = a \\\\\n"
                     "    b = c\n"
                     "\\end{gather*}",
                     "Unnumbered gather", None),

                    ("multline",
                     "\\begin{multline}\n"
                     "    a + b + c = d + e + f\n"
                     "\\end{multline}",
                     "Multiline equation", None),

                    ("cases",
                     "\\begin{cases}\n"
                     "    cursor = 1 \\\\\n"
                     "    x = 2\n"
                     "\\end{cases}",
                     "Cases", None),

                    ("split",
                     "\\begin{split}\n"
                     "    cursor &= b + c \\\\\n"
                     "    d &= e + f\n"
                     "\\end{split}",
                     "Split equations", None),

                    # Matrices & arrays
                    ("matrix",
                     "\\begin{matrix}\n"
                     "    cursor & b \\\\\n"
                     "    c & d\n"
                     "\\end{matrix}",
                     "Matrix", None),

                    ("pmatrix",
                     "\\begin{pmatrix}\n"
                     "    cursor & b \\\\\n"
                     "    c & d\n"
                     "\\end{pmatrix}",
                     "Matrix with parentheses", None),

                    ("bmatrix",
                     "\\begin{bmatrix}\n"
                     "    cursor & b \\\\\n"
                     "    c & d\n"
                     "\\end{bmatrix}",
                     "Matrix with brackets", None),

                    ("vmatrix",
                     "\\begin{vmatrix}\n"
                     "    cursor & b \\\\\n"
                     "    c & d\n"
                     "\\end{vmatrix}",
                     "Matrix with vertical bars", None),

                    ("Vmatrix",
                     "\\begin{Vmatrix}\n"
                     "    cursor & b \\\\\n"
                     "    c & d\n"
                     "\\end{Vmatrix}",
                     "Matrix with double bars", None),

                    ("array",
                     "\\begin{array}{cc}\n"
                     "    cursor & b \\\\\n"
                     "    c & d\n"
                     "\\end{array}",
                     "Array", None),

                    # Code & framed
                    ("lstlisting",
                     "\\begin{lstlisting}\n" "cursor\n"  "\\end{lstlisting}",
                     "Code listing (listings pkg)", None),

                    ("verbatim*",
                     "\\begin{verbatim*}\n"  "cursor\n" "\\end{verbatim*}",
                     "Verbatim (show spaces)", None),

                    ("framed",
                     "\\begin{framed}\n" "cursor\n" "\\end{framed}",
                     "Framed box", None),

                    ("shaded",
                     "\\begin{shaded}\n" "cursor\n"  "\\end{shaded}",
                     "Shaded box", None),

                    ("tcolorbox",
                     "\\begin{tcolorbox}[colback=blue!5!white, colframe=blue!75!black, fonttitle=\\small\\sffamily\\bfseries, title=My Title]\n" "cursor\n" "\\end{tcolorbox}", "Colored box", "\\usepackage{tcolorbox}"),
                ]
            },
            
            "Boxes": {
                "tr" : tr["commands:boxes"],
                "commands": [

                    # Basic boxes
                    ("\\mbox{}", r"\mbox{cursor}", "Make box", None),
                    ("\\makebox", r"\makebox[width][position]{cursor}", "Make box with width", None),
                    ("\\fbox{}", r"\fbox{cursor}", "Framed box", None),
                    ("\\framebox", r"\framebox[width][position]{cursor}", "Framed box with width", None),

                    # Save boxes
                    ("\\newsavebox", r"\newsavebox{\boxname}", "New save box", None),
                    ("\\sbox", r"\sbox{\boxname}{cursor}", "Save box", None),
                    ("\\savebox", r"\savebox{\boxname}[width][position]{cursor}", "Save box with options", None),
                    ("\\usebox", r"\usebox{\boxname}", "Use saved box", None),

                    # Vertical adjustments
                    ("\\raisebox", r"\raisebox{height}[depth][totalheight]{cursor}", "Raise box", None),
                    ("\\lowerbox", r"\raisebox{-height}{cursor}", "Lower box (negative raise)", None),

                    # Paragraph / text boxes
                    ("\\parbox", r"\parbox[position][height]{width}{cursor}", "Paragraph box", None),
                    ("\\minipage", "\\begin{minipage}[position][height]{width}\n" "cursor\n" "\\end{minipage}", "Mini page box", None),
                    ("\\shortstack", r"\shortstack[position]{line1 \\ line2}", "Stacked text box", None),
                    ("\\tabularbox", "\begin{tabular}{c}\n" "cursor\n" "\\end{tabular}", "Tabular box", None),

                    # Color boxes (xcolor)
                    ("\\colorbox", r"\colorbox{color}{cursor}", "Colored box", None),
                    ("\\fcolorbox", r"\fcolorbox{framecolor}{bgcolor}{cursor}", "Framed colored box", None),

                    # Rule / struts
                    ("\\rule", r"\rule{width}{height}", "Rule box", None),
                    ("\\phantom", r"\phantom{cursor}", "Invisible box (phantom)", None),
                    ("\\hphantom", r"\hphantom{cursor}", "Horizontal phantom", None),
                    ("\\vphantom", r"\vphantom{cursor}", "Vertical phantom", None),
                    ("\\strut", r"\strut", "Standard strut", None),

                    # Resize & scale (graphicx)
                    ("\\resizebox", r"\resizebox{width}{height}{cursor}", "Resize box", None),
                    ("\\scalebox", r"\scalebox{scale}{cursor}", "Scale box", None),
                    ("\\rotatebox", r"\rotatebox{angle}{cursor}", "Rotate box", None),

                    # Fancy framed boxes (various packages)
                    ("\\ovalbox", r"\ovalbox{cursor}", "Oval framed box", None),
                    ("\\shadowbox", r"\shadowbox{cursor}", "Shadowed box", None),
                    ("\\doublebox", r"\doublebox{cursor}", "Double framed box", None),

                    # Custom box environments (framed/mdframed/tcolorbox)
                    ("\\fboxrule", r"\setlength{\fboxrule}{thickness}", "Set frame thickness", None),
                    ("\\fboxsep", r"\setlength{\fboxsep}{spacing}", "Set frame padding", None),

                    ("\\begin{framed}", "\\begin{framed}\n"   "cursor\n" "\\end{framed}", "Framed environment", None),
                    ("\\begin{shaded}", "\\begin{shaded}\n"    "cursor\n" "\\end{shaded}", "Shaded box", None),
                    ("\\begin{leftbar}", "\\begin{leftbar}\n"   "cursor\n" "\\end{leftbar}", "Left bar box", None),

                    ("\\begin{mdframed}", "\\begin{mdframed}\n"   "cursor\n" "\\end{mdframed}", "mdframed box", None),
                    ("\\begin{tcolorbox}", "\\begin{tcolorbox}[options]\n"    "cursor\n" "\\end{tcolorbox}", "tcolorbox", r"\usepackage{tcolorbox}"),

                    # Margin & layout boxes
                    ("\\marginpar", r"\marginpar{cursor}", "Margin note box", None),
                    ("\\rlap", r"\rlap{cursor}", "Right overlap box", None),
                    ("\\llap", r"\llap{cursor}", "Left overlap box", None),
                    ("\\clap", r"\clap{cursor}", "Centered overlap box (mathtools)", None),

                    # Math boxes
                    ("\\boxed", r"\boxed{math}", "Boxed math", None),
                    ("\\fboxed", r"\fboxed{math}", "Framed boxed math", None),

                    # Catch-all / placeholders
                    ("\\newbox", r"\newbox\boxname", "Low-level new box register", None),
                    ("\\setbox", r"\setbox\boxname=\hbox{cursor}", "Low-level set box", None),
                    ("\\copybox", r"\copy\boxname", "Copy box", None),
                    ("\\unbox", r"\unhbox\boxname", "Unbox (use contents)", None),

                ]
            },

            "Fonts": {
                "tr" : tr["commands:fonts"],
                "commands": [

                    # Text fonts & emphasis
                    ("\\emph{}", r"\emph{cursor}", "Emphasis", None),
                    ("\\textit{}", r"\textit{cursor}", "Italic text", None),
                    ("\\textsl{}", r"\textsl{cursor}", "Slanted text", None),
                    ("\\textbf{}", r"\textbf{cursor}", "Bold text", None),
                    ("\\texttt{}", r"\texttt{cursor}", "Typewriter text", None),
                    ("\\textsc{}", r"\textsc{cursor}", "Small caps", None),
                    ("\\textsf{}", r"\textsf{cursor}", "Sans serif", None),
                    ("\\textup{}", r"\textup{cursor}", "Upright text", None),
                    ("\\textrm{}", r"\textrm{cursor}", "Roman text", None),
                    ("\\underline{}", r"\underline{cursor}", "Underlined text", None),
                    ("\\overline{}", r"\overline{cursor}", "Overlined text", None),
                    ("\\textcolor{}", r"\textcolor{color}{cursor}", "Colored text", None),

                    # Text size
                    ("{\\tiny }", r"{\tiny cursor}", "Tiny size", None),
                    ("{\\scriptsize }", r"{\scriptsize cursor}", "Script size", None),
                    ("{\\footnotesize }", r"{\footnotesize cursor}", "Footnote size", None),
                    ("{\\small }", r"{\small cursor}", "Small size", None),
                    ("{\\normalsize }", r"{\normalsize cursor}", "Normal size", None),
                    ("{\\large }", r"{\large cursor}", "Large size", None),
                    ("{\\Large }", r"{\Large cursor}", "Larger size", None),
                    ("{\\LARGE }", r"{\LARGE cursor}", "Very large size", None),
                    ("{\\huge }", r"{\huge cursor}", "Huge size", None),
                    ("{\\Huge }", r"{\Huge cursor}", "Largest size", None),

                    # Math fonts (letters)
                    ("\\mathrm{}", r"\mathrm{cursor}", "Math roman", None),
                    ("\\mathit{}", r"\mathit{cursor}", "Math italic", None),
                    ("\\mathbf{}", r"\mathbf{cursor}", "Math bold", None),
                    ("\\mathsf{}", r"\mathsf{cursor}", "Math sans serif", None),
                    ("\\mathtt{}", r"\mathtt{cursor}", "Math typewriter", None),
                    ("\\mathcal{}", r"\mathcal{cursor}", "Math calligraphic", None),
                    ("\\mathscr{}", r"\mathscr{cursor}", "Math script (requires mathrsfs)", None),
                    ("\\mathfrak{}", r"\mathfrak{cursor}", "Math fraktur", None),
                    ("\\mathbb{}", r"\mathbb{cursor}", "Blackboard bold (requires amsfonts)", None),

                    # Math bold variants
                    ("\\boldsymbol{}", r"\boldsymbol{cursor}", "Bold math symbol", None),
                    ("\\bm{}", r"\bm{cursor}", "Bold math (bm package)", None),

                    # Math size styles
                    ("\\displaystyle", r"\displaystyle cursor", "Display style math", None),
                    ("\\textstyle", r"\textstyle cursor", "Text style math", None),
                    ("\\scriptstyle", r"\scriptstyle cursor", "Script style math", None),
                    ("\\scriptscriptstyle", r"\scriptscriptstyle cursor", "Scriptscript style math", None),

                    # Operators & upright symbols
                    ("\\operatorname{}", r"\operatorname{cursor}", "Custom math operator", None),
                    ("\\DeclareMathOperator", r"\DeclareMathOperator{\\{cursor}}{cursor}", "Declare math operator", None),

                ]
            },
            
            "Accents": {
                "tr" : tr["commands:accents"],
                "commands": [

                    # Acute / Grave / Circumflex / Diaeresis / Macron / Breve / Dot
                    ("é", r"\'e", "Acute accent", None),
                    ("è", r"\`e", "Grave accent", None),
                    ("ê", r"\^e", "Circumflex accent", None),
                    ("ë", r"\"e", "Diaeresis", None),
                    ("ē", r"\=e", "Macron", None),
                    ("ĕ", r"\u{e}", "Breve", None),
                    ("ė", r"\.e", "Dot accent", None),
                    ("ȩ", r"\.{e}", "Dot below (text)", None),

                    # Hooks / Tails / Marks
                    ("ę", r"\k{e}", "Ogonek", None),
                    ("ě", r"\v{e}", "Caron (háček)", None),
                    ("ȩ̣", r"\d{e}", "Dot below", None),
                    ("ȩ̦", r"\b{e}", "Bar under", None),

                    # Other diacritics
                    ("ç", r"\c{c}", "Cedilla", None),
                    ("ñ", r"\~n", "Tilde", None),
                    ("å", r"\r{a}", "Ring above", None),
                    ("ǎ", r"\v{a}", "Caron on a", None),
                    ("ǧ", r"\v{g}", "Caron on g", None),
                    ("ş", r"\c{s}", "Cedilla on s", None),
                    ("ţ", r"\c{t}", "Cedilla on t", None),
                    ("đ", r"\dj", "D with stroke", None),
                    ("ł", r"\l", "L with stroke", None),

                    # Double accents
                    ("ő", r"\H{o}", "Double acute", None),
                    ("ű", r"\H{u}", "Double acute on u", None),

                    # Ligatures & special letters
                    ("æ", r"\ae", "AE ligature", None),
                    ("Æ", r"\AE", "AE ligature (uppercase)", None),
                    ("œ", r"\oe", "OE ligature", None),
                    ("Œ", r"\OE", "OE ligature (uppercase)", None),
                    ("ø", r"\o", "O with stroke", None),
                    ("Ø", r"\O", "O with stroke (uppercase)", None),
                    ("ß", r"\ss", "Sharp s", None),
                    ("ẞ", r"\SS", "Sharp S (uppercase)", None),

                    # Special punctuation
                    ("¡", r"!`", "Inverted exclamation", None),
                    ("¿", r"?`", "Inverted question mark", None),
                    ("«", r"\guillemotleft", "Left guillemet", None),
                    ("»", r"\guillemotright", "Right guillemet", None),

                    # Math accents
                    ("ā", r"\bar{a}", "Math bar", None),
                    ("â", r"\hat{a}", "Math hat", None),
                    ("ã", r"\tilde{a}", "Math tilde", None),
                    ("ǎ", r"\check{a}", "Math check", None),
                    ("⃗a", r"\vec{a}", "Vector arrow", None),
                    ("⏞", r"\overbrace{a+b}", "Overbrace", None),
                    ("⏟", r"\underbrace{a+b}", "Underbrace", None),

                    # Dots in math
                    ("ȧ", r"\dot{a}", "Math dot", None),
                    ("ä", r"\ddot{a}", "Math double dot", None),

                ]
            },

            "References": {
                "tr" : tr["commands:references"],
                "commands": [

                    # Basic cross-referencing
                    ("\\label{}", r"\label{cursor}", "Label", None),
                    ("\\ref{}", r"\ref{cursor}", "Reference", None),
                    ("\\pageref{}", r"\pageref{cursor}", "Page reference", None),
                    ("\\eqref{}", r"\eqref{eq:cursor}", "Equation reference", None),
                    ("\\autoref{}", r"\autoref{cursor}", "Automatic reference (hyperref)", None),
                    ("\\nameref{}", r"\nameref{cursor}", "Reference name (hyperref)", None),
                    ("\\hyperref[]{}", r"\hyperref[cursor]{text}", "Custom hyperlink", None),
                    ("\\phantomsection", r"\phantomsection", "Anchor for hyperref", None),
                    ("\\hypertarget{}{}", r"\hypertarget{cursor}{text}", "Create hyperlink target", None),
                    ("\\hyperlink{}{}", r"\hyperlink{cursor}{text}", "Link to target", None),

                    # Citations (generic + natbib)
                    ("\\cite{}", r"\cite{cursor}", "Citation", None),
                    ("\\citep{}", r"\citep{cursor}", "Parenthetical citation", None),
                    ("\\citet{}", r"\citet{cursor}", "Textual citation", None),
                    ("\\citeauthor{}", r"\citeauthor{cursor}", "Citation author", None),
                    ("\\citeyear{}", r"\citeyear{cursor}", "Citation year", None),
                    ("\\citealt{}", r"\citealt{cursor}", "Alternate citation", None),
                    ("\\citealp{}", r"\citealp{cursor}", "Parenthetical (no parentheses)", None),
                    ("\\citeyearpar{}", r"\citeyearpar{cursor}", "Year in parentheses", None),
                    ("\\nocite{}", r"\nocite{cursor}", "Add to bibliography without citing", None),

                    # BibLaTeX-style
                    ("\\parencite{}", r"\parencite{cursor}", "Parenthetical citation (biblatex)", None),
                    ("\\textcite{}", r"\textcite{cursor}", "Textual citation (biblatex)", None),
                    ("\\footcite{}", r"\footcite{cursor}", "Footnote citation", None),
                    ("\\fullcite{}", r"\fullcite{cursor}", "Full bibliography entry", None),
                    ("\\citeauthor*", r"\citeauthor*{cursor}", "Full author list", None),
                    ("\\citeyear*", r"\citeyear*{cursor}", "Full year", None),

                    # Footnotes
                    ("\\footnote{}", r"\footnote{cursor}", "Footnote", None),
                    ("\\footnotemark", r"\footnotemark", "Footnote mark", None),
                    ("\\footnotetext{}", r"\footnotetext{cursor}", "Footnote text", None),
                    ("\\thanks{}", r"\thanks{cursor}", "Thanks footnote (title)", None),

                    # Indexing
                    ("\\makeindex", r"\makeindex", "Enable index", None),
                    ("\\index{}", r"\index{cursor}", "Index entry", None),
                    ("\\printindex", r"\printindex", "Print index", None),
                    ("\\see{}", r"\see{cursor}{see also}", "Index cross-reference", None),
                    ("\\seealso{}", r"\seealso{cursor}{related}", "Index see-also", None),

                    # Glossaries
                    ("\\makeglossaries", r"\makeglossaries", "Enable glossaries", None),
                    ("\\newglossaryentry{}", r"\newglossaryentry{cursor}{name={Name},description={Desc}}", "New glossary entry", None),
                    ("\\gls{}", r"\gls{cursor}", "Glossary term", None),
                    ("\\Gls{}", r"\Gls{cursor}", "Capitalized glossary term", None),
                    ("\\glspl{}", r"\glspl{cursor}", "Plural glossary term", None),
                    ("\\printglossary", r"\printglossary", "Print glossary", None),
                    ("\\glsadd{}", r"\glsadd{cursor}", "Add entry without printing", None),

                    # Bibliography control
                    ("\\bibliography{}", r"\bibliography{refs}", "Bibliography file", None),
                    ("\\bibliographystyle{}", r"\bibliographystyle{plain}", "Bibliography style", None),
                    ("\\printbibliography", r"\printbibliography", "Print bibliography (biblatex)", None),
                    ("\\addbibresource{}", r"\addbibresource{refs.bib}", "Add bibliography resource", None),
                    ("\\defbibheading{}", r"\defbibheading{bibliography}{Title}", "Custom bibliography title", None),

                    # Cleveref package
                    ("\\cref{}", r"\cref{cursor}", "Smart reference (cleveref)", None),
                    ("\\Cref{}", r"\Cref{cursor}", "Capitalized smart reference", None),
                    ("\\crefname{}", r"\crefname{equation}{eq.}{eqs.}", "Set reference names", None),
                    ("\\Crefname{}", r"\Crefname{figure}{Fig.}{Figs.}", "Capitalized reference names", None),

                ]
            },
            
            "Bibliography": {
                "tr" : tr["commands:bibliography"],
                "commands": [

                    # Journals / Periodicals
                    ("@article", r"@article{key,"
                     "\n    author = {Author Name},"
                     "\n    title = {Title},"
                     "\n    journal = {Journal Name},"
                     "\n    year = {2026},"
                     "\n    volume = {1},"
                     "\n    number = {1},"
                     "\n    pages = {1--10}"
                     "\n}", "Article in Journal", None),

                    ("@periodical", r"@periodical{key,"
                     "\n    title = {Periodical Title},"
                     "\n    year = {2026},"
                     "\n}", "Complete Issue of a Periodical", None),

                    ("@suppperiodical", r"@suppperiodical{key,"
                     "\n    title = {Supplement Title},"
                     "\n    journal = {Journal Name},"
                     "\n    year = {2026},"
                     "\n}", "Supplemental Material in a Periodical", None),


                    # Books
                    ("@book", r"@book{key,"
                     "\n    author = {Author Name},"
                     "\n    title = {Book Title},"
                     "\n    publisher = {Publisher},"
                     "\n    year = {2026},"
                     "\n    address = {City}"
                     "\n}", "Book", None),

                    ("@mvbook", r"@mvbook{key,"
                     "\n    author = {Author Name},"
                     "\n    title = {Multi-volume Book Title},"
                     "\n    publisher = {Publisher},"
                     "\n    year = {2026}"
                     "\n}", "Multi-volume Book", None),

                    ("@inbook", r"@inbook{key,"
                     "\n    author = {Author Name},"
                     "\n    title = {Chapter Title},"
                     "\n    booktitle = {Book Title},"
                     "\n    publisher = {Publisher},"
                     "\n    year = {2026},"
                     "\n    pages = {1--20}"
                     "\n}", "Part of a Book With Its Own Title", None),

                    ("@bookinbook", r"@bookinbook{key,"
                     "\n    author = {Author Name},"
                     "\n    title = {Inner Book Title},"
                     "\n    booktitle = {Outer Book Title},"
                     "\n    publisher = {Publisher},"
                     "\n    year = {2026}"
                     "\n}", "Book in Book", None),

                    ("@suppbook", r"@suppbook{key,"
                     "\n    title = {Supplement Title},"
                     "\n    booktitle = {Book Title},"
                     "\n    year = {2026}"
                     "\n}", "Supplemental Material in a Book", None),

                    ("@booklet", r"@booklet{key,"
                     "\n    title = {Booklet Title},"
                     "\n    author = {Author Name},"
                     "\n    year = {2026}"
                     "\n}", "Booklet", None),


                    # Collections
                    ("@collection", r"@collection{key,"
                     "\n    editor = {Editor Name},"
                     "\n    title = {Collection Title},"
                     "\n    publisher = {Publisher},"
                     "\n    year = {2026}"
                     "\n}", "Single-volume Collection", None),

                    ("@mvcollection", r"@mvcollection{key,"
                     "\n    editor = {Editor Name},"
                     "\n    title = {Multi-volume Collection Title},"
                     "\n    publisher = {Publisher},"
                     "\n    year = {2026}"
                     "\n}", "Multi-volume Collection", None),

                    ("@incollection", r"@incollection{key,"
                     "\n    author = {Author Name},"
                     "\n    title = {Article Title},"
                     "\n    booktitle = {Collection Title},"
                     "\n    editor = {Editor Name},"
                     "\n    publisher = {Publisher},"
                     "\n    year = {2026},"
                     "\n    pages = {1--20}"
                     "\n}", "Article in a Collection", None),

                    ("@suppcollection", r"@suppcollection{key,"
                     "\n    title = {Supplement Title},"
                     "\n    booktitle = {Collection Title},"
                     "\n    year = {2026}"
                     "\n}", "Supplemental Material in a Collection", None),


                    # Conferences
                    ("@proceedings", r"@proceedings{key,"
                     "\n    title = {Proceedings Title},"
                     "\n    editor = {Editor Name},"
                     "\n    year = {2026},"
                     "\n    publisher = {Publisher}"
                     "\n}", "Conference Proceedings", None),

                    ("@mvproceedings", r"@mvproceedings{key,"
                     "\n    title = {Multi-volume Proceedings Title},"
                     "\n    editor = {Editor Name},"
                     "\n    year = {2026},"
                     "\n    publisher = {Publisher}"
                     "\n}", "Multi-volume Proceedings Entry", None),

                    ("@inproceedings", r"@inproceedings{key,"
                     "\n    author = {Author Name},"
                     "\n    title = {Paper Title},"
                     "\n    booktitle = {Conference Name},"
                     "\n    year = {2026},"
                     "\n    pages = {1--10}"
                     "\n}", "Article in Conference Proceedings", None),


                    # Reference Works
                    ("@reference", r"@reference{key,"
                     "\n    editor = {Editor Name},"
                     "\n    title = {Reference Title},"
                     "\n    year = {2026}"
                     "\n}", "Reference", None),

                    ("@mvreference", r"@mvreference{key,"
                     "\n    editor = {Editor Name},"
                     "\n    title = {Multi-volume Reference Title},"
                     "\n    year = {2026}"
                     "\n}", "Multi-volume Reference Entry", None),

                    ("@inreference", r"@inreference{key,"
                     "\n    author = {Author Name},"
                     "\n    title = {Entry Title},"
                     "\n    booktitle = {Reference Title},"
                     "\n    year = {2026}"
                     "\n}", "Article in a Reference", None),


                    # Reports & Manuals
                    ("@report", r"@report{key,"
                     "\n    author = {Author Name},"
                     "\n    title = {Report Title},"
                     "\n    institution = {Institution},"
                     "\n    year = {2026}"
                     "\n}", "Report", None),

                    ("@techreport", r"@techreport{key,"
                     "\n    author = {Author Name},"
                     "\n    title = {Technical Report Title},"
                     "\n    institution = {Institution},"
                     "\n    year = {2026},"
                     "\n    number = {TR-001}"
                     "\n}", "Technical Manual", None),

                    ("@manual", r"@manual{key,"
                     "\n    title = {Manual Title},"
                     "\n    author = {Organization},"
                     "\n    year = {2026}"
                     "\n}", "Manual", None),

                    ("@standard", r"@standard{key,"
                     "\n    title = {Standard Title},"
                     "\n    organization = {Organization},"
                     "\n    number = {ISO 9001},"
                     "\n    year = {2026}"
                     "\n}", "Standard", None),


                    # Theses & Academic
                    ("@phdthesis", r"@phdthesis{key,"
                     "\n    author = {Author Name},"
                     "\n    title = {Thesis Title},"
                     "\n    school = {University},"
                     "\n    year = {2026}"
                     "\n}", "PhD Thesis", None),

                    ("@mastersthesis", r"@mastersthesis{key,"
                     "\n    author = {Author Name},"
                     "\n    title = {Thesis Title},"
                     "\n    school = {University},"
                     "\n    year = {2026}"
                     "\n}", "Master’s Thesis", None),

                    ("@thesis", r"@thesis{key,"
                     "\n    author = {Author Name},"
                     "\n    title = {Thesis Title},"
                     "\n    school = {University},"
                     "\n    year = {2026},"
                     "\n    type = {Bachelor's Thesis}"
                     "\n}", "Thesis", None),

                    ("@unpublished", r"@unpublished{key,"
                     "\n    author = {Author Name},"
                     "\n    title = {Title},"
                     "\n    note = {Manuscript in preparation},"
                     "\n    year = {2026}"
                     "\n}", "Unpublished", None),


                    # Digital & Online
                    ("@online", r"@online{key,"
                     "\n    author = {Author Name},"
                     "\n    title = {Title},"
                     "\n    url = {https://example.com},"
                     "\n    urldate = {2024-01-01}"
                     "\n}", "Online Resource", None),

                    ("@preprint", r"@article{key,"
                     "\n    author = {Author Name},"
                     "\n    title = {Preprint Title},"
                     "\n    eprint = {arXiv:1234.5678},"
                     "\n    year = {2026}"
                     "\n}", "Preprint", None),

                    ("@dataset", r"@dataset{key,"
                     "\n    author = {Author Name},"
                     "\n    title = {Dataset Title},"
                     "\n    year = {2026},"
                     "\n    publisher = {Repository},"
                     "\n    doi = {10.1234/example}"
                     "\n}", "Dataset", None),

                    ("@software", r"@software{key,"
                     "\n    author = {Author Name},"
                     "\n    title = {Software Title},"
                     "\n    year = {2026},"
                     "\n    version = {1.0},"
                     "\n    url = {https://example.com}"
                     "\n}", "Software", None),

                    ("@presentation", r"@presentation{key,"
                     "\n    author = {Author Name},"
                     "\n    title = {Presentation Title},"
                     "\n    event = {Event Name},"
                     "\n    year = {2026}"
                     "\n}", "Presentation", None),


                    # Legal & Patents
                    ("@patent", r"@patent{key,"
                     "\n    author = {Inventor Name},"
                     "\n    title = {Patent Title},"
                     "\n    number = {US1234567},"
                     "\n    year = {2026}"
                     "\n}", "Patent", None),

                    ("@case", r"@case{key,"
                     "\n    title = {Case Title},"
                     "\n    court = {Court Name},"
                     "\n    year = {2026}"
                     "\n}", "Legal Document", None),


                    # Media & Creative
                    ("@map", r"@map{key,"
                     "\n    title = {Map Title},"
                     "\n    year = {2026},"
                     "\n    publisher = {Publisher}"
                     "\n}", "Map", None),

                    ("@artwork", r"@artwork{key,"
                     "\n    author = {Artist Name},"
                     "\n    title = {Artwork Title},"
                     "\n    year = {2026}"
                     "\n}", "Artwork", None),

                    ("@audio", r"@audio{key,"
                     "\n    author = {Artist Name},"
                     "\n    title = {Audio Title},"
                     "\n    year = {2026}"
                     "\n}", "Audio Recording", None),

                    ("@video", r"@video{key,"
                     "\n    author = {Director Name},"
                     "\n    title = {Video Title},"
                     "\n    year = {2026}"
                     "\n}", "Video Recording", None),


                    # Catch-all
                    ("@misc", r"@misc{key,"
                     "\n    author = {Author Name},"
                     "\n    title = {Title},"
                     "\n    howpublished = {\\url{https://example.com}},"
                     "\n    year = {2026}"
                     "\n}", "Miscellaneous", None),
                ]
            },       
            
            "Lists_Tables": {
                "tr" : tr["commands:lists"],
                "commands": [

                    # Contents & navigation
                    ("\\tableofcontents", r"\tableofcontents", "Table of contents", None),
                    ("\\listoffigures", r"\listoffigures", "List of figures", None),
                    ("\\listoftables", r"\listoftables", "List of tables", None),
                    ("\\addcontentsline{}", r"\addcontentsline{toc}{section}{Title}", "Add entry to TOC", None),
                    ("\\setcounter{}", r"\setcounter{tocdepth}{2}", "Set TOC depth", None),

                    # Page & line breaks
                    ("\\newpage", r"\newpage", "New page", None),
                    ("\\clearpage", r"\clearpage", "Clear page", None),
                    ("\\pagebreak", r"\pagebreak", "Page break", None),
                    ("\\nopagebreak", r"\nopagebreak", "Prevent page break", None),
                    ("\\linebreak", r"\linebreak", "Line break", None),
                    ("\\nolinebreak", r"\nolinebreak", "Prevent line break", None),
                    ("\\newline", r"\newline", "New line", None),
                    ("\\\\", r"\\", "Line break (forced)", None),
                    ("\\\\[1cm]", r"\\[1cm]", "Line break with space", None),

                    # Horizontal & vertical spacing
                    ("\\hspace{}", r"\hspace{1cm}", "Horizontal space", None),
                    ("\\hspace*{}", r"\hspace*{1cm}", "Forced horizontal space", None),
                    ("\\vspace{}", r"\vspace{1cm}", "Vertical space", None),
                    ("\\vspace*{}", r"\vspace*{1cm}", "Forced vertical space", None),
                    ("\\hfill", r"\hfill", "Horizontal fill", None),
                    ("\\vfill", r"\vfill", "Vertical fill", None),
                    ("\\dotfill", r"\dotfill", "Dot fill", None),
                    ("\\hrulefill", r"\hrulefill", "Rule fill", None),
                    ("\\quad", r"\quad", "Space = 1em", None),
                    ("\\qquad", r"\qquad", "Space = 2em", None),

                    # Lists
                    ("itemize", "\\begin{itemize}\n"  "\\item cursor\n"  "\item Item 2\n" "\item Item 3\n" "\\end{itemize}", "Bullet list", None),
                    ("enumerate", "\\begin{enumerate}\n"  "\\item cursor\n"  "\item Item 2\n" "\item Item 3\n" "\\end{enumerate}", "Numbered list", None),
                    ("description", "\\begin{description}\n"  "\\item[Term] cursor\n" "\item[Term] Description\n" "\item[Term] Description\n" "\\end{description}", "Description list", None),
                    #("\\item", r"\item", "List item", None),
                    ("\\setlength{}", r"\setlength{\itemsep}{0.5em}", "List spacing", None),
                    ("\\renewcommand{}", r"\renewcommand{\labelitemi}{$\bullet$}", "Change bullet symbol", None),
                    ("\\setcounter{}", r"\setcounter{enumi}{3}", "Set list counter", None),

                    # Tables
                    ("tabular", "\\begin{tabular}{|c|c|}\n"  "\\hline\n"  "A & B \\\\\n"  "\\hline\n\\end{tabular}", "Basic table", None),
                    ("table", "\\begin{table}[h]\n"  "\\centering\n"  "\\caption{Caption}\n"  "\\label{tab:label}\n\\end{table}", "Floating table", None),
                    ("\\hline", r"\hline", "Horizontal line", None),
                    ("\\cline{}", r"\cline{1-2}", "Partial horizontal line", None),
                    ("\\multicolumn{}", r"\multicolumn{2}{c}{cursor}", "Merge columns", None),
                    ("\\multirow{}", r"\multirow{2}{*}{cursor}", "Merge rows (multirow pkg)", None),
                    ("\\caption{}", r"\caption{Caption}", "Table caption", None),
                    ("\\label{}", r"\label{tab:label}", "Table label", None),
                    ("\\centering", r"\centering", "Center table", None),
                    ("\\raggedright", r"\raggedright", "Left align table", None),
                    ("\\raggedleft", r"\raggedleft", "Right align table", None),

                    # Column formatting
                    ("p{}", r"p{3cm}", "Fixed-width column", None),
                    ("m{}", r"m{3cm}", "Vertically centered column", None),
                    ("b{}", r"b{3cm}", "Bottom-aligned column", None),
                    ("@{}", r"@{ }", "Inter-column spacing", None),
                    ("|", r"|", "Vertical rule", None),

                    # Long / advanced tables
                    ("longtable", "\\begin{longtable}{|c|c|} \n"  "A & B \\\\\n" "\\end{longtable}", "Multi-page table", None),
                    ("tabularx", "\\begin{tabularx}{\\textwidth}{|X|X|} \n"  "A & B \\\\ \n" "\\end{tabularx}", "Auto-width table", None),
                    ("booktabs", r"\toprule ... \midrule ... \bottomrule", "Professional rules", None),
                    ("\\arraystretch", r"\renewcommand{\arraystretch}{1.2}", "Row height scaling", None),

                ]
            },          

            "Special_Characters": {
                "tr" : tr["commands:characters"],
                "commands": [

                    # Core escaped characters
                    ("&&", r"\&", "Ampersand", None),
                    ("%", r"\%", "Percent", None),
                    ("$", r"\$", "Dollar sign", None),
                    ("#", r"\#", "Hash / Number sign", None),
                    ("_", r"\_", "Underscore", None),
                    ("{", r"\{", "Left brace", None),
                    ("}", r"\}", "Right brace", None),
                    ("\\", r"\textbackslash", "Backslash", None),
                    ("^", r"\^{}", "Circumflex", None),
                    ("~", r"\~{}", "Tilde", None),

                    # Legal & commercial symbols
                    ("©", r"\copyright", "Copyright", None),
                    ("®", r"\textregistered", "Registered", None),
                    ("™", r"\trademark", "Trademark", None),
                    ("℠", r"\textservicemark", "Service mark", None),

                    # Typography & punctuation
                    ("…", r"\ldots", "Ellipsis", None),
                    ("–", r"\textendash", "En dash", None),
                    ("—", r"\textemdash", "Em dash", None),
                    ("«", r"\guillemotleft", "Left guillemet", None),
                    ("»", r"\guillemotright", "Right guillemet", None),
                    ("‹", r"\guilsinglleft", "Left single guillemet", None),
                    ("›", r"\guilsinglright", "Right single guillemet", None),
                    ("“", r"\textquotedblleft", "Left double quote", None),
                    ("”", r"\textquotedblright", "Right double quote", None),
                    ("‘", r"\textquoteleft", "Left single quote", None),
                    ("’", r"\textquoteright", "Right single quote", None),
                    ("„", r"\quotedblbase", "Low double quote", None),
                    ("‚", r"\quotesinglbase", "Low single quote", None),

                    # Sectioning & reference marks
                    ("§", r"\S", "Section sign", None),
                    ("¶", r"\P", "Paragraph sign", None),
                    ("†", r"\dag", "Dagger", None),
                    ("‡", r"\ddag", "Double dagger", None),
                    ("•", r"\textbullet", "Bullet", None),
                    ("°", r"\textdegree", "Degree sign", None),
                    ("‰", r"\textperthousand", "Per mille", None),
                    ("‱", r"\textpertenthousand", "Per ten thousand", None),

                    # Math-like text symbols
                    ("±", r"\textpm", "Plus–minus", None),
                    ("×", r"\texttimes", "Multiplication sign", None),
                    ("÷", r"\textdiv", "Division sign", None),
                    ("≤", r"\textleq", "Less-than or equal", None),
                    ("≥", r"\textgeq", "Greater-than or equal", None),
                    ("≠", r"\textneq", "Not equal", None),
                    ("≈", r"\textasciitilde", "Approximately equal", None),

                    # Currency symbols
                    ("€", r"\texteuro", "Euro", None),
                    ("£", r"\pounds", "Pound sterling", None),
                    ("¥", r"\textyen", "Yen", None),
                    ("¢", r"\textcent", "Cent", None),
                    ("₹", r"\textrupee", "Rupee", None),

                    # Miscellaneous useful
                    ("✓", r"\checkmark", "Check mark", None),
                    ("✗", r"\xmark", "Cross mark", None),
                    ("∞", r"\infty", "Infinity", None),
                    ("∑", r"\sum", "Summation", None),
                    ("∏", r"\prod", "Product", None),
                    ("∂", r"\partial", "Partial derivative", None),
                    ("∇", r"\nabla", "Nabla", None),
                    ("→", r"\rightarrow", "Right arrow", None),
                    ("←", r"\leftarrow", "Left arrow", None),
                    ("↔", r"\leftrightarrow", "Left-right arrow", None),
                    ("⇒", r"\Rightarrow", "Double right arrow", None),
                    ("⇐", r"\Leftarrow", "Double left arrow", None),
                    ("⇔", r"\Leftrightarrow", "Double left-right arrow", None),

                ]
            },
            
            "Layout_Spacing": {
                "tr" : tr["commands:layout"],
                "commands": [

                    # Document structure
                    ("\\documentclass{}", r"\documentclass[12pt]{cursor}", "Document class", None),
                    ("\\usepackage{}", r"\usepackage{cursor}", "Use package", None),
                    ("\\title{}", r"\title{cursor}", "Document title", None),
                    ("\\subtitle{}", r"\subtitle{cursor}", "Document subtitle", None),
                    ("\\author{}", r"\author{cursor}", "Document author", None),
                    ("\\date{}", r"\date{\today}", "Document date", None),
                    ("\\maketitle", r"\maketitle", "Make title", None),
                    ("\\abstract", "\\begin{abstract}\n"    "cursor\n" "\\end{abstract}", "Abstract", None),
                    ("\\appendix", r"\appendix", "Appendix", None),
                    ("\\tableofcontents", r"\tableofcontents", "Table of contents", None),
                    ("\\listoffigures", r"\listoffigures", "List of figures", None),
                    ("\\listoftables", r"\listoftables", "List of tables", None),

                    # File inclusion
                    ("\\include{}", r"\include{cursor}", "Include file", None),
                    ("\\input{}", r"\input{cursor}", "Input file", None),
                    ("\\includegraphics{}", r"\includegraphics[width=0.8\textwidth]{cursor}", "Include graphics", None),

                    # Page geometry & dimensions
                    ("\\textwidth", r"\textwidth", "Text width", None),
                    ("\\textheight", r"\textheight", "Text height", None),
                    ("\\linewidth", r"\linewidth", "Line width", None),
                    ("\\columnwidth", r"\columnwidth", "Column width", None),
                    ("\\pagewidth", r"\pagewidth", "Page width", None),
                    ("\\paperwidth", r"\paperwidth", "Paper width", None),
                    ("\\paperheight", r"\paperheight", "Paper height", None),
                    ("\\oddsidemargin", r"\oddsidemargin", "Odd side margin", None),
                    ("\\evensidemargin", r"\evensidemargin", "Even side margin", None),
                    ("\\topmargin", r"\topmargin", "Top margin", None),
                    ("\\headheight", r"\headheight", "Header height", None),
                    ("\\headsep", r"\headsep", "Header separation", None),
                    ("\\footskip", r"\footskip", "Footer separation", None),

                    # Spacing (horizontal & vertical)
                    ("\\hspace{}", r"\hspace{1cm}", "Horizontal space", None),
                    ("\\hspace*{}", r"\hspace*{1cm}", "Forced horizontal space", None),
                    ("\\vspace{}", r"\vspace{1cm}", "Vertical space", None),
                    ("\\vspace*{}", r"\vspace*{1cm}", "Forced vertical space", None),
                    ("\\smallskip", r"\smallskip", "Small vertical skip", None),
                    ("\\medskip", r"\medskip", "Medium vertical skip", None),
                    ("\\bigskip", r"\bigskip", "Big vertical skip", None),
                    ("\\quad", r"\quad", "Space = 1em", None),
                    ("\\qquad", r"\qquad", "Space = 2em", None),
                    ("\\,", r"\,", "Thin space", None),
                    ("\\:", r"\:", "Medium space", None),
                    ("\\;", r"\;", "Thick space", None),
                    ("\\!", r"\!", "Negative thin space", None),
                    ("\\enspace", r"\enspace", "En space", None),
                    ("\\enskip", r"\enskip", "En skip", None),
                    ("\\hfill", r"\hfill", "Horizontal fill", None),
                    ("\\vfill", r"\vfill", "Vertical fill", None),
                    ("\\stretch{}", r"\stretch{1}", "Stretchable space", None),

                    # Line & paragraph spacing
                    ("\\linespread{}", r"\linespread{1.3}", "Line spread factor", None),
                    ("\\baselineskip", r"\baselineskip", "Baseline skip", None),
                    ("\\parskip", r"\parskip", "Paragraph skip", None),
                    ("\\parindent", r"\parindent", "Paragraph indent", None),
                    ("\\noindent", r"\noindent", "No paragraph indent", None),
                    ("\\indent", r"\indent", "Force indent", None),
                    ("\\raggedright", r"\raggedright", "Ragged right", None),
                    ("\\raggedleft", r"\raggedleft", "Ragged left", None),
                    ("\\centering", r"\centering", "Center alignment", None),
                    ("\\flushleft", r"\flushleft", "Flush left", None),
                    ("\\flushright", r"\flushright", "Flush right", None),

                    # Page breaks & layout control
                    ("\\newpage", r"\newpage", "New page", None),
                    ("\\clearpage", r"\clearpage", "Clear page (flush floats)", None),
                    ("\\pagebreak", r"\pagebreak", "Suggest page break", None),
                    ("\\nopagebreak", r"\nopagebreak", "Prevent page break", None),
                    ("\\linebreak", r"\linebreak", "Suggest line break", None),
                    ("\\nolinebreak", r"\nolinebreak", "Prevent line break", None),
                    ("\\sloppy", r"\sloppy", "Looser spacing", None),
                    ("\\fussy", r"\fussy", "Normal spacing", None),

                    # Geometry package helpers
                    ("\\geometry{}", r"\geometry{margin=2.5cm}", "Set page geometry", None),
                    ("\\newgeometry{}", r"\newgeometry{margin=2cm}", "Change geometry", None),
                    ("\\restoregeometry", r"\restoregeometry", "Restore geometry", None),

                    # Columns & layout modes
                    ("\\onecolumn", r"\onecolumn", "Single column", None),
                    ("\\twocolumn", r"\twocolumn", "Two columns", None),
                    ("\\columnsep", r"\columnsep", "Column separation", None),
                    ("\\columnseprule", r"\columnseprule", "Column separation rule", None),

                ]
            },
            
        }
    
               
    def create_comprehensive_menu(self, parent_menu):
        """Create comprehensive math symbols menu"""
       
        for category_key, category_data in self.sectionning_categories.items():
            category_name = category_data["tr"]
            category_menu = parent_menu.addMenu(category_name)
            
           
            for item in category_data["commands"]:
                if len(item) == 3:
                    symbol_display, latex_code, description = item
                    package = None
                else:
                    symbol_display, latex_code, description, package = item

                action_text = description
                action = QAction(action_text, self.main_window)

                tooltip = f"<b>{description}</b><br>"
                tooltip += f"Symbol: {symbol_display}<br>"
                tooltip += f"LaTeX: <code>{latex_code}</code>"

                if package:
                    tooltip += f"<br><span style='color:gray;'>Requires: <code>{package}</code></span>"

                action.setToolTip(tooltip)

                action.triggered.connect(lambda checked, code=latex_code: self.insert_callback(code))
                #action.setIcon(self.create_symbol_icon(symbol_display))

                category_menu.addAction(action)                
