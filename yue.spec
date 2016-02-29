# -*- mode: python -*-
import os
isPosix = os.name == 'posix'
PATH_TO_DEV_ROOT = os.path.join(os.getcwd(),"")

EXT = ".exe"
ICOEXT = '.ico'
if isPosix:
    EXT = '';
    ICOEXT='.png'

def getVersionNumber(settings_path):
    """
        Returns the version number from a ConsolePlayer settings.ini file,
            or empty string if no file or version string is found
        path must be a full path to a settings file.
        no relative paths
    """
    version = "0.0.0.0";

    if os.path.exists(settings_path):
        rf = open(settings_path,"r")

        line = True

        while line:
            line = rf.readline().strip()

            i = line.index(":") # first index of a colon
            key,value = ( line[:i], line[i+1:])

            if (key == "str_VERSION"):
                version = value;
                break;

        rf.close();

    return version;

my_version = getVersionNumber(PATH_TO_DEV_ROOT+"user/settings.ini");
FULL_NAME = 'ConsolePlayer-%s.%s%s'%(my_version,os.name,EXT)

#build a debug version and look for import errors,
# add those import libraries to hidden imports list
a = Analysis(['ConsolePlayer.py'],
             pathex=[os.path.join(os.getcwd(),"yue"),],
             hiddenimports=["pkg_resources"],
             hookspath=None,
             runtime_hooks=None)

a.datas += [("lib/win32/x86_64/bass.dll",      "bass.dll",'DATA'),]
a.datas += [("lib/win32/x86_64/bassdsp.dll",   "bassdsp.dll",'DATA'),]
a.datas += [("lib/win32/x86_64/libfftw3-3.dll","libfftw3-3.dll",'DATA'),]

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
          icon= PATH_TO_DEV_ROOT+'icon'+ICOEXT)
