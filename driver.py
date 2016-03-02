#! python34 $this

from yue.core.sqlstore import SQLStore
from yue.core.sound.bassdevice import BassSoundDevice
from yue.core.library import Library
from yue.core.playlist import PlaylistManager
from yue.core.bass.bassplayer import BassPlayer
from yue.core.search import sql_search
from yue.core.song import Song
from yue.core.repl import YueRepl

def main():

    db_path = "./libimport.db"
    sqlstore = SQLStore(db_path)
    Library.init( sqlstore )
    PlaylistManager.init( sqlstore )

    pl = PlaylistManager.instance().openPlaylist( "current" )
    device = BassSoundDevice(pl, "./lib/win32/x86_64",True);

    songs = Library.instance().search(None, orderby=Song.random, limit=5)
    lst = [ s['uid'] for s in songs ]
    pl.set( lst )

    print( "supports float", BassPlayer.supportsFloat() )

    device.setVolume( .25 )
    device.play_index( 0 )

    YueRepl( device=device ).repl()

if __name__ == '__main__':
    main()

