
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

from kivy.core.text import Label as CoreLabel
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.logger import Logger
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout

from yue.custom_widgets.view import TreeViewWidget, TreeElem
from yue.custom_widgets.querybuilder import QueryBuilder, QueryKind


from yue.settings import Settings
from yue.library import Library

from yue.search import PartialStringSearchRule, \
                       InvertedPartialStringSearchRule, \
                       ExactSearchRule, \
                       InvertedExactSearchRule, \
                       LessThanSearchRule, \
                       LessThanEqualSearchRule, \
                       GreaterThanSearchRule, \
                       GreaterThanEqualSearchRule, \
                       RangeSearchRule, \
                       NotRangeSearchRule, \
                       AndSearchRule, \
                       OrSearchRule, \
                       sql_search

kindToRule = {
    QueryKind.LIKE    : PartialStringSearchRule,
    QueryKind.NOTLIKE : InvertedPartialStringSearchRule,
    QueryKind.EQ : ExactSearchRule,
    QueryKind.NE : InvertedExactSearchRule,
    QueryKind.LT : LessThanSearchRule,
    QueryKind.LE : LessThanEqualSearchRule,
    QueryKind.GT : GreaterThanSearchRule,
    QueryKind.GE : GreaterThanEqualSearchRule,
    QueryKind.BETWEEN : RangeSearchRule,
    QueryKind.NOTBETWEEN : NotRangeSearchRule,
}

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

        lbl = CoreLabel()
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

        self.queryview = QueryBuilder( columns, kind_map, default_column = 'all-text' )
        self.queryview.newTerm()

        self.treeview = TreeViewWidget(font_size = Settings.instance().font_size)

        self.btn_new = Button(text="new")
        self.btn_new.bind(on_press= lambda *x : self.queryview.newTerm() )
        self.btn_new.size_hint = (1.0,None)
        self.btn_new.height = row_height

        self.btn_query = Button(text="search")
        self.btn_query.bind(on_press=self.executeQuery)
        self.btn_query.size_hint = (1.0,None)
        self.btn_query.height = row_height

        qb_row_height = self.queryview.row_height
        # TODO: determine height of one query editor, show ~2-3 rows depending on height
        self.scrollview = ScrollView(size_hint=(1.0, None), height = 3.5 * qb_row_height)
        self.scrollview.add_widget( self.queryview )

        self.hbox_bot = BoxLayout(orientation='horizontal')
        self.hbox_bot.size_hint = (1.0,None)
        self.hbox_bot.height = row_height
        self.btn_home = Button(text="home")
        self.btn_home.bind(on_press=Settings.instance().go_home)
        #self.btn_home.size_hint = (1.0,None)
        #self.btn_home.height = row_height
        self.btn_save   = Button(text='save')
        #self.btn_save.size_hint = (1.0,None)
        #self.btn_save.height = row_height
        self.btn_create = Button(text='Create Playlist')
        #self.btn_create.size_hint = (1.0,None)
        #self.btn_create.height = row_height
        self.hbox_bot.add_widget(self.btn_home)
        self.hbox_bot.add_widget(self.btn_save)
        self.hbox_bot.add_widget(self.btn_create)

        self.vbox.add_widget( self.btn_new )
        self.vbox.add_widget( self.scrollview )
        self.vbox.add_widget( self.btn_query )
        self.vbox.add_widget( self.treeview )
        self.vbox.add_widget( self.hbox_bot )

        self.bind(size=self.resize)
        self.bind(pos=self.resize)

    def resize(self, *args):

        #self.scrollview.height = self.height/3
        pass

    def executeQuery(self,*args):

        query = self.queryview.toQuery()

        rules = []
        for c,a,v in query:

            rule_type = kindToRule[a]

            if c == 'all-text':
                rule = createAllTextRule(a, *v)
            else:
                rule = rule_type(c,*v)
            rules.append( rule )

        if len(rules) == 0:
            # execute blank search
            tree =  Library.instance().toTree( )
            self.treeview.setData( tree)
            return

        rule = AndSearchRule(rules)
        sql,values = rule.sql()
        try:
            Logger.info("sql: %s"%sql)
            Logger.info("sql: %s"%values)
            result = sql_search( Library.instance().db, rule )
            tree =  Library.instance().toTreeFromIterable( result )
            self.treeview.setData( tree)
        except OperationalError as e:

            Logger.error("sql: %s"%e)

    def toggleSelection(self,state=None):
        """ TODO: library implements a toggle select all, which should
            be moved into the tree view class. """
        pass

def createAllTextRule( action, string ):

    meta = OrSearchRule
    if action in (QueryKind.NOTLIKE, QueryKind.NE):
        meta = AndSearchRule
    str_rule = kindToRule[ action ]

    rule = meta( [ str_rule("artist",string),
                   str_rule("composer",string),
                   str_rule("album",string),
                   str_rule("title",string),
                   str_rule("genre",string),
                   str_rule("comment",string) ] )
    return rule

