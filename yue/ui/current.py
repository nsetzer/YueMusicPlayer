
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label

from yue.custom_widgets.view import TreeViewWidget, ListViewWidget, TreeElem, ListElem
from yue.custom_widgets.playlist import PlayListViewWidget
from yue.settings import Settings

class CurrentPlaylistScreen(Screen):
    def __init__(self,**kwargs):
        super(CurrentPlaylistScreen,self).__init__(**kwargs)

        row_height = Settings.instance().row_height()
        self.vbox = BoxLayout(orientation='vertical')
        self.hbox = BoxLayout(orientation='horizontal')
        self.hbox.size_hint=(1.0,None)
        self.hbox.height=row_height

        self.btn_home = Button(text="home")
        self.btn_home.size_hint = (1.0,None)
        self.btn_home.height = row_height
        self.btn_home.bind(on_press=Settings.instance().go_home)
        self.btn_nowplaying = Button(text="Now Playing")
        self.btn_nowplaying.size_hint = (1.0,None)
        self.btn_nowplaying.height = row_height
        self.btn_nowplaying.bind(on_press=Settings.instance().go_now_playing)
        self.hbox.add_widget(self.btn_home)
        self.hbox.add_widget(self.btn_nowplaying)

        self.view = PlayListViewWidget(font_size = Settings.instance().font_size)

        self.add_widget( self.vbox )
        self.vbox.add_widget( self.hbox )
        self.vbox.add_widget( self.view )

    def setLibraryTree(self,data):
        self.view.setData(data)