#! python2.7 $this
import os, sys
dirpath = os.path.dirname(os.path.abspath(__file__))
dirpath = os.path.dirname(dirpath)
sys.path.insert(0,dirpath)


from yue.library import Library
from yue.sqlstore import SQLStore
from yue.search import *

import time

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

    rule = OrSearchRule( [ PartialStringSearchRule("artist","1"),
                           PartialStringSearchRule("artist","2") ] )
    rule = AndSearchRule( [rule, PartialStringSearchRule("artist","3")] )

    print("begin naive test")
    s = time.time()
    result = list( naive_search( library.db, rule ) )
    e = time.time()
    t1 = e-s
    print(len(result), t1)

    print("begin sql test")
    s = time.time()
    result = list( sql_search( library.db, rule ) )
    e = time.time()
    t2 = e-s
    print(len(result), t2)
    print(" naive is %f times slower than sql"%(t1/t2))


if __name__ == '__main__':
    main()
