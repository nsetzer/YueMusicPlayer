#! cd .. && python2.7 main.py --size=480x640
import os

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.logger import Logger

from yue.ui.library import LibraryScreen
from yue.ui.home import HomeScreen
from yue.ui.nowplaying import NowPlayingScreen
from yue.ui.current import CurrentPlaylistScreen
from yue.ui.preset import PresetScreen
from yue.ui.ingest import IngestScreen
from yue.ui.settings import SettingsScreen

from yue.library import Library
from yue.settings import Settings
from yue.sound import SoundManager

class YueApp(App):

    def build(self):

        # init controller objects
        Settings.init()
        Library.init()
        SoundManager.init()

        # create the screen manager and application screens
        sm = ScreenManager(transition=FadeTransition())
        Settings.instance().manager = sm

        hm_scr = HomeScreen(name=Settings.instance().screen_home)
        np_scr = NowPlayingScreen(name=Settings.instance().screen_now_playing)
        cu_scr = CurrentPlaylistScreen(name=Settings.instance().screen_current_playlist)
        lb_scr = LibraryScreen(name=Settings.instance().screen_library)
        pr_scr = PresetScreen(name=Settings.instance().screen_presets)
        in_scr = PresetScreen(name=Settings.instance().screen_ingest)
        se_scr = PresetScreen(name=Settings.instance().screen_settings)

        sm.add_widget(hm_scr)
        sm.add_widget(cu_scr)
        sm.add_widget(np_scr)
        sm.add_widget(lb_scr)
        sm.add_widget(pr_scr)
        sm.add_widget(in_scr)
        sm.add_widget(se_scr)

        # initialize data to be displayed

        # load a test library into the database
        Library.instance().loadTestData( os.path.join( \
            Settings.instance().platform_path,"library.ini") );

        tree = Library.instance().toTree()
        lst = list(Library.instance().db.keys())
        viewlst = Library.instance().PlayListToViewList( lst )

        SoundManager.instance().setCurrentPlayList( lst )

        cu_scr.setPlayList( viewlst )
        lb_scr.setLibraryTree( tree )

        return sm

    def on_start(self):
        Logger.info('Yue Start')

    def on_stop(self):
        # TODO save current playlist to settings db
        Logger.critical('Yue Exit.')
