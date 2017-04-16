

import os
import sys
import subprocess


def getVagrantInstances():
    """
    return a list of running virtual machines

    runs the vagrant command and parses the output
    """
    proc = subprocess.Popen(["vagrant","global-status"],
                 stdout=subprocess.PIPE,
                 stderr=subprocess.PIPE,)
    out,err = proc.communicate()
    out = out.decode("utf-8")

    available = []
    for line in out.split("\n"):
        x = line.strip().split(None,4)
        if len(x) != 5:
            continue
        state = x[3]
        directory = x[4]
        print(state,directory)
        if state.lower() == "running":
            available.append(directory)
    return available

def getVagrantSSH(cwd):
    """
    return the credentials to log into a vagrant VM

    cwd: directory containing the VagrantFile
    """
    proc = subprocess.Popen(["vagrant","ssh-config"],
                 cwd=cwd,
                 stdout=subprocess.PIPE,
                 stderr=subprocess.PIPE,)
    out,err = proc.communicate()
    out = out.decode("utf-8")

    host=None
    port=None
    user=None
    pswd=None
    ikey=None

    for line in out.split("\n"):
        x = line.strip().split(None,1)
        if len(x) != 2:
            continue
        key=x[0].lower()
        val=x[1]
        if key == "hostname":
            host = val
        elif key == "user":
            user = val
        elif key == "port":
            port = int(val)
        elif key == "identityfile":
            ikey = val

    d = {"host":host,"port":port,"user":user,"password":pswd,"key":ikey}

    return d