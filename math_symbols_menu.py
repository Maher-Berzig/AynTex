# math_symbols_menu.py
"""
Math Symbols Menu - Enhanced with Text Selection Handler integration
"""

from PyQt5.QtWidgets import QAction, QMenu
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QPainter, QFont, QIcon


class MathSymbolsMenu:
    def __init__(self, main_window, insert_callback, language="en"):
        self.main_window = main_window
        self.insert_callback = insert_callback
        self.menu_language = language
        self.build_symbol_categories()

    def build_symbol_categories(self):   
        """Build/rebuild symbol categories with current language translations"""        
        lang = self.main_window.menu_language
        tr = self.main_window.translations[lang]        
        # Mathematical symbols organized by category
        # Updated with proper cursor positioning and delimiter handling
        self.symbol_categories = {
            "basic_operations": {
                "tr" : tr["symbols:basic_operations"],
                "symbols": [
                    ("+", "+", "Plus", None),
                    ("-", "-", "Minus", None),
                    ("×", r"\times", "Multiplication", None),
                    ("÷", r"\div", "Division", None),
                    ("±", r"\pm", "Plus-minus", None),
                    ("∓", r"\mp", "Minus-plus", None),
                    ("a/b", r"\frac{cursor}{#}", "Fraction", None),
                    ("a^b", r"^{cursor}", "Superscript", None),
                    ("a_b", r"_{cursor}", "Subscript", None),
                    ("√", r"\sqrt{cursor}", "Square root", None),
                    ("∛", r"\sqrt[3]{cursor}", "Cube root", None),
                    ("ⁿ√", r"\sqrt[n]{cursor}", "Nth root", None),
                    #("∞", r"\infty", "Infinity", None),                    
                    
                    ("á", r"\acute{cursor}", "Acute Accent", None),
                    ("à", r"\grave{cursor}", "Grave Accent", None),
                    ("ǎ", r"\check{cursor}", "Check Accent", None),
                    ("^", r"\hat{cursor}", "Hat Accent", None),
                    ("~", r"\tilde{cursor}", "Tilde Accent", None),
                    ("¯", r"\bar{cursor}", "Bar Accent", None),
                    ("→", r"\vec{cursor}", "Vector Accent", None),
                    ("˘", r"\breve{cursor}", "Breve Accent", None),
                    ("˙", r"\dot{cursor}", "Dot Accent", None),
                    ("¨", r"\ddot{cursor}", "Double Dot Accent", None),
                    ("˚", r"\mathring{cursor}", "Ring Accent", None),
                    
                    
                    ("~", r"\widetilde{cursor}", "Tilde Accent", None),
                    ("^", r"\widehat{cursor}", "Hat Accent", None),
                    ("←", r"\overleftarrow{cursor}", "Over Left Arrow", None),
                    ("‾", r"\overline{cursor}", "Overline", None),
                    ("_", r"\underline{cursor}", "Underline", None),
                    ("⏞", r"\overbrace{cursor}", "Overbrace", None),
                    ("⏟", r"\underbrace{cursor}", "Underbrace", None),
                    ("↔", r"\overleftrightarrow{cursor}", "Over Double Arrow", None),
                    ("↔", r"\underleftrightarrow{cursor}", "Under Double Arrow", None),
                    ("←", r"\underleftarrow{cursor}", "Under Left Arrow", None),
                    ("⇒", r"\xRightarrow{cursor}", "Extensible Right Arrow", None),
                    #("=", r"\stackrel{cursor}{#}", "Stacked Relation", None),
                    ("◌̅", r"\overset{cursor}{=}", "Overset", r"\usepackage{amsmath}"),                    
                    ("◌̲", r"\underset{cursor}{=}", "Underset", r"\usepackage{amsmath}"),
                    
                    ("⋅", r"\cdot", "Center dot", None),
                    ("…", r"\ldots", "Baseline three dots", None),
                    ("⋯", r"\cdots", "Center three dots", None),
                    ("⋱", r"\ddotd", "Diagonal three dots", None),
                    ("*", r"\ast", "Asterisk", None),
                    ("∗", r"\star", "Start", None),
                    ("∘", r"\circ", "Composition", None),
                    ("●", r"\bullet", "Bullet", None),
                    ("⋄", r"\diamond", "Diamond", None),
                    ("⃝", r"\bigcirc", "Big circle", None),
                    ("⊕", r"\oplus", "Direct sum", None),
                    ("⊖", r"\ominus", "Direct minus", None),
                    ("⊘", r"\oslash", "Direct division", None),
                    ("⊗", r"\otimes", "Tensor product", None),
                    ("⊙", r"\odot", "Dot product", None),
                    ("⊚", r"\circledcirc", "Circled Ring Operator",  r"\usepackage{amssymb}"),
                    ("⊝", r"\circleddash", "Circled Dash",  r"\usepackage{amssymb}"),
                    ("⊛", r"\circledast", "Circled Asterisk Operator",  r"\usepackage{amssymb}"),
                ]
            },
            "functions": {
                "tr" : tr["symbols:functions"],                
                "symbols": [
                    ("sin", r"\sin{cursor}", "Sinus", None),
                    ("cos", r"\cos{cursor}", "Cosinus", None),
                    ("tan", r"\tan{cursor}", "Tangent", None),
                    ("cot", r"\cot{cursor}", "Cotangent", None),
                    ("sec", r"\sec{cursor}", "Secant", None),
                    ("csc", r"\csc{cursor}", "Cosecant", None),
                    ("arcsin", r"\arcsin{cursor}", "Arcsine", None),
                    ("arccos", r"\arccos{cursor}", "Arccosine", None),
                    ("arctan", r"\arctan{cursor}", "Arctangent", None),
                    ("arccot", r"\arccot{cursor}", "Arccotangent", None),
                    ("sinh", r"\sinh{cursor}", "Hyperbolic Sinus", None),
                    ("cosh", r"\cosh{cursor}", "Hyperbolic Cosinus", None),
                    ("tanh", r"\tanh{cursor}", "Hyperbolic Tangent", None),
                    ("coth", r"\coth{cursor}", "Hyperbolic Cotangent", None),
                    ("log", r"\log{cursor}", "Logarithm", None),
                    ("ln", r"\ln{cursor}", "Natural Logarithm", None),
                    ("exp", r"\exp{cursor}", "Exponential", None),
                    ("lim", r"\lim{cursor}", "Limit", None),
                    ("sup", r"\sup{cursor}", "Supremum", None),
                    ("inf", r"\inf{cursor}", "Infimum", None),                    
                    ("min", r"\min{cursor}", "Minimum", None),
                    ("max", r"\max{cursor}", "Maximum", None),                    
                    ("deg", r"\deg{cursor}", "Degree", None),
                    ("det", r"\det{cursor}", "Determinant", None), 
                    ("ker", r"\ker{cursor}", "Kernel", None),
                    ("dim", r"\dim{cursor}", "Dimension", None), 
                    ("hom", r"\hom{cursor}", "Homomorphism", None),
                    ("arg", r"\arg{cursor}", "Argument", None),                     
                    ("gcd", r"\gcd{cursor}", "Greatest Common Divisor", None), 
                    ("lcm", r"\lcm{cursor}", "least common multiple", None),
                    ("Pr", r"\Pr{cursor}", "Probability", None),
                    ("Re", r"\Re{cursor}", "Real Part", None),
                    ("Im", r"\Im{cursor}", "Imaginary Part", None),
                    ("abs", r"\left|{cursor}\right|", "Absolute Value", None),
                    ("floor", r"\lfloor{cursor}\rfloor", "Floor", None),
                    ("ceil", r"\lceil{cursor}\rceil", "Ceiling", None),                   
                    
                ]
            },                       
            "relations": {
                "tr" : tr["symbols:relations"],
                "ar": "العلاقات",
                "symbols": [
                    ("=", r"=", "Equals", None),
                    ("≍", r"\asymp", "Asymptotic", None),
                    ("≈", r"\approx", "Approximately equal", None),
                    ("≅", r"\cong", "Congruent", None),
                    ("≡", r"\equiv", "Identical", None),
                    ("∼", r"\sim", "Similar", None),
                    ("∝", r"\propto", "Proportional", None),
                    ("⋉", r"\ltimes", "Left Normal Factor Semidirect Product", r"\usepackage{amssymb}"),
                    
                    ("<", r"<", "Less than", None),
                    (">", r">", "Greater than", None),
                    ("≤", r"\leq", "Less than or equal", None),
                    ("≥", r"\geq", "Greater than or equal", None),
                    ("≦", r"\leqq", "Less than over equal", r"\usepackage{amssymb}"),
                    ("≧", r"\geqq", "Greater than over equal", r"\usepackage{amssymb}"),
                    ("⩽", r"\leqslant", "Less than or slanted equal", r"\usepackage{amssymb}"),
                    ("⩾", r"\geqslant", "Greater than or slanted equal", r"\usepackage{amssymb}"),
                    ("⪕", r"\eqslantless", "Slanted Equal to or Less than", r"\usepackage{amssymb}"),
                    ("⪖", r"\eqslantgtr", "Slanted Equal to or Greater than", r"\usepackage{amssymb}"),
                    ("≶", r"\lessgtr", "Less-Than or Greater-Than", r"\usepackage{amssymb}"),
                    ("≷", r"\gtrless", "Greater-Than or Less-Than", r"\usepackage{amssymb}"),
                    ("⋚", r"\lesseqgtr", "Less-than or Equal to or Greater-than", r"\usepackage{amssymb}"),
                    ("⋛", r"\gtreqless", "Greater-than or Equal to or Less-than", r"\usepackage{amssymb}"),
                    ("⪋", r"\lesseqqgtr", "Less-than over Equal to or Greater-than", r"\usepackage{amssymb}"),
                    ("⪌", r"\gtreqqless", "Greater-than over Equal to or Less-than", r"\usepackage{amssymb}"),
                    ("≲", r"\lesssim", "Less-than or Similar to", r"\usepackage{amssymb}"),
                    ("≳", r"\gtrsim", "Greater-than or Similar to", r"\usepackage{amssymb}"),
                    ("⪅", r"\lessapprox", "Less-than or Approximately Equal", r"\usepackage{amssymb}"),
                    ("⪆", r"\gtrapprox", "Greater-than or Approximately Equal", r"\usepackage{amssymb}"),                
                    ("≪", r"\ll", "Much less than", None),
                    ("≫", r"\gg", "Much greater than", None),
                    ("⋘", r"\lll", "Very much less than", None),
                    ("⋙", r"\ggg", "Very much greater than", None),                    
                    ("≺", r"\prec", "Prec", None),
                    ("≻", r"\succ", "Succ", None),
                    ("⪯", r"\preceq", "Prec  or equal", None),
                    ("⪰", r"\succeq", "Succ  or equal", None),   
                    
                    ("∈", r"\in", "Element of", None),
                    ("∋", r"\ni", "Contains", None),                    
                    ("⊂", r"\subset", "Subset", None),
                    ("⊃", r"\supset", "Superset", None),
                    ("⊆", r"\subseteq", "Subset or equal", None),
                    ("⊇", r"\supseteq", "Superset or equal", None),
                    ("⫅", r"\subseteqq", "Subset or Equal (double equals)", r"\usepackage{amssymb}"),
                    ("⫆", r"\supseteqq", "Superset or Equal (double equals)", r"\usepackage{amssymb}"),                    
                    ("⋐", r"\Subset", "Double Subset", r"\usepackage{amssymb}"),
                    ("⋑", r"\Supset", "Double Supset", r"\usepackage{amssymb}"),
                    ("⊏", r"\sqsubset", "Square Subset", r"\usepackage{amssymb}"),
                    ("⊐", r"\sqsupset", "Square Supset", r"\usepackage{amssymb}"),
                    ("⊑", r"\sqsubseteq", "Square Subset or Equal", r"\usepackage{amssymb}"),                    
                    ("⊒", r"\sqsupseteq", "Square Supset or Equal", r"\usepackage{amssymb}"), 

                    ("⊲", r"\lhd", "Normal Subgroup Of", r"\usepackage{amssymb}"),
                    ("⊳", r"\rhd", "Contains as Normal Subgroup", r"\usepackage{amssymb}"),
                    ("⊴", r"\unlhd", "Normal Subgroup of or Equal To", r"\usepackage{amssymb}"),
                    ("⊵", r"\unrhd", "Contains as Normal Subgroup or Equal To", r"\usepackage{amssymb}"),                    

                    ("⊥", r"\perp", "Perpendicular", None),
                    ("∥", r"\parallel", "Parallel", None)
                ]
            },
            "negated_relations": {
                "tr" : tr["symbols:negated_relations"],
                "symbols": [
                    ("≠", r"\neq", "Not equal", None),
                    ("≭", r"\nasymp", "Not asymptotic", None),
                    ("≉", r"\napprox", "Not approximately equal", None),
                    ("≇", r"\ncong", "Not congruent", None),
                    ("≢", r"\not\equiv", "Not identical", None),
                    ("≁", r"\nsim", "Not similar", None),                    
                    ("∝̸", r"\not\propto", "Not proportional", None),
                    
                    ("≮", r"\nless", "Not less than", None),
                    ("≯", r"\ngtr", "Not greater than", None),
                    ("≰", r"\nleq", "Not less than or equal", None),
                    ("≱", r"\ngeq", "Not greater than or equal", None),
                    ("⪇", r"\nleqslant", "Not less than or slanted equal", r"\usepackage{amssymb}"),
                    ("⪈", r"\ngeqslant", "Not greater than or slanted equal", r"\usepackage{amssymb}"),
                    ("≨", r"\nleqq", "Not less than over equal", r"\usepackage{amssymb}"),
                    ("≩", r"\ngeqq", "Not greater than over equal", r"\usepackage{amssymb}"),

                    ("≸", r"\nlessgtr", "Not less-than or greater-than", r"\usepackage{amssymb}"),
                    ("≹", r"\ngtrless", "Not greater-than or less-than", r"\usepackage{amssymb}"),

                    ("⋦", r"\lnsim", "Not less-than or similar", r"\usepackage{amssymb}"),
                    ("⋧", r"\gnsim", "Not greater-than or similar", r"\usepackage{amssymb}"),
                    ("⪉", r"\nlessapprox", "Not less-than or approximately equal", r"\usepackage{amssymb}"),
                    ("⪊", r"\ngtrapprox", "Not greater-than or approximately equal", r"\usepackage{amssymb}"),

                    ("⊀", r"\nprec", "Not prec", None),
                    ("⊁", r"\nsucc", "Not succ", None),
                    ("⋠", r"\npreceq", "Not prec or equal", None),
                    ("⋡", r"\nsucceq", "Not succ or equal", None),

                    ("∉", r"\notin", "Not element of", None),
                    ("∌", r"\nni", "Not contains", None),

                    ("⊄", r"\nsubset", "Not subset", None),
                    ("⊅", r"\nsupset", "Not superset", None),
                    ("⊈", r"\nsubseteq", "Not subset or equal", None),
                    ("⊉", r"\nsupseteq", "Not superset or equal", None),
                    ("⫋", r"\nsubseteqq", "Not subset or equal (double equals)", r"\usepackage{amssymb}"),
                    ("⫌", r"\nsupseteqq", "Not superset or equal (double equals)", r"\usepackage{amssymb}"),
                    ("⫋", r"\subsetneqq", "Subset of or not equal (double equals)", r"\usepackage{amssymb}"),
                    ("⫌", r"\supsetneqq", "Superset of or not equal (double equals)", r"\usepackage{amssymb}"),
                    
                    #("⊈̸", r"\not\Subset", "Not double subset", r"\usepackage{amssymb}"),
                    #("⊉̸", r"\not\Supset", "Not double superset", r"\usepackage{amssymb}"),
                    
                    ("⋢", r"\nsqsubseteq", "Not square subset or equal", r"\usepackage{amssymb}"),
                    ("⋣", r"\nsqsupseteq", "Not square superset or equal", r"\usepackage{amssymb}"),

                    ("⋪", r"\ntrianglelef", "Not normal subgroup of", r"\usepackage{amssymb}"),
                    ("⋫", r"\ntriangleright", "Not contains as normal subgroup", r"\usepackage{amssymb}"),
                    ("⋬", r"\ntrianglelefteq", "Not normal subgroup or equal", r"\usepackage{amssymb}"),
                    ("⋭", r"\ntrianglerighteq", "Not contains as normal subgroup or equal", r"\usepackage{amssymb}"),

                    ("⊥̸", r"\not\perp", "Not perpendicular", None),
                    ("∦", r"\nparallel", "Not parallel", None)
                ]
            },
            "greek_letters": {
                "tr" : tr["symbols:greek_letters"],
                "symbols": [
                    ("α", r"\alpha", "Alpha", None),
                    ("β", r"\beta", "Beta", None),
                    ("γ", r"\gamma", "Gamma", None),
                    ("δ", r"\delta", "Delta", None),
                    ("ε", r"\varepsilon", "varEpsilon", None),
                    ("ε", r"\epsilon", "Epsilon", None),                    
                    ("ζ", r"\zeta", "Zeta", None),
                    ("η", r"\eta", "Eta", None),
                    ("θ", r"\theta", "Theta", None),
                    ("θ", r"\vartheta", "varTheta", None),
                    ("ι", r"\iota", "Iota", None),
                    ("κ", r"\kappa", "Kappa", None),
                    ("λ", r"\lambda", "Lambda", None),
                    ("μ", r"\mu", "Mu", None),
                    ("ν", r"\nu", "Nu", None),
                    ("ξ", r"\xi", "Xi", None),
                    ("π", r"\pi", "Pi", None),
                    ("ρ", r"\rho", "Rho", None),
                    ("σ", r"\sigma", "Sigma", None),
                    ("τ", r"\tau", "Tau", None),
                    ("υ", r"\upsilon", "Upsilon", None),
                    ("φ", r"\phi", "phi", None),
                    ("𝜑", r"\varphi", "varphi", None),
                    ("χ", r"\chi", "Chi", None),
                    ("ψ", r"\psi", "Psi", None),
                    ("ω", r"\omega", "Omega", None),
                    ("Γ", r"\Gamma", "Capital Gamma", None),
                    ("Δ", r"\Delta", "Capital Delta", None),
                    ("Θ", r"\Theta", "Capital Theta", None),
                    ("Λ", r"\Lambda", "Capital Lambda", None),
                    ("Ξ", r"\Xi", "Capital Xi", None),
                    ("Π", r"\Pi", "Capital Pi", None),
                    ("Σ", r"\Sigma", "Capital Sigma", None),
                    ("Φ", r"\Phi", "Capital Phi", None),
                    ("Ψ", r"\Psi", "Capital Psi", None),
                    ("Ω", r"\Omega", "Capital Omega", None),
                    ("Y", r"\Upsilon", "Capital Upsilon", None),
                ]
            },
            "calculus": {
                "tr" : tr["symbols:calculus"],            
                "symbols": [
                    ("∂", r"\partial", "Partial derivative", None),
                    ("∇", r"\nabla", "Nabla", None),
                    ("△", r"\bigtriangleup", "Laplacian", None),
                    ("∫", r"\int_{a}^{b}{cursor}{\rm d}x", "Integral", None),
                    ("∬", r"\iint", "Double integral", None),
                    ("∭", r"\iiint", "Triple integral", None),
                    ("∮", r"\oint", "Contour integral", None),
                    ("∞", r"\infty", "Infinity", None),
                    ("lim", r"\lim_{n\to\infty}{cursor}", "Limit", None),
                    ("ℓ", r"\ell", "Script Small L", None),
                    ("ℒ", r"\mathscr{L}", "Script Capital L", r"\usepackage{mathrsfs}"),
                    ("∑", r"\sum_{k=0}^{\infty}", "Summation", None),
                    ("∏", r"\prod_{k=0}^{\infty}", "Product", None),
                    ("∐", r"\coprod_{k=0}^{\infty}", "Coproduct", None)
                ]
            },
            "logic": {
                "tr" : tr["symbols:logic"],                        
                "symbols": [
                    ("¬", r"\neg", "Not", None),
                    ("∧", r"\land", "And", None),
                    ("∨", r"\lor", "Or", None),
                    ("≡", r"\equiv", "Identical", None),
                    ("→", r"\to", "Implies", None),
                    ("↔", r"\leftrightarrow", "If and only if", None),
                    ("⇒", r"\implies", "Implies", None),
                    ("⇔", r"\iff", "If and only if", None),
                    ("∀", r"\forall", "For all", None),
                    ("∃", r"\exists", "There exists", None),
                    ("∄", r"\nexists", "Does not exist", None),
                    ("⊢", r"\vdash", "Proves", None),
                    ("⊨", r"\models", "Models", None),
                    ("⊤", r"\top", "True", None),
                    ("⊥", r"\bot", "False", None),
                    ("∴", r"\therefore", "Therefore", r"\usepackage{amssymb}"),
                    ("∵", r"\because", "Because", r"\usepackage{amssymb}"),
                    ("⊕", r"\oplus", "Direct sum", None),
                ]
            },
            "sets": {
                "tr" : tr["symbols:sets"],                 
                "symbols": [
                    ("∅", r"\emptyset", "Empty set", None),
                    ("∪", r"\cup", "Union", None),
                    ("∩", r"\cap", "Intersection", None),
                    ("∖", r"\setminus", "Set minus", None),
                    ("△", r"\triangle", "Up triangle", None),
                    ("▷", r"\triangleleft", "Left triangle", None),
                    ("◁", r"\triangleright", "Right triangle", None),
                    ("▽", r"\triangledown", "Down triangle", None),
                    ("⊂", r"\subset", "Subset", None),
                    ("⊃", r"\supset", "Superset", None),
                    ("⊆", r"\subseteq", "Subset or equal", None),
                    ("⊇", r"\supseteq", "Superset or equal", None),
                    ("∈", r"\in", "Element of", None),
                    ("∉", r"\notin", "Not element of", None),
                    ("ℕ", r"\mathbb{N}", "Natural numbers", None),
                    ("ℤ", r"\mathbb{Z}", "Integers", None),
                    ("ℚ", r"\mathbb{Q}", "Rational numbers", None),
                    ("ℝ", r"\mathbb{R}", "Real numbers", None),
                    ("ℂ", r"\mathbb{C}", "Complex numbers", None)
                ]
            },
            "arrows": {
                "tr" : tr["symbols:arrows"],              
                "symbols": [
                    ("←", r"\leftarrow", "Left arrow", None),
                    ("→", r"\rightarrow", "Right arrow", None),
                    ("↑", r"\uparrow", "Up arrow", None),
                    ("↓", r"\downarrow", "Down arrow", None),
                    ("↔", r"\leftrightarrow", "Left-right arrow", None),
                    ("↕", r"\updownarrow", "Up-down arrow", None),
                    ("⇐", r"\Leftarrow", "Left double arrow", None),
                    ("⇒", r"\Rightarrow", "Right double arrow", None),
                    ("⇑", r"\Uparrow", "Up double arrow", None),
                    ("⇓", r"\Downarrow", "Down double arrow", None),
                    ("⇔", r"\Leftrightarrow", "Left-right double arrow", None),
                    ("⇕", r"\Updownarrow", "Up-down double arrow", None),
                    ("↗", r"\nearrow", "Northeast arrow", None),
                    ("↘", r"\searrow", "Southeast arrow", None),
                    ("↙", r"\swarrow", "Southwest arrow", None),
                    ("↖", r"\nwarrow", "Northwest arrow", None),
                    ("↦", r"\mapsto", "Maps to", None),
                    ("↪", r"\hookrightarrow", "Hook right arrow", None),
                    ("↩", r"\hookleftarrow", "Hook left arrow", None),
                ]
            },
            "environments": {
                "tr" : tr["symbols:environments"],                   
                "symbols": [
                    ("Equation", "\\begin{equation}\label{eq:1}\n" "\n\\end{equation}", "Numbered equation", None),
                    ("Cases", "\\begin{cases}\n" ", & \\text{if }  \\\\ \n" ", & \\text{otherwise}\n" "\\end{cases}", "Cases", None),
                    ("Equation*", "\\begin{equation*}\n" "\n\\end{equation*}", "Not numbered equation", None),
                    ("Enumerate", "\\begin{enumerate}\n" "\item \n"  "\item \n"  "\item \n" "\\end{enumerate}", "Enumerate list", None),
                    ("Itemize", "\\begin{itemize}\n" "\item \n"  "\item \n"  "\item \n" "\\end{itemize}", "Itemize list", None),
                    ("Align", "\\begin{align}\n" " &=  \\\\ \n" " &= \n\\end{align}", "Align equations", None),
                    ("Array", "\\begin{array}{cc}\n" " &  \\\\ \n" " & \n" "\\end{array}", "Array", None),    
                    ("Tabular", "\\begin{tabular}{|c|c|}\\hline\n" " &  \\\\ \\hline\n" " & \\hline\n" "\\end{tabular}", "Tabular", None),                    
                    ("Matrix", "\\begin{matrix}\n" " &  \\\\ \n" " & \n" "\\end{matrix}", "Matrix", None),                    
                    ("Pmatrix", "\\begin{pmatrix}\n"  " &  \\\\ \n"  " & \n\\end{pmatrix}", "Parentheses matrix", None),
                    ("Bmatrix", "\\begin{bmatrix}\n"  " &  \\\\ \n"  " & \n\\end{bmatrix}", "Bracket matrix", None),
                    ("Vmatrix", "\\begin{vmatrix}\n"  " &  \\\\ \n"  " & \n\\end{vmatrix}", "Determinant", None),
                    ("Split", "\\begin{split}\n" " &=  \\\\ \n " "&\quad + \n" "\\end{split}", "Split equation", None),
                    ("Minipage", "\\begin{minipage}[<pos:t,c,b>][<height>][<inner-pos:t,c,b,s>]{<width>}\n" " \n" "\\end{minipage}", "Minipage", None),
                    ("Quotation", "\\begin{quotation}\n" " \n" "\\end{quotation}", "Quotation", None),
                    ("Quote", "\\begin{quote}\n" " \n" "\\end{quote}", "Quote", None),
                    ("Verse", "\\begin{verse}\n" " \n" "\\end{verse}", "Verse", None),
                    ("New", "\\(re)newenvironment{<env-name>}[<n-args>][<default>]{<begin-code>}{<end-code>}", "New environment", None),
                ]
            },
            "delimiters": {
                "tr" : tr["symbols:delimiters"],                   
                "symbols": [
                    ("( )", r"(cursor)", "Parentheses", None),
                    ("[ ]", r"[cursor]", "Square brackets", None),
                    ("{ }", r"\{cursor\}", "Curly braces", None),
                    ("⟨ ⟩", r"\langle cursor \rangle", "Angle brackets", None),
                    ("| |", r"|cursor|", "Vertical bars", None),
                    ("‖ ‖", r"\|cursor\|", "Double vertical bars", None),
                    ("⌊ ⌋", r"\lfloor cursor \rfloor", "Floor", None),
                    ("⌈ ⌉", r"\lceil cursor \rceil", "Ceiling", None),
                    ("/", r"\left/ cursor \right\\", "Forward/backward slash", None),
                    ("(*)", r"\left(cursor\right)", "Scalable parentheses", None),
                    ("[*]", r"\left[cursor\right]", "Scalable brackets", None),
                    ("{*}", r"\left\{cursor\right\}", "Scalable braces", None),
                    ("|*|", r"\left|cursor\right|", "Scalable bars", None),
                ]
            }
        }



    # def create_symbol_icon(self, symbol, size=18):
        # pixmap = QPixmap(size, size)
        # pixmap.fill(Qt.transparent)

        # painter = QPainter(pixmap)

        # font = QFont("DejaVu Sans", int(size * 0.45))  # good math support
        # painter.setFont(font)
        # painter.setPen(Qt.black)

        # painter.drawText(pixmap.rect(), Qt.AlignCenter, symbol)
        # painter.end()

        # return QIcon(pixmap)
    
    # def create_comprehensive_menu(self, parent_menu):
        # """Create comprehensive math symbols menu - NO direction calls"""
        # for category_key, category_data in self.symbol_categories.items():
            # category_name = category_data["tr"]
            # category_menu = parent_menu.addMenu(category_name)
            # # ✅ No setLayoutDirection here at all

            # for item in category_data["symbols"]:
                # if len(item) == 3:
                    # symbol_display, latex_code, description = item
                    # package = None
                # else:
                    # symbol_display, latex_code, description, package = item

                # action = QAction(description, self.main_window)
                # tooltip = f"<b>{description}</b><br>"
                # tooltip += f"Symbol: {symbol_display}<br>"
                # tooltip += f"LaTeX: <code>{latex_code}</code>"
                # if package:
                    # tooltip += f"<br><span style='color:gray;'>Requires: <code>{package}</code></span>"
                # action.setToolTip(tooltip)
                # action.triggered.connect(
                    # lambda checked, code=latex_code: self.insert_callback(code)
                # )
                # if category_key != "environments":
                    # action.setIcon(self.create_symbol_icon(symbol_display))
                # category_menu.addAction(action)  



    def create_symbol_icon(self, symbol, width=24, height=24, alignment=Qt.AlignCenter, font_size=None):
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        try:
            if font_size is None:
                font_size = int(min(width, height) * 0.45)
            font = QFont("DejaVu Sans", font_size)
            painter.setFont(font)
            painter.setPen(Qt.black)
            if alignment & Qt.AlignLeft:
                margin = max(1, width // 8)
                rect = pixmap.rect().adjusted(margin, 0, 0, 0)
            else:
                rect = pixmap.rect()
            painter.drawText(rect, alignment, symbol)
        finally:
            painter.end()
        return QIcon(pixmap)
    
    def create_comprehensive_menu(self, parent_menu):
        for category_key, category_data in self.symbol_categories.items():
            category_name = category_data["tr"]
            category_menu = parent_menu.addMenu(category_name)

            for item in category_data["symbols"]:
                if len(item) == 3:
                    symbol_display, latex_code, description = item
                    package = None
                else:
                    symbol_display, latex_code, description, package = item

                action = QAction(description, self.main_window)
                tooltip = f"<b>{description}</b><br>"
                tooltip += f"Symbol: {symbol_display}<br>"
                tooltip += f"LaTeX: <code>{latex_code}</code>"
                if package:
                    tooltip += f"<br><span style='color:gray;'>Requires: <code>{package}</code></span>"
                action.setToolTip(tooltip)
                action.triggered.connect(
                    lambda checked, code=latex_code: self.insert_callback(code)
                )

                if category_key != "environments":
                    if category_key == "functions":
                        icon = self.create_symbol_icon(
                            symbol_display,
                            width=24, height=24,
                            alignment=Qt.AlignLeft | Qt.AlignVCenter,
                            font_size=7          # small font so "arcsin" fits in 24px
                        )
                    else:
                        icon = self.create_symbol_icon(symbol_display)
                    action.setIcon(icon)

                category_menu.addAction(action)