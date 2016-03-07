#! cd ../../.. && python34 $path\\$this

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

import os,sys


from yue.core.sqlstore import SQLStore
from yue.core.library import Library
from yue.core.playlist import PlaylistManager
from yue.client.widgets.LargeTable import LargeTable
from yue.client.widgets.LineEdit import LineEdit

class SelectTable(LargeTable):
    """docstring for SelectTable"""
    def __init__(self, parent=None):
        super(SelectTable, self).__init__(parent)

        self.setSelectionRule(LargeTable.SELECT_ONE)
        self.setLastColumnExpanding( True )
        self.setAlwaysHideScrollbar(True,False)
        self.showColumnHeader( False )
        self.showRowHeader( True )

    def mouseDoubleClick(self,row,col,event):

        if event is None or event.button() == Qt.LeftButton:
            if 0<= row < len(self.data):
                self.parent().accept()

    def mouseReleaseRight(self,event):

        items = self.getSelection()
        print(items)
        menu = QMenu(self)

        act = menu.addAction(QIcon(":/img/app_trash.png"),"Delete",lambda:self.delete_list(items[0]))
        act.setDisabled( len(items) != 1 ) # in case selection is zero?

        menu.exec_( event.globalPos() )

    def delete_list(self,listname):

        title = "Delete Playlist"
        msg = "Are you sure you want to delete `%s`."%listname
        # I would prefer to use "delete" and "cancel", but this does not seem to accept strings
        result = QMessageBox.warning(self, title, msg, QMessageBox.Ok, QMessageBox.Cancel)
        if result==QMessageBox.Ok:
            sys.stderr.write("delete: %s. <not supported>\n"%listname)


class OpenPlaylistDialog(QDialog):

    def __init__(self,text='',title='Open Playlist', prompt='', parent=None):

        super(OpenPlaylistDialog,self).__init__(parent)
        self.setWindowTitle(title)
        self.resize(320, 240)

        hbox = QHBoxLayout();
        vbox = QVBoxLayout(self);
        self.table = SelectTable(self)

        self.btna = QPushButton("Accept")
        self.btnc = QPushButton("Cancel")

        hbox.addWidget(self.btnc)
        hbox.addWidget(self.btna)

        if len(prompt) > 0:
            vbox.addWidget(QLabel(prompt))

        vbox.addWidget(self.table.container)
        vbox.addLayout(hbox)

        # cant edit the current playlist because reasons
        data = [ [x,] for x in sorted(PlaylistManager.instance().names()) if x != "current" ]
        self.table.setData( data )

        self.btna.clicked.connect(self.accept)
        self.btnc.clicked.connect(self.reject)

        self.selected_name = None

    def text(self):
        """ returns the name of the selected playlist, or None """
        return self.selected_name

    def accept(self):
        sel = self.table.getSelection()
        if len(sel) == 1:
            self.selected_name = sel[0]
            super().accept()

def main():

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    db_path = "./yue.db"
    sqlstore = SQLStore(db_path)
    Library.init( sqlstore )
    PlaylistManager.init( sqlstore )

    window = OpenPlaylistDialog()
    window.show()

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()