
from kivy.logger import Logger
from kivy.lib import osc

from threading import Thread
import traceback
import os, stat
import time

from yue.core.library import Library
from yue.core.sqlstore import SQLStore
from yue.sound.manager import SoundManager

ignore_paths = { '/d', '/sys', '/system', '/sbin', '/bin', '/firmware', '/dev', '/proc' }

def android_walk(root, exts, callback=None, t1=.2, t2=.1):
    """
    walk a directory and all sub directories.

    ignore directories that contain a '.nomedia' directory
    callback is a callable object that accepts two strings,
        a directory and count of files found so far
    t1,t2 are used to rate-limit this function
        the functions sleeps for t2 seconds every t1 seconds.
    """
    queue = [root, ]
    tstart = time.clock()
    count = 0

    while queue:
        path = queue.pop(0)

        try:
            children = os.listdir( path )
        except OSError:
            continue # TODO test permissions

        # android convention
        if '.nomedia' in children:
            Logger.info(u"ingest: skipping: %s"%(path))
            continue

        Logger.info(u"ingest: %s"%(path))

        for name in children:
            child_path = os.path.join( path, name)
            try:
                st = os.stat( child_path )
                if stat.S_ISDIR( st.st_mode ):
                    if child_path in ignore_paths:
                        Logger.info(u"ingest: skipping: %s"%(path))
                        continue
                    queue.append( child_path )
                else:
                    ext = os.path.splitext(name)[1].lower()
                    if ext in exts:
                        count += 1
                        yield child_path
            except OSError:
                pass

        # ratelimit
        e = time.clock()
        delta = e - tstart
        if delta > t1 :
            tstart = e
            if callback is not None:
                callback(path,"%d"%count)
            time.sleep(t2)

    if callback is not None:
        callback("done","%d"%count)


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

        for path in android_walk( unicode(dir) ,  self.types, self.update_labels ):
            if path not in self.path_lut:
                try:
                    key = self.library.loadPath( path )
                    self.path_lut[path] = key # not strictly necessary here.
                except Exception as e:
                    # TODO: log traceback
                    Logger.error("ingest: %s: %s"%(type(e),e))




        #count = 0
        #for dirpath,_,filenames in os.walk( unicode(dir) ):
        #    Logger.info(u"ingest: %s"%(dirpath))
        #    count += self.load_directory(dirpath,filenames)
        #    self.rate_limit(.2,.1,dirpath,count)

        # one final ui updated.
        #self.update_labels("","%d"%count)

    #def load_directory(self,dirpath,filenames):
    #    count = 0
    #    for name in filenames:
    #        try:
    #            path = os.path.join(dirpath,name).encode('utf-8')
    #            path = path.decode('utf-8')
    #            if self.load_file( path ):
    #                count += 1
    #        except Exception as e:
    #            Logger.error("bg: error %s"%e)
    #            traceback.print_exc()
    #    return count

    #def load_file(self, path):
    #    ext = os.path.splitext(path)[1].lower()
    #    if ext in self.types and path not in self.path_lut:
    #        key = self.library.loadPath( path )
    #        self.path_lut[path] = key # not strictly necessary here.
    #        return True
    #    return False

    def update_labels(self,msg1,msg2):
        osc.sendMsg('/ingest_update', dataArray=[msg1,msg2,], port=self.activityport)

    def finished(self):
        osc.sendMsg('/ingest_finished', dataArray=[], port=self.activityport)
