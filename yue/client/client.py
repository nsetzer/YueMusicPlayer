#! cd ../.. && python34 test/test_client.py

import sys
isPython3 = sys.version_info[0]==3
if isPython3:
    unicode = str

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

import yue.client.resource

from ..core.sqlstore import SQLStore
from ..core.library import Library
from ..core.playlist import PlaylistManager
from ..core.sound.device import MediaState
from ..core.song import Song
from ..core.repl import YueRepl

from .ui.library_view import LibraryView
from .ui.explorer_view import ExplorerView
from .ui.playlist_view import PlayListViewWidget
from .ui.playlistedit_view import PlaylistEditView

from .widgets.logview import LogView
from .widgets.LineEdit import LineEditRepl
from .widgets.playbutton import PlayButton
from .widgets.songview import CurrentSongView, SongPositionView

from .controller import newDevice, PlaybackController

from .ui.ingest_dialog import IngestProgressDialog

from .DSP.peqwidget import WidgetOctaveEqualizer

from .ui.visualizer import BassVisualizer

class MainWindow(QMainWindow):
    """docstring for MainWindow"""

    def __init__(self, diag, device):
        super(MainWindow, self).__init__()

        self.setAcceptDrops( True )

        self.device = device
        self.controller = PlaybackController( device, self );
        self.repl = YueRepl( device )

        self.dialog_ingest = None
        self._init_ui( diag)

    def _init_ui(self, diag):
        self.libview = LibraryView();
        self.expview = ExplorerView(self.controller);
        self.plview = PlayListViewWidget(); # TODO parents
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
        self.btn_playpause.on_stop.connect(self.controller.setStop)
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
        self.tabview.addTab( self.expview, QIcon(':/img/app_folder.png'), "Explorer")
        self.pledit = PlaylistEditView("current")
        self.tabview.addTab( self.pledit, "Playlist Edit")

        if self.controller.dspSupported():
            self.tabview.addTab( self.peqview, "Equalizer")

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
        Library.init( sqlstore )
        PlaylistManager.init( sqlstore )

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

        window.show()
        window.resize(960,720)

        device.setVolume( .25 )
        device.load_current( )

    sys.exit(app.exec_())

