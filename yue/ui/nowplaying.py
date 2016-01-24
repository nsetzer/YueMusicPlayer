
import os
import traceback

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image, AsyncImage
from kivy.logger import Logger
from kivy.clock import mainthread

from yue.custom_widgets.timebar import TimeBar
from yue.settings import Settings
from yue.playlist import PlaylistManager
from yue.sound.manager import SoundManager
from yue.sound.device import MediaState
from yue.song import ArtNotFound, get_album_art

class NowPlayingScreen(Screen):
    def __init__(self,**kwargs):
        super(NowPlayingScreen,self).__init__(**kwargs)

        self.current_song = { 'uid': -1}

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

        self.lbl_title = Label()
        self.lbl_title.size_hint=(1.0,None)
        self.lbl_title.height=row_height
        self.lbl_artist = Label()
        self.lbl_artist.size_hint=(1.0,None)
        self.lbl_artist.height=row_height
        self.lbl_index = Label()
        self.lbl_index.size_hint=(1.0,None)
        self.lbl_index.height=row_height

        self.img_albumart = AsyncImage();

        self.btn_playpause = Button(text="play")
        self.btn_playpause.bind(on_press=(lambda *x : SoundManager.instance().playpause()))

        self.btn_next = Button(text="next")
        self.btn_next.bind(on_press=(lambda *x : SoundManager.instance().next()))

        self.btn_prev = Button(text="prev")
        self.btn_prev.bind(on_press=(lambda *x : SoundManager.instance().prev()))

        self.timebar = TimeBar()

        self.hbox_btns.add_widget( self.btn_prev )
        self.hbox_btns.add_widget( self.btn_playpause )
        self.hbox_btns.add_widget( self.btn_next )

        self.add_widget( self.vbox )
        self.vbox.add_widget( self.hbox )
        self.vbox.add_widget( self.lbl_title )
        self.vbox.add_widget( self.lbl_artist )
        self.vbox.add_widget( self.lbl_index ) # for lack of a better place for now
        self.vbox.add_widget( self.img_albumart )
        self.vbox.add_widget( self.hbox_btns )
        self.vbox.add_widget( self.timebar )

        self.timebar.bind(on_seek=self.change_position)
        SoundManager.instance().bind(on_load=self.update)
        SoundManager.instance().bind(on_song_tick=self.on_tick)


    def on_tick(self,position,duration):
        self.timebar.value = position
        self.timebar.duration = duration

    @mainthread
    def update(self, obj, song):

        if song['uid'] != self.current_song['uid']:
            self.current_song = song
            self.timebar.value = 0
            #self.timebar.duration = SoundManager.instance().duration()
            self.update_albumart(song)
            self.lbl_title.text = song['title']
            self.lbl_artist.text = song['artist']
            pl = PlaylistManager.instance().openPlaylist('current')
            idx,_ = pl.current()
            sz = pl.size()
            self.lbl_index.text = "%d/%d"%(idx+1,sz)



    @mainthread
    def update_statechange(self, obj, state):
        print(state, state==MediaState.play,state==MediaState.pause)

        if state==MediaState.play:
            self.btn_playpause.text="pause"
        else:
            self.btn_playpause.text="play"

    def update_albumart(self,song):
         # TODO this needs to be done async
        try:
            default_path = os.path.join(Settings.instance().platform_path,"cover.jpg")
            art_path = get_album_art(song['path'],default_path)
            self.img_albumart.source = art_path

            Logger.info("nowplaying: found art: %s"%art_path)
            print("exists",os.path.exists(art_path))

        except ArtNotFound as e:
            Logger.warning("nowplaying: no art found for %s"%song['path'])
            self.img_albumart.source = Settings.instance().img_noart_path
        except Exception as e:
            self.img_albumart.source = ""
            Logger.error("nowplaying: unable to load art for %s"%song['path'])
            traceback.print_exc()

    def change_position(self,obj,position):

        SoundManager.instance().seek( position )