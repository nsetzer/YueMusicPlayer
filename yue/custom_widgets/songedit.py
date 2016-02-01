from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.properties import NumericProperty,BooleanProperty
from kivy.graphics import Color, Rectangle, Line
from kivy.uix.boxlayout import BoxLayout

from kivy.uix.gridlayout import GridLayout

class SongEdit(GridLayout):


    def __init__(self, song, spacing=1, **kwargs):
        # size_hint_y=None,
        super(SongEdit, self).__init__(cols=2, spacing=spacing, **kwargs)

        self.song = song

        for k,v in sorted(song.items()):
            self.add_widget( Label(text=unicode(k)))
            self.add_widget( Label(text=unicode(v)))

        self.bind(pos=self.resize)
        self.bind(size=self.resize)

    def resize(self,*args):
        pass
