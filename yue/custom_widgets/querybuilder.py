#! python2.7 ../../test/test_widget.py query
"""

"""
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.properties import NumericProperty,BooleanProperty
from kivy.graphics import Color, Rectangle, Line
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image, AsyncImage
from kivy.uix.gridlayout import GridLayout
import random

from enum import Enum

from datetime import date, timedelta
from functools import partial

class QueryKind(Enum):
    LIKE=1 # partial match
    EQ=2   # exact match
    NE=3   # not equal
    LT=4   # less than
    LE=5   # less than or equal
    GT=6   # greater than
    GE=7   # greater than or equal
    BETWEEN=8
    NOTBETWEEN=9
    AND=10
    OR=11

class QueryTerm(Widget):
    """
    editor for a single part of a query.

    enables changing parameters of the query.
    """
    def __init__(self, builder, column):
        super(QueryTerm, self).__init__()

        self.builder = builder
        self.column = column

        self.hbox = BoxLayout(orientation='horizontal')
        self.add_widget(self.hbox)

        self.btn_select_action = Button(text='action')
        self.btn_select_action.bind( on_press=self.select_action)

        self.btn_select_column = Button(text=column)
        self.btn_select_column.bind( on_press=self.select_column)

        self.hbox.add_widget(self.btn_select_action)
        self.hbox.add_widget(self.btn_select_column)
        self.hbox.add_widget(TextInput())

        self.bind(size=self.resize)

    def select_action(self, *args):
        content = ActionSelector(self.builder.action_names(self.column),
                                 accept=self.change_action)
        self.popup = Popup(title='Select Action',
                      content=content,
                      size_hint=(.8,.8) )

        self.popup.open()

    def select_column(self,*args):

        content = ColumnSelector(self.builder.column_names(),
                                 accept=self.change_column)
        self.popup = Popup(title='Select Search Field',
                      content=content,
                      size_hint=(.8,.8) )

        self.popup.open()

    def change_action(self, new_action):
        self.btn_select_action.text = str(new_action)

        if self.popup is not None:
            self.popup.dismiss()
            self.popup = None

    def change_column(self, new_column):
        self.btn_select_column.text = new_column

        # TODO: when changing column, set default action
        col_type = self.builder.columns[ new_column ]
        acts = self.builder.column_kind_map[ col_type ]
        self.btn_select_action.text = str(acts[0])

        self.column = new_column

        if self.popup is not None:
            self.popup.dismiss()
            self.popup = None

    def resize(self, *args):
        self.hbox.size = self.size
        self.hbox.pos = self.pos

class ActionSelector(ScrollView):
    """
    display a grid view of possible search actions,
        e.g. exact or partial match, or lt, gt, etc
    """
    def __init__(self, actions, accept = None, **kwargs):
        super(ActionSelector,self).__init__(**kwargs)

        self.accept = accept

        self.vbox = GridLayout(cols=4)
        self.add_widget(self.vbox)

        for action in actions:
            btn = Button(text=str(action))
            btn.action_kind = action
            btn.bind(on_press=self.select)
            self.vbox.add_widget( btn )

    def select( self, btn, *args):
        if self.accept is not None:
            self.accept( btn.action_kind )

class ColumnSelector(ScrollView):

    """
    display a grid view of possible search fields, columns in the db
    """
    def __init__(self, actions, accept = None, **kwargs):
        super(ColumnSelector,self).__init__(**kwargs)

        self.accept = accept

        self.vbox = BoxLayout(orientation='vertical')
        self.add_widget(self.vbox)

        for action in actions:
            btn = Button(text=action)
            btn.bind(on_press=self.select)
            self.vbox.add_widget( btn )

    def select( self, btn, *args):
        if self.accept is not None:
            self.accept( btn.text )

class QueryBuilder(Widget):

    """
    construct with:
    dictionary of action names, icons
        e.g. lt, le, gt, ge, eq, ne, between, not between, etc
    dictionary of meta actions, icons
        e.g. and, or ( i think this is all there is )
    dicitonary of columns, mapping type
        e.g. artist, title : text as python type 'str'
             playcount, date, year : numeric as python type 'int'

    there are essentially three types of terms
        string, allowing exact and partial matching
        numeric, allowing lt, gt, le, ge, ne, eq,
        numeric-range, allowing between, not between

    """
    def __init__(self, columns , default_column=None ):
        super(QueryBuilder, self).__init__()

        self.columns = columns
        self.default_column = default_column
        # by convention, first value in the kind map is the default for that type
        self.column_kind_map = {
            str : [QueryKind.LIKE, QueryKind.EQ],
            int : [
                    QueryKind.EQ,
                    QueryKind.NE,
                    QueryKind.LT,
                    QueryKind.LE,
                    QueryKind.GT,
                    QueryKind.GE,
                    QueryKind.BETWEEN,
                    QueryKind.NOTBETWEEN, ]
        }

        self.vbox = BoxLayout(orientation='vertical')
        self.add_widget(self.vbox)

        self.bind(size=self.resize)

    def action_names(self, column):
        col_type = self.columns[ column ]
        return self.column_kind_map[ col_type ]

    def column_names(self):
        return sorted(self.columns.keys())

    def resize(self, *args):
        self.vbox.size = self.size

    def newTerm(self):
        #term = Button(text='artist')

        term = QueryTerm(self,self.default_column)
        print("add", id(term))
        self.vbox.add_widget( term)


