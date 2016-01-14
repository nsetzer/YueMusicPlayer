

from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label

Builder.load_string("""

<NowPlayingScreen>:
    BoxLayout:
        orientation: 'horizontal'
        Button:
            text: 'Home'
            on_press:
                root.manager.current = 'Home'
        Label:
            text: 'Now Playing'

""")

# TODO
class NowPlayingScreen(Screen):
    pass

