
from ftplib import FTP,error_perm, all_errors
import posixpath
from io import BytesIO,SEEK_SET

from .source import DataSource
import sys
import re

reftp = re.compile('ftp\:\/\/(([^@:]+)?:?([^@]+)?@)?([^:]+)(:[0-9]+)?\/(.*)')

def parseFTPurl( url ):
    m = reftp.match( url )
    if m:
        g = m.groups()
        return {
            "username" : g[1] or "",
            "password" : g[2] or "",
            "hostname" : g[3] or "",
            "port"     : int(g[4][1:]) if g[4] else 21, # default ftp port
            "path"     : g[5] or "/",
        }
    raise ValueError("invalid: %s"%url)

def utf8_fix(s):
    return ''.join([ a if ord(a)<128 else "%02X"%ord(a) for a in s])

class FTPWriter(object):
    """docstring for FTPWriter"""
    def __init__(self, ftp, path):
        super(FTPWriter, self).__init__()
        self.ftp = ftp
        self.path = path
        self.file = BytesIO()

    def write(self,data):
        return self.file.write(data)

    def seek(self,pos,whence=SEEK_SET):
        return self.file.seek(pos,whence)

    def tell(self):
        return self.file.tell()

    def close(self):
        self.file.seek(0)
        text = "STOR " + utf8_fix(self.path)
        self.ftp.storbinary(text, self.file)

    def __enter__(self):
        return self

    def __exit__(self,typ,val,tb):
        if typ is None:
            self.close()

class FTPReader(object):
    """docstring for FTPWriter"""
    def __init__(self, ftp, path):
        super(FTPReader, self).__init__()
        self.ftp = ftp
        self.path = path
        self.file = BytesIO()

        # open the file
        text = "RETR " + utf8_fix(self.path)
        self.ftp.retrbinary(text, self.file.write)
        self.file.seek(0)

    def read(self,n=None):
        return self.file.read(n)

    def seek(self,pos,whence=SEEK_SET):
        return self.file.seek(pos,whence)

    def tell(self):
        return self.file.tell()

    def close(self):
        self.file.close()

    def __enter__(self):
        return self

    def __exit__(self,typ,val,tb):
        if typ is None:
            self.close()

class FTPSource(DataSource):
    """
    there is some sort of problem with utf-8/latin-1 and ftplib

    storbinary must accepts a STRING, since it builds a cmd and add
    the CRLF to the input argument using the plus operator.

    the command fails when given unicode text (ord > 127) and also
    fails whenm given a byte string.
    """

    # TODO: turn this into a directory generator
    # which first loads the directory, then loops over
    # loaded items.

    # TODO: on windows we need a way to view available
    # drive letters
    def __init__(self, host, port, username="", password=""):
        super(FTPSource, self).__init__()

        self.ftp = FTP()
        self.ftp.connect(host,port)
        self.ftp.login(username,password)

        self.hostname = "%s:%d"%(host,port)

    def root(self):
        return "/"

    def close(self):

        try:
            self.ftp.quit()
        except all_errors as e:
            sys.stderr.write("Error Closing FTP connection\n")
            sys.stderr.write("%s\n"%e)

        super().close()

    def fix(self, path):
        return utf8_fix(path)

    def join(self,*args):
        return posixpath.join(*args)

    def breakpath(self,path):
        return [ x for x in path.replace("/","\\").split("\\") if x ]

    def relpath(self,path,base):
        return posixpath.relpath(path,base)

    def normpath(self,path,root=None):
        if root and not path.startswith("/"):
            path = posixpath.join(root,path)
        return posixpath.normpath( path )

    def listdir(self,path):
        return self.ftp.nlst(path)

    def parent(self,path):
        # TODO: if path is C:\\ return empty string ?
        # empty string returns drives
        p,_ = posixpath.split(path)
        return p

    def move(self,oldpath,newpath):
        self.ftp.rename(oldpath,newpath)

    def delete(self,path):
        # todo support removing directory rmdir()
        path = utf8_fix(path)
        if self.exists( path ):
            if self.isdir(path):
                try:
                    self.ftp.rmd(path)
                except Exception as e:
                    print("ftp delete error: %s"%e)
            else:
                try:
                    self.ftp.delete(path)
                except Exception as e:
                    print("ftp delete error: %s"%e)

    def open(self,path,mode):
        if mode=="wb":
            return FTPWriter(self.ftp,path)
        elif mode=="rb":
            return FTPReader(self.ftp,path)
        raise NotImplementedError(mode)

    def exists(self,path):
        path = utf8_fix(path)
        p,n=posixpath.split(path)
        lst = set(self.listdir(p))
        return n in lst

    def isdir(self,path):
        path = utf8_fix(path)
        try:
            return self.ftp.size(path) is None
        except error_perm:
            # TODO: to think about more later,
            # under my use-case, I'm only asking if a path is a directory
            # if I Already think it exists. Under the current FTP impl
            # ftp.size() fails for various reasons unless the file exists
            # and is an accessable file. I can infer that a failure to
            # determine the size means that the path is a directory,
            # but this does not hold true under other use cases.
            # I can't cache listdir calls, but if I could, then I could
            # use that to determine if the file exists
            return True#self.exists( path )

    def mkdir(self,path):
        # this is a really ugly quick and dirty solution
        path = utf8_fix(path)
        if not self.exists(path):
            p = self.parent( path )
            try:
                if not self.exists(p):
                    self.ftp.mkd( p )
                self.ftp.mkd(path)
            except Exception as e:
                print("ftp mkd error: %s"%e)


    def split(self,path):
        return posixpath.split(path)

    def splitext(self,path):
        return posixpath.splitext(path)

    def stat_fast(self,path):
        # not fast for thus file system :(
        try:
            size = self.ftp.size(path)
        except error_perm:
            size = None

        result = {
            "size"  : size or 0,
            "isDir" : size is None ,
        }
        return result

    def getExportPath(self,path):
        return self.hostname+path
