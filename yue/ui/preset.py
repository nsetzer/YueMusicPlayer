
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
from sqlite3 import OperationalError

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
#from kivy.uix.label import Label
from kivy.logger import Logger
from kivy.uix.scrollview import ScrollView
#from kivy.uix.gridlayout import GridLayout

from yue.custom_widgets.view import TreeViewWidget
from yue.custom_widgets.querybuilder import QueryBuilder, QueryKind

from yue.ui.util import libraryToTree, libraryToTreeFromIterable, queryParamToRule

from yue.settings import Settings
from yue.library import Library

from yue.search import sql_search

class PresetScreen(Screen):
    def __init__(self,**kwargs):
        super(PresetScreen,self).__init__(**kwargs)

        self.vbox = BoxLayout(orientation='vertical')
        self.add_widget(self.vbox)

        self.btn_home = Button(text="home")
        self.btn_home.bind(on_press=Settings.instance().go_home)
        self.vbox.add_widget( self.btn_home )

class ModifyPresetScreen(Screen):
    def __init__(self,**kwargs):
        super(ModifyPresetScreen,self).__init__(**kwargs)

        self.vbox = BoxLayout(orientation='vertical')
        self.add_widget(self.vbox)

        row_height = Settings.instance().row_height()

        kind_map = { QueryKind.LIKE : "~",
                     QueryKind.NOTLIKE : "!~",
                     QueryKind.EQ : "==",
                     QueryKind.NE : "!=",
                     QueryKind.LT : "<",
                     QueryKind.LE : "<=",
                     QueryKind.GT : ">",
                     QueryKind.GE : ">=",
                     QueryKind.BETWEEN : "<->",
                     QueryKind.NOTBETWEEN : "-><-",
                     QueryKind.AND : "&",
                     QueryKind.OR : "||", }
        columns = {'all-text':str, 'artist':str, 'album':str, 'title':str,
         'playcount':int, 'year':int, 'last_played':int }

        self.scrollview = ScrollView(size_hint=(1.0, None), )
        self.queryview = QueryBuilder( columns, kind_map, default_column = 'all-text' )
        self.queryview.bind(on_children_change=self.on_terms_change)
        self.queryview.newTerm()
        self.scrollview.add_widget( self.queryview )

        self.treeview = TreeViewWidget(font_size = Settings.instance().font_size)


        self.btn_new = Button(text="+")
        self.btn_new.bind(on_press= lambda *x : self.queryview.newTerm() )
        self.btn_new.size_hint = (None,None)
        self.btn_new.size = (row_height,row_height)

        self.btn_query = Button(text="search")
        self.btn_query.bind(on_press=self.executeQuery)
        self.btn_query.size_hint = (1.0,None)
        self.btn_query.height = row_height

        self.hbox_mid = BoxLayout(orientation='horizontal')
        self.hbox_mid.size_hint = (1.0,None)
        self.hbox_mid.height = row_height
        self.hbox_mid.add_widget( self.btn_new )
        self.hbox_mid.add_widget( self.btn_query )

        qb_row_height = self.queryview.row_height
        # TODO: determine height of one query editor, show ~2-3 rows depending on height



        self.btn_home = Button(text="home")
        self.btn_home.bind(on_press=Settings.instance().go_home)
        self.btn_save   = Button(text='save')
        self.btn_create = Button(text='Create Playlist')
        self.hbox_bot = BoxLayout(orientation='horizontal')
        self.hbox_bot.size_hint = (1.0,None)
        self.hbox_bot.height = row_height
        self.hbox_bot.add_widget(self.btn_home)
        self.hbox_bot.add_widget(self.btn_save)
        self.hbox_bot.add_widget(self.btn_create)

        self.vbox.add_widget( self.scrollview )
        self.vbox.add_widget( self.hbox_mid )
        self.vbox.add_widget( self.treeview )
        self.vbox.add_widget( self.hbox_bot )

        self.bind(size=self.resize)
        self.bind(pos=self.resize)

    def resize(self, *args):

        pass

    def on_terms_change(self, obj, count, *args):
        factor = min(3.5,float(count))
        self.scrollview.height = factor * self.queryview.row_height

    def executeQuery(self,*args):

        query = self.queryview.toQuery()

        rule = queryParamToRule( Library.instance(), query )
        if rule is None:
            # execute blank search
            tree = libraryToTree( Library.instance() )
            self.setData( tree)
            return

        sql,values = rule.sql()
        try:
            Logger.info("sql: %s"%sql)
            Logger.info("sql: %s"%values)
            result = sql_search( Library.instance().db, rule )
            tree =  libraryToTreeFromIterable( result )
            self.setData( tree)
        except OperationalError as e:

            Logger.error("sql: %s"%e)

    def setData(self, tree):
        self.treeview.setData( tree )

    def toggleSelection(self,state=None):
        """ TODO: library implements a toggle select all, which should
            be moved into the tree view class. """
        pass

