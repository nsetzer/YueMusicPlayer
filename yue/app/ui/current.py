
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.clock import mainthread

from yue.app.widgets.songinfo import SongInfo


from yue.app.widgets.playlist import PlayListViewWidget
from yue.app.settings import Settings
from yue.app.sound.manager import SoundManager
from yue.core.library import Library
from yue.core.playlist import PlaylistManager

from yue.app.ui.util import PlayListToViewList

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

        idx,_ = playlist.current()
        scr = Settings.instance().manager.get_screen( Settings.instance().screen_current_playlist )
        scr.view.setHighlight(idx)

        #self.update_labels()

    def on_double_tap(self,index, elem):
        # this is essentially a non-android feature
        SoundManager.instance().play_index( index )

    def on_tap(self,idx,elem,*args):
        song = Library.instance().songFromId( elem.uid )

        content = SongInfo( song, action_label="play song" )
        popup = Popup(title='Song Information',
                  content=content,
                  size_hint=(.9,.9) )

        def on_action(*args):
            SoundManager.instance().play_index( idx )
            popup.dismiss()

        content.bind(on_action= on_action)
        content.bind(on_accept= lambda *x : popup.dismiss() )
        content.bind(on_reject= lambda *x : popup.dismiss() )

        popup.open()


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

        idx,_ = playlist.current()
        size = playlist.size()
        playlist.shuffle_range(idx+1,size)

        lst = list(playlist.iter())
        viewlst = PlayListToViewList(  Library.instance(), lst )
        self.setPlayList( viewlst )
