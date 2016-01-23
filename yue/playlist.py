

import os,sys

from kivy.logger import Logger
from kivy.storage.dictstore import DictStore

from yue.settings import Settings
from yue.song import read_tags
from yue.sqlstore import SQLStore, SQLView

from yue.custom_widgets.tristate import TriState
from yue.custom_widgets.view import TreeElem
from yue.custom_widgets.playlist import PlayListElem

from ConfigParser import ConfigParser
import codecs

class PlaylistManager(object):
    """docstring for PlaylistManager"""
    __instance = None
    def __init__(self, sqlstore):
        super(PlaylistManager, self).__init__()

        playlist_columns = [
            ('uid','integer PRIMARY KEY AUTOINCREMENT'),
            ('name','text UNIQUE'),
            ('size','integer'), # number of elements in the playlist
            ('idx','integer'), # current playback index
        ]

        playlist_songs_columns = [
            ('uid','integer'), # foreign key into 'playlists'
            ('idx','integer'), # index in the current playlist
            ('song_id','integer') # foreign key into 'library'
        ]

        self.db_names = SQLView( sqlstore ,"playlists", playlist_columns)
        self.db_lists = SQLView( sqlstore ,"playlist_songs", playlist_songs_columns)

    @staticmethod
    def init( sqlstore ):
        PlaylistManager.__instance = PlaylistManager( sqlstore )


    @staticmethod
    def instance():
        return PlaylistManager.__instance

    def newPlaylist(self, name):

        uid = self.db_names.insert(name=name,size=0,idx=0)

        view = PlayListView( self.db_names, self.db_lists, uid)

        return view


class PlayListView(object):
    def __init__(self, db_names, db_lists, uid):
        super(PlayListView, self).__init__()

        self.db_names = db_names
        self.db_lists = db_lists
        self.uid = uid

    def append(self, key):
        with self.db_names.conn() as conn:
            c = conn.cursor()
            _, name, size, idx = self.db_names._get( c, self.uid );
            self.db_lists._insert(c, uid=self.uid, idx=size, song_id=key)
            self.db_names._update(c, self.uid, size=size+1)

    def size(self):
        with self.db_names.conn() as conn:
            c = conn.cursor()
            _, name, size, index = self.db_names._get( c, self.uid );
            return size

    def delete(self,idx):
        with self.db_lists.conn() as conn:
            c = conn.cursor()
            c.execute("DELETE from playlist_songs where uid=? and idx=?",(self.uid,idx))
            c.execute("UPDATE playlist_songs SET idx=idx-1 WHERE uid=? and idx>?",(self.uid,idx))
            self.db_names._update(c, self.uid, size=size-1)

    def reinsert(self,idx1,idx2):
        """ remove an element at idx1, then insert at idx2 """
        pass

    def iter(self):
        with self.db_lists.conn() as conn:
            c = conn.cursor()
            c.execute("select * from playlist_songs WHERE uid=? ORDER BY idx",(self.uid,))
            item = c.fetchone()
            while item is not None:
                yield item
                item = c.fetchone()






