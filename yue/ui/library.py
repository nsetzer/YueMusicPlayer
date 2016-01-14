

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label

from yue.custom_widgets.view import TreeViewWidget, ListViewWidget, TreeElem, ListElem
from yue.settings import Settings

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
        self.btn_select = Button(text="select-all")
        self.btn_select.size_hint = (1.0,None)
        self.btn_select.height = row_height
        self.hbox.add_widget(self.btn_home)
        self.hbox.add_widget(self.btn_select)

        self.view = TreeViewWidget(font_size = Settings.instance().font_size)

        self.btn_create = Button(text="Create Playlist")
        self.btn_create.size_hint = (1.0,None)
        self.btn_create.height = row_height

        self.add_widget( self.vbox )
        self.vbox.add_widget( self.hbox )
        self.vbox.add_widget( self.view )
        self.vbox.add_widget(self.btn_create)

    def setLibraryTree(self,data):
        self.view.setData(data)