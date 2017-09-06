
import os,sys

from yue.explor.util import proc_exec

def _normpath(path,root=None):
    path = os.path.expanduser(path)
    if not path.startswith("/"):
        path = os.path.join(root,path)
    return path

def _mode(path):
    tar_shortcuts = {
        "tb2"  : "bz2",
        "tbz"  : "bz2",
        "tbz2" : "bz2",
        "tgz"  : "gz",
        "tlz"  : "lzma",
        "txz"  : "xz",
        "tZ"   : "Z"
    }

    path,ext = os.path.splitext(path)
    mode = ext[1:].lower()

    if mode in tar_shortcuts:
        mode = tar_shortcuts[mode]
        submode = "tar"
    else:
        # submode will be "tar" if it exists
        submode = os.path.splitext(path)[1][1:].lower()
    return mode,submode

def _compress(pwd, arc_path, paths):

    # TODO: method to override the mode
    #  flag `--mode tar.xz` when type cannot be infered from ext
    # pass mode, submode into this function, instead of extracting from path
    # TODO: mode transforms
    #   e.g. 7zip -> 7z

    mode,submode = _mode(arc_path)

    if mode == "7z":
        cmd = ["7za", "a", arc_path] + paths
    elif mode == "zip":
        cmd = ["zip", arc_path] + paths
    elif submode == "tar":
        if mode == "gz":
            cmd = ["tar", "-czvf", arc_path] + paths
        elif mode == "bz2":
            cmd = ["tar", "-cjvf", arc_path] + paths
        else:
            cmd = ["tar", "-cvf", arc_path] + paths
    else:
        raise Exception("Unrecognized mode: %s.%s"%(submode,mode))

    proc_exec(cmd, pwd, blocking=True)

def _extract(arc_path, directory):

    mode,submode = _mode(arc_path)

    if mode == "7z":
        cmd = ["7za", "x", arc_path]
    elif mode == "zip":
        cmd = ["unzip", arc_path]
    elif submode == "tar":
        if mode == "gz":
            cmd = ["tar", "-xzvf", arc_path]
        elif mode == "bz2":
            cmd = ["tar", "-xjvf", arc_path]
        else:
            cmd = ["tar", "-xvf", arc_path]
    else:
        raise Exception("Unrecognized mode: %s.%s"%(submode,mode))

    os.chdir(directory)

    proc_exec(cmd, directory, blocking=True)

def extract_supported(path):
    mode,submode = _mode(path)
    if mode == "7z" or \
       mode == "zip" or \
       (mode == "gz" and submode == "tar") or \
       (mode == "bz2" and submode == "tar"):
        return True
    return False;

def do_compress(args):
    """
    archive_path: path to the archive
    path :
    pwd
    """
    args.archive_path = _normpath(args.archive_path,args.pwd)

    _,ext = os.path.splitext(args.archive_path)

    paths = []
    for path in args.path:
        #normpath = _normpath(path,args.pwd)
        if not os.path.exists(path):
            sys.stderr.write("Not Found: %s\n"%path)
        else:
            paths.append(path)

    _compress(args.pwd, args.archive_path, paths)

    return 0;

def do_extract(args):
    """
    archive_path: path to the archive
    directory:
    pwd
    """

    args.archive_path = _normpath(args.archive_path,args.pwd)
    args.directory = _normpath(args.directory,args.pwd)

    if not os.path.exists(args.directory):
        os.makedirs(args.directory)

    if not os.path.isdir(args.directory):
        raise Exception("output not a directory")

    _extract(args.archive_path,args.directory)

    return 0;
