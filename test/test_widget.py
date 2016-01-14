#! python2.7 $this tree
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
sys.path.append(dirpath)

from kivy.app import App

from yue.custom_widgets.expander import Expander
from yue.custom_widgets.view import TreeViewWidget, ListViewWidget, TreeElem, ListElem
from yue.custom_widgets.tristate import TriStateCheckBox

def build_expander():
    return Expander()

def build_tristatecheckbox():
    return TriStateCheckBox()

def build_treeview():
    art1 = TreeElem("Artist-1")
    alb = art1.addChild( TreeElem("Album-1") )
    alb.addChild(TreeElem("Title-1-1"))
    alb.addChild(TreeElem("Title-1-2"))
    alb.addChild(TreeElem("Title-1-3"))
    alb.addChild(TreeElem("Title-1-4"))
    alb.addChild(TreeElem("Title-1-5"))
    alb = art1.addChild( TreeElem("Album-2") )
    alb.addChild(TreeElem("Title-2-1"))
    alb.addChild(TreeElem("Title-2-2"))
    alb.addChild(TreeElem("Title-2-3"))
    alb.addChild(TreeElem("Title-2-4"))
    alb.addChild(TreeElem("Title-2-5"))
    art2 = TreeElem("Artist-2")
    temp = art2.addChild( TreeElem("Album-3") )
    temp.addChild(TreeElem("Title-3-1"))
    temp.addChild(TreeElem("Title-3-2"))
    temp.addChild(TreeElem("Title-3-3"))
    temp.addChild(TreeElem("Title-3-4"))
    temp.addChild(TreeElem("Title-3-5"))
    data = [ art1, art2 ]

    return TreeViewWidget( data, font_size=16 )

def build_listview():
        data = [
            ListElem("item-1"),
            ListElem("item-2"),
            ListElem("item-3"),
            ListElem("item-4"),
            ListElem("item-5"),
        ]
        return ListViewWidget( data, font_size=16 )

class TestApp(App):

    def build(self):

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