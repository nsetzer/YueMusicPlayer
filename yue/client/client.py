#! cd ../.. && python34 test/test_client.py

import os,sys
isPython3 = sys.version_info[0]==3
if isPython3:
    unicode = str

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from sip import SIP_VERSION_STR

import time

import yue.client.resource

import urllib

from ..core.sqlstore import SQLStore
from ..core.settings import Settings
from ..core.library import Library
from ..core.playlist import PlaylistManager
from ..core.sound.device import MediaState
from ..core.song import Song
from ..core.repl import YueRepl, ReplArgumentParser

from .ui.library_view import LibraryView
from .ui.quickselect_view import QuickSelectView
from .ui.explorer_view import ExplorerView, explorerOpen
from .ui.playlist_view import PlayListViewWidget
from .ui.playlistedit_view import PlaylistEditView
from .ui.rename_dialog import RenameDialog
from .ui.openpl_dialog import OpenPlaylistDialog
from .ui.newpl_dialog import NewPlaylistDialog

from .widgets.logview import LogView
from .widgets.LineEdit import LineEditRepl
from .widgets.playbutton import PlayButton
from .widgets.songview import CurrentSongView, SongPositionView
from .widgets.closebutton import  CloseTabButton
from .widgets.volume import VolumeController

from .controller import newDevice, PlaybackController
from .hook import KeyHook

from .ui.ingest_dialog import IngestProgressDialog

from .DSP.peqwidget import WidgetOctaveEqualizer
from .DSP.equalizer import DialogVolEqLearn

from .ui.visualizer import BassVisualizer

class ClientRepl(object):
    """ augments the basic repl given in yue.core """

    def __init__(self, client):
        super().__init__()
        self.client = client

        self.actions = {}

        self.actions["new"] = self.exnew
        self.actions["open"] = self.exopen

    def register(self, repl):
        for name,func in self.actions.items():
            repl.registerAction(name,func)

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
        lst = [ s['uid'] for s in songs ]
        pl.set( lst )
        self.client.plview.updateData()

    def exopen(self, args):
        """
        $0 -c
        -c : create if playlist does not exist
        """
        args = ReplArgumentParser(args)
        args.assertMinArgs( 1 )

        self.client.openPlaylistEditor( args[0] )

class MainWindow(QMainWindow):
    """docstring for MainWindow"""

    def __init__(self, diag, device):
        super(MainWindow, self).__init__()

        self.setAcceptDrops( True )

        self.device = device
        self.controller = PlaybackController( device, self );
        self.repl = YueRepl( device )
        self.clientrepl = ClientRepl( self )
        self.clientrepl.register( self.repl )

        s = Settings.instance()
        self.keyhook = KeyHook(self.controller, s['enable_keyboard_hook'])

        self.dialog_ingest = None
        self._init_ui( diag)
        self._init_values()
        self._init_menubar()

    def _init_ui(self, diag):
        s = Settings.instance()

        # init primary views
        self.libview = LibraryView(self);
        self.libview.create_playlist.connect(self.createNewPlaylist)
        self.libview.set_playlist.connect(self.setCurrentPlaylist)
        self.libview.setMenuCallback( self.addSongActions )

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

        if self.controller.dspSupported():
            self.peqview = WidgetOctaveEqualizer();
            # TODO: we should not be passing controller into these widgets
            self.audioview = BassVisualizer(self.controller, self)
            self.audioview.setFixedHeight( 48 )
            self.audioview.start()
            self.peqview.gain_updated.connect( self.controller.setEQGain )

        # initialize layout

        self.btn_playpause = PlayButton( self )
        h = self.songview.height()
        self.btn_playpause.setFixedHeight( h )
        self.btn_playpause.setFixedWidth( h )
        self.btn_playpause.on_play.connect(self.controller.playpause)
        self.btn_playpause.on_stop.connect(self.controller._setStop)
        self.hbox = QHBoxLayout();
        self.hbox.addWidget( self.btn_playpause )
        self.hbox.addWidget( self.songview )

        self.edit_cmd = LineEditRepl( self.repl, self );
        self.edit_cmd.setFocus()
        self.edit_cmd.setPlaceholderText("Command Input")
        if not s['ui_show_console']:
            self.edit_cmd.hide()

        self.plview.vbox.insertWidget(0, self.audioview)
        self.plview.vbox.insertLayout(0, self.hbox)
        self.plview.vbox.insertWidget(0, self.posview)
        self.plview.vbox.insertWidget(0, self.edit_cmd)

        # note: visible state is not stored for the playlist,
        # it should always be displayed at startup
        self.dock_list = QDockWidget()
        self.dock_list.setWidget( self.plview )
        self.dock_list.setAllowedAreas(Qt.LeftDockWidgetArea|Qt.RightDockWidgetArea)
        #self.dock_list.resize(300,0)
        self.dock_list.visibilityChanged.connect(self.showhide_list)

        self.dock_diag = QDockWidget()
        self.dock_diag.setWidget( diag )
        self.dock_diag.setAllowedAreas(Qt.BottomDockWidgetArea)
        if not s['ui_show_error_log']:
            self.dock_diag.hide()
        self.dock_diag.visibilityChanged.connect(self.showhide_diag)

        self.addDockWidget (Qt.RightDockWidgetArea, self.dock_list)
        self.addDockWidget (Qt.BottomDockWidgetArea, self.dock_diag)

        self.tabview = QTabWidget( self )
        self.tabview.addTab( self.libview, QIcon(':/img/app_note.png'), "Library")
        self.tabview.addTab( self.quickview, QIcon(':/img/app_fav.png'), "Quick Select")
        self.tabview.addTab( self.expview, QIcon(':/img/app_folder.png'), "Explorer")
        self.volcontroller = VolumeController(self)
        self.volcontroller.volume_slider.valueChanged.connect(self.setVolume)
        self.tabview.setCornerWidget( self.volcontroller )

        if self.controller.dspSupported():
            self.tabview.addTab( self.peqview, QIcon(':/img/app_eq.png'), "Equalizer")

        self.bar_menu = QMenuBar( self )
        self.bar_status = QStatusBar( self )

        self.setMenuBar( self.bar_menu )
        self.setStatusBar( self.bar_status )
        self.setCentralWidget(self.tabview)

    def _init_values(self):

        s = Settings.instance()
        vol = s['volume']
        self.volcontroller.volume_slider.setValue( vol )
        self.controller.device.setVolume( vol/100.0 )

    def _init_menubar(self):
        s = Settings.instance()
        menu = self.bar_menu.addMenu("&File")
        self.action_undo_delete = menu.addAction("Undo Delete")
        menu.addAction("Exit")

        menu = self.bar_menu.addMenu("&Music")
        menu.addAction("New Playlist",self.createNewPlaylist)
        menu.addSeparator()
        menu.addAction("New Editable Playlist", self.newEditablePlaylist)
        menu.addAction("Open Editable Playlist", self.openEditablePlaylist)
        if self.controller.dspSupported():
            menu.addSeparator()
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
        about_text += "Version: 1.0\n"
        about_text += "Python Version: %d.%d.%d-%s\n"%(v.major,v.minor,v.micro,v.releaselevel)
        about_text += "Qt Version: %s\n"%QT_VERSION_STR
        about_text += "sip Version: %s\n"%SIP_VERSION_STR
        about_text += "PyQt Version: %s\n"%PYQT_VERSION_STR
        menu.addAction("About",lambda:QMessageBox.about(self,"Yue Music Player",about_text))

    def closeEvent(self, event):

        s = Settings.instance()

        start = time.time()

        s['ui_show_error_log'] = int(not self.dock_diag.isHidden())
        s['ui_show_console'] = int(not self.edit_cmd.isHidden())
        # hide now, to make it look like the application closed faster
        self.hide()

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

        q1 = "artist = \"%s\""%(song[Song.artist].replace("\\","\\\\").replace("\"","\\\""))
        menu.addAction("Search for Artist", lambda : self.executeSearch(q1))
        q2 = q1 + " && album = \"%s\""%(song[Song.album].replace("\\","\\\\").replace("\"","\\\""))
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

    def on_seek(self,position):

        self.controller.device.seek( position )
        if self.controller.device.isPaused():
            self.controller.device.play()


def setSettingsDefaults():

    s = Settings.instance()
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
        ]) # off

def main():

    app = QApplication(sys.argv)
    app.setApplicationName("Yue Music Player")
    app.setQuitOnLastWindowClosed(True)
    app_icon = QIcon(':/img/icon.png')
    app.setWindowIcon(app_icon)

    with LogView(trace=False,echo=True) as diag:

        plugin_path = "./lib/win32/x86_64"
        db_path = "./yue.db"

        sys.stdout.write("Loading database\n")
        sqlstore = SQLStore(db_path)
        Settings.init( sqlstore )
        Library.init( sqlstore )
        PlaylistManager.init( sqlstore )

        setSettingsDefaults()

        pl = PlaylistManager.instance().openCurrent()
        if len(pl)==0:
            songs = Library.instance().search(None, orderby=Song.random, limit=5)
            lst = [ s['uid'] for s in songs ]
            pl.set( lst )

        sys.stdout.write("Create Sound Device\n")
        device = newDevice(pl,plugin_path)

        sys.stdout.write("Initializing application\n")
        window = MainWindow( diag, device )
        window.plview.setPlaylist( Library.instance(), pl)

        s = Settings.instance()

        geometry = QDesktopWidget().screenGeometry()
        sw = geometry.width()
        sh = geometry.height()
        dw = int(sw*.8)
        dh = int(sh*.8)
        dx = sw//2 - dw//2
        dy = sh//2 - dh//2
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
        window.resize(cw,ch)
        window.move(cx,cy)
        window.show()

        try:
            device.load_current( )
        except IndexError:
            sys.stderr.write("error: No Current Song\n")

    sys.exit(app.exec_())

