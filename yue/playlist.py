

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

    def openPlaylist(self, name):
        """ create if it does not exist """

        with self.db_names.conn() as conn:
            c = conn.cursor()
            res = c.execute("SELECT uid from playlists where name=?", (name,))
            item = res.fetchone()
            if item is not None:
                return PlayListView( self.db_names, self.db_lists, item[0])
            # playlist does not exist, create a new empty one
            uid = self.db_names._insert(c,name=name,size=0,idx=0)
            view = PlayListView( self.db_names, self.db_lists, uid)
            return view



class PlayListView(object):
    def __init__(self, db_names, db_lists, uid):
        super(PlayListView, self).__init__()

        self.db_names = db_names
        self.db_lists = db_lists
        self.uid = uid

    def set(self, lst):
        with self.db_names.conn() as conn:
            c = conn.cursor()
            c.execute("DELETE from playlist_songs where uid=?",(self.uid,))
            for idx, key in enumerate( lst ):
                self.db_lists._insert(c, uid=self.uid, idx=idx, song_id=key)
            self.db_names._update(c, self.uid, size=len(lst), idx=0)

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

    def get(self, idx):
        with self.db_lists.conn() as conn:
            c = conn.cursor()
            _, _, size, _ = self.db_names._get( c, self.uid );
            if 0 <= idx < size:
                res = (c.execute("SELECT song_id from playlist_songs where uid=? and idx=?", (self.uid,idx)))
                return c.fetchone()[0]
        raise IndexError(idx)

    def insert(self,idx,key):
        with self.db_lists.conn() as conn:
            c = conn.cursor()
            c.execute("UPDATE playlist_songs SET idx=idx+1 WHERE uid=? and idx>=?",(self.uid,idx))
            self.db_lists._insert(c, uid=self.uid, idx=idx, song_id=key)
            c.execute("UPDATE playlists SET size=size+1 WHERE uid=?",(self.uid,))

    def insert_next(self,key):
        """ insert a song id after the current song id """
        with self.db_lists.conn() as conn:
            c = conn.cursor()
            _, name, size, idx = self.db_names._get( c, self.uid );
            idx += 1
            c.execute("UPDATE playlist_songs SET idx=idx+1 WHERE uid=? and idx>=?",(self.uid,idx))
            self.db_lists._insert(c, uid=self.uid, idx=idx, song_id=key)
            c.execute("UPDATE playlists SET size=size+1 WHERE uid=?",(self.uid,))

    def delete(self,idx):
        """ remove an song from the playlist by it's position in the list """
        with self.db_lists.conn() as conn:
            c = conn.cursor()
            c.execute("DELETE from playlist_songs where uid=? and idx=?",(self.uid,idx))
            c.execute("UPDATE playlist_songs SET idx=idx-1 WHERE uid=? and idx>?",(self.uid,idx))
            c.execute("UPDATE playlists SET size=size-1 WHERE uid=?",(self.uid,))

    def clear(self):
        with self.db_lists.conn() as conn:
            c = conn.cursor()
            c.execute("DELETE from playlist_songs where uid=? and idx=?",(self.uid,idx))
            c.execute("UPDATE playlist_songs SET idx=idx-1 WHERE uid=? and idx>?",(self.uid,idx))
            c.execute("UPDATE playlists SET size=size-1 WHERE uid=?",(self.uid,))

    def reinsert(self,idx1,idx2):
        """ remove an element at idx1, then insert at idx2 """
        with self.db_lists.conn() as conn:
            c = conn.cursor()
            res = (c.execute("SELECT song_id from playlist_songs where uid=? and idx=?", (self.uid,idx1)))
            key = c.fetchone()[0]
            c.execute("DELETE from playlist_songs where uid=? and idx=?",(self.uid,idx1))
            c.execute("UPDATE playlist_songs SET idx=idx-1 WHERE uid=? and idx>?",(self.uid,idx1))
            c.execute("UPDATE playlist_songs SET idx=idx+1 WHERE uid=? and idx>=?",(self.uid,idx2))
            self.db_lists._insert(c, uid=self.uid, idx=idx2, song_id=key)

    def shuffle_range(self,start,end):
        """ shuffle a slice of the list, using python slice semantics
            playlist[start:end]
        """
        pass

    def iter(self):
        with self.db_lists.conn() as conn:
            c = conn.cursor()
            c.execute("select * from playlist_songs WHERE uid=? ORDER BY idx",(self.uid,))
            items = c.fetchmany()
            while items:
                for item in items:
                    yield item
                items = c.fetchmany()

    def current(self):
        """ return a 2-tuple, current index, and song_id """
        with self.db_lists.conn() as conn:
            c = conn.cursor()
            _, name, size, idx = self.db_names._get( c, self.uid );
            res = (c.execute("SELECT song_id from playlist_songs where uid=? and idx=?", (self.uid,idx)))
            key = c.fetchone()[0]
            return idx,key

    def next(self):
        """ increase current index by 1
            return a 2-tuple, current index, and song_id
            raise StopIteration if no more songs
        """
        with self.db_lists.conn() as conn:
            c = conn.cursor()
            _, name, size, idx = self.db_names._get( c, self.uid );
            if idx >= size:
                raise StopIteration()
            idx += 1
            self.db_names._update( c, self.uid, idx=idx)
            res = (c.execute("SELECT song_id from playlist_songs where uid=? and idx=?", (self.uid,idx)))
            key = c.fetchone()[0]
            return idx,key

    def prev(self):
        """ increase current index by 1
            return a 2-tuple, current index, and song_id
            raise StopIteration if no more songs
        """
        with self.db_lists.conn() as conn:
            c = conn.cursor()
            _, name, size, idx = self.db_names._get( c, self.uid );
            if idx <= 0:
                raise StopIteration()
            idx -= 1
            self.db_names._update( c, self.uid, idx=idx)
            res = (c.execute("SELECT song_id from playlist_songs where uid=? and idx=?", (self.uid,idx)))
            key = c.fetchone()[0]
            return idx,key






