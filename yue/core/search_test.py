#! cd ../.. && python2.7 setup.py cover
#! cd ../.. && python2.7 setup.py test --test=search
import unittest

import os
from yue.core.library import Library
from yue.core.search import PartialStringSearchRule, \
        InvertedPartialStringSearchRule, \
        ExactSearchRule, \
        InvertedExactSearchRule, \
        LessThanSearchRule, \
        LessThanEqualSearchRule, \
        GreaterThanSearchRule, \
        GreaterThanEqualSearchRule, \
        RangeSearchRule, \
        NotRangeSearchRule, \
        naive_search, \
        sql_search
from yue.core.sqlstore import SQLStore

DB_PATH = "./unittest.db"


class TestLibrarySearch(unittest.TestCase):
    """Examples for using the cEBFS library
    """

    def __init__(self,*args,**kwargs):
        super(TestLibrarySearch,self).__init__(*args,**kwargs)

    def setUp(self):
        #if os.path.exists(DB_PATH):
        #    os.remove(DB_PATH)
        pass

    def tearDown(self):
        #if os.path.exists(DB_PATH):
        #    os.remove(DB_PATH)
        pass

    def compare( self, library, rule, msg=""):
        """ compare the two search methods, verify they return the same results"""

        sqlview = library.song_view
        s1 = set( song['uid'] for song in naive_search( sqlview, rule ) )
        s2 = set( song['uid'] for song in sql_search( sqlview, rule ) )

        self.assertEqual(s1,s2,msg)

    def test_library_create(self):

        # removing / creating db is slow
        # therefore it is only done for this test

        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)

        sqlstore = SQLStore( DB_PATH )
        library = Library( sqlstore )

        for i in range(20):
            song = {"artist":"art%d"%i,
                    "album" :"alb%d"%i,
                    "title" :"ttl%d"%i,
                    "path"  :"/path/%d"%i,
                    "playcount":i,
                    "year":i%21+1990}
            library.insert(**song)

        self.compare( library, PartialStringSearchRule('artist','art1'), 'partial')

        self.compare( library, InvertedPartialStringSearchRule('artist','art1'), 'partial-inv')

        self.compare( library, ExactSearchRule('artist','art1'), 'eq-string')
        self.compare( library, ExactSearchRule('playcount',2000), 'eq-numeric')

        self.compare( library, InvertedExactSearchRule('artist','art1'), 'eq-string-inv')
        self.compare( library, InvertedExactSearchRule('playcount',2000), 'eq-numeric-inv')

        self.compare( library, LessThanSearchRule('playcount',2000), 'lt')
        self.compare( library, LessThanEqualSearchRule('playcount',2000), 'le')
        self.compare( library, GreaterThanSearchRule('playcount',2000), 'gt')
        self.compare( library, GreaterThanEqualSearchRule('playcount',2000), 'ge')

        self.compare( library, RangeSearchRule('playcount',1995,2005), 'range')
        self.compare( library, NotRangeSearchRule('playcount',1995,2005), 'not-range')