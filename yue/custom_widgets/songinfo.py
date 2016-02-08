#! python2.7 ../../test/test_widget.py songinfo


from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.core.text import Label as CoreLabel

from kivy.uix.scrollview import ScrollView

from yue.custom_widgets.songedit import SongEdit


class SongInfo(Widget):
    """
    action_label : text for a button that is displayed above song info
    """

    def __init__(self, song, action_label=None, font_size=12, row_height=0, **kwargs):
        self.register_event_type('on_accept')
        self.register_event_type('on_reject')
        self.register_event_type('on_action')
        super(SongInfo, self).__init__(**kwargs)

        self.song = song

        lblheight = CoreLabel(font_size=font_size).get_extents("_")[1]
        if row_height < lblheight:
            row_height = 3*lblheight
        self.row_height = row_height

        self.songedit = SongEdit( song , row_height = lblheight)

        self.vbox = BoxLayout(orientation='vertical')
        self.hbox = BoxLayout(orientation='horizontal')

        #self.scrollview = ScrollView(size_hint=(1.0, 1.0))
        #self.scrollview.add_widget( self.songedit )

        btn= Button(text='cancel')
        btn.bind(on_press=lambda *x : self.dispatch('on_reject'))
        self.hbox.add_widget(btn)
        btn= Button(text='accept')
        btn.bind(on_press=lambda *x : self.dispatch('on_accept'))
        self.hbox.add_widget(btn)

        self.hbox.size_hint = (1.0,None)
        self.hbox.height = self.row_height

        if action_label is not None:
            btn = Button(text=action_label)
            btn.size_hint = (1.0,None)
            btn.bind(on_press=lambda *x : self.dispatch('on_action'))
            btn.height = self.row_height
            self.vbox.add_widget(btn)

        self.vbox.add_widget(self.songedit)
        self.vbox.add_widget(self.hbox)

        self.add_widget(self.vbox)

        self.bind(pos=self.resize)
        self.bind(size=self.resize)

    def resize(self,*args):

        self.vbox.pos = self.pos
        self.vbox.size = self.size

    def on_accept(self,*args):
        pass

    def on_reject(self,*args):
        pass

    def on_action(self,*args):
        pass