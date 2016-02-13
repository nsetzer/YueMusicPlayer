#! cd ../.. && python2.7 setup.py test --test=lib
#! cd ../.. && python2.7 setup.py cover
import unittest

import os
from yue.core.library import Library
from yue.core.sqlstore import SQLStore

DB_PATH = "./unittest.db"

class TestLibrary(unittest.TestCase):
    """Examples for using the cEBFS library
    """

    def __init__(self,*args,**kwargs):
        super(TestLibrary,self).__init__(*args,**kwargs)

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

        uid = lib.insert(artist="artist1",
                         album='album1',
                         title='title1',
                         path='/path')
        song =lib.songFromId(uid)

        # check required fields
        self.assertEqual(song['artist'],'artist1')
        self.assertEqual(song['album'],'album1')
        self.assertEqual(song['title'],'title1')
        self.assertEqual(song['path'],'/path')
        # check default fields
        self.assertEqual(song['playcount'],0)

        # both these values should be 1
        artists = list(lib.getArtists())
        self.assertEqual( len(artists), 1 )
        art = artists[0]['uid']
        albums = list(lib.getAlbums(art))
        self.assertEqual( len(albums), 1 )

        lib.update(uid, artist="Artist", album="Album", title="Title")

        song =lib.songFromId(uid)

        self.assertEqual(song['artist'],'Artist')
        self.assertEqual(song['album'],'Album')
        self.assertEqual(song['title'],'Title')

        lib.increment(uid,'playcount',5)
        song =lib.songFromId(uid)
        self.assertEqual(song['playcount'],5)

        lib.increment(uid,'playcount',-2)
        song =lib.songFromId(uid)
        self.assertEqual(song['playcount'],3)

        # both these values should be 1, after updating artist,album
        artists = list(lib.getArtists())
        self.assertEqual( len(artists), 1 )
        art = artists[0]['uid']
        albums = list(lib.getAlbums(art))
        self.assertEqual( len(albums), 1 )

