

import sys
isPython3 = sys.version_info[0]==3
if isPython3:
    unicode = str
try:
    from PyQt4.QtCore import *
    from PyQt4.QtGui import *
except:
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
    from PyQt5.QtGui import *

import yue.client.resource

from ..core.sqlstore import SQLStore
from ..core.library import Library
from ..core.playlist import PlaylistManager
from ..core.song import Song
from ..core.repl import YueRepl

from .ui.library_view import LibraryView
from .ui.playlist_view import PlayListViewWidget

from .widgets.logview import LogView
from .widgets.LineEdit import LineEditRepl
from .widgets.playbutton import PlayButton
from .widgets.songview import CurrentSongView, SongPositionView

from .controller import newDevice, PlaybackController

class MainWindow(QMainWindow):
    """docstring for MainWindow"""

    def __init__(self, diag, device):
        super(MainWindow, self).__init__()

        self.device = device

        self.controller = PlaybackController( device, self );

        self.repl = YueRepl( device )

        self._init_ui()

    def _init_ui(self):
        self.libview = LibraryView();
        self.plview = PlayListViewWidget();
        self.posview = SongPositionView( device, self );

        self.songview = CurrentSongView( self );
        self.btn_playpause = PlayButton( self )
        h = self.songview.height()
        self.btn_playpause.setFixedHeight( h )
        self.btn_playpause.setFixedWidth( h )
        self.hbox = QHBoxLayout();
        self.hbox.addWidget( self.btn_playpause )
        self.hbox.addWidget( self.songview )

        self.edit_cmd = LineEditRepl( self.repl, self );
        self.edit_cmd.grabKeyboard()

        self.plview.vbox.insertLayout(0, self.hbox)
        self.plview.vbox.insertWidget(0, self.posview)
        self.plview.vbox.insertWidget(0, self.edit_cmd)

        self.dock_list = QDockWidget()
        self.dock_list.setWidget( self.plview )
        self.dock_list.resize(300,0)

        self.dock_diag = QDockWidget()
        self.dock_diag.setWidget( diag )

        self.addDockWidget (Qt.RightDockWidgetArea, self.dock_list)
        self.addDockWidget (Qt.BottomDockWidgetArea, self.dock_diag)

        self.setCentralWidget(self.libview)

def main():

    app = QApplication(sys.argv)
    app.setApplicationName("Yue Music Player")
    app.setQuitOnLastWindowClosed(True)
    app_icon = QIcon(':/img/icon.png')
    app.setWindowIcon(app_icon)

    with LogView(trace=False,echo=True) as diag:

        db_path = "./libimport.db"
        sqlstore = SQLStore(db_path)
        Library.init( sqlstore )
        PlaylistManager.init( sqlstore )

        pl = PlaylistManager.instance().openPlaylist("current")
        songs = Library.instance().search(None, orderby=Song.random, limit=5)
        lst = [ s['uid'] for s in songs ]
        pl.set( lst )

        device = newDevice(pl,"./lib/win32/x86_64")

        window = MainWindow( diag, device )

        window.plview.setPlaylist( Library.instance(), pl)

        window.show()
        window.resize(960,720)

        device.setVolume( .25 )
        device.load_current( )

    sys.exit(app.exec_())