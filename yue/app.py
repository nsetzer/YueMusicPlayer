#! cd .. && python2.7 main.py --size=480x640

"""

todo:
    https://kivy.org/docs/api-kivy.app.html
    see built in support for settings,

    Pause Mode
"""

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from kivy.logger import Logger
from kivy.lib import osc
from kivy.clock import Clock
from kivy.core.window import Window, Keyboard

from yue.ui.library import LibraryScreen
from yue.ui.home import HomeScreen
from yue.ui.nowplaying import NowPlayingScreen
from yue.ui.current import CurrentPlaylistScreen
from yue.ui.preset import PresetScreen, ModifyPresetScreen
from yue.ui.ingest import IngestScreen
from yue.ui.settings import SettingsScreen
from yue.ui.util import libraryToTree, PlayListToViewList

from yue.core.playlist import PlaylistManager
from yue.core.library import Library
from yue.settings import Settings
from yue.sound.manager import SoundManager
from yue.sound.clientdevice import ServiceInfo
from yue.core.sqlstore import SQLStore

import os,sys
from subprocess import Popen
from threading import Thread
import time

serviceport = 15123 # Todo select these at run time
activityport = 15124

class BackgroundDataLoad(Thread):
    def __init__(self):
        super(BackgroundDataLoad,self).__init__()

    def run(self):

        Logger.info("data: starting background load thread")

        settings = Settings.instance()
        # somewhat annoying, but I need a unique library per thread

        sqlstore = SQLStore(settings.db_path)
        library = Library( sqlstore )
        plmgr = PlaylistManager( sqlstore )
        plcur = plmgr.openPlaylist( 'current' )

        scr_lib = settings.manager.get_screen( settings.screen_library )
        scr_cur = settings.manager.get_screen( settings.screen_current_playlist )

        # simulate taking a long time to load:
        #n=20
        #for i in range(n):
        #    msg = "please wait... %%%d"%(100*i/(n-1))
        #    scr_cur.setPlaceholderText( msg )
        #    scr_lib.setPlaceholderText( msg )
        #    time.sleep(.25)

        # load a test library into the database
        Logger.warning(" load test data ")
        library.loadTestData( os.path.join( \
            Settings.instance().platform_path,"library.ini") );

        tree = libraryToTree( library )
        # build a dummy playlist until it can be stored in the db
        lst = []
        g = library.iter()
        try:
            for i in range(20):
                song = next(g)
                lst.append(song['uid'])
        except StopIteration:
            pass

        if len(lst):
            viewlst = PlayListToViewList( library, lst )
            plcur.set( lst )
            idx,key = plcur.current()
            song = library.songFromId( key )
            SoundManager.instance().load( song )
            scr_cur.setPlayList( viewlst )

        scr_lib.setLibraryTree( tree )

        Logger.info("data: background load thread finished")

class YueApp(App):
    title = "Yue Music Player"
    icon = "./img/icon.png"

    def __init__(self,**kwargs):
        super(YueApp,self).__init__(**kwargs)
        self.bg_thread = None
        self.pid = None # popen service reference
        self.service = None # android service reference

    def start_service(self):

        if Settings.instance().platform == 'android':
            Logger.info("service: Creating Android Service")
            from android import AndroidService
            service = AndroidService('Yue Service', 'running')
            service.start('service started')
            self.service = service
        else:
            Logger.info("service: Creating Android Service as Secondary Process")
            self.pid = Popen([sys.executable, "service/main.py"])

        hostname = '127.0.0.1'
        osc.init()
        oscid = osc.listen(ipAddr=hostname, port=activityport)

        Clock.schedule_interval(lambda *x: osc.readQueue(oscid), 0)

        time.sleep(.5)

        return ServiceInfo(oscid,hostname,activityport,serviceport)

    def stop_service(self):
        # note: not a kivy function, is not called automatically
        # on windows, child processs is stopped when the shell
        # exits.
        if self.pid is not None:
            Logger.info("Yue: stopping popen service")
            self.pid.kill()
        if self.service is not None:
            Logger.info("Yue: stopping android service")
            self.service.stop()
            self.service = None

    def on_song_tick(self,p,d):

        settings = Settings.instance()
        scr = settings.manager.get_screen( settings.screen_now_playing )
        scr.on_tick(None, p,d)

    def on_state_changed(self,idx,uid,state):

        Logger.info("now playing: state changed idx:%d uid:%d state:%d"%(idx,uid,state))
        song = Library.instance().songFromId(uid)
        settings = Settings.instance()
        scr = settings.manager.get_screen( settings.screen_now_playing )
        scr.update( None, song )
        scr.update_statechange( None, state )

        scr = settings.manager.get_screen( settings.screen_current_playlist )
        scr.view.setHighlight(idx)

    def ingest_update(self,message,*args):

        settings = Settings.instance()
        scr = settings.manager.get_screen( settings.screen_ingest )
        scr.update_labels(*message[2:])

    def ingest_finished(self,message,*args):

        Logger.info("ingest: signal finished received.")
        settings = Settings.instance()
        scr = settings.manager.get_screen( settings.screen_library )
        sqlstore = SQLStore(settings.db_path)
        library = Library( sqlstore )
        scr.setLibraryTree( libraryToTree( library ) )

        Logger.info("ingest: updated tree")

        scr = settings.manager.get_screen( settings.screen_ingest )
        scr.ingest_finished()


    def build(self):

        # create the screen manager and application screens
        sm = ScreenManager(transition=FadeTransition())

        # init controller objects
        Settings.init( sm )
        Library.init( Settings.instance().sqldb )
        PlaylistManager.init( Settings.instance().sqldb )

        info = self.start_service()

        Settings.service_info = info

        SoundManager.init( Settings.instance().platform_libpath, info = info )

        hm_scr = HomeScreen(name=Settings.instance().screen_home)
        np_scr = NowPlayingScreen(name=Settings.instance().screen_now_playing)
        cu_scr = CurrentPlaylistScreen(name=Settings.instance().screen_current_playlist)
        lb_scr = LibraryScreen(name=Settings.instance().screen_library)
        pr_scr = PresetScreen(name=Settings.instance().screen_presets)
        mp_scr = ModifyPresetScreen(name=Settings.instance().screen_modify_preset)
        in_scr = IngestScreen(name=Settings.instance().screen_ingest)
        se_scr = SettingsScreen(name=Settings.instance().screen_settings)

        osc.bind(info.oscid, lambda m,*a: self.on_song_tick(m[2],m[3]) , '/song_tick')
        osc.bind(info.oscid, lambda m,*a: self.on_state_changed(*m[2:]) , '/song_state')
        osc.bind(info.oscid, self.ingest_update , '/ingest_update')
        osc.bind(info.oscid, self.ingest_finished , '/ingest_finished')

        sm.add_widget(hm_scr)
        sm.add_widget(cu_scr)
        sm.add_widget(np_scr)
        sm.add_widget(lb_scr)
        sm.add_widget(pr_scr)
        sm.add_widget(mp_scr)
        sm.add_widget(in_scr)
        sm.add_widget(se_scr)

        # initialize data to be displayed

        self.bg_thread = BackgroundDataLoad()
        self.bg_thread.start()

        self.bind(on_start=self.post_build_init)

        return sm

    def post_build_init(self, *args):
        if Settings.instance().platform == 'android':
            import android
            android.map_key(android.KEYCODE_BACK, Keyboard.keycodes['escape'])

        Window.bind(on_keyboard=self.on_key_event)

    def on_key_event(self, window, keycode1, keycode2, text, modifiers):
        if keycode1 in [Keyboard.keycodes['escape'], ]:
            return Settings.instance().go_back()
        return False


    def on_pause(self):
        return True # prevent on_stop when in background

    def on_resume(self):
        pass # not guaranteed after an on_pause

    def on_start(self):
        Logger.info('Yue: start')

    def on_stop(self):
        # TODO save current playlist to settings db

        Logger.info('Yue: on exit joining threads')

        self.stop_service()

        if self.bg_thread is not None:
            #TODO: send kill msg
            self.bg_thread.join()

        Logger.critical('Yue: exit')

def main():
    YueApp().run()
