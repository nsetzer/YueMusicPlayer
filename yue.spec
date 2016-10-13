# -*- mode: python -*-
import os,sys
from distutils.sysconfig import get_python_lib
isPosix = os.name != 'nt'
ROOT_PATH = os.path.join(os.getcwd(),"")

EXT = ".exe"
ICOEXT = '.ico'
if isPosix:
    EXT = '';
    ICOEXT='.png'

isDebug = ('--debug' in sys.argv)

if isDebug:
  EXT="-debug"+EXT

version = '0.0.0'

main_script = os.path.join(ROOT_PATH,'client-main.py')

with open(main_script,"r") as rf:
  for line in rf:
    line = line.strip()
    if line.startswith("__version__"):
      version = line.split('=')[1].strip()[1:-1]

FULL_NAME = 'YueMusicPlayer-%s-%s%s'%(os.name,version,EXT)

# needed on some linux platforms
extra = ["six","packaging",'packaging.version',
         'packaging.specifiers','packaging.requirements',
         "yue.client"]

#build a debug version and look for import errors,
# add those import libraries to hidden imports list

a = Analysis([main_script,],
             pathex=[os.path.join(os.getcwd(),"yue"),
                     os.path.join(os.getcwd(),"yue","client") ],
             hiddenimports=["pkg_resources","PyQt5"]+extra,
             hookspath=None,
             runtime_hooks=None)

libpath = os.path.join(ROOT_PATH,"lib", sys.platform, "x86_64")

def addDllFile(a,name):
  current_path = os.path.join(libpath,name)
  if os.path.exists( current_path ):
    a.datas.append( (name, current_path, 'DATA') )

addDllFile(a,"bass.dll")
addDllFile(a,"bass_aac.dll")
addDllFile(a,"bass_alac.dll")
addDllFile(a,"bassdsp.dll")
addDllFile(a,"bassflac.dll")
addDllFile(a,"bassmidi.dll")
addDllFile(a,"bassopus.dll")
addDllFile(a,"basswma.dll")
addDllFile(a,"basswv.dll")
addDllFile(a,"libfftw3-3.dll")
addDllFile(a,"hook.dll")

def addQtPlatformDllFile(a,name):
  qtdll = os.path.join(get_python_lib(),"PyQt5","plugins","platforms",name)
  if os.path.exists( qtdll ):
    a.datas.append( (os.path.join("platforms",name), qtdll, 'DATA') )

addQtPlatformDllFile(a,"qwindows.dll")

def addQtDllFile(a,name):
  qtdll = os.path.join(get_python_lib(),"PyQt5",name)
  if os.path.exists( qtdll ):
    a.datas.append( (name, qtdll, 'DATA') )

addQtDllFile(a,"libEGL.dll")
addQtDllFile(a,"libGLESv2.dll")

# %QT_QPA_PLATFORM_PLUGIN_PATH%
# C:\Python34\Lib\site-packages\PyQt5\plugins
# QApplication.addLibraryPath(os.path.join(pyqt, "plugins"))

# workaround remove extra copies of pyconfig under --onefile
# if yopu still see an error, there may be more than 2 copies in the data.
for d in a.datas:
    if 'pyconfig' in d[0]:
        a.datas.remove(d)
        break

pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name=FULL_NAME,
          debug=isDebug,
          strip=('--strip' in sys.argv),
          upx=False,
          console=isDebug,
          icon= os.path.join(ROOT_PATH,"img",'icon'+ICOEXT))
