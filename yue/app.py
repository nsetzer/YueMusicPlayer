#! cd .. && python2.7 main.py --size=480x640
import os
"""

todo:
    https://kivy.org/docs/api-kivy.app.html
    see built in support for settings,

    Pause Mode
"""

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
from yue.sound.manager import SoundManager

from threading import Thread
import time

class BackgroundDataLoad(Thread):
    def __init__(self):
        super(BackgroundDataLoad,self).__init__()

    def run(self):

        Logger.info("data: starting background load thread")

        settings = Settings.instance()

        scr_lib = settings.manager.get_screen( settings.screen_library )
        scr_cur = settings.manager.get_screen( settings.screen_current_playlist )

        # simulate taking a long time to load:
        #n=20
        #for i in range(n):
        #    msg = "please wait... %%%d"%(100*i/(n-1))
        #    scr_cur.setPlaceholderText( msg )
        #    scr_lib.setPlaceholderText( msg )
        #    time.sleep(.25)

        # load a test library into the database
        Library.instance().loadTestData( os.path.join( \
            Settings.instance().platform_path,"library.ini") );

        # this is fairly slow for larger data sets
        # I should launch a background thread which:
        #     - loads current playlist and displays it in 'current'
        #     - loads the tree view and displays it in 'library'
        # while loading, display a 'please wait message' in the screen
        # In the future, a different database may improve speed
        tree = Library.instance().toTree()
        lst = list(Library.instance().db.keys())[:20]
        viewlst = Library.instance().PlayListToViewList( lst )
        SoundManager.instance().setCurrentPlayList( lst )

        scr_lib.setLibraryTree( tree )
        scr_cur.setPlayList( viewlst )

        Logger.info("data: background load thread finished")


class YueApp(App):
    title = "Yue Music Player"
    icon = "./img/icon.png"

    def __init__(self,**kwargs):
        super(YueApp,self).__init__(**kwargs)
        self.bg_thread = None

    def build(self):

        # create the screen manager and application screens
        sm = ScreenManager(transition=FadeTransition())

        # init controller objects
        Settings.init( sm )
        Library.init()
        SoundManager.init( Settings.instance().platform_libpath )

        hm_scr = HomeScreen(name=Settings.instance().screen_home)
        np_scr = NowPlayingScreen(name=Settings.instance().screen_now_playing)
        cu_scr = CurrentPlaylistScreen(name=Settings.instance().screen_current_playlist)
        lb_scr = LibraryScreen(name=Settings.instance().screen_library)
        pr_scr = PresetScreen(name=Settings.instance().screen_presets)
        in_scr = IngestScreen(name=Settings.instance().screen_ingest)
        se_scr = SettingsScreen(name=Settings.instance().screen_settings)

        sm.add_widget(hm_scr)
        sm.add_widget(cu_scr)
        sm.add_widget(np_scr)
        sm.add_widget(lb_scr)
        sm.add_widget(pr_scr)
        sm.add_widget(in_scr)
        sm.add_widget(se_scr)

        # initialize data to be displayed

        self.bg_thread = BackgroundDataLoad()
        self.bg_thread.start()

        return sm

    def on_pause():
        return True # prevent on_stop when in background

    def on_resume():
        pass # not guaranteed after an on_pause

    def on_start(self):
        Logger.info('Yue: start')

    def on_stop(self):
        # TODO save current playlist to settings db

        Logger.info('Yue: on exit joining threads')

        if self.bg_thread is not None:
            #TODO: send kill msg
            self.bg_thread.join()

        Logger.critical('Yue: exit')
