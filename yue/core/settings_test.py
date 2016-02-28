#! cd ../.. && python2.7 setup.py test --test=set
#! cd ../.. && python2.7 setup.py cover
import unittest

import os
from yue.core.settings import Settings
from yue.core.sqlstore import SQLStore
from yue.core.playlist import PlaylistManager

DB_PATH = "./unittest.db"

class TestSettings(unittest.TestCase):
    """Examples for using the cEBFS library
    """

    def __init__(self,*args,**kwargs):
        super(TestSettings,self).__init__(*args,**kwargs)

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_str(self):

        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)

        sqlstore = SQLStore( DB_PATH )
        s = Settings( sqlstore )

        # -------------------------------------------------
        # test inserting/retrieving a string
        key = "strkey"
        val = "strval"
        s[key] = val
        self.assertEqual( s[key], val)

        # show that a string can be overwritten
        val = "foo"
        s[key] = val
        self.assertEqual( s[key], val)

        # can't overwrite an existing value with a different type
        with self.assertRaises(ValueError):
            s[key] = 123

        # -------------------------------------------------
        # test inserting/retrieving an integer
        key = "intkey"
        val = 1474
        s[key] = val
        self.assertEqual( s[key], val)

        # show that an integer can be overwritten
        val = 42
        s[key] = val
        self.assertEqual( s[key], val)

        # can't overwrite an existing value with a different type
        with self.assertRaises(ValueError):
            s[key] = "string"

        # -------------------------------------------------
        # test inserting/retrieving a list
        key = "csvkey"
        val = ["a","b","c"]
        s[key] = val
        self.assertEqual( s[key], val)

        # show that a list can be overwritten
        val = ["a",]
        s[key] = val
        self.assertEqual( s[key], val)

        # can't overwrite an existing value with a different type
        with self.assertRaises(ValueError):
            s[key] = 123

        # -------------------------------------------------
        # setDefault only update if the key does not yet exist
        key = "default"
        val = "value"
        s.setDefault(key,val)
        self.assertEqual( s[key], val)
        s.setDefault(key,"new value")
        self.assertEqual( s[key], val)

