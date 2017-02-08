#! cd ../.. && python setup.py test
#! C:\\Python35\\python.exe $this

"""
todo: none of these tests actually check that the correct answer is returned,
only that the answers for applying rules, vs using sql match.
"""

import unittest
import os
import datetime
import calendar
import traceback
from .util import with_metaclass

from .library import Library
from .search import SearchGrammar, \
        FormatConversion, \
        PartialStringSearchRule, \
        InvertedPartialStringSearchRule, \
        ExactSearchRule, \
        InvertedExactSearchRule, \
        LessThanSearchRule, \
        LessThanEqualSearchRule, \
        GreaterThanSearchRule, \
        GreaterThanEqualSearchRule, \
        RangeSearchRule, \
        NotRangeSearchRule, \
        AndSearchRule, \
        OrSearchRule, \
        naive_search, \
        sql_search
from .sqlstore import SQLStore

DB_PATH = "./unittest.db"

def extract(field, items):
    return set( item[field] for item in items )

class TestSearchMeta(type):
    """
    Build a Search Test class.
    search test follow a forumla, compare output from two different search
    methods. This class builds a Test Class where each method in the class
    runs the same test with different parameters

    """
    def __new__(cls, name, bases, attr):

        def gen_compare_test(rule):
            """ check that a given rule returns the same results,
                using the sql expression, or directly applying the rule """
            def test(self):
                s1 = extract( 'uid', naive_search( self.sqlview, rule ) )
                s2 = extract( 'uid', sql_search( self.sqlview, rule ) )
                self.assertEqual(s1, s2)
            return test

        def gen_compare_count_test(rule,count):
            """ check that a rule returns the expected number of results"""
            def test(self):
                s1 = extract( 'uid', sql_search( self.sqlview, rule ) )
                self.assertEqual(len(s1), count)
            return test

        def gen_compare_rule_test(rule1,rule2):
            """ check that two different rules return the same results """
            def test(self):
                s1 = extract( 'uid', sql_search( self.sqlview, rule1 ) )
                s2 = extract( 'uid', sql_search( self.sqlview, rule2 ) )
                self.assertEqual(s1, s2)
            return test

        rng1 = RangeSearchRule('playcount',1995,2005)
        rng2 = NotRangeSearchRule('playcount',1995,2005)

        # show that two rules combined using 'and' produce the expected result
        gt1=GreaterThanEqualSearchRule('playcount',1995)
        lt1=LessThanEqualSearchRule('playcount',2005)

        # show that two rules combined using 'or' produce the correct result
        lt2=LessThanSearchRule('playcount',1995)
        gt2=GreaterThanSearchRule('playcount',2005)

        pl1 = PartialStringSearchRule('artist','art1')
        pl2 = InvertedPartialStringSearchRule('artist','art1')
        rules = [ pl1,
                  pl2,
                  ExactSearchRule('artist','art1'),
                  ExactSearchRule('playcount',2000),
                  InvertedExactSearchRule('artist','art1'),
                  InvertedExactSearchRule('playcount',2000),
                  rng1, rng2, gt1, gt2, lt1, lt2]

        for i, rule in enumerate(rules):
            test_name = "test_rule_%d" % i
            attr[test_name] = gen_compare_test(rule)

        attr["test_and"] = gen_compare_rule_test(AndSearchRule([gt1,lt1]), rng1)
        attr["test_or"] = gen_compare_rule_test(OrSearchRule([lt2,gt2]), rng2)

        attr["test_pl1"] = gen_compare_count_test(pl1,11)
        attr["test_pl2"] = gen_compare_count_test(pl2, 9)

        return super(TestSearchMeta,cls).__new__(cls, name, bases, attr)

@with_metaclass(TestSearchMeta)
class TestSearch(unittest.TestCase):

    # python 2.7, >3.2

    @classmethod
    def setUpClass(cls):
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)

        cls.sqlstore = SQLStore( DB_PATH )
        library = Library( cls.sqlstore )

        for i in range(20):
            song = {"artist":"art%d"%i,
                    "album" :"alb%d"%i,
                    "title" :"ttl%d"%i,
                    "path"  :"/path/%d"%i,
                    "playcount":i,
                    "year":i%21+1990}
            library.insert(**song)

        cls.sqlview = library.song_view


    @classmethod
    def tearDownClass(cls):

        cls.sqlstore.close()


class TestSearchGrammar(unittest.TestCase):
    """
    """
    def __init__(self,*args,**kwargs):
        super(TestSearchGrammar,self).__init__(*args,**kwargs)

    def setUp(self):

        self.sg = SearchGrammar();


    def tearDown(self):
        pass

    def test_date_delta(self):

        dtn = datetime.datetime(2015,6,15)
        fc = FormatConversion( dtn );

        # show that we can subtract one month and one year from a date
        dt = fc.computeDateDelta(dtn.year,dtn.month,dtn.day,1,1)
        self.assertEqual(dt.year,dtn.year-1)
        self.assertEqual(dt.month,dtn.month-1)
        self.assertEqual(dt.day,dtn.day)

        # there is no february 31st, so the month is incremented
        # to get the day value to agree
        dt = fc.computeDateDelta(2015,3,31,0,1)
        self.assertEqual(dt.year ,2015)
        self.assertEqual(dt.month,3)
        self.assertEqual(dt.day  ,3)

        # december is a special case, and subtracting (0,0) uncovered it.
        dt = fc.computeDateDelta(2016,12,1,0,0)
        self.assertEqual(dt.year ,2016)
        self.assertEqual(dt.month,12)
        self.assertEqual(dt.day  ,1)

        dt = fc.computeDateDelta(2016,11,1,1,0)
        self.assertEqual(dt.year ,2015)
        self.assertEqual(dt.month,11)
        self.assertEqual(dt.day  ,1)

        dt = fc.computeDateDelta(2017,2,1,0,2) # 0 month bug
        self.assertEqual(dt.year ,2016)
        self.assertEqual(dt.month,12)
        self.assertEqual(dt.day  ,1)

        dt = fc.computeDateDelta(2017,2,15,0,1,15) # check delta day
        self.assertEqual(dt.year ,2016)
        self.assertEqual(dt.month,12)
        self.assertEqual(dt.day  ,31)

        # show that days can be subtracted correctly
        t1,t2 = fc.formatDateDelta("1y1m1w1d")
        dt = datetime.datetime(dtn.year-1,dtn.month-1,dtn.day-8)
        self.assertEqual(t1,calendar.timegm(dt.timetuple()))

    def test_date_format(self):

        dtn = self.sg.fc.datetime_now = datetime.datetime(2015,6,15);
        self.sg.autoset_datetime = False

        t1,t2 = self.sg.fc.formatDate("2015/6/15")
        self.assertEqual(t1,calendar.timegm(datetime.datetime(2015,6,15).timetuple()))

        t1,t2 = self.sg.fc.formatDate("15/06/15")
        self.assertEqual(t1,calendar.timegm(datetime.datetime(2015,6,15).timetuple()))

        t1,t2 = self.sg.fc.formatDate("75/06/15")
        self.assertEqual(t1,calendar.timegm(datetime.datetime(1975,6,15).timetuple()))



