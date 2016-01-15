
"""

Expected features:
    playpause tile
    album art tile, possibly song name, artist
    buttons for:
        Now Playing
            - screen for current song playing
            - audio controls
        Library
            - screen for creating playlists
        Current Playlist
            - screen listing songs in current playlist
            - user should be able to remove songs and shuffle
        Settings
            - change font size, font family.
            - import/export library to xml
            - scan file system
"""
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label

from kivy.lang import Builder

from yue.custom_widgets.view import TreeViewWidget, ListViewWidget, TreeElem, ListElem
from yue.settings import Settings

class HomeScreen(Screen):
    def __init__(self,**kwargs):
        super(HomeScreen,self).__init__(**kwargs)

        self.vbox = BoxLayout(orientation='vertical')
        self.add_widget(self.vbox)

        self.btn_nowplaying = Button(text="Now Playing")
        self.btn_current    = Button(text="Current Playlist")
        self.btn_library    = Button(text="Library")
        self.btn_settings   = Button(text="Settings")

        self.vbox.add_widget(self.btn_nowplaying)
        self.vbox.add_widget(self.btn_current)
        self.vbox.add_widget(self.btn_library)
        self.vbox.add_widget(self.btn_settings)

        self.btn_library.bind(on_press=Settings.instance().go_library)
        self.btn_current.bind(on_press=Settings.instance().go_current_playlist)
        self.btn_nowplaying.bind(on_press=Settings.instance().go_now_playing)

    def setLibraryTree(self,data):
        self.view.setData(data)