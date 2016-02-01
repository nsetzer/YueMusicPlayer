from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.properties import NumericProperty,BooleanProperty
from kivy.graphics import Color, Rectangle, Line
from kivy.uix.boxlayout import BoxLayout

from kivy.uix.gridlayout import GridLayout

class SongEdit(GridLayout):


    def __init__(self, song, spacing=1, **kwargs):
        super(SongEdit, self).__init__(cols=2, spacing=spacing,size_hint_y=None, **kwargs)

        self.song = song

        self.add_widget(Label(text="boo"))
        self.add_widget(Label(text="boo"))
        self.add_widget(Label(text="boo"))

        self.bind(pos=self.resize)
        self.bind(size=self.resize)

    def resize(self,*args):

        pass
        #self.vbox.pos = self.pos
        #self.vbox.size = self.size

    def on_accept(self,*args):
        pass

    def on_reject(self,*args):
        pass