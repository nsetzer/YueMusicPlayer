#! cd ../.. && python34 setup.py cover
import unittest

import os
from yue.core.playlist import PlaylistManager
from yue.core.sqlstore import SQLStore, SQLView

DB_PATH = "./unitteset.db"

class TestPlaylist(unittest.TestCase):
    """Examples for using the cEBFS library
    """

    def setUp(self):
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)

    def tearDown(self):
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)

    def test_playlist_create(self):

        sqlstore = SQLStore( DB_PATH )
        pm = PlaylistManager( sqlstore )

        pl = pm.openPlaylist("current")

        self.assertEqual(pl.size(),0)


