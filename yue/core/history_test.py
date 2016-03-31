#! cd ../.. && python2.7 setup.py test --test=history
#! cd ../.. && python2.7 setup.py cover
import unittest

import os
from yue.core.song import Song
from yue.core.library import Library
from yue.core.history import History
from yue.core.sqlstore import SQLStore
from yue.core.playlist import PlaylistManager
from calendar import timegm
import time

DB_PATH = "./unittest.db"

class TestHistory(unittest.TestCase):
    """Examples for using the library
    """

    def __init__(self,*args,**kwargs):
        super(TestHistory,self).__init__(*args,**kwargs)

    def setUp(self):
        #if os.path.exists(DB_PATH):
        #    os.remove(DB_PATH)
        pass

    def tearDown(self):
        #if os.path.exists(DB_PATH):
        #    os.remove(DB_PATH)
        pass

    def test_history_export(self):

        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)

        sqlstore = SQLStore( DB_PATH )

        h = History( sqlstore )
        h.setEnabled(True)
        date = timegm(time.localtime(time.time()))

        uid = 0

        with h.sqlstore.conn:
            c = h.sqlstore.conn.cursor()
            h.incrementPlaycount(c,uid,date)

        records = list(h.export())
        self.assertEqual(len(records),1)
        record = records[0]
        self.assertEqual(record['uid'],uid)
        self.assertEqual(record['date'],date)
        self.assertEqual(record['column'],Song.playtime)

    def test_history_export2(self):

        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)

        sqlstore = SQLStore( DB_PATH )

        h = History( sqlstore )
        h.setEnabled(True)
        lib = Library( sqlstore )
        lib.history = h

        uid = lib.insert(artist="artist1",
                         album='album1',
                         title='title1',
                         path='/path')

        lib.incrementPlaycount(uid)

        records = list(h.export())
        self.assertEqual(len(records),1)
        record = records[0]
        self.assertEqual(record['uid'],uid)
        self.assertEqual(record['column'],Song.playtime)

    def test_history_import(self):

        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)

        sqlstore = SQLStore( DB_PATH )

        h = History( sqlstore )
        lib = Library( sqlstore )

        uid = lib.insert(artist="artist1",
                         album='album1',
                         title='title1',
                         path='/path',
                         last_played=100000)

        songb = lib.songFromId( uid )


        record = {'date':50000,
                  'uid':uid,
                  'column':Song.playtime,
                  'value':None}

        with sqlstore.conn:
            c = sqlstore.conn.cursor()
            h.import_record(c,record)

        songa = lib.songFromId( uid )

        self.assertEqual(songa[Song.last_played],songb[Song.last_played])
        self.assertEqual(songa[Song.play_count],1+songb[Song.play_count])

        new_date = 300000
        record['date'] = new_date
        with sqlstore.conn:
            c = sqlstore.conn.cursor()
            h.import_record(c,record)

        songa = lib.songFromId( uid )

        self.assertNotEqual(songa[Song.frequency],0)
        self.assertEqual(songa[Song.last_played],new_date)
        self.assertEqual(songa[Song.play_count],2+songb[Song.play_count])

