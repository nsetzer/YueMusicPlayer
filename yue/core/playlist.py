

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
        self.sqlstore = sqlstore

    @staticmethod
    def init( sqlstore ):
        PlaylistManager.__instance = PlaylistManager( sqlstore )

    @staticmethod
    def instance():
        return PlaylistManager.__instance

    def reopen(self):
        # return a copy of the library,
        # use to access from another thread
        return PlaylistManager( self.sqlstore.reopen() )

    def newPlaylist(self, name):

        uid = self.db_names.insert(name=name,size=0,idx=-1)

        view = PlayListView( self.db_names, self.db_lists, uid)

        return view

    def openCurrent(self):
        return self.openPlaylist("current")


    def deletePlaylist(self,name):

        with self.db_names.conn() as conn:
            c = conn.cursor()
            res = c.execute("SELECT uid from playlists where name=?", (name,))
            item = res.fetchone()
            if item is not None:
                c.execute("DELETE from playlist_songs where uid=?",(item[0],))
                c.execute("DELETE from playlists where name=?",(name,))

    def renamePlaylist(self,old_name,new_name):

        with self.db_names.conn() as conn:
            c = conn.cursor()
            res = c.execute("UPDATE playlists set name=? WHERE name=?", (new_name,old_name))
            print(res)

    def openPlaylist(self, name):
        """ create if it does not exist """

        with self.db_names.conn() as conn:
            c = conn.cursor()
            res = c.execute("SELECT uid from playlists where name=?", (name,))
            item = res.fetchone()
            if item is not None:
                return PlayListView( self.db_names, self.db_lists, item[0])
            # playlist does not exist, create a new empty one
            uid = self.db_names._insert(c,name=name,size=0,idx=-1)
            view = PlayListView( self.db_names, self.db_lists, uid)
            return view

    def names(self):
        """ return all playlist names """
        with self.db_names.conn() as conn:
            c = conn.cursor()
            c.execute("SELECT name from playlists ORDER BY name")
            items = c.fetchmany()
            while items:
                for item in items:
                    yield item[0]
                items = c.fetchmany()

    def exists(self,name):
        with self.db_names.conn() as conn:
            c = conn.cursor()
            c.execute("SELECT name from playlists ORDER BY name")
            items = c.fetchmany()
            while items:
                for item in items:
                    print(item[0],name)
                    if item[0] == name:
                        return True
                items = c.fetchmany()
        return False

class PlayListView(object):
    def __init__(self, db_names, db_lists, uid):
        super(PlayListView, self).__init__()

        self.db_names = db_names
        self.db_lists = db_lists
        self.uid = uid

    def set(self, lst):
        with self.db_names.conn() as conn:
            c = conn.cursor()
            self._set(c,lst)
            self.db_names._update(c, self.uid, size=len(lst), idx=0)

    def _set(self,cursor, lst):
        """ set the list of songs in the playlist to lst """
        cursor.execute("DELETE from playlist_songs where uid=?",(self.uid,))
        for idx, key in enumerate( lst ):
            self.db_lists._insert(cursor, uid=self.uid, idx=idx, song_id=key)

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
            return max(0,size)

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
            result = c.fetchone()
            if not result:
                raise IndexError("%d/%d - (no item)"%(idx,size))
            key = result[0]
            return key
        raise IndexError("%d/%d"%(idx,size))

    def insert(self,idx,key_or_lst):

        lst = key_or_lst
        if isinstance(key_or_lst, int):
            lst = [key_or_lst,]

        with self.db_lists.conn() as conn:
            c = conn.cursor()
            _, _, size, current = self.db_names._get( c, self.uid );
            if idx >= size:
                idx = size
            for key in reversed(lst):
                self._insert_one( c, idx, key)
                if idx <= current:
                    current += 1
                    self.db_names._update( c, self.uid, idx=current)

    def insert_next(self,key_or_lst):
        """ insert a song id after the current song id """
        with self.db_lists.conn() as conn:
            c = conn.cursor()
            if isinstance(key_or_lst,int):
                lst = [key_or_lst,]
            else:
                lst = key_or_lst

            _, name, size, current = self.db_names._get( c, self.uid );
            if size == 0:
                current = -1;
            for key in reversed(lst):
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
            result = c.fetchone()
            if not result:
                raise IndexError(idx1)
            key = result[0]
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

    def reinsertList(self, selection, insert_row):
        """
        selection: a list of unique row indices
        insert_row: move selection so the first element is at this index.
                    insert_row is an index in the original list

        Note: this returns the new list, but this is only a hack
        to optimize one specific area in the Qt Client.

        """
        selection = set(selection)

        with self.db_lists.conn() as conn:
            c = conn.cursor()

            _, name, size, current_index = self.db_names._get( c, self.uid );

            c.execute("select song_id from playlist_songs WHERE uid=? ORDER BY idx",(self.uid,))

            lst = []
            items = c.fetchmany()
            while items:
                lst += [ x[0] for x in items ]
                items = c.fetchmany()

            lsta, insert_row, count, current_index = reinsertList(lst, selection, insert_row, current_index)

            self._set(c, lsta)
            self.db_names._update( c, self.uid, idx=current_index)

            return lsta, insert_row, count

    def shuffle_range(self,start=None,end=None):
        """ shuffle a slice of the list, using python slice semantics
            playlist[start:end]

            TODO: doesnt handle update to current.
                current use case only ever shuffles [current + 1 : end]
                so this is not a problem
        """
        with self.db_lists.conn() as conn:
            c = conn.cursor()

            _, _, size, current = self.db_names._get( c, self.uid );

            if end is None:
                end = size

            if start is None:
                start = current + 1;
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

    def shuffle_selection(self, lst):
        """
        given a list of row indices, swap the position of each
        element randomly
        """
        # the set of keys to insert
        keys = []

        current_key = -1;

        with self.db_lists.conn() as conn:
            c = conn.cursor()
            _, _, _, current = self.db_names._get( c, self.uid );

            for item in lst:
                key = self._get(c, item)
                keys.append( key )

                if item == current:
                    current_key = key

            random.shuffle( keys )

            for i,k in zip(lst, keys):
                c.execute("UPDATE playlist_songs SET song_id=? WHERE uid=? and idx=?",(k,self.uid,i))
                if k == current_key:
                    self.db_names._update( c, self.uid, idx=i)

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
            result = c.fetchone()
            if not result:
                raise IndexError("name:`%s` idx:%d size:%d"%(name,idx,size))
            key = result[0]
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
            result = c.fetchone()
            if not result:
                raise IndexError(idx)
            key = result[0]
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
            result = c.fetchone()
            if not result:
                raise IndexError(idx)
            key = result[0]
            return idx,key

    def getDataView( self, library ):
        return PlayListDataView( library, self.db_names, self.db_lists, self.uid )

def reinsertList(lst,selection,insert_row,current_index=0):

    """
    Generic implementation for reinserting a set of elements.

    lst : a list of items (data type not important)
    selection : list/set of indices of elements in lst
    insert_row : an integer index into lst
    current_index : index of the current song, optional

    returns the new list, actual insert row, number of selected items
    and the updated current index.

    selects the set of items in selection in the order in which
    they appear in lst. These items are then insert at insert_row.
    removal / insertion may change the actual index of
    insert_row and current_index so these values will be recalculated
    accordingly
    """
    lsta = []
    lstb = []
    idx = 0;
    insert_offset = 0; # for updating current idx
    new_index = -1;

    for item in lst:
        if idx in selection:
            # if we need to update the current idx after drop
            if idx == current_index:
                insert_offset = len(lstb)
            # if the selection effects insert row
            if idx < insert_row:
                insert_row -= 1
            lstb.append(item)
        else:
            if (idx == current_index):
                new_index = len(lsta)
            lsta.append(item)
        idx += 1;

    # insert row must be in range 0..len(lsta)
    insert_row = min(insert_row, len(lsta))
    if new_index < 0:
        new_index = insert_row + insert_offset;
    elif insert_row <= new_index:
        new_index += len(lstb)

    if insert_row < len(lsta):
        lsta = lsta[:insert_row] + lstb + lsta[insert_row:]
    else:
        lsta = lsta + lstb

    return (lsta, insert_row, insert_row+len(lstb), new_index)

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

