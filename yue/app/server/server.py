
import os,sys
import time
from threading import Thread, Condition
import Queue

from kivy.lib import osc
from kivy.logger import Logger

from yue.app.sound.manager import SoundManager
from yue.app.sound.device import MediaState
from yue.app.sound.pybass import get_platform_path
from yue.core.library import Library
from yue.core.playlist import PlaylistManager
from yue.core.sqlstore import SQLStore

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
        Logger.info("service: lib path: %s"%libpath)
        SoundManager.init( libpath )

        SoundManager.instance().bind(on_state_changed=self.on_state_change)
        SoundManager.instance().bind(on_song_end=self.on_song_end_event)
        SoundManager.instance().bind(on_playlist_end=self.on_playlist_end)

        self.event_queue = Queue.Queue()
        self.cv_wait = Condition()
        self.cv_tick = Condition()

        self.songtickthread = SongTick( self.cv_tick, activityport, self.on_song_end_event )
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

        Logger.info("service: action: %s"%action)

        inst = SoundManager.instance()
        if action == 'load':
            inst.load( {'path':message[3],} )
            self.sendCurrent()
        elif action == 'play':
            inst.play()
        elif action == 'pause':
            inst.pause()
        elif action == 'playpause':
            inst.playpause()
        elif action == 'unload':
            inst.unload()
        elif action == 'seek':
            seconds = message[3]
            inst.seek(seconds)
        elif action == 'volume':
            volume = message[3]
            inst.setVolume(volume)

        with self.cv_tick:
            self.cv_tick.notify()

    def on_state_change(self,*args):
        osc.sendMsg('/song_state', dataArray=args, port=activityport)

    def on_song_end_event(self,*args):
        """ catch the song end event, then pass off to the main thread.
        """
        self.event_queue.put( self.on_song_end )
        with self.cv_wait:
            self.cv_wait.notify()

    def on_song_end(self):
        Logger.info("service: song finished ")
        sm = SoundManager.instance()
        if not sm.next():
            sm.dispatch('on_playlist_end')
        else:
            self.sendCurrent()

        with self.cv_tick:
            self.cv_tick.notify()

    def sendCurrent(self):
        sm = SoundManager.instance()
        pl = PlaylistManager.instance().openPlaylist('current')
        idx,key = pl.current()
        osc.sendMsg('/song_state', dataArray=(idx,key,sm.state()), port=activityport)

    def on_playlist_end(self,*args):
        """callback for when there are no more songs in the current playlist"""
        Logger.info("service: playlist finished ")
        #sm.unload()

    def ingest_start(self,message, *args):
        Logger.info("service: Ingest request recieved.")
        path = message[2]
        self.ingestthread = Ingest( activityport, self.db_path, path )
        self.ingestthread.start()

class SongTick(Thread):

    """
    Note: this design was due to a threading problem with the on song
    end callback system within bass. Instead, this thread can now detect
    the end of a song via polling and call the next function automatically.
    this is a less than ideal temporary fix.
    """
    def __init__(self, cv_tick, port, cbk_end):
        super(SongTick,self).__init__()
        self.port = port
        self.cv_tick = cv_tick
        self.cbk_end = cbk_end

    def run(self):
        notified = True # prevent duplicate signals
        tpos = -1 # only update when the time changes
        tdur = -1
        while True:
            # update ui with current position
            tmp=SoundManager.instance().position()
            tdur=SoundManager.instance().duration()
            if tmp != tpos:
                tpos = tmp
                osc.sendMsg('/song_tick', dataArray=[tpos,tdur], port=self.port)

            # rate limit this thread
            time.sleep(.125)

            # pause this thread while playback is paused
            state = SoundManager.instance().state()

            if state == MediaState.end and not notified:
                self.cbk_end()
                notified = True
            else:
                with self.cv_tick:
                    # TODO:
                    # checking not_ready is a temporary patch where after seeking
                    # bass will be not_ready for a moment on android (uncertain why).
                    while state != MediaState.play and state != MediaState.not_ready:
                        Logger.info("service: song tick thread going to sleep %s"%state)
                        self.cv_tick.wait()
                        state = SoundManager.instance().state()
                        Logger.info("service: song tick thread waking up")
                    notified = False

