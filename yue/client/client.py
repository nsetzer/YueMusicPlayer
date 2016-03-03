#! cd ../.. && python34 test/test_client.py

import os,sys
import time
from datetime import datetime
import urllib
import argparse

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from sip import SIP_VERSION_STR, delete as sip_delete

from ..core.sqlstore import SQLStore
from ..core.settings import Settings
from ..core.library import Library
from ..core.playlist import PlaylistManager
from ..core.sound.device import MediaState
from ..core.song import Song
from ..core.util import string_quote, backupDatabase
from ..core.repl import YueRepl, ReplArgumentParser

from . import resource
from .controller import newDevice, PlaybackController
try:
    if os.name == 'nt':
        from .hook2 import HookThread
    else:
        HookThread = None
except ImportError as e:
    sys.stderr.write("hook import: %s\n"%e)
    HookThread = None
try:
    from .remote import SocketListen
except ImportError as e:
    sys.stderr.write("socket import: %s\n"%e)
    SocketListen = None

from .ui.library_view import LibraryView
from .ui.quickselect_view import QuickSelectView
from .ui.explorer_view import ExplorerView, explorerOpen
from .ui.playlist_view import PlayListViewWidget
from .ui.playlistedit_view import PlaylistEditView
from .ui.rename_dialog import RenameDialog
from .ui.openpl_dialog import OpenPlaylistDialog
from .ui.newpl_dialog import NewPlaylistDialog
from .ui.visualizer import BassVisualizer
from .ui.ingest_dialog import IngestProgressDialog
from .ui.updatetags_dialog import SelectSongsDialog,UpdateTagProgressDialog

from .widgets.logview import LogView
from .widgets.LineEdit import LineEditRepl
from .widgets.playbutton import PlayButton
from .widgets.songview import CurrentSongView, SongPositionView
from .widgets.closebutton import  CloseTabButton
from .widgets.volume import VolumeController

from .DSP.peqwidget import WidgetOctaveEqualizer
from .DSP.equalizer import DialogVolEqLearn

class ClientRepl(object):
    """ augments the basic repl given in yue.core """

    def __init__(self, client):
        super().__init__()
        self.client = client

        self.actions = {}
        self.helptopics = {}

        self.actions["new"] = self.exnew
        self.actions["open"] = self.exopen
        self.actions["backup"] = self.exbackup
        self.actions["explorer"] = self.exexplorer
        self.actions["diag"] = self.exdiag

        self.actions["quit"] = self.exexit
        self.actions["exit"] = self.exexit

        self.helptopics['search'] = """ information on search format

        Examples:
            `artist = Soundgarden` return all songs with a given artist
            `date = today`
            `added = this week`
            `(artist = one || artist = two) && playcount > 5`

        Search Fields:

        path, text, artist, composer, album, title, genre, country, lang, comment
        uid, year, album_index, length, date, added,, playcount, skipcount

        Special Search Fields:

        text : simulataneous search of artist, composer, album, title, genre,
               country, lang, and comment.

               the default search field, when none is given.

        length: accepts two formats
            N : a duration specified in seconds
            [dd:hh:]mm:ss : a duration specified in days, hours, minutes seconds.

        data, added: accept three different formats

            integer: a count of days.
                `date < 7` returns any song played in the last week
            date   : relative to a fixed date in year/month/day format
                `date = 16/05/01` returns any song played on the given date
            string : a string using natural language
                `date = today` return any song played today
                valid values:
                    'today'
                    'last [day|week|month|year]'
                    'older than x [day|week|month|year][s]'

        Operations:

        text:
            =   : partial string match
            ==  : exact string match
            !=  : don't match if there is a partial match
            !== : don't match if there is an exact match

        number:
            =     : match exactly a given value
                    `playcount = 5`
            !=    : don't match a  given value
            <, <= : match less than, or less than or equal to
                    `playcount <= 5`
            >, >= : match greater than, or greater than or equal to.
                    `playcount >= 5`

        Other:

        logical and (&&) is optional between fields
        the following are equivalent:
            'artist=one && artist=two'
            'artist=one artist=two'


        Old Style mode:

            `.art one two` is the same as 'artist=one && artist=two'





        """

    def register(self, repl):
        for name,func in self.actions.items():
            repl.registerAction(name,func)

        for name,string in self.helptopics.items():
            repl.registerTopic(name,string)

    def exexit(self,args):
        """ exit application """
        QApplication.quit()

    def exnew(self, args):
        """
        $0 --preset=<int> --search=<str> --limit=<int>

        --search -s : select from songs matching query string
        --limit  -l : select N songs
        --preset -p : use a query preset (instead of --search)
        """
        args = ReplArgumentParser(args,{'p':'preset', 's':'search', 'l':'limit'})

        limit = 50
        if 'limit' in args:
            query = int(args['limit'])

        query = None
        if 'search' in args:
            query = str(args['search'])

        songs = Library.instance().search(query, orderby=Song.random, limit=limit)
        pl = PlaylistManager.instance().openCurrent()
        lst = [ song['uid'] for song in songs ]
        pl.set( lst )
        self.client.plview.updateData()

    def exopen(self, args):
        """
        $0 [-c]
        -c : create if playlist does not exist
        """
        args = ReplArgumentParser(args)
        args.assertMinArgs( 1 )

        self.client.openPlaylistEditor( args[0] )

    def exbackup(self, args):
        """ backup the database """
        self.client.backup_database()

    def exexplorer(self, args):
        """ open directory of the database in explorer """
        dbpath = os.path.realpath(Library.instance().sqlstore.path())
        dirpath = os.path.split(dbpath)[0]
        explorerOpen( dirpath )

    def exdiag(self, args):
        """ open directory of the database in explorer """

        self.client.keyhook.diag = not self.client.keyhook.diag
        print(self.client.keyhook.diag)

class MainWindow(QMainWindow):
    """docstring for MainWindow"""

    def __init__(self, diag, device, version):
        super(MainWindow, self).__init__()

        self.setAcceptDrops( True )
        self.version = version
        self.device = device
        self.controller = PlaybackController( device, self );
        self.repl = YueRepl( device )
        self.clientrepl = ClientRepl( self )
        self.clientrepl.register( self.repl )
        #self.keyhook = KeyHook(self.controller, False)
        if HookThread is not None:
            self.keyhook = HookThread()
            self.keyhook.start()
            self.keyhook.playpause.connect(self.device.playpause)
            self.keyhook.play_next.connect(self.controller.play_next)
            self.keyhook.play_prev.connect(self.controller.play_prev)
            sys.stdout.write("Keyboard Hook initialized.\n")
        else:
            sys.stdout.write("Unable to initialize Keyboard Hook.\n")

        if SocketListen is not None:
            port = 15123
            if hasattr(sys,"_MEIPASS"):
                port = 15124 # use a different port when frozen
            self.remotethread = SocketListen(port=port,parent=self)
            self.remotethread.message_recieved.connect(self.executeCommand)
            self.remotethread.start()
            sys.stdout.write("Remote Thread initialized.\n")
        else:
            sys.stdout.write("Unable to initialize Remote Thread.\n")

        self.dialog_ingest = None
        self.dialog_update = None
        self._init_ui( diag)
        self._init_values()
        self._init_menubar()

    def _init_ui(self, diag):

        self.bar_menu = QMenuBar( self )
        self.setMenuBar( self.bar_menu )

        self.bar_status = QStatusBar( self )
        self.lbl_status = QLabel(self)
        self.bar_status.addWidget( self.lbl_status)
        self.setStatusBar( self.bar_status )

        self.tabview = QTabWidget( self )
        self.setCentralWidget(self.tabview)

        # init primary views
        self.libview = LibraryView(self);
        self.libview.create_playlist.connect(self.createNewPlaylist)
        self.libview.set_playlist.connect(self.setCurrentPlaylist)
        self.libview.setMenuCallback( self.addSongActions )
        self.libview.notify.connect( self.update_statusbar_message )

        self.quickview = QuickSelectView(self);
        self.quickview.create_playlist.connect(self.createQuickPlaylist)

        self.expview = ExplorerView(self);
        self.expview.play_file.connect(self.controller.playOneShot)
        self.expview.execute_search.connect(self.executeSearch)

        self.plview = PlayListViewWidget(self);
        self.plview.setMenuCallback( self.addSongActions )
        self.plview.play_index.connect( self.controller.play_index )

        self.songview = CurrentSongView( self );
        self.songview.setMenuCallback( self.addSongActions )

        self.posview = SongPositionView( self );
        self.posview.seek.connect(self.on_seek)
        self.posview.next.connect(self.controller.play_next)
        self.posview.prev.connect(self.controller.play_prev)

        h = self.songview.height()
        self.btn_playpause = PlayButton( self )
        self.btn_playpause.setFixedHeight( h )
        self.btn_playpause.setFixedWidth( h )
        self.btn_playpause.on_play.connect(self.controller.playpause)
        self.btn_playpause.on_stop.connect(self.controller._setStop)

        self.edit_cmd = LineEditRepl( self.repl, self );
        self.edit_cmd.setFocus()
        self.edit_cmd.setPlaceholderText("Command Input")

        self.volcontroller = VolumeController(self)
        self.volcontroller.volume_slider.valueChanged.connect(self.setVolume)

        # note: visible state is not stored for the playlist,
        # it should always be displayed at startup
        self.dock_list = QDockWidget()
        self.dock_list.setWidget( self.plview )
        self.dock_list.setAllowedAreas(Qt.LeftDockWidgetArea|Qt.RightDockWidgetArea)
        self.dock_list.visibilityChanged.connect(self.showhide_list)

        self.dock_diag = QDockWidget()
        self.dock_diag.setWidget( diag )
        self.dock_diag.setAllowedAreas(Qt.BottomDockWidgetArea)
        self.dock_diag.visibilityChanged.connect(self.showhide_diag)

        # add widgets to layout

        self.addDockWidget (Qt.RightDockWidgetArea, self.dock_list)
        self.addDockWidget (Qt.BottomDockWidgetArea, self.dock_diag)

        self.tabview.addTab( self.libview, QIcon(':/img/app_note.png'), "Library")
        self.tabview.addTab( self.quickview, QIcon(':/img/app_fav.png'), "Quick Select")
        self.tabview.addTab( self.expview, QIcon(':/img/app_folder.png'), "Explorer")
        if self.controller.dspSupported():
            self.peqview = WidgetOctaveEqualizer();
            # TODO: we should not be passing controller into these widgets
            self.audioview = BassVisualizer(self.controller, self)
            self.audioview.setFixedHeight( 48 )
            self.audioview.start()
            self.peqview.gain_updated.connect( self.controller.setEQGain )
            self.tabview.addTab( self.peqview, QIcon(':/img/app_eq.png'), "Equalizer")
            self.plview.vbox.insertWidget(0, self.audioview)
        self.tabview.setCornerWidget( self.volcontroller )

        self.hbox = QHBoxLayout();
        self.hbox.addWidget( self.btn_playpause )
        self.hbox.addWidget( self.songview )

        # TODO: this is currently the biggest hack here
        self.plview.vbox.insertLayout(0, self.hbox)
        self.plview.vbox.insertWidget(0, self.posview)
        self.plview.vbox.insertWidget(0, self.edit_cmd)

    def _init_values(self):

        s = Settings.instance()
        vol = s['volume']
        self.volcontroller.volume_slider.setValue( vol )
        self.controller.device.setVolume( vol/100.0 )

        if not s['ui_show_console']:
            self.edit_cmd.hide()

        if not s['ui_show_error_log']:
            self.dock_diag.hide()

        #if s['enable_keyboard_hook']:
        #    pass # TODO enable keyhook here

        self.quickview.setFavorites(Song.artist,s["ui_quickselect_favorite_artists"])
        self.quickview.setFavorites(Song.genre,s["ui_quickselect_favorite_genres"])
        self.libview.setColumnState(s["ui_library_column_order"])

        pl = PlaylistManager.instance().openCurrent()
        if len(pl)==0:
            songs = Library.instance().search(None, orderby=Song.random, limit=5)
            lst = [ s['uid'] for s in songs ]
            pl.set( lst )
        self.plview.setPlaylist( Library.instance(), pl)

    def _init_menubar(self):
        s = Settings.instance()
        menu = self.bar_menu.addMenu("&File")
        menu.addAction("Exit",QApplication.quit)

        menu = self.bar_menu.addMenu("&Music")
        menu.addAction(QIcon(":/img/app_newlist.png"),"New Playlist",self.createNewPlaylist)
        menu.addSeparator()
        menu.addAction("New Editable Playlist", self.newEditablePlaylist)
        menu.addAction("Open Editable Playlist", self.openEditablePlaylist)
        menu.addSeparator()
        menu.addAction("Update Song Tags",self.updateTags)
        if self.controller.dspSupported():
            menu.addAction("Run Equalizer",self.runEqualizer)
            self.action_equalizer = menu.addAction("", self.toggleEQ)
            self.action_equalizer.setIcon( QIcon(":/img/app_check.png"))
            if s['volume_equalizer']:
                self.action_equalizer.setIconVisibleInMenu ( True )
                self.action_equalizer.setText("Disable Equalizer")
                self.songview.setEQEnabled(True)
            else:
                self.action_equalizer.setIconVisibleInMenu ( False )
                self.action_equalizer.setText("Enable Equalizer")
                self.songview.setEQEnabled(False)
            menu.addSeparator()
        self.action_undo_delete = menu.addAction("Undo Delete")
        self.action_undo_delete.setDisabled( True )

        menu = self.bar_menu.addMenu("&View")
        self.action_view_console = menu.addAction("",self.toggleConsoleVisible)
        if s['ui_show_console']:
            self.action_view_console.setText("Hide Console")
        else:
            self.action_view_console.setText("Show Console")

        self.action_view_list = menu.addAction("Show Play List",lambda : self.toggleDialogVisible(self.dock_list))
        self.action_view_logger  = menu.addAction("",lambda : self.toggleDialogVisible(self.dock_diag))
        if s['ui_show_error_log']:
            self.action_view_logger.setText("Hide Error Log")
        else:
            self.action_view_logger.setText("Show Error Log")
        self.action_view_tree    = menu.addAction("Show Tree View")
        self.action_view_tree.setDisabled(True)

        menu = self.bar_menu.addMenu("&?")
        # sip version, qt version, python version, application version
        about_text = ""
        v = sys.version_info
        about_text += "Version: %s\n"%self.version
        about_text += "Python Version: %d.%d.%d-%s\n"%(v.major,v.minor,v.micro,v.releaselevel)
        about_text += "Qt Version: %s\n"%QT_VERSION_STR
        about_text += "sip Version: %s\n"%SIP_VERSION_STR
        about_text += "PyQt Version: %s\n"%PYQT_VERSION_STR
        about_text += "Playback Engine: %s\n"%self.controller.device.name()
        menu.addAction("About",lambda:QMessageBox.about(self,"Yue Music Player",about_text))

    def closeEvent(self, event):

        s = Settings.instance()

        self.controller.device.pause()

        start = time.time()

        s['ui_show_error_log'] = int(not self.dock_diag.isHidden())
        s['ui_show_console'] = int(not self.edit_cmd.isHidden())
        # hide now, to make it look like the application closed faster
        self.hide()

        self.remotethread.join()
        #self.keyhook.join()

        # record the current volume, but prevent the application
        # from starting muted
        v = self.volcontroller.volume_slider.value()
        s["volume"] = v if v > 0 else 25

        # record the current position of the window
        # application startup will check this is still valid, and try
        # to reposition accordingly
        s["window_width"] = self.width()
        s["window_height"] = self.height()
        s["window_x"] = self.x()
        s["window_y"] = self.y()

        s['ui_library_column_order'] = self.libview.getColumnState();

        s['ui_quickselect_favorite_artists'] = self.quickview.getFavoriteArtists()
        s['ui_quickselect_favorite_genres'] = self.quickview.getFavoriteGenres()

        super(MainWindow,self).closeEvent( event )

        sys.stdout.write("finished saving state (%d)\n"%(time.time()-start))

    def tabIndex(self, widget):
        idx = -1
        for i in range(self.tabview.count()):
            w = self.tabview.widget( i )
            if w is widget:
                idx = i
        return idx

    def renameTab(self,widget,name):
        idx = self.tabIndex( widget )
        if idx >= 0:
            self.tabview.setTabText(idx,name)

    def openPlaylistEditor(self, playlist_name, switchto=False):

        widget = PlaylistEditView(playlist_name)
        widget.on_rename.connect( self.renameTab )
        index = self.tabview.addTab( widget, QIcon(':/img/app_list.png'), playlist_name)
        widget.btn = CloseTabButton( lambda : self.closePlaylistEditorTab( widget ), self)
        self.tabview.tabBar().setTabButton(index,QTabBar.RightSide,widget.btn)
        if switchto:
            self.tabview.setCurrentWidget( widget )

    def closePlaylistEditorTab(self,widget):

        # TODO: check if the tab *can* be closed
        # e.g. if the playlist editor has made changes,
        # ask if the user wants to discard the changes.

        idx = self.tabIndex( widget )
        if idx >= 0:
            self.tabview.removeTab( idx )

    def dragEnterEvent(self,event):
        # event comes from outside the application
        if event.source() is None and self.dialog_ingest is None:
            if event.mimeData().hasUrls():
                event.accept()

    def dropEvent(self,event):
        # event comes from outside the application
        if event.source() is None:
            mdata = event.mimeData()
            if mdata.hasUrls() :
                # accept before processing or explorer will hang
                event.accept()
                paths = [ url.toLocalFile() for url in mdata.urls() if url.isLocalFile() ]
                self.ingestPaths( paths )

    def ingestPaths(self,paths):
        """
        paths: list of files or directories.
        """
        self.dialog_ingest = IngestProgressDialog( paths, self)
        self.dialog_ingest.setOnCloseCallback(self.onIngestExit)
        self.dialog_ingest.start()
        self.dialog_ingest.show()

    def onIngestExit(self):
        self.dialog_ingest = None
        self.libview.run_search("added = today",True)
        print("ingest complete")

    def setVolume(self, vol):

        #Settings.instance()["volume"] = vol
        self.controller.device.setVolume( vol/100.0 )

    def executeSearch(self,query,switch=True):
        #idx = self.tabIndex( self.libview )
        self.libview.run_search(query,setText=True)
        if switch:
            self.tabview.setCurrentWidget(self.libview)

    def executeCommand(self,text):

        try:
            result = self.repl.exec_( text )
        except ValueError as e:
            print(e)

    def exploreDirectory(self, path):
        self.expview.chdir(path, True)
        self.tabview.setCurrentWidget(self.expview)

    def toggleEQ(self):
        self.controller.toggleEQ()
        s = Settings.instance()
        if self.controller.getEQ():
            s["volume_equalizer"] = True
            self.action_equalizer.setIconVisibleInMenu ( True )
            self.action_equalizer.setText("Disable Equalizer")
            self.songview.setEQEnabled(True)
        else:
            s["volume_equalizer"] = False
            self.action_equalizer.setIconVisibleInMenu ( False )
            self.action_equalizer.setText("Enable Equalizer")
            self.songview.setEQEnabled(False)

    def runEqualizer(self):
        # todo: pass in the controller
        self.dialog_eq = DialogVolEqLearn( )
        self.dialog_eq.show()

    def newEditablePlaylist(self):

        #diag = RenameDialog("New Playlist", \
        # "New Editable Playlist","Enter a Playlist name:", self)
        self.openPlaylistEditor( "New Playlist", True )

    def openEditablePlaylist(self):
        diag = OpenPlaylistDialog(self)

        if diag.exec_():
            name = diag.text()
            self.openPlaylistEditor( name, True )

    def addSongActions(self, menu, song ):
        """ common actions for context menus dealing with a song """

        q1 = "artist = %s"%(string_quote(song[Song.artist]))
        menu.addAction("Search for Artist", lambda : self.executeSearch(q1))
        q2 = q1 + " && album = %s"%(string_quote(song[Song.album]))
        menu.addAction("Search for Album", lambda : self.executeSearch(q2))
        menu.addSeparator()
        art = urllib.parse.quote(song[Song.artist])
        q3 = "http://www.songmeanings.net/query/?q=%s&type=artists"%art
        menu.addAction("Find Lyrics", lambda : explorerOpen(q3))
        q4 = "http://en.wikipedia.org/w/index.php?search=%s"%art
        menu.addAction("Wikipedia", lambda : explorerOpen(q4))
        menu.addSeparator()
        q5 = os.path.split(song[Song.path])[0]
        menu.addAction("Explore Containing Folder", lambda: self.exploreDirectory(q5))

    def toggleConsoleVisible(self):
        if self.edit_cmd.isHidden():
            self.action_view_console.setText("Hide Console")
            self.edit_cmd.show()
        else:
            self.action_view_console.setText("Show Console")
            self.edit_cmd.hide()

    def toggleDialogVisible(self, widget):
        if widget.isHidden():
            widget.show()
        else:
            widget.hide()

    def showhide_list(self,b):
        if b:
            self.action_view_list.setText("Hide Play List")
        else:
            self.action_view_list.setText("Show Play List")

    def showhide_diag(self,b):
        if b:
            self.action_view_logger.setText("Hide Error Log")
        else:
            self.action_view_logger.setText("Show Error Log")

    def createQuickPlaylist(self, query):
        s = Settings.instance()
        size =s['playlist_size']
        songs = Library.instance().search(query,orderby=Song.random,limit=size)
        pl = PlaylistManager.instance().openCurrent()
        lst = [ song[Song.uid] for song in songs ]
        pl.set( lst )
        self.controller.play_index( 0 )
        self.plview.updateData()

    def createNewPlaylist(self,query=""):

        s = Settings.instance();
        limit = s['playlist_size']
        presets = s['playlist_presets']
        dialog = NewPlaylistDialog(query,limit=limit,parent=self)
        dialog.setPresets(presets)

        if dialog.exec():

            params = dialog.getQueryParams()
            songs = Library.instance().search( \
                        params['query'],
                        orderby=Song.random,
                        limit=params['limit'])
            lst = [ song[Song.uid] for song in songs ]
            pl = PlaylistManager.instance().openCurrent()
            pl.set( lst )
            self.controller.play_index( 0 )
            self.plview.updateData()

    def setCurrentPlaylist(self, uids,play=False):
        pl = PlaylistManager.instance().openCurrent()
        pl.insert_next( uids )
        if play:
            self.controller.play_next()
        self.plview.updateData()

    def updateTags(self):

        if self.dialog_update is not None:
            return

        dialog = SelectSongsDialog(parent=self)

        if dialog.exec_():
            query = dialog.getQuery()
            self.dialog_update = UpdateTagProgressDialog(query,self)
            self.dialog_update.setOnCloseCallback(self.onUpdateTagsExit)
            self.dialog_update.start()
            self.dialog_update.show()
            dialog.setParent(None)

    def onUpdateTagsExit(self):
        if self.dialog_update is not None:
            self.dialog_update.setParent(None)
            #self.dialog_update.deleteLater()
            self.dialog_update = None

    def on_seek(self,position):

        self.controller.device.seek( position )
        if self.controller.device.isPaused():
            self.controller.device.play()

    def update_statusbar_message(self,msg):

        self.lbl_status.setText(msg)

    def backup_database(self):

        s = Settings.instance();
        if s['backup_enabled']:
            dir = s['backup_directory']
            backupDatabase( Library.instance().sqlstore, dir)

    def showWindow(self):

        s = Settings.instance()
        geometry = QDesktopWidget().screenGeometry()
        sw = geometry.width()
        sh = geometry.height()
        # calculate default values
        dw = int(sw*.8)
        dh = int(sh*.8)
        dx = sw//2 - dw//2
        dy = sh//2 - dh//2
        # use stored values if they exist
        cw = s.getDefault("window_width",dw)
        ch = s.getDefault("window_height",dh)
        cx = s.getDefault("window_x",dx)
        cy = s.getDefault("window_y",dy)
        # the application should start wholly on the screen
        # otherwise, default its position to the center of the screen
        if cx < 0 or cx+cw>sw:
            cx = dx
            cw = dw
        if cy < 0 or cy+ch>sh:
            cy = dy
            ch = dh
        self.resize(cw,ch)
        self.move(cx,cy)
        self.show()

def setSettingsDefaults():

    s = Settings.instance()

    s.setDefault("backup_enabled",1)
    s.setDefault("backup_directory","./backup")

    s.setDefault("volume",50)
    s.setDefault("volume_equalizer",0) # off

    s.setDefault("ui_show_console",0) # off
    s.setDefault("ui_show_error_log",0) # off

    s.setDefault("enable_keyboard_hook",1) # on by default

    # when empty, default order is used
    s.setDefault("ui_library_column_order",[])
    s.setDefault("ui_quickselect_favorite_artists",[])
    s.setDefault("ui_quickselect_favorite_genres",[])

    s.setDefault("playlist_size",50)
    s.setDefault("playlist_presets",[
        "ban=0 && date>14",
        ])

def main(version="0.0.0"):

    app = QApplication(sys.argv)
    app.setApplicationName("Yue Music Player - v%s"%version)
    app.setQuitOnLastWindowClosed(True)
    app_icon = QIcon(':/img/icon.png')
    app.setWindowIcon(app_icon)

    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--sound', default="default",
                   help='set sound device: default, bass, dummy')
    args = parser.parse_args()

    with LogView(trace=False,echo=True) as diag:

        plugin_path = "./lib/%s/x86_64"%sys.platform
        if hasattr(sys,"_MEIPASS"):
            plugin_path = sys._MEIPASS

        db_path = "./yue.db"

        sys.stdout.write("Loading database\n")
        sqlstore = SQLStore(db_path)
        Settings.init( sqlstore )
        Library.init( sqlstore )
        PlaylistManager.init( sqlstore )

        setSettingsDefaults()

        sys.stdout.write("Create Sound Device\n")
        pl=PlaylistManager.instance().openCurrent()
        device = newDevice(pl,plugin_path,kind=args.sound)

        sys.stdout.write("Initializing application\n")
        window = MainWindow( diag, device, version )
        window.showWindow()

        try:
            device.load_current( )
        except IndexError:
            sys.stderr.write("error: No Current Song\n")

    sys.exit(app.exec_())

