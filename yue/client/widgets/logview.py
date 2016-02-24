#! python33 $this
import os,sys,codecs
import traceback

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from yue.core.logger import Logger

class LogView(QTextEdit):
    """docstring for Console"""

    logLine = pyqtSignal(str,name="logLine");

    def __init__(self,trace=False,echo = False):
        super(LogView, self).__init__()
        self.trace = trace
        self.echo = echo
        self.setReadOnly(True) # Qt options
        self.setLineWrapMode(QTextEdit.NoWrap)
        self.logLine.connect(self.writeToWidget)


        self.setFont(QFontDatabase.systemFont(QFontDatabase.FixedFont))

    def writeToWidget(self,utf8str):
        self.moveCursor(QTextCursor.End)
        self.insertPlainText( utf8str )
        self.moveCursor(QTextCursor.End)

    def write(self,utf8str):
        # this allows mutli threading
        # also widgets can only be updated from the main thread.
        self.logLine.emit(utf8str)

    def writelines(self,seq):
        self.moveCursor(QTextCursor.End)
        for line in seq:
            self.insertPlainText( line )
            self.moveCursor(QTextCursor.End)

    def flush(self):
        pass

    def close(self):
        pass

    def __enter__(self):
        Logger(Logger.BUFFER,trace=self.trace,echo=self.echo).register()
        return self

    def __exit__(self,typ,val,trace):
        # write recorded messages to a file on any error
        if typ is None:
            self.writelines(Logger.instance.history())
            Logger.instance.setWriter(self)
        else:
            # setting trace to false removes these lines from the traceback.
            Logger.instance.enableTraceback(False)
            sys.stdout("\n")
            for line in traceback.format_exception(typ,val,trace):
                sys.stdout(line)
            with codecs.open("error.log","w","utf-8") as wf:
                for line in Logger.instance.history():
                    wf.write(line)
        return

def main():
    """
    demonstrate how to use a log view object.
    a LogView can be used in the with context to capture all
    stdout/stderr messages. if an exception is caught it will
    be written to an error log in the current directory.
    otherwise the messages will be displayed inside the text area
    for the LogView. When the with context ends, stdout and stderr will
    be instrumented to send future log statements to the LogView

    this is to be used in a width console during initialization before show()
    can be called on the main window.
    """

    app = QApplication(sys.argv)
    app.setApplicationName("Console")
    app.setQuitOnLastWindowClosed(True)
    view = LogView()

    with view:
        print("init client")
        sys.stderr.write("error\n")
    print("done...")
    view.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()