
import os,sys
import time
from threading import Thread, Condition
import Queue

from kivy.lib import osc
from kivy.logger import Logger

from yue.sound.manager import SoundManager
from yue.sound.device import MediaState
from yue.sound.pybass import get_platform_path
from yue.library import Library
from yue.playlist import PlaylistManager
from yue.sqlstore import SQLStore, SQLView

from yue.server.ingest import Ingest

serviceport = 15123
activityport = 15124



class YueServer(object):
    """docstring for YueServer"""
    # https://docs.python.org/2/library/queue.html
    # https://docs.python.org/2/library/threading.html#condition-objects
    def __init__(self, app_path):
        super(YueServer, self).__init__()

        osc.init()
        self.oscid = osc.listen(ipAddr='127.0.0.1', port=serviceport)
        osc.bind(self.oscid, self.audio_action_callback, '/audio_action')
        osc.bind(self.oscid, self.ingest_start, '/ingest_start')

        self.db_path = os.path.join(app_path,"yue.db")
        self.sqlstore = SQLStore( self.db_path )
        Library.init( self.sqlstore )
        PlaylistManager.init( self.sqlstore )
        libpath = get_platform_path()
        SoundManager.init( libpath )

        SoundManager.instance().bind(on_state_changed=self.on_state_change)
        SoundManager.instance().bind(on_song_end=self.on_song_end_event)
        SoundManager.instance().bind(on_playlist_end=self.on_playlist_end)

        self.event_queue = Queue.Queue()
        self.cv_wait = Condition()
        self.cv_tick = Condition()

        self.songtickthread = SongTick( self.cv_tick, activityport )
        self.songtickthread.start()

        self.ingestthread = None

        self.alive = True

    def main(self):
        while self.alive:
            # process socket queue
            osc.readQueue(self.oscid)
            # process local even queue
            try:
                item = self.event_queue.get(block=False)
                item()
            except Queue.Empty:
                pass
            # wait for new events
            with self.cv_wait:
                self.cv_wait.wait( .1 )

    def audio_action_callback(self, message,*args):
        action = message[2]

        Logger.info("action: %s"%action)
        inst = SoundManager.instance()
        if action == 'load':
            inst.load( {'path':message[3],} )
        elif action == 'play':
            inst.play()
            with self.cv_tick:
                self.cv_tick.notify()
        elif action == 'pause':
            inst.pause()
            with self.cv_tick:
                self.cv_tick.notify()
        elif action == 'playpause':
            inst.playpause()
            with self.cv_tick:
                self.cv_tick.notify()
        elif action == 'unload':
            inst.unload()
        elif action == 'seek':
            seconds = message[3]
            inst.seek(seconds)
        elif action == 'volume':
            volume = message[3]
            inst.setVolume(volume)

    def on_state_change(self,*args):
        osc.sendMsg('/song_state', dataArray=args, port=activityport)

    def on_song_end_event(self,*args):
        """ catch the song end event, then pass off to the main thread.
        """
        self.event_queue.put( self.on_song_end )
        with self.cv_wait:
            self.cv_wait.notify()

    def on_song_end(self):
        Logger.info(" song finished ")
        sm = SoundManager.instance()
        if not sm.next():
            sm.dispatch('on_playlist_end')
        else:
            pl = PlaylistManager.instance().openPlaylist('current')
            idx,key = pl.current()
            sm.dispatch('on_state_changed',idx,key,sm.state())

    def on_playlist_end(self,*args):
        """callback for when there are no more songs in the current playlist"""
        Logger.info(" playlist finished ")
        #sm.unload()

    def ingest_start(self,message, *args):
        Logger.info("service: Ingest request recieved.")
        path = message[2]
        self.ingestthread = Ingest( activityport, self.db_path, path )
        self.ingestthread.start()

class SongTick(Thread):

    def __init__(self, cv_tick, port):
        super(SongTick,self).__init__()
        self.port = port
        self.cv_tick = cv_tick

    def run(self):
        while True:
            # update ui with current position
            p=SoundManager.instance().position()
            d=SoundManager.instance().duration()
            osc.sendMsg('/song_tick', dataArray=[p,d], port=self.port)

            # limit how often the message is sent.
            time.sleep(.5)

            # pause this thread while playback is paused
            with self.cv_tick:
                while SoundManager.instance().state() != MediaState.play:
                    self.cv_tick.wait()

