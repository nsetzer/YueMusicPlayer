#! python2.7 main.py --size=480x640
__version__ = "1.0"

import os

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.logger import Logger

from yue.ui.library import LibraryScreen
from yue.ui.home import HomeScreen
from yue.ui.nowplaying import NowPlayingScreen
from yue.ui.current import CurrentPlaylistScreen
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

        hs = HomeScreen(name=Settings.instance().screen_home)
        ns = NowPlayingScreen(name=Settings.instance().screen_now_playing)
        cs = CurrentPlaylistScreen(name=Settings.instance().screen_current_playlist)
        ls = LibraryScreen(name=Settings.instance().screen_library)

        sm.add_widget(hs)
        sm.add_widget(cs)
        sm.add_widget(ns)
        sm.add_widget(ls)

        # initialize data to be displayed

        # load a test library into the database
        Library.instance().loadTestData( os.path.join( \
            Settings.instance().platform_path,"library.ini") );

        tree = Library.instance().toTree()
        lst = list(Library.instance().db.keys())
        viewlst = Library.instance().PlayListToViewList( lst )

        SoundManager.instance().setCurrentPlayList( lst )

        cs.setPlayList( viewlst )
        ls.setLibraryTree( tree )

        return sm

    def on_start(self):
        Logger.info('Yue Start')

    def on_stop(self):
        # TODO save current playlist to settings db
        Logger.critical('Yue Exit.')

YueApp().run()
