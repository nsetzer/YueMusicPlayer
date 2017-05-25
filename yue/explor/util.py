

import subprocess, shlex
import os,sys

def safeprint(s):
    s = ("%s\n"%s)
    if sys.platform!="win32":
        sys.stdout.write(s)
    else:
        sys.stdout.write(s.encode("utf-8"))


def proc_exec(cmdstr,pwd=None,blocking=False):
    """
    pwd must be provided if it is a network path on windows.
    a network path begins with '\\' or '//'
    otherwise popen will automatically preface the path
    with the drive letter of the current working directory.
    """

    try:
        if isinstance(cmdstr,str):
            safeprint(cmdstr)
            args = shlex.split(cmdstr)
        else:
            safeprint(' '.join(cmdstr))
            args = cmdstr
        proc = subprocess.Popen(args,cwd=pwd)
        if blocking:
            proc.communicate()
    except:
        raise Exception(cmdstr)

