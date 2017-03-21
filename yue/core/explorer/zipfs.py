#! python34 $this
# TODO support for libarchive (7z)
# libarchive may render the other implementations void

import os,sys
import zipfile
import tarfile
try:
    import rarfile
except ImportError:
    sys.stderr.write("rar not supported by zipfs\n")
    rarfile = None

import io
# this one uses the dll
#from unrar import rarfile
#https://github.com/matiasb/python-unrar
"""
RAR files:
    two different impls:
    'rarfile' : uses unrar.exe
    'unrar'   : uses unrar.dll
"""
import errno
#from EBFS.bfs import *
from io import BytesIO

from .dictfs import DictFSImpl

class ZipFileWriter(object):
    """docstring for ZipFileWriter"""
    def __init__(self, fs, path):
        super(ZipFileWriter, self).__init__()
        self.fs = fs
        self.path = path
        self.file = BytesIO()

    def write(self,data):
        return self.file.write(data)

    def seek(self,pos,whence=io.SEEK_SET):
        return self.file.seek(pos,whence)

    def tell(self):
        return self.file.tell()

    def close(self):
        self.fs.create(self.path)
        self.fs.zip.writestr(self.path,self.file.getvalue())

    def __enter__(self):
        return self

    def __exit__(self,typ,val,tb):
        # only save and flush the file on success ???
        if typ is None:
            self.close()

class TarFileWriter(object):
    def close(self):
        self.file.seek(0)
        inf = self.fs.ark.gettarinfo(self.path,fileobj=self.file)
        self.fs.ark.addfile(info,self.file)

class ZipFSImpl(DictFSImpl):
    """docstring for ZipFSImpl"""
    # python implementation prevents removal or updating of a file.
    def __init__(self, filepath,mode="r"):
        super(ZipFSImpl, self).__init__()
        self.mode = "r" if "r" in mode else "a"
        self._open(filepath,self.mode)

    def _open(self,filepath,mode):
        self.filepath = filepath
        self.zip = zipfile.ZipFile(self.filepath,mode=mode,
                                   compression=zipfile.ZIP_DEFLATED)
        self.load(self.zip.namelist())

    def open(self,path,mode):
        zippath = path[1:]
        if "r" in mode:
            return self.zip.open(zippath,mode)
        if self.exists(path):
            raise RuntimeError("cannot alter file")
        return ZipFileWriter(self,zippath)

    def readonly(self):
        return self.mode.startswith("r")

    def stat(self,path):
        zippath = path[1:]
        if self.isdir(path):
            return {'size':0, "isDir":True}
        info = self.zip.getinfo(zippath)
        data = {'size':info.file_size,"isDir":False}
        return data

    def stat_fast(self,path):
        zippath = path[1:]
        if self.isdir(path):
            return {'size':0, "isDir":True}
        info = self.zip.getinfo(zippath)
        data = {'size':info.file_size,"isDir":False}
        return data

    def close(self):
        self.zip.close()

class TarFSImpl(DictFSImpl):
    """docstring for ZipFSImpl"""
    # python implementation prevents removal or updating of a file.
    def __init__(self, filepath,mode="r",fileobj=None):
        super(TarFSImpl, self).__init__()

        self.filepath = filepath
        self.fileobj = fileobj

        filename = filepath.replace("\\","/").split('/')[-1]
        fileext = filename.split(".")[-1]
        print(filename,fileext)
        if fileext == "gz":
            mode += ":gz"
        elif fileext == "bz2":
            mode += ":bz2"
        elif fileext == "xz":
            mode += ":xz"
        elif fileext == "7z":
            mode += ":xz"

        self.mode = mode

        self._open()

    def _open(self):

        fo = self.fileobj or self.filepath
        self.ark = tarfile.open(fo,mode=self.mode)

        names = []
        inf = self.ark.next()
        while inf is not None:
            if not inf.isdir():
                names.append(inf.name)
            inf = self.ark.next()
        self.load(names)

    def readonly(self):
        return self.mode.startswith("r")

    def open(self,path,mode):
        tarpath = path[1:]
        if "r" in mode:
            return self.ark.extractfile(tarpath)
        if self.exists(path):
            raise RuntimeError("cannot alter file")
        return TarFileWriter(self,tarpath)

    def stat(self,path):
        tarpath = path[1:]
        _,name = self.split(path)
        if self.isdir(path):
            return {'size':0,
                    'name':name,
                    "isDir":True,
                    "isLink":False,
                    "mtime":0}
        info = self.ark.gettarinfo(tarpath)
        data = {'size':info.size,
                'name':name,
                "isDir":False,
                "isLink":False,
                "mtime":0}
        return data

    def stat_fast(self,path):
        tarpath = path[1:]
        _,name = self.split(path)
        if self.isdir(path):
            return {'size':0,
                    'name':name,
                    "isDir":True,
                    "isLink":False}
        info = self.ark.getmember(tarpath)
        data = {'size':info.size,
                'name':name,
                "isDir":False,
                "isLink":False}
        return data

    def close(self):
        self.zip.close()


class RarFSImpl(ZipFSImpl):

    def __init__(self, filepath,mode="r"):
        super(RarFSImpl, self).__init__(filepath)

    def _open(self,filepath,mode):
        self.filepath = filepath
        self.zip = rarfile.RarFile(self.filepath,"r")
        self.load(self.zip.namelist())

    def open(self,path,mode):
        zippath = path[1:]
        if "r" in mode:
            try :
                return self.zip.open(zippath,mode)
            except TypeError:
                raise OSError(errno.EEXIST)

        raise RuntimeError("cannot alter file")

def ZipFS(fileobj,name=None,mode="r"):
    """
    opens zip,cbz and rar,cbr files
    """
    if name is None:
        if not isinstance(fileobj,str):
            raise Exception("name must be provided when given file-like object")
        name = fileobj.replace("\\","/").split('/')[-1]

    path = (name or fileobj).lower()
    if path.endswith(".rar") or path.endswith(".cbr"):
        return RarFSImpl(fileobj,mode)
    if path.endswith(".tar.gz") or path.endswith(".7z"):
        return TarFSImpl(path,mode,fileobj)
    return ZipFSImpl(fileobj,mode)

def isArchiveFile(filepath):

    # not using os.path to allow using arbitrary sources
    filename = filepath.replace("\\","/").split('/')[-1]
    fileext = filename.split(".")[-1]
    return fileext in {"gz","zip","rar","7z",".tar",".iz"}

def main():

    #arc = Archive("D:\\Shelf\\test\\test.cz",b"password",overwrite=True)
    zip=r"ziptest.zip"

    #zfs = ZipFS(zip)
    zfs = DictFSImpl()
    zfs.load(["/foo",])

    print(zfs.exists("/"))
    #print(("%s"%zfs.listdir("/")).encode('utf-8'))
    #for item in zfs.listdir("/ziptest/"):
    #    print(item)
    #print(zfs.exists('/ziptest/file1.txt'))
    #print( zfs.stat('/ziptest/file1.txt') )
    #print( zfs.stat('/ziptest/folder1') )


if __name__ == '__main__':
    main()