from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.properties import NumericProperty,BooleanProperty
from kivy.graphics import Color, Rectangle, Line
from kivy.uix.boxlayout import BoxLayout

from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout

from yue.custom_widgets.songedit import SongEdit


class SongInfo(Widget):

    def __init__(self, song, **kwargs):
        super(SongInfo, self).__init__(**kwargs)

        self.song = song

        self.songedit = SongEdit( song )

        self.vbox = BoxLayout(orientation='vertical')

        self.scrollview = ScrollView(size_hint=(1.0, None))
        self.scrollview.add_widget( self.songedit )

        self.add_widget(self.vbox)
        self.vbox.add_widget(Button(text='playnext'))
        self.vbox.add_widget(self.scrollview)
        self.vbox.add_widget(Button(text='cancel'))
        self.vbox.add_widget(Button(text='accept'))

        self.bind(pos=self.resize)
        self.bind(size=self.resize)

        self.register_event_type('on_accept')
        self.register_event_type('on_reject')

    def resize(self,*args):

        self.vbox.pos = self.pos
        self.vbox.size = self.size

    def on_accept(self,*args):
        pass

    def on_reject(self,*args):
        pass