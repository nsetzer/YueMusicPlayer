#! python34 $this

# http://www.rachaelrayshow.com/recipe/12896_Meat_Sauce_with_Pork_and_Fennel/

import io

# ------------------

def generateUniquePath(view,path):
    count=1
    dir,name = view.split(path)
    name,ext = view.splitext(path)
    while view.exists(path):
        path = view.join(dir,name+" (%d)"%count + ext)
        count += 1
    return path

# ------------------
# These iterators implement the algorithm
# for walking a directory structure for a source.

def walk_files( source, paths ):
    """
    accept a list of files and/or directories and yeild
    each file name. recursivley drops into each directory found looking
    for more files.
    """
    paths = [ (p,None) for p in paths ]
    while len(paths):
        path,base = paths.pop(0)
        if not base:
            base,_ = source.split(path)
        if source.isdir(path):
            for item in source.listdir(path):
                abspath = source.join(path,item)
                #relpath = source.relpath(abspath,base)
                paths.append( (abspath,base) )
        else:
            yield path,base

def walk_dir(source, dirpath ):

    # i tried to write this without recursion, but it became
    # too complicated - the problem was yielding the input last correctly

    for item in source.listdir(dirpath):
        if item == ".." or item == ".":
            continue
        path = source.join(dirpath,item)
        if source.isdir(path):
            # TODO: how does yield from work?
            for x in walk_dir( source, path ):
                yield x
        else:
            yield path

    yield dirpath

def walk_paths( source, paths ):
    """
    like walk_files, but yields directory names in a safe order
    such that each files can be deleted in order they are returned.
    """

    for path in paths:
        if source.stat_fast(path)["isDir"]:
            yield from walk_dir( source, path )
        else:
            yield path

# ------------------
# These iterators implement the algorithm
# for the copy,move, and remove operations.
# Each one accepts user input and yields output absolute paths
#
def iter_copy(sourceA,input,sourceB,target):
    """
    input  - either string or list-of-string
    target - string

    perform a file copy between two sources
    if input is a string copy the given file path to target

    if input is a list, target must be an existing directory
        all items in the input will be recursively copied to target.

    """
    # yield input/output names for each
    # path in paths
    # mv: does not need to delve into paths
    # cp: needs to delve into paths
    single = False
    if isinstance(input,str):
        if sourceA.isdir(input):
            paths = [ sourceA.join(input,name) for name in \
                          sourceA.listdir(input) ]
        else:
            single=True
            paths = [input,]
    else:
        paths = input

    for path,base in walk_files(sourceA,paths):
        relpath = sourceA.relpath(path,base)
        if single:
            dname,fname=sourceA.split(path)
            if sourceB.isdir(target):
                newpath = sourceB.join(target,relpath)
            else:
                newpath = target
        else:
            newpath = sourceB.join(target,\
                      *sourceA.breakpath(relpath))
        yield (path,newpath)

def iter_move(source,input,target):
    """
    yield the original filepath and output path for a set of files.

    if input is a string, target is the new
        name for the file or directory
    if input is a list, target is a directory
        for which all items will be moved into.
    """

    if isinstance(input,str):
        yield (input,target)
    else:
        for srcpath in input:
            _,name = source.split(srcpath)
            dstpath = source.join(target,name)
            yield( (srcpath,dstpath) )

def iter_remove(source,input):

    if isinstance(input,str):
        input = [input,]

    yield from walk_paths( source, input )

# ------------------
# These operations use the above iterators to perform
# basic file operations in batch mode, in a predictable
# and consistent way.

# this provides an example for how to implement a progress dialog

def source_walk(source,dirpath):
    """yield the list of files in a directory and all sub directories."""
    paths = [dirpath,]
    while len(paths):
        path = paths.pop(0)
        if source.isdir(path):
            for item in source.listdir(path):
                abspath = source.join(path,item)
                paths.append( abspath )
        else:
            yield path

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

def source_copy(sourceA, input, sourceB, target, chunksize=None):

    chunksize = chunksize or 32*1024 # arbitrary 32kb size

    for src,dst in iter_copy(sourceA, input, sourceB, target):
        dname,_ = sourceB.split(dst)
        sourceB.mkdir( dname )
        source_copy_file(sourceA, src, sourceB, dst, chunksize)

def source_move(source,input,target):
    """
    move the input file or list of files to target.
    if input is a string, target is the new name for the input
    otherwise, input is a list and the contents of the list
    will be moved under the target directory.
    """
    for src,dst in iter_move(source,input,target):
        source.move(src,dst)

def source_remove(source,input):
    """delete input path or list of paths
    path can be a file or directory.
    directories will have contents deleted recursively.
    """
    for path in iter_remove(source,input):
        source.delete(path)

# ------------------

class ThreadSafeFileIO(object):
    """docstring for ThreadSafeFileIO"""
    def __init__(self, fobj, mutex):
        super(ThreadSafeFileIO, self).__init__()
        self.fobj = fobj
        self.mutex = mutex

    def write(self,data):
        with self.mutex:
            return self.fobj.write(data)

    def read(self,count=-1):
        with self.mutex:
            return self.fobj.read(count)

    def close(self):
        with self.mutex:
            return self.fobj.close()

    def tell(self):
        with self.mutex:
            return self.fobj.tell()

    def seek(self,pos,whence=io.SEEK_SET):
        with self.mutex:
            return self.fobj.seek(pos,whence)

    def __enter__(self):
        return self

    def __exit__(self,typ,val,tb):
        if typ is None:
            self.close()
