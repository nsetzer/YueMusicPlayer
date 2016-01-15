#! python2.7 main.py --size=480x640
__version__ = "1.0"
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.logger import Logger

from yue.ui.library import LibraryScreen
from yue.ui.home import HomeScreen
from yue.ui.nowplaying import NowPlayingScreen
from yue.ui.current import CurrentPlaylistScreen
from yue.library import Library
from yue.settings import Settings

class YueApp(App):

    def build(self):

        Settings.init()

        Library.test_init()
        data = Library.instance().toTree()

        sm = ScreenManager(transition=FadeTransition())
        Settings.instance().manager = sm

        sm.add_widget(HomeScreen(name=Settings.instance().screen_home))
        sm.add_widget(CurrentPlaylistScreen(name=Settings.instance().screen_current_playlist))
        sm.add_widget(NowPlayingScreen(name=Settings.instance().screen_now_playing))
        ls = LibraryScreen(name=Settings.instance().screen_library)
        ls.setLibraryTree(data)
        sm.add_widget(ls)

        return sm

    def on_start(self):
        Logger.info('Yue Start')

    def on_stop(self):
        Logger.critical('Yue Exit.')

YueApp().run()
