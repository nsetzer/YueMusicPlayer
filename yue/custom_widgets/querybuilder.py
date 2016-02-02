#! python2.7 ../../test/test_widget.py query
"""

TODO:
    eventually allow a more advanced search option for creating groups.
    e.g. (x or y or z) and w
    i just don't know how to visualize this yet, possibly internal visual
    spacer widgets in the vbox. use a push/pop stack method for translating
    a linear list into a nested tree.

    remove the 'new button' from the query builder widget
    change the widget into a scroll view,
    provide a set height method which sets the height in terms of
    number of visible rows.

"""
from kivy.uix.widget import Widget
from kivy.uix.button import Button

##########################
# get the font_height in pixels for a given dont size
from kivy.core.text import Label as CoreLabel
#CoreLabel().get_extents("x")
##########################
from kivy.logger import Logger
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
import re
from enum import Enum

class QueryKind(Enum):
    LIKE   =1 # partial match
    NOTLIKE=2 # partial match
    EQ=3   # exact match
    NE=4   # not equal
    LT=5   # less than
    LE=6   # less than or equal
    GT=7   # greater than
    GE=8   # greater than or equal
    BETWEEN=9
    NOTBETWEEN=10
    AND=11
    OR=12

class FilterTextInput(TextInput):

    numeric_ptn = re.compile('[^0-9]')
    def insert_text(self, substring, from_undo=False):
        if self.input_type == 'number':
            s = re.sub(self.numeric_ptn, '', substring)
        else:
            s = substring
        return super(FilterTextInput, self).insert_text(s, from_undo=from_undo)

class QueryTerm(Widget):
    """
    editor for a single part of a query.

    enables changing parameters of the query.
    """
    def __init__(self, builder, column, font_size=12, height = 0):
        super(QueryTerm, self).__init__()

        self.builder = builder
        self.column = column
        self.action, actionlabel= self.builder.default_column_action( column )

        # TODO: this is not quite correct
        # TODO: there is a bug in kivy/uix/boxlayout.py
        # when we do_layout() for a layout containing fixed widgets
        # it sometimes draws incorrectly.
        self.size_hint = (1.0,None)

        self.cached_height = height
        if height == 0:
            self.cached_height =  3 * CoreLabel().get_extents("_")[1]
        self.height = self.cached_height

        self.hbox = BoxLayout(orientation='horizontal')
        self.add_widget(self.hbox)

        self.btn_remove = Button(text="X" )
        self.btn_remove.bind( on_press=self.remove)
        self.btn_remove.size_hint = (None,None)
        self.btn_remove.size = (self.height,self.height)

        self.btn_select_action = Button(text=actionlabel )
        self.btn_select_action.bind( on_press=self.select_action)
        self.btn_select_action.size_hint = (None,None)
        self.btn_select_action.size = (self.height,self.height)

        self.btn_select_column = Button(text=column)
        self.btn_select_column.bind( on_press=self.select_column)
        self.btn_select_column.size_hint = (0.5,1.0)

        self.txt_main      = FilterTextInput(multiline=False)
        self.lbl_range     = Label(text="to")
        self.txt_secondary = FilterTextInput(multiline=False)

        self.hbox.add_widget(self.btn_remove)
        self.hbox.add_widget(self.btn_select_column)
        self.hbox.add_widget(self.btn_select_action)
        self.hbox.add_widget(self.txt_main)
        # self.txt.input_type = 'number' or 'text'

        self.bind(size=self.resize)
        self.bind(pos=self.resize)

    def toQuery(self):
        value = (self.txt_main.text,)
        if self.action in [QueryKind.BETWEEN,QueryKind.NOTBETWEEN]:
            value = (self.txt_main.text,self.txt_secondary.text )
        typ = self.builder.columns[ self.column ]
        try:
            if typ != str:
                value = map(typ,value)
        except ValueError as e:
            Logger.warning("%s"%e)
        return self.column, self.action, value

    def remove(self,*args):
        self.builder.remove(self)

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
        self.btn_select_action.text = self.builder.kind_map[new_action]

        self.action = new_action

        if new_action in [QueryKind.BETWEEN,QueryKind.NOTBETWEEN]:
            if self.lbl_range.parent is None:
                self.hbox.add_widget( self.lbl_range )
                self.hbox.add_widget( self.txt_secondary )
        else:
            if self.lbl_range.parent is not None:
                self.hbox.remove_widget( self.lbl_range )
                self.hbox.remove_widget( self.txt_secondary )

        if self.popup is not None:
            self.popup.dismiss()
            self.popup = None

    def change_column(self, new_column):
        self.btn_select_column.text = new_column

        action, lbl = self.builder.default_column_action( new_column )
        self.btn_select_action.text = lbl

        new_type=self.builder.columns[ new_column ]
        if self.builder.columns[ self.column ] != new_type:
            self.txt_main.text= str(new_type())
            self.txt_secondary.text= str(new_type())

        if new_type == str:
            self.txt_main.input_type = 'text'
            self.txt_main.input_type = 'text'
        elif new_type == int:
            self.txt_main.input_type = 'number'
            self.txt_main.input_type = 'number'

        self.column = new_column

        self.change_action( action )

    def resize(self, *args):
        self.hbox.size = self.size
        self.hbox.pos = self.pos

class ActionSelector(GridLayout):
    """
    display a grid view of possible search actions,
        e.g. exact or partial match, or lt, gt, etc
    """
    def __init__(self, actions, accept = None, **kwargs):
        super(ActionSelector,self).__init__(cols=4, **kwargs)

        self.accept = accept

        for action, label in actions:
            btn = Button(text=label)
            btn.action_kind = action
            btn.bind(on_press=self.select)
            self.add_widget( btn )

    def select( self, btn, *args):
        if self.accept is not None:
            self.accept( btn.action_kind )

class ColumnSelector(GridLayout):

    """
    display a grid view of possible search fields, columns in the db
    """
    def __init__(self, actions, accept = None, **kwargs):
        super(ColumnSelector,self).__init__(cols=3, **kwargs)

        self.accept = accept

        for action in actions:
            btn = Button(text=action)
            btn.bind(on_press=self.select)
            self.add_widget( btn )

    def select( self, btn, *args):
        if self.accept is not None:
            self.accept( btn.text )

class QueryBuilder(GridLayout):

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

    kind_map should map a query kind to either an icon or string.

    """
    def __init__(self, columns , kind_map, default_column=None, row_height=0, spacing=1, font_size=12 ):
        self.register_event_type('on_children_change')
        super(QueryBuilder, self).__init__(cols=1, spacing=spacing, size_hint_y=None )
        self.bind(minimum_height=self.setter('height'))

        self.columns = columns
        self.default_column = default_column
        self.font_size = font_size

        lblheight = CoreLabel(font_size=font_size).get_extents("_")[1]
        if row_height < lblheight:
            row_height = 3 * lblheight
        self.row_height = row_height

        # by convention, first value in the kind map is the default for that type
        self.column_kind_map = {
            # these type keys must be callables
            #   with no arguments return a suitable default value
            #   with one argument convert a string into type.
            str : [QueryKind.LIKE, QueryKind.NOTLIKE, QueryKind.EQ, QueryKind.NE],
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
        self.kind_map = kind_map

        self.widget_count = 0

        self.bind(size=self.resize)
        self.bind(pos=self.resize)

    def on_children_change(self,*args):
        pass

    def remove(self, child):

        self.remove_widget( child )
        self.dispatch('on_children_change', len(self.children))

    def action_names(self, column):
        col_type = self.columns[ column ]

        actions = self.column_kind_map[ col_type ]
        labels = [ self.kind_map[a] for a in actions ]
        return zip(actions,labels)

    def column_names(self):
        return sorted(self.columns.keys())

    def default_column_action(self,column):
        col_type = self.columns[ column ]
        acts = self.column_kind_map[ col_type ]
        return acts[0], self.kind_map[acts[0]]

    def resize(self, *args):
        #self.vbox.size = self.size
        #self.vbox.pos = self.pos
        pass

    def newTerm(self):
        col = self.default_column
        if col is None: # pick one at random
            col = list(self.columns.keys())[0]
        term = QueryTerm(self,col,font_size=self.font_size, height=self.row_height)
        self.add_widget( term )
        self.dispatch('on_children_change', len(self.children) )


    def toQuery(self):
        """
        return a (potentially nested) list of query parameters
        each will be formatted as a 3-tuple
            (column, QueryKind, values)
        depending on the query kind values will be tuple of either
            1 or 2 values.
        """
        query = []
        for t in self.children:
            query.append( t.toQuery() )
        return query


