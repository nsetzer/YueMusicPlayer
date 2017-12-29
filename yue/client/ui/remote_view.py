
import os, sys

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

import traceback


from yue.core.song import Song, SongSearchGrammar
from yue.core.search import naive_search, ParseError, SearchGrammar, \
    AndSearchRule, ExactSearchRule
from yue.core.sqlstore import SQLStore
from yue.core.library import Library
from yue.core.history import History
from yue.core.settings import Settings
# from yue.core.api import ApiClient
from yue.core.api2 import ApiClient, ApiClientWrapper
from yue.qtcommon.explorer.jobs import Job, Dashboard

from yue.qtcommon.Tab import Tab
from yue.qtcommon.SongTable import SongTable

from yue.client.ui.library_view import LineEdit_Search

from urllib.error import HTTPError

import datetime
from yue.core.search import AndSearchRule, ExactSearchRule, GreaterThanEqualSearchRule

SONG_ALL = 0
SONG_SYNCED = 3
SONG_REMOTE = 1
SONG_LOCAL = 2

class RemoteTable(SongTable):
    """docstring for RemoteTable"""

    def __init__(self, parent):
        super(RemoteTable, self).__init__(parent)

        self.addRowTextColorComplexRule(self.localSongRule,
            self.color_text_played_not_recent)

        self.addRowTextColorComplexRule(self.remoteSongRule,
            self.color_text_played_recent)

    def localSongRule(self, row):
        return self.data[row][Song.remote] == SONG_LOCAL

    def remoteSongRule(self, row):
        return self.data[row][Song.remote] == SONG_REMOTE

    def mouseReleaseRight(self, event):

        items = self.getSelection()

        menu = QMenu(self)

        enable_download = all([s[Song.remote] == SONG_REMOTE for s in items])
        enable_upload = all([s[Song.remote] == SONG_LOCAL for s in items])

        act = menu.addAction("Download")
        act.triggered.connect(
            lambda: self.parent().action_downloadSelection(items))
        # act.setEnabled(enable_download)

        act = menu.addAction("Upload Metadata")
        act.triggered.connect(
            lambda: self.parent().action_uploadSelection(items))
        # act.setEnabled(enable_upload)

        action = menu.exec_(event.globalPos())

    # disable song drag and drop on this table
    # the file paths are likely invalid.

    def dragEnterEvent(self, event):
        event.ignore()

    def dragMoveEvent(self, event):
        event.ignore()

    def dropEvent(self, event):
        event.ignore()

class DownloadJob(Job):
    """docstring for DownloadJob"""

    def __init__(self, client, songs, dir_base):
        super(DownloadJob, self).__init__()
        self.client = client
        self.songs = songs
        self.dir_base = dir_base
        self._iterprogress = 0

    def doTask(self):

        lib = Library.instance().reopen()
        for i, song in enumerate(self.songs):
            self._iterprogress = float(i) / len(self.songs)
            path = self.client.download_song(self.dir_base, song, self._dlprogress)
            temp = song.copy()
            temp[Song.path] = path
            del temp[Song.artist_key]
            del temp[Song.remote]  # delete it before adding to db
            # add the song to the library if the key does not exist
            try:
                if temp[Song.uid]:
                    lib.songFromId(temp[Song.uid])
                else:
                    lib.insert(**temp)
            except KeyError:
                lib.insert(**temp)
            song[Song.remote] = SONG_SYNCED  # no longer remote

    def _dlprogress(self, x, y):
        p = self._iterprogress + (x / y) / len(self.songs)
        self.setProgress(int(100 * p))

class DownloadMetadataJob(Job):
    """docstring for DownloadJob"""

    def __init__(self, client, songs):
        super(DownloadMetadataJob, self).__init__()
        self.client = client
        self.songs = songs
        self._iterprogress = 0

    def doTask(self):

        records = {}

        lib = Library.instance().reopen()
        for i, song in enumerate(self.songs):
            self._iterprogress = float(i) / len(self.songs)
            if song[Song.remote] != SONG_SYNCED:
                continue
            self._dlprogress()

            temp = song.copy()
            uid = temp[Song.uid]
            del temp[Song.path]
            del temp[Song.artist_key]
            del temp[Song.remote]
            del temp[Song.uid]
            for  key in ["id", "art_path", "domain_id", "user_id", "file_size"]:
                if key in temp:
                    del temp[key]

            records[uid] = temp

        lib.update_all(records)

    def _dlprogress(self):
        p = self._iterprogress
        self.setProgress(int(100 * p))

class UploadJob(Job):
    """docstring for DownloadJob"""

    def __init__(self, client, songs, dir_base, upload_filepath=True):
        super(UploadJob, self).__init__()
        self.client = client
        self.songs = songs

        if not dir_base.endswith("/"):
            dir_base += "/"

        self.dir_base = dir_base

        self._iterprogress = 0
        self.upload_filepath = upload_filepath

    def doTask(self):

        lib = Library.instance().reopen()

        updates = []
        for i, song in enumerate(self.songs):
            self._iterprogress = float(i) / len(self.songs)
            self._ulprogress(1,1)

            _song = song.copy()
            if self.upload_filepath:
                path = _song[Song.path]
                _path = path.lower().replace("\\","/")
                _root = self.dir_base.lower().replace("\\","/")
                if _path.startswith(_root):
                    # remove the base from the path
                    path = path[len(self.dir_base):]
                    _song[Song.path] = path
                else:
                    # the file does not start with the given base,
                    # remove the path from the request to prevent updating
                    # the filepath
                    del _song[Song.path]
            else:
                del _song[Song.path]

            try:
                if _song[Song.remote] == SONG_LOCAL:
                    print("create %s" % song[Song.uid])
                    song_id = self.client.library_create_song(
                        _song, self._ulprogress)
                    song[Song.remote] = SONG_SYNCED  # no longer local

                elif _song[Song.remote] == SONG_SYNCED:
                    updates.append(_song)

                else:
                    print("cannot upload remote song %s" % song[Song.uid])
            except HTTPError as e:
                print("%s: %s" % (e,e.reason))

        try:
            print("update %d songs" % len(updates))

            for i in range(0,len(updates),100):
                self._iterprogress = float(i) / len(updates)
                self._ulprogress(1,1)
                self.client.library_update_songs(updates[i:i+100], self._ulprogress)
        except HTTPError as e:
            print("%s: %s" % (e,e.reason))


    def _ulprogress(self, x, y):
        p = self._iterprogress + (x / y) / len(self.songs)
        self.setProgress(int(100 * p))

class ConnectJob(Job):
    """docstring for ConnectJob"""
    newLibrary = pyqtSignal(list)
    newApiKey = pyqtSignal(str, str)  # username, apikey

    def __init__(self, client, basedir):
        super(ConnectJob, self).__init__()
        self.client = client
        self.basedir = basedir

    def addToDbIfMissing(self, lib, song):
        """
        if we found the song locally, but not in the database
        add the song record to the database
        """
        try:
            local_song = lib.songFromId(song[Song.uid])
        except KeyError:
            temp = song.copy()
            del temp['remote']
            del temp['artist_key']
            lib.insert(**temp)

    def _dlprogress(self, x, y):
        # downloading accounts  for 90% of the progress bar
        # the last 10% is for post processing.
        self.setProgress(int(90 * x / y))

    def doTask(self):

        username = self.client.getUserName()
        if ":" in username:
            username, password = username.split(":")
            user = self.client.login(username, password)
            self.newApiKey.emit(username, user['apikey'])
            print(username)
            print(user['apikey'])

        lib = Library.instance().reopen()

        remote_songs = self.client.connect(callback=self._dlprogress)
        local_map = {s['uid']: s for s in lib.search(None)}

        for song in remote_songs:

            # match by id
            if song[Song.uid] in local_map:
                local_song = local_map[song[Song.uid]]
                del local_map[song[Song.uid]]
                song[Song.path] = local_song[Song.path]
                song[Song.remote] = SONG_SYNCED

            else:
                # not found locally
                song[Song.remote] = SONG_REMOTE
                # match by path
                # path = self.client.local_path(self.basedir, song)
                # if os.path.exists(path):
                #    song[Song.path] = path
                #    song[Song.remote] = SONG_SYNCED
                #    # self.addToDbIfMissing(lib, song)
                #    continue

        # songs not found on remote
        local_songs = list(local_map.values())
        for song in local_songs:
            song[Song.remote] = SONG_LOCAL

        songs = remote_songs + local_songs

        clss = {0: 0, 1: 0, 2: 0, 3:0}
        for s in songs:
            clss[s[Song.remote]] += 1
        print(clss)

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

        hist = History.instance().reopen()

        ts = int((datetime.datetime.now() - datetime.timedelta(28)).timestamp())

        records = []
        page_size = 500
        result = self.client.history_get(hist, ts, None, 0, page_size)
        records += result

        page = 1
        num_pages = 20
        while len(result) > 0 and page < 20:
            p = 90.0 * (page + 1) / num_pages
            self.setProgress(p)
            result = self.client.history_get(hist, ts, None, page, page_size)
            records += result
            page += 1

        print("num history pages: %d" % page)
        print("num history records: %d" % len(records))

        title = "Import History"
        message = "Import %d records?" % len(records)
        options = ["cancel", "ok"]
        i = self.getInput(title, message, options)

        if i > 0:
            #hist = History.instance().reopen()
            # hist._import(records)
            lib = Library.instance().reopen()
            lib.import_record(records)

class HistoryPushJob(Job):
    def __init__(self, client):
        super(HistoryPushJob, self).__init__()
        self.client = client

    def doTask(self):
        hist = History.instance().reopen()

        ts = int((datetime.datetime.now() - datetime.timedelta(28)).timestamp())

        rule = AndSearchRule(
                [ExactSearchRule("column", "playtime"),
                 GreaterThanEqualSearchRule("date", ts, type_=int)])
        # get all records in the local database
        records = hist.export(rule)

        self.client.history_put(records)

"""
class HistoryDeleteJob(Job):
    def __init__(self, client):
        super(HistoryDeleteJob, self).__init__()
        self.client = client

    def doTask(self):
        self.client.history_delete()

class HistoryHardSyncJob(Job):
    '''
    take meta data  from a list of songs and apply
    it to the internal library
    '''

    def __init__(self, songs):
        super(HistoryHardSyncJob, self).__init__()
        self.songs = songs

    def doTask(self):

        lib = Library.instance().reopen()

        updates = {}
        for i, song in enumerate(self.songs):
            # skip songs that are not local
            if song[Song.remote] != SONG_SYNCED:
                continue

            self.setProgress(90.0 * (i + 1.0) / len(self.songs))

            exif = {}

            for field in Song.textFields():
                exif[field] = song[field]

            for field in Song.numberFields():
                exif[field] = song[field]

            for field in Song.dateFields():
                exif[field] = song[field]

            if Song.uid in exif:
                del exif[Song.uid]

            if Song.path in exif:
                del exif[Song.path]

            updates[song[Song.uid]] = exif

        title = "Update Metadata"
        message = "Overwrite metadata for %d songs?" % len(updates)
        options = ["cancel", "ok"]
        i = self.getInput(title, message, options)
        if i > 0:
            lib.update_all(updates)

        self.setProgress(100)

class HistoryHardPushJob(Job):
    '''
    push the local library to remote

    this includes the file path.
    the server must have the path alternatives set
    to correctly locate songs after a hard sync
    '''

    def __init__(self, client):
        super(HistoryHardPushJob, self).__init__()
        self.client = client

    def doTask(self):

        lib = Library.instance().reopen()
        songs = lib.search("", limit=10)
        self.client.library_put(songs)
"""

class RemoteSongSearchGrammar(SongSearchGrammar):
    """docstring for SongSearchGrammar

    A SongSearchGrammar that allows for searching a remote database.
    A "remote" field is set true if the song has not been downloaded
    """

    def __init__(self):
        super(RemoteSongSearchGrammar, self).__init__()

    def translateColumn(self, colid):
        if colid == Song.remote:
            return Song.remote
        return super().translateColumn(colid)

class RemoteView(Tab):
    """docstring for RemoteView"""

    def __init__(self, parent=None):
        super(RemoteView, self).__init__(parent)

        self.client = None

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
        self.tbl_remote.showColumnHeader(True)
        self.tbl_remote.showRowHeader(False)

        self.edit_search = LineEdit_Search(self, self.tbl_remote, "Search Remote")

        self.btn_connect = QPushButton("Connect", self)

        lbl = QLabel("Hostname:")
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.grid_info.addWidget(lbl, 0, 0)
        self.grid_info.addWidget(self.edit_hostname, 0, 1)

        lbl = QLabel("User Name:")
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.grid_info.addWidget(lbl, 0, 2)
        self.grid_info.addWidget(self.edit_username, 0, 3)

        lbl = QLabel("Local Directory:")
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.grid_info.addWidget(lbl, 1, 0)
        self.grid_info.addWidget(self.edit_dir, 1, 1)

        lbl = QLabel("API Key:")
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.grid_info.addWidget(lbl, 1, 2)
        self.grid_info.addWidget(self.edit_apikey, 1, 3)

        self.lbl_error  = QLabel("")
        self.lbl_search  = QLabel("")

        self.cb_remote = QComboBox(self)
        self.cb_remote.addItem("Show All", SONG_ALL)
        self.cb_remote.addItem("Show Remote", SONG_REMOTE)  # index 1
        self.cb_remote.addItem("Show Local", SONG_LOCAL)   # index 2
        self.cb_remote.addItem("Show Sync", SONG_SYNCED)    # index 3
        self.cb_remote.currentIndexChanged.connect(self.onRemoteIndexChanged)

        #self.btn_hardsync = QPushButton("Hard Sync", self)
        #self.btn_hardpush = QPushButton("Hard Push", self)
        self.btn_push     = QPushButton("Push", self)
        self.btn_pull     = QPushButton("Pull", self)
        self.btn_upload   = QPushButton("Upload", self)
        self.btn_download = QPushButton("Download", self)
        #self.btn_delete   = QPushButton("Delete", self)

        self.hbox_search.addWidget(self.btn_connect)
        self.hbox_search.addWidget(self.edit_search)
        self.hbox_search.addWidget(self.cb_remote)
        self.hbox_search.addWidget(self.lbl_search)

        self.hbox_admin.addWidget(QLabel("History:"))
        #self.hbox_admin.addWidget(self.btn_hardsync)
        #self.hbox_admin.addWidget(self.btn_hardpush)
        self.hbox_admin.addWidget(self.btn_push)
        self.hbox_admin.addWidget(self.btn_pull)
        #self.hbox_admin.addWidget(self.btn_delete)

        self.hbox_admin.addWidget(QLabel("Library:"))
        #self.hbox_admin.addWidget(self.btn_hardsync)
        #self.hbox_admin.addWidget(self.btn_hardpush)
        self.hbox_admin.addWidget(self.btn_upload)
        self.hbox_admin.addWidget(self.btn_download)
        #self.hbox_admin.addWidget(self.btn_delete)


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
        self.btn_upload.clicked.connect(self.onLibraryUploadClicked)
        self.btn_download.clicked.connect(self.onLibraryDownloadClicked)
        #self.btn_delete.clicked.connect(self.onHistoryDeleteClicked)
        #self.btn_hardsync.clicked.connect(self.onHistoryHardSyncClicked)
        #self.btn_hardpush.clicked.connect(self.onHistoryHardPushClicked)

        self.tbl_remote.update_data.connect(self.refresh)  # on sort...

        self.grammar = RemoteSongSearchGrammar()
        self.song_library = []
        """
        # generate simple library for testing purposes.
        songs = Library.instance().search("",limit=100)
        for song in songs:
            song['remote'] = SONG_REMOTE
        self.song_library = songs
        """
        self.setSongs(self.song_library)

    def onSearchTextChanged(self):

        text = self.edit_search.text()
        self.run_search(text)

    def refresh(self):
        self.run_search(self.edit_search.text())

    def run_search(self, text):

        try:
            rule = self.grammar.ruleFromString(text)
            limit = self.grammar.getMetaValue("limit", None)
            offset = self.grammar.getMetaValue("offset", 0)

            # TODO: instead of comparing index, store the
            # enum value with the combo box item
            remote = int(self.cb_remote.currentData())
            if remote == SONG_SYNCED:
                rule = AndSearchRule.join(rule,
                    ExactSearchRule(Song.remote, SONG_SYNCED, type_=int))
            elif remote == SONG_LOCAL:
                rule = AndSearchRule.join(rule,
                    ExactSearchRule(Song.remote, SONG_LOCAL, type_=int))
            elif remote == SONG_REMOTE:
                rule = AndSearchRule.join(rule,
                    ExactSearchRule(Song.remote, SONG_REMOTE, type_=int))

            songs = naive_search(self.song_library, rule,
                orderby=self.tbl_remote.sort_orderby,
                reverse=self.tbl_remote.sort_reverse,
                limit=limit, offset=offset)

            self.setSongs(songs)

        except ParseError as e:
            self.edit_search.setStyleSheet("background: #CC0000;")
            self.lbl_error.setText("%s" % e)
            self.lbl_error.show()

    def setSongs(self, songs):

        self.tbl_remote.setData(songs)
        self.edit_search.setStyleSheet("")
        self.lbl_error.hide()
        self.lbl_search.setText("%d/%d" % (len(songs), len(self.song_library)))

    def getNewClient(self):

        hostname = self.edit_hostname.text().strip()
        apikey = self.edit_apikey.text().strip()
        username = self.edit_username.text().strip()

        if self.client is None:
            self.client = ApiClientWrapper(ApiClient(hostname))
            self.client.setApiKey(apikey)
            self.client.setApiUser(username)

        return self.client

    def onConnectClicked(self):

        client = self.getNewClient()

        basedir = self.edit_dir.text().strip()

        self.btn_connect.setEnabled(False)

        job = ConnectJob(client, basedir)
        job.newLibrary.connect(self.onNewLibrary)
        job.newApiKey.connect(self.onNewApiKey)
        job.finished.connect(lambda: self.btn_connect.setEnabled(True))
        self.dashboard.startJob(job)

    def onRemoteIndexChanged(self, idx):
        self.refresh()

    def onNewApiKey(self, username, apikey):

        self.edit_username.setText(username)
        self.edit_apikey.setText(apikey)

    def onNewLibrary(self, songs):
        # TODO: convert the connect button to a disconnect button
        self.song_library = songs
        self.refresh()  # run the current query, update table

    def action_downloadSelection(self, items):
        client = self.getNewClient()
        job = DownloadJob(client, items, self.edit_dir.text())
        self.dashboard.startJob(job)

    def action_uploadSelection(self, items):
        client = self.getNewClient()
        upload_filepath = True
        job = UploadJob(client, items, self.edit_dir.text(), upload_filepath)
        job.finished.connect(self.refresh)
        self.dashboard.startJob(job)

    def onHistoryPullClicked(self):
        client = self.getNewClient()
        job = HistoryPullJob(client)
        self.dashboard.startJob(job)

    def onHistoryPushClicked(self):
        client = self.getNewClient()
        job = HistoryPushJob(client)
        self.dashboard.startJob(job)

    def onLibraryUploadClicked(self):
        client = self.getNewClient()
        upload_filepath = True
        job = UploadJob(client, self.song_library, self.edit_dir.text(), upload_filepath)
        job.finished.connect(self.refresh)
        self.dashboard.startJob(job)

    def onLibraryDownloadClicked(self):
        client = self.getNewClient()
        upload_filepath = True
        job = DownloadMetadataJob(client, self.song_library)
        job.finished.connect(self.refresh)
        self.dashboard.startJob(job)


    # def onHistoryDeleteClicked(self):
    #     client = self.getNewClient()
    #     job = HistoryDeleteJob(client)
    #     self.dashboard.startJob(job)
    # def onHistoryHardSyncClicked(self):
    #     client = self.getNewClient()
    #     job = HistoryHardSyncJob(self.song_library)
    #     self.dashboard.startJob(job)
    # def onHistoryHardPushClicked(self):
    #     client = self.getNewClient()
    #     job = HistoryHardPushJob(client)
    #     self.dashboard.startJob(job)
