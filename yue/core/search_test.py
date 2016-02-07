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

def extract(field, items):
    return set( item[field] for item in items )

class TestSearchMeta(type):
    """
    Build a Search Test class.
    search test follow a forumla, compare output from two different search
    methods. This class builds a Test Class where each method in the class
    runs the same test with different parameters

    """
    def __new__(cls, name, bases, dict):

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
            dict[test_name] = gen_compare_test(rule)

        dict["test_and"] = gen_compare_rule_test(AndSearchRule([gt1,lt1]), rng1)
        dict["test_or"] = gen_compare_rule_test(OrSearchRule([lt2,gt2]), rng2)

        dict["test_pl1"] = gen_compare_count_test(pl1,11)
        dict["test_pl2"] = gen_compare_count_test(pl2, 9)

        return type.__new__(cls, name, bases, dict)

class TestSearch(unittest.TestCase):
    __metaclass__ = TestSearchMeta

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