# -*- mode: python -*-
import os,sys
import subprocess

from distutils.sysconfig import get_python_lib
isPosix = os.name != 'nt'
ROOT_PATH = os.path.join(os.getcwd(),"")

EXT = ".exe"
ICOEXT = '.ico'
if isPosix:
    EXT = '';
    ICOEXT='.png'

isDebug = ('--debug' in sys.argv)

def getCommit():
    commit="none"
    date=""
    time=""
    args = ['git','log','--pretty=format:%h %ci','-1']
    proc = subprocess.Popen(args,stdout=subprocess.PIPE)
    try:
        o,_ = proc.communicate()
        o = o.decode('utf-8')
        print(o)
        commit,date,time,_  = o.split()
    except (OSError,ValueError) as e:
        print("%s"%e)
    return commit,date,time

commit,c_date,c_time = getCommit()

if isDebug:
  EXT="-debug"+EXT

version = '0.0.0'

main_script = os.path.join(ROOT_PATH,'client-main.py')
target_script = os.path.join(ROOT_PATH,'client-main-freeze.py')

with open(target_script,"w") as wf:
  with open(main_script,"r") as rf:
    for line in rf:
      temp = line.strip()
      if temp.startswith("__version__"):
        version = temp.split('=')[1].strip()[1:-1]
        wf.write("__version__ = \"%s.%s\"\n"%(version,commit))
        # adding commit is actually more annoying than you would believe
        #version += "." + commit
      elif temp.startswith("__datetime__"):
        wf.write("__datetime__ = \"%s %s\"\n"%(c_date,c_time))
      else:
        wf.write( line )

FULL_NAME = 'YueMusicPlayer-%s-%s%s'%(os.name,version,EXT)

#build a debug version and look for import errors,
# add those import libraries to hidden imports list
a = Analysis([target_script,],
             pathex=[os.path.join(os.getcwd(),"yue"),],
             hiddenimports=["pkg_resources","PyQt5"],
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

if os.path.exists(target_script):
  os.remove(target_script)