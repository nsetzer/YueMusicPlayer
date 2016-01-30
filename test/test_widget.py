#! python2.7 $this scroll
import os,sys

"""
run a test app with a single widget, for testing that widget

Example:
    execute:
        python2.7 test_widget.py tri

        to run an application containing the TriStateCheckBox widget.

"""
dirpath = os.path.dirname(os.path.abspath(__file__))
dirpath = os.path.dirname(dirpath)
sys.path.insert(0,dirpath)

print(dirpath)

import yue
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from yue.custom_widgets.expander import Expander
from yue.custom_widgets.view import TreeViewWidget, ListViewWidget, TreeElem, ListElem
from yue.custom_widgets.tristate import TriStateCheckBox
from yue.custom_widgets.playlist import PlayListElem, PlayListViewWidget
from yue.custom_widgets.timebar import TimeBar
from yue.custom_widgets.querybuilder import QueryBuilder, QueryKind
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from yue.library import Library
from yue.settings import Settings

from kivy.app import App
from kivy.core.text import LabelBase

def build_expander():
    return Expander()

def build_tristatecheckbox():
    return TriStateCheckBox()

def build_timebar():
    return TimeBar()

def build_treeview():

    Settings.init( "./yue.db" )
    Library.init()
    data = Library.instance().toTree()

    view = TreeViewWidget( font_size=16 )
    view.setData(data)
    return view

def build_listview():
    data = [
        ListElem("item-1"),
        ListElem("item-2"),
        ListElem("item-3"),
        ListElem("item-4"),
        ListElem("item-5"),
    ]
    view = ListViewWidget( font_size=16 )
    view.setData(data)
    return view

def build_playlistview():
    data = [
        PlayListElem(0,{"artist":"Art1","title":"item-1","length":123}),
        PlayListElem(1,{"artist":"Art1","title":"item-2","length":60 }),
        PlayListElem(2,{"artist":"Art1","title":"item-3","length":400}),
        PlayListElem(3,{"artist":"Art1","title":"item-4","length":123}),
        PlayListElem(4,{"artist":"Art1","title":"item-5","length":123}),
    ]
    view = PlayListViewWidget( font_size=16 )
    view.setData(data)
    view.setHighlight(3)
    return view

def build_querybuilder():

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

    vbox = BoxLayout(orientation='vertical')
    view = QueryBuilder( columns, kind_map, default_column = 'all-text' )
    view.newTerm()

    root = ScrollView(size_hint=(1.0, 1.0))
    root.add_widget( view )
    vbox.add_widget( root )


    btn = Button(text="new term")
    btn.bind(on_press=lambda *x: view.newTerm())
    vbox.add_widget( btn )

    btn = Button(text="print query")
    btn.bind(on_press=lambda *x: sys.stdout.write( "%s\n\n"%view.toQuery()))
    vbox.add_widget( btn )
    return vbox

def build_scroll():
    layout = GridLayout(cols=1, spacing=10, size_hint_y=None)
    # Make sure the height is such that there is something to scroll.
    layout.bind(minimum_height=layout.setter('height'))
    for i in range(30):
        btn = Button(text=str(i), size_hint_y=None, height=40)
        layout.add_widget(btn)
    root = ScrollView(size_hint=(1.0, 1.0))
    root.add_widget(layout)


    return root



class TestApp(App):

    def build(self):

        font = r"C:\Users\Nick\Documents\GitHub\YueMusicPlayer\DroidSansJapanese.ttf"
        if os.path.exists(font):
            LabelBase.register("DroidSansJapanese",font)

        ptn = "none"
        if len(sys.argv)>1:
            ptn = sys.argv[1].lower() # TODO use as regex
            widgets = {
                'treeview' : build_treeview,
                'listview' : build_listview,
                'playlistview' : build_playlistview,
                'expander' : build_expander,
                'time' : build_timebar,
                'tristatecheckbox' : build_tristatecheckbox,
                'querybuilder' : build_querybuilder,
                'scroll' : build_scroll,
            }

            for name,func in widgets.items():
                if name.startswith(ptn):
                    return func()

        raise ValueError("invalid pattern: %s"%ptn)

def main():

    TestApp().run()

if __name__ == '__main__':
    main()