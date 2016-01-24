
# todo use argparse to get host/port from parent.
#   then:
#       1. send listening port back to the parent
#       2. or have the parent pass in the port to listen on.
# see PyOSC documentation
import os,sys
import time
from threading import Thread, Condition
import Queue

from kivy.lib import osc
from kivy.logger import Logger

app_path = '/data/data/com.github.nsetzer.yue/'
if os.path.exists(app_path):
    # android
    dirpath = '/data/data/com.github.nsetzer.yue/files'
else:
    # other
    dirpath = os.path.dirname(os.path.abspath(__file__))
    dirpath = os.path.dirname(dirpath)
    app_path = os.getcwd()
# update system path with path to yue package
sys.path.insert(0,dirpath)

from yue.sound.manager import SoundManager
from yue.sound.pybass import get_platform_path
from yue.library import Library
from yue.playlist import PlaylistManager
from yue.sqlstore import SQLStore, SQLView

serviceport = 15123
activityport = 15124

def audio_action_callback(message,*args):
    action = message[2]

    Logger.info("action: %s"%action)
    inst = SoundManager.instance()
    if action == 'load':
        inst.load( {'path':message[3],} )
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

class YueServer(object):
    """docstring for YueServer"""
    # https://docs.python.org/2/library/queue.html
    # https://docs.python.org/2/library/threading.html#condition-objects
    def __init__(self):
        super(YueServer, self).__init__()

        osc.init()
        self.oscid = osc.listen(ipAddr='127.0.0.1', port=serviceport)
        osc.bind(self.oscid, audio_action_callback, '/audio_action')

        db_path = os.path.join(app_path,"yue.db")
        self.sqlstore = SQLStore(db_path)
        Library.init( self.sqlstore )
        PlaylistManager.init( self.sqlstore )
        libpath = get_platform_path()
        SoundManager.init( libpath )

        SoundManager.instance().bind(on_state_changed=self.on_state_change)
        SoundManager.instance().bind(on_song_end=self.on_song_end_event)
        SoundManager.instance().bind(on_playlist_end=self.on_playlist_end)

        self.event_queue = Queue.Queue()
        self.cv_wait = Condition()

        self.songtickthread = SongTick()
        self.songtickthread.start()

    def main(self):
        while True:
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

class SongTick(Thread):

    # todo: condition variables to sleep this thread when not playing music
    def run(self):
        while True:
            p=SoundManager.instance().position()
            d=SoundManager.instance().duration()
            osc.sendMsg('/song_tick', dataArray=[p,d], port=activityport)
            time.sleep(.5)

if __name__ == '__main__':

    server = YueServer()
    server.main()


    Logger.info("service: exit")

