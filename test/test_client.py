#! cd .. && python34 test/$this

import os, sys
dirpath = os.path.dirname(os.path.abspath(__file__))
dirpath = os.path.dirname(dirpath)
sys.path.insert(0,dirpath)
os.chdir(dirpath)

isPython3 = sys.version_info[0]==3
if isPython3:
    unicode = str

from yue.core.song import Song
from yue.core.sqlstore import SQLStore
from yue.core.library import Library
from yue.core.playlist import PlaylistManager

from yue.client.client import main as client_main

from yue.client.DSP.equalizer import main as eq_main
from yue.client.ui.openpl_dialog import main as pl_main
from yue.client.ui.newpl_dialog import main as newpl_main
from yue.client.ui.updatetags_dialog import main as ut_main
from yue.client.ui.sync_dialog import main as sync_main
from yue.client.ui.settings import main as settings_main
from yue.client.ui.song_view import main as sv_main
from yue.core.sync import main as sync_core_main

def convert():
    """ convert from old style library to new style library """
    from Song_XMLFormat import SongXML
    from Song_Object import EnumSong
    from Song_PlaylistFormat import playList_Load_M3U

    db_path = "./yue.db"
    sqlstore = SQLStore(db_path)
    Library.init( sqlstore )
    PlaylistManager.init( sqlstore )

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

        xml = r"D:/Dropbox/ConsolePlayer/user/music.xml"
        if not os.path.exists(xml):
            xml = r"/home/nsetzer/Dropbox/ConsolePlayer/user/music.xml"
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

        #m3udir=r"D:\Dropbox\ConsolePlayer\user\playlist"
        #for name in os.listdir(m3udir):
        #    shortname,ext = os.path.splitext(name)
        #    if ext == ".m3u":
        #        print(name)
        #        songs = playList_Load_M3U(os.path.join(m3udir,name),lib)
        #        print("len",len(songs),len(lib))
        #        lst = [ song[EnumSong.UID] for song in songs]
        #        pl = PlaylistManager.instance().openPlaylist( shortname )
        #        pl.set( lst )
        #        print("done")

    return library

if __name__ == '__main__':
    convert()
    print(sys.argv)

    key = "client"
    if len(sys.argv) > 1:
        key = sys.argv[1]
    programs = {
        "songview.py" : sv_main,
        "sync.py" : sync_core_main,
        "sync_dialog.py" : sync_main,
        "settings.py" : settings_main,
        "newpl_dialog.py" : newpl_main,
        "client" : client_main,
    }
    print("key: %s"%key)
    main = programs.get(key,client_main)
    main()
    #eq_main()
    #pl_main();
    #npl_main();
    #ut_main();
    #client_main();
    #sv_main();
