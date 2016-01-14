#! python2.7 $this lib

"""

usage:
    python2.7 test_sound.py <path to media file>
"""
import os,sys


dirpath = os.path.dirname(os.path.abspath(__file__))
dirpath = os.path.dirname(dirpath)
sys.path.insert(0,dirpath)

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition

from yue.library import Library
from yue.ui.library import LibraryScreen
from yue.settings import Settings

def build_library(sm):

    Library.test_init()
    data = Library.instance().toTree()

    ls = LibraryScreen(name='Library')
    ls.setLibraryTree(data)
    sm.add_widget( ls )


class TestApp(App):

    def build(self):

        ptn = "none"
        if len(sys.argv)>1:
            ptn = sys.argv[1].lower() # TODO use as regex
            widgets = {
                'library' : build_library,
            }

            Settings.init()

            sm = ScreenManager(transition=FadeTransition())
            Settings.instance().manager = sm

            for name,func in widgets.items():
                if name.startswith(ptn):
                    func(sm)
                    return sm

        raise ValueError("invalid pattern: %s"%ptn)

def main():

    TestApp().run()

if __name__ == '__main__':
    main()