


import os, sys

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

import traceback


from yue.core.song import Song
from yue.core.search import naive_search, ParseError, SearchGrammar
from yue.core.sqlstore import SQLStore
from yue.core.library import Library
from yue.core.api import ApiClient
from yue.qtcommon.explorer.jobs import Job, Dashboard

from yue.qtcommon.Tab import Tab
from yue.qtcommon.SongTable import SongTable

from yue.client.ui.library_view import LineEdit_Search

class RemoteTable(SongTable):
    """docstring for RemoteTable"""
    def __init__(self, parent):
        super(RemoteTable, self).__init__(parent)

    def mouseReleaseRight(self,event):

        items = self.getSelection()

        menu = QMenu(self)

        act = menu.addAction("Download")
        act.triggered.connect(lambda:self.parent().action_downloadSelection(items))

        action = menu.exec_( event.globalPos() )

class QueryJob(Job):
    """docstring for QueryJob"""
    def __init__(self, client, query, page, page_size, callback):
        super(QueryJob, self).__init__()
        self.client = client
        self.query = query
        self.page = page
        self.page_size = page_size
        self.callback = callback

    def doTask(self):
        result = self.client.get_songs(self.query,self.page,self.page_size)
        self.callback(result)

class DownloadJob(Job):
    """docstring for DownloadJob"""
    def __init__(self, client, songs, dir_base):
        super(DownloadJob, self).__init__()
        self.client = client
        self.songs = songs
        self.dir_base = dir_base

    def doTask(self):

        lib = Library.instance().reopen()
        for song in self.songs:
            path = self.client.download_song(self.dir_base,song,self._dlprogress)
            temp = song.copy()
            temp[Song.path] = path
            del temp[Song.artist_key]
            del temp[Song.remote] # delete it before adding to db
            lib.insert(**temp)
            song[Song.remote] = 0 # no longer remote

    def _dlprogress(self,x,y):
        p = int(100.0*x/y)
        self.setProgress(p)


class ConnectJob(Job):
    """docstring for ConnectJob"""
    newLibrary = pyqtSignal(list)

    def __init__(self, client, basedir):
        super(ConnectJob, self).__init__()
        self.client = client
        self.basedir = basedir

    def doTask(self):

        songs=[]
        page_size = 500
        result = self.client.get_songs("",0,page_size)

        num_pages = result['num_pages']
        songs += result['songs']
        for page in range(1,num_pages):
            p = 90.0*(page+1)/num_pages
            self.setProgress(p)
            result = self.client.get_songs("ban=0",page,page_size)
            songs += result['songs']

        for song in songs:
            path = self.client.local_path(self.basedir,song)
            if os.path.exists(path):
                song[Song.path] = path
                song[Song.remote] = 0
            else:
                song[Song.remote] = 1

        self.setProgress(100)
        self.newLibrary.emit(songs)

class RemoteSongSearchGrammar(SearchGrammar):
    """docstring for SongSearchGrammar"""

    def __init__(self):
        super(RemoteSongSearchGrammar, self).__init__()

        # all_text is a meta-column name which is used to search all text fields
        self.all_text = Song.all_text
        self.text_fields = set(Song.textFields())
        # i still treat the path as a special case even though it really isnt
        self.text_fields.add(Song.path)
        self.date_fields = set(Song.dateFields())
        self.time_fields = set([Song.length,])
        self.year_fields = set([Song.year,])

    def translateColumn(self,colid):
        # translate the given colid to an internal column name
        # e.g. user may type 'pcnt' which expands to 'playcount'
        try:
            if colid == Song.remote:
                return Song.remote
            return Song.column( colid );
        except KeyError:
            raise ParseError("Invalid column name `%s` at position %d"%(colid,colid.pos))


class RemoteView(Tab):
    """docstring for RemoteView"""

    def __init__(self, parent=None):
        super(RemoteView, self).__init__(parent)


        self.grid_info = QGridLayout()
        self.hbox_search = QHBoxLayout()
        self.vbox = QVBoxLayout(self)

        self.dashboard = Dashboard(self)

        self.edit_hostname = QLineEdit(self)
        self.edit_username = QLineEdit(self)
        self.edit_apikey   = QLineEdit(self)
        self.edit_dir      = QLineEdit(self)

        self.tbl_remote = RemoteTable(self)
        self.tbl_remote.showColumnHeader( True )
        self.tbl_remote.showRowHeader( False )

        self.edit_search = LineEdit_Search(self,self.tbl_remote,"Search Remote")
        #self.btn_search  = QPushButton("Search",self)
        #self.spin_page   = QSpinBox(self)
        #self.lbl_page    = QLabel(self)

        self.btn_connect = QPushButton("Connect",self)

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

        self.lbl_error  = QLabel("")
        self.lbl_search  = QLabel("")

        self.hbox_search.addWidget(self.btn_connect)
        self.hbox_search.addWidget(self.edit_search)
        self.hbox_search.addWidget(self.lbl_search)

        self.vbox.addLayout(self.grid_info)
        self.vbox.addLayout(self.hbox_search)
        self.vbox.addWidget(self.lbl_error)
        self.vbox.addWidget(self.tbl_remote.container)
        self.vbox.addWidget(self.dashboard)


        self.edit_hostname.setText("http://localhost:5000")
        self.edit_username.setText("admin")
        self.edit_apikey.setText("a10ddf873662f4aabd67f62c799ecfbb")
        self.edit_dir.setText(os.path.expanduser("~/Music/downloads"))

        self.edit_search.textChanged.connect(self.onSearchTextChanged)
        self.btn_connect.clicked.connect(self.onConnectClicked)

        self.grammar = RemoteSongSearchGrammar()
        self.song_library = []

        self.lbl_error.hide()

    def onSearchTextChanged(self):

        text = self.edit_search.text()
        self.run_search(text)

    def run_search(self,text):

        try:
            rule = self.grammar.ruleFromString( text )

            items = list(naive_search(self.song_library,rule))
            self.tbl_remote.setData(items)
            self.edit_search.setStyleSheet("")
            self.lbl_error.hide()
            self.lbl_search.setText("%d/%d"%(len(items),len(self.song_library)))

        except ParseError as e:
            self.edit_search.setStyleSheet("background: #CC0000;")
            self.lbl_error.setText("%s"%e)
            self.lbl_error.show()

    def onConnectClicked(self):

        client = ApiClient(self.edit_hostname.text())
        client.setApiKey(self.edit_apikey.text())
        client.setApiUser(self.edit_username.text())

        dir = self.edit_dir.text()

        job = ConnectJob(client,dir)
        job.newLibrary.connect(self.onNewLibrary)
        self.dashboard.startJob(job)

    def onNewLibrary(self,songs):
        self.song_library = songs
        self.tbl_remote.setData(songs)

    def action_downloadSelection(self,items):

        client = ApiClient(self.edit_hostname.text())
        client.setApiKey(self.edit_apikey.text())
        client.setApiUser(self.edit_username.text())

        job = DownloadJob(client,items,self.edit_dir.text())
        self.dashboard.startJob(job)




