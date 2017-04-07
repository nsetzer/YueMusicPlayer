
import os,sys
import shutil
import natsort

import threading
import posixpath
from .drives import get_drives
import stat
import traceback
import time
import calendar
import ctypes
from fnmatch import fnmatch
from collections import defaultdict
# for windows, the dummy path lists all available drive letters
class SourceNotImplemented(NotImplementedError):
    def __init__(self,cls,msg):
        msg = "Source %s :"%cls.__class__.__name__ + msg
        super(SourceNotImplemented,self).__init__(msg)

class DataSource(object):
    """docstring for DataSource"""

    IS_REG = 0
    IS_LNK = 1
    IS_LNK_BROKEN = 3

    def __init__(self):
        super(DataSource, self).__init__()

    def close(self):
        print("closing %s."%self.__class__.__name__)

    def fix(self,path):
        # override for filesystems that restrict charactersets
        return path

    def equals(self,other):
        """ return true if the given source/view matches this one
        """
        print(type(self))
        print(type(other))
        return isinstance(other,type(self))

    def islocal(self):
        """ return True if the source represents the local file system

        This means that an external program can easily access the file
        """
        return False

    def readonly(self):
        """ return true if write operations will fail """
        return False

    def expanduser(self,path):
        """
        expanduser is a leaky abstraction do not use it
        realpath or normpath should expand environment variables
        """
        raise SourceNotImplemented("use realpath")

    def relpath(self,path,base):
        """return a new path which is relative to the given base path"""
        raise SourceNotImplemented(self,"cannot list path.")

    def normpath(self,path,root=None):
        """return an absolute path representing path
        if path is relative, assume it is relative to the
        given root directory
        """
        raise SourceNotImplemented(self,"cannot list path.")

    def listdir(self,path):
        """ return a list of filenames in a given directory """
        raise SourceNotImplemented(self,"cannot list path.")

    def join(self,*args):
        raise SourceNotImplemented(self,"cannot join paths.")

    def breakpath(self,path):
        return [ x for x in path.replace("/","\\").split("\\") if x ]

    def move(self,oldpath,newpath):
        raise SourceNotImplemented(self,"cannot move files.")

    def isdir(self,path):
        raise SourceNotImplemented(self,"cannot stat path.")

    def islink(self,path):
        raise SourceNotImplemented(self,"cannot stat path.")

    def mkdir(self,path):
        raise SourceNotImplemented(self,"cannot create directories.")

    def readlink(self,path):
        """ return the target path of a symlink """
        raise SourceNotImplemented(self,"cannot read link.")

    def mklink(self,target,path):
        """ create a new symlink at path pointing at target

        path must not exist
        """
        raise SourceNotImplemented(self,"cannot create link.")

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
        return self.splitext(self.split(path)[1])[0]

    def hidden(self,path):
        name = self.split(path)[1]
        return name.startswith(".")

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
            "isLink" : self.islink(path),
        }
        return result

    def __enter__(self):
        return self

    def __exit__(self,typ,val,tb):
        if typ is None:
            self.close()

def trace():
    return '->'.join([s[2] for s in traceback.extract_stack()])

def pretty_trace():
    print(trace())


def has_hidden_attribute(filepath):
    try:
        attrs = ctypes.windll.kernel32.GetFileAttributesW(filepath)

        if attrs != -1:
            result = bool(attrs & 2)
        else:
            result = False
    except AttributeError as e:
        print(e)
        result = False
    except AssertionError as e:
        result = False
    return result

class DirectorySource(DataSource):
    dummy_path="\\"

    """DirectorySource wraps os.path into the Source Interface
    a DirectorySource enables interacting with the local file system
    in an abstract way
    """

    def __init__(self):
        super(DirectorySource, self).__init__()

    def islocal(self):
        return True

    def root(self):
        if sys.platform == "win32":
            return DirectorySource.dummy_path
        return "/"

    def join(self,*args):
        return os.path.join(*args)

    def relpath(self,path,base):
        return os.path.relpath(path,base)

    def normpath(self,path,root=None):

        if path == DirectorySource.dummy_path:
            return DirectorySource.dummy_path
        if sys.platform=="win32" and path.startswith(DirectorySource.dummy_path):
            path = path[len(DirectorySource.dummy_path):]
        path = os.path.expanduser(path)
        if root and not path.startswith("/"):
            path = os.path.join(root,path)
        return os.path.normpath( path )

    def readlink(self,path):
        """ return the target path of a symlink """
        if path == DirectorySource.dummy_path:
            return path
        return os.readlink(path)

    def listdir(self,path):
        if path == DirectorySource.dummy_path:
            return get_drives()
        return os.listdir(path)

    def parent(self,path):
        # TODO: if path is C:\\ return empty string ?
        # empty string returns drives
        if path[1:] == ":\\":
            return DirectorySource.dummy_path
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
        if self.isdir(path):
            os.rmdir( path )
        elif self.islink(path):
            os.unlink(path)
        else:
            os.remove( path )

    def open(self,path,mode):
        return open(path,mode)

    def exists(self,path):
        if path == DirectorySource.dummy_path:
            return True
        return os.path.exists(path)

    def isdir(self,path):
        return os.path.isdir(path)

    def islink(self,path):
        st = os.lstat(path )
        return stat.S_ISLNK(st.st_mode)

    def mkdir(self,path):
        if not self.exists( path ):
            os.makedirs( path )

    def mklink(self,target,path):
        os.symlink(target,path)

    def split(self,path):
        return os.path.split(path)

    def splitext(self,path):
        return os.path.splitext(path)

    def stat(self,path):

        #try:
        st = os.lstat(path)
        #except FileNotFoundError:
        #    result = {
        #        "isDir" : False,
        #        "isLink" : False,
        #        "mtime" : 0,
        #        "ctime" : 0,
        #        "size"  : 0,
        #        "mode"  : 0
        #    }
        #    return result

        isLink = DirectorySource.IS_REG
        if stat.S_ISLNK(st.st_mode):
            # only links are stated twice. we first need to know
            # if it is a link, and if it is, what does it point to.
            try:
                st = os.stat(path)
            except FileNotFoundError:
                isLink = DirectorySource.IS_LNK_BROKEN
            else:
                isLink = DirectorySource.IS_LNK

        result = {
            "isDir" : stat.S_ISDIR(st.st_mode),
            "isLink" : isLink,
            # TODO: always store time without timezone info....?
            "mtime" : calendar.timegm(time.localtime(st.st_mtime)),
            "ctime" : calendar.timegm(time.localtime(st.st_ctime)),
            "size"  : st.st_size,
            "mode"  : stat.S_IMODE(st.st_mode)
        }
        # if on windows and path is not a plain drive letter
        if sys.platform == "win32" and path[1:] != ":\\":
            if has_hidden_attribute(path):
                result['isHidden'] = True

        return result

    def stat_fast(self,path):
        """ there is no such thing as a "fast" stat
        for this file system so just call stat
        """
        return self.stat(path)

    def getExportPath(self,path):
        return path # nothing to do

class SourceView(object):
    """
    A source view is a view into a directory of a source.

    A source view has a current working directory, for which relative
    paths can be automatically resolved. A cache is maintained for
    the result of stat calls to items in the current directory

    other than the addition of "chdir" and "pwd",
    a source view is a drop in replacement for a source.
    """
    def __init__(self,source,dirpath,show_hidden=False):
        super(SourceView,self).__init__()
        if isinstance(source,SourceView):
            self.source = source.source
        else:
            self.source = source

        self.path = dirpath

        self.statcache = {}
        self.statcache_index = {}
        self.show_hidden = show_hidden;

        self._stat_data = defaultdict(int)

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

    def equals(self,other):
        """ return true if the given source/view matches this one
        """
        if isinstance(other,SourceView):
            other = other.source
        return self.source.equals(other)

    def setShowHidden(self,b):
        self.show_hidden = b

    def refresh(self,b=False):
        self.chdir(self.path)

    def islocal(self):
        return self.source.islocal()

    def readonly(self):
        return self.source.readonly()

    def root(self):
        return self.source.root()

    def relpath(self,path,base):
        return self.source.relpath(path,base)

    def breakpath(self,path):
        return self.source.breakpath(path)

    # ----------------------------------------------

    def pwd(self):
        return self.path

    def chdir(self,path):
        # realpath == normpath
        fullpath = self.realpath(path)
        if self.source.exists(fullpath):
            self.statcache = {}
            self.statcache_index = {}
            self.path = fullpath
            return True
        return False

    def parent(self,path):
        path = self.realpath(path)
        return self.source.parent(path)

    def exists(self,path):
        path = self.realpath(path)
        return self.source.exists(path)

    def isdir(self,path):
        path = self.realpath(path)
        return self.source.isdir(path)

    def realpath(self,path):
        path = self.source.normpath(path,self.pwd())
        return path

    def normpath(self,path,root=None):
        return self.source.normpath(path,root)

    def readlink(self,path):
        path = self.realpath(path)
        return self.source.readlink(path)

    def mklink(self,target,path):
        return self.source.mklink(target,path)

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
        path = self.realpath(path)
        return self.source.open(path,mode)

    def _stat(self,stat,path):
        """
        perform a stat or fast stat of the given path.
        if the given path is an item in the current directory, cache the result
        """


        _,name = self.split(path)
        if name == "." or name == "..":
            return {"name":name,"isDir":True,"isLink":True,\
                    "size":0, "mtime":0, "ctime":0, "mode":0}
        path=self.realpath(path)
        dir,_ = self.split(path)

        if not name:
            name=path # root directory

        #self._stat_data[trace()]+=1

        if (self.path == DirectorySource.dummy_path and dir==name) or \
            dir == self.path:

            if name not in self.statcache or \
                'mtime' not in self.statcache[name]:
                st = stat(path)
                st['name'] = name
                self.statcache[name] = st

            return self.statcache[name]


        #except OSError as e:
        #    print(e)
        #    self.statcache[name] = {"isDir":False,"isLink":False, "size":-1}
        #    s='->'.join([s[2] for s in traceback.extract_stack()])
        #    print("stat_fast OS error:",path,name)
        #   print(s)

        st = stat(path)
        st['name'] = name
        return st

    def stat(self,path):
        return self._stat(self.source.stat,path)

    def stat_fast(self,path):
        return self._stat(self.source.stat_fast,path)

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

    def isdir_cached(self,name):
        return self.stat_fast(name)["isDir"]

    def fileSize_cached(self,name):
        return self.stat_fast(name)["size"]

    def hidden(self,name):
        return self.source.hidden(name)

class SourceListView(SourceView):

    def __init__(self,source,dirpath,dirsOnly=False,show_hidden=False):
        self.data = []
        self.data_filtered = []
        self.sort_reverse = False
        self.sort_column_name = 'name'
        self.dirsOnly = dirsOnly;

        self.text_filter = None
        super(SourceListView,self).__init__(source,dirpath,show_hidden)

    def load(self):
        data = self.source.listdir(self.path)

        # remove hidden files to limit the number of elements
        # that we will eventually have to stat.
        if not self.show_hidden:
            data =  [ x for x in data if not self.source.hidden(x) ]

        # stat the names, certain sort orders can be optimized
        if self.sort_column_name in {"name","size"}:
            data = [self.stat_fast(name) for name in data]
        else:
            data = [self.stat(name) for name in data]

        # on windows, stat uncovers additional hidden resources
        if sys.platform == "win32" and not self.show_hidden:
            data = [ x for x in data if "isHidden" not in x]

        data = self._sort(data) # and assignt to this instance

        self.setData([ x['name'] for x in data ])

    def setData(self,data):
        self.data = data
        if self.text_filter is not None:
            f = lambda x: self.statcache[x]['isDir'] or fnmatch(x,self.text_filter)
            self.data_filtered = [ x for x in data if f(x) ]
        else:
            self.data_filtered = data
        self.statcache_index = {}

    def _sort(self,data):
        # TODO: tristate, BOTH, FILES-ONLY, DIRECTORIES-ONLY

        if self.dirsOnly :
            data = natsort.natsorted(filter( lambda x : x['isDir'], data),
                                     key=lambda x: x[self.sort_column_name], \
                                     alg=natsort.ns.IGNORECASE,
                                     reverse=self.sort_reverse)
        else:
            # key sorts by directories, then files
            # and by filename decending.
            data = natsort.natsorted(data,
                                     key=lambda x: (not x['isDir'], x[self.sort_column_name]), \
                                     alg=natsort.ns.IGNORECASE,
                                     reverse=self.sort_reverse)
        return data

    def sort(self,column_name,toggle=False):
        """
        sort the view by the given column (stat key)
        return whether a reverse sort is being used

        if toggle is true reverse the sort so long as column matches
        the current sort order
        """
        if toggle and self.sort_column_name == column_name:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_reverse = False

        self.sort_column_name = column_name

        if self.sort_column_name in {"name","size"}:
            items = [self.stat_fast(name) for name in self.data]
        else:
            items = [self.stat(name) for name in self.data]

        items = self._sort(items)

        self.setData([ x['name'] for x in items ])

        return self.sort_reverse

    def chdir(self,path):
        if super().chdir(path):
            self.load()
            return True
        return False

    def move(self,oldpath,newpath):
        oldpath = self.realpath(oldpath)
        newpath = self.realpath(newpath)

        dir1,name1 = self.split(oldpath)
        dir2,name2 = self.split(newpath)
        if (dir1==dir2 and dir1 == self.path):
            for idx in range(len(self.data)):
                name = self.data[idx]
                if name == name1:
                    self.data[idx]=name2
                    self.statcache_index={} # TODO: a better way?
                    break;
        return self.source.move(oldpath,newpath)

    def mklink(self,target,path):
        path = self.realpath(path)
        # need to update statcache and data
        self.source.mklink(target,path)

    def delete(self,path):

        path = self.realpath(path)
        dir1,name1 = self.split(path)
        if dir1 == self.path:
            for idx in range(len(self.data)):
                name = self.data[idx]
                if name == name1:
                    self.data.pop(idx)
                    self.statcache_index={} # TODO: a better way?
                    break;
        return self.source.delete(path)

    def __len__(self):
        if self.text_filter is not None:
            return len(self.data_filtered)
        return len(self.data)

    def __getitem__(self,idx):
        dat=self.data
        if self.text_filter is not None:
            dat=self.data_filtered

        if 0 <= idx < len(dat):
            # cache the result for a given index in the statcache_index
            if idx not in self.statcache_index:
                name = dat[idx]
                if not name:
                    raise Exception("empty file name in directory")
                self.statcache_index[idx] = self.stat_fast( name )
            return self.statcache_index[idx]

    def __iter__(self):
        for i in range(len(self)):
            yield self[i]
    # new and index are hacks enabling editing names for
    # items which do not exist, is there a betterway?
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

    def setTextFilter(self,filter):
        filter = filter.strip()
        if filter == "*.*" or filter == "":
            self.text_filter = None
        else:
            filter = filter.strip()
            if not filter.startswith("*"):
                filter = '*' + filter
            if not filter.endswith("*"):
                filter = filter + '*'
            self.text_filter = filter
        self.setData(self.data)
