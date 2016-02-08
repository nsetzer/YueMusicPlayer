
import sqlite3

"""
todo: read sqlalchemy
http://docs.sqlalchemy.org/en/rel_1_0/core/tutorial.html
"""

class SQLStore(object):
    """docstring for SQLStore"""
    def __init__(self, filename):
        super(SQLStore, self).__init__()
        self.filename = filename
        self.conn = sqlite3.connect(filename)

    def close(self):
        self.conn.close()

class SQLTable(object):
    """docstring for SQLTable"""
    def __init__(self, store, name, columns, foreign_keys=None):
        super(SQLTable, self).__init__()
        self.store = store
        self.name = name
        self.columns = columns
        self.foreign_keys = foreign_keys
        self.column_names = [x[0] for x in columns]
        self.create( columns )

    def conn(self):
        """ return a reference to the db connection """
        return self.store.conn

    def create(self, columns):
        with self.store.conn:
            field = ','.join(a+' '+b for a,b in columns)
            if self.foreign_keys is not None:
                field += ", " + ', '.join(self.foreign_keys)
            sql = '''CREATE TABLE if not exists {} ({})'''.format(self.name,field)
            self.store.conn.execute(sql)

    def drop(self):
        with self.store.conn:
            self.store.conn.execute('''drop table if exists %s'''%self.name)

    def get(self,key):
        with self.store.conn:
            c = self.store.conn.cursor()
            item = self._get( c, key )
            return dict(zip(self.column_names,item))

    def _get(self, cursor, key):
        cursor.execute("select * from %s where uid=?"%self.name,[key,])
        item = cursor.fetchone()
        if item is None:
            raise KeyError(key)
        return item

    def get_id_or_insert(self,**kwargs):
        with self.store.conn:
            c = self.store.conn.cursor()
            return self._get_id_or_insert( c, **kwargs )

    def _get_id_or_insert(self, cursor, **kwargs):

        #f = ','.join(fields)
        k = ', '.join('%s=?'%x for x in kwargs.keys())
        v = list(kwargs.values())
        sql = "select uid from %s where %s"%(self.name,k)
        cursor.execute( sql, v)
        item = cursor.fetchone()
        if item is None:
            return self._insert(cursor,**kwargs)
        return item[0]

    def select(self,**kwargs):
        with self.store.conn:
            c = self.store.conn.cursor()
            s = ', '.join('%s=?'%x for x in kwargs.keys())
            fmt = "select * from %s WHERE %s"%(self.name,s)
            c.execute(fmt,list(kwargs.values()))
            item = c.fetchone()
            while item is not None:
                yield dict(zip(self.column_names,item))
                item = c.fetchone()

    def query(self,query,*values):
        with self.store.conn:
            c = self.store.conn.cursor()
            c.execute(query,values)
            item = c.fetchone()
            while item is not None:
                yield dict(zip(self.column_names,item))
                item = c.fetchone()

    def insert(self,**kwargs):
        with self.store.conn:
            c = self.store.conn.cursor()
            return self._insert(c, **kwargs)

    def _insert(self, cursor, **kwargs):
        s = ', '.join('%s'%x for x in kwargs.keys())
        r = ('?,'*len(kwargs))[:-1]
        fmt = "insert into %s (%s) VALUES (%s)"%(self.name,s,r)
        res = cursor.execute(fmt,list(kwargs.values()))
        return res.lastrowid

    def update(self,key,**kwargs):
        with self.store.conn:
            c = self.store.conn.cursor()
            self._update(c,key,**kwargs)

    def _update(self,cursor, key, **kwargs):
        s = ', '.join('%s=?'%x for x in kwargs.keys())
        fmt="update %s set %s WHERE uid=%s"%(self.name,s,key)
        cursor.execute(fmt,list(kwargs.values()))

    def iter(self):
        with self.store.conn:
            c = self.store.conn.cursor()
            c.execute("select * from %s"%self.name)
            item = c.fetchone()
            while item is not None:
                yield dict(zip(self.column_names,item))
                item = c.fetchone()


class SQLView(object):
    """docstring for SQLTable"""
    def __init__(self, store, name, sql, column_names):
        """
        name : sql name of the view
        sql : sql that can create the view if needed
        column_names : names of each column in the view
        """
        super(SQLView, self).__init__()
        self.store = store
        self.name = name
        self.column_names = column_names

        self.create(sql)

    def create(self, sql):
        with self.store.conn:
            self.store.conn.execute(sql)

    def get(self,key):
        with self.store.conn:
            c = self.store.conn.cursor()
            item = self._get( c, key )
            return dict(zip(self.column_names,item))

    def _get(self, cursor, key):
        cursor.execute("select * from %s where uid=?"%self.name,[key,])
        item = cursor.fetchone()
        if item is None:
            raise KeyError(key)
        return item

    def iter(self):
        with self.store.conn:
            c = self.store.conn.cursor()
            c.execute("select * from %s"%self.name)
            item = c.fetchone()
            while item is not None:
                yield dict(zip(self.column_names,item))
                item = c.fetchone()

    def query(self,query,*values):
        with self.store.conn:
            c = self.store.conn.cursor()
            c.execute(query,values)
            item = c.fetchone()
            while item is not None:
                yield dict(zip(self.column_names,item))
                item = c.fetchone()