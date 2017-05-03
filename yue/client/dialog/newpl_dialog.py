#! python34 ../../../test/test_client.py $this

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from yue.qtcommon.LineEdit import LineEdit
from yue.core.song import Song

import os,sys

class NewPlaylistDialog(QDialog):
    def __init__(self,query="",limit=50,parent=None,create=True):
        super(NewPlaylistDialog,self).__init__(parent);
        self.setWindowTitle("Create New Playlist")

        # --------------------------
        # Widgets

        self.edit         = LineEdit(self)

        self.btn_accept  = QPushButton("Create",self)
        self.btn_cancel  = QPushButton("Cancel",self)

        self.chk_today   = QCheckBox("Ignore Songs Played Today",self)
        self.chk_ban     = QCheckBox("Ignore Bannished Songs",self)

        #self.cbox_preset = QComboBox(self)
        self.spin_size   = QSpinBox(self)
        #self.spin_hash   = QSpinBox(self)

        self.rbCreate = QRadioButton("Create New")
        self.rbInsert = QRadioButton("Insert")

        self.rbOrderRandom = QRadioButton("Random")
        self.rbOrderIndex = QRadioButton("Album Index")

        # --------------------------
        # Default Values

        self.edit.setReadOnly(True)
        self.edit.setPlaceholderText("All Music")

        if query:
            #self.rad_custom.setChecked(True)
            self.edit.setText(query)
        #else:
        #    self.rad_all.setChecked(True)

        self.chk_ban.setChecked(True)

        #self.spin_hash.setRange(0,100);
        self.spin_size.setRange(10,200);

        #self.cbox_preset.setDisabled(True);

        #self.spin_hash.setValue(0);
        self.spin_size.setValue(limit);

        if create:
            self.rbCreate.setChecked(True)
        else:
            self.rbInsert.setChecked(True)
        self.rbOrderRandom.setChecked(True)

        # --------------------------
        # Layout
        self.grid = QGridLayout(self)

        row = 0
        vl_edit = QVBoxLayout(); # layout allows self.edit to expand
        self.grid.addLayout(vl_edit,row,0,1,3)#       widget,row,col,row_span,col_span
        vl_edit.addWidget(self.edit)

        row+=1;
        #self.grid.addWidget(QLabel("Artist Song Limit:"),row,0,Qt.AlignLeft)
        self.grid.addWidget(self.chk_today,row,0,1,3,Qt.AlignLeft)
        self.grid.addWidget(QLabel("Play List Length"),row,2,Qt.AlignLeft)

        row+=1;
        #self.grid.addWidget(self.spin_hash,row,0,Qt.AlignRight)
        self.grid.addWidget(self.chk_ban,row,0,1,3,Qt.AlignLeft)
        self.grid.addWidget(self.spin_size,row,2,Qt.AlignRight)

        row+=1;
        gbMode = QGroupBox("Mode")
        vbMode = QVBoxLayout(gbMode)
        vbMode.addWidget(self.rbCreate)
        vbMode.addWidget(self.rbInsert)
        self.grid.addWidget(gbMode,row,0,2,1)

        gbOrder = QGroupBox("Order")
        vbOrder = QVBoxLayout(gbOrder)
        vbOrder.addWidget(self.rbOrderRandom)
        vbOrder.addWidget(self.rbOrderIndex)
        self.grid.addWidget(gbOrder,row,1,2,1)


        row+=2;
        self.grid.addWidget(self.btn_cancel,row,0,Qt.AlignCenter)
        self.grid.addWidget(self.btn_accept,row,2,Qt.AlignCenter)

        for i in range(0,row+1):
            self.grid.setRowMinimumHeight(row,20)

        # --------------------------
        # connect signals

        self.btn_accept.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

        self.resize(480,240)

    def getQueryParams(self):

        query = self.edit.text()
        extra = ""
        if self.chk_ban.isChecked():
            extra += " ban=0 "
        if self.chk_today.isChecked():
            extra += " date>1 "
        if query and extra:
            query = "(%s) && (%s)"%(query,extra)
        elif not query and extra:
            query = extra

        params = {
            "query":query,
            "limit":self.spin_size.value(),
        }
        return params

    def getCreatePlaylist(self):
        return self.rbCreate.isChecked()

    def getSortOrder(self):
        # sort songs by year, then albumm,then index
        # to get the natural order for the set of songs
        if self.rbOrderIndex.isChecked():
            return [(Song.year,Song.asc),
                    (Song.album,Song.asc),
                    (Song.album_index,Song.asc)]
        return Song.random

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Console Player")
    app.setQuitOnLastWindowClosed(True)
    window = NewPlaylistDialog("artist=foo")

    q=["!ban","abm=bar","this || that"]
    n=["not banned","test"]
    window.setPresets(n,q)
    window.exec_()

    print(window.getQueryParams())

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()