
import sqlite3
import sys
"""
todo: read sqlalchemy
http://docs.sqlalchemy.org/en/rel_1_0/core/tutorial.html
"""
import re
import shutil

def regexp(expr, item):
    # TODO: memoize expr
    # TODO: IGNORECASE only on windows
    reg = re.compile(expr,re.IGNORECASE)
    return reg.search(item) is not None

class SQLStore(object):
    """docstring for SQLStore"""
    def __init__(self, filepath):
        super(SQLStore, self).__init__()
        self.filepath = filepath
        self.conn = sqlite3.connect(filepath)

        self.conn.create_function("REGEXP", 2, regexp)

        with self.conn:
            c = self.conn.cursor()
            sql = 'CREATE TABLE if not exists yue_version (name text, version integer)'
            c.execute(sql)
            c.execute("SELECT version from yue_version WHERE name==?",("schema",))
            results = c.fetchone()
            if results is None:
                c.execute("INSERT INTO yue_version (name,version) VALUES (?,?)",("schema",1))

    def close(self):
        self.conn.close()

    def reopen(self):
        # return a copy of the sqlstore,
        # use to access from another thread
        return SQLStore( self.filepath )

    def backup(self, backup_path):

        #https://bugs.python.org/issue28518
        #https://hg.python.org/cpython/rev/284676cf2ac8
        # a bug was introduced in sept 2016 affecting 3.6.0
        # when this bug is present, perform an unsafe backup
        # I believe the begin immediate is only to lockdown
        # other processes which may be using th db
        safe_backup = sys.version_info[:3]!=(3,6,0)

        with self.conn:
            cursor = self.conn.cursor()
            if safe_backup:
                cursor.execute('BEGIN IMMEDIATE')
            sys.stdout.write("saving database to `%s`\n"%backup_path)
            shutil.copyfile(self.filepath, backup_path)
            if safe_backup:
                cursor.execute('END')
            #cursor.execute('rollback')

    def path(self):
        return self.filepath

    def execute(self,sqlstr,sqlargs):
        res = self.conn.execute(sqlstr,sqlargs)
        item = res.fetchone()
        while item is not None:
            yield item
            item = res.fetchone()

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

    def count(self):
        with self.store.conn:
            c = self.store.conn.cursor()
            return self._count(c)

    def _count(self,cursor):
        cursor.execute("select COUNT(*) from %s"%self.name)
        item = cursor.fetchone()
        if item is None:
            raise ValueError()
        return item[0]

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

    def get(self, key):
        with self.store.conn:
            c = self.store.conn.cursor()
            item = self._get(c, key)
            return dict(zip(self.column_names, item))

    def _get(self, cursor, key):
        cursor.execute("select * from %s where uid=?" % self.name, [key])
        item = cursor.fetchone()
        if item is None:
            raise KeyError(key)
        return item

    def get_id_or_insert(self,**kwargs):
        with self.store.conn:
            c = self.store.conn.cursor()
            return self._get_id_or_insert( c, **kwargs )

    def _get_id_or_insert(self, cursor, **kwargs):
        k,v = zip(*kwargs.items())
        s = ' AND '.join('%s=?'%x for x in k)
        sql = "select uid from %s where (%s)"%(self.name,s)
        cursor.execute( sql, v)
        item = cursor.fetchone()
        if item is None:
            return self._insert(cursor,**kwargs)
        return item[0]

    def select(self,**kwargs):
        with self.store.conn:
            c = self.store.conn.cursor()
            return self._select(c, **kwargs)

    def _select(self, cursor, **kwargs):
        k,v = zip(*kwargs.items())
        s = ', '.join('%s=?'%x for x in k)
        sql = "select * from %s WHERE (%s)"%(self.name,s)
        cursor.execute(sql,v)
        item = cursor.fetchone()
        while item is not None:
            yield dict(zip(self.column_names,item))
            item = cursor.fetchone()

    def _select_columns(self, cursor, cols, **kwargs):
        v = []
        c = ', '.join( cols )
        sql = "select %s from %s"%(c, self.name)
        if kwargs:
            k,v = zip(*kwargs.items())
            s = 'AND '.join('%s=?'%x for x in k)
            sql += " WHERE (%s)"%s
        cursor.execute(sql,v)
        item = cursor.fetchone()
        while item is not None:
            yield dict(zip(cols,item))
            item = cursor.fetchone()

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
            cols = ', '.join(self.column_names)
            c.execute("select %s from %s"%(cols,self.name))
            item = c.fetchone()
            while item is not None:
                yield dict(zip(self.column_names,item))
                item = c.fetchone()

    def __iter__(self):
        return self.iter()

    def query(self,query,*values):
        with self.store.conn:
            c = self.store.conn.cursor()
            c.execute(query,values)
            item = c.fetchone()
            while item is not None:
                yield dict(zip(self.column_names,item))
                item = c.fetchone()