
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition

Builder.load_string("""
<HomeScreen>:
    BoxLayout:
        orientation: 'vertical'
        Button:
            text: 'Now Playing'
            on_press:
                root.manager.current = 'Now Playing'
        Button:
            text: 'Library'
            on_press:
                root.manager.current = 'Library'

<NowPlayingScreen>:
    BoxLayout:
        orientation: 'horizontal'
        Button:
            text: 'Home'
            on_press:
                root.manager.current = 'Home'
        Label:
            text: 'Now Playing'

<LibraryScreen>:
    BoxLayout:
        orientation: 'vertical'
        Button:
            text: 'Home'
            on_press:
                root.manager.current = 'Home'
        Label:
            text: 'Library'

""")

class HomeScreen(Screen):
    pass

class NowPlayingScreen(Screen):
    pass

class LibraryScreen(Screen):
    pass