

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.logger import Logger

from yue.settings import Settings
from yue.sound import SoundManager

class NowPlayingScreen(Screen):
    def __init__(self,**kwargs):
        super(NowPlayingScreen,self).__init__(**kwargs)

        row_height = Settings.instance().row_height()
        self.vbox = BoxLayout(orientation='vertical')
        self.hbox = BoxLayout(orientation='horizontal')
        self.hbox.size_hint=(1.0,None)
        self.hbox.height=row_height

        self.btn_home = Button(text="home")
        self.btn_home.size_hint = (1.0,None)
        self.btn_home.height = row_height
        self.btn_home.bind(on_press=Settings.instance().go_home)
        self.btn_nowplaying = Button(text="Current Playlist")
        self.btn_nowplaying.size_hint = (1.0,None)
        self.btn_nowplaying.height = row_height
        self.btn_nowplaying.bind(on_press=Settings.instance().go_current_playlist)
        self.hbox.add_widget(self.btn_home)
        self.hbox.add_widget(self.btn_nowplaying)

        self.btn_playpause = Button(text="play/pause")
        self.btn_playpause.bind(on_press=(lambda *x : SoundManager.instance().playpause()))

        self.btn_next = Button(text="next")
        self.btn_next.bind(on_press=(lambda *x : SoundManager.instance().next()))

        self.btn_prev = Button(text="prev")
        self.btn_prev.bind(on_press=(lambda *x : SoundManager.instance().prev()))

        self.btn_test = Button(text="jump to end")
        self.btn_test.bind(on_press=self.jump_to_end)


        self.add_widget( self.vbox )
        self.vbox.add_widget( self.hbox )
        self.vbox.add_widget( self.btn_playpause )
        self.vbox.add_widget( self.btn_next )
        self.vbox.add_widget( self.btn_prev )
        self.vbox.add_widget( self.btn_test )

    def jump_to_end(self,*args):

        sm = SoundManager.instance()
        t = sm.duration() - 2.0
        Logger.info("> jump to %d/%d"%(t,sm.duration()))
        sm.seek( t )

