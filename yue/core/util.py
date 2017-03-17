
import time
import os
import sys
from datetime import datetime

from collections import OrderedDict

try:
    from functools import lru_cache
except:
    def lru_cache(maxsize=128):
        def lru_cache_decorator(func):
            cache = OrderedDict()
            def lru_cache_wrapper(*args):
                if args in cache:
                    return cache[args]
                result = func(*args);
                cache[args] = result
                while len(cache)>maxsize:
                    del cache[cache.keys()[0]]
                return result
            return lru_cache_wrapper
        return lru_cache_decorator


def with_metaclass(mcls):
    """ 2.7 and 3.5+ compatable metaclass decorator
    python2 uses a __metaclass__ class atribute whlie python3
    has a class level keyword argument.

    """
    # http://stackoverflow.com/questions/22409430/portable-meta-class-between-python2-and-python3
    def decorator(cls):
        body = vars(cls).copy()
        # clean out class body
        body.pop('__dict__', None)
        body.pop('__weakref__', None)
        return mcls(cls.__name__, cls.__bases__, body)
    return decorator

def format_date( unixTime ):
    """ format epoch time stamp as string """
    return time.strftime("%Y/%m/%d %H:%M", time.gmtime(unixTime))

def format_time( t ):
    """ format seconds as mm:ss """
    m,s = divmod(t,60)
    if m > 59:
        h,m = divmod(m,60)
        return "%d:%02d:%02d"%(h,m,s)
    else:
        return "%d:%02d"%(m,s)

def format_delta(t):
    """ format seconds as days:hh:mm:ss"""
    m,s = divmod(t,60)
    if m >= 60:
        h,m = divmod(m,60)
        if h > 23:
            d,h = divmod(h,24)
            return "%d:%02d:%02d:%02d"%(d,h,m,s)
        return "%d:%02d:%02d"%(h,m,s)
    return "%d:%02d"%(m,s)

byte_labels = ['B','KB','MB','GB']
def format_bytes(b):
    kb=1024
    for label in byte_labels:
        if b < kb:
            return "%d%s"%(b,label)
        b /= kb
    return "%d%s"%(b,byte_labels[-1])

def days_elapsed( epochtime ):
    t1 = datetime.utcfromtimestamp( epochtime )
    delta = datetime.now() - t1
    return delta.days

def format_mode_part(mode):
    s = ""
    s += "r" if 0x4&mode else "-"
    s += "w" if 0x2&mode else "-"
    s += "x" if 0x1&mode else "-"
    return s

def format_mode(mode):
    """ format unix permissions as string
    e.g. octal 0o755 to rwxr-xr-x
    """
    if isinstance(mode,int):
        u = format_mode_part(mode >> 6) # user
        g = format_mode_part(mode >> 3) # group
        o = format_mode_part(mode)      # other
        return u+g+o
    return ""

def string_escape(string):
    """escape special characters in a string for use in search"""
    return string.replace("\\","\\\\").replace("\"","\\\"")

def string_quote(string):
    """quote a string for use in search"""
    return "\""+string.replace("\\","\\\\").replace("\"","\\\"")+"\""

def backupDatabase(sqlstore,backupdir=".", maxsave=6, force=False):
    """
        note this has been hacked to suport xml formats
        save a copy of the current library to ./backup/
        only save if one has not been made today,
        delete old backups

        adding new music, deleting music, are good reasons to force backup
    """

    if not os.path.exists(backupdir):
        os.mkdir(backupdir)
        sys.stdout.write("backup directory created: `%s`\n"%backupdir)

    date = datetime.now().strftime("%Y-%m-%d")

    name = 'yue-backup-'
    fullname = name+date+'.db'
    fullpath = os.path.join(backupdir,fullname)

    if not force and os.path.exists(fullpath):
        return

    existing_backups = []
    dir = os.listdir(backupdir)
    for file in dir:
        if file.startswith(name) and file.endswith(".db"):
            existing_backups.append(file);

    newestbu = ""
    existing_backups.sort(reverse=True)
    if len(existing_backups) > 0:
        #remove old backups
        # while there are more than 6,
        # and one has not been saved today
        while len(existing_backups) > maxsave and existing_backups[0] != fullname:
            delfile = existing_backups.pop()
            sys.stdout.write("Deleting %s\n"%delfile)
            os.remove(os.path.join(backupdir,delfile))
        # record name of most recent backup, one backup per day unless forced
        newestbu = existing_backups[0]

    # todo: compare newestbu path to current
    # save a new backup
    sqlstore.backup( fullpath )

def check_path_alternatives( alternatives, path, last=None ):
    """
    enable alternative locations

    The library stores an absolute path.
    on some media (usb drive) the drive letter
    may change computer to computer
    """
    if last is not None:
        b,a = last
        res = update_path_alternatives(a,b,path)
        if res != None:
            return (b,a), new_path
    for a in alternatives:
        if path.startswith(a):
            for b in alternatives:
                if a == b:
                    continue
                res = update_path_alternatives(a,b,path)
                if res != None:
                    return (b,a), new_path
    return None, path

def update_path_alternatives(a,b,path):
    new_path = a + path[len(b):]
    if sys.platform != "nt":
        new_path = new_path.replace("\\",'/')
    print(b,a,new_path)
    if os.path.exists( new_path ):
        return new_path
    return None
