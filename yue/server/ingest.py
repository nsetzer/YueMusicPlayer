
from kivy.logger import Logger
from kivy.lib import osc

from threading import Thread
import traceback
import os
import time

from yue.library import Library
from yue.sqlstore import SQLStore
from yue.sound.manager import SoundManager

class Ingest(Thread):
    """ scan a list of directories asynchronously for media files
    """
    def __init__(self, activityport, db_path, *dirs):
        super(Ingest,self).__init__()
        self.activityport = activityport
        self.dirs = dirs
        self.db_path = db_path

        Logger.info(u"ingest: directory list %s"%(self.dirs))

    def run(self):

        Logger.info("ingest: thread start")
        self.init_lut()

        Logger.info(u"ingest: directory list%s"%(self.dirs))

        for d in self.dirs:
            self.walk_directory(d)

        self.finished()

        Logger.info("ingest: thread exit")

    def init_lut(self):

        self.sqlstore = SQLStore( self.db_path )
        self.library = Library( self.sqlstore )

        self.path_lut = self.library.toPathMap()
        self.types = SoundManager.supported_types

    def walk_directory(self,dir):

        self.tstart = time.clock()
        count = 0
        for dirpath,_,filenames in os.walk( unicode(dir) ):

            Logger.info(u"ingest: %s"%(dirpath))

            count += self.load_directory(dirpath,filenames)

            self.rate_limit(.2,.1,dirpath,count)

        # one final ui updated.
        self.update_labels("","%d"%count)

    def load_directory(self,dirpath,filenames):
        count = 0
        for name in filenames:
            try:
                path = os.path.join(dirpath,name).encode('utf-8')
                path = path.decode('utf-8')
                if self.load_file( path ):
                    count += 1
            except Exception as e:
                Logger.error("bg: error %s"%e)
                traceback.print_exc()
        return count

    def load_file(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext in self.types and path not in self.path_lut:
            key = self.library.loadPath( path )
            self.path_lut[path] = key # not strictly necessary here.
            return True
        return False

    def rate_limit(self,t1,t2,msg,count):
        # rate limit background thread (needs some work)
        # sleep for t2 seconds every t1 seconds.
        # update the ui before sleeping ( this prevents flooding
        # the event manager with ui updates ). This should
        # also allow other apps time to run, access the disk
        e = time.clock()
        delta = e - self.tstart
        if delta > t1 :
            self.tstart = e
            self.update_labels(msg,"%d"%count)
            time.sleep(t2)


    def update_labels(self,msg1,msg2):
        osc.sendMsg('/ingest_update', dataArray=[msg1,msg2,], port=self.activityport)

    def finished(self):
        osc.sendMsg('/ingest_finished', dataArray=[], port=self.activityport)
