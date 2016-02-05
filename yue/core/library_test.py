#! cd ../.. && python2.7 setup.py test --test=library
import unittest

import os
from yue.core.library import Library
from yue.core.sqlstore import SQLStore, SQLTable

DB_PATH = "./unitteset.db"

class TestPlaylist(unittest.TestCase):
    """Examples for using the cEBFS library
    """

    def __init__(self,*args,**kwargs):
        super(TestPlaylist,self).__init__(*args,**kwargs)

    def setUp(self):
        #if os.path.exists(DB_PATH):
        #    os.remove(DB_PATH)
        pass

    def tearDown(self):
        #if os.path.exists(DB_PATH):
        #    os.remove(DB_PATH)
        pass

    def test_library_create(self):

        # removing / creating db is slow
        # therefore it is only done for this test

        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)

        sqlstore = SQLStore( DB_PATH )
        lib = Library( sqlstore )

        uid = lib.insert(artist="artist",
                         album='album',
                         title='title',
                         path='/path')
        print(uid)

        print(lib.songFromId(uid))

