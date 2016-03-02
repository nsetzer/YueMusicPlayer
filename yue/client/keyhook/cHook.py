#! python34 $this

"""
example useage:
use the default listener:
  listen_keyboard(KEYHOOKPROC(0));
wrap a python function
  def myproc(vkCode,scanCode):
       print(vkCode,scanCode)
       return 1
  listen_keyboard(KEYHOOKPROC(myproc));
"""
import os,sys,platform
import ctypes

def getDLLPath(dllname):

    if os.path.exists(dllname):
        return dllname;

    if hasattr(sys,"_MEIPASS"):
      return os.path.join(sys._MEIPASS,dllname)

    arch = 'x86_64'
    platform_name = sys.platform
    platform_path = os.getcwd()
    if platform.architecture()[0] != '64bit':
            arch = 'x86'
    platform_libpath = os.path.join(platform_path,'lib',
                                    platform_name,
                                    arch)

    return os.path.join(platform_libpath,dllname)

def LoadLibrary(dllname):
    if platform.system().lower() == 'windows':
        dllpath=getDLLPath(dllname+".dll")
        if not os.path.exists(dllpath):
            raise ImportError(dllpath)
        sys.stdout.write("%s\n"%dllpath)
        hook_module = ctypes.WinDLL( dllpath )
        func_type = ctypes.WINFUNCTYPE
        return hook_module, func_type
    else:
        raise ImportError(platform.system())

hook_module, func_type = LoadLibrary("hook")
INT = ctypes.c_int
USHORT = ctypes.c_ushort
DWORD = ctypes.c_ulong

KEYHOOKPROC = func_type(INT, DWORD, DWORD, DWORD, DWORD, USHORT)

hook_module
mod = lambda x : (x,hook_module)

listen_keyboard = func_type(INT,KEYHOOKPROC)(mod('listen_keyboard'))
unhook = func_type(None)(mod('unhook'))

def listen( proc ):
    listen_keyboard(KEYHOOKPROC( proc ));

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

# flag bits
KEY_SHIFT   = 0x1000
KEY_CTRL    = 0x2000
KEY_RELEASE = 0x80