#! python ../../explor.py C:\\Users\\Nick\\Documents\\playground C:\\Users\\Nick\\Documents\\playground

"""
support for symlinks
    if is link : show an extra icon in the icon place

if an editor is open, shortcuts such as ctrl+c ctrl+v need to be disabled.

http://stackoverflow.com/questions/130763/request-uac-elevation-from-within-a-python-script

launchctl load -w /System/Library/LaunchAgents/com.apple.rcd.plist
cd /Applications/iTunes.app/Contents/MacOS
sudo chmod -x iTunes

sudo mkdir /Volumes/mount
sudo mount -t afp afp://user:pass@ipaddress/user /Volumes/Shared
    afp://nsetzer:password@nas-ha.cogitohealth.net/Signals_Audio
    afp://nsetzer:password@nas-ha.cogitohealth.net/Software

"""
import os,sys
if (sys.version_info[0]==2):
    raise RuntimeError("python2 not supported")
import time
from datetime import datetime
import urllib
import argparse
import traceback
from enum import Enum
import subprocess, shlex

from PyQt5.QtCore import *
# this is required so that the frozen executable
# can find `platforms/qwindows.dll`
if hasattr(sys,"_MEIPASS"):
    QCoreApplication.addLibraryPath(sys._MEIPASS)
    QCoreApplication.addLibraryPath(os.path.join(sys._MEIPASS,"qt5_plugins"))
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from sip import SIP_VERSION_STR, delete as sip_delete

from yue.core.sqlstore import SQLStore
from yue.core.settings import Settings

from yue.client import resource

from yue.explor.mainwindow import MainWindow, FileAssoc

def initSettings():

    if os.name == 'nt':
        settings_db_path = os.path.join(os.getenv('APPDATA'),"explor","settings.db")
    else:
        settings_db_path = os.path.expanduser("~/.config/explor/settings.db")

    path,_ = os.path.split(settings_db_path)

    if not os.path.exists(path):
        os.makedirs(path)

    sqlstore = SQLStore(settings_db_path)
    Settings.init( sqlstore )

    data = {}

    # basic associations by extension
    data['ext_text'] = [".txt",".log",".md",
                        ".c",".cpp",".c++",".h",".hpp", ".h++",
                        ".py", ".sh", ".pl",".bat",]
    data['ext_image'] = [".bmp",".png","jpg"]

    if sys.platform == 'darwin':
        cmd_edit_text = "\"/Applications/Sublime Text.app/Contents/SharedSupport/bin/subl\" \"%s\""
        cmd_edit_image = ""
        cmd_open_native = "open \"%s\""
        cmd_launch_terminal = "open -b com.apple.terminal \"%s\""
        cmd_diff_files = "/Applications/Beyond Compare.app/Contents/MacOS/bcomp \"%s\" \"%s\""
    elif sys.platform=="win32":

        cmd_edit_text = "\"C:\\Program Files\\Sublime Text 3\\subl.exe\" \"%s\""
        #cmd_edit_image = "mspaint.exe \"%s\""
        cmd_edit_image = "pythonw \"D:\\Dropbox\\Code\\packages\\PyPaint\\PyPaint.py\" \"%s\""
        cmd_open_native = "explorer \"%s\""
        cmd_launch_terminal = "start /D \"%s\""
        cmd_diff_files = ""
    else:
        cmd_edit_text = "subl3 \"%s\""
        cmd_edit_image = ""
        # nemo caja thunar dolphin
        cmd_open_native = "nemo \"%s\""
        cmd_launch_terminal = "xterm -e \"cd %s; bash\""
        cmd_diff_files = ""

    data["cmd_edit_text"] = cmd_edit_text
    data["cmd_edit_image"] = cmd_edit_image
    data["cmd_open_native"] = cmd_open_native
    data["cmd_launch_terminal"] = cmd_launch_terminal
    data["cmd_diff_files"] = cmd_diff_files

    #~/projects/android/YueMusicPlayer/explor.py
    if sys.platform == 'darwin':
        data["quick_access_paths"] = [
            "/root=:/img/app_folder.png=/",
            "/Favorites/home=:/img/app_folder.png=~",
            "/Favorites/Desktop=:/img/app_folder.png=~/Desktop",
            "/Favorites/Documents=:/img/app_folder.png=~/Documents",
            "/Favorites/Downloads=:/img/app_folder.png=~/Downloads",
            "/Favorites/Music=:/img/app_folder.png=~/Music",
            "/Favorites/git/kws=:/img/app_folder.png=/Users/nsetzer/git/kws",
            "/Favorites/git=:/img/app_folder.png=/Users/nsetzer/git",
            "/Favorites=:/img/app_fav.png=",
            "/NAS/Software=:/img/app_folder.png=/Volumes/Software",
            "/NAS/KWS=:/img/app_folder.png=/Volumes/Software/KeywordSpotting",
            "/NAS/Signals_Audio=:/img/app_folder.png=/Volumes/Signals_Audio",
            "/NAS=:/img/app_fav.png=",
        ]
    elif os.name == 'nt':
        data["quick_access_paths"] = [
            "/My Computer/C:\\=:/img/app_folder.png=C:\\",
            "/My Computer/D:\\=:/img/app_folder.png=D:\\",
            "/My Computer=:/img/app_folder.png=\\",
            "/Favorites=:/img/app_fav.png=",
            "/Favorites/home=:/img/app_folder.png=~",
            "/Favorites/Downloads=:/img/app_folder.png=~/Downloads",
            "/Favorites/Dropbox=:/img/app_folder.png=D:\\Dropbox",
            "/Favorites/Music=:/img/app_folder.png=D:\\Music",
            "/git/yue=:/img/app_folder.png=D:\\git\\YueMusicPlayer",
            "/git/ComicReader=:/img/app_folder.png=D:\\Dropbox\\Code\\packages\\ComicReader",
            "/git/EBFS=:/img/app_folder.png=D:\\Dropbox\\Code\\packages\\EBFS2",
            "/git=:/img/app_folder.png=D:\\git",
            "/school/CS6140=:/img/app_folder.png=D:\Dropbox\School\CS6140",
            "/school=:/img/app_folder.png=D:\\Dropbox\\School",
        ]
    else:
        data["quick_access_paths"] = [
            "/root=:/img/app_folder.png=/",
            "/Favorites/home=:/img/app_folder.png=~",
            "/Favorites/Dropbox=:/img/app_folder.png=~/Dropbox",
            "/Favorites=:/img/app_fav.png=",
        ]


    # view_show_hidden is the default value for new tabs
    # each widget supports an individual setting, which can be toggled.
    data['view_show_hidden'] = True

    Settings.instance().setMulti(data,True)

def get_modes():
    # modes change the command line syntax
    modes = {} # string -> (long-name, shortcut-flag)
    def add_mode(x,y):
        f = "-" + x
        modes["-"+x] = (y,f);
        modes["--"+y] = (y,f);
    add_mode("b","browse")
    add_mode("e","edit")
    add_mode("o","open")
    add_mode("d","diff")
    add_mode("x","extract")
    add_mode("c","compress")

    return modes

def print_help(binpath):
    sys.stdout.write("Cross Platform File Explorer and FTP Browser\n\n")
    sys.stdout.write("usage:\n  %s [-b|-c|-d|-e|-o|-x] options\n"%binpath)

    modes = [
        ("b","browse",   "open file browser"),
        ("e","edit",     "open a file for editing"),
        ("o","open",     "open a file using OS native application"),
        ("d","diff",     "compare two files"),
        ("x","extract",  "extract a file"),
        ("c","compress", "compress a set of files"),
    ]

    sys.stdout.write("extended help:\n\n")
    for x,l,h in modes:
        sys.stdout.write("  -%s  --%-8s  %s\n"%(x,l,h))

def parse_args(script_file):

    procv = sys.argv[:]
    binpath = sys.argv[0]
    argv = sys.argv[1:]
    if len(argv)>0 and argv[0] in ("-h","--help"):
        print_help(binpath);
        sys.exit(0)

    modes = get_modes()

    mode,xcut = "browse","-b"
    if len(argv)>0:
        for idx in range(len(argv)):
            opt = argv[idx]
            if opt in modes:
                # allows --edit or -e
                mode,xcut = modes[opt]
                print("++")
                procv.pop(idx+1)
                break;
            elif len(opt)>=2:
                # allows "-eh" for "edit help"
                if opt[:2] in modes:
                    mode,xcut = modes[opt[:2]]
                    new_opt = "-" + opt[2:]
                    if len(new_opt) == 1:
                        procv.pop(idx+1)
                    else:
                        procv[idx+1] = new_opt
                    break;
                elif opt[0]=="-" and opt[1]!="-": # illegal letter
                    print_help(binpath);
                    sys.exit(0)
    procv[0] = binpath + " " + xcut
    print(procv)

    parser = argparse.ArgumentParser(\
        description="Cross Platform File Explorer and FTP Browser",
        usage = "explor [-b|-c|-d|-e|-o|-x] options")

    parser.add_argument("--bg",dest="bg",action="store_true",
                        help="run gui as background task")
    parser.add_argument("--pwd",dest="pwd",type=str,default=os.getcwd(),
                        help="working directory for relative paths given")

    if mode == "compress":
        parser.add_argument("archive_path",type=str,nargs='?',
                        help="a secondary file or directory to display")
        parser.add_argument("files",type=str,nargs='+',
                        help="a secondary file or directory to display")
    elif mode == "extract":
        parser.add_argument("archive_path",type=str,nargs='?',
                        help="a secondary file or directory to display")
        parser.add_argument("directory",type=str,nargs='+',
                        help="a secondary file or directory to display")
    else:
        parser.add_argument("path",type=str,nargs='?', default = "",
                        help="a file or directory path to open")
        if mode in {"diff","browse"}:
            parser.add_argument("path_r",type=str,nargs='?',default="",
                            help="a secondary file or directory to display")

    args = parser.parse_args(procv[1:])

    if mode not in {"diff","browse"}:
        args.path_r = None

    if args.path:
        args.path = os.path.expanduser(args.path)

        if not args.path.startswith("/"):
            args.path = os.path.join(args.pwd,args.path)

        if mode == "open":
            # open the file using user defined the OS native method
            cmdstr = Settings.instance()['cmd_open_native']
            cmdstr = cmdstr%args.path
            args=shlex.split(cmdstr)
            subprocess.Popen(args)
            sys.exit(0)

        if os.path.isfile(args.path):
            #if mode == "edit" or FileAssoc.isText(args.path):
            if mode == "edit":
                # open the file for editing using the
                cmdstr = Settings.instance()['cmd_edit_text']
                cmdstr = cmdstr%(args.path)
                args=shlex.split(cmdstr)
                subprocess.Popen(args)
                sys.exit(0)
            else:
                # its a file, display the containing directory
                args.path,_ = os.path.split(args.path)
    else:
        args.path = args.pwd

    if args.path_r:
        args.path_r = os.path.expanduser(args.path_r)

        if not args.path_r.startswith("/"):
            args.path_r = os.path.join(args.pwd,args.path_r)

        if os.path.isfile(args.path_r):
            args.path_r,_ = os.path.split(args.path_r)

    if mode == "diff":
        cmdstr = Settings.instance()['cmd_diff_files']
        cmd=cmdstr%(args.path,args.path_r)
        args=shlex.split(cmd)
        subprocess.Popen(args)
        sys.exit(0)

    if args.bg:
        # user requested to run this process in the background
        # execute the process again, as a background task, then exit
        # (the double fork trick doesnt play nicely with Qt)
        # this wont work when frozen
        # detach stdout from the current shell

        argv=[sys.executable,script_file,"-b",args.path]
        if args.path_r:
            argv.append(args.path_r)
        environ=os.environ.copy()
        # TODO: this breaks windows
        environ['PATH']=':'.join(sys.path)
        subprocess.Popen(argv,cwd=os.getcwd(), \
                stderr= subprocess.DEVNULL,
                stdout= subprocess.DEVNULL,
                env = environ)
        sys.exit(0)

    return args

def handle_exception(exc_type, exc_value, exc_traceback):
    for line in traceback.format_exception(exc_type,exc_value,exc_traceback):
        print(line)

def main(script_file=__file__):
    initSettings()
    args = parse_args(script_file)

    app = QApplication(sys.argv)
    app.setApplicationName("explor")
    #app_icon = QIcon(':/img/icon.png')
    #app.setWindowIcon(app_icon)
    app.setQuitOnLastWindowClosed(True)

    sys.excepthook = handle_exception

    window = MainWindow(args.path,args.path_r)

    window.showWindow()

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()