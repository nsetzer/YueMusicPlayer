
import traceback

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.logger import Logger

from yue.settings import Settings
from yue.sound import SoundManager
from yue.song import ArtNotFound, get_album_art

class NowPlayingScreen(Screen):
    def __init__(self,**kwargs):
        super(NowPlayingScreen,self).__init__(**kwargs)

        row_height = Settings.instance().row_height()
        self.vbox = BoxLayout(orientation='vertical')

        self.hbox_btns = BoxLayout(orientation='horizontal')
        self.hbox_btns.size_hint=(1.0,None)
        self.hbox_btns.height=row_height

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

        self.img_albumart = Image();

        self.btn_playpause = Button(text="play/pause")
        self.btn_playpause.bind(on_press=(lambda *x : SoundManager.instance().playpause()))

        self.btn_next = Button(text="next")
        self.btn_next.bind(on_press=(lambda *x : SoundManager.instance().next()))

        self.btn_prev = Button(text="prev")
        self.btn_prev.bind(on_press=(lambda *x : SoundManager.instance().prev()))

        self.btn_test = Button(text="jump to end")
        self.btn_test.bind(on_press=self.jump_to_end)

        self.hbox_btns.add_widget( self.btn_prev )
        self.hbox_btns.add_widget( self.btn_playpause )
        self.hbox_btns.add_widget( self.btn_next )

        self.add_widget( self.vbox )
        self.vbox.add_widget( self.hbox )
        self.vbox.add_widget( self.img_albumart )
        self.vbox.add_widget( self.hbox_btns )

        self.vbox.add_widget( self.btn_test )

        SoundManager.instance().bind(on_load=self.update_albumart)

    def jump_to_end(self,*args):

        sm = SoundManager.instance()
        t = sm.duration() - 2.0
        Logger.info("> jump to %d/%d"%(t,sm.duration()))
        sm.seek( t )

    def update_albumart(self,obj,song):
         # TODO this needs to be done async
        try:
            art_path = get_album_art(song['path'],"./cover.jpg")
            self.img_albumart.source = art_path
            Logger.info("nowplaying: found art")

        except ArtNotFound as e:
            Logger.warning("nowplaying: no art found for %s"%song['path'])
            self.img_albumart.source = ""
        except Exception as e:
            self.img_albumart.source = ""
            Logger.error("nowplaying: unable to load art for %s"%song['path'])
            traceback.print_exc()


