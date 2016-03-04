#! cd ../../.. && python34 $path/$this

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from yue.client.widgets.LineEdit import LineEdit
from ..widgets.ProgressDialog import ProgressDialog

from yue.core.song import Song, write_tags, UnsupportedFormatError
from yue.core.library import Library

import os,sys



class SelectSongsDialog(QDialog):
    def __init__(self,query="",parent=None):
        super(SelectSongsDialog,self).__init__(parent);
        self.setWindowTitle("Select Music")

        # --------------------------
        # Widgets
        self.rad_all     = QRadioButton("All Music",self)
        self.rad_custom  = QRadioButton("Custom Search:",self)

        self.edit         = LineEdit(self)

        self.btn_accept  = QPushButton("Update",self)
        self.btn_cancel  = QPushButton("Cancel",self)

        # --------------------------
        # Default Values

        self.edit.setPlaceholderText("All Music")

        if query:
            self.rad_custom.setChecked(True)
            self.edit.setText(query)
        else:
            self.rad_all.setChecked(True)

        # --------------------------
        # Layout
        self.grid = QGridLayout(self)

        row = 0
        self.grid.addWidget(self.rad_all   ,row,0,Qt.AlignLeft)
        row+=1;
        self.grid.addWidget(self.rad_custom,row,0,Qt.AlignLeft)

        row+=1; # self.edit ROW
        vl_edit = QVBoxLayout(); # layout allows self.edit to expand
        self.grid.addLayout(vl_edit,row,0,1,3)#       widget,row,col,row_span,col_span
        vl_edit.addWidget(self.edit)
        self.grid.setRowMinimumHeight(row,20)

        row+=1;
        self.grid.addWidget(self.btn_cancel,row,0,Qt.AlignCenter)
        self.grid.addWidget(self.btn_accept,row,2,Qt.AlignCenter)
        self.grid.setRowMinimumHeight(row,20)

        # --------------------------
        # connect signals
        self.rad_all.clicked.connect(self.event_click_radio_button_1)
        self.rad_custom.clicked.connect(self.event_click_radio_button_2)
        self.edit.keyPressEvent = self.event_text_changed

        self.btn_accept.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

    def event_click_radio_button_1(self,event=None):
        self.edit.setText("");

    def event_click_radio_button_2(self,event=None):
        pass

    def event_text_changed(self,event=None):
        super(LineEdit,self.edit).keyPressEvent(event)
        self.rad_custom.setChecked(True)

    def getQuery(self):
        return self.edit.text()

class UpdateTagProgressDialog(ProgressDialog):

    def __init__(self, query="", parent=None):
        super().__init__("Update Tags", parent)
        self.query = query

    def run(self):

        self.setMessage("Reticulating splines")

        # get a thread local copy
        lib = Library.instance().reopen()
        songs = lib.search( self.query )
        self.pbar.setMaximum( len(songs)-1 )

        QThread.usleep(2000000);

        self.setMessage("Updating MP3 Tags")
        count = 0
        for i,song in enumerate(songs):
            try:
                write_tags( song )
            except UnsupportedFormatError:
                pass
            except PermissionError as e:
                sys.stderr.write("Permission Denied: %s\n"%song[Song.path])
                sys.stderr.write("%s\n"%e)
            except OSError as e:
                sys.stderr.write("System Error: %s\n"%song[Song.path])
                sys.stderr.write("%s\n"%e)
            else:
                count += 1
                sys.stdout.write(Song.toString( song ) + "\n")
            finally:
                self.valueChanged.emit(i)

        if count == 0:
            self.setMessage("No songs updated.");
        else:
            self.setMessage("Successfully update %d/%d files."%(count,len(songs)))

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    window = SelectSongsDialog("artist=unknown")

    if window.exec_():
        q = window.getQuery()

        dialog = UpdateTagProgressDialog(q)
        dialog.start()
        dialog.exec_()


    #sys.exit(app.exec_())


if __name__ == '__main__':
    main()