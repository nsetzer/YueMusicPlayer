
import os, sys
dirpath = os.path.dirname(os.path.abspath(__file__))
dirpath = os.path.dirname(dirpath)
sys.path.insert(0,dirpath)

from yue.core.library import Library
from yue.core.sqlstore import SQLStore

def main():

    """
    create a library tree.

    when an artist node is expanded the databas is queried
    asynchronously for the list of child albums. then when an album
    is expanded, the database is queried again for the list of songs.

    on application startup the initial library view need only load
    the list of artists, which should be significantly smaller than the
    number of songs. this should increase loading time significantly,
    as well as only require loading parts of the library
    that will be shown on the ui.

    """

    db_path = "./libasync.db"
    sqlstore = SQLStore(db_path)
    library = Library( sqlstore )

    if len(library) == 0:
        print("recreating db")
        for i in range(40):
            song = {"artist":"art%d"%(i%7),
                    "album" :"alb%d"%(i%3),
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



def convert():
    """ convert from old style library to new style library """
    from Song_XMLFormat import SongXML
    from Song_Object import EnumSong
    from SystemDateTime import DateTime

    db_path = "./libimport.db"
    sqlstore = SQLStore(db_path)
    library = Library( sqlstore )

    columns = {
        EnumSong.UID        : "uid",
        EnumSong.PATH       : "path",
        EnumSong.ARTIST     : "artist",
        EnumSong.COMPOSER   : "composer",
        EnumSong.ALBUM      : "album",
        EnumSong.TITLE      : "title",
        EnumSong.GENRE      : "genre",
        EnumSong.DATESTAMP  : "last_played",
        EnumSong.COMMENT    : "comment",
        EnumSong.LANG       : "lang",
        EnumSong.COUNTRY    : "country",
        EnumSong.RATING     : "rating",
        EnumSong.LENGTH     : "length",
        EnumSong.SONGINDEX  : "album_index",
        EnumSong.PLAYCOUNT  : "playcount",
        EnumSong.YEAR       : "year",
    }

    xml = r"D:\Dropbox\ConsolePlayer\user\music.xml"
    lib = SongXML().read(xml)

    if len(library) == 0:
        for idx, old_song in enumerate(lib):
            print("processing %d/%d - %d"%(idx,len(lib),old_song[EnumSong.UID]))
            new_song = {}
            for field,column in columns.items():
                new_song[column] = old_song[field]
            library.insert(**new_song)

    dt = DateTime(format)
    dt.timer_start()
    songlist = list(library.iter())
    dt.timer_end();

    sys.stderr.write("Loaded %d songs from sqlite container in %s\n"%( len(songlist), DateTime.formatTimeDeltams(dt.timedelta)))




if __name__ == '__main__':
    main()
    #convert()
