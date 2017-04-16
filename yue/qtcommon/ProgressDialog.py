#! python34 $this

import os,sys

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

import natsort
import traceback

class ProgressThread(QThread):
    """docstring for ProgressThread"""
    def __init__(self, parent):
        super(ProgressThread, self).__init__()
        self.parent = parent

    def run(self):
        self.parent._run()

class ProgressDialog(QDialog):
    """Dialog for displaying long running events
    run() method updates the gui while performing some action
    a multi-state button both cancels the task early and exists the gui
    the dialog cannot be closed until the process is completed or canceled
    by the user
    """

    # TODO: checkbox : close when transfer completes
    # TODO: if not started the context button should display Start

    messageChanged = pyqtSignal(str)
    valueChanged = pyqtSignal(int)
    finalize = pyqtSignal()
    showDialog = pyqtSignal(str,str,tuple)

    def __init__(self,title="Window Title",parent=None):
        super(ProgressDialog, self).__init__(parent)
        self._init_gui(title)
        self.alive = True
        self.done = False
        self.canceled = False
        self.thread = ProgressThread(self)
        self.old_progress = -1 # used to limit ui updates
        self.success_callback  = None
        self.close_callback = None

        # required objects to display a dialog and wait for the result
        # from another thread. The thread waits on the condition variable
        # while the main thread displays the dialog. The main thread
        # can then signal the result
        self.showDialog.connect(self._getInput)
        self.mutex = QMutex()
        self.condition = QWaitCondition()
        self.confirm_result = False

    def _init_gui(self,title):

        self.setWindowTitle(title)
        self.vbox = QVBoxLayout(self)
        self.pbar = QProgressBar()
        self.pbar.setTextVisible(False)
        self.pbar.setRange(0,200)
        self.valueChanged.connect(self.pbar.setValue)

        self.hbox_button = QHBoxLayout()
        self.btn_exit = QPushButton("Cancel")
        self.btn_exit.setSizePolicy(QSizePolicy.Maximum,QSizePolicy.Maximum)
        self.btn_exit.clicked.connect(self.exit)
        self.hbox_button.addStretch(1)
        self.hbox_button.addWidget(self.btn_exit,Qt.AlignRight)

        self.lbl_message = QLabel("")
        self.messageChanged.connect(self.lbl_message.setText)
        self.vbox.addWidget(self.lbl_message)
        self.vbox.addWidget(self.pbar)
        self.vbox.addLayout(self.hbox_button)

        self.finalize.connect(self.setFinished)

        self.resize(320,-1)

    def exit(self):

        if self.alive:
            self.alive = False
            self.canceled = True
            return

        if self.canceled:
            return self.reject()

        if self.done:
            return self.accept()

    def start(self):
        self.thread.start()

    def _run(self):
        # main thread function
        print(self.__class__.__name__,"begin")
        try:
            self.run()
        except Exception as e:
        #    # TODO: alternate path
            print(e)
            print(traceback.format_exc())
        #    raise

        self.alive = False
        self.valueChanged.emit(self.pbar.maximum())
        self.finalize.emit()

    def run(self):
        count = self.pbar.minimum()
        while self.alive and count < self.pbar.maximum():
            count += 1
            self.valueChanged.emit(count)
            QThread.usleep(100000);

    def setFinished(self):
        self.done = True
        self.btn_exit.setText("Exit");

        if self.success_callback is not None:
            self.success_callback()

        if self.closeOnFinish():
            self.accept()

    def close(self):
        self.thread.wait() # join

        if self.close_callback is not None:
            self.close_callback();

    def accept(self):
        if self.done:
            self.close()
            return super().accept()

    def reject(self):
        if self.done:
            self.close()
            super().reject()

    def setProgress(self,fprogress):
        progress = int(fprogress*self.pbar.maximum())
        if progress > self.old_progress:
            self.valueChanged.emit(progress)
            self.old_progress = progress
            return True
        return False

    def setMessage(self,message):
        self.messageChanged.emit(message)

    def closeOnFinish(self):
        return False

    def setSuccessCallback(self,cbk):
        self.success_callback = cbk

    def setOnCloseCallback(self,cbk):
        self.close_callback = cbk;

    def getInput(self,title,text,*btnText):
        """
        get input can only be called from a thread that
        is not the main thread. it can be used to ask a question
        to the user. the result is the index of a button.

        btntext should be a list of text to display on each button
        """
        self.mutex.lock();
        self.showDialog.emit(title,text,btnText)
        self.condition.wait(self.mutex)
        result = self.confirm_result
        self.mutex.unlock();
        return result

    def _getInput(self,title,text,txtlst):

        self.mutex.lock();
        mbox = QMessageBox(QMessageBox.Question,title,text)
        for text in txtlst:
            mbox.addButton(text,QMessageBox.AcceptRole)
        result = self.confirm_result = mbox.exec_()
        self.condition.wakeAll()
        self.mutex.unlock();
        return result

    def join(self):

        while not self.done:
            QThread.usleep(100*1000)

def main():

    class DemoProgressDialog(ProgressDialog):

        def run(self):
            self.setMessage("demo progress dialog")
            count = self.pbar.minimum()
            while self.alive and count < self.pbar.maximum():
                count += 1
                self.valueChanged.emit(count)
                QThread.usleep(7500);

    if os.name == 'nt':
        plugin_path = r"C:\Python34\Lib\site-packages\PyQt5\plugins"
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugin_path

    app = QApplication(sys.argv)
    app.setApplicationName("Console")
    app.setQuitOnLastWindowClosed(True)

    diag = DemoProgressDialog();
    diag.start()

    result = diag.exec_()
    if result:
        print("accepted")
    else:
        print("rejected")

    #sys.exit(app.exec_())
if __name__ == "__main__":
    main()