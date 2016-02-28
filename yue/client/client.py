#! cd ../.. && python34 test/test_client.py

import os,sys
isPython3 = sys.version_info[0]==3
if isPython3:
    unicode = str

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

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
from .ui.explorer_view import ExplorerView, explorerOpen
from .ui.playlist_view import PlayListViewWidget
from .ui.playlistedit_view import PlaylistEditView

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
        pl = PlaylistManager.instance().openPlaylist("current")
        lst = [ s['uid'] for s in songs ]
        pl.set( lst )

        self.client.plview.update()

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
        self.keyhook = KeyHook(self.controller,False)

        self.dialog_ingest = None
        self._init_ui( diag)
        self._init_values()

    def _init_ui(self, diag):
        self.libview = LibraryView(self);
        self.expview = ExplorerView(self.controller);
        self.plview = PlayListViewWidget(self);
        self.songview = CurrentSongView( self );

        if self.controller.dspSupported():
            self.peqview = WidgetOctaveEqualizer();
            self.posview = SongPositionView( self.device, self );
            self.audioview = BassVisualizer(self.controller, self)
            self.audioview.setFixedHeight( 48 )
            self.audioview.start()
            self.peqview.gain_updated.connect( self.controller.setEQGain )

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

        self.plview.vbox.insertWidget(0, self.audioview)
        self.plview.vbox.insertLayout(0, self.hbox)
        self.plview.vbox.insertWidget(0, self.posview)
        self.plview.vbox.insertWidget(0, self.edit_cmd)
        self.plview.play_index.connect( self.controller.play_index )

        self.dock_list = QDockWidget()
        self.dock_list.setWidget( self.plview )
        self.dock_list.resize(300,0)

        self.dock_diag = QDockWidget()
        self.dock_diag.setWidget( diag )

        self.addDockWidget (Qt.RightDockWidgetArea, self.dock_list)
        self.addDockWidget (Qt.BottomDockWidgetArea, self.dock_diag)

        self.tabview = QTabWidget( self )
        self.tabview.addTab( self.libview, QIcon(':/img/app_note.png'), "Library")
        self.tabview.addTab( QWidget(), QIcon(':/img/app_fav.png'), "Quick Select")
        self.tabview.addTab( self.expview, QIcon(':/img/app_folder.png'), "Explorer")
        self.volcontroller = VolumeController(self)
        self.volcontroller.volume_slider.valueChanged.connect(self.setVolume)
        self.tabview.setCornerWidget( self.volcontroller )

        if self.controller.dspSupported():
            self.tabview.addTab( self.peqview, QIcon(':/img/app_eq.png'), "Equalizer")

        self.openPlaylistEditor( "testlist" )

        self.bar_menu = QMenuBar( self )
        self.bar_menu.addMenu("&File")
        self.bar_menu.addMenu("&Music")
        self.bar_menu.addMenu("&View")
        self.bar_menu.addMenu("&Settings")
        self.bar_menu.addMenu("&?")
        self.bar_status = QStatusBar( self )

        self.setMenuBar( self.bar_menu )
        self.setStatusBar( self.bar_status )
        self.setCentralWidget(self.tabview)

    def _init_values(self):

        s = Settings.instance()
        vol = s['volume']
        self.volcontroller.volume_slider.setValue( vol )
        self.controller.device.setVolume( vol/100.0 )

    def closeEvent(self, event):

        s = Settings.instance()

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

        super(MainWindow,self).closeEvent( event )

    def tabIndex(self, widget):
        idx = -1
        for i in range(self.tabview.count()):
            w = self.tabview.widget( i )
            if w is widget:
                idx = i
    def openPlaylistEditor(self, playlist_name):

        widget = PlaylistEditView(playlist_name)
        index = self.tabview.addTab( widget, QIcon(':/img/app_list.png'), playlist_name)
        widget.btn = CloseTabButton( lambda : self.closePlaylistEditorTab( widget ), self)
        self.tabview.tabBar().setTabButton(index,QTabBar.RightSide,widget.btn)

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

    def executeSearch(self,query):
        #idx = self.tabIndex( self.libview )
        self.libview.run_search(query,setText=True)
        self.tabview.setCurrentWidget(self.libview)

    def exploreDirectory(self, path):
        self.expview.chdir(path, True)
        self.tabview.setCurrentWidget(self.expview)

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

def setSettingsDefaults():

    s = Settings.instance()
    s.setDefault("volume",50)



def main():

    app = QApplication(sys.argv)
    app.setApplicationName("Yue Music Player")
    app.setQuitOnLastWindowClosed(True)
    app_icon = QIcon(':/img/icon.png')
    app.setWindowIcon(app_icon)

    with LogView(trace=False,echo=True) as diag:


        sys.stdout.write("Loading database\n")
        db_path = "./libimport.db"
        sqlstore = SQLStore(db_path)
        Settings.init( sqlstore )
        Library.init( sqlstore )
        PlaylistManager.init( sqlstore )

        setSettingsDefaults()

        pl = PlaylistManager.instance().openPlaylist("current")
        if len(pl)==0:
            songs = Library.instance().search(None, orderby=Song.random, limit=5)
            lst = [ s['uid'] for s in songs ]
            pl.set( lst )

        sys.stdout.write("Create Sound Device\n")
        device = newDevice(pl,"./lib/win32/x86_64")

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

        device.load_current( )

    sys.exit(app.exec_())

