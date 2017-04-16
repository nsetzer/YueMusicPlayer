#! cd ../.. && python client-main.py

# xx 1 G:\\Music /Users/nsetzer/Music/Library

import os,sys
import time
from datetime import datetime
import urllib
import argparse
import traceback
import codecs

from PyQt5.QtCore import *
# this is required so that the frozen executable
# can find `platforms/qwindows.dll`
if hasattr(sys,"_MEIPASS"):
    QCoreApplication.addLibraryPath(sys._MEIPASS)
    QCoreApplication.addLibraryPath(os.path.join(sys._MEIPASS,"qt5_plugins"))
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from sip import SIP_VERSION_STR, delete as sip_delete

from .style import style_set_custom_theme, setApplicationPallete, currentStyle, clearStyle, StyleError

from yue.qtcommon.Tab import TabWidget

from ..core.sqlstore import SQLStore
from ..core.settings import Settings
from ..core.library import Library
from ..core.playlist import PlaylistManager
from ..core.history import History
from ..core.sound.device import MediaState
from ..core.song import Song , get_album_art_data, ArtNotFound
from ..core.util import string_quote, backupDatabase, format_delta
from ..core.repl import YueRepl, ReplArgumentParser
from ..core.bass import pybass

from . import resource
from .controller import newDevice, PlaybackController

HookThread = None
KeyHook = None

sys.stdout.write(">>"+os.name+"\n");
if sys.platform == 'darwin':
    print("darwin")
    from .hookosx import HookThread
else:
    try:
        from .hook import KeyHook
    except ImportError as e:
        sys.stderr.write("pyHook not supported: %s\n"%e)
        KeyHook = None
    if KeyHook is None:
        try:
            if os.name == 'nt':
                from .hook2 import HookThread
            else:
                HookThread = None
        except ImportError as e:
            sys.stderr.write("hook not supported: %s\n"%e)
            HookThread = None
        except OSError as e:
            sys.stderr.write("hook not supported: %s\n"%e)
            HookThread = None

try:
    from .remote import SocketListen
except ImportError as e:
    sys.stderr.write("socket import: %s\n"%e)
    SocketListen = None

from .ui.library_view import LibraryView
from .ui.playlisttab_view import PlaylistTabView
from .ui.history_view import HistoryView
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
from .ui.settings import SettingsDialog
from .ui.song_view import CurrentSongView
from .ui.art_view import AlbumArtView
from .ui.volume import VolumeController

from yue.qtcommon.logview import LogView
from yue.qtcommon.LineEdit import LineEditRepl
from yue.qtcommon.playbutton import PlayButton, AdvanceButton
from yue.qtcommon.slider import PositionSlider
from yue.qtcommon.closebutton import  CloseTabButton
try:
    from yue.qtcommon.scieditor import CodeEditor
except ImportError:
    CodeEditor = None

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
        self.actions["theme"] = self.extheme
        self.actions["history"] = self.exhistory
        if CodeEditor is not None:
            self.actions["editor"] = self.exeditor

        self.actions["quit"] = self.exexit
        self.actions["exit"] = self.exexit
        self.actions["xx"] = self.exxx
        self.actions["clear"] = self.exclear
        self.actions["clr"] = self.exclear
        self.actions["settings"] = self.exset

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

    def exclear(self,args):
        """ clear the error log """
        self.client.errorlog_view.clear()

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
        self.client.backup_database( True )



    def exexplorer(self, args):
        """ open directory of the database in explorer """
        dbpath = os.path.realpath(Library.instance().sqlstore.path())
        dirpath = os.path.split(dbpath)[0]
        explorerOpen( dirpath )

    def exdiag(self, args):
        """ enable/disable diagnostics

        currently toggles keylogger enable
        """

        keyhook = self.client.keyhook
        keyhook.setDiagEnabled( not keyhook.getDiagEnabled() )
        print(self.client.keyhook.diag)

    def exeditor(self, args):

        if not hasattr(self,'editor'):
            self.editor = CodeEditor()
            self.editor.setVariable("Repl",self)
            self.editor.setVariable("Client",self.client)
            self.editor.setVariable("Library",Library.instance())
            self.editor.setVariable("PlaylistManager",PlaylistManager.instance())
            self.editor.setVariable("Settings",Settings.instance())
            self.editor.setVariable("History",History.instance())
            self.editor.setVariable("Song",Song)
            self.editor.setText("help()\nfor song in Library.search('title=fizzbuzz'):"+\
                "\n    pass # Library.update(song[Song.uid],**{Song.title:'foobar'}")
        self.editor.show()

    def extheme(self,args):

        args = ReplArgumentParser(args,{'p':'preset', 's':'search', 'l':'limit'})
        args.assertMinArgs( 1 )
        theme = args[0]
        self.client.set_style( theme )

    def exset(self,args):
        # TODO: at app level specify some settings as constants
        # values that cannot be changed (by the user) and hide
        # those values from the settings command (get, set, list)
        # e.g. window position
        args = ReplArgumentParser(args)
        args.assertMinArgs( 1 )
        cmd = args[0]
        if cmd == 'set':
            args.assertMinArgs( 3 )
            field = args[1]
            value = args[2]
            Settings.instance()[field] = value
            print("changing setting %s to `%s`"%(field,value))
        elif cmd == 'get':
            args.assertMinArgs( 2 )
            field = args[1]
            print("%s=%s"%(field,Settings.instance()[field]))
        elif cmd == 'list':
            print("\nSettings:")
            for field,value in sorted(Settings.instance().items()):
                print("%s=%s"%(field,Settings.instance()[field]))


    def exhistory_old(self,args):
        """
        0 : disable
        1 : enable logging
        2 : enable logging of record changes
        3 : enable logging + record logging
        """
        args = ReplArgumentParser(args)
        args.assertMinArgs( 1 )

        enable_log    = bool(int(args[0]) & 1)
        enable_update = bool(int(args[0]) & 2)

        History.instance().setLogEnabled( enable_log )
        History.instance().setUpdateEnabled( enable_update )

        print("history log: %d"%(enable_log))
        print("history update: %d"%(enable_update))

    def exhistory(self,args):
        """ manage history

        $0 enable [log|update]
            log: enable history logging of playback
            update: enable history logging of metadata
        $0 disable [log|update]
            log: disable history logging of playback
            update: disable history logging of metadata
        $0 [-s] export path
            write history database to a file (history.log)
            -s --simple : write playtime records as last_played.

        $0 import path
            read back the history log and place the values in the database
        $0 clear
            wipe the history database
        $0 pl name path
            export playlist metadata given by name to path as a history log file
        $0 info
            print information about the current history state

        """
        args = ReplArgumentParser(args,{'s':'simple'})
        args.assertMinArgs( 1 )
        cmd = args[0]
        if cmd == "enable":
            args.assertMinArgs( 2 )
            mode = args[1]
            if mode == "log":
                History.instance().setLogEnabled( True )
            elif mode == "update":
                History.instance().setUpdateEnabled( True )

        elif cmd == "disable":
            args.assertMinArgs( 2 )
            mode = args[1]
            if mode == "log":
                History.instance().setLogEnabled( False )
            elif mode == "update":
                History.instance().setUpdateEnabled( False )

        elif cmd == "export":
            args.assertMinArgs( 2 )
            path = args[1]

            if os.path.exists(path):
                print("EEXIST %s"%path) # prevent overwriting
                return

            with codecs.open(path,"w","utf-8") as af:
                nrecs=0
                for record in History.instance().export():

                    if 'simple' in args and record['column']==Song.playtime:
                        record['column'] = Song.last_played
                        record['value'] = record['date']

                    af.write("%d %-6d %s=%s\n"%(\
                        record['date'],record['uid'],\
                        record['column'],record['value']));
                    nrecs+=1
                print("exported %d records simple=%s"%(nrecs,'simple' in args))

        elif cmd == "import":
            #for record in remote_history.export():
            #    self.parent.library._import_record( c, record )
            args.assertMinArgs( 2 )
            path = args[1]

            if not os.path.exists(path):
                print("EEXIST %s"%path)
                return

            Library.instance().import_record_file(path)

        elif cmd == "clear":
            History.instance().db.store.conn.execute("DELETE FROM history")

        elif cmd == "pl":
            args.assertMinArgs( 3 )
            name = args[1]
            path = args[2]

            if not PlaylistManager.instance().exists(name):
                print("EEXIST %s"%name) # prevent overwriting
                return

            pl = PlaylistManager.instance().openPlaylist(name)

            if os.path.exists(path):
                print("EEXIST %s"%path) # prevent overwriting
                return

            with codecs.open(path,"w","utf-8") as wf:
                for song in Library.instance().songFromIds(pl):
                    s = song[Song.last_played]
                    t = (s,song[Song.uid],Song.last_played,s)
                    wf.write("%d %-6d %s=%s\n"%t)
                    c = song[Song.play_count]
                    t = (s,song[Song.uid],Song.play_count,c)
                    wf.write("%d %-6d %s=%s\n"%t)
                    r = song[Song.rating]
                    t = (s,song[Song.uid],Song.rating,r)
                    wf.write("%d %-6d %s=%s\n"%t)
                    a = song[Song.artist]
                    t = (s,song[Song.uid],Song.artist,a)
                    wf.write("%d %-6d %s=%s\n"%t)
                    a = song[Song.title]
                    t = (s,song[Song.uid],Song.title,a)
                    wf.write("%d %-6d %s=%s\n"%t)
        elif cmd == "info":
            print("history log: %d"%(History.instance().isLogEnabled()))
            print("history update: %d"%(History.instance().isUpdateEnabled()))

    def exxx(self,args):
        """
        1: xx 1 alt alt [alt ...]
            update song path in db based on provided update alternatives list
        2: xx 2 path
            write history database to a file (history.log)
            wipe the history database
        3: xx 3 path
            read back the history log and place the values in the database
        4: xx 4 name path
            export playlist metadata given by name to path
        """
        args = ReplArgumentParser(args,{'p':'preset', 's':'search', 'l':'limit'})
        args.assertMinArgs( 1 )

        value = int(args[0])
        if value == 1:
            alternatives = args[1:]
            print(alternatives)
            Library.instance().songPathHack( alternatives )



class MainWindow(QMainWindow):
    """docstring for MainWindow"""

    refreshTreeView = pyqtSignal()

    def __init__(self, errorlog_view, device, version_info ):
        super(MainWindow, self).__init__()

        start = time.time()

        self.setAcceptDrops( True )
        self.version,self.versiondate,self.builddate = version_info
        self.device = device
        self.controller = PlaybackController( device, self );
        self.repl = YueRepl( device )
        self.clientrepl = ClientRepl( self )
        self.clientrepl.register( self.repl )
        self.errorlog_view = errorlog_view

        sys.stdout.write(" >> 0 >> %f\n"%(time.time()-start))

        self.keyhook = None
        self.remotethread = None

        self.default_palette = QPalette(self.palette())
        self.default_font    = QFont(self.font())

        self.dialog_ingest = None
        self.dialog_update = None

        self._init_keyhook()
        self._init_remote()
        self._init_ui()
        s = Settings.instance().getMulti('volume',
                                         'volume_equalizer',
                                         "ui_show_console",
                                         'ui_show_visualizer',
                                         'ui_show_treeview',
                                         'ui_show_history',
                                         'ui_show_error_log',
                                         'ui_quickselect_favorite_artists',
                                         'ui_quickselect_favorite_genres',
                                         'ui_library_column_order');
        self._init_values(s)
        self._init_menubar(s)
        self._init_misc()

    def _init_keyhook(self):
        if KeyHook is not None:
            sys.stdout.write("Initialize pyHook.\n")
            self.keyhook = KeyHook()
            self.setEnabled(True)
            self.keyhook.playpause.connect(self.device.playpause)
            self.keyhook.play_next.connect(self.controller.play_next)
            self.keyhook.play_prev.connect(self.controller.play_prev)
            self.keyhook.stop.connect(self.controller.toggleStop)
        elif HookThread is not None:
            sys.stdout.write("Initialize Keyboard hook.\n")
            self.keyhook = HookThread()
            self.keyhook.start()
            self.keyhook.playpause.connect(self.device.playpause)
            self.keyhook.play_next.connect(self.controller.play_next)
            self.keyhook.play_prev.connect(self.controller.play_prev)
            self.keyhook.stop.connect(self.controller.toggleStop)
        else:
            sys.stdout.write("Unable to initialize Keyboard Hook.\n")

    def _init_remote(self):
        s = Settings.instance()

        if s['enable_remote_commands']:
            if SocketListen is not None:
                port = 15123
                if hasattr(sys,"_MEIPASS"):
                    port = 15124 # use a different port when frozen
                sys.stdout.write("Initialize Remote Thread.\n")
                self.remotethread = SocketListen(port=port,parent=self)
                self.remotethread.message_recieved.connect(self.executeCommand)
                self.remotethread.start()
            else:
                sys.stdout.write("Unable to initialize Remote Thread.\n")
        else:
            sys.stdout.write("Socket Thread not started. Remote Commands Disabled.\n")

    def _init_ui(self):
        start = time.time()
        sys.stdout.write("Initializing Ui\n")

        self.bar_menu = QMenuBar( self )
        self.setMenuBar( self.bar_menu )

        self.bar_status = QStatusBar( self )
        self.lbl_status = QLabel(self)
        # allow this widget to shrink as much as possible
        self.lbl_status.setMinimumWidth(1)
        self.lbl_pl_status = QLabel(self)
        self.bar_status.addWidget( self.lbl_status)
        self.bar_status.addPermanentWidget( self.lbl_pl_status)
        self.setStatusBar( self.bar_status )

        self.tabview = TabWidget( self )
        self.setCentralWidget(self.tabview)

        # init primary views
        self.libview = LibraryView(self);
        self.libview.create_playlist.connect(self.createNewPlaylist)
        self.libview.insert_playlist.connect(self.insertIntoCurrentPlaylist)
        self.libview.set_playlist.connect(self.setNewPlaylist)
        self.libview.setMenuCallback( self.addSongActions )
        self.libview.notify.connect( self.update_statusbar_message )

        self.quickview = QuickSelectView(self);
        self.quickview.create_playlist.connect(self.createQuickPlaylist)

        self.expview = ExplorerView(self);
        self.expview.play_file.connect(self.controller.playOneShot)
        self.expview.ingest_finished.connect(self.ingestFinished)

        self.plview = PlayListViewWidget(self);
        self.plview.setMenuCallback( self.addSongActions )
        self.plview.play_index.connect( self.controller.play_index )
        self.plview.playlist_duration.connect( self.update_statusbar_duration )
        self.plview.playlist_changed.connect( self.update_song_view )
        self.plview.playlist_generate.connect( self.rollCurrentPlaylist )

        self.historyview = HistoryView(self);

        self.songview = CurrentSongView( self );
        self.songview.setMenuCallback( self.addSongActions )
        self.songview.update_rating.connect(self.setRating)

        self.edit_cmd = LineEditRepl( self.repl, self );
        self.edit_cmd.setFocus()
        self.edit_cmd.setPlaceholderText("Command Input")

        self.pleditview = PlaylistTabView(self)

        self.volcontroller = VolumeController(self)
        self.volcontroller.volume_slider.valueChanged.connect(self.setVolume)
        self.volcontroller.volume_slider.value_set.connect(self.setVolume)

        # note: visible state is not stored for the playlist,
        # it should always be displayed at startup
        self.dock_list = QDockWidget()
        self.dock_list.setWidget( self.plview )
        self.dock_list.setAllowedAreas(Qt.LeftDockWidgetArea|Qt.RightDockWidgetArea)
        self.dock_list.visibilityChanged.connect(self.showhide_list)

        self.dock_diag = QDockWidget()
        self.dock_diag.setWidget( self.errorlog_view )
        self.dock_diag.setAllowedAreas(Qt.BottomDockWidgetArea)
        self.dock_diag.visibilityChanged.connect(self.showhide_diag)

        # add widgets to layout

        self.addDockWidget (Qt.RightDockWidgetArea, self.dock_list)
        self.addDockWidget (Qt.BottomDockWidgetArea, self.dock_diag)

        self.tabview.addTab( self.libview, QIcon(':/img/app_note.png'), "Library")
        self.tabview.addTab( self.pleditview, QIcon(':/img/app_list.png'), "Playlists")
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
        self.tabview.addTab(self.historyview,"History")
        self.tabview.setCornerWidget( self.volcontroller )

        self.historyview_index = self.tabview.indexOf( self.historyview )

        h=48
        self.btn_playpause = PlayButton( self )
        self.btn_playpause.setFixedHeight( h )
        self.btn_playpause.setFixedWidth( h )
        self.btn_playpause.on_play.connect(self.controller.playpause)
        self.btn_playpause.on_stop.connect(self.controller._setStop)

        self.btn_next = AdvanceButton(True,self)
        self.btn_next.setFixedHeight( .66*h )
        self.btn_next.setFixedWidth( 32 )
        self.btn_next.clicked.connect(self.controller.play_next)
        self.btn_prev = AdvanceButton(False,self)
        self.btn_prev.setFixedHeight( .66*h )
        self.btn_prev.setFixedWidth( 32 )
        self.btn_prev.clicked.connect(self.controller.play_prev)

        self.hbox_btn = QHBoxLayout();
        self.hbox_btn.setContentsMargins(0,0,0,0)
        self.hbox_btn.addStretch(1) # layout spacer
        self.hbox_btn.addWidget( self.btn_prev )
        self.hbox_btn.addWidget( self.btn_playpause )
        self.hbox_btn.addWidget( self.btn_next )
        self.hbox_btn.addStretch(1)

        self.posview = PositionSlider( self );
        self.posview.value_set.connect(self.controller.seek)
        self.posview.setObjectName("TimeSlider")

        self.aartview = AlbumArtView(self)
        h=self.songview.height()
        self.aartview.setFixedHeight(h)
        self.aartview.setFixedWidth(h)
        self.hbox_sv = QHBoxLayout();
        self.hbox_sv.setContentsMargins(0,0,0,0)
        self.hbox_sv.addWidget( self.aartview )
        self.hbox_sv.addWidget( self.songview )

        # TODO: this is currently the biggest hack here
        self.plview.vbox.insertLayout(0, self.hbox_sv)
        self.plview.vbox.insertWidget(0, self.posview)
        self.plview.vbox.insertLayout(0, self.hbox_btn)
        self.plview.vbox.insertWidget(0, self.edit_cmd)

        sys.stdout.write("Initialization of Ui completed in %f seconds\n"%(time.time()-start))

    def _init_values(self,s):
        sys.stdout.write("Initializing default values\n")


        vol = s['volume']
        self.volcontroller.volume_slider.setValue( vol )
        self.controller.device.setVolume( vol/100.0 )

        if not s['ui_show_console']:
            self.edit_cmd.hide()

        if not s['ui_show_error_log']:
            self.dock_diag.hide()

        if not s['ui_show_treeview']:
            self.libview.tree_lib.container.hide()

        if not s['ui_show_history']:
            self.tabview.removeTab(self.historyview_index)

        if self.controller.dspSupported():
            if not s['ui_show_visualizer']:
                self.audioview.hide()
                self.audioview.stop()

        #if s['enable_keyboard_hook']:
        #    pass # TODO enable keyhook here

        self.quickview.setFavorites(Song.artist,s["ui_quickselect_favorite_artists"])
        self.quickview.setFavorites(Song.genre,s["ui_quickselect_favorite_genres"])
        self.libview.setColumnState(s["ui_library_column_order"])

        pl = PlaylistManager.instance().openCurrent()
        if len(pl)==0:
            songs = Library.instance().search(None, orderby=Song.random, limit=5)
            lst = [ song['uid'] for song in songs ]
            pl.set( lst )
        self.plview.setPlaylist( Library.instance(), pl)

    def _init_menubar(self,s):

        self.xcut_fullscreen = QShortcut(QKeySequence("F1"), self)
        self.xcut_fullscreen.activated.connect(self.toggleFullScreen)

        menu = self.bar_menu.addMenu("&File")
        menu.addAction("Settings",self.showSettings)
        menu.addAction("Exit",QApplication.quit)

        menu = self.bar_menu.addMenu("&Music")
        menu.addAction(QIcon(":/img/app_newlist.png"),"New Playlist",self.createNewPlaylist)
        #menu.addSeparator()
        #menu.addAction("New Editable Playlist", self.newEditablePlaylist)
        #menu.addAction("Open Editable Playlist", self.openEditablePlaylist)
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

        if self.controller.dspSupported():
            self.action_view_visualizer = menu.addAction("",self.toggleVisualizerVisible)
            if s['ui_show_visualizer']:
                self.action_view_visualizer.setText("Hide Visualizer")
            else:
                self.action_view_visualizer.setText("Show Visualizer")

        self.action_view_tree    = menu.addAction("",self.toggleTreeViewVisible)
        if s['ui_show_treeview']:
            self.action_view_tree.setText("Hide Tree View")
        else:
            self.action_view_tree.setText("Show Tree View")

        self.action_view_history    = menu.addAction("",self.toggleHistoryVisible)
        if s['ui_show_history']:
            self.action_view_history.setText("Hide History")
        else:
            self.action_view_history.setText("Show History")

        self.action_view_logger  = menu.addAction("",lambda : self.toggleDialogVisible(self.dock_diag))
        if s['ui_show_error_log']:
            self.action_view_logger.setText("Hide Error Log")
        else:
            self.action_view_logger.setText("Show Error Log")

        menu.addAction("Clear Error Log",self.errorlog_view.clear)

        menu = self.bar_menu.addMenu("&?")
        # sip version, qt version, python version, application version
        about_text = ""
        v = sys.version_info
        about_text += "Version: %s\n"%(self.version)
        about_text += "Commit Date:%s\n"%(self.versiondate)
        about_text += "Build Date:%s\n"%(self.builddate)
        about_text += "Python Version: %d.%d.%d-%s\n"%(v.major,v.minor,v.micro,v.releaselevel)
        about_text += "Qt Version: %s\n"%QT_VERSION_STR
        about_text += "sip Version: %s\n"%SIP_VERSION_STR
        about_text += "PyQt Version: %s\n"%PYQT_VERSION_STR
        about_text += "Playback Engine: %s\n"%self.controller.device.name()
        menu.addAction("About",lambda:QMessageBox.about(self,"Yue Music Player",about_text))

    def _init_misc(self):

        s = Settings.instance().getMulti("current_theme",
                                         'enable_history',
                                         'enable_history_update',
                                         "current_position",
                                         "current_song_id")

        self.set_style(s["current_theme"])

        History.instance().setLogEnabled( s['enable_history'] )
        History.instance().setUpdateEnabled( s['enable_history_update'] )

        #self.device.setAlternatives(s['path_alternatives'])

        sys.stdout.write("record history: log:%s update:%s\n"%( \
                    bool(s['enable_history']), \
                    bool(s['enable_history_update'])))
       # sys.stdout.write("path alternatives: %s\n"%s['path_alternatives'])

        try:
            song = self.device.load_current()
            # TODO: check that p is less than length of current song (minus 5s)
            # or something similar. Then make this a configuration option
            # that defaults on.
            p = s["current_position"]
            if song[Song.uid] == s['current_song_id']:
                self.device.seek( p )
                self.controller.on_song_tick( p )
                print("Setting song position for %d to %s"%(song[Song.uid],format_delta(p)))
            else:
                print("Failed to set song position. stored id:%d current id: %d"%(s['current_song_id'], song[Song.uid]))
        except IndexError:
            sys.stderr.write("error: No Current Song\n")

        self.libview.tree_lib.refreshData()

        songs = Library.instance().search(None)
        self.libview.displaySongs( songs );
        self.quickview.generateData( songs );

    def toggleFullScreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def closeEvent(self, event):

        sys.stdout.write("Closing Application\n")

        sdat = {}
        self.controller.device.pause()

        start = time.time()

        # todo, speed this up, store all values into a local dictionary
        # then update the settings object in a single write block

        sdat['ui_show_error_log'] = int(not self.dock_diag.isHidden())
        sdat['ui_show_console'] = int(not self.edit_cmd.isHidden())
        sdat['ui_show_treeview'] = int(not self.libview.tree_lib.container.isHidden())
        sdat['ui_show_history'] = int(self.tabview.indexOf(self.historyview) == self.historyview_index)
        if self.controller.dspSupported():
            sdat['ui_show_visualizer'] = int(not self.audioview.isHidden())
        # hide now, to make it look like the application closed faster

        sdat['enable_history'] = int(History.instance().isLogEnabled())
        sdat['enable_history_update'] = int(History.instance().isUpdateEnabled())

        # todo, only if a song from the library is playing
        sdat['current_position'] = int(self.device.position())
        try:
            idx,key = PlaylistManager.instance().openCurrent().current()
            sdat['current_song_id'] = int(key)
        except IndexError:
            sdat['current_song_id'] = int(0)
        #sdat['current_song_id']  =

        if self.keyhook is not None:
            self.keyhook.join()

        # record the current volume, but prevent the application
        # from starting muted
        v = self.volcontroller.volume_slider.value()
        sdat["volume"] = v if v > 0 else 25

        # record the current position of the window
        # application startup will check this is still valid, and try
        # to reposition accordingly
        sdat["window_width"] = self.width()
        sdat["window_height"] = self.height()
        sdat["window_x"] = self.x()
        sdat["window_y"] = self.y()

        sdat['ui_library_column_order'] = self.libview.getColumnState();

        sdat['ui_quickselect_favorite_artists'] = self.quickview.getFavoriteArtists()
        sdat['ui_quickselect_favorite_genres'] = self.quickview.getFavoriteGenres()

        sys.stdout.write("Saving state (%f)\n"%(time.time()-start))
        s = Settings.instance().setMulti(sdat)
        sys.stdout.write("finished saving state (%f)\n"%(time.time()-start))

        self.hide()
        if self.remotethread is not None:
            self.remotethread.join()

        super(MainWindow,self).closeEvent( event )
        sys.stdout.write("goodbye :) (%f)\n"%(time.time()-start))

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
        widget.set_playlist.connect(self.insertIntoCurrentPlaylist)
        widget.notify.connect(self.update_statusbar_message)
        widget.set_playlist.connect(self.setNewPlaylist)

        index = self.tabview.addTab( widget, QIcon(':/img/app_list.png'), playlist_name)
        widget.btn = CloseTabButton( lambda : self.closePlaylistEditorTab( widget ), self)
        self.tabview.tabBar().setTabButton(index,QTabBar.RightSide,widget.btn)
        if switchto:
            self.tabview.setCurrentWidget( widget )

    def closePlaylistEditorTab(self,widget):

        # TODO: check if the tab *can* be closed
        # e.g. if the playlist editor has made changes,
        # ask if the user wants to discard the changes.

        if isinstance(widget,PlaylistEditView):
            # if the widget has unsaved changes issue a warning
            # this is a tri-state field
            # save, discard, or cancel
            # TODO: this could be standardized, (when and if there
            # are other types of closeable tabs)
            if widget.isDirty():
                result = widget.save_warning()
                if result == QMessageBox.Cancel:
                    return

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
        def onIngestExit():
            self.dialog_ingest = None
            self.ingestFinished()
        self.dialog_ingest = IngestProgressDialog( paths, self)
        self.dialog_ingest.setOnCloseCallback(onIngestExit)
        self.dialog_ingest.start()
        self.dialog_ingest.show()

    def setVolume(self, vol):

        #Settings.instance()["volume"] = vol
        self.controller.device.setVolume( vol/100.0 )

    def ingestFinished(self):
        self.executeSearch("added = today",False)
        self.libview.tree_lib.refreshData()

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
        self.expview.chdir(path)
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

        q1 = "artist == %s"%(string_quote(song[Song.artist]))
        menu.addAction("Search for Artist", lambda : self.executeSearch(q1))
        q2 = q1 + " && album == %s"%(string_quote(song[Song.album]))
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

    def toggleHistoryVisible(self):
        if self.tabview.indexOf(self.historyview) != self.historyview_index:
            self.action_view_history.setText("Hide History")
            self.tabview.insertTab(self.historyview_index, self.historyview, "History")

        else:
            self.action_view_history.setText("Show History")
            self.tabview.removeTab(self.historyview_index)

    def toggleTreeViewVisible(self):
        if self.libview.tree_lib.container.isHidden():
            self.action_view_tree.setText("Hide Tree View")
            self.libview.tree_lib.container.show()
        else:
            self.action_view_tree.setText("Show Tree View")
            self.libview.tree_lib.container.hide()

    def toggleVisualizerVisible(self):
        if self.audioview.isHidden():
            self.action_view_visualizer.setText("Hide Visualizer")
            self.audioview.show()
            self.audioview.start()
        else:
            self.action_view_visualizer.setText("Show Visualizer")
            self.audioview.hide()
            self.audioview.stop()

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

        if dialog.exec():

            params = dialog.getQueryParams()
            songs = Library.instance().search( \
                        params['query'],
                        orderby=dialog.getSortOrder(),
                        limit=params['limit'])
            lst = [ song[Song.uid] for song in songs ]

            if dialog.getCreatePlaylist():
                self.setNewPlaylist( lst )
            else:
                self.insertIntoCurrentPlaylist(lst)

    def showSettings(self):

        dialog = SettingsDialog(self)
        dialog.import_settings( Settings.instance() )
        if dialog.exec_():
            dialog.export_settings( Settings.instance() )

    #
    # TODO: what is the difference?
    # not obvious from the names

    def setNewPlaylist(self,uids):
        pl = PlaylistManager.instance().openCurrent()
        pl.set( uids )
        self.controller.play_index( 0 )
        self.plview.updateData()

    def insertIntoCurrentPlaylist(self, uids,play=False):
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

    def setRating(self,uid,rte):
        # TODO: refresh library view
        Library.instance().update(uid,**{Song.rating:rte})
        self.libview.onUpdate()

    def update_statusbar_message(self,msg):

        self.lbl_status.setText(msg)

    def update_song_view(self):
        index,length = self.controller.get_playlist_info()
        self.songview.setPlaylistInfo( index, length )

    def update_statusbar_duration(self,duration,remaining):
        msg = "%s / %s"%(format_delta(remaining), format_delta(duration))
        self.lbl_pl_status.setText(msg)

    def rollCurrentPlaylist(self):
        self.controller.rollPlaylist();
        self.plview.updateData()
        self.update_song_view()

    def backup_database(self, force = False ):

        s = Settings.instance();
        if s['backup_enabled'] or force:
            dir = s['backup_directory']
            backupDatabase( Library.instance().sqlstore, dir, force=force)

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
        if cx+cw < 0 or cx+cw>sw:
            cx = dx
            cw = dw
        if cy+ch < 0 or cy+ch>sh:
            cy = dy
            ch = dh
        if cw <= 0:
            cw = dw
        if ch <= 0:
            ch = dh
        self.resize(cw,ch)
        self.move(cx,cy)
        self.show()

        if not self.edit_cmd.isHidden():
            self.edit_cmd.setFocus()

    def set_style(self, theme):
        app = QApplication.instance()

        if theme == "none":
            clearStyle()
            app.setStyleSheet("")
            app.setPalette(self.default_palette)
            qdct = {"font_family":"",
                    "font_size":"10",
                    #color_special1":QColor(220,220,120),
                    "color_special1":QColor(16,128,32),
                    "text_important1":QColor(125,50,100),
                    "text_important2":QColor(255,5,15),
                    "theme_s_mid":QColor(60,60,200),
                    "theme_p_mid":QColor(60,60,200),
                    "theme_s_vdark":QColor(160,175,220)}
            app.setFont(self.default_font)
            css="""
            QSlider#TimeSlider::handle:horizontal {
                background:rgb(214,120,  0);
                border: 2px solid black;
                border-radius: 1px;
                max-width: 6px;

            }
            QTextEdit {
                font-family: "Lucida Console";
            }
            """
            app.setStyleSheet(css)
        else:
            try:
                css,cdct = style_set_custom_theme(os.getcwd()+"/theme",theme)
            except StyleError as e:
                sys.stderr.write("style error: %s\n"%e)
                return
            else:
                app.setStyleSheet(css)
                p = setApplicationPallete(app,cdct);
                qdct = currentStyle()
                font=QFont(qdct['font_family'],pointSize=int(qdct['font_size']))

        print("qdct font: `%s` `%d`"%(qdct['font_family'],int(qdct['font_size'])))
                #app.setFont(font)
        # TODO:
        # This needs to be refactored once I have a better idea
        # of how to adjust palettes for specific widgets, and know
        # exactly what widgets need to be updated manually.
        # note: currentStyle(), clearStyle() should instead be used
        # by widgets to grab color changes.

        # table highlight rules
        #self.plview.tbl.setRowHighlightComplexRule(0,None,qdct["color_special1"])
        #self.plview.brush_current.setColor(qdct["color_special1"])
        self.plview.color_current.setRgb(qdct["color_special1"].rgb())
        self.expview.ex_main.brush_library.setColor(qdct["color_special1"])
        self.expview.ex_secondary.brush_library.setColor(qdct["color_special1"])

        # manually update all SongTable instances in the app
        songtables = [self.libview.tbl_song,]
        for i in range( self.tabview.count() ):
            tab = self.tabview.widget(i)
            if isinstance(tab,PlaylistEditView):
                songtables.append( tab.tbl_lib)
                songtables.append( tab.tbl_pl)
        colors = ( qdct["text_important1"], \
                   qdct["text_important2"], \
                   qdct["theme_p_mid"]    , \
                   qdct["color_special1"] )
        for table in songtables:
            table.setRuleColors(*colors)
        self.pleditview.setRuleColors(*colors)

        # create and set a custom palette for the song view
        p = self.palette()
        CG   = [QPalette.Disabled,QPalette.Active,QPalette.Inactive]
        for cg in CG:
            p.setColor( cg, QPalette.Light    , qdct['theme_s_mid']   )
            p.setColor( cg, QPalette.Dark     , qdct['theme_s_vdark']   )
        cfont = self.songview.font()
        self.songview.setPalette(p)
        self.songview.resize()

        h = 48#self.songview.height()
        self.btn_playpause.setFixedHeight( h )
        self.btn_playpause.setFixedWidth( h )

        h=self.songview.height()
        self.aartview.setFixedHeight(h)
        self.aartview.setFixedWidth(h)

        if self.controller.dspSupported():
            self.peqview.setColors()

        s = Settings.instance()
        s["current_theme"] = theme

def setSettingsDefaults():

    data = {}

    data["current_theme"] = "none"

    data["current_position"] = 0
    data["current_song_id"] = 0

    data["backup_enabled"] = 1
    data["backup_directory"] = "./backup"

    data["volume"] = 50
    data["volume_equalizer"] = 0 # off

    data["ui_show_console"] = 0    # off
    data["ui_show_error_log"] = 0  # off
    data["ui_show_visualizer"] = 1 # on
    data["ui_show_treeview"] = 1   # on
    data["ui_show_history"] = 0

    data["keyhook_playpause"] =  0xB3
    data["keyhook_stop"] =  0xB2
    data["keyhook_prev"] =  0xB1
    data["keyhook_next"] =  0xB0

    data["enable_keyboard_hook"] = 1 # on by default
    data["enable_remote_commands"] = 0 # off by default

    data["enable_history"] = 1
    data["enable_history_update"] = 0
    data["path_alternatives"] = []

    # when empty] =  default order is used
    data["ui_library_column_order"] = []
    data["ui_quickselect_favorite_artists"] = []
    data["ui_quickselect_favorite_genres"] = []

    data["playlist_size"] = 50
    data["playlist_preset_default"] = 0
    data["playlist_presets"] = [
        "ban=0 && date>14",
        ]
    data["playlist_preset_names"] = [
        "Not Recent",
        ]

    Settings.instance().setMulti(data,False)

def handle_exception(exc_type, exc_value, exc_traceback):
    for line in traceback.format_exception(exc_type,exc_value,exc_traceback):
        sys.stderr.write(line)

def main(version="",commitdate="",builddate=""):

    app = QApplication(sys.argv)
    if version == "":
        version = "{:%H:%M}".format(datetime.now())
        app.setApplicationName("Yue Debug %s"%(version))
    else:
        app.setApplicationName("Yue Music Player - v%s"%(version))

    app.setQuitOnLastWindowClosed(True)
    app_icon = QIcon(':/img/icon.png')
    app.setWindowIcon(app_icon)

    parser = argparse.ArgumentParser(description='Audio Playback and Library Manager')
    parser.add_argument('--sound', default="default",
                   help='set sound device: default, bass, dummy')
    parser.add_argument('--altdb', default=False, action="store_true",
                   help='use separate db for settings')
    args = parser.parse_args()

    with LogView(trace=False,echo=True) as diag:

        start = time.time()
        sys.excepthook = handle_exception

        plugin_path = pybass.get_plugin_path();

        settings_db_path = "./settings.db"
        db_path = "./yue.db"

        sys.stdout.write("Loading database\n")

        if os.path.exists(settings_db_path) or args.altdb:
            sys.stdout.write("Separate Settings db found.\n")
            settings_sqlstore = SQLStore(settings_db_path)
            Settings.init( settings_sqlstore )
            Settings.instance().setDefault("db_path","./yue.db")
            db_path = Settings.instance()['db_path']
            sqlstore = SQLStore(db_path)
        else:
            sqlstore = SQLStore(db_path)
            Settings.init( sqlstore )

        Library.init( sqlstore )
        PlaylistManager.init( sqlstore )
        History.init( sqlstore )
        #History.instance().setEnabled(True)
        Library.instance().history = History.instance()

        setSettingsDefaults()

        sys.stdout.write("Create Sound Device\n")
        pl=PlaylistManager.instance().openCurrent()
        device = newDevice(pl,plugin_path,kind=args.sound)

        sys.stdout.write("Initializing application (%f)\n"%(time.time()-start))
        print("build info: `%s` `%s`"%(version,commitdate))
        window = MainWindow( diag, device, (version,commitdate,builddate) )

        sys.stdout.write("Initialization Complete. Showing Window (%f)\n"%(time.time()-start))
        window.showWindow()

    sys.exit(app.exec_())

