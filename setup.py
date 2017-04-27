#! python setup.py install

import imp,os,sys
from setuptools import setup, Command
#from distutils.core import setup, Command
from distutils.sysconfig import get_python_lib
import unittest
import shutil

name='yue'

class UnitTest(Command):
    """run package unit tests
       e.g. python34 setup.py test --test=bf
    """
    description = __doc__
    user_options = [
         ("test=",None,"named test to run"),
         ]
    def initialize_options(self):
        self.test = None

    def finalize_options(self):
        pass

    def run(self):
        verbosity = 2 if "-v" in sys.argv else 1

        test_loader = unittest.defaultTestLoader
        test_runner = unittest.TextTestRunner(verbosity=verbosity)
        ptn=""
        if self.test:
          ptn = "*"+self.test
        #test_suite = test_loader.discover("./%s"%name,pattern="%s*_test.py"%ptn)
        test_suite = test_loader.discover("./%s"%name,pattern="%s*_test.py"%ptn)
        return test_runner.run(test_suite)

class Coverage(Command):
    """

    INSTALL:
      pip install coverage
    """
    description = __doc__
    user_options = []
    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def _exec(self,*args):
      cmd=' '.join(args)
      print(cmd)
      os.system(cmd)

    def run(self):
      self._exec("coverage run setup.py test")
      #self._exec("coverage report -m")
      self._exec("coverage html")

pkg_sys = "win32" if os.name=="nt" else "linux"
pkg_fix = ""      if os.name=="nt" else "lib"
pkg_ext = ".dll"  if os.name=="nt" else ".so"
pkg_lib = os.path.join(".","lib",pkg_sys,"x86_64")
libnames = ["bass","bassdsp",
            "bass_aac","bass_alac","bassflac",
            "bassmidi","bassopus","basswma",
            "basswv"]
lib_paths = []
for libname in libnames:
  path = os.path.join(pkg_lib,pkg_fix+libname+pkg_ext)
  if os.path.exists(path):
    lib_paths.append(path)
data_files = [("lib",lib_paths),]

# entry_points in the form "genPron = viragelm.pron.genPron:main"
#entry_points = [ "yue-music = yue.app:main", ]
# windows 10 requires the following registry change for entry points to work
# [HKEY_CLASSES_ROOT\Applications\python.exe\shell\open\command]
# @="\"C:\\Python25\\python.exe\" \"%1\" %*"
entry_points = ["explor2=yue.explor.explor:main"]

setup(name=name,
      version='1.0',
      description="Yue Music Player",
      packages=[name,
                'yue.core',
                "yue.core.bass",
                "yue.core.explorer",
                "yue.core.sound",
                "yue.core.SymTr",
                "yue.core.vlc",
                "yue.client",
                "yue.client.ui",
                "yue.qtcommon",
                "yue.qtcommon.explorer",
                "yue.explor"],
      install_requires=[
        'mutagen',
      ],
      data_files=data_files,
      cmdclass = {'test': UnitTest,
                  'cover' : Coverage},
      entry_points={"gui_scripts":entry_points},
      )
