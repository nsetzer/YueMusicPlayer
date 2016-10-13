
"""
display a list of 'preset' / 'dynamic' playlist options

selecting a preset should go to the prest modifier screen.
which displays the set of selected songs as a tree view,
and allows for modifying the preset, creating a playist

e.g.
    songs that have not been played in the last two weeks.
    artist of the day
    album of the day

TODO:
    after writing 'preset' everywhere, i want to change it to
        'Dynamic Playlists'

    query with a string field that is empty should be dropped,
        or throw an error.

"""
import random
from sqlite3 import OperationalError

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
#from kivy.uix.label import Label
from kivy.logger import Logger
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.clock import mainthread

#from kivy.uix.gridlayout import GridLayout

from yue.app.widgets.view import TreeViewWidget, ListViewWidget, ListElem
from yue.app.widgets.querybuilder import QueryBuilder, QueryKind

from yue.app.ui.util import libraryToTree, libraryToTreeFromIterable, queryParamToRule
from yue.app.ui.util import PlayListToViewList, PlayListFromTree, TrackTreeElem
from yue.app.widgets.tristate import TriState
from yue.app.sound.manager import SoundManager

from yue.app.settings import Settings
from yue.core.library import Library
from yue.core.playlist import PlaylistManager
from yue.core.song import Song
from yue.core.search import ParseError

class PresetElem(ListElem):
    def __init__(self, name, query):
        super(PresetElem, self).__init__(name)
        self.query = query

class PresetViewWidget(ListViewWidget):

    def on_tap(self,idx,elem,*args):
        print(idx,elem)

        settings = Settings.instance()

        settings.go_library()

        scr = settings.manager.get_screen( settings.screen_library )
        scr.txt_filter.text = elem.query
        scr.executeQuery()

class PresetScreen(Screen):
    def __init__(self,**kwargs):
        super(PresetScreen,self).__init__(**kwargs)

        self.vbox = BoxLayout(orientation='vertical')
        self.add_widget(self.vbox)

        row_height = Settings.instance().row_height()
        fs = Settings.instance().font_size
        self.listview = PresetViewWidget(font_size = fs)

        self.listview.setData([ \
            PresetElem("Not Recent", "date>14"),
            PresetElem("Genre: Stoner","gen=stoner"),
            PresetElem("Album: Gothic Emily","album=\"gothic emily\""),
            PresetElem("Best: Grunge","genre=grunge rating>5"),
            PresetElem("Best: Japanese","country=japan rating>2"),
            PresetElem("Best: Visual Kei","(genre=j-metal || genre=visual) && rating>2") ] )

        self.btn_home = Button(text="home")
        self.btn_home.bind(on_press=Settings.instance().go_home)
        self.btn_home.size_hint = (1.0,None)
        self.btn_home.height = row_height

        self.vbox.add_widget( self.btn_home )
        self.vbox.add_widget( self.listview )

class LibraryScreen(Screen):
    def __init__(self,**kwargs):
        super(LibraryScreen,self).__init__(**kwargs)

        self.vbox = BoxLayout(orientation='vertical')
        self.add_widget(self.vbox)

        row_height = Settings.instance().row_height()
        fs = Settings.instance().font_size
        self.treeview = TreeViewWidget(font_size = fs)

        self.btn_query = Button(text="search")
        self.btn_query.bind(on_press=self.executeQuery)
        self.btn_query.size_hint = (1.0,None)
        self.btn_query.height = row_height

        self.hbox_mid = BoxLayout(orientation='horizontal')
        self.hbox_mid.size_hint = (1.0,None)
        self.hbox_mid.height = row_height
        self.hbox_mid.add_widget( self.btn_query )

        self.btn_home = Button(text="home")
        self.btn_home.bind(on_press=Settings.instance().go_home)
        self.btn_tglchk = Button(text="chk")
        self.btn_tglchk.bind(on_press=lambda *x:self.toggleSelection())

        self.btn_save   = Button(text='save')
        self.btn_create = Button(text='Create Playlist')
        self.hbox_bot = BoxLayout(orientation='horizontal')
        self.hbox_bot.size_hint = (1.0,None)
        self.hbox_bot.height = row_height
        self.hbox_bot.add_widget(self.btn_home)
        self.hbox_bot.add_widget(self.btn_tglchk)
        self.hbox_bot.add_widget(self.btn_save)
        self.hbox_bot.add_widget(self.btn_create)

        self.btn_create.bind(on_press=self.on_create_playlist)

        self.txt_filter = TextInput(multiline=False)
        self.txt_filter.size_hint = (1.0,None)
        self.txt_filter.height = row_height
        self.txt_filter.bind(on_text_validate=self.executeQuery)

        self.vbox.add_widget( self.txt_filter )
        self.vbox.add_widget( self.hbox_mid )
        self.vbox.add_widget( self.treeview )
        self.vbox.add_widget( self.hbox_bot )

        self.bind(size=self.resize)
        self.bind(pos=self.resize)

    def resize(self, *args):
        pass

    @mainthread
    def executeQuery(self,*args):

        try:
            #result = Library.instance().search( self.txt_filter.text, \
            #    orderby=[Song.artist,Song.album,Song.title] )
            tree =  libraryToTree( Library.instance(), rule=self.txt_filter.text )
            self.setData(tree)
        except ParseError as e:
            Logger.error("search error: %s"%e)
            self.setData([])

    def setData(self, tree):
        self.treeview.setData( tree )

    def toggleSelection(self,state=None):
        """ TODO: library implements a toggle select all, which should
            be moved into the tree view class. """
        # if no target state is given, check to see if any
        # elements are selected, if they are then unselect all
        # otherwise set all to selected
        if state is None:
            state = TriState.checked
            for item in self.treeview.data:
                if item.check_state is not TriState.unchecked:
                    state = TriState.unchecked
                    break;

        for item in self.treeview.data:
            item.setChecked( state )

        self.treeview.update_labels()

    def on_create_playlist(self,*args):
        """ TODO this is duplicated from library """
        # i should do this asynchronously
        # but i don't yet know how to disable the button until
        # the task completes
        # also, I think I want this to pull up a new screen for more options

        # so for now, this will do everything, but it will change soon

        lst = PlayListFromTree( Library.instance(), self.treeview.data )
        if len(lst) == 0:
            return

        self.toggleSelection(TriState.unchecked)

        random.shuffle(lst)
        viewlst = PlayListToViewList( Library.instance(), lst )

        settings = Settings.instance()
        scr = settings.manager.get_screen( settings.screen_current_playlist )
        scr.setPlayList( viewlst )

        playlist = PlaylistManager.instance().openPlaylist('current')
        playlist.set( lst )
        SoundManager.instance().play_index(0)