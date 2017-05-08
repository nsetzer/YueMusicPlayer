


import os, sys

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

import traceback


from yue.core.song import Song
from yue.core.sqlstore import SQLStore
from yue.core.library import Library
from yue.core.api import ApiClient

from yue.qtcommon.Tab import Tab
from yue.qtcommon.SongTable import SongTable

from yue.client.ui.library_view import LineEdit_Search

class Concurrent(QThread):
    """docstring for Concurrent"""
    def __init__(self, fptr):
        super(Concurrent, self).__init__()
        self.run = fptr
        self.start()

class RemoteView(Tab):
    """docstring for RemoteView"""

    def __init__(self, parent=None):
        super(RemoteView, self).__init__(parent)


        self.grid_info = QGridLayout()
        self.hbox_search = QHBoxLayout()
        self.vbox = QVBoxLayout(self)

        self.edit_hostname = QLineEdit(self)
        self.edit_username = QLineEdit(self)
        self.edit_apikey   = QLineEdit(self)
        self.edit_dir      = QLineEdit(self)


        self.tbl_remote = SongTable(self)
        self.tbl_remote.showColumnHeader( True )
        self.tbl_remote.showRowHeader( False )

        self.edit_search = LineEdit_Search(self,self.tbl_remote,"Search Remote")
        self.btn_search  = QPushButton("Search",self)
        self.spin_page   = QSpinBox(self)
        self.lbl_page    = QLabel(self)

        lbl = QLabel("Hostname:")
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.grid_info.addWidget(lbl,0,0)
        self.grid_info.addWidget(self.edit_hostname,0,1)

        lbl = QLabel("User Name:")
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.grid_info.addWidget(lbl,0,2)
        self.grid_info.addWidget(self.edit_username,0,3)

        lbl = QLabel("Local Directory:")
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.grid_info.addWidget(lbl,1,0)
        self.grid_info.addWidget(self.edit_dir,1,1)

        lbl = QLabel("API Key:")
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.grid_info.addWidget(lbl,1,2)
        self.grid_info.addWidget(self.edit_apikey,1,3)

        self.hbox_search.addWidget(self.edit_search)
        self.hbox_search.addWidget(self.btn_search)
        self.hbox_search.addWidget(self.spin_page)
        self.hbox_search.addWidget(self.lbl_page)

        self.vbox.addLayout(self.grid_info)
        self.vbox.addLayout(self.hbox_search)
        self.vbox.addWidget(self.tbl_remote.container)

        self.edit_hostname.setText("http://localhost:5000")
        self.edit_username.setText("admin")
        self.edit_apikey.setText("admin")
        self.edit_dir.setText(os.path.expanduser("~/Music/downloads"))

        self.edit_search.textChanged.connect(self.onSearchTextChanged)
        self.btn_search.clicked.connect(self.onSearchClicked)
        self.spin_page.valueChanged.connect(self.onPageIndexChanged)

        self.page_size = 50

    def onSearchTextChanged(self):

        self.spin_page.setEnabled(False)
        self.btn_search.setEnabled(True)
        self.tbl_remote.setData([])

    def onSearchClicked(self):

        client = ApiClient(self.edit_hostname.text())
        client.setApiKey(self.edit_apikey.text())
        client.setApiUser(self.edit_username.text())

        self.query_text = self.edit_search.text()

        self._ctx = Concurrent(lambda:self._query(client,self.query_text,0,self.page_size))

    def onPageIndexChanged(self,index):

        client = ApiClient(self.edit_hostname.text())
        client.setApiKey(self.edit_apikey.text())
        client.setApiUser(self.edit_username.text())

        self.query_text = self.edit_search.text()

        self._ctx = Concurrent(lambda:self._query(client,self.query_text,index-1,self.page_size))

    def _query(self,client,text,index,page_size):
        result = client.get_songs(text,index,page_size)
        self._handle_result(result)

    def _handle_result(self,result):
        self.query_page      = result['page']
        self.query_num_pages = result['num_pages']
        self.query_songs     = result['songs']

        try:
            self.spin_page.blockSignals(True)
            self.btn_search.blockSignals(True)

            self.lbl_page.setText("/%d"%self.query_num_pages)
            self.spin_page.setRange(1,self.query_num_pages)
            self.spin_page.setValue(self.query_page+1)

            self.tbl_remote.setData(self.query_songs)

            self.btn_search.setEnabled(False)
            self.spin_page.setEnabled(True)
        finally:
            self.spin_page.blockSignals(False)
            self.btn_search.blockSignals(False)





