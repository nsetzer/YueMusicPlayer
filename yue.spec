# -*- mode: python -*-
import os,sys
isPosix = os.name != 'nt'
ROOT_PATH = os.path.join(os.getcwd(),"")

EXT = ".exe"
ICOEXT = '.ico'
if isPosix:
    EXT = '';
    ICOEXT='.png'

FULL_NAME = 'YueMusicPlayer-%s%s'%(os.name,EXT)

#build a debug version and look for import errors,
# add those import libraries to hidden imports list
a = Analysis([os.path.join(ROOT_PATH,'client-main.py'),],
             pathex=[os.path.join(os.getcwd(),"yue"),],
             hiddenimports=["pkg_resources"],
             hookspath=None,
             runtime_hooks=None)

libpath = os.path.join(ROOT_PATH,"lib", "win32", "x86_64")

#a.datas += [(os.path.join(libpath,"bass.dll"),      "bass.dll",'DATA'),]
#a.datas += [(os.path.join(libpath,"bassdsp.dll"),   "bassdsp.dll",'DATA'),]
#a.datas += [(os.path.join(libpath,"libfftw3-3.dll"),"libfftw3-3.dll",'DATA'),]

libdata = lambda name : [(name,      os.path.join(libpath,name),      'DATA'),]
a.datas += libdata("bass.dll")
a.datas += libdata("bass_aac.dll")
a.datas += libdata("bass_alac.dll")
a.datas += libdata("bassdsp.dll")
a.datas += libdata("bassflac.dll")
a.datas += libdata("bassmidi.dll")
a.datas += libdata("bassopus.dll")
a.datas += libdata("basswma.dll")
a.datas += libdata("basswv.dll")
a.datas += libdata("libfftw3-3.dll")

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
          debug=('--debug' in sys.argv),
          strip=('--strip' in sys.argv),
          upx=True,
          console=('--debug' in sys.argv),
          icon= os.path.join(ROOT_PATH,"img",'icon'+ICOEXT))
