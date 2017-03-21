
import os,sys
from io import BytesIO
import posixpath

from .source import DataSource

class DictFSImpl(DataSource):
    """DictFSImpl builds a tree of dictionaries from
    a set of input filepaths, allowing basic file-like operations.
    """
    def __init__(self,):
        super(DictFSImpl, self).__init__()
        self._root = {}
        self.sep = "/"

    def load(self,namelist):
        self._root = {}
        for name in namelist:
            self.create(name)

    def _getDir(self,spath):
        record = self._root
        for name in spath:
            if not name: # allow repeated /
                continue
            if name not in record:
                record[name] = {}
            record = record[name]
        return record

    def _new(self,name,value):
        *path,name = name.split(self.sep)
        if name:
            rec = self._getDir(path)
            rec[name] = value

    def root(self):
        return "/"

    def parent(self,path):
        p,_ = self.split(path)
        return p

    def create(self,name):
        self._new(name,True)

    def mkdir(self,name):
        self._new(name,{})

    def relpath(self,path,base):
        return posixpath.relpath(path,base)

    def normpath(self,path,root=None):
        if root and not path.startswith("/"):
            path = os.path.join(root,path)
        return path

    def split(self,path):
        return posixpath.split(path)

    def splitext(self,path):
        return posixpath.splitext(path)

    def join(self,*items):
        return posixpath.join(*items)

    def exists(self,path):
        spath = path.split("/")[1:]
        record = self._getDir(spath[:-1])
        name = spath[-1]
        return not name or name in record

    def isdir(self,path):
        spath = path.split("/")[1:]
        if not spath or not spath[-1]:# ended with "/"
            return True
        record = self._getDir(spath[:-1])
        return spath[-1] in record and isinstance(record[spath[-1]],dict)

    def listdir(self,path):
        spath = path.split("/")[1:]
        record = self._getDir(spath)
        return list(record.keys())

    def delete(self,path):
        spath = path.split("/")[1:]
        record = self._getDir(spath[:-1])
        if spath[-1]:
            del record[spath[-1]]