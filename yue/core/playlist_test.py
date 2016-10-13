#! cd ../.. && python setup.py test --test=playlist
import unittest

import os
from yue.core.playlist import PlaylistManager, reinsertList
from yue.core.sqlstore import SQLStore

DB_PATH = "./unittest.db"
PL_NAME = 'demo'

class TestPlaylist(unittest.TestCase):
    """Examples for using the playlist
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

    def test_playlist_create(self):

        # removing / creating db is slow
        # therefore it is only done for this test

        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)

        sqlstore = SQLStore( DB_PATH )
        pm = PlaylistManager( sqlstore )

        pl = pm.openPlaylist(PL_NAME)

        self.assertEqual(pl.size(),0)

        data = [1,2,3,4,5]
        pl.set( data )

        self.assertEqual(pl.size(), len(data) )

    def test_playlist_append(self):

        sqlstore = SQLStore( DB_PATH )
        pm = PlaylistManager( sqlstore )
        pl = pm.openPlaylist(PL_NAME)
        pl.set( [] )

        self.assertEqual(pl.size(),0)

        pl.append( 10 )
        self.assertEqual(pl.size(),1)
        self.assertEqual(pl.get(0),10)

        pl.append( 20 )
        self.assertEqual(pl.size(),2)
        self.assertEqual(pl.get(1),20)

    def test_playlist_insert_begin(self):

        sqlstore = SQLStore( DB_PATH )
        pm = PlaylistManager( sqlstore )
        pl = pm.openPlaylist(PL_NAME)
        pl.set( [1,2,3,4,5] )

        first = pl.get(0)
        size = pl.size()

        value = 10
        pl.insert(0,value)
        self.assertEqual(pl.size(), size+1 )
        new_first = pl.get(0)
        self.assertEqual(new_first,value)
        new_second = pl.get(1)
        self.assertEqual(new_second,first)

    def test_playlist_insert_middle(self):

        sqlstore = SQLStore( DB_PATH )
        pm = PlaylistManager( sqlstore )
        pl = pm.openPlaylist(PL_NAME)
        pl.set( [1,2,3,4,5] )

        size = pl.size()

        value = 10
        pl.insert(size//2,value)
        self.assertEqual(pl.size(), size+1 )
        new_value = pl.get(size//2)
        self.assertEqual(new_value,value)


    def test_playlist_insert_end(self):

        sqlstore = SQLStore( DB_PATH )
        pm = PlaylistManager( sqlstore )
        pl = pm.openPlaylist(PL_NAME)
        pl.set( [1,2,3,4,5] )

        size = pl.size()

        value = 10
        pl.insert(size,value)
        self.assertEqual(pl.size(), size+1 )
        new_value = pl.get(size)
        self.assertEqual(new_value,value)

    def test_playlist_insert_end2(self):

        sqlstore = SQLStore( DB_PATH )
        pm = PlaylistManager( sqlstore )
        pl = pm.openPlaylist(PL_NAME)
        pl.set( [1,2,3,4,5] )

        size = pl.size()

        value = 10
        pl.insert( 200 ,value)
        self.assertEqual(pl.size(), size+1 )
        new_value = pl.get(size)
        self.assertEqual(new_value,value)

    @unittest.skip("undefined behavior")
    def test_playlist_insert_beyond_end(self):

        sqlstore = SQLStore( DB_PATH )
        pm = PlaylistManager( sqlstore )
        pl = pm.openPlaylist(PL_NAME)
        pl.set( [1,2,3,4,5] )

        size = pl.size()

        value = 10
        pl.insert(size+1,value)
        self.assertEqual(pl.size(), size+1 )

        # TODO: undefined behavior.
        new_value = pl.get(size)
        self.assertEqual(new_value,value)

    def test_playlist_delete(self):

        sqlstore = SQLStore( DB_PATH )
        pm = PlaylistManager( sqlstore )
        pl = pm.openPlaylist(PL_NAME)
        pl.set( [1,2,3,4,5] )

        # delete first
        pl.delete(0)
        self.assertEqual(pl.get(0),2)

        # delete last
        pl.delete( pl.size() - 1 )
        self.assertEqual(pl.get( pl.size() - 1 ), 4)

        # delete middle
        pl.delete( pl.size() // 2 )
        self.assertEqual(pl.size(), 2)
        self.assertEqual(pl.get(0), 2)
        self.assertEqual(pl.get(1), 4)

    # TODO: delete empty, delete beyond

    def test_playlist_reinsert_simple(self):

        sqlstore = SQLStore( DB_PATH )
        pm = PlaylistManager( sqlstore )
        pl = pm.openPlaylist(PL_NAME)
        pl.set( [1,2,3,4,5] )

        pl.reinsert( 3, 1 )

        expected = [1 , 4, 2, 3, 5]
        for i,v in enumerate(expected):
            actual = pl.get(i)
            self.assertEqual( actual, v, "%d %d"%(v,actual))
        idx,key = pl.current()
        self.assertEqual(idx,0)
        self.assertEqual(key,1)

        # move current into the middle
        pl.reinsert( 0, 2 )
        expected = [4, 2, 1, 3, 5]
        for i,v in enumerate(expected):
            actual = pl.get(i)
            self.assertEqual( actual, v, "%d %d"%(v,actual))
        idx,key = pl.current()
        self.assertEqual(idx,2)
        self.assertEqual(key,1)

        # move one below current above
        pl.reinsert( 4, 0 )
        expected = [ 5, 4, 2, 1, 3]
        actual = []
        for i in range(len(expected)):
            actual.append( pl.get(i) )
        self.assertEqual( actual, expected, "%s %s"%(expected,actual))
        idx,key = pl.current()
        self.assertEqual(idx,3)
        self.assertEqual(key,1)

        # move one above current below
        pl.reinsert( 0, 4 )
        expected = [4, 2, 1, 3, 5]
        actual = []
        for i in range(len(expected)):
            actual.append( pl.get(i) )
        self.assertEqual( actual, expected, "%s %s"%(expected,actual))
        idx,key = pl.current()
        self.assertEqual(idx,2)
        self.assertEqual(key,1)

    def test_reinsertList(self):

        lst = [1,2,3,4,5]

        def _assert(actual,expected):
            for i,v in enumerate(expected):
                self.assertEqual( actual[i], v, "error at position %d actual:%s expected:%s"%(i, actual, expected))

        # insert at selection index, no change
        sel = [2,]
        out,_,_,_ = reinsertList( lst, sel, sel[0] )
        _assert(out,[1, 2, 3, 4, 5])

        # insert at zero
        sel = [2,]
        out,_,_,_ = reinsertList( lst, sel, 0 )
        _assert(out,[3, 1, 2, 4, 5])

        # drop on last element
        sel = [2,]
        out,_,_,_ = reinsertList( lst, sel, len(lst)-1 )
        _assert(out,[1, 2, 4, 3, 5])

         # drop below last element
        sel = [2,]
        out,_,_,_ = reinsertList( lst, sel, len(lst) )
        _assert(out,[1, 2, 4, 5, 3])

        # reinsert, where insert index is beyond length of list
        sel = [0,1,2]
        out,_,_,_ = reinsertList( lst, sel, 17 )
        _assert(out,[4, 5, 1, 2, 3])

    def test_playlist_shuffle(self):
        sqlstore = SQLStore( DB_PATH )
        pm = PlaylistManager( sqlstore )
        pl = pm.openPlaylist(PL_NAME)
        pl.set( [1,2,3,4,5] )

        pl.shuffle_range( 1, 3 )
        # these two values should be the same every time.
        key = pl.get(0)
        self.assertEqual(1,key)
        key = pl.get(4)
        self.assertEqual(5,key)

    # TODO: somehow test shuffle range
    #    [0:n] should include index 0 to n
    #    [n:end] should include n and end


    def test_playlist_next_prev(self):
        sqlstore = SQLStore( DB_PATH )
        pm = PlaylistManager( sqlstore )
        pl = pm.openPlaylist(PL_NAME)
        pl.set( [1,2,3,4,5] )

        idx,key = pl.current()
        self.assertEqual(idx,0)
        self.assertEqual(key,1)

        idx,key = pl.next()
        self.assertEqual(idx,1)
        self.assertEqual(key,2)

        idx,key = pl.prev()
        self.assertEqual(idx,0)
        self.assertEqual(key,1)

        with self.assertRaises(StopIteration):
            pl.prev()

        pl.set_index(4)
        with self.assertRaises(StopIteration):
            pl.next()