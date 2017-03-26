
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
# for windows, the dummy path lists all available drive letters
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
            "name" : self.split(path)[1],
        }
        return result

    def __enter__(self):
        return self

    def __exit__(self,typ,val,tb):
        if typ is None:
            self.close()

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
        if self.exists( path ):
            if self.isdir(path):
                os.rmdir( path )
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

    def mkdir(self,path):
        if not self.exists( path ):
            os.makedirs( path )

    def split(self,path):
        return os.path.split(path)

    def splitext(self,path):
        return os.path.splitext(path)

    def stat(self,path):

        if os.path.exists(path):
            st = os.lstat(path)
            isLink = False
            if stat.S_ISLNK(st.st_mode):
                st = os.stat(path)
                isLink = True
            result = {
                "isDir" : stat.S_ISDIR(st.st_mode),
                "isLink" : isLink,
                "mtime" : calendar.timegm(time.localtime(st.st_mtime)),
                "ctime" : calendar.timegm(time.localtime(st.st_ctime)),
                "size"  : st.st_size,
                "mode"  : stat.S_IMODE(st.st_mode)
            }
        else:
            result = {
                "isDir" : False,
                "isLink" : False,
                "mtime" : 0,
                "ctime" : 0,
                "size"  : 0,
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
        self.show_hidden = show_hidden;

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

    def isdir(self,path):
        path = self.realpath(path)
        return self.source.isdir(path)

    def realpath(self,path):

        path = self.source.normpath(path,self.pwd())
        return path

    def normpath(self,path,root=None):
        return self.source.normpath(path,root)

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

        if dir == self.path:

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

class SourceListView(SourceView):

    def __init__(self,source,dirpath,dirsOnly=False,show_hidden=False):
        self.data = []
        self.sort_reverse = False
        self.sort_column_name = 'name'
        self.dirsOnly = dirsOnly;

        super(SourceListView,self).__init__(source,dirpath,show_hidden)

    def load(self):
        data = self.source.listdir(self.path)

        if self.show_hidden:
            data =  [ x for x in data ]
        else:
            data =  [ x for x in data if not self.source.hidden(x) ]

        data = self._sort(data) # and assignt to this instance

        #if self.path!=DirectorySource.dummy_path:
        #    data.insert(0,"..")

        self.data = data

    def _sort(self,data):
        # TODO: tristate, BOTH, FILES-ONLY, DIRECTORIES-ONLY

        # TODO: sort has a massive performance penalty
        # add logic to use STAT_FAST in place of stat if sorting
        # would not require a full stat.
        # or, if only sorting by name, we can avoid the stat_fast probably.\

        col_name=self.sort_column_name

        if col_name in {"name","size"}:
            data = [self.stat_fast(name) for name in data]
        else:
            data = [self.stat(name) for name in data]


        if self.dirsOnly :
            data = natsort.natsorted(filter( lambda x : x['isDir'], data),
                                     key=lambda x: x[col_name], \
                                     alg=natsort.ns.IGNORECASE,
                                     reverse=self.sort_reverse)
        else:
            # key sorts by directories, then files
            # and by filename decending.
            data = natsort.natsorted(data,
                                     key=lambda x: (not x['isDir'], x[col_name]), \
                                     alg=natsort.ns.IGNORECASE,
                                     reverse=self.sort_reverse)
        return [ x['name'] for x in data ]

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
        print(self.sort_column_name,self.sort_reverse)
        self.data = self._sort(self.data)

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
        print(dir1)
        print(dir2)
        print(self.path)
        if (dir1==dir2 and dir1 == self.path):
            for idx in range(len(self.data)):
                name = self.data[idx]
                if name == name1:
                    self.data[idx]=name2
        return self.source.move(oldpath,newpath)

    def __len__(self):
        return len(self.data)

    def __getitem__(self,idx):
        if 0 <= idx < len(self.data):
            name = self.data[idx]
            if not name:
                raise Exception("empty file name in directory")
            st = self.stat_fast( name )
            return st

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
