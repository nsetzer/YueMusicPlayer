
from ftplib import FTP
import posixpath
from io import BytesIO,SEEK_SET

from .source import DataSource

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
        self.ftp.storbinary('STOR %s'%self.path, self.file)

    def __enter__(self):
        return self

    def __exit__(self,typ,val,tb):
        if typ is None:
            self.close()


class FTPSource(DataSource):
    """docstring for DirectorySource"""

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

    def root(self):
        return "/"

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
        if self.exists( path ):
            if self.isdir(path):
                self.ftp.rmd(path)
            else:
                self.ftp.remove(path)

    def open(self,path,mode):
        if mode=="wb":
            return FTPWriter(self.ftp,path)
        raise NotImplementedError(mode)

    def exists(self,path):
        p,n=posixpath.split(path)
        lst = set(self.listdir(p))
        return n in lst

    def isdir(self,path):
        return self.ftp.size(path) is None

    def mkdir(self,path):
        self.ftp.mkd(path)

    def split(self,path):
        return posixpath.split(path)

    def splitext(self,path):
        return posixpath.splitext(path)

    def stat_fast(self,path):
        # not fast for thus file system :(
        size = self.ftp.size(path)
        result = {
            "size"  : size or 0,
            "isDir" : size is None ,
        }
        return result

    def getExportPath(self,path):
        return path # nothing to do
