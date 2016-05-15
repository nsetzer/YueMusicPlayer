#! cd ../.. && python setup.py test --test=history
#! cd ../.. && python setup.py cover
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

        lib = Library( sqlstore )
        h = History( sqlstore )

        h.setLogEnabled(True)
        h.setUpdateEnabled(True)
        lib.history = h

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

        lib = Library( sqlstore )
        h = History( sqlstore )

        h.setLogEnabled(True)
        h.setUpdateEnabled(True)
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

    def test_history_export3(self):
        """
        show that export returns in the correct order
        """
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)

        sqlstore = SQLStore( DB_PATH )

        lib = Library( sqlstore )
        h = History( sqlstore )

        h.setLogEnabled(True)
        h.setUpdateEnabled(True)
        lib.history = h

        date = timegm(time.localtime(time.time()))

        dates = [date, date + 2, date + 4]
        uid = 0

        with h.sqlstore.conn:
            c = h.sqlstore.conn.cursor()
            for d in dates:
                h.incrementPlaycount(c,uid,d)

        records = list(h.export())
        self.assertEqual(len(records),3)
        for d,r in zip(dates,records):
            self.assertEqual(r['date'],d)

    def test_history_import_playback(self):

        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)

        sqlstore = SQLStore( DB_PATH )

        lib = Library( sqlstore )
        h = History( sqlstore )

        h.setLogEnabled(True)
        h.setUpdateEnabled(True)
        lib.history = h

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

        lib.import_record(record)

        songa = lib.songFromId( uid )

        self.assertEqual(songa[Song.last_played],songb[Song.last_played])
        self.assertEqual(songa[Song.play_count],1+songb[Song.play_count])

        new_date = 300000
        record['date'] = new_date
        lib.import_record(record)

        songa = lib.songFromId( uid )

        self.assertNotEqual(songa[Song.frequency],0)
        self.assertEqual(songa[Song.last_played],new_date)
        self.assertEqual(songa[Song.play_count],2+songb[Song.play_count])

    def test_history_import_update_str(self):
        """
        create a song, then a record which will update the
        artist name of that song

        import the record and verify that the artist name was changed
        successfully
        """
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)

        sqlstore = SQLStore( DB_PATH )

        lib = Library( sqlstore )
        h = History( sqlstore )

        h.setLogEnabled(True)
        h.setUpdateEnabled(True)
        lib.history = h

        art1 = "artist1"
        art2 = "artist2"

        uid = lib.insert(artist=art1,
                         album='album1',
                         title='title1',
                         path='/path')

        songb = lib.songFromId( uid )

        record = {'date':0,
                  'uid':uid,
                  'column':Song.artist,
                  'value':art2}

        lib.import_record(record)

        songa = lib.songFromId( uid )

        self.assertNotEqual(songb[Song.artist],songa[Song.artist])
        self.assertEqual(songa[Song.artist],art2)

    def test_history_import_update_int(self):
        """
        create a song, then a record which will update the
        rating

        import the record and verify that the artist name was changed
        successfully
        """
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)

        sqlstore = SQLStore( DB_PATH )

        lib = Library( sqlstore )
        h = History( sqlstore )

        h.setLogEnabled(True)
        h.setUpdateEnabled(True)
        lib.history = h

        rate1=5
        rate2=10
        uid = lib.insert(artist="artist1",
                         album='album1',
                         title='title1',
                         rating=rate1,
                         path='/path')

        songb = lib.songFromId( uid )

        record = {'date':0,
                  'uid':uid,
                  'column':Song.rating,
                  'value':"%s"%rate2}

        lib.import_record(record)

        songa = lib.songFromId( uid )

        self.assertNotEqual(songb[Song.rating],songa[Song.rating])
        self.assertEqual(songa[Song.rating],rate2)
