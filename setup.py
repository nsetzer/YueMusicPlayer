#! python34 setup.py test

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

# entry_points in the form "genPron = viragelm.pron.genPron:main"
#entry_points = [ "yue-music = yue.app:main", ]
entry_points = []

setup(name=name,
      version='1.0',
      description="Encrypted Block File System",
      packages=[name],
      data_files=[],
      cmdclass = {'test': UnitTest,
                  'cover' : Coverage},
      entry_points={"console_scripts":entry_points},
      )
