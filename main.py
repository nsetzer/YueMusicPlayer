#! python2.7 main.py
__version__ = "1.0"
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition

from yue.ui.library import LibraryScreen
from yue.ui.home import HomeScreen
from yue.ui.nowplaying import NowPlayingScreen
from yue.library import Library
from yue.settings import Settings

class DemoApp(App):

    def build(self):

        Settings.init()

        Library.test_init()
        data = Library.instance().toTree()

        sm = ScreenManager(transition=FadeTransition())
        Settings.instance().manager = sm

        sm.add_widget(HomeScreen(name=Settings.instance().screen_home))
        sm.add_widget(NowPlayingScreen(name=Settings.instance().screen_now_playing))
        ls = LibraryScreen(name=Settings.instance().screen_library)
        ls.setLibraryTree(data)
        sm.add_widget(ls)

        return sm

DemoApp().run()
