

import subprocess, shlex
import os,sys

def proc_exec(cmdstr,pwd=None):
    """
    pwd must be provided if it is a network path on windows.
    a network path begins with '\\' or '//'
    otherwise popen will automatically preface the path
    with the drive letter of the current working directory.
    """
    if sys.platform!="win32":
        print(("cmd:%s\npwd:%s"%(cmdstr,pwd)))
    else:
        print(("cmd:%s"%(cmdstr)).encode("utf-8"))
        print(("pwd:%s"%(pwd)).encode("utf-8"))

    try:
        args=shlex.split(cmdstr)
        subprocess.Popen(args,cwd=pwd)
    except:
        raise Exception(cmdstr)