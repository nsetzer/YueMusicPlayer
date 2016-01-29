#! python2.7 $this
import os, sys
dirpath = os.path.dirname(os.path.abspath(__file__))
dirpath = os.path.dirname(dirpath)
sys.path.insert(0,dirpath)


from yue.library import Library
from yue.sqlstore import SQLStore
from yue.search import *

import time


def benchmark( sqlview, rule, msg=""):

    print("benchmark: %s"%msg)
    s = time.time()
    result = list( naive_search( sqlview, rule ) )
    e = time.time()
    t1 = e-s
    print("naive: found %d records in %f seconds"%(len(result), t1))

    s = time.time()
    result = list( sql_search( sqlview, rule ) )
    e = time.time()
    t2 = e-s
    print("sql: found %d records in %f seconds"%(len(result), t2))
    print("naive search is %f times slower than sql"%(t1/t2))


def compare( sqlview, rule, msg=""):
    """ compare the two search methods, verify they return the same results"""
    s1 = set( song['uid'] for song in naive_search( sqlview, rule ) )
    s2 = set( song['uid'] for song in sql_search( sqlview, rule ) )

    if s1 == s2:
        sys.stdout.write("test: %s passed.\n"%msg)
    else:
        sys.stdout.write("test: %s failed.\n"%msg)


def main():

    db_path = "./libtest.db"
    sqlstore = SQLStore(db_path)
    library = Library( sqlstore )

    try:
        library.db.get(1)
    except KeyError:
        print("recreating db")
        for i in range(2000):
            song = {"artist":"art%d"%i,
                    "album" :"alb%d"%i,
                    "title" :"ttl%d"%i,
                    "path"  :"/path/%d"%i,
                    "playcount":i,
                    "year":i%21+1990}
            library.db.insert(**song)
        print("finished")

    compare( library.db, PartialStringSearchRule('artist','art1'), 'partial')

    compare( library.db, InvertedPartialStringSearchRule('artist','art1'), 'partial-inv')

    compare( library.db, ExactSearchRule('artist','art1'), 'eq-string')
    compare( library.db, ExactSearchRule('playcount',2000), 'eq-numeric')

    compare( library.db, InvertedExactSearchRule('artist','art1'), 'eq-string-inv')
    compare( library.db, InvertedExactSearchRule('playcount',2000), 'eq-numeric-inv')

    compare( library.db, LessThanSearchRule('playcount',2000), 'lt')
    compare( library.db, LessThanEqualSearchRule('playcount',2000), 'le')
    compare( library.db, GreaterThanSearchRule('playcount',2000), 'gt')
    compare( library.db, GreaterThanEqualSearchRule('playcount',2000), 'ge')

    compare( library.db, RangeSearchRule('playcount',1995,2005), 'range')
    compare( library.db, NotRangeSearchRule('playcount',1995,2005), 'not-range')

    # test a somewhat complex rule
    rule = PartialStringSearchRule("artist","3")
    benchmark( library.db, rule, 'simple')

    # test a somewhat complex rule
    rule = OrSearchRule( [ PartialStringSearchRule("artist","1"),
                           PartialStringSearchRule("artist","2") ] )
    rule = AndSearchRule( [rule, PartialStringSearchRule("artist","3")] )

    benchmark( library.db, rule, 'complex')

    # search all useful text fields for a given string,
    # in my tests, sql is several times faster
    s = "alb2"
    rule = OrSearchRule( [ PartialStringSearchRule("artist",s),
                           PartialStringSearchRule("composer",s),
                           PartialStringSearchRule("album",s),
                           PartialStringSearchRule("title",s),
                           PartialStringSearchRule("genre",s),
                           PartialStringSearchRule("comment",s) ] )

    benchmark( library.db, rule, 'text fields')

if __name__ == '__main__':
    main()
