
import os,sys

from yue.explor.util import proc_exec

def _normpath(path,root=None):
    path = os.path.expanduser(path)
    if not path.startswith("/"):
        path = os.path.join(root,path)
    return path

def _mode(path):
    path,ext = os.path.splitext(path)
    mode = ext[1:].lower()
    # submode will be "tar" if it exists
    submode = os.path.splitext(path)[1][1:].lower()
    return mode,submode

def _compress(pwd, arc_path, paths):

    mode,submode = _mode(arc_path)

    if mode == "7z":
        cmd = ["7za", "a", arc_path] + paths
    elif mode == "zip":
        cmd = ["zip", arc_path] + paths
    elif mode == "gz" and submode == "tar":
        cmd = ["tar", "-czvf", arc_path] + paths
    elif mode == "bz2" and submode == "tar":
        cmd = ["tar", "-cjvf", arc_path] + paths
    else:
        raise Exception("Unrecognized mode: %s.%s"%(submode,mode))

    proc_exec(cmd, pwd, blocking=True)

def _extract(arc_path, directory):

    mode,submode = _mode(arc_path)

    if mode == "7z":
        cmd = ["7za", "x", arc_path]
    elif mode == "zip":
        cmd = ["unzip", arc_path]
    elif mode == "gz" and submode == "tar":
        cmd = ["tar", "-xzvf", arc_path]
    elif mode == "bz2" and submode == "tar":
        cmd = ["tar", "-xjvf", arc_path]
    else:
        raise Exception("Unrecognized mode: %s.%s"%(submode,mode))

    os.chdir(directory)

    proc_exec(cmd, directory, blocking=True)

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

    _extract(args.archive_path,args.directory)

    return 0;
