#! cd ../.. && python2.7 setup.py test

"""
todo: none of these tests actually check that the correct answer is returned,
only that the answers for applying rules, vs using sql match.
"""

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
        AndSearchRule, \
        OrSearchRule, \
        naive_search, \
        sql_search
from yue.core.sqlstore import SQLStore

DB_PATH = "./unittest.db"

sqlstore = None
sqlview = None

def setUpModule():

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    global sqlstore
    global sqlview

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

    sqlview = library.song_view

def tearDownModule():

    global sqlstore
    global sqlview

    sqlstore.close()

class TestSearchMeta(type):
    """
    Build a Search Test class.
    search test follow a forumla, compare output from two different search
    methods. This class builds a Test Class where each method in the class
    is a test the same test, with different parameters

    """
    def __new__(cls, name, bases, dict):

        def gen_compare_test(rule):
            def test(self):
                global sqlview
                s1 = set( song['uid'] for song in naive_search( sqlview, rule ) )
                s2 = set( song['uid'] for song in sql_search( sqlview, rule ) )
                self.assertEqual(s1, s2)
            return test

        def gen_compare_rule_test(rule1,rule2):
            def test(self):
                global sqlview
                s1 = set( song['uid'] for song in sql_search( sqlview, rule1 ) )
                s2 = set( song['uid'] for song in sql_search( sqlview, rule2 ) )
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

        rules = [ PartialStringSearchRule('artist','art1'),
                  InvertedPartialStringSearchRule('artist','art1'),
                  ExactSearchRule('artist','art1'),
                  ExactSearchRule('playcount',2000),
                  InvertedExactSearchRule('artist','art1'),
                  InvertedExactSearchRule('playcount',2000),
                  rng1, rng2, gt1, gt2, lt1, lt2]

        for i, rule in enumerate(rules):
            test_name = "test_rule_%d" % i
            dict[test_name] = gen_compare_test(rule)

        dict["test_and"] = gen_compare_rule_test(AndSearchRule([gt1,lt1]), rng1)
        dict["test_or"] = gen_compare_rule_test(OrSearchRule([lt2,gt2]), rng2)

        return type.__new__(cls, name, bases, dict)

class TestSearch(unittest.TestCase):
    __metaclass__ = TestSearchMeta

    # python 2.7, 3.2 only, could be a better way to set up the db

    #@classmethod
    #def setUpClass(cls):
    #    pass

    #@classmethod
    #def tearDownClass(cls):
    #    pass
