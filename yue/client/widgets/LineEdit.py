#! python $this
import os,sys
isPython3 = sys.version_info[0]==3
if isPython3:
    unicode = str
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
#from UnicodeTranslate import Translate
from yue.client.SymTr import SymTr
#from Kana import Translate

class LineEdit(QLineEdit):

    def __init__(self,parent=None):
        self.color = QColor(127,127,127)
        super(LineEdit,self).__init__(parent)

        fm = QFontMetrics(self.font())
        self.textHeight = fm.height()

        self.textEdited.connect(self.textUpdate)

    def keyReleaseEvent(self,event):
        key = event.key()
        if key == Qt.Key_Enter or key == Qt.Key_Return :
            self.keyReleaseEnter(self.displayText())

    def keyReleaseEnter(self,text):
        pass # print text

    def textUpdate(self,text):
        text = unicode(text)
        temp = SymTr.SymTr(text)
        #temp = Translate(text,hu=True)
        if temp.success:
            self.setText(temp.nstring)
            self.cursorBackward(False,temp.rposition)
        return temp.nstring

class LineEditHistory(LineEdit):
    # text edit which maintains a history of previous input
    history = []
    hindex = 0;
    def __init__(self,parent=None):
        super(LineEditHistory,self).__init__(parent)

        self.history = []
        self.hindex = 0;

    def keyReleaseEvent(self,event):
        txt = self.displayText()
        key = event.key()
        if key == Qt.Key_Up :
            if len(self.history) > 0 :
                self.setText(self.history[self.hindex])
                if self.hindex < len(self.history) - 1:
                    self.hindex += 1
        elif key == Qt.Key_Down :
            if self.hindex > 0 :
                self.hindex -= 1
                self.setText(self.history[self.hindex])
            else:
                self.setText("")
        elif key == Qt.Key_Enter or key == Qt.Key_Return :
            self.updateHistory(txt);
            self.keyReleaseEnter(txt)
            self.setText("")

    def updateHistory(self,text):
        self.history.insert(0,text) # make a copy of the item to store in the history
        self.hindex = 0;

    def clearHistory(self):
        self.history = [];
        self.hindex = 0;

class LineEditRepl( LineEditHistory ):

    def __init__(self,repl, parent=None):
        super(LineEditRepl,self).__init__(parent)
        self.repl=repl

    def keyReleaseEnter(self,text):

        result = None
        try:
            result = self.repl.exec_( text )
        except ValueError as e:
            print(e)
            result = False

        if result is False:
            # i intend to flash the background color red for a second
            pass

class ComboBox(QComboBox):

    def __init__(self,parent=None):
        self.color = QColor(127,127,127)
        super(ComboBox,self).__init__(parent)

        self.edit = LineEdit(self)
        self.setLineEdit(self.edit)

        #self.editTextChanged.connect(self.textUpdate)

if __name__ == '__main__':

    import sys

    app = QApplication(sys.argv)
    main = LineEditHistory()
    main.show()
    sys.exit(app.exec_())