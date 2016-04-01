

from .sqlstore import SQLTable, SQLView

K_STR=1 # a single string value
K_INT=2 # a numeric field
K_CSV=3 #

class Settings(object):
    """Application Settings backed by a database

    provides a basic key/value store for Strings, Integers, and List-Of-Strings
    """
    __instance = None

    def __init__(self, sqlstore):
        super(Settings, self).__init__()

        self.sqlstore = sqlstore

        settings = [
            ('uid','INTEGER PRIMARY KEY AUTOINCREMENT'),
            ('key',"TEXT"),
            ('kind',"INTEGER"),
        ]
        self.dbsettings = SQLTable( sqlstore ,"settings", settings)

        str_settings = [
            ("uid","INTEGER"),
            ("value","TEXT"),
        ]
        self.dbstr = SQLTable( sqlstore ,"setstr", str_settings)

        int_settings = [
            ("uid","INTEGER"),
            ("value","INTEGER"),
        ]
        self.dbint = SQLTable( sqlstore ,"setint", int_settings)

        csv_settings = [
            ("uid","INTEGER"),
            ("idx","INTEGER"),
            ("value","TEXT"),
        ]
        self.dbcsv = SQLTable( sqlstore ,"setcsv", csv_settings)

    @staticmethod
    def init( sqlstore ):
        Settings.__instance = Settings( sqlstore )

    @staticmethod
    def instance():
        return Settings.__instance

    def __getitem__(self,key):
        with self.sqlstore.conn:
            c = self.sqlstore.conn.cursor()
            c.execute("SELECT uid,kind FROM settings WHERE key=?",(key,))
            result = c.fetchone()
            if not result:
                raise KeyError(key)
            uid,kind = result

            if kind == K_STR:
                return self._get(c,"setstr",uid)
            elif kind == K_INT:
                return self._get(c,"setint",uid)
            elif kind == K_CSV:
                return self._get_list(c,uid)

            raise TypeError(kind)

    def _get(self,c,tbl,uid):
        c.execute("SELECT value FROM %s WHERE uid=?"%tbl,(uid,))
        value = c.fetchone()
        return value[0]

    def _get_list(self,c,uid):
        result = []
        c.execute("SELECT value FROM setcsv WHERE uid=? ORDER BY idx",(uid,))
        items = c.fetchmany()
        while items:
            for item in items:
                result.append( item[0] )
            items = c.fetchmany()
        return result

    def getDefault(self,key,default):
        with self.sqlstore.conn:
            c = self.sqlstore.conn.cursor()
            c.execute("SELECT uid,kind FROM settings WHERE key=?",(key,))
            result = c.fetchone()
            if not result:
                return default
            uid,kind = result

            if kind == K_STR:
                return self._get(c,"setstr",uid)
            elif kind == K_INT:
                return self._get(c,"setint",uid)
            elif kind == K_CSV:
                return self._get_list(c,uid)

            raise TypeError(kind)

    def __setitem__(self,key,value):

        if isinstance(value,str):
            self._set("setstr",K_STR,key,value)
        elif isinstance(value,int):
            self._set("setint",K_INT,key,value)
        elif isinstance(value,(list,tuple,set)):
            self._set_list(key,value)
        else:
            raise TypeError(key)

    def _set(self,tbl,kind,key,value,overwrite=True):
        with self.sqlstore.conn:
            c = self.sqlstore.conn.cursor()
            c.execute("SELECT uid,kind FROM settings WHERE key=?",(key,))
            result = c.fetchone()
            if not result:
                result = c.execute("INSERT INTO settings (key,kind)  VALUES (?,?)",(key,kind))
                uid = result.lastrowid
                c.execute("INSERT INTO %s (uid,value)  VALUES (?,?)"%tbl,(uid,value))
            else:
                uid,skind = result
                if not overwrite:
                    return

                if skind != kind:
                    raise ValueError(type(value))

                c.execute("UPDATE %s SET value=? WHERE uid=?"%tbl,(value,uid,))

    def _set_list(self,key,data,overwrite=True):
        with self.sqlstore.conn:
            c = self.sqlstore.conn.cursor()
            c.execute("SELECT uid, kind FROM settings WHERE key=?",(key,))
            result = c.fetchone()
            if not result:
                result = c.execute("INSERT INTO settings (key,kind)  VALUES (?,?)",(key,K_CSV))
                uid = result.lastrowid
            else:
                uid, skind = result
                if not overwrite:
                    return

                if skind != K_CSV:
                    raise ValueError(type(data))

            # remove any preexisting list
            c.execute("DELETE from setcsv where (uid=?)",(uid,))

            for idx, item in enumerate(data):
                c.execute("INSERT INTO setcsv (uid,idx,value)  VALUES (?,?,?)",(uid,idx,item))

    def setDefault(self,key,value):
        """ set the value iff it does not exist"""

        if isinstance(value,str):
            self._set("setstr",K_STR,key,value,False)
        elif isinstance(value,int):
            self._set("setint",K_INT,key,value,False)
        elif isinstance(value,(list,tuple)):
            self._set_list(key,value,False)
        else:
            raise TypeError(key)

    def keys(self):
        """ generator function returns all settings keys """
        with self.sqlstore.conn:
            c = self.sqlstore.conn.cursor()
            c.execute("SELECT key FROM settings")
            results = c.fetchmany()
            while results:
                for item in results:
                    yield item[0]
                results = c.fetchmany()

    def items(self):
        """ generator function returns all settings keys, values """
        with self.sqlstore.conn:
            c = self.sqlstore.conn.cursor()
            c2 = self.sqlstore.conn.cursor()
            c.execute("SELECT uid,key,kind FROM settings")
            results = c.fetchmany()
            while results:
                for item in results:
                    uid,key,kind = item
                    value = None

                    if kind == K_STR:
                        value = self._get(c2,"setstr",uid)
                    elif kind == K_INT:
                        value = self._get(c2,"setint",uid)
                    elif kind == K_CSV:
                        value = self._get_list(c2,uid)

                    yield (key,value)

                results = c.fetchmany()
