#! python2.7 $this list
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
from yue.custom_widgets.expander import Expander
from yue.custom_widgets.view import TreeViewWidget, ListViewWidget, TreeElem, ListElem
from yue.custom_widgets.tristate import TriStateCheckBox
from yue.library import Library

from kivy.app import App
from kivy.core.text import LabelBase

def build_expander():
    return Expander()

def build_tristatecheckbox():
    return TriStateCheckBox()

def build_treeview():

    Library.test_init()
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
                'expander' : build_expander,
                'tristatecheckbox' : build_tristatecheckbox,
            }

            for name,func in widgets.items():
                if name.startswith(ptn):
                    return func()

        raise ValueError("invalid pattern: %s"%ptn)

def main():

    TestApp().run()

if __name__ == '__main__':
    main()