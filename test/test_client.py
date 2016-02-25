#! cd .. && python34 test/$this

import os, sys
dirpath = os.path.dirname(os.path.abspath(__file__))
dirpath = os.path.dirname(dirpath)
sys.path.insert(0,dirpath)

isPython3 = sys.version_info[0]==3
if isPython3:
    unicode = str

from yue.core.song import Song
from yue.core.sqlstore import SQLStore
from yue.core.library import Library

from yue.client.client import main as client_main

def convert():
    """ convert from old style library to new style library """
    from Song_XMLFormat import SongXML
    from Song_Object import EnumSong

    db_path = "./libimport.db"
    sqlstore = SQLStore(db_path)
    Library.init( sqlstore )

    library = Library.instance()

    columns = {
        EnumSong.UID        : "uid",
        EnumSong.PATH       : "path",
        EnumSong.ARTIST     : "artist",
        EnumSong.COMPOSER   : "composer",
        EnumSong.ALBUM      : "album",
        EnumSong.TITLE      : "title",
        EnumSong.GENRE      : "genre",
        EnumSong.DATEVALUE  : "last_played",
        EnumSong.COMMENT    : "comment",
        EnumSong.LANG       : "lang",
        EnumSong.COUNTRY    : "country",
        EnumSong.RATING     : "rating",
        EnumSong.LENGTH     : "length",
        EnumSong.SONGINDEX  : "album_index",
        EnumSong.PLAYCOUNT  : "playcount",
        EnumSong.SKIPCOUNT  : "skip_count",
        EnumSong.YEAR       : "year",
        EnumSong.OPM        : "opm",
        EnumSong.EQUALIZER  : "equalizer",
        EnumSong.DATEADDED  : "date_added",
        EnumSong.FREQUENCY  : "frequency",
        EnumSong.FILESIZE   : "file_size",
    }

    if len(library) == 0:

        xml = r"/home/nsetzer/Dropbox/ConsolePlayer/user/music.xml"
        if not os.path.exists(xml):
            xml = r
        lib = SongXML().read(xml)

        with library.sqlstore.conn:
            c = library.sqlstore.conn.cursor()
            for idx, old_song in enumerate(lib):
                print("processing %d/%d - %d : %s"%(idx,len(lib),old_song[EnumSong.UID],old_song[EnumSong.DATESTAMP]))
                new_song = Song.new()
                for field,column in columns.items():
                    new_song[column] = old_song[field]
                new_song["blocked"] = old_song.banish
                library._insert(c, **new_song)

    return library

if __name__ == '__main__':
    convert()
    client_main();
