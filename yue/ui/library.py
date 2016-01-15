

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label

from yue.custom_widgets.tristate import TriState
from yue.custom_widgets.view import TreeViewWidget, ListViewWidget, TreeElem, ListElem
from yue.settings import Settings
from yue.library import Library
from yue.sound import SoundManager

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
        self.hbox.add_widget(self.btn_home)
        self.hbox.add_widget(self.btn_select)

        self.view = TreeViewWidget(font_size = Settings.instance().font_size)

        self.btn_create = Button(text="Create Playlist")
        self.btn_create.size_hint = (1.0,None)
        self.btn_create.height = row_height
        self.btn_create.bind(on_press=self.on_create_playlist)

        self.add_widget( self.vbox )
        self.vbox.add_widget( self.hbox )
        self.vbox.add_widget( self.view )
        self.vbox.add_widget(self.btn_create)

    def setLibraryTree(self,data):
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

        lst = Library.instance().PlayListFromTree( self.view.data )
        if len(lst) == 0:
            return

        self.toggleSelection(TriState.unchecked)

        viewlst = Library.instance().PlayListToViewList( lst )

        settings = Settings.instance()
        scr = settings.manager.get_screen( settings.screen_current_playlist )
        scr.setPlayList( viewlst )
        SoundManager.instance().setCurrentPlayList( lst )
        SoundManager.instance().play()
