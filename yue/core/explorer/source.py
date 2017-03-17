
import os,sys
import shutil
import natsort

import threading
import posixpath
from .drives import get_drives
import stat

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

    def expanduser(self,path):
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

    def stat(self,path):
        raise SourceNotImplemented(self,"cannot stat path")

    def stat_fast(self,path):
        """
        fast_stat must at minimum return
            isDir, isLink, size, name

        size can be zero. on some platforms
        a stat_fast can be implemented without
        reading the inode for the file, using
        only directory entry information
        """
        result = {
            "size"  : 0,
            "isDir" : self.isdir(path),
            "isLink" : False,
            "name" : self.split(path)[1],
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

    def expanduser(self,path):
        if path.startswith("~"):
            return os.path.expanduser(path)
        return path

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

    def stat(self,path):
        st = os.stat(path)
        if os.path.exists(path):
            st = os.stat(path)
            result = {
                "isDir" : stat.S_ISDIR(st.st_mode),
                "isLink" : stat.S_ISLNK(st.st_mode),
                "mtime" : st.st_mtime,
                "ctime" : st.st_ctime,
                "size"  : st.st_size,
                "name"  : self.split(path)[1],
                "mode"  : stat.S_IMODE(st.st_mode)
            }
        else:
            result = {
                "isDir" : False,
                "isLink" : False,
                "mtime" : 0,
                "ctime" : 0,
                "size"  : 0,
                "name"  : self.split(path)[1],
                "mode"  : 0
            }
        return result

    def stat_fast(self,path):
        """ there is no such thing as a "fast" stat
        for this file system so just call stat
        """
        return self.stat(path)

    def getExportPath(self,path):
        return path # nothing to do

class SourceView(object):

    def __init__(self,source,dirpath,show_hidden=False):
        super(SourceView,self).__init__()
        if isinstance(source,SourceView):
            self.source = source.source
        else:
            self.source = source
        #self.path, self.name = source.split(path)
        self.path = dirpath

        self.statcache = {}
        self.show_hidden = show_hidden;

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
        path = self.source.expanduser(path)
        path = self.source.normpath(path,self.pwd())
        return path

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

    def stat(self,path):
        path = self.realpath(path)
        return self.source.stat(path)

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

    def __init__(self,source,dirpath,dirsOnly=False,show_hidden=False):
        self.data = []
        self.sort_reverse = False
        self.dirsOnly = dirsOnly;

        super(SourceListView,self).__init__(source,dirpath,show_hidden)

    def load(self):
        #self.data = self.listdir( self.pwd() )
        #self.data.sort(key=lambda x: x.lower())

        data = self.source.listdir(self.path)

        if self.show_hidden:
            data =  [ x for x in data ]
        else:
            data =  [ x for x in data if not self.source.hidden(x) ]

        self._sort(data) # and assignt to this instance

        if self.path!=dummy_path:
            self.data.insert(0,"..")

    def _sort(self,data):
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

    def sort(self,reverse=None):
        """
        """
        if reverse is not None:
            self.sort_reverse = reverse
        self._sort(self.data)

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

    def stat(self,name):
        # todo: need to mingle the statfast and stat caches
        # must be one in a way that makes sense given the type of source
        if name in self.statcache:
            if 'mtime' not in self.statcache[name]:
                self.statcache[name] = super().stat(name)
            return self.statcache[name]
        return super().stat(name)

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

    def new(self,basename,isDir=False):
        """
        generate a new file name for the directory
        """
        name = basename
        i = 1
        while name in self.data:
            name = basename + " (%d)"%i
            i += 1
        # create a dummy entry in the cache
        # as far as the view is concerned, the file exist
        # but the file system does not yet know about it yet.
        index = len(self.data)
        self.statcache[name] = {
            "isDir" : isDir,
            "isLink" : False,
            "mtime" : 0,
            "ctime" : 0,
            "size"  : 0,
            "name"  : name,
            "mode"  : 0,
        }
        index = len(self.data)
        self.data.append(name)
        return index,name

    def index(self,name):
        return self.data.index(name)

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

