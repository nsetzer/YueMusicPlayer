
# single instance pattern
# contains boolean : save history true false
# mimic update pattern

from .search import SearchGrammar, BlankSearchRule, AndSearchRule, \
    LessThanEqualSearchRule, GreaterThanEqualSearchRule, \
    sql_search, sqlFromRule, ParseError
from yue.core.song import Song
from yue.core.search import SearchRule
from yue.core.sqlstore import SQLTable, SQLView
from calendar import timegm
import time

import sys
isPython3 = sys.version_info[0]==3
if isPython3:
    unicode = str

"""
visited = set()
duplicates = []

for item in History.search('date < 3w'):
    if item['date'] in visited:
        duplicates.append(item);
    else:
        visited.add(item['date'])

print(len(duplicates))

#for item in duplicates:
#    song = Library.songFromId(item['uid'])
#    Library.update(item['uid'],playcount=song['playcount']-1);
#    History.delete(item)

"""
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
        self.enabled_log = False
        self.enabled_update = False


        self.grammar = HistorySearchGrammar( )
        self.raw_grammar = HistorySearchGrammar( )
        self.raw_grammar.text_fields = ["column", "value"]

    def reopen(self):
        # return a copy of the library,
        # use to access from another thread
        return History( self.sqlstore.reopen() )

    @staticmethod
    def init( sqlstore ):
        History.__instance = History( sqlstore )

    @staticmethod
    def instance():
        return History.__instance

    def setLogEnabled(self, b):
        """ enable recording of playback events"""
        temp = self.enabled_log
        self.enabled_log = bool(b)
        return temp

    def setUpdateEnabled(self, b):
        """ enable recording of record changes """
        temp = self.enabled_update
        self.enabled_update = bool(b)
        return temp

    def isLogEnabled(self):
        return self.enabled_log

    def isUpdateEnabled(self):
        return self.enabled_update

    def __len__(self):
        return self.db.count()

    def size(self):
        return self.db.count()

    def update(self, c, uid, **kwargs):

        if not self.enabled_update:
            return

        date = timegm(time.localtime(time.time()))
        data = {
            "date" : date,
            "uid"  : uid,
        }
        for col,val in kwargs.items():
            # don't record changes for path, since that will overwrite
            # the path on import - bad!
            if col == Song.path:
                continue;
            data['column'] = col
            data['value'] = str(val)
            self.db._insert(c,**data)

    def incrementPlaycount(self, c, uid, date):

        if not self.enabled_log:
            return

        kwargs = {
            "date": date,
            "uid": uid,
            "column": Song.playtime
        }
        self.db._insert(c, **kwargs)

    def export(self, rule=None, case_insensitive=True, orderby=None, reverse=False, limit=None, offset=0):
        """
        this returns raw database results from this History Database
        see search(), which returns values from the History View, which
        would be better for displaying to a user
        """
        if rule is None:
            rule = BlankSearchRule()
        elif isinstance(rule, (str, unicode)):
            rule = self.raw_grammar.ruleFromString(rule)
            limit = self.raw_grammar.getMetaValue("limit", limit)
            offset = self.raw_grammar.getMetaValue("offset", offset)
        elif not isinstance(rule, SearchRule):
            raise ParseError("invalid rule type: %s"%type(rule))

        if isinstance(rule,(str,unicode)):
            raise ParseError("invalid rule type: %s"%type(rule))
        if orderby is not None:
            if not isinstance( orderby, (list,tuple)):
                orderby = [ orderby, ]

        return sql_search( self.db, rule, case_insensitive, orderby, reverse, limit, offset )

    def export_date_range(self, start, end=None):
        """
        start, end:  unix timestamps

        import datetime
        e=int(datetime.datetime.now().timestamp())
        s=e-(1000*60)
        data=History.export_date_range(s)
        _max=max((r['date'] for r in data))
        _min=min((r['date'] for r in data))
        print(_min,_max,_max-_min)

        """
        rule = GreaterThanEqualSearchRule("date", start, type_=int)
        if end is not None:
            rule = AndSearchRule([rule,
                LessThanEqualSearchRule("date", end, type_=int)])
        return sql_search(self.db, rule)


    def _import(self,records):
        """
        see Library() for a history import function that will update the library.
        """

        with self.sqlstore.conn:
            c = self.sqlstore.conn.cursor()
            for rec in records:
                self.db._insert(c,**rec)

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

    def search(self, rule , case_insensitive=True, orderby=None, reverse = False, limit = None, offset=0):
        if rule is None:
            rule = BlankSearchRule();
        elif isinstance(rule,(str,unicode)):
            rule = self.grammar.ruleFromString( rule )
            limit = self.grammar.getMetaValue("limit",limit)
            offset = self.grammar.getMetaValue("offset",offset)

        if orderby is not None:
            if not isinstance( orderby, (list,tuple)):
                orderby = [ orderby, ]

        return sql_search( self.view, rule, case_insensitive, orderby, reverse, limit, offset )

    def clear(self):
        self.db.store.conn.execute("DELETE FROM history")

class HistorySearchGrammar(SearchGrammar):
    """docstring for HistorySearchGrammar"""

    def __init__(self):
        super(HistorySearchGrammar, self).__init__()

        # [ "uid", "date", "column", "value", "artist", "album", "title" ]
        self.text_fields = {'column', 'artist','album','title'}
        self.date_fields = {'date',}

        self.columns = {self.all_text, "uid", "date", 'column', 'artist','album','title', }
        self.shortcuts = {
                        "art"    : "artist", # copied from Song
                        "artist" : "artist",
                        "abm"    : "album",
                        "alb"    : "album",
                        "album"  : "album",
                        "ttl"    : "title",
                        "tit"    : "title",
                        "title"  : "title",
                        "data"   : "column",
                        "action" : "column",
                        "id"     : "uid",
                    }

    def translateColumn(self,colid):
        if colid in self.shortcuts:
            return self.shortcuts[colid]
        if colid in self.columns:
            return colid
        raise ParseError("Invalid column name `%s`"%colid)
