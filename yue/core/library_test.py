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

        lib.update(uid, artist="The Artist", album="Album", title="Title")

        song =lib.songFromId(uid)

        self.assertEqual(song['artist'],'The Artist')
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


    def test_library_findpath(self):

        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)

        sqlstore = SQLStore( DB_PATH )
        lib = Library( sqlstore )

        lib.insert(artist="artist1",
                   album='album1',
                   title='title1',
                   path='C:\\path\\to\\file.mp3')
        lib.insert(artist="artist2",
                   album='album2',
                   title='title2',
                   path='C:/path/to/file.mp3')
        lib.insert(artist="artist3",
                   album='album3',
                   title='title3',
                   path='C:/file.mp3')

        # return the one file which is at the root directory
        res = list(lib.searchDirectory("C:\\",False))
        self.assertEqual(len(res), 1)

        # show that the search result is a song dictionary
        self.assertEqual( res[0]['artist'], 'artist3')

        # return all songs, regardless of directory or toothpicks
        res = list(lib.searchDirectory("C:\\",True))
        self.assertEqual(len(res), 3)

        # find a file that matches exactly
        res = list(lib.searchPath("C:\\file.mp3"))
        self.assertEqual(len(res), 1)