


import os, sys

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

import traceback


from yue.core.song import Song, SongSearchGrammar
from yue.core.search import naive_search, ParseError, SearchGrammar
from yue.core.sqlstore import SQLStore
from yue.core.library import Library
from yue.core.history import History
from yue.core.settings import Settings
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

        lib = Library.instance().reopen()
        for song in songs:

            # match by id
            try:
                local_song = lib.songFromId(song[Song.uid])
                song[Song.path] = local_song[Song.path]
                song[Song.remote] = 0
                continue
            except KeyError:
                pass

            # match by path
            path = self.client.local_path(self.basedir,song)
            if os.path.exists(path):
                song[Song.path] = path
                song[Song.remote] = 0
                continue

            # not found locally
            song[Song.remote] = 1

        self.setProgress(100)
        self.newLibrary.emit(songs)

        # success, update settings
        settings = Settings.instance().reopen()
        settings['remote_hostname'] = self.client.getHostName()
        settings['remote_username'] = self.client.getUserName()
        settings['remote_apikey']   = self.client.getApiKey()
        settings['remote_basedir']  = self.basedir

class HistoryPullJob(Job):
    def __init__(self, client):
        super(HistoryPullJob, self).__init__()
        self.client = client

    def doTask(self):

        records = []
        page_size = 100
        result = self.client.history_get(0,page_size)
        num_pages = result['num_pages']
        records += result['records']

        for page in range(1,num_pages):
            p = 90.0*(page+1)/num_pages
            self.setProgress(p)
            result = self.client.history_get(page,page_size)
            records += result['records']
            break

        print("num history pages: %d"%num_pages)
        print("num history records: %d"%len(records))

class HistoryPushJob(Job):
    def __init__(self, client):
        super(HistoryPushJob, self).__init__()
        self.client = client

    def doTask(self):
        page_size = 100
        hist = History.instance().reopen()
        self.client.history_put(hist.export())

class HistoryDeleteJob(Job):
    def __init__(self, client):
        super(HistoryDeleteJob, self).__init__()
        self.client = client

    def doTask(self):
        self.client.history_delete()

class RemoteSongSearchGrammar(SongSearchGrammar):
    """docstring for SongSearchGrammar

    A SongSearchGrammar that allows for searching a remote database.
    A "remote" field is set true if the song has not been downloaded
    """

    def __init__(self):
        super(RemoteSongSearchGrammar, self).__init__()

    def translateColumn(self,colid):
        if colid == Song.remote:
            return Song.remote
        return super().translateColumn( colid );

class RemoteView(Tab):
    """docstring for RemoteView"""

    def __init__(self, parent=None):
        super(RemoteView, self).__init__(parent)


        self.grid_info = QGridLayout()
        self.hbox_search = QHBoxLayout()
        self.hbox_admin = QHBoxLayout()
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

        self.btn_hardsync = QPushButton("Hard Sync", self)
        self.btn_hardpush = QPushButton("Hard Pull", self)
        self.btn_push     = QPushButton("Push", self)
        self.btn_pull     = QPushButton("Pull", self)
        self.btn_delete   = QPushButton("Delete", self)

        self.hbox_search.addWidget(self.btn_connect)
        self.hbox_search.addWidget(self.edit_search)
        self.hbox_search.addWidget(self.lbl_search)

        self.hbox_admin.addWidget(QLabel("History:"))
        self.hbox_admin.addWidget(self.btn_hardsync)
        self.hbox_admin.addWidget(self.btn_hardpush)
        self.hbox_admin.addWidget(self.btn_push)
        self.hbox_admin.addWidget(self.btn_pull)
        self.hbox_admin.addWidget(self.btn_delete)

        self.vbox.addLayout(self.grid_info)
        self.vbox.addLayout(self.hbox_admin)
        self.vbox.addLayout(self.hbox_search)
        self.vbox.addWidget(self.lbl_error)
        self.vbox.addWidget(self.tbl_remote.container)
        self.vbox.addWidget(self.dashboard)

        self.edit_hostname.setText(Settings.instance()['remote_hostname'])
        self.edit_username.setText(Settings.instance()['remote_username'])
        # "a10ddf873662f4aabd67f62c799ecfbb"
        self.edit_apikey.setText(Settings.instance()['remote_apikey'])
        self.edit_dir.setText(Settings.instance()['remote_basedir'])

        self.edit_search.textChanged.connect(self.onSearchTextChanged)
        self.btn_connect.clicked.connect(self.onConnectClicked)

        self.btn_pull.clicked.connect(self.onHistoryPullClicked)
        self.btn_push.clicked.connect(self.onHistoryPushClicked)
        self.btn_delete.clicked.connect(self.onHistoryDeleteClicked)

        self.grammar = RemoteSongSearchGrammar()
        self.song_library = []

        self.lbl_error.hide()

    def onSearchTextChanged(self):

        text = self.edit_search.text()
        self.run_search(text)

    def run_search(self,text):

        try:
            rule = self.grammar.ruleFromString( text )

            songs = naive_search(self.song_library,rule)

            self.setSongs(songs)

        except ParseError as e:
            self.edit_search.setStyleSheet("background: #CC0000;")
            self.lbl_error.setText("%s"%e)
            self.lbl_error.show()

    def setSongs(self,songs):

        self.tbl_remote.setData(songs)
        self.edit_search.setStyleSheet("")
        self.lbl_error.hide()
        self.lbl_search.setText("%d/%d"%(len(songs),len(self.song_library)))

    def getNewClient(self):

        client = ApiClient(self.edit_hostname.text().strip())
        client.setApiKey(self.edit_apikey.text().strip())
        client.setApiUser(self.edit_username.text().strip())

        return client

    def onConnectClicked(self):

        client = self.getNewClient()

        basedir = self.edit_dir.text().strip()

        self.btn_connect.setEnabled(False)

        job = ConnectJob(client,basedir)
        job.newLibrary.connect(self.onNewLibrary)
        job.finished.connect(lambda:self.btn_connect.setEnabled(True))
        self.dashboard.startJob(job)

    def onNewLibrary(self,songs):
        self.song_library = songs
        self.setSongs(songs)

    def action_downloadSelection(self,items):

        client = ApiClient(self.edit_hostname.text())
        client.setApiKey(self.edit_apikey.text())
        client.setApiUser(self.edit_username.text())

        job = DownloadJob(client,items,self.edit_dir.text())
        self.dashboard.startJob(job)

    def onHistoryPullClicked(self):
        client = self.getNewClient()
        job = HistoryPullJob(client)
        self.dashboard.startJob(job)

    def onHistoryPushClicked(self):
        client = self.getNewClient()
        job = HistoryPushJob(client)
        self.dashboard.startJob(job)

    def onHistoryDeleteClicked(self):
        client = self.getNewClient()
        job = HistoryDeleteJob(client)
        self.dashboard.startJob(job)