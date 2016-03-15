
import os,sys
import shutil
import natsort

import threading
import posixpath
from .drives import get_drives

# for windows, the dummy path lists all available drive letters
dummy_path="$"

class SourceNotImplemented(NotImplementedError):
    def __init__(self,cls,msg):
        msg = "Source %s :"%cls.__class__.__name__ + msg
        super(SourceNotImplemented,self).__init__(msg)

class DataSource(object):
    """docstring for DataSource"""
    def __init__(self):
        super(DataSource, self).__init__()

    def close(self):
        print("closing %s."%self.__class__.__name__)

    def fix(self,path):
        # override for filesystems that restrict charactersets
        return path

    def normpath(self,path,root):
        raise SourceNotImplemented(self,"cannot list path.")

    def listdir(self,path):
        raise SourceNotImplemented(self,"cannot list path.")

    def join(self,*args):
        raise SourceNotImplemented(self,"cannot join paths.")

    def breakpath(self,path):
        raise SourceNotImplemented(self,"cannot break paths.")

    def move(self,oldpath,newpath):
        raise SourceNotImplemented(self,"cannot move files.")

    def isdir(self,path):
        raise SourceNotImplemented(self,"cannot stat path.")

    def mkdir(self,path):
        raise SourceNotImplemented(self,"cannot create directories.")

    def delete(self,path):
        raise SourceNotImplemented(self,"cannot delete path.")

    def split(self,path):
        raise SourceNotImplemented(self,"cannot split path")

    def splitext(self,path):
        raise SourceNotImplemented(self,"cannot splitext path")

    def open(self,path,mode):
        raise SourceNotImplemented(self,"cannot open path")

    def getExportPath(self,path):
        # return a filepath that can be opened by the base file system
        # will be be passed to vlc.
        raise SourceNotImplemented(self,"cannot export path")

    def basename(self,path):
        return os.path.splitext(self.split(path)[1])[0]

    def hidden(self,path):
        name = self.split(path)[1]
        return name.startswith(".") and name != ".."

    def stat_fast(self,path):
        result = {
            "size"  : 0,
            "isDir" : self.isdir(path),
        }
        return result

    def __enter__(self):
        return self

    def __exit__(self,typ,val,tb):
        if typ is None:
            self.close()

class DirectorySource(DataSource):
    """docstring for DirectorySource"""

    # TODO: turn this into a directory generator
    # which first loads the directory, then loops over
    # loaded items.

    # TODO: on windows we need a way to view available
    # drive letters
    def __init__(self):
        super(DirectorySource, self).__init__()

    def root(self):
        return os.path.expanduser("~")

    def join(self,*args):
        return os.path.join(*args)

    def breakpath(self,path):
        return [ x for x in path.replace("/","\\").split("\\") if x ]

    def relpath(self,path,base):
        return os.path.relpath(path,base)

    def normpath(self,path,root=None):
        if path == dummy_path:
            return dummy_path
        if root and not path.startswith("/"):
            path = os.path.join(root,path)
        return os.path.normpath( path )

    def listdir(self,path):
        if path == dummy_path:
            return get_drives()
        return os.listdir(path)

    def parent(self,path):
        # TODO: if path is C:\\ return empty string ?
        # empty string returns drives
        if path[1:] == ":\\":
            return dummy_path
        p,_ = os.path.split(path)
        return p

    def move(self,oldpath,newpath):
        # throws OS errors for related errors
        # e.g. file does not exist, file already exists
        if not os.path.exists(newpath):
            shutil.move(oldpath,newpath)
        else:
            raise OSError("File already exists: %s"%newpath)

    def delete(self,path):
        # todo support removing directory rmdir()
        if self.exists( path ):
            os.remove( path )

    def open(self,path,mode):
        return open(path,mode)

    def exists(self,path):
        if path == dummy_path:
            return True
        return os.path.exists(path)

    def isdir(self,path):
        return os.path.isdir(path)

    def mkdir(self,path):
        if not self.exists( path ):
            os.makedirs( path )

    def split(self,path):
        return os.path.split(path)

    def splitext(self,path):
        return os.path.splitext(path)

    def stat_fast(self,path):
        result = {
            "size"  : 0, #st.st_size,
            "isDir" : False,
        }
        if os.path.exists(path):
            try:
                st = os.stat(path)
            except:
                pass
            finally:
                result["size"] = st.st_size
                result["isDir"] = os.path.isdir(path)
        return result

    def getExportPath(self,path):
        return path # nothing to do

class SourceView(object):

    def __init__(self,source,dirpath):
        super(SourceView,self).__init__()
        if isinstance(source,SourceView):
            self.source = source.source
        else:
            self.source = source
        #self.path, self.name = source.split(path)
        self.path = dirpath

        self.statcache = {}
        self.show_hidden = False;

        self.chdir(dirpath)

    def name(self):
        p = self.breakpath(self.pwd())
        b = self.source.__class__.__name__+":/"
        j="/"
        if len(p) > 2:
            j = "/.../"
        if len(p) > 1:
            return b+p[0]+j+p[-1]
        if len(p) > 0:
            return b+p[0]
        return b

    def setShowHidden(self,b):
        self.show_hidden = b
        #self.chdir(self.path)

    def refresh(self,b=False):
        self.chdir(self.path)

    def pwd(self):
        return self.path

    def kind(self,path):

        path=self.realpath(path)

        if self.isdir( path ):
            return DataResource.DIRECTORY

        return DataResource.kindFromPath( path )

    def relpath(self,path,base):
        return self.source.relpath(path,base)

    def breakpath(self,path):
        return self.source.breakpath(path)

    # ----------------------------------------------

    def chdir(self,path):
        # realpath == normpath
        fullpath = self.realpath(path)
        if self.source.exists(fullpath):
            if fullpath != self.path:
                self.statcache = {}
            self.path = fullpath
            return True
        return False

    def parent(self,path):
        path = self.realpath(path)
        return self.source.parent(path)

    def exists(self,path):
        path = self.realpath(path)
        return self.source.exists(path)

    # TODO: conflicting requirements...
    def isdir(self,path):
        path = self.realpath(path)
        return self.source.isdir(path)

    def realpath(self,path):
        return self.source.normpath(path,self.pwd())

    def listdir(self,path):
        path = self.realpath(path)
        return self.source.listdir(path)

    def join(self,*args):
        return self.source.join(*args)

    def move(self,oldpath,newpath):
        oldpath = self.realpath(oldpath)
        newpath = self.realpath(newpath)
        return self.source.move(oldpath,newpath)

    def mkdir(self,path):
        path = self.realpath(path)
        return self.source.mkdir(path)

    def delete(self,path):
        path = self.realpath(path)
        return self.source.delete(path)

    def open(self,path,mode):
        return self.source.open(path,mode)

    def stat_fast(self,path):
        path = self.realpath(path)
        return self.source.stat_fast(path)

    def split(self,path):
        #path = self.realpath(path)
        return self.source.split(path)

    def splitext(self,path):
        return self.source.splitext(path)

    def basename(self,path):
        # todo what if path is a directory?
        return self.source.basename(path)

    def close(self,path):
        raise RuntimeError("cannot close view")

    def getExportPath(self,path):
        return self.source.getExportPath(path)
# todo:  rename Iter View
# todo: removre all reference to 'image'
#        that shoulld be done in a subclass specific to comic reader
class SourceListView(SourceView):

    def __init__(self,source,dirpath,dirsOnly=False):
        self.data = []
        self.sort_reverse = False
        self.dirsOnly = dirsOnly;

        super(SourceListView,self).__init__(source,dirpath)

    def load(self):
        #self.data = self.listdir( self.pwd() )
        #self.data.sort(key=lambda x: x.lower())

        data = self.source.listdir(self.path)


        if self.show_hidden:
            data =  [ x for x in data ]
        else:
            data =  [ x for x in data if not self.source.hidden(x) ]

        # TODO: tristate, BOTH, FILES-ONLY, DIRECTORIES-ONLY
        if self.dirsOnly : # == QFileDialog.Directory:
            data = natsort.natsorted(filter( self.isdir, data),
                                     alg=natsort.ns.IGNORECASE,
                                     reverse=self.sort_reverse)
        else:
            # key sorts by directories, then files
            # and by filename decending.
            data = natsort.natsorted(data,
                                     key=lambda x: (not self.isdir(x),x), \
                                     alg=natsort.ns.IGNORECASE,
                                     reverse=self.sort_reverse)
        self.data = data

        if self.path!=dummy_path:
            self.data.insert(0,"..")

    def chdir(self,path):
        if super().chdir(path):
            self.load()
            return True
        return False

    def __len__(self):
        return len(self.data)

    def __getitem__(self,idx):
        if 0 <= idx < len(self.data):
            name = self.data[idx]
            if not name:
                name = "-"
            return self._statfast( name )

    def isdir_cached(self,name):
        return self._statfast(name)["isDir"]

    def fileSize_cached(self,name):
        return self._statfast(name)["size"]

    def _statfast(self,path):
        # create a cache of stat calls
        # also, collecting isDir and size attributes
        # can be done without looking at the inode on some file
        # systems, so this can overall be faster than calling stat
        if self.path==dummy_path:
            return {'name':path, "isDir":True,"size":0}
        _,name = self.source.split(path)
        if name == "." or name == "..":
            return {'name':name, "isDir":True,"size":0}

        if name not in self.statcache:
            path=self.source.join(self.path,name)
            #if not self.source.exists(path):
            #    s='->'.join([s[2] for s in traceback.extract_stack()])
            #    print("stat_fast ST error:",path,name)
            #    print(s)
            #    return {"isDir":True,"size":0}
            try:

                st = self.source.stat_fast(path)
                st['name'] = name
                self.statcache[name]=st
            except OSError:
                self.statcache[name] = {'name':name, "isDir":False, "size":0}
                s='->'.join([s[2] for s in traceback.extract_stack()])
                print("stat_fast OS error:",path,name)
                print(s)
        return self.statcache[name]

def source_copy_file(sourceA, pathA, sourceB, pathB, chunksize):
    """
    Perform file copy from one source to another.
    chunksize is the number of bytes to read/write at one time.
    """
    with sourceA.open(pathA,"rb") as rb:
        with sourceB.open(pathB,"wb") as wb:
            buf = rb.read(chunksize)
            while buf:
                wb.write(buf)# TODO: write should return len buf
                buf = rb.read(chunksize)

def source_walk(source, dirpath ):
    """ return all files from target source directory """
    # i tried to write this without recursion, but it became
    # too complicated - the problem was yielding the input last correctly

    for item in source.listdir(dirpath):
        if item == ".." or item == ".":
            continue
        path = source.join(dirpath,item)
        if source.isdir(path):
            for x in source_walk( source, path ):
                yield x
        else:
            yield path

    yield dirpath

def source_walk_ext(source, dirpath, extensions):
    """ return all files from target source directory """
    # i tried to write this without recursion, but it became
    # too complicated - the problem was yielding the input last correctly

    for item in source.listdir(dirpath):
        if item == ".." or item == ".":
            continue
        path = source.join(dirpath,item)
        ext = os.path.splitext(item)[1]
        if ext in extensions:
            yield path
        elif source.isdir(path):
            for x in source_walk_ext( source, path, extensions ):
                yield x
