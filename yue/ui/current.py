
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.clock import mainthread

from yue.custom_widgets.view import TreeViewWidget, ListViewWidget, TreeElem, ListElem
from yue.custom_widgets.playlist import PlayListViewWidget
from yue.settings import Settings
from yue.sound.manager import SoundManager
from yue.library import Library
from yue.playlist import PlaylistManager

class CurrentPlayListViewWidget(PlayListViewWidget):
    """docstring for PlayListViewWidget"""

    def swipeEvent(self,elem_idx, elem,direction):
        """ direction is one of : "left", "right" """
        super(CurrentPlayListViewWidget,self).swipeEvent(elem_idx, elem, direction)

        playlist = PlaylistManager.instance().openPlaylist('current')
        playlist.delete( elem_idx )

    def on_drop(self,i,j):
        if j < i : # ensure droped element is inserted after
            j += 1

        # execute a move in the playlist
        playlist = PlaylistManager.instance().openPlaylist('current')
        playlist.reinsert(i,j)

        # re insert list view data
        item = self.data[i]
        del self.data[i]
        self.data.insert(j,item)

        self.update_labels()

    def on_double_tap(self,index):
        SoundManager.instance().play_index( index )

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
        self.btn_shuffle = Button(text="Shuffle")
        self.btn_shuffle.size_hint = (1.0,None)
        self.btn_shuffle.height = row_height
        self.btn_shuffle.bind(on_press=self.shuffle_playlist)

        self.lbl_placeholder = Label(text="please wait")

        self.hbox.add_widget(self.btn_home)
        self.hbox.add_widget(self.btn_nowplaying)
        self.hbox.add_widget(self.btn_shuffle)

        self.view = CurrentPlayListViewWidget(font_size = Settings.instance().font_size)

        self.add_widget( self.vbox )
        self.vbox.add_widget( self.hbox )
        self.vbox.add_widget( self.lbl_placeholder )

    @mainthread
    def setPlaceholderText(self,msg):
        self.lbl_placeholder.text = msg

    @mainthread
    def setPlayList(self,data):

        if self.lbl_placeholder is not None:
            self.vbox.remove_widget( self.lbl_placeholder )
            self.vbox.add_widget( self.view, index=0 )
            self.lbl_placeholder = None

        self.view.setData(data)

    def shuffle_playlist(self,*args):

        playlist = PlaylistManager.instance().openPlaylist('current')

        idx,_ = playlist.current(current,end)
        size = playlist.size()
        playlist.shuffle_range(idx,size)

        lst = SoundManager.instance().current_playlist
        viewlst = Library.instance().PlayListToViewList( lst )
        self.setPlayList( viewlst )
