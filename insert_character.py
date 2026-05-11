# insert_character.py
"""
Insert Character Tab - STIX Two Math, Pifont (Dingbats) and FontAwesome symbol insertion
"""
import sys
import os
import struct
from PyQt5.QtWidgets import (
    QApplication, QWidget, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QHBoxLayout, QHeaderView, QMessageBox,
    QTabWidget, QPushButton, QFrame, QScrollArea, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFontDatabase, QFont, QResizeEvent, QIcon


def _insert_text_into_editor(main_window, text):
    try:
        if hasattr(main_window, 'editor_manager'):
            active_editor = main_window.editor_manager.get_active_editor()
            if active_editor:
                cursor = active_editor.textCursor()
                cursor.insertText(text)
                active_editor.setFocus()
                main_window.editor_manager.on_text_changed()
                #print(f"✅ Inserted: {text[:60]}{'...' if len(text) > 60 else ''}")
            else:
                QMessageBox.warning(None, "Warning", "No active editor found!")
        else:
            QMessageBox.warning(None, "Warning", "Editor manager not available!")
    except Exception as e:
        QMessageBox.critical(None, "Error", f"Failed to insert text:\n{str(e)}")


# ============================================================
# STIX TWO MATH SYMBOLS DATABASE
# Replace this dict with the full version from the separate symbols file
# ============================================================
STIX_SYMBOLS = {
    # ─── 5.1 Alphabetics ────────────────────────────────────────
    0x0393: "Gamma",       0x0394: "Delta",       0x0398: "Theta",
    0x039B: "Lambda",      0x039E: "Xi",          0x03A0: "Pi",
    0x03A3: "Sigma",       0x03A5: "Upsilon",     0x03A6: "Phi",
    0x03A8: "Psi",         0x03A9: "Omega",
    0x03B1: "alpha",       0x03B2: "beta",        0x03B3: "gamma",
    0x03B4: "delta",       0x03B5: "epsilon",     0x03B6: "zeta",
    0x03B7: "eta",         0x03B8: "theta",       0x03B9: "iota",
    0x03BA: "kappa",       0x03BB: "lambda",      0x03BC: "mu",
    0x03BD: "nu",          0x03BE: "xi",          0x03C0: "pi",
    0x03C1: "rho",         0x03C3: "sigma",       0x03C4: "tau",
    0x03C5: "upsilon",     0x03D5: "phi",         0x03C7: "chi",
    0x03C8: "psi",         0x03C9: "omega",       0x03F5: "varepsilon",
    0x03D1: "vartheta",    0x03D6: "varpi",       0x03F1: "varrho",
    0x03C2: "varsigma",    0x03C6: "varphi",
    0x2207: "nabla",       0x2202: "partial",
    # ─── 5.2 Ordinary Symbols ──────────────────────────────────
    0x00AC: "neg",         0x00F0: "eth",         0x01B5: "Zbar",
    0x03DD: "digamma",     0x03F0: "varkappa",    0x03F6: "backepsilon",
    0x2025: "enleadertwodots", 0x2026: "mathellipsis",
    0x2032: "prime",       0x2033: "dprime",      0x2034: "trprime",
    0x2035: "backprime",   0x2036: "backdprime",  0x2037: "backtrprime",
    0x2038: "caretinsert", 0x203C: "Exclam",      0x2043: "hyphenbullet",
    0x2047: "Question",    0x2057: "qprime",
    0x20DD: "enclosecircle", 0x20DE: "enclosesquare", 0x20DF: "enclosediamond",
    0x20E4: "enclosetriangle", 0x2107: "Eulerconst",
    0x210F: "hslash",      0x2111: "Im",          0x2113: "ell",
    0x2118: "wp",          0x211C: "Re",          0x2127: "mho",
    0x2129: "turnediota",  0x212B: "Angstrom",    0x2132: "Finv",
    0x2135: "aleph",       0x2136: "beth",        0x2137: "gimel",
    0x2138: "daleth",      0x2141: "Game",        0x2142: "sansLturned",
    0x2143: "sansLmirrored", 0x2144: "Yup",       0x214A: "PropertyLine",
    # Ordinary: forall/exists/emptyset/etc
    0x2200: "forall",      0x2201: "complement",  0x2203: "exists",
    0x2204: "nexists",     0x2205: "emptyset",    0x2206: "increment",
    0x220E: "QED",         0x221E: "infty",       0x221F: "rightangle",
    0x2220: "angle",       0x2221: "measuredangle", 0x2222: "sphericalangle",
    0x2234: "therefore",   0x2235: "because",     0x223F: "sinewave",
    0x22A4: "top",         0x22A5: "bot",         0x22B9: "hermitmatrix",
    0x22BE: "measuredrightangle", 0x22BF: "varlrtriangle",
    0x22EF: "cdots",
    # Ordinary: shapes
    0x2300: "diameter",    0x2302: "house",       0x2310: "invnot",
    0x2311: "sqlozenge",   0x2312: "profline",    0x2313: "profsurf",
    0x2317: "viewdata",    0x2319: "turnednot",   0x232C: "varhexagonlrbonds",
    0x2332: "conictaper",  0x2336: "topbot",      0x2340: "APLnotbackslash",
    0x2353: "APLboxupcaret", 0x2370: "APLboxquestion",
    0x237C: "rangledownzigzagarrow", 0x2394: "hexagon",
    0x23B6: "bbrktbrk",    0x23CE: "varcarriagereturn",
    0x23E0: "obrbrak",     0x23E1: "ubrbrak",     0x23E2: "trapezium",
    0x23E3: "benzenr",     0x23E4: "strns",       0x23E5: "fltns",
    0x23E6: "accurrent",   0x23E7: "elinters",    0x2423: "mathvisiblespace",
    # Ordinary: geometric shapes
    0x25A0: "blacksquare", 0x25A1: "square",      0x25A2: "squoval",
    0x25A3: "blackinwhitesquare", 0x25A4: "squarehfill",
    0x25A5: "squarevfill", 0x25A6: "squarehvfill",
    0x25A7: "squarenwsefill", 0x25A8: "squareneswfill",
    0x25A9: "squarecrossfill", 0x25AA: "smblksquare",
    0x25AB: "smwhtsquare", 0x25AC: "hrectangleblack",
    0x25AD: "hrectangle",  0x25AE: "vrectangleblack",
    0x25AF: "vrectangle",  0x25B0: "parallelogramblack",
    0x25B1: "parallelogram", 0x25B2: "bigblacktriangleup",
    0x25B4: "blacktriangle", 0x25B5: "vartriangle",
    0x25B6: "blacktriangleright", 0x25B8: "smallblacktriangleright",
    0x25B9: "smalltriangleright", 0x25BA: "blackpointerright",
    0x25BB: "whitepointerright", 0x25BC: "bigblacktriangledown",
    0x25BD: "bigtriangledown", 0x25BE: "blacktriangledown",
    0x25BF: "triangledown", 0x25C0: "blacktriangleleft",
    0x25C2: "smallblacktriangleleft", 0x25C3: "smalltriangleleft",
    0x25C4: "blackpointerleft", 0x25C5: "whitepointerleft",
    0x25C6: "mdlgblkdiamond", 0x25C7: "mdlgwhtdiamond",
    0x25C8: "blackinwhitediamond", 0x25C9: "fisheye",
    0x25CA: "lozenge",     0x25CC: "dottedcircle",
    0x25CD: "circlevertfill", 0x25CE: "bullseye",
    0x25CF: "mdlgblkcircle", 0x25D0: "circlelefthalfblack",
    0x25D1: "circlerighthalfblack", 0x25D2: "circlebottomhalfblack",
    0x25D3: "circletophalfblack", 0x25D4: "circleurquadblack",
    0x25D5: "blackcircleulquadwhite", 0x25D6: "blacklefthalfcircle",
    0x25D7: "blackrighthalfcircle", 0x25D8: "inversebullet",
    0x25D9: "inversewhitecircle", 0x25DA: "invwhiteupperhalfcircle",
    0x25DB: "invwhitelowerhalfcircle",
    0x25DC: "ularc",       0x25DD: "urarc",
    0x25DE: "lrarc",       0x25DF: "llarc",
    0x25E0: "topsemicircle", 0x25E1: "botsemicircle",
    0x25E2: "lrblacktriangle", 0x25E3: "llblacktriangle",
    0x25E4: "ulblacktriangle", 0x25E5: "urblacktriangle",
    0x25E6: "smwhtcircle", 0x25E7: "squareleftblack",
    0x25E8: "squarerightblack", 0x25E9: "squareulblack",
    0x25EA: "squarelrblack", 0x25EC: "trianglecdot",
    0x25ED: "triangleleftblack", 0x25EE: "trianglerightblack",
    0x25EF: "lgwhtcircle",
    0x25F0: "squareulquad", 0x25F1: "squarellquad",
    0x25F2: "squarelrquad", 0x25F3: "squareurquad",
    0x25F4: "circleulquad", 0x25F5: "circlellquad",
    0x25F6: "circlelrquad", 0x25F7: "circleurquad",
    0x25F8: "ultriangle",  0x25F9: "urtriangle",
    0x25FA: "lltriangle",  0x25FB: "mdwhtsquare",
    0x25FC: "mdblksquare", 0x25FD: "mdsmwhtsquare",
    0x25FE: "mdsmblksquare", 0x25FF: "lrtriangle",
    # Ordinary: misc symbols
    0x2605: "bigstar",     0x2606: "bigwhitestar", 0x2609: "astrosun",
    0x2621: "danger",      0x263B: "blacksmiley",  0x263C: "sun",
    0x263D: "rightmoon",   0x263E: "leftmoon",
    0x2640: "female",      0x2642: "male",
    0x2660: "spadesuit",   0x2661: "heartsuit",
    0x2662: "diamondsuit", 0x2663: "clubsuit",
    0x2664: "varspadesuit", 0x2665: "varheartsuit",
    0x2666: "vardiamondsuit", 0x2667: "varclubsuit",
    0x2669: "quarternote", 0x266A: "eighthnote",  0x266B: "twonotes",
    0x266D: "flat",        0x266E: "natural",     0x266F: "sharp",
    0x267E: "acidfree",
    0x2680: "dicei",       0x2681: "diceii",      0x2682: "diceiii",
    0x2683: "diceiv",      0x2684: "dicev",       0x2685: "dicevi",
    0x2686: "circledrightdot", 0x2687: "circledtwodots",
    0x2688: "blackcircledrightdot", 0x2689: "blackcircledtwodots",
    0x26A5: "Hermaphrodite", 0x26AA: "mdwhtcircle",
    0x26AB: "mdblkcircle", 0x26AC: "mdsmwhtcircle", 0x26B2: "neuter",
    0x2713: "checkmark",   0x2720: "maltese",     0x272A: "circledstar",
    0x2736: "varstar",     0x273D: "dingasterisk", 0x279B: "draftingarrow",
    0x27C0: "threedangle", 0x27C1: "whiteinwhitetriangle",
    0x27C3: "subsetcirc",  0x27C4: "supsetcirc",
    0x27CB: "diagup",      0x27CD: "diagdown",    0x27D0: "diamondcdot",
    # Ordinary: angle variants
    0x292B: "rdiagovfdiag", 0x292C: "fdiagovrdiag",
    0x292D: "seovnearrow", 0x292E: "neovsearrow",
    0x292F: "fdiagovnearrow", 0x2930: "rdiagovsearrow",
    0x2931: "neovnwarrow", 0x2932: "nwovnearrow",
    0x2934: "uprightcurvearrow", 0x2935: "downrightcurvedarrow",
    0x2981: "mdsmblkcircle", 0x2999: "fourvdots",  0x299A: "vzigzag",
    0x299B: "measuredangleleft", 0x299C: "rightanglesqr",
    0x299D: "rightanglemdot", 0x299E: "angles",    0x299F: "angdnr",
    0x29A0: "gtlpar",      0x29A1: "sphericalangleup",
    0x29A2: "turnangle",   0x29A3: "revangle",
    0x29A4: "angleubar",   0x29A5: "revangleubar",
    0x29A6: "wideangledown", 0x29A7: "wideangleup",
    0x29A8: "measanglerutone", 0x29A9: "measanglelutonw",
    0x29AA: "measanglerdtose", 0x29AB: "measangleldtosw",
    0x29AC: "measangleurtone", 0x29AD: "measangleultonw",
    0x29AE: "measangledrtose", 0x29AF: "measangledltosw",
    0x29B0: "revemptyset", 0x29B1: "emptysetobar",
    0x29B2: "emptysetocirc", 0x29B3: "emptysetoarr",
    0x29B4: "emptysetoarrl", 0x29BA: "obot",       0x29BB: "olcross",
    0x29BC: "odotslashdot", 0x29BD: "uparrowoncircle",
    0x29BE: "circledwhitebullet", 0x29BF: "circledbullet",
    0x29C2: "cirscir",     0x29C3: "cirE",        0x29C9: "boxonbox",
    0x29CA: "triangleodot", 0x29CB: "triangleubar", 0x29CC: "triangles",
    0x29DC: "iinfin",      0x29DD: "tieinfty",    0x29DE: "nvinfty",
    0x29E0: "laplac",      0x29E7: "thermod",
    0x29E8: "downtriangleleftblack", 0x29E9: "downtrianglerightblack",
    0x29EA: "blackdiamonddownarrow", 0x29EB: "blacklozenge",
    0x29EC: "circledownarrow", 0x29ED: "blackcircledownarrow",
    0x29EE: "errbarsquare", 0x29EF: "errbarblacksquare",
    0x29F0: "errbardiamond", 0x29F1: "errbarblackdiamond",
    0x29F2: "errbarcircle", 0x29F3: "errbarblackcircle",
    0x2AE1: "perps",       0x2AF1: "topcir",
    # Ordinary: 2Bxx shapes
    0x2B12: "squaretopblack", 0x2B13: "squarebotblack",
    0x2B14: "squareurblack", 0x2B15: "squarellblack",
    0x2B16: "diamondleftblack", 0x2B17: "diamondrightblack",
    0x2B18: "diamondtopblack", 0x2B19: "diamondbotblack",
    0x2B1A: "dottedsquare", 0x2B1B: "lgblksquare",
    0x2B1C: "lgwhtsquare", 0x2B1D: "vysmblksquare",
    0x2B1E: "vysmwhtsquare", 0x2B1F: "pentagonblack",
    0x2B20: "pentagon",    0x2B21: "varhexagon",
    0x2B22: "varhexagonblack", 0x2B23: "hexagonblack",
    0x2B24: "lgblkcircle", 0x2B25: "mdblkdiamond",
    0x2B26: "mdwhtdiamond", 0x2B27: "mdblklozenge",
    0x2B28: "mdwhtlozenge", 0x2B29: "smblkdiamond",
    0x2B2A: "smblklozenge", 0x2B2B: "smwhtlozenge",
    0x2B2C: "blkhorzoval", 0x2B2D: "whthorzoval",
    0x2B2E: "blkvertoval", 0x2B2F: "whtvertoval",
    0x2B50: "medwhitestar", 0x2B51: "medblackstar", 0x2B52: "smwhitestar",
    0x2B53: "rightpentagonblack", 0x2B54: "rightpentagon",
    0x3012: "postalmark",  0x3030: "hzigzag",

    # ─── 5.3 Binary Operators ──────────────────────────────────
    0x00B1: "pm",          0x00B7: "centerdot",   0x00D7: "times",
    0x00F7: "div",         0x2020: "dagger",      0x2021: "ddagger",
    0x2044: "fracslash",   0x214B: "upand",       0x2213: "mp",
    0x2214: "dotplus",     0x2216: "smallsetminus", 0x2217: "ast",
    0x2218: "vysmwhtcircle", 0x2219: "bullet",    0x2227: "wedge",
    0x2228: "vee",         0x2229: "cap",         0x222A: "cup",
    0x2238: "dotminus",    0x223E: "invlazys",    0x2240: "wr",
    0x228C: "cupleftarrow", 0x228D: "cupdot",     0x228E: "uplus",
    0x2293: "sqcap",       0x2294: "sqcup",       0x2295: "oplus",
    0x2296: "ominus",      0x2297: "otimes",      0x2298: "oslash",
    0x2299: "odot",        0x229A: "circledcirc", 0x229B: "circledast",
    0x229C: "circledequal", 0x229D: "circleddash",
    0x229E: "boxplus",     0x229F: "boxminus",    0x22A0: "boxtimes",
    0x22A1: "boxdot",      0x22BA: "intercal",    0x22BB: "veebar",
    0x22BC: "barwedge",    0x22BD: "barvee",      0x22C4: "diamond",
    0x22C5: "cdot",        0x22C6: "star",        0x22C7: "divideontimes",
    0x22C9: "ltimes",      0x22CA: "rtimes",
    0x22CB: "leftthreetimes", 0x22CC: "rightthreetimes",
    0x22CE: "curlyvee",    0x22CF: "curlywedge",
    0x22D2: "Cap",         0x22D3: "Cup",
    0x2305: "varbarwedge", 0x2306: "vardoublebarwedge",
    0x233D: "obar",        0x25B3: "triangle",
    0x22B2: "lhd",         0x22B3: "rhd",         0x22B4: "unlhd",
    0x22B5: "unrhd",       0x25CB: "mdlgwhtcircle", 0x25EB: "boxbar",
    0x27C7: "veedot",      0x27D1: "wedgedot",    0x27E0: "lozengeminus",
    0x27E1: "concavediamond",
    0x27E2: "concavediamondtickleft", 0x27E3: "concavediamondtickright",
    0x27E4: "whitesquaretickleft", 0x27E5: "whitesquaretickright",
    0x2982: "typecolon",   0x29B5: "circlehbar",  0x29B6: "circledvert",
    0x29B7: "circledparallel", 0x29B8: "obslash",  0x29B9: "operp",
    0x29C0: "olessthan",   0x29C1: "ogreaterthan",
    0x29C4: "boxdiag",     0x29C5: "boxbslash",   0x29C6: "boxast",
    0x29C7: "boxcircle",   0x29C8: "boxbox",
    0x29CD: "triangleserifs", 0x29D6: "hourglass", 0x29D7: "blackhourglass",
    0x29E2: "shuffle",     0x29F5: "setminus",
    0x29F6: "dsol",        0x29F7: "rsolbar",
    0x29FA: "doubleplus",  0x29FB: "tripleplus",
    0x29FE: "tplus",       0x29FF: "tminus",
    0x2A22: "ringplus",    0x2A23: "plushat",      0x2A24: "simplus",
    0x2A25: "plusdot",     0x2A26: "plussim",      0x2A27: "plussubtwo",
    0x2A28: "plustrif",    0x2A29: "commaminus",   0x2A2A: "minusdot",
    0x2A2B: "minusfdots",  0x2A2C: "minusrdots",
    0x2A2D: "opluslhrim",  0x2A2E: "oplusrhrim",  0x2A2F: "vectimes",
    0x2A30: "dottimes",    0x2A31: "timesbar",     0x2A32: "btimes",
    0x2A33: "smashtimes",  0x2A34: "otimeslhrim",  0x2A35: "otimesrhrim",
    0x2A36: "otimeshat",   0x2A37: "Otimes",       0x2A38: "odiv",
    0x2A39: "triangleplus", 0x2A3A: "triangleminus", 0x2A3B: "triangletimes",
    0x2A3C: "intprod",     0x2A3D: "intprodr",     0x2A3E: "fcmp",
    0x2A3F: "amalg",       0x2A40: "capdot",       0x2A41: "uminus",
    0x2A42: "barcup",      0x2A43: "barcap",       0x2A44: "capwedge",
    0x2A45: "cupvee",      0x2A46: "cupovercap",   0x2A47: "capovercup",
    0x2A48: "cupbarcap",   0x2A49: "capbarcup",    0x2A4A: "twocups",
    0x2A4B: "twocaps",     0x2A4C: "closedvarcup", 0x2A4D: "closedvarcap",
    0x2A4E: "Sqcap",       0x2A4F: "Sqcup",        0x2A50: "closedvarcupsmashprod",
    0x2A51: "wedgeodot",   0x2A52: "veeodot",      0x2A53: "Wedge",
    0x2A54: "Vee",         0x2A55: "wedgeonwedge", 0x2A56: "veeonvee",
    0x2A57: "bigslopedvee", 0x2A58: "bigslopedwedge",
    0x2A5A: "wedgemidvert", 0x2A5B: "veemidvert",
    0x2A5C: "midbarwedge", 0x2A5D: "midbarvee",   0x2A5E: "doublebarwedge",
    0x2A5F: "wedgebar",    0x2A60: "wedgedoublebar", 0x2A61: "varveebar",
    0x2A62: "doublebarvee", 0x2A63: "veedoublebar",
    0x2A64: "dsub",        0x2A65: "rsub",
    0x2A71: "eqqplus",     0x2A72: "pluseqq",
    0x2AF4: "interleave",  0x2AF5: "nhVvert",     0x2AF6: "threedotcolon",
    0x2AFB: "trslash",     0x2AFD: "sslash",      0x2AFE: "talloblong",
    # ─── 5.4 Relations ──────────────────────────────────────────
    0x2190: "leftarrow",   0x2191: "uparrow",     0x2192: "rightarrow",
    0x2193: "downarrow",   0x2194: "leftrightarrow", 0x2195: "updownarrow",
    0x2196: "nwarrow",     0x2197: "nearrow",     0x2198: "searrow",
    0x2199: "swarrow",     0x219A: "nleftarrow",  0x219B: "nrightarrow",
    0x219C: "leftwavearrow", 0x219D: "rightwavearrow",
    0x219E: "twoheadleftarrow", 0x219F: "twoheaduparrow",
    0x21A0: "twoheadrightarrow", 0x21A1: "twoheaddownarrow",
    0x21A2: "leftarrowtail", 0x21A3: "rightarrowtail",
    0x21A4: "mapsfrom",    0x21A5: "mapsup",      0x21A6: "mapsto",
    0x21A7: "mapsdown",    0x21A9: "hookleftarrow", 0x21AA: "hookrightarrow",
    0x21AB: "looparrowleft", 0x21AC: "looparrowright",
    0x21AD: "leftrightsquigarrow", 0x21AE: "nleftrightarrow",
    0x21AF: "downzigzagarrow",
    0x21B0: "Lsh",         0x21B1: "Rsh",         0x21B2: "Ldsh",
    0x21B3: "Rdsh",        0x21B6: "curvearrowleft", 0x21B7: "curvearrowright",
    0x21BC: "leftharpoonup", 0x21BD: "leftharpoondown",
    0x21BE: "upharpoonright", 0x21BF: "upharpoonleft",
    0x21C0: "rightharpoonup", 0x21C1: "rightharpoondown",
    0x21C2: "downharpoonright", 0x21C3: "downharpoonleft",
    0x21C4: "rightleftarrows", 0x21C5: "updownarrows",
    0x21C6: "leftrightarrows", 0x21C7: "leftleftarrows",
    0x21C8: "upuparrows",  0x21C9: "rightrightarrows",
    0x21CA: "downdownarrows", 0x21CB: "leftrightharpoons",
    0x21CC: "rightleftharpoons",
    0x21CD: "nLeftarrow",  0x21CE: "nLeftrightarrow", 0x21CF: "nRightarrow",
    0x21D0: "Leftarrow",   0x21D1: "Uparrow",     0x21D2: "Rightarrow",
    0x21D3: "Downarrow",   0x21D4: "Leftrightarrow", 0x21D5: "Updownarrow",
    0x21D6: "Nwarrow",     0x21D7: "Nearrow",     0x21D8: "Searrow",
    0x21D9: "Swarrow",     0x21DA: "Lleftarrow",  0x21DB: "Rrightarrow",
    0x21DC: "leftsquigarrow", 0x21DD: "rightsquigarrow",
    0x21E4: "barleftarrow", 0x21E5: "rightarrowbar",
    0x21F4: "circleonrightarrow", 0x21F5: "downuparrows",
    0x21F6: "rightthreearrows", 0x21F7: "nvleftarrow",
    0x21F8: "nvrightarrow", 0x21F9: "nvleftrightarrow",
    0x21FA: "nVleftarrow", 0x21FB: "nVrightarrow", 0x21FC: "nVleftrightarrow",
    0x21FD: "leftarrowtriangle", 0x21FE: "rightarrowtriangle",
    0x21FF: "leftrightarrowtriangle",
    0x2940: "circlearrowleft", 0x2941: "circlearrowright",
    0x2208: "in",          0x2209: "notin",       0x220A: "smallin",
    0x220B: "ni",          0x220C: "nni",         0x220D: "smallni",
    0x221D: "propto",      0x2223: "mid",         0x2224: "nmid",
    0x2225: "parallel",    0x2226: "nparallel",   0x2237: "Colon",
    0x2239: "dashcolon",   0x223A: "dotsminusdots", 0x223B: "kernelcontraction",
    0x223C: "sim",         0x223D: "backsim",     0x2241: "nsim",
    0x2242: "eqsim",       0x2243: "simeq",       0x2244: "nsime",
    0x2245: "cong",        0x2246: "simneqq",     0x2247: "ncong",
    0x2248: "approx",      0x2249: "napprox",     0x224A: "approxeq",
    0x224B: "approxident", 0x224C: "backcong",    0x224D: "asymp",
    0x224E: "Bumpeq",      0x224F: "bumpeq",      0x2250: "doteq",
    0x2251: "Doteq",       0x2252: "fallingdotseq", 0x2253: "risingdotseq",
    0x2254: "coloneq",     0x2255: "eqcolon",     0x2256: "eqcirc",
    0x2257: "circeq",      0x2258: "arceq",       0x2259: "wedgeq",
    0x225A: "veeeq",       0x225B: "stareq",      0x225C: "triangleq",
    0x225D: "eqdef",       0x225E: "measeq",      0x225F: "questeq",
    0x2260: "ne",          0x2261: "equiv",       0x2262: "nequiv",
    0x2263: "Equiv",       0x2264: "leq",         0x2265: "geq",
    0x2266: "leqq",        0x2267: "geqq",        0x2268: "lneqq",
    0x2269: "gneqq",       0x226A: "ll",          0x226B: "gg",
    0x226C: "between",     0x226D: "nasymp",      0x226E: "nless",
    0x226F: "ngtr",        0x2270: "nleq",        0x2271: "ngeq",
    0x2272: "lesssim",     0x2273: "gtrsim",      0x2274: "nlesssim",
    0x2275: "ngtrsim",     0x2276: "lessgtr",     0x2277: "gtrless",
    0x2278: "nlessgtr",    0x2279: "ngtrless",    0x227A: "prec",
    0x227B: "succ",        0x227C: "preccurlyeq", 0x227D: "succcurlyeq",
    0x227E: "precsim",     0x227F: "succsim",     0x2280: "nprec",
    0x2281: "nsucc",       0x2282: "subset",      0x2283: "supset",
    0x2284: "nsubset",     0x2285: "nsupset",     0x2286: "subseteq",
    0x2287: "supseteq",    0x2288: "nsubseteq",   0x2289: "nsupseteq",
    0x228A: "subsetneq",   0x228B: "supsetneq",   0x228F: "sqsubset",
    0x2290: "sqsupset",    0x2291: "sqsubseteq",  0x2292: "sqsupseteq",
    0x22A2: "vdash",       0x22A3: "dashv",       0x22A6: "assert",
    0x22A7: "models",      0x22A8: "vDash",       0x22A9: "Vdash",
    0x22AA: "Vvdash",      0x22AB: "VDash",       0x22AC: "nvdash",
    0x22AD: "nvDash",      0x22AE: "nVdash",      0x22AF: "nVDash",
    0x22B0: "prurel",      0x22B1: "scurel",
    0x22B2: "vartriangleleft", 0x22B3: "vartriangleright",
    0x22B4: "trianglelefteq", 0x22B5: "trianglerighteq",
    0x22B6: "origof",      0x22B7: "imageof",     0x22B8: "multimap",
    0x22C8: "bowtie",      0x22CD: "backsimeq",   0x22D0: "Subset",
    0x22D1: "Supset",      0x22D4: "pitchfork",   0x22D5: "equalparallel",
    0x22D6: "lessdot",     0x22D7: "gtrdot",      0x22D8: "lll",
    0x22D9: "ggg",         0x22DA: "lesseqgtr",   0x22DB: "gtreqless",
    0x22DC: "eqless",      0x22DD: "eqgtr",
    0x22DE: "curlyeqprec", 0x22DF: "curlyeqsucc",
    0x22E0: "npreccurlyeq", 0x22E1: "nsucccurlyeq",
    0x22E2: "nsqsubseteq", 0x22E3: "nsqsupseteq",
    0x22E4: "sqsubsetneq", 0x22E5: "sqsupsetneq",
    0x22E6: "lnsim",       0x22E7: "gnsim",
    0x22E8: "precnsim",    0x22E9: "succnsim",
    0x22EA: "nvartriangleleft", 0x22EB: "nvartriangleright",
    0x22EC: "ntrianglelefteq", 0x22ED: "ntrianglerighteq",
    0x22EE: "vdots",       0x22F0: "adots",       0x22F1: "ddots",
    0x22F2: "disin",       0x22F3: "varisins",    0x22F4: "isins",
    0x22F5: "isindot",     0x22F6: "varisinobar", 0x22F7: "isinobar",
    0x22F8: "isinvb",      0x22F9: "isinE",       0x22FA: "nisd",
    0x22FB: "varnis",      0x22FC: "nis",         0x22FD: "varniobar",
    0x22FE: "niobar",      0x22FF: "bagmember",
    0x2322: "frown",       0x2323: "smile",       0x233F: "APLnotslash",
    0x27C2: "perp",        0x27C8: "bsolhsub",    0x27C9: "suphsol",
    0x27D2: "upin",        0x27D3: "pullback",    0x27D4: "pushout",
    0x27DA: "DashVDash",   0x27DB: "dashVdash",   0x27DC: "multimapinv",
    0x27DD: "vlongdash",   0x27DE: "longdashv",   0x27DF: "cirbot",
    0x27F0: "UUparrow",    0x27F1: "DDownarrow",
    0x27F2: "acwgapcirclearrow", 0x27F3: "cwgapcirclearrow",
    0x27F4: "rightarrowonoplus",
    0x27F5: "longleftarrow", 0x27F6: "longrightarrow",
    0x27F7: "longleftrightarrow", 0x27F8: "Longleftarrow",
    0x27F9: "Longrightarrow", 0x27FA: "Longleftrightarrow",
    0x27FB: "longmapsfrom", 0x27FC: "longmapsto",
    0x27FD: "Longmapsfrom", 0x27FE: "Longmapsto",
    0x27FF: "longrightsquigarrow",
    # Relations: 29xx
    0x29CE: "rtriltri",    0x29CF: "ltrivb",      0x29D0: "vbrtri",
    0x29D1: "lfbowtie",    0x29D2: "rfbowtie",    0x29D3: "fbowtie",
    0x29D4: "lftimes",     0x29D5: "rftimes",     0x29DF: "dualmap",
    0x29E1: "lrtriangleeq", 0x29E3: "eparsl",     0x29E4: "smeparsl",
    0x29E5: "eqvparsl",    0x29E6: "gleichstark", 0x29F4: "ruledelayed",
    # Relations: 2Axx
    0x2A59: "veeonwedge",  0x2A66: "eqdot",       0x2A67: "dotequiv",
    0x2A68: "equivVert",   0x2A69: "equivVvert",  0x2A6A: "dotsim",
    0x2A6B: "simrdots",    0x2A6C: "simminussim", 0x2A6D: "congdot",
    0x2A6E: "asteq",       0x2A6F: "hatapprox",   0x2A70: "approxeqq",
    0x2A73: "eqqsim",      0x2A74: "Coloneq",     0x2A75: "eqeq",
    0x2A76: "eqeqeq",      0x2A77: "ddotseq",     0x2A78: "equivDD",
    0x2A79: "ltcir",       0x2A7A: "gtcir",       0x2A7B: "ltquest",
    0x2A7C: "gtquest",     0x2A7D: "leqslant",    0x2A7E: "geqslant",
    0x2A7F: "lesdot",      0x2A80: "gesdot",      0x2A81: "lesdoto",
    0x2A82: "gesdoto",     0x2A83: "lesdotor",    0x2A84: "gesdotol",
    0x2A85: "lessapprox",  0x2A86: "gtrapprox",   0x2A87: "lneq",
    0x2A88: "gneq",        0x2A89: "lnapprox",    0x2A8A: "gnapprox",
    0x2A8B: "lesseqqgtr",  0x2A8C: "gtreqqless",  0x2A8D: "lsime",
    0x2A8E: "gsime",       0x2A8F: "lsimg",       0x2A90: "gsiml",
    0x2A91: "lgE",         0x2A92: "glE",         0x2A93: "lesges",
    0x2A94: "gesles",      0x2A95: "eqslantless", 0x2A96: "eqslantgtr",
    0x2A97: "elsdot",      0x2A98: "egsdot",      0x2A99: "eqqless",
    0x2A9A: "eqqgtr",      0x2A9B: "eqqslantless", 0x2A9C: "eqqslantgtr",
    0x2A9D: "simless",     0x2A9E: "simgtr",      0x2A9F: "simlE",
    0x2AA0: "simgE",       0x2AA1: "Lt",          0x2AA2: "Gt",
    0x2AA3: "partialmeetcontraction",
    0x2AA4: "glj",         0x2AA5: "gla",         0x2AA6: "ltcc",
    0x2AA7: "gtcc",        0x2AA8: "lescc",       0x2AA9: "gescc",
    0x2AAA: "smt",         0x2AAB: "lat",         0x2AAC: "smte",
    0x2AAD: "late",        0x2AAE: "bumpeqq",     0x2AAF: "preceq",
    0x2AB0: "succeq",      0x2AB1: "precneq",     0x2AB2: "succneq",
    0x2AB3: "preceqq",     0x2AB4: "succeqq",     0x2AB5: "precneqq",
    0x2AB6: "succneqq",    0x2AB7: "precapprox",  0x2AB8: "succapprox",
    0x2AB9: "precnapprox", 0x2ABA: "succnapprox", 0x2ABB: "Prec",
    0x2ABC: "Succ",        0x2ABD: "subsetdot",   0x2ABE: "supsetdot",
    0x2ABF: "subsetplus",  0x2AC0: "supsetplus",  0x2AC1: "submult",
    0x2AC2: "supmult",     0x2AC3: "subedot",     0x2AC4: "supedot",
    0x2AC5: "subseteqq",   0x2AC6: "supseteqq",   0x2AC7: "subsim",
    0x2AC8: "supsim",      0x2AC9: "subsetapprox", 0x2ACA: "supsetapprox",
    0x2ACB: "subsetneqq",  0x2ACC: "supsetneqq",
    0x2ACD: "lsqhook",    0x2ACE: "rsqhook",     0x2ACF: "csub",
    0x2AD0: "csup",        0x2AD1: "csube",       0x2AD2: "csupe",
    0x2AD3: "subsup",      0x2AD4: "supsub",      0x2AD5: "subsub",
    0x2AD6: "supsup",      0x2AD7: "suphsub",     0x2AD8: "supdsub",
    0x2AD9: "forkv",       0x2ADA: "topfork",     0x2ADB: "mlcp",
    0x2ADC: "forks",       0x2ADD: "forksnot",
    0x2ADE: "shortlefttack", 0x2ADF: "shortdowntack", 0x2AE0: "shortuptack",
    0x2AE2: "vDdash",      0x2AE3: "dashV",       0x2AE4: "Dashv",
    0x2AE5: "DashV",       0x2AE6: "varVdash",    0x2AE7: "Barv",
    0x2AE8: "vBar",        0x2AE9: "vBarv",       0x2AEA: "barV",
    0x2AEB: "Vbar",        0x2AEC: "Not",         0x2AED: "bNot",
    0x2AEE: "revnmid",     0x2AEF: "cirmid",      0x2AF0: "midcir",
    0x2AF2: "nhpar",       0x2AF3: "parsim",
    0x2AF7: "lllnest",     0x2AF8: "gggnest",
    0x2AF9: "leqqslant",   0x2AFA: "geqqslant",
    # Relations: arrows 29xx/2Bxx
    0x2900: "nvtwoheadrightarrow", 0x2901: "nVtwoheadrightarrow",
    0x2902: "nvLeftarrow", 0x2903: "nvRightarrow",
    0x2904: "nvLeftrightarrow", 0x2905: "twoheadmapsto",
    0x2906: "Mapsfrom",    0x2907: "Mapsto",
    0x2908: "downarrowbarred", 0x2909: "uparrowbarred",
    0x290A: "Uuparrow",    0x290B: "Ddownarrow",
    0x290C: "leftbkarrow", 0x290D: "rightbkarrow",
    0x290E: "dashleftarrow", 0x290F: "dashrightarrow",
    0x2910: "drbkarow",    0x2911: "rightdotarrow",
    0x2912: "baruparrow",  0x2913: "downarrowbar",
    0x2914: "nvrightarrowtail", 0x2915: "nVrightarrowtail",
    0x2916: "twoheadrightarrowtail", 0x2917: "nvtwoheadrightarrowtail",
    0x2918: "nVtwoheadrightarrowtail",
    0x2919: "lefttail",    0x291A: "righttail",
    0x291B: "leftdbltail", 0x291C: "rightdbltail",
    0x291D: "diamondleftarrow", 0x291E: "rightarrowdiamond",
    0x291F: "diamondleftarrowbar", 0x2920: "barrightarrowdiamond",
    0x2921: "nwsearrow",   0x2922: "neswarrow",
    0x2923: "hknwarrow",   0x2924: "hknearrow",
    0x2925: "hksearow",    0x2926: "hkswarow",
    0x2927: "tona",        0x2928: "toea",
    0x2929: "tosa",        0x292A: "towa",
    0x2933: "rightcurvedarrow",
    0x2936: "leftdowncurvedarrow", 0x2937: "rightdowncurvedarrow",
    0x2938: "cwrightarcarrow", 0x2939: "acwleftarcarrow",
    0x293A: "acwoverarcarrow", 0x293B: "acwunderarcarrow",
    0x293C: "curvearrowrightminus", 0x293D: "curvearrowleftplus",
    0x293E: "cwundercurvearrow", 0x293F: "ccwundercurvearrow",
    0x2940: "acwcirclearrow", 0x2941: "cwcirclearrow",
    0x2942: "rightarrowshortleftarrow", 0x2943: "leftarrowshortrightarrow",
    0x2944: "shortrightarrowleftarrow", 0x2945: "rightarrowplus",
    0x2946: "leftarrowplus", 0x2947: "rightarrowx",
    0x2948: "leftrightarrowcircle", 0x2949: "twoheaduparrowcircle",
    0x294A: "leftrightharpoonupdown", 0x294B: "leftrightharpoondownup",
    0x294C: "updownharpoonrightleft", 0x294D: "updownharpoonleftright",
    0x294E: "leftrightharpoonupup", 0x294F: "updownharpoonrightright",
    0x2950: "leftrightharpoondowndown", 0x2951: "updownharpoonleftleft",
    0x2952: "barleftharpoonup", 0x2953: "rightharpoonupbar",
    0x2954: "barupharpoonright", 0x2955: "downharpoonrightbar",
    0x2956: "barleftharpoondown", 0x2957: "rightharpoondownbar",
    0x2958: "barupharpoonleft", 0x2959: "downharpoonleftbar",
    0x295A: "leftharpoonupbar", 0x295B: "barrightharpoonup",
    0x295C: "upharpoonrightbar", 0x295D: "bardownharpoonright",
    0x295E: "leftharpoondownbar", 0x295F: "barrightharpoondown",
    0x2960: "upharpoonleftbar", 0x2961: "bardownharpoonleft",
    0x2962: "leftharpoonsupdown", 0x2963: "upharpoonsleftright",
    0x2964: "rightharpoonsupdown", 0x2965: "downharpoonsleftright",
    0x2966: "leftrightharpoonsup", 0x2967: "leftrightharpoonsdown",
    0x2968: "rightleftharpoonsup", 0x2969: "rightleftharpoonsdown",
    0x296A: "leftharpoonupdash", 0x296B: "dashleftharpoondown",
    0x296C: "rightharpoonupdash", 0x296D: "dashrightharpoondown",
    0x296E: "updownharpoonsleftright", 0x296F: "downupharpoonsleftright",
    0x2970: "rightimply",  0x2971: "equalrightarrow",
    0x2972: "similarrightarrow", 0x2973: "leftarrowsimilar",
    0x2974: "rightarrowsimilar", 0x2975: "rightarrowapprox",
    0x2976: "ltlarr",      0x2977: "leftarrowless",
    0x2978: "gtrarr",      0x2979: "subrarr",
    0x297A: "leftarrowsubset", 0x297B: "suplarr",
    0x297C: "leftfishtail", 0x297D: "rightfishtail",
    0x297E: "upfishtail",  0x297F: "downfishtail",
    # Relations: 2Bxx arrows
    0x2B30: "circleonleftarrow", 0x2B31: "leftthreearrows",
    0x2B32: "leftarrowonoplus", 0x2B33: "longleftsquigarrow",
    0x2B34: "nvtwoheadleftarrow", 0x2B35: "nVtwoheadleftarrow",
    0x2B36: "twoheadmapsfrom", 0x2B37: "twoheadleftdbkarrow",
    0x2B38: "leftdotarrow", 0x2B39: "nvleftarrowtail",
    0x2B3A: "nVleftarrowtail", 0x2B3B: "twoheadleftarrowtail",
    0x2B3C: "nvtwoheadleftarrowtail", 0x2B3D: "nVtwoheadleftarrowtail",
    0x2B3E: "leftarrowx",  0x2B3F: "leftcurvedarrow",
    0x2B40: "equalleftarrow", 0x2B41: "bsimilarleftarrow",
    0x2B42: "leftarrowbackapprox", 0x2B43: "rightarrowgtr",
    0x2B44: "rightarrowsupset", 0x2B45: "LLeftarrow",
    0x2B46: "RRightarrow", 0x2B47: "bsimilarrightarrow",
    0x2B48: "rightarrowbackapprox", 0x2B49: "similarleftarrow",
    0x2B4A: "leftarrowapprox", 0x2B4B: "leftarrowbsimilar",
    0x2B4C: "rightarrowbsimilar",
    # ─── 5.6 Integrals ──────────────────────────────────────────
    0x222B: "int",         0x222C: "iint",        0x222D: "iiint",
    0x222E: "oint",        0x222F: "oiint",       0x2230: "oiiint",
    0x2231: "intclockwise", 0x2232: "varointclockwise",
    0x2233: "ointctrclockwise",
    0x2A0B: "sumint",      0x2A0C: "iiiint",      0x2A0D: "intbar",
    0x2A0E: "intBar",      0x2A0F: "fint",        0x2A10: "cirfnint",
    0x2A11: "awint",       0x2A12: "rppolint",    0x2A13: "scpolint",
    0x2A14: "npolint",     0x2A15: "pointint",    0x2A16: "sqint",
    0x2A17: "intlarhk",    0x2A18: "intx",        0x2A19: "intcap",
    0x2A1A: "intcup",      0x2A1B: "upint",       0x2A1C: "lowint",
    # ─── 5.7 Big Operators ──────────────────────────────────────
    0x2140: "Bbbsum",      0x220F: "prod",        0x2210: "coprod",
    0x2211: "sum",         0x22C0: "bigwedge",    0x22C1: "bigvee",
    0x22C2: "bigcap",      0x22C3: "bigcup",
    0x27D5: "leftouterjoin", 0x27D6: "rightouterjoin",
    0x27D7: "fullouterjoin", 0x27D8: "bigbot",    0x27D9: "bigtop",
    0x29F8: "xsol",        0x29F9: "xbsol",
    0x2A00: "bigodot",     0x2A01: "bigoplus",    0x2A02: "bigotimes",
    0x2A03: "bigcupdot",   0x2A04: "biguplus",    0x2A05: "bigsqcap",
    0x2A06: "bigsqcup",    0x2A07: "conjquant",   0x2A08: "disjquant",
    0x2A09: "bigtimes",    0x2A0A: "modtwosum",   0x2A1D: "Join",
    0x2A1E: "bigtriangleleft", 0x2A1F: "zcmp",    0x2A20: "zpipe",
    0x2A21: "zproject",    0x2AFC: "biginterleave", 0x2AFF: "bigtalloblong",
    # ─── 5.8 Delimiters ─────────────────────────────────────────
    0x2308: "lceil",       0x2309: "rceil",       0x230A: "lfloor",
    0x230B: "rfloor",      0x2016: "Vert",        0x2980: "Vvert",
    # ─── 5.9 Other Braces ───────────────────────────────────────
    0x231C: "ulcorner",    0x231D: "urcorner",    0x231E: "llcorner",
    0x231F: "lrcorner",    0x27EC: "Lbrbrak",     0x27ED: "Rbrbrak",
    0x2987: "llparenthesis", 0x2988: "rrparenthesis",
    0x2989: "llangle",     0x298A: "rrangle",
    0x298B: "lbrackubar",  0x298C: "rbrackubar",
    0x298D: "lbrackultick", 0x298E: "rbracklrtick",
    0x298F: "lbracklltick", 0x2990: "rbrackurtick",
    0x2991: "langledot",   0x2992: "rangledot",
    0x2993: "lparenless",  0x2994: "rparengtr",
    0x2995: "Lparengtr",   0x2996: "Rparenless",
    0x2997: "lblkbrbrak",  0x2998: "rblkbrbrak",
    0x29D8: "lvzigzag",    0x29D9: "rvzigzag",
    0x29DA: "Lvzigzag",    0x29DB: "Rvzigzag",
    0x29FC: "lcurvyangle", 0x29FD: "rcurvyangle",
    0x27C5: "lbag",        0x27C6: "rbag",
    # ─── 5.12 Radicals ──────────────────────────────────────────
    0x221A: "sqrt",
}


class STIXTab(QWidget):
    PACKAGES = (
        "\\usepackage{amsmath}\n"
        "\\usepackage{amssymb}\n"
        "\\usepackage{stmaryrd}\n"
        "\\usepackage{MnSymbol}\n"
        "\\usepackage{mathtools}\n"
        "\\usepackage{newtxmath}\n"        
        "\\usepackage[charter]{mathdesign}\n"
        "% or \\usepackage{stix}\n"
    )

    def __init__(self, main_window, font_filename="STIXTwoMath-Regular.otf", parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.font_filename = font_filename
        self.font_family = None
        self.symbols = []
        self.current_columns = 0
        self.load_font()
        self.setup_ui()

    def load_font(self):
        possible_paths = [
            os.path.join(os.path.dirname(__file__), self.font_filename),
            self.font_filename,
            os.path.expanduser(f"~/Library/Fonts/{self.font_filename}"),
            f"/usr/share/fonts/{self.font_filename}",
            f"C:\\Windows\\Fonts\\{self.font_filename}",
        ]
        font_path = next((p for p in possible_paths if os.path.exists(p)), None)
        if not font_path:
            #print(f"⚠️ '{self.font_filename}' not found – fallback (text) mode enabled")
            return
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id == -1:
            #print(f"❌ Failed to load STIX Two Math font '{self.font_filename}'")
            return
        self.font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
        #print(f"✅ Loaded STIX Two Math font: {self.font_family}")

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        btn_frame = QFrame()
        btn_frame.setFrameShape(QFrame.StyledPanel)
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(5, 5, 5, 5)
        btn_layout.setSpacing(4)

        btn_pkg = QPushButton("usepackage")
        btn_pkg.setToolTip(
            "Insert \\usepackage declarations for amsmath, amssymb, stmaryrd,\n"
            "MnSymbol, mathtools, newtxmath and mathdesign"
        )
        btn_pkg.clicked.connect(
            lambda: _insert_text_into_editor(self.main_window, self.PACKAGES)
        )
        btn_layout.addWidget(btn_pkg)
        btn_layout.addStretch()
        layout.addWidget(btn_frame)

        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setWordWrap(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        self.init_symbols()
        
        self.remove_symbols([0x26A5, 0x2720])
        # ── Remove unwanted symbols here ──────────────────────
        # Single symbol:
        # self.remove_symbols(0x2302)

        # Multiple specific symbols:
        # self.remove_symbols([0x2302, 0x2336, 0x2423])

        # Entire range (e.g. all geometric shapes U+25A0–U+25FF):
        # self.remove_symbols(range(0x25A0, 0x2600))

        # Combined — remove a range plus individual ones:
        # self.remove_symbols(list(range(0x25A0, 0x2600)) + [0x2302, 0x2336])
        
        
        self.calculate_columns()
        self.populate_table()
        self.table.cellClicked.connect(self.cell_clicked)

    def init_symbols(self):
        self.symbols = []
        
        for code, latex_name in sorted(STIX_SYMBOLS.items()):
            if self.font_family:
                try:
                    display_text = chr(code)
                except Exception:
                    display_text = f"[{latex_name}]"
            else:
                display_text = f"[{latex_name}]"

            if latex_name.startswith("\\"):
                latex_command = latex_name
            elif latex_name in ("sqrt",):
                latex_command = "\\sqrt{x}"
            elif latex_name == "sqrt[3]":
                latex_command = "\\sqrt[3]{x}"
            elif latex_name == "sqrt[4]":
                latex_command = "\\sqrt[4]{x}"
            elif len(latex_name) == 1 and not latex_name.isalpha():
                latex_command = latex_name
            else:
                latex_command = f"\\{latex_name}"

            self.symbols.append({
                "code":    code,
                "latex":   latex_command,
                "name":    latex_name,
                "display": display_text,
                "tooltip": f"{latex_command} (U+{code:04X})",
            })
        #print(f"✅ Loaded {len(self.symbols)} STIX Two Math symbols")

    def remove_symbols(self, codes_to_remove):
        """Remove symbols by code point(s). Accepts a single int, a list, or a range.
        
        Usage examples:
            self.remove_symbols(0x2200)                    # single
            self.remove_symbols([0x2200, 0x2201, 0x2205])  # list
            self.remove_symbols(range(0x25A0, 0x25FF))     # range
        """
        if isinstance(codes_to_remove, int):
            codes_to_remove = {codes_to_remove}
        else:
            codes_to_remove = set(codes_to_remove)

        self.symbols = [s for s in self.symbols if s["code"] not in codes_to_remove]
        self.populate_table()
        #print(f"✅ Removed {len(codes_to_remove)} symbol(s), {len(self.symbols)} remaining")

    def calculate_columns(self):
        if not self.table:
            return False
        width = (self.table.viewport().width()
                 if self.table.viewport() else self.width() - 50)
        columns = max(8, min(24, width // 70))
        if columns != self.current_columns:
            self.current_columns = columns
            return True
        return False

    def populate_table(self):
        if not self.symbols or self.current_columns == 0:
            return
        rows = (len(self.symbols) + self.current_columns - 1) // self.current_columns
        self.table.setRowCount(rows)
        self.table.setColumnCount(self.current_columns)
        self.table.verticalHeader().setDefaultSectionSize(50)

        for idx, sym in enumerate(self.symbols):
            row, col = divmod(idx, self.current_columns)
            item = QTableWidgetItem()
            item.setData(Qt.UserRole, sym["code"])
            item.setText(sym["display"])
            item.setTextAlignment(Qt.AlignCenter)
            item.setToolTip(sym["tooltip"])
            font_size = 20 if self.font_family else 14
            item.setFont(QFont(self.font_family or "Arial", font_size))
            self.table.setItem(row, col, item)

        for row in range(rows):
            for col in range(self.current_columns):
                if row * self.current_columns + col >= len(self.symbols):
                    self.table.setItem(row, col, None)
        self.table.resizeRowsToContents()

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        if self.calculate_columns():
            self.populate_table()

    def showEvent(self, event):
        super().showEvent(event)
        self.calculate_columns()
        self.populate_table()

    def cell_clicked(self, row, col):
        item = self.table.item(row, col)
        if not item:
            return
        code = item.data(Qt.UserRole)
        for sym in self.symbols:
            if sym["code"] == code:
                print(f"Selected: {sym['name']}  U+{code:04X}  →  {sym['latex']}")
                _insert_text_into_editor(self.main_window, sym["latex"])
                break


def load_dingbat_font():
    font_path = os.path.join(os.path.dirname(__file__), "D050000L.otf")
    if not os.path.exists(font_path):
        #print("⚠️ Dingbat font file not found, fallback mode enabled")
        return None
    font_id = QFontDatabase.addApplicationFont(font_path)
    if font_id == -1:
        #print("❌ Failed to load Dingbat font")
        return None
    family = QFontDatabase.applicationFontFamilies(font_id)[0]
    #print("✅ Loaded Dingbat font:", family)
    return family


class PifontTab(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.font_family = load_dingbat_font()
        self.symbols = []
        self.current_columns = 0
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        btn_frame = QFrame()
        btn_frame.setFrameShape(QFrame.StyledPanel)
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(5, 5, 5, 5)
        btn_layout.setSpacing(4)

        btn1 = QPushButton("usepackage")
        btn1.setToolTip("Insert \\usepackage{pifont}")
        btn1.clicked.connect(lambda: _insert_text_into_editor(
            self.main_window,
            "%\\usepackage{lmodern}\n\\usepackage{pifont}\n"
        ))
        btn_layout.addWidget(btn1)

        btn2 = QPushButton("dinglist")
        btn2.setToolTip("Insert dinglist environment")
        btn2.clicked.connect(lambda: _insert_text_into_editor(
            self.main_window,
            "\\begin{dinglist}{43}\n"
            "\\item The first item in the list\n"
            "\\item The second item in the list\n"
            "\\item The third item in the list\n"
            "\\end{dinglist}\n"
        ))
        btn_layout.addWidget(btn2)

        btn3 = QPushButton("dingautolist")
        btn3.setToolTip("Insert dingautolist environment")
        btn3.clicked.connect(lambda: _insert_text_into_editor(
            self.main_window,
            "\\begin{dingautolist}{192}\n"
            "\\item The first item\n"
            "\\item The second item\n"
            "\\item The third item\n"
            "\\end{dingautolist}\n"
        ))
        btn_layout.addWidget(btn3)

        btn4 = QPushButton("dingfill")
        btn4.setToolTip("Insert \\dingfill{224}")
        btn4.clicked.connect(lambda: _insert_text_into_editor(
            self.main_window, "\\dingfill{224}\n"
        ))
        btn_layout.addWidget(btn4)

        btn5 = QPushButton("dingline")
        btn5.setToolTip("Insert \\dingline{34}")
        btn5.clicked.connect(lambda: _insert_text_into_editor(
            self.main_window, "\\dingline{34}\n"
        ))
        btn_layout.addWidget(btn5)

        layout.addWidget(btn_frame)

        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setWordWrap(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        self.init_symbols()
        self.calculate_columns()
        self.populate_table()
        self.table.cellClicked.connect(self.cell_clicked)

    def init_symbols(self):
        self.symbols = []
        excluded_codes = {32, 127, 149, 157, 158, 160}
        excluded_codes.update(range(142, 145),range(61,64),range(150,153))
        for code in range(32, 255):
            if code in excluded_codes:
                continue
            display_text = chr(code) if self.font_family else f"\\ding{{{code}}}"
            self.symbols.append({
                "code":    code,
                "display": display_text,
                "tooltip": f"\\ding{{{code}}}",
            })

    def calculate_columns(self):
        if not self.table:
            return False
        width = (self.table.viewport().width()
                 if self.table.viewport() else self.width() - 50)
        columns = max(8, min(24, width // 80))
        if columns != self.current_columns:
            self.current_columns = columns
            return True
        return False

    def populate_table(self):
        if not self.symbols or self.current_columns == 0:
            return
        rows = (len(self.symbols) + self.current_columns - 1) // self.current_columns
        self.table.setRowCount(rows)
        self.table.setColumnCount(self.current_columns)
        for idx, sym in enumerate(self.symbols):
            row, col = divmod(idx, self.current_columns)
            item = QTableWidgetItem()
            item.setData(Qt.UserRole, sym["code"])
            item.setText(sym["display"])
            item.setTextAlignment(Qt.AlignCenter)
            item.setToolTip(sym["tooltip"])
            item.setFont(QFont(self.font_family or "Arial", 18 if self.font_family else 10))
            self.table.setItem(row, col, item)
        for row in range(rows):
            for col in range(self.current_columns):
                if row * self.current_columns + col >= len(self.symbols):
                    self.table.setItem(row, col, None)
        self.table.resizeRowsToContents()

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        if self.calculate_columns():
            self.populate_table()

    def showEvent(self, event):
        super().showEvent(event)
        self.calculate_columns()
        self.populate_table()

    def cell_clicked(self, row, col):
        item = self.table.item(row, col)
        if not item:
            return
        _insert_text_into_editor(self.main_window, f"\\ding{{{item.data(Qt.UserRole)}}}")


class FontAwesomeParser:
    def __init__(self, font_path):
        self.font_path = font_path
        self.glyphs = []

    def parse(self):
        try:
            with open(self.font_path, 'rb') as f:
                data = f.read(12)
                if len(data) < 12:
                    return False
                sfnt_version = struct.unpack('>I', data[:4])[0]
                if sfnt_version not in (0x4F54544F, 0x74727565):
                    #print("Not a valid OpenType font")
                    return False
                num_tables = struct.unpack('>H', data[4:6])[0]
                cmap_offset = None
                for i in range(num_tables):
                    tag = f.read(4).decode('ascii')
                    f.read(4)
                    offset = struct.unpack('>I', f.read(4))[0]
                    f.read(4)
                    if tag == 'cmap':
                        cmap_offset = offset
                        break
                if cmap_offset is None:
                    #print("CMAP table not found")
                    return False
                f.seek(cmap_offset)
                f.read(2)
                num_subtables = struct.unpack('>H', f.read(2))[0]
                cmap_subtable_offset = None
                for i in range(num_subtables):
                    platform_id = struct.unpack('>H', f.read(2))[0]
                    encoding_id = struct.unpack('>H', f.read(2))[0]
                    subtable_offset = struct.unpack('>I', f.read(4))[0]
                    if platform_id == 3 and encoding_id == 1:
                        cmap_subtable_offset = subtable_offset
                        break
                if cmap_subtable_offset is None:
                    f.seek(cmap_offset + 4)
                    for i in range(num_subtables):
                        platform_id = struct.unpack('>H', f.read(2))[0]
                        f.read(2)
                        subtable_offset = struct.unpack('>I', f.read(4))[0]
                        if platform_id == 0:
                            cmap_subtable_offset = subtable_offset
                            break
                if cmap_subtable_offset is None:
                    #print("Unicode cmap subtable not found")
                    return False
                f.seek(cmap_offset + cmap_subtable_offset)
                format_type = struct.unpack('>H', f.read(2))[0]
                if format_type == 4:
                    length = struct.unpack('>H', f.read(2))[0]
                    language = struct.unpack('>H', f.read(2))[0]
                    seg_count = struct.unpack('>H', f.read(2))[0] // 2
                    f.read(6)
                    end_codes = [struct.unpack('>H', f.read(2))[0] for _ in range(seg_count)]
                    f.read(2)
                    start_codes = [struct.unpack('>H', f.read(2))[0] for _ in range(seg_count)]
                    id_deltas = [struct.unpack('>h', f.read(2))[0] for _ in range(seg_count)]
                    id_range_offsets = [struct.unpack('>H', f.read(2))[0] for _ in range(seg_count)]
                    for i in range(seg_count):
                        start, end = start_codes[i], end_codes[i]
                        delta, range_offset = id_deltas[i], id_range_offsets[i]
                        if start == 0xFFFF:
                            break
                        if range_offset == 0:
                            for code in range(start, end + 1):
                                glyph_index = (code + delta) & 0xFFFF
                                if glyph_index:
                                    self.glyphs.append((code, f"glyph_{glyph_index:04X}"))
                        else:
                            base = (f.tell() - 2) + range_offset
                            for code in range(start, end + 1):
                                f.seek(base + (code - start) * 2)
                                glyph_offset = struct.unpack('>H', f.read(2))[0]
                                if glyph_offset:
                                    glyph_index = (delta + glyph_offset) & 0xFFFF
                                    if glyph_index:
                                        self.glyphs.append((code, f"glyph_{glyph_index:04X}"))
                    return True
                elif format_type == 12:
                    f.read(4)
                    n_groups = struct.unpack('>I', f.read(4))[0]
                    for i in range(n_groups):
                        start = struct.unpack('>I', f.read(4))[0]
                        end = struct.unpack('>I', f.read(4))[0]
                        start_glyph = struct.unpack('>I', f.read(4))[0]
                        for code in range(start, end + 1):
                            glyph_index = start_glyph + (code - start)
                            if glyph_index:
                                self.glyphs.append((code, f"glyph_{glyph_index:04X}"))
                    return True
                else:
                    #print(f"Unsupported cmap format: {format_type}")
                    return False
        except Exception as e:
            print(f"Error parsing font: {e}")
            return False

    def get_usable_glyphs(self, min_code=0xF000, max_code=0xF8FF):
        excluded_ranges = [(0xF223, 0xF22F), (0xF116, 0xF117), (0xF2B5, 0xF500)]
        usable = []
        for code, name in self.glyphs:
            if min_code <= code <= max_code:
                if not any(s <= code <= e for s, e in excluded_ranges):
                    usable.append((code, name))
        return usable


class FontAwesomeTab(QWidget):
    def __init__(self, main_window, font_filename="FontAwesome.otf", parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.font_filename = font_filename
        self.font_family = None
        self.glyphs = []
        self.symbols = []
        self.current_columns = 0
        self.load_font_and_parse()
        self.setup_ui()

    def load_font_and_parse(self):
        font_path = os.path.join(os.path.dirname(__file__), self.font_filename)
        if not os.path.exists(font_path):
            #print(f"⚠️ Font file '{self.font_filename}' not found, fallback mode")
            return
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id == -1:
            #print(f"❌ Failed to load font '{self.font_filename}'")
            return
        self.font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
        #print(f"✅ Loaded FontAwesome font: {self.font_family}")
        parser = FontAwesomeParser(font_path)
        if parser.parse():
            self.glyphs = parser.get_usable_glyphs()
            #print(f"✅ Found {len(self.glyphs)} FontAwesome glyphs")
        else:
            print("⚠️ Failed to parse FontAwesome font, using fallback")

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        btn_frame = QFrame()
        btn_frame.setFrameShape(QFrame.StyledPanel)
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(5, 5, 5, 5)
        btn_layout.setSpacing(4)

        btn1 = QPushButton("usepackage")
        btn1.setToolTip("Insert \\usepackage{fontawesome5}")
        btn1.clicked.connect(lambda: _insert_text_into_editor(
            self.main_window,
            "%\\usepackage[fixed]{fontawesome5}\n\\usepackage{fontawesome5}\n"
        ))
        btn_layout.addWidget(btn1)
        btn_layout.addStretch()
        layout.addWidget(btn_frame)

        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setWordWrap(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        self.init_symbols()
        self.calculate_columns()
        self.populate_table()
        self.table.cellClicked.connect(self.cell_clicked)

    def init_symbols(self):
        self.symbols = []
        source = self.glyphs if self.glyphs else [
            (0xF000, "glass"), (0xF001, "music"), (0xF002, "search"),
            (0xF003, "envelope"), (0xF004, "heart"), (0xF005, "star"),
            (0xF006, "star-o"), (0xF007, "user"), (0xF008, "film"),
            (0xF009, "th-large"), (0xF00A, "th"), (0xF00B, "th-list"),
            (0xF00C, "check"), (0xF00D, "times"), (0xF00E, "search-plus"),
            (0xF230, "facebook-official"), (0xF231, "pinterest-p"),
            (0xF232, "whatsapp"), (0xF233, "server"),
        ]
        for code, name in source:
            if 0xF223 <= code <= 0xF22F:
                continue
            self.symbols.append({
                "code":    code,
                "name":    name,
                "display": chr(code) if self.font_family else f"[{name}]",
                "tooltip": f"{name} (U+{code:04X})",
            })

    def calculate_columns(self):
        if not self.table:
            return False
        width = (self.table.viewport().width()
                 if self.table.viewport() else self.width() - 50)
        columns = max(6, min(24, width // 85))
        if columns != self.current_columns:
            self.current_columns = columns
            return True
        return False

    def populate_table(self):
        if not self.symbols or self.current_columns == 0:
            return
        rows = (len(self.symbols) + self.current_columns - 1) // self.current_columns
        self.table.setRowCount(rows)
        self.table.setColumnCount(self.current_columns)
        for idx, sym in enumerate(self.symbols):
            row, col = divmod(idx, self.current_columns)
            item = QTableWidgetItem()
            item.setData(Qt.UserRole, sym["code"])
            item.setData(Qt.UserRole + 1, sym["name"])
            item.setText(sym["display"])
            item.setTextAlignment(Qt.AlignCenter)
            item.setToolTip(sym["tooltip"])
            item.setFont(QFont(self.font_family or "Arial", 24 if self.font_family else 10))
            self.table.setItem(row, col, item)
        for row in range(rows):
            for col in range(self.current_columns):
                if row * self.current_columns + col >= len(self.symbols):
                    self.table.setItem(row, col, None)
        self.table.resizeRowsToContents()

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        if self.calculate_columns():
            self.populate_table()

    def showEvent(self, event):
        super().showEvent(event)
        self.calculate_columns()
        self.populate_table()

    def cell_clicked(self, row, col):
        item = self.table.item(row, col)
        if not item:
            return
        name = item.data(Qt.UserRole + 1) or ""
        _insert_text_into_editor(self.main_window, f"\\faIcon{{{name}}}")


class InsertCharacterTab(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.tab_widget = QTabWidget()
        self.stix_tab = STIXTab(self.main_window)
        self.tab_widget.addTab(self.stix_tab, "STIX Two Math")
        self.pifont_tab = PifontTab(self.main_window)
        self.tab_widget.addTab(self.pifont_tab, "Pifont (Dingbats)")
        self.fontawesome_tab = FontAwesomeTab(self.main_window)
        self.tab_widget.addTab(self.fontawesome_tab, "FontAwesome")
        layout.addWidget(self.tab_widget)


            
def add_insert_character_tab_to_pdf_viewer(main_window):
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
        pdf_manager = main_window.pdf_manager
        if not hasattr(layout_manager, 'pdf_container') or layout_manager.pdf_container is None:
            layout_manager._recreate_pdf_container()
        if pdf_manager.pdf_layout_mode != "tabbed":
            QMessageBox.information(main_window, "Info",
                "Insert Character tab is only available in tabbed mode. "
                "Switch to tabbed mode first.")
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
            if tab_widget.tabText(i) in ("Welcome", "No Pdfs", "No PDFs"):
                tab_widget.removeTab(i)
        
        possible_labels = {
            tr["insert_character"] for tr in translations.values()
        }                                        
        for i in range(tab_widget.count()):
            if tab_widget.tabText(i) in possible_labels:
                tab_widget.setCurrentIndex(i)
                #print(f"✅ Switched to existing '{tab_title}' tab")
                return
        insert_char_tab = InsertCharacterTab(main_window)
        if not hasattr(main_window, '_insert_char_tabs'):
            main_window._insert_char_tabs = []
        main_window._insert_char_tabs.append(insert_char_tab)
        # Add to tab widget
        tab_title = tr.get("insert_character", "Insert Character")
        tab_index = tab_widget.addTab(insert_char_tab, tab_title)                        
        tab_widget.tabBar().setTabData(tab_index, "insert_character")    
        
        tab_widget.setTabIcon(tab_index, QIcon("icons/insert_character.svg"))
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
        insert_char_tab.show()
        layout_manager.pdf_container.update()
        layout_manager.pdf_container.repaint()        
        #print(f"✅ Insert Character tab added at index {tab_index}")
    except Exception as e:
        QMessageBox.critical(main_window, "Error",
            f"Failed to add Insert Character tab:\n{str(e)}")
        import traceback
        traceback.print_exc()
