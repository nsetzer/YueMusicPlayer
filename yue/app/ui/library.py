
"""
todo:
    swipe right on SONG : add to next in current playlist
"""
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.clock import mainthread

from yue.app.widgets.songinfo import SongInfo
from yue.app.widgets.tristate import TriState
from yue.app.widgets.view import TreeViewWidget
from yue.app.settings import Settings
from yue.core.library import Library
from yue.core.playlist import PlaylistManager
from yue.app.sound.manager import SoundManager


from yue.app.ui.util import PlayListToViewList, PlayListFromTree, TrackTreeElem

class LibraryScreen(Screen):

    def __init__(self,**kwargs):
        super(LibraryScreen,self).__init__(**kwargs)

        row_height = Settings.instance().row_height()
        self.vbox = BoxLayout(orientation='vertical')
        self.hbox = BoxLayout(orientation='horizontal')
        self.hbox.size_hint=(1.0,None)
        self.hbox.height=row_height

        self.btn_home = Button(text="home")
        self.btn_home.size_hint = (1.0,None)
        self.btn_home.height = row_height
        self.btn_home.bind(on_press=Settings.instance().go_home)
        self.btn_select = Button(text="toggle-select-all")
        self.btn_select.size_hint = (1.0,None)
        self.btn_select.height = row_height
        self.btn_select.bind(on_press=lambda *x:self.toggleSelection())

        self.lbl_placeholder = Label(text="please wait")
        self.view = TreeViewWidget(font_size = Settings.instance().font_size)

        self.btn_create = Button(text="Create Playlist")
        self.btn_create.size_hint = (1.0,None)
        self.btn_create.height = row_height
        self.btn_create.bind(on_press=self.on_create_playlist)

        self.hbox.add_widget(self.btn_home)
        self.hbox.add_widget(self.btn_select)
        self.hbox.add_widget( self.btn_create )

        self.add_widget( self.vbox )
        self.vbox.add_widget( self.lbl_placeholder )
        self.vbox.add_widget( self.hbox )

        self.view.bind(on_tap=self.on_tap_song)
        self.view.bind(on_press_aux1=self.on_press_aux1)

    @mainthread
    def setPlaceholderText(self,msg):
        self.lbl_placeholder.text = msg

    @mainthread
    def setLibraryTree(self,data):

        if self.lbl_placeholder is not None:
            self.vbox.remove_widget( self.lbl_placeholder )
            self.vbox.add_widget( self.view, index=1 )
            self.lbl_placeholder = None

        self.view.setData(data)

    def toggleSelection(self,state=None):
        # if no target state is given, check to see if any
        # elements are selected, if they are then unselect all
        # otherwise set all to selected
        if state is None:
            state = TriState.checked
            for item in self.view.data:
                if item.check_state is not TriState.unchecked:
                    state = TriState.unchecked
                    break;

        for item in self.view.data:
            item.setChecked( state )

        self.view.update_labels()

    def on_create_playlist(self,*args):

        # i should do this asynchronously
        # but i don't yet know how to disable the button until
        # the task completes
        # also, I think I want this to pull up a new screen for more options

        # so for now, this will do everything, but it will change soon

        lst = PlayListFromTree( Library.instance(), self.view.data )
        if len(lst) == 0:
            return

        self.toggleSelection(TriState.unchecked)

        viewlst = PlayListToViewList( Library.instance(), lst )

        settings = Settings.instance()
        scr = settings.manager.get_screen( settings.screen_current_playlist )
        scr.setPlayList( viewlst )

        playlist = PlaylistManager.instance().openPlaylist('current')
        playlist.set( lst )
        SoundManager.instance().play_index(0)

    def on_tap_song(self,obj, idx, elem, *args):

        state = TriState.checked
        if elem.check_state is not TriState.unchecked:
            state = TriState.unchecked
        elem.setChecked( state )
        self.view.update_labels()

    def on_press_aux1(self,obj,elem,*args):

        #TODO: there are options for aux on album, artist
        # display album art, # of songs, ability to change album name
        # for artist, display artist, number of albums, number of songs
        # and ability to change artist name.
        # changing artist, album is an easy database change

        if isinstance(elem,TrackTreeElem):
            song = Library.instance().songFromId( elem.uid )
            content = SongInfo( song, action_label="play next" )

            popup = Popup(title='Song Information',
                          content=content,
                          size_hint=(.9,.9) )

            def on_action(*args):
                playlist = PlaylistManager.instance().openPlaylist('current')
                playlist.insert_next( elem.uid )

                lst = list(playlist.iter())
                viewlst = PlayListToViewList( Library.instance(), lst )
                settings = Settings.instance()
                scr = settings.manager.get_screen( settings.screen_current_playlist )
                scr.setPlayList( viewlst )

                popup.dismiss()

            content.bind(on_action= on_action  )
            content.bind(on_accept= lambda *x : popup.dismiss() )
            content.bind(on_reject= lambda *x : popup.dismiss() )
            popup.open()
