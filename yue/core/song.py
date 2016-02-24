
import os

from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, ID3NoHeaderError
from mutagen.flac import FLAC
from mutagen.mp3 import MP3

class Song(object):
    # column names
    uid         = 'uid'
    path        = 'path'
    source_path = 'source_path'
    artist      = 'artist'
    composer    = 'composer'
    album       = 'album'
    title       = 'title'
    genre       = 'genre'
    year        = 'year'
    country     = 'country'
    lang        = 'lang'
    comment     = 'comment'
    album_index = 'album_index' # order of song in album
    length      = 'length'
    last_played = 'last_played' # as unix time stamp
    play_count  = 'playcount'
    skip_count  = 'skip_count'
    rating      = 'rating'  # from 0 - 10
    blocked     = 'blocked' # was 'banished', type boolean
    opm         = 'opm' # used in beat detection
    equalizer   = 'equalizer' # used in automatic volume leveling
    date_added  = 'date_added' # as unix time stamp
    frequency   = 'frequency'  # how often the song is played
    file_size   = 'file_size'  # in bytes (was kb)

    # this is not a column, but stands in for all text fields.
    all_text    = "all_text"
    # this is not a column, but is used by the orderby option
    # when search / sorting a song list, causing a random ordering
    random = "RANDOM"

    abbreviations = {
        "id"          : uid,
        "uid"         : uid,
        "path"        : path,
        "src"         : source_path,
        "source_path" : source_path,
        "art"         : artist,
        "artist"      : artist,
        "composer"    : composer,
        "abm"         : album,
        "alb"         : album,
        "album"       : album,
        "ttl"         : title,
        "tit"         : title,
        "title"       : title,
        "gen"         : genre,
        "genre"       : genre,
        "year"        : year,
        "country"     : country,
        "lang"        : lang,
        "com"         : comment,
        "comm"        : comment,
        "comment"     : comment,
        "index"       : album_index,
        "album_index" : album_index,
        "len"         : length,
        "length"      : length,
        "date"        : last_played,
        "last_played" : last_played,
        "pcnt"        : play_count,
        "count"       : play_count,
        "play_count"  : play_count,
        "skip"        : skip_count,
        "scnt"        : skip_count,
        "skip_count"  : skip_count,
        "rate"        : rating,
        "rating"      : rating,
        "text"        : all_text,
        "all_text"    : all_text,
        "ban"         : blocked,
        "banned"      : blocked,
        "blocked"     : blocked,
        "opm"         : opm,
        "eq"          : equalizer,
        "equalizer"   : equalizer,
        "added"       : date_added,
        "freq"        : frequency,
        "frequency"   : frequency,
        "size"        : file_size,
        "file_size"   : file_size,
    }

    @staticmethod
    def column( abrv ):
        return Song.abbreviations[ abrv ]

    @staticmethod
    def textFields():
        return Song.artist, Song.composer, Song.album, Song.title, \
               Song.genre, Song.country, Song.lang, Song.comment

    @staticmethod
    def dateFields():
        return Song.last_played, Song.date_added;

    @staticmethod
    def new():
        return {
            Song.uid         : 0,
            Song.path        : "",
            Song.source_path : "",
            Song.artist      : "Unknown Artist",
            Song.composer    : "",
            Song.album       : "Unknown Album",
            Song.title       : "Unknown Title",
            Song.genre       : "",
            Song.year        : 0,
            Song.country     : "",
            Song.lang        : "",
            Song.comment     : "",
            Song.album_index : 0,
            Song.length      : 0,
            Song.last_played : 0,
            Song.date_added  : 0,
            Song.play_count  : 0,
            Song.skip_count  : 0,
            Song.rating      : 0,
            Song.blocked     : 0,
            Song.equalizer   : 0,
            Song.opm         : 0,
            Song.frequency   : 0,
            Song.file_size   : 0,
        }

    @ staticmethod
    def fromPath( path ):
        return read_tags( path )

# from kivy.logger import Logger

def read_tags( path):

    song = Song.new()

    ext = os.path.splitext(path)[1].lower()

    if ext == ".mp3":
        read_mp3_tags( song, path )
    elif ext == '.flac':
        read_flac_tags( song, path )
    else:
        raise ValueError(ext)

    song['path']=path

    return song

def read_mp3_tags( song, path):
    pass

    # album, artist, title, genre
    # tracknumber -> as int, parse 'x/y' and 'x' formats

    try:
        audio = EasyID3( path )
        audio2 = MP3( path )

        song[Song.artist] = get_str(audio,'artist')
        song[Song.album]  = get_str(audio,'album')
        song[Song.title]  = get_str(audio,'title')
        song[Song.genre]  = get_str(audio,'genre')
        song[Song.year]   = get_int(audio,'date','-')
        song[Song.album_index]  = get_int(audio,'tracknumber','/')
        song[Song.length]       = int(audio2.info.length)

    except ID3NoHeaderError:
        # no tag found
        # use directory as an album name, to hopefully group all
        # songs within the album
        p = os.path.splitext(path)[0]
        p,t = os.path.split(p)
        _,a = os.path.split(p)
        song[Song.album]  = a
        song[Song.title]  = t

def read_flac_tags( song, path):

    # album, artist, title, genre
    # tracknumber: '0x'
    # alternative: albumartist
    audio = FLAC( path )

    song[Song.artist] = get_str(audio,'artist')
    song[Song.album]  = get_str(audio,'album')
    song[Song.title]  = get_str(audio,'title')
    song[Song.genre]  = get_str(audio,'genre')
    song[Song.year]   = get_int(audio,'year','-')
    song[Song.album_index]  = get_int(audio,'tracknumber','/')
    song[Song.length]       = int(audio2.info.length)

def get_str(audio,tag):
    if tag in audio:
        return audio[tag][0]
    return 'unknown ' + tag

def get_int(audio,tag,split_on=None):
    try:
        if tag in audio:
            field = audio[tag][0]
            if split_on:
                field = field.split(split_on)[0]
            return int(field)
    except Exception as e:
        print("mutagen: error reading %s: %s"%(tag,e))
    return 0

class ArtNotFound(IOError):
    pass

def get_album_art( song_path, temp_path):
    """
        return a path to an album art file (jpg/png)

        if the album art is contained within the file, the file
        will be extracted to temp_path and temp_path will be
        returned. otherwise the path to the image will be returned.

        1. check the album art tag in the file
        2. check for cover.jpg / cover.png in the same directory
        3. check for folder.jpg/folder.png in the same directory
    """
    ext = os.path.splitext(song_path)[1].lower()

    #if type(song_path) is str:
    #    song_path = str.decode("utf-8")

    data = None
    try:
        if ext == ".mp3":
            data = get_album_art_mp3( song_path )
        elif ext == '.flac':
            data = get_album_art_flac( song_path )
    except Exception as e:
        print("mutagen: %s"%e)

    if data is not None:
        with open(temp_path,"wb") as wb:
            wb.write( data )
        return temp_path

    dirname = os.path.dirname( song_path )

    for name in ["cover.jpg","cover.png","folder.jpg","folder.png"]:
        path = os.path.join(dirname,name)
        if os.path.exists( path ):
            return path

    raise ArtNotFound(ext) # todo: file not found error

def get_album_art_mp3( path ):
    audio = ID3(path)
    if 'APIC' in audio:
        return audio['APIC']
    if 'covr' in audio:
        return audio['covr']
    return None

def get_album_art_flac( path ):
    audio = FLAC(path)
    if len(audio.pictures) > 0:
        return audio.pictures[0].data
    return None

if __name__ == '__main__':

    #['album', 'tracknumber', 'language', 'artist', 'date', 'title', 'genre']

    m = r"D:\Music\Discography\Discography - Beast\[2009] Beast\04-beast-interlude_1-crn.mp3"
    f = r"D:\Music\Discography\Discography - Beast\[2009] Beast\FLAC\04 Interlude 1.flac"

    s = read_tags(m)
    print(s)

    s = read_tags(f)
    print(s)