
import time
import os
import sys
from datetime import datetime

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

def days_elapsed( epochtime ):
    t1 = datetime.utcfromtimestamp( epochtime )
    delta = datetime.now() - t1
    return delta.days

def string_escape(string):
    """escape special characters in a string for use in search"""
    return string.replace("\\","\\\\").replace("\"","\\\"")

def string_quote(string):
    """quote a string for use in search"""
    return "\""+string.replace("\\","\\\\").replace("\"","\\\"")+"\""

def backupDatabase(sqlstore,backupdir=".",maxsave=6,force=False):
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