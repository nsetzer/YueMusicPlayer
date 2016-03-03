#! python34 ../test_texteditor.py

# http://www.scintilla.org/ScintillaDoc.html

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.Qsci import *

import os,sys
from io import BytesIO

import codecs
import datetime

lexers = {
    "Python" : QsciLexerPython,
    "Makefile" : QsciLexerMakefile,
    "HTML" : QsciLexerHTML,
    "Bash" : QsciLexerBash,
    "Batch" : QsciLexerBatch,
    "CSS" : QsciLexerCSS,
    "Properties" : QsciLexerProperties,
    "Java Script" : QsciLexerJavaScript,
    "Java" : QsciLexerJavaScript
}

class SimpleSciEditor(QsciScintilla):
    ARROW_MARKER_NUM = 8

    def __init__(self, parent=None):
        super(SimpleSciEditor, self).__init__(parent)

        # Set the default font
        #font = QFont()
        font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        #font.setFamily('Courier')
        font.setFixedPitch(True)
        font.setPointSize(10)
        self.setFont(font)
        self.setMarginsFont(font)

        # Margin 0 is used for line numbers
        fontmetrics = QFontMetrics(font)
        self.setMarginWidth(0, fontmetrics.width("0000") + 6)
        self.setMarginLineNumbers(0, True)
        self.setMarginsBackgroundColor(QColor("#cccccc"))

        # Clickable margin 1 for showing markers
        self.setMarginSensitivity(1, True)
        #self.connect(self,
        #    SIGNAL('marginClicked(int, int, Qt::KeyboardModifiers)'),
        #    self.on_margin_clicked)
        self.markerDefine(QsciScintilla.RightArrow,
            self.ARROW_MARKER_NUM)
        self.setMarkerBackgroundColor(QColor("#ee1111"),
            self.ARROW_MARKER_NUM)

        # Brace matching: enable for a brace immediately before or after
        # the current position
        #
        self.setBraceMatching(QsciScintilla.SloppyBraceMatch)


        # Current line visible with special background color
        self.setCaretLineVisible(True)
        self.setCaretLineBackgroundColor(QColor("#e4e4ff"))

        # Set lexer
        lexer = QsciLexerProperties()
        #lexer = QsciLexerPython()
        lexer.setDefaultFont(font)
        self.setLexer(lexer)

        self.setAutoIndent(True)
        self.setIndentationsUseTabs(False)
        self.setTabWidth(4)
        self.setWhitespaceVisibility(True)

        # Don't want to see the horizontal scrollbar at all
        # Use raw message to Scintilla here (all messages are documented
        # here: http://www.scintilla.org/ScintillaDoc.html)
        self.SendScintilla(QsciScintilla.SCI_SETHSCROLLBAR, 0)

        # not too small
        #self.setMinimumSize(600, 450)
        #self.resize(600, 450) # after show
        return

    def on_margin_clicked(self, nmargin, nline, modifiers):
        # Toggle marker for the line the margin was clicked on
        if self.markersAtLine(nline) != 0:
            self.markerDelete(nline, self.ARROW_MARKER_NUM)
        else:
            self.markerAdd(nline, self.ARROW_MARKER_NUM)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = SimpleSciEditor()
    editor.show()
    text=open(sys.argv[0]).read()
    editor.setText(text)
    assert editor.text()==text
    app.exec_()