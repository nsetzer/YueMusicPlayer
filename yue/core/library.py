
import re

"""

Schema (high level description)

tables:
    artists
    albums
    songs

views:
    library

The 'artists' and 'albums' tables encode the libraries set of
artists and albums. They each maintain a count of associated songs
each album is unique to a given artist (so that there may be multiple
albums with the same name associated with different artists)

the 'songs' table encodes the remaining information for each song. It
uses foreign keys to map to an artist / album.

Sort Keys are used for certain text fields (currently artist name only)
A function is used to map an text field to a value to be used in sorting.
when using ORDER BY in sequal `column`_key may be used in place of `column`
to sort by the alternate text.

"""

import os, time

import sys
isPython3 = sys.version_info[0]==3
if isPython3:
    unicode = str

from .search import sql_search, BlankSearchRule, RegExpSearchRule, ExactSearchRule, AndSearchRule
#from kivy.logger import Logger
#from kivy.storage.dictstore import DictStore

#from yue.settings import Settings
from .song import Song, SongSearchGrammar
from .history import History
from .sqlstore import SQLTable, SQLView
from .util import check_path_alternatives

try:
    # 3.x name
    import configparser
except ImportError:
    # 2.x name
    import ConfigParser as configparser
import codecs

def getSortKey( string ):
    """
    normalize text fields for sorting
    """
    low = string.lower()
    if low.startswith("the "):
        string = string[4:]
    return string

class Library(object):
    """docstring for Library"""
    __instance = None
    def __init__(self, sqlstore):
        super(Library, self).__init__()
        artists = [
            ("uid","INTEGER PRIMARY KEY AUTOINCREMENT"),
            ("artist","text"),
            ("sortkey","text"),
            ("count","INTEGER DEFAULT 0")
        ]

        albums = [
            ("uid","INTEGER PRIMARY KEY AUTOINCREMENT"),
            ("artist","INTEGER"),
            ("album","text"),
            ("sortkey","text"), # TODO: deprecated
            ("count","INTEGER DEFAULT 0")
        ]
        album_foreign_keys = [
            "FOREIGN KEY(artist) REFERENCES artists(uid)",
        ]

        #composers = [
        #    ("uid","INTEGER PRIMARY KEY AUTOINCREMENT"),
        #    ("composer","text")
        #]

        songs_columns = [
            ('uid','integer PRIMARY KEY AUTOINCREMENT'),
            ('path',"text"),
            ('source_path',"text DEFAULT ''"),
            #('artist',"text"),
            ('artist',"INTEGER"),
            ('composer',"text DEFAULT ''"),
            #('album','text'),
            ('album','INTEGER'),
            ('title','text'),
            #('title_key','text'), #TODO: look into data duplication
            ('genre',"text DEFAULT ''"),
            ('year','integer DEFAULT 0'),
            ('country',"text DEFAULT ''"),
            ('lang',"text DEFAULT ''"),
            ('comment',"text DEFAULT ''"),
            ('album_index','integer DEFAULT 0'),
            ('length','integer DEFAULT 0'),
            ('last_played','integer DEFAULT 0'),
            ('date_added','integer DEFAULT 0'),
            ('playcount','integer DEFAULT 0'),
            ('skip_count','integer DEFAULT 0'),
            ('rating','integer DEFAULT 0'),
            ('blocked','integer DEFAULT 0'),
            ('equalizer','integer DEFAULT 0'),
            ('opm','integer DEFAULT 0'),
            ('frequency','integer DEFAULT 0'),
            ('file_size','integer DEFAULT 0'),

        ]
        songs_foreign_keys = [
            "FOREIGN KEY(artist) REFERENCES artists(uid)",
            "FOREIGN KEY(album) REFERENCES albums(uid)",
        ]

        self.sqlstore = sqlstore
        self.artist_db = SQLTable( sqlstore ,"artists", artists)
        self.album_db = SQLTable( sqlstore ,"albums", albums, album_foreign_keys)
        self.song_db = SQLTable( sqlstore ,"songs", songs_columns, songs_foreign_keys)

        colnames = [ 'uid', 'path', 'source_path',
                     'artist', 'artist_key',
                     'composer',
                     'album', #'album_key',
                     'title', #'title_key',
                     'genre', 'year', 'country', 'lang', 'comment',
                     'album_index', 'length', 'last_played', 'date_added',
                     'playcount', 'skip_count', 'rating',
                     'blocked', 'equalizer', 'opm', 'frequency', 'file_size']

        cols = []
        for col in colnames:
            if col == 'artist':
                cols.append("a."+col)
            elif col == 'artist_key':
                cols.append("a.sortkey as artist_key")
            elif col == 'album':
                cols.append("b."+col)
            #elif col == 'album_key':
            #    cols.append("b.sortkey as album_key")
            else:
                cols.append("s."+col)
        viewname = "library"
        #cols = "s.uid, s.path, a.artist, s.composer, b.album, s.title,
        # s.genre, s.year, s.country, s.lang, s.comment, s.album_index,
        #s.length, s.last_played, s.date_added, s.playcount, s.skip_count,
        # s.rating, s.blocked, s.equalizer, s.opm, s.frequency, s.file_size"
        cols = ', '.join(cols)
        tbls = "songs s, artists a, albums b"
        where = "s.artist=a.uid AND s.album=b.uid"
        sql = """CREATE VIEW IF NOT EXISTS {} as SELECT {} FROM {} WHERE {}""".format(viewname,cols,tbls,where)

        self.song_view = SQLView( sqlstore, viewname, sql, colnames)
        #instance of History() for recording events
        self.history = None

        self.grammar = SongSearchGrammar();

    @staticmethod
    def init( sqlstore ):
        Library.__instance = Library( sqlstore )

    @staticmethod
    def instance():
        return Library.__instance

    def reopen(self):
        # return a copy of the library,
        # use to access from another thread
        return Library( self.sqlstore.reopen() )

    def __len__(self):
        return self.song_db.count()

    def insert(self,**kwargs):

        # prevent assigning a uid of 0 to a song, instead
        # let the db determine a unique id
        if Song.uid in kwargs:
            if not kwargs[Song.uid]:
                del kwargs[Song.uid]

        with self.sqlstore.conn:
            c = self.sqlstore.conn.cursor()
            return self._insert(c, **kwargs)

    def _insert(self,c, **kwargs):
        kwargs['artist'] = self.artist_db._get_id_or_insert(c,
                artist=kwargs['artist'],
                sortkey=getSortKey(kwargs['artist']))
        kwargs['album'] = self.album_db._get_id_or_insert(c, \
            album=kwargs['album'], \
            sortkey=getSortKey(kwargs['album']),
            artist=kwargs['artist'])
        #if 'title_key' not in kwargs:
        #    kwargs['title_key'] = getSortKey( kwargs['title'] )
        c.execute("UPDATE artists SET count=count+1 WHERE uid=?",(kwargs['artist'],))
        c.execute("UPDATE albums SET count=count+1 WHERE uid=?",(kwargs['album'],))
        return self.song_db._insert(c,**kwargs)

    def update(self,uid,**kwargs):
        """ update song values in the database """
        with self.sqlstore.conn:
            c = self.sqlstore.conn.cursor()
            self._update_one(c, uid, **kwargs)
            c.execute("DELETE FROM artists WHERE count=0")
            c.execute("DELETE FROM albums WHERE count=0")

    def update_many(self,uids,**kwards):
        """ update song values in the database """
        with self.sqlstore.conn:
            c = self.sqlstore.conn.cursor()
            for uid in uids:
                self._update_one(c, uid, **kwards)
            c.execute("DELETE FROM artists WHERE count=0")
            c.execute("DELETE FROM albums WHERE count=0")

    def incrementPlaycount(self, uid):

        with self.sqlstore.conn:
            c = self.sqlstore.conn.cursor()
            c.execute("SELECT playcount, frequency, last_played FROM songs WHERE uid=?",(uid,))
            item = c.fetchone()
            if item is None:
                raise ValueError( uid )
            last_played, freq = Song.calculateFrequency(*item);
            c.execute("UPDATE songs SET playcount=playcount+1, frequency=?, last_played=? WHERE uid=?", \
                      (freq, last_played, uid))
            if self.history is not None:
                self.history.incrementPlaycount(c,uid,last_played)

    def incrementSkipcount(self, uid):

        with self.sqlstore.conn:
            c = self.sqlstore.conn.cursor()
            c.execute("UPDATE songs SET skip_count=skip_count+1 WHERE uid=?", (uid,))

    def _update_one(self,c, uid, **kwargs):
        info = list(self.song_db._select_columns(c,['artist','album'],uid=uid))[0]
        old_art_id = info['artist']
        old_abm_id = info['album']

        # cannot change uid
        if 'uid' in kwargs:
            del kwargs['uid']

        if self.history is not None:
            self.history.update(c,uid,**kwargs)

        # altering artist, album requires updating count of songs
        # and removing artists that no longer exist.
        if 'artist' in kwargs:
            new_art_id = self.artist_db._get_id_or_insert(c,
                artist=kwargs['artist'],
                sortkey=getSortKey(kwargs['artist']))
            c.execute("UPDATE artists SET count=count+1 WHERE uid=?",(new_art_id,))
            c.execute("UPDATE artists SET count=count-1 WHERE uid=?",(old_art_id,))
            # update field as integer, not string
            kwargs['artist'] = new_art_id
            old_art_id = new_art_id

        if 'album' in kwargs:
            new_abm_id = self.album_db._get_id_or_insert(c,
                album=kwargs['album'],
                #sortkey=getSortKey(kwargs['album']),
                artist=old_art_id)
            c.execute("UPDATE albums SET count=count+1 WHERE uid=?",(new_abm_id,))
            c.execute("UPDATE albums SET count=count-1 WHERE uid=?",(old_abm_id,))
            # update field as integer, not string
            kwargs['album'] = new_abm_id

        #if 'title' in kwargs and 'title_key' not in kwargs:
        #    kwargs['title_key'] = getSortKey( kwargs['title'] )

        # update all remaining fields
        if kwargs:
            self.song_db._update(c, uid, **kwargs)

    def increment(self,uid,field,value=1):
        """
        increment an integer field for a song
        e.g.
            self.increment(uid,'playcount')
        """
        with self.sqlstore.conn:
            c = self.sqlstore.conn.cursor()
            c.execute("UPDATE songs SET %s=%s%+d WHERE uid=?"%(field,field,value),(uid,))

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
            self.song_view.get(1)
            return
        except:
            pass
        if not os.path.exists(inipath):
            #Logger.critical('test library not found: %s'%inipath)
            return

        #Logger.info('loading test library: %s'%inipath)

        config = configparser.ConfigParser()
        config.readfp(codecs.open(inipath,"r","utf-8"))

        def get_default(section,option,default):
            if config.has_option(section,option):
                return config.get(section,option)
            return default

        for section in config.sections():
            song = {
                "artist" : get_default(section,"artist","Unkown Artist"),
                "album"  : get_default(section,"album" ,"Unkown Album"),
                "title"  : get_default(section,"title" ,"Unkown Title"),
                "path"   : get_default(section,"path"  ,""),

            }
            self.insert(**song)

        #Logger.info('loading test library: %s'%inipath)

    def loadPath(self,songpath):
        """ does not check for duplicates """
        #Logger.info("library: load song path: %s"%songpath)
        song = Song.fromPath( songpath )
        return self.insert(**song)

    def songFromId(self,uid):
        return self.song_view.get(uid)

    def songFromIds(self,lst):

        songs = []
        with self.song_view.store.conn:
            c = self.song_view.store.conn.cursor()
            for uid in lst:
                item = self.song_view._get(c,uid)
                songs.append( dict(zip(self.song_view.column_names,item)) )
        return songs

    def toPathMap(self):
        """
        the current kivy datastore impl for find() is to scan the entire store
        for a key value pair that matches a given filter.

        this pre-computes a dictionary of path -> uid, to quickly test if
        a given path exists in the db.
        """
        m = {}
        for song in self.song_view.iter():
            m[song[Song.path]] = song[Song.uid]
        return m

    # deprecated
    def iter(self):
        return self.song_view.iter()

    def search(self, rule , case_insensitive=True, orderby=None, reverse = False, limit = None):

        if rule is None:
            rule = BlankSearchRule();
        elif isinstance(rule,(str,unicode)):
            rule = self.grammar.ruleFromString( rule )
            limit = self.grammar.getMetaValue("limit",limit)

        if orderby is not None:
            if not isinstance( orderby, (list,tuple)):
                orderby = [ orderby, ]
            # this column has a special column used in sorting.
            for i,v in enumerate(orderby):
                if v in [Song.artist,]:
                    orderby[i]+="_key"

        echo = False
        return sql_search( self.song_view, rule, case_insensitive, orderby, reverse, limit, echo )

    def searchPlaylist(self, playlist_name, rule=None, case_insensitive=True, invert=False, orderby=None, reverse = False, limit=None):

        if rule is None:
            rule = BlankSearchRule();
        elif isinstance(rule,(str,unicode)):
            rule = self.grammar.ruleFromString( rule )

        where,where_vals = rule.sql()

        if where:

            if invert:
                # select songs not in a named playlist (filtered)
                sql = "where (sv.uid NOT IN (SELECT ps.song_id from playlist_songs ps where ps.uid=?) AND %s)"%where
            else:
                # select songs in a named playlist, (filtered)
                sql = "JOIN playlist_songs ps where (ps.uid=? and ps.song_id=sv.uid AND %s)"%where
        else:

            if invert:
                # select songs not in a named playlist, (blank search)
                sql = "where sv.uid NOT IN (SELECT ps.song_id from playlist_songs ps where ps.uid=?)"
            else:
                # select songs in a named playlist (blank search)
                sql = "JOIN playlist_songs ps where (ps.uid=? and ps.song_id=sv.uid)"

        sql = "SELECT sv.* FROM library as sv " + sl

        if case_insensitive:
            sql += " COLLATE NOCASE"

        direction = " ASC"
        if reverse:
            direction = " DESC"
        if case_insensitive:
            direction = " COLLATE NOCASE" + direction

        # TODO: ORDERBY=INDEX : keep the order given by the playlist
        if orderby is not None:
            if not isinstance(orderby,(tuple,list)):
                orderby = [ orderby, ]
            if orderby[0].upper() == "RANDOM":
                sql += " ORDER BY RANDOM()"
            else:
                orderby = [ x+direction for x in orderby]
                sql += " ORDER BY " + ", ".join(orderby)

        if limit is not None:
            sql += " LIMIT %d"%limit

        with self.sqlstore.conn:
            c = self.sqlstore.conn.cursor()

            #s = time.time()
            c.execute("SELECT uid from playlists where name=?", (playlist_name,))
            item = c.fetchone()
            if item is None:
                raise ValueError( playlist_name )
            pluid = item[0]

            c.execute(sql,(pluid,) + tuple(where_vals))
            items = c.fetchmany()
            while items:
                for item in items:
                    yield {k:v for k,v in zip(self.song_view.column_names,item)}
                items = c.fetchmany()
            #e =  time.time()
            #print("pl search",e-s,sql)

        return

    def searchPath(self, path):
        """
        return a list of songs that match a given path
        """

        # TODO: windows only, must be able to match both types of slashes

        # replace toothpicks
        path = path.replace("\\","/")
        # escape all special characters .... including forward slash
        path = re.escape( path )
        # replace forward slash with a pattern that matches both slashes
        path = path.replace("\\/","[\\\\/]")

        rule = RegExpSearchRule(Song.path,"^%s$"%path)

        return self.search(rule)

    def searchDirectory(self, path, recursive=False):
        """
        query the database for all songs that exist in a directory.

        path must be an absolute path (e.g. C:\Music or /path/to/file)
            it cannot be a path to a file.

        recursive:
            True : return files in subdirectories of the given directory
            False: returns files only in the given directory.
        """

        # TODO: windows only, must be able to match both types of slashes

        # replace toothpicks, and ensure path ends with a final slash
        path = path.replace("\\","/")
        if not path.endswith("/"):
            path += "/"
        # escape all special characters .... including forward slash
        path = re.escape( path )
        # replace forward slash with a pattern that matches both slashes
        path = path.replace("\\/","[\\\\/]")

        if recursive:
            # match any file that starts with
            q = "^%s.*$"%path
        else:
            # match only in this directory
            # todo linux: use "^%s[^/]*$"
            q = "^%s[^\\\\/]*$"%path

        rule = RegExpSearchRule(Song.path,q)

        return self.search(rule)

    def getArtists(self):
        """ get a list of artists within the database."""
        with self.sqlstore.conn:
            c = self.sqlstore.conn.cursor()
            cols = ['uid','artist','count']
            return self.artist_db._select_columns(c, cols)

    def getAlbums(self,artistid):
        """ return all albums associated with a given artist id"""
        with self.sqlstore.conn:
            c = self.sqlstore.conn.cursor()
            cols = ['uid','album','count']
            return self.album_db._select_columns(c, cols, artist=artistid)

    def getArtistAlbums(self):
        """ returns a list of all artist and album names

        format is
            list-of-tuple
        where each tuple is a:
            (string, list-of-string)
        which denotes the artist name and associated albums

        output is in sorted order.

        This function also serves as an integrity check for the database,
        It will find inconsistencies due to a bug in update().
        """
        root = []
        map = {}
        errors = []

        with self.sqlstore.conn:
            c = self.sqlstore.conn.cursor()

            c.execute("SELECT uid, artist from artists ORDER BY sortkey COLLATE NOCASE" )
            items = c.fetchmany()
            while items:
                for uid,art in items:
                    elem = (art,list())
                    map[uid] = elem
                    root.append(elem)
                items = c.fetchmany()

            c.execute("SELECT uid, artist, album from albums ORDER BY album COLLATE NOCASE" )
            items = c.fetchmany()
            while items:
                for uid, art,abm in items:
                    if art in map:
                        map[art][1].append(abm)
                    else:
                        errors.append( (uid,art,abm) )
                items = c.fetchmany()

        for err in errors:
            self.repairArtistAlbums(*err)

        return root

    def repairArtistAlbums(self, uid, art, abmstr):
        """
        """
        sys.stderr.write("Missing Artist Info for %d:%d\n"%(uid,art))

        return

        rule = ExactSearchRule(Song.album,abmstr)
        songs = sql_search( self.song_view, rule, case_insensitive=False);
        artists = set([song[Song.artist] for song in songs])

        if len(artists) == 1:
            artist = list(artists)[0]
            res = self.sqlstore.conn.execute("SELECT uid from artists where artist==?",(artist,),)
            item = res.fetchone()
            if item is not None:
                artidx = item[0]
                self.sqlstore.conn.execute("UPDATE albums SET artist=? WHERE uid=?",(artidx,uid))
        else:
            for artist in artists:
                res = self.sqlstore.conn.execute("SELECT uid from artists where artist==?",(artist,),)
                items = res.fetchone()
                index = items[0]

                res = self.sqlstore.conn.execute("SELECT uid,count from albums where artist==?",(index,),)
                item = res.fetchone()
                if item is not None:
                    # there is already an entry for this element
                    pass
                else:
                    # create a new entry because one is missing
                    alb_index = -1
                    with self.sqlstore.conn:
                        c = self.sqlstore.conn.cursor()
                        alb_index = self.album_db._get_id_or_insert(c,
                            album=abmstr,
                            artist=index)
                    # update the count for the entry to be correct
                    rule = AndSearchRule([ ExactSearchRule(Song.artist,artist),
                                           ExactSearchRule(Song.album,abmstr) ])
                    songs = sql_search( self.song_view, rule, case_insensitive=False);
                    self.sqlstore.conn.execute.execute("UPDATE albums SET count=? WHERE uid=?",(len(songs),alb_index,))
            # delete the existing row, since it is not attached to any artist
            res = self.sqlstore.conn.execute("DELETE FROM albums WHERE uid==?",(uid,))

    def songPathHack(self, alternatives):

        songs = list(self.search(None))
        last = None
        print(len(songs))
        with self.sqlstore.conn:
            c = self.sqlstore.conn.cursor()
            for song in songs:
                old_path = song[Song.path]
                last, new_path = check_path_alternatives( \
                                    alternatives, old_path, last)
                if (new_path != old_path):
                    self._update_one(c, song[Song.uid], **{Song.path:new_path})

    def import_record(self, record):

        with self.sqlstore.conn as conn:
            c = conn.cursor()
            self._import_record(c,record)

    def _import_record(self, c, record):

        if record['column'] == Song.playtime:
            self.import_record_playtime(c,record)
        else:
            self.import_record_update(c,record)

    # TODO these should probably be moved to the Library()
    def import_record_playtime(self, c, record):
        """
        update playcount for a song given a record

        c: connection cursor associated with target library
        record: a history record
        """

        # experimental: insert record into THIS db
        k,v = zip(*record.items())
        s = ', '.join(str(x) for x in k)
        r = ('?,'*len(v))[:-1]
        fmt = "insert into %s (%s) VALUES (%s)"%("history",s,r)
        c.execute(fmt,list(v))

        #song = library.songFromId( record['uid'])
        date = record['date']
        uid = record['uid']

        c = self.sqlstore.conn.cursor()
        c.execute("SELECT playcount, frequency, last_played FROM songs WHERE uid=?",(uid,))
        item = c.fetchone()
        if item is None:
            raise ValueError( uid )
        playcount, frequency, last_played = item
        # only update frequency, last_played if the item is newer
        if date > last_played:
            d, freq = Song.calculateFrequency(playcount, frequency, last_played, date);
            c.execute("UPDATE songs SET playcount=playcount+1, frequency=?, last_played=? WHERE uid=?", \
                      (freq, date, uid))
        else:
            c.execute("UPDATE songs SET playcount=playcount+1 WHERE uid=?", (uid,))

    def import_record_update(self, c, record):
        """
        update column/value for uid given a record

        c: connection cursor associated with target library
        record: a history record
        """

        col=record['column']
        val=record['value']
        if col in Song.numberFields():
            new_value = {col:int(val)}
        else:
            new_value = {col:val}
        self._update_one(c, record['uid'], **new_value)
