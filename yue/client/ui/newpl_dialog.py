#! python34 ../../../test/test_client.py $this

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from yue.client.widgets.LineEdit import LineEdit

import os,sys

class NewPlaylistDialog(QDialog):
    def __init__(self,query="",limit=50,parent=None):
        super(NewPlaylistDialog,self).__init__(parent);
        self.setWindowTitle("Create New Playlist")

        # --------------------------
        # Widgets
        self.rad_all     = QRadioButton("All Music",self)
        self.rad_preset  = QRadioButton("Preset Search",self)
        self.rad_preset.setDisabled(True)
        self.rad_custom  = QRadioButton("Custom Search:",self)

        self.edit         = LineEdit(self)

        self.btn_accept  = QPushButton("Create",self)
        self.btn_cancel  = QPushButton("Cancel",self)

        self.chk_today   = QCheckBox("Ignore Songs Played Today",self)
        self.chk_ban     = QCheckBox("Ignore Bannished Songs",self)

        self.cbox_preset = QComboBox(self)
        self.spin_size   = QSpinBox(self)
        #self.spin_hash   = QSpinBox(self)

        # --------------------------
        # Default Values

        self.edit.setPlaceholderText("All Music")

        if query:
            self.rad_custom.setChecked(True)
            self.edit.setText(query)
        else:
            self.rad_all.setChecked(True)

        self.chk_ban.setChecked(True)

        #self.spin_hash.setRange(0,100);
        self.spin_size.setRange(10,200);

        self.cbox_preset.setDisabled(True);

        #self.spin_hash.setValue(0);
        self.spin_size.setValue(limit);

        # --------------------------
        # Layout
        self.grid = QGridLayout(self)

        row = 0
        self.grid.addWidget(self.rad_all   ,row,0,Qt.AlignLeft)
        row+=1;
        self.grid.addWidget(self.rad_preset,row,0,Qt.AlignLeft)
        #self.grid.addWidget(QLabel("Preset Number:"),row,1,Qt.AlignRight)
        self.grid.addWidget(self.cbox_preset,row,1,1,2,Qt.AlignRight)
        row+=1;
        self.grid.addWidget(self.rad_custom,row,0,Qt.AlignLeft)

        row+=1; # self.edit ROW
        vl_edit = QVBoxLayout(); # layout allows self.edit to expand
        self.grid.addLayout(vl_edit,row,0,1,3)#       widget,row,col,row_span,col_span
        vl_edit.addWidget(self.edit)
        self.grid.setRowMinimumHeight(row,20)

        row+=1;
        #self.grid.addWidget(QLabel("Artist Song Limit:"),row,0,Qt.AlignLeft)
        self.grid.addWidget(self.chk_today,row,0,1,3,Qt.AlignLeft)
        self.grid.addWidget(QLabel("Play List Length"),row,2,Qt.AlignLeft)
        self.grid.setRowMinimumHeight(row,20)

        row+=1;
        #self.grid.addWidget(self.spin_hash,row,0,Qt.AlignRight)
        self.grid.addWidget(self.chk_ban,row,0,1,3,Qt.AlignLeft)
        self.grid.addWidget(self.spin_size,row,2,Qt.AlignRight)
        self.grid.setRowMinimumHeight(row,20)

        row+=1;
        self.grid.addWidget(self.btn_cancel,row,0,Qt.AlignCenter)
        self.grid.addWidget(self.btn_accept,row,2,Qt.AlignCenter)
        self.grid.setRowMinimumHeight(row,20)

        # --------------------------
        # connect signals
        self.rad_all.clicked.connect(self.event_click_radio_button_1)
        self.rad_preset.clicked.connect(self.event_click_radio_button_2)
        self.rad_custom.clicked.connect(self.event_click_radio_button_3)
        #self.edit.textEdited.connect(self.event_text_changed)
        self.edit.keyPressEvent = self.event_text_changed

        self.btn_accept.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

        self.cbox_preset.currentIndexChanged.connect(self.event_cbox_preset_changed)

        self.resize(480,240)

    def setPresets(self,names,queries):
        self.rad_preset.setEnabled(True)
        self.cbox_preset.clear();
        for n,q in sorted(zip(names,queries),key=lambda x:x[0]):
            self.cbox_preset.addItem(n,q)
        self.cbox_preset.setCurrentIndex(0);

    def event_click_radio_button_1(self,event=None):
        self.cbox_preset.setDisabled(True);
        self.edit.setText("");

    def event_click_radio_button_2(self,event=None):
        self.cbox_preset.setDisabled(False);
        self.event_cbox_preset_changed(self.cbox_preset.currentIndex())

    def event_click_radio_button_3(self,event=None):
        self.cbox_preset.setDisabled(True);

    def event_text_changed(self,event=None):
        super(LineEdit,self.edit).keyPressEvent(event)
        self.rad_custom.setChecked(True)
        self.cbox_preset.setDisabled(True);

    def event_cbox_preset_changed(self, value):
        if self.rad_preset.isChecked():
            text = self.cbox_preset.itemData(value)
            self.edit.setText(text);

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