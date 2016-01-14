#! python2.7 main.py
__version__ = "1.0"
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition

from yue.screen import HomeScreen, NowPlayingScreen, LibraryScreen

class DemoApp(App):

    def build(self):

        sm = ScreenManager(transition=FadeTransition())
        sm.add_widget(HomeScreen(name='Home'))
        sm.add_widget(NowPlayingScreen(name='Now Playing'))
        sm.add_widget(LibraryScreen(name='Library'))

        return sm

DemoApp().run()
