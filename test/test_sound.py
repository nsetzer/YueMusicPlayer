#! python2.7 $this ./top.wav

"""

usage:
    python2.7 test_sound.py <path to media file>
"""
import os,sys

dirpath = os.path.dirname(os.path.abspath(__file__))
dirpath = os.path.dirname(dirpath)
sys.path.append(dirpath)

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.button import Button

from yue.sound import SoundManager

class SoundWidget(Widget):

    def __init__(self, **kwargs):
        super(SoundWidget, self).__init__(**kwargs)

        self.btn1 = Button(text="play/pause")
        self.add_widget(self.btn1)
        self.btn1.bind(on_press=self.playpause)

    def on_test(self,*args):
        print(args)

    def playpause(self,*args):

        SoundManager.instance().playpause()

if __name__ == '__main__':

    class TestApp(App):

        def build(self):

            path = None
            if len(sys.argv)>1:
                path = sys.argv[1]

            if path is None or not os.path.exists(path):
                raise RuntimeError("file: %s"%path)

            SoundManager.init()
            SoundManager.instance().load(path)

            return SoundWidget()

    TestApp().run()
