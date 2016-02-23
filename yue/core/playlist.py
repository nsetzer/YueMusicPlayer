

from yue.core.sqlstore import SQLTable

import random

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

        self.db_names = SQLTable( sqlstore ,"playlists", playlist_columns)
        self.db_lists = SQLTable( sqlstore ,"playlist_songs", playlist_songs_columns)

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

    def __len__(self):
        return self.size()

    def set_index(self,idx):
        """ set the current playlist index, return key at that position """
        with self.db_lists.conn() as conn:
            c = conn.cursor()
            _, _, size, _ = self.db_names._get( c, self.uid );
            if 0 <= idx < size:
                self.db_names._update( c, self.uid, idx=idx );
                c.execute("SELECT song_id from playlist_songs where uid=? and idx=?", (self.uid,idx))
                return c.fetchone()[0]
        raise IndexError(idx)

    def get(self, idx):
        with self.db_lists.conn() as conn:
            return self._get( conn.cursor(), idx)

    def __getitem__(self,idx):

        if isinstance( idx, slice):
            raise ValueError(idx);

        with self.db_lists.conn() as conn:
            return self._get( conn.cursor(), idx)

    def _get(self,c, idx):
        _, _, size, _ = self.db_names._get( c, self.uid );
        assert size is not None
        if 0 <= idx < size:
            c.execute("SELECT song_id from playlist_songs where uid=? and idx=?", (self.uid,idx))
            return c.fetchone()[0]
        raise IndexError(idx)

    def insert(self,idx,key_or_lst):

        lst = key_or_lst
        if isinstance(key_or_lst, int):
            lst = [key_or_lst,]

        with self.db_lists.conn() as conn:
            c = conn.cursor()
            _, _, _, current = self.db_names._get( c, self.uid );
            for key in reversed(lst):
                self._insert_one( c, idx, key)
                if idx <= current:
                    current += 1
                    self.db_names._update( c, self.uid, idx=current)

    def insert_next(self,key):
        """ insert a song id after the current song id """
        with self.db_lists.conn() as conn:
            c = conn.cursor()
            _, name, size, current = self.db_names._get( c, self.uid );
            self._insert_one( c, current+1, key)

    def _insert_one(self, c, idx, key):
        c.execute("UPDATE playlist_songs SET idx=idx+1 WHERE uid=? and idx>=?",(self.uid,idx))
        self.db_lists._insert(c, uid=self.uid, idx=idx, song_id=key)
        c.execute("UPDATE playlists SET size=size+1 WHERE uid=?",(self.uid,))

    def delete(self,idx_or_lst):
        """ remove a song from the playlist by it's position in the list """

        lst = idx_or_lst
        if isinstance(idx_or_lst, int):
            lst = [idx_or_lst,]

        with self.db_lists.conn() as conn:
            c = conn.cursor()
            _, _, _, current = self.db_names._get( c, self.uid );
            for item in sorted(lst,reverse=True):
                self._delete_one(c, item)
                if item < current:
                    current -= 1
                    self.db_names._update( c, self.uid, idx=current)

    def _delete_one(self,c,idx):
        c.execute("DELETE from playlist_songs where uid=? and idx=?",(self.uid,idx))
        c.execute("UPDATE playlist_songs SET idx=idx-1 WHERE uid=? and idx>?",(self.uid,idx))
        c.execute("UPDATE playlists SET size=size-1 WHERE uid=?",(self.uid,))

    def clear(self):
        with self.db_lists.conn() as conn:
            c = conn.cursor()
            c.execute("DELETE from playlist_songs where uid=?",(self.uid,))

    def reinsert(self,idx1,idx2):
        """ remove an element at idx1, then insert at idx2 """
        with self.db_lists.conn() as conn:
            c = conn.cursor()
            _, _, _, cur = self.db_names._get( c, self.uid );
            c.execute("SELECT song_id from playlist_songs where uid=? and idx=?", (self.uid,idx1))
            key = c.fetchone()[0]
            c.execute("DELETE from playlist_songs where uid=? and idx=?",(self.uid,idx1))
            c.execute("UPDATE playlist_songs SET idx=idx-1 WHERE uid=? and idx>?",(self.uid,idx1))
            c.execute("UPDATE playlist_songs SET idx=idx+1 WHERE uid=? and idx>=?",(self.uid,idx2))
            if idx1 == cur:
                self.db_names._update( c, self.uid, idx=idx2)
            elif idx1 < cur and idx2 > cur:
                self.db_names._update( c, self.uid, idx=cur-1)
            elif idx1 > cur and idx2 < cur:
                self.db_names._update( c, self.uid, idx=cur+1)
            self.db_lists._insert(c, uid=self.uid, idx=idx2, song_id=key)

    def reinsertList(self, lst, row):
        """
        given a list of row indices, remove each row from the table
        then, in the order given, reinsert each element at the given row.
        """
        keys = []
        with self.db_lists.conn() as conn:
            c = conn.cursor()
            _, _, _, current = self.db_names._get( c, self.uid );

            # delete and keep track of selected items
            for item in sorted(lst,reverse=True):
                key = self._get(c, item)
                self._delete_one(c, item)
                if item <= current:
                    current -= 1
                    self.db_names._update( c, self.uid, idx=current)
                if item < row:
                    row -= 1
                keys.append( key )

            # reinsert the keys
            for key in keys:
                self._insert_one( c, row, key)

            # update the current index

            if row <= current:
                current += len(keys)
                self.db_names._update( c, self.uid, idx=current)

            _, _, _, cur = self.db_names._get( c, self.uid );

            return row,row+len(keys);

    def shuffle_range(self,start,end):
        """ shuffle a slice of the list, using python slice semantics
            playlist[start:end]

            TODO: doesnt handle update to current.
                current use case only ever shuffles [current + 1 : end]
                so this is not a problem
        """
        with self.db_lists.conn() as conn:
            c = conn.cursor()
            # extract the set of songs in the given range
            c.execute("SELECT song_id from playlist_songs where uid=? and idx BETWEEN ? and ?", (self.uid,start,end))
            keys = []
            items = c.fetchmany()
            while items:
                for item in items:
                    keys.append( item[0] )# song_id
                items = c.fetchmany()
            # this part could probably be done better
            # shuffle the song set
            random.shuffle(keys)
            # write the new order back to the list
            for i,k in enumerate(keys):
                c.execute("UPDATE playlist_songs SET song_id=? WHERE uid=? and idx=?",(k,self.uid,start+i))

    def iter(self):
        with self.db_lists.conn() as conn:
            c = conn.cursor()
            c.execute("select song_id from playlist_songs WHERE uid=? ORDER BY idx",(self.uid,))
            items = c.fetchmany()
            while items:
                for item in items:
                    yield item[0] # song_id
                items = c.fetchmany()

    def current(self):
        """ return a 2-tuple, current index, and song_id """
        with self.db_lists.conn() as conn:
            c = conn.cursor()
            _, name, size, idx = self.db_names._get( c, self.uid );
            c.execute("SELECT song_id from playlist_songs where uid=? and idx=?", (self.uid,idx))
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
            idx += 1
            if idx >= size:
                raise StopIteration()
            self.db_names._update( c, self.uid, idx=idx)
            c.execute("SELECT song_id from playlist_songs where uid=? and idx=?", (self.uid,idx))
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
            idx -= 1
            if idx < 0:
                raise StopIteration()
            self.db_names._update( c, self.uid, idx=idx)
            c.execute("SELECT song_id from playlist_songs where uid=? and idx=?", (self.uid,idx))
            key = c.fetchone()[0]
            return idx,key

    def getDataView( self, library ):
        return PlayListDataView( library, self.db_names, self.db_lists, self.uid )

class PlayListDataView(PlayListView):
    """A PlayListView backed by a library

    get returns a song instead of a
    """
    def __init__(self, library, db_names, db_lists, uid):
        super(PlayListDataView, self).__init__(db_names, db_lists, uid)
        self.library = library


    def get(self, idx):
        return self.__getitem__(idx)

    def __getitem__(self,idx):

        if isinstance( idx, slice):
            raise ValueError(idx);

        with self.db_lists.conn() as conn:
            c = conn.cursor()
            uid = self._get( c, idx);
            view = self.library.song_view
            item = view._get( c, uid)
            return dict(zip(view.column_names,item))
