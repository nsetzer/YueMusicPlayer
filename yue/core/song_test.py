#! cd ../.. && python2.7 setup.py test
#! cd ../.. && python2.7 setup.py cover
import unittest, time

import os
from yue.core.song import Song

class TestSong(unittest.TestCase):
    """
    """

    def __init__(self,*args,**kwargs):
        super(TestSong,self).__init__(*args,**kwargs)

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_frequency(self):

        # this test depends on the fact that a rolling average over
        # 4 points is used to calculate the frequency

        t1 = time.time() - 7*24*60*60
        freq = 0
        pcnt = 0

        t2,f = Song.calculateFrequency(pcnt,freq,t1)
        self.assertEqual(f,0)

        pcnt = 1
        t2,f = Song.calculateFrequency(pcnt,freq,t1)
        self.assertEqual(f,7)

        pcnt = 2
        t2,freq = Song.calculateFrequency(pcnt,freq,t1)
        self.assertEqual(freq,3)
