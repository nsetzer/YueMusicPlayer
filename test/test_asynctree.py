
import os, sys
dirpath = os.path.dirname(os.path.abspath(__file__))
dirpath = os.path.dirname(dirpath)
sys.path.insert(0,dirpath)

from yue.core.library import Library
from yue.core.sqlstore import SQLStore

def main():

    db_path = "./libasync.db"
    sqlstore = SQLStore(db_path)
    library = Library( sqlstore )

    if len(library) == 0:
        print("recreating db")
        for i in range(40):
            song = {"artist":"art%d"%(i%7),
                    "album" :"alb%d"%(i%4),
                    "title" :"ttl%d"%(i%10),
                    "path"  :"/path/%d"%i,
                    "playcount":i,
                    "year":i%21+1990}
            library.insert(**song)
        print("finished")

    for result in library.getArtists():
        print(result)

    for result in library.getAlbums(1):
        print(result)

if __name__ == '__main__':
    main()