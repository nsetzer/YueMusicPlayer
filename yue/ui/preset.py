
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

"""
from sqlite3 import OperationalError

from kivy.core.text import Label as CoreLabel
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.logger import Logger

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
    QueryKind.AND : AndSearchRule,
    QueryKind.OR : OrSearchRule,
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
        self.cached_height = lbl.get_extents("_")[1]

        self.btn_home = Button(text="home")
        self.btn_home.bind(on_press=Settings.instance().go_home)
        self.btn_home.size_hint = (1.0,None)
        self.btn_home.height = 2 * self.cached_height

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

        self.btn_query = Button(text="execute query")
        self.btn_query.bind(on_press=self.executeQuery)

        self.btn_query.size_hint = (1.0,None)
        self.btn_query.height = 2 * self.cached_height

        self.vbox.add_widget( self.btn_home )
        self.vbox.add_widget( self.queryview )
        self.vbox.add_widget( self.btn_query )
        self.vbox.add_widget( self.treeview )


    def executeQuery(self,*args):

        query = self.queryview.toQuery()

        rules = []
        for c,a,v in query:

            rule_type = kindToRule[a]

            if c == 'all-text':
                rule = createAllTextRule(*v)
            else:
                rule = rule_type(c,*v)
            rules.append( rule )

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



def createAllTextRule( string ):
    rule = OrSearchRule( [ PartialStringSearchRule("artist",string),
                           PartialStringSearchRule("composer",string),
                           PartialStringSearchRule("album",string),
                           PartialStringSearchRule("title",string),
                           PartialStringSearchRule("genre",string),
                           PartialStringSearchRule("comment",string) ] )
    return rule

