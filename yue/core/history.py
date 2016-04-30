
# single instance pattern
# contains boolean : save history true false
# mimic update pattern

from .search import SearchGrammar, BlankSearchRule, sql_search, ParseError
from yue.core.song import Song
from yue.core.sqlstore import SQLTable, SQLView
from calendar import timegm
import time

import sys
isPython3 = sys.version_info[0]==3
if isPython3:
    unicode = str

class History(object):
    """docstring for Library"""
    __instance = None
    def __init__(self, sqlstore):
        super(History, self).__init__()
        fields = [
            ("date","INTEGER"),
            ("uid","INTEGER"),
            ("column","text"),
            ("value","text"),
        ]

        self.db = SQLTable( sqlstore ,"history", fields)


        #SELECT s.uid, h.date, h.column, h.value, a.artist, b.album, s.title
        #FROM songs s, artists a, albums b, history h
        #WHERE s.uid=h.uid AND a.uid = s.artist AND b.uid = s.album

        viewname = "history_view"
        colnames = [ "uid", "date", "column", "value", "artist", "album", "title" ]
        cols = [ 's.uid', 'h.date', 'h.column', 'h.value', 'a.artist', 'b.album', 's.title']
        cols = ', '.join(cols)
        tbls = "songs s, artists a, albums b, history h"
        where = "s.uid=h.uid AND a.uid = s.artist AND b.uid = s.album"
        sql = """CREATE VIEW IF NOT EXISTS {} as SELECT {} FROM {} WHERE {}""".format(viewname,cols,tbls,where)

        self.view = SQLView( sqlstore, viewname, sql, colnames)
        self.sqlstore = sqlstore
        self.enabled = False

        self.grammar = HistorySearchGrammar( )

    @staticmethod
    def init( sqlstore ):
        History.__instance = History( sqlstore )

    @staticmethod
    def instance():
        return History.__instance

    def setEnabled(self, b):
        self.enabled = bool(b)

    def isEnabled(self):
        return self.enabled

    def __len__(self):
        return self.db.count()

    def size(self):
        return self.db.count()

    def update(self,c, uid,**kwargs):

        if not self.enabled:
            return

        date = timegm(time.localtime(time.time()))
        data = {
            "date" : date,
            "uid"  : uid,
        }
        for col,val in kwargs.items():
            data['column'] = col
            data['value'] = val
            self.db._insert(c,**data)

    def incrementPlaycount(self, c, uid, date):

        if not self.enabled:
            return

        kwargs = {
            "date" : date,
            "uid"  : uid,
            "column" : Song.playtime
        }
        self.db._insert(c,**kwargs)

    def export(self):

        with self.sqlstore.conn:
            c = self.sqlstore.conn.cursor()
            c.execute("SELECT date,uid,column,value FROM history ORDER BY date")

            item = c.fetchone()
            while item is not None:
                yield dict(zip(self.db.column_names,item))
                item = c.fetchone()

    def import_record(self, c, record):


        if record['column'] == Song.playtime:
            self.import_playtime(c,record)
        else:
            self.import_update(c,record)

    # TODO" these should probably be moved to the Library()
    def import_playtime(self, c, record):
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

    def import_update(self, c, record):
        # update column/value for uid given a record
        pass


    def delete(self,records_lst):
        """ delete a record, or a list of records
        """
        lst = records_lst
        if isinstance(records_lst,dict):
            lst = [records_lst, ]

        with self.sqlstore.conn:
            c = self.sqlstore.conn.cursor()

            for record in lst:
                self._delete(c,record)

    def _delete(self,c,record):
        date = record['date']
        uid = record['uid']
        c.execute("DELETE from history where uid=? and date=?",(uid,date))

    def search(self, rule , case_insensitive=True, orderby=None, reverse = False, limit = None):

        if rule is None:
            rule = BlankSearchRule();
        elif isinstance(rule,(str,unicode)):
            rule = self.grammar.ruleFromString( rule )
        else:
            raise ParseError("invalid rule type: %s"%type(rule))
        if isinstance(rule,(str,unicode)):
            raise ParseError("fuck. invalid rule type: %s"%type(rule))
        if orderby is not None:
            if not isinstance( orderby, (list,tuple)):
                orderby = [ orderby, ]

        echo = False
        return sql_search( self.view, rule, case_insensitive, orderby, reverse, limit, echo )


class HistorySearchGrammar(SearchGrammar):
    """docstring for HistorySearchGrammar"""

    def __init__(self):
        super(HistorySearchGrammar, self).__init__()

        # [ "uid", "date", "column", "value", "artist", "album", "title" ]
        self.text_fields = {'column', 'artist','album','title'}
        self.date_fields = {'date',}

        self.columns = {self.all_text, "uid", "date", 'column', 'artist','album','title', }
        self.col_shortcuts = {
                                "art"    : "artist", # copied from Song
                                "artist" : "artist",
                                "abm"    : "album",
                                "alb"    : "album",
                                "album"  : "album",
                                "ttl"    : "title",
                                "tit"    : "title",
                                "title"  : "title",
                                "data"   : "column",
                            }

    def translateColumn(self,colid):
        if colid in self.col_shortcuts:
            return self.col_shortcuts[colid]
        if colid in self.columns:
            return colid
        raise ParseError("Invalid column name `%s`"%colid)
