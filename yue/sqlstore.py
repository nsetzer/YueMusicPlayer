
import os
import sqlite3

class SQLStore(object):
    """docstring for SQLStore"""
    def __init__(self, filename):
        super(SQLStore, self).__init__()
        self.filename = filename
        self.conn = sqlite3.connect(filename)

class SQLView(object):
    """docstring for SQLView"""
    def __init__(self, store, name, columns):
        super(SQLView, self).__init__()
        self.store = store
        self.name = name
        self.columns = columns
        self.column_names = [x[0] for x in columns]
        self.create( columns )

    def create(self, columns):
        with self.store.conn:
            field = ','.join(a+' '+b for a,b in columns)
            self.store.conn.execute('''CREATE TABLE if not exists {} ({})'''.format(self.name,field))

    def drop(self):
        with self.store.conn:
            self.store.conn.execute('''drop table if exists %s'''%self.name)

    def get(self,key):
        with self.store.conn:
            c = self.store.conn.cursor()
            c.execute("select * from %s where uid=?"%self.name,[key,])
            item = c.fetchone()
            if item is None:
                raise KeyError(key)
            return dict(zip(self.column_names,item))

    def insert(self,**kwargs):
        with self.store.conn:
            c = self.store.conn.cursor()
            s = ', '.join('%s'%x for x in kwargs.keys())
            r = ('?,'*len(kwargs))[:-1]
            fmt = "insert into %s (%s) VALUES (%s)"%(self.name,s,r)
            res = c.execute(fmt,list(kwargs.values()))
            return res.lastrowid

    def update(self,key,**kwargs):
        with self.store.conn:
            c = self.store.conn.cursor()
            s = ', '.join('%s=?'%x for x in kwargs.keys())
            fmt="update %s set %s WHERE uid=%s"%(self.name,s,key)
            c.execute(fmt,list(kwargs.values()))

    def iter(self):
        with self.store.conn:
            c = self.store.conn.cursor()
            c.execute("select * from %s"%self.name)
            item = c.fetchone()
            while item is not None:
                yield dict(zip(self.column_names,item))
                item = c.fetchone()
