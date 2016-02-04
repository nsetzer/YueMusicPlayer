
import os

from kivy.logger import Logger
#from kivy.storage.dictstore import DictStore

#from yue.settings import Settings
from yue.core.song import read_tags
from yue.core.sqlstore import SQLView

from ConfigParser import ConfigParser
import codecs

class Library(object):
    """docstring for Library"""
    __instance = None
    def __init__(self, sqlstore):
        super(Library, self).__init__()

        library_columns = [
            ('uid','integer PRIMARY KEY AUTOINCREMENT'),
            ('path',"text"),
            ('artist',"text"),
            ('composer',"text DEFAULT ''"),
            ('album','text'),
            ('title','text'),
            ('genre',"text DEFAULT ''"),
            ('year','integer DEFAULT 0'),
            ('country',"text DEFAULT ''"),
            ('lang',"text DEFAULT ''"),
            ('comment',"text DEFAULT ''"),
            ('album_index','integer DEFAULT 0'),
            ('length','integer DEFAULT 0'),
            ('last_played','integer DEFAULT 0'),
            ('playcount','integer DEFAULT 0'),
            ('rating','integer DEFAULT 0'),
        ]

        self.db = SQLView( sqlstore ,"library", library_columns)

    @staticmethod
    def init( sqlstore ):
        Library.__instance = Library( sqlstore )

    @staticmethod
    def instance():
        return Library.__instance

    def loadTestData(self,inipath,force=False):
        """
        read an ini file containing names and locations of songs.

        force: reload ini even if library db exists

        each section should be an unique integer starting at 1

        example:

        [1]
        artist=David Bowie
        title=....
        album=....
        path=/path/to/file

        [2]
        artist=David Bowie
        title=....
        album=....
        path=/path/to/file
        """

        #if not force and os.path.exists(Settings.instance().db_path):
        #    # delete the library to load the test file
        #    Logger.info('Library Found - not loading test data')
        #    return

        try:
            self.db.get(1)
            return
        except:
            pass
        if not os.path.exists(inipath):
            Logger.critical('test library not found: %s'%inipath)
            return

        Logger.info('loading test library: %s'%inipath)

        config = ConfigParser()
        config.readfp(codecs.open(inipath,"r","utf-8"))

        def get_default(section,option,default):
            if config.has_option(section,option):
                return config.get(section,option)
            return default

        for section in config.sections():
            print(section)
            song = {
                "artist" : get_default(section,"artist","Unkown Artist"),
                "album"  : get_default(section,"album" ,"Unkown Album"),
                "title"  : get_default(section,"title" ,"Unkown Title"),
                "path"   : get_default(section,"path"  ,""),

            }
            self.db.insert(**song)

        Logger.info('loading test library: %s'%inipath)

    def loadPath(self,songpath):
        """ does not check for duplicates """
        Logger.info("library: load song path: %s"%songpath)
        song = read_tags( songpath )
        return self.db.insert(**song)

    def songFromId(self,uid):
        return self.db.get(uid)

    def toPathMap(self):
        """
        the current kivy datastore impl for find() is to scan the entire store
        for a key value pair that matches a given filter.

        this pre-computes a dictionary of path -> uid, to quickly test if
        a given path exists in the db.
        """
        m = {}
        for song in self.db.iter():
            m[song['path']] = song['uid']
        return m

    def iter(self):
        return self.db.iter()


