
"""

screen that is displayed while searching the file system
for music to add to the library.

on first time use (before there is a database) this should
be the default home screen.

by default, scan the entire sdcard for supported file types

for the first time, after ~ 50 songs are found, build a playlist
and jump to now playing while this runs in the background. display
a pop up message that his is happening. maybe ask the user if it
is ok to jump.

allowing the user to use the app while loading creates a few ui issues
    a map is needed for 'artist' -> TreeElem, so that the library
    view can be updated.
    when calling settings go_library, the screen would need to be updated.
    this will inevitably slow down the loading process.

need a way to prevent duplicates, paths are case sensitive on linux,
    so matching by path should be sufficient. a hash table works
    but a bloom filter may be better.

"""
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.clock import mainthread
from kivy.logger import Logger

from yue.settings import Settings
from yue.library import Library

from threading import Thread
import traceback
import os
import time


class IngestScreen(Screen):
    def __init__(self,**kwargs):
        super(IngestScreen,self).__init__(**kwargs)

        self.vbox = BoxLayout(orientation='vertical')
        self.add_widget(self.vbox)

        self.lbl_dirname = Label(text="/")
        self.lbl_count   = Label(text="#") # display number of keys found

        self.btn_start = Button(text="start")
        self.btn_start.bind(on_press=self.start_ingest)

        self.btn_home = Button(text="home")
        self.btn_home.bind(on_press=Settings.instance().go_home)

        self.vbox.add_widget( self.btn_start )
        self.vbox.add_widget( self.lbl_dirname )
        self.vbox.add_widget( self.lbl_count )
        self.vbox.add_widget( self.btn_home )

    def start_ingest(self,*args):

        self.vbox.remove_widget( self.btn_start )
        #self.vbox.remove_widget( self.btn_home )
        self.thread = Ingest(self, Settings.instance().default_ingest_path )
        self.thread.start()

    @mainthread
    def update_labels(self,dirname,count):
        self.lbl_dirname.text = dirname
        self.lbl_count.text = count

    @mainthread
    def ingest_finished(self):
        self.vbox.add_widget( self.btn_start, index = 4 )
        #self.vbox.add_widget( self.btn_home , index = 0 )

class Ingest(Thread):
    """ scan a list of directories asynchronously for media files
    """
    def __init__(self,parent, *dirs):
        super(Ingest,self).__init__()
        self.parent = parent # instance of IngestScreen
        self.dirs = dirs

        Logger.info(u"ingest: directory list %s"%(self.dirs))

    def run(self):

        Logger.info("ingest: thread start")
        self.init_lut()

        Logger.info(u"ingest: directory list%s"%(self.dirs))

        for d in self.dirs:
            self.walk_directory(d)

        # couple ways to do this:
        #   1. after loading each song, update the tree.
        #   2. refresh the tree when ingest finishes
        # 2 is easier for now.

        settings = Settings.instance()
        scr = settings.manager.get_screen( settings.screen_library )
        scr.setLibraryTree( Library.instance().toTree() )

        self.parent.ingest_finished()

        Logger.info("ingest: thread exit")

    def init_lut(self):

        self.path_lut = Library.instance().toPathMap()
        self.types = Settings.instance().supported_types

    def walk_directory(self,dir):

        self.tstart = time.clock()
        count = 0
        for dirpath,_,filenames in os.walk( unicode(dir) ):

            Logger.info(u"ingest: %s"%(dirpath))

            count += self.load_directory(dirpath,filenames)

            self.rate_limit(.2,.1,dirpath,count)

        self.parent.update_labels("","%d"%count)

    def load_directory(self,dirpath,filenames):
        count = 0
        for name in filenames:
            try:
                path = os.path.join(dirpath,name).encode('utf-8')
                path = path.decode('utf-8')
                self.load_file( path )
                count += 1
            except Exception as e:
                Logger.error("bg: error %s"%e)
                traceback.print_exc()
        return count

    def load_file(self, path):

        ext = os.path.splitext(path)[1].lower()
        if ext in self.types and path not in self.path_lut:
            key = Library.instance().loadPath( path )
            self.path_lut[path] = key # not strictly necessary here.

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
            self.parent.update_labels(msg,"%d"%count)
            time.sleep(t2)

