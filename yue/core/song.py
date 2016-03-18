
import os,sys

from calendar import timegm
import time
import datetime

from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, ID3NoHeaderError
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.asf import ASF # *.wma

ext_mp3  = (".mp3",)
ext_mp4  = ('.m4a', '.m4b', '.m4p', '.mpeg4', '.aac')
ext_asf  = ('.asf','.wma')
ext_flac = ('.flac',)

isPython3 = sys.version_info[0]==3
if isPython3:
    unicode = str

class UnsupportedFormatError(ValueError):
    pass

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
    asc = "ASC"
    desc = "DESC"

    eqfactor = 250.0

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
        "playcount"  : play_count,
        "skip"        : skip_count,
        "scnt"        : skip_count,
        "skip_count"  : skip_count,
        "skipcount"  : skip_count,
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
            Song.date_added  : timegm(time.localtime(time.time())),
            Song.play_count  : 0,
            Song.skip_count  : 0,
            Song.rating      : 0,
            Song.blocked     : 0,
            Song.equalizer   : 0,
            Song.opm         : 0,
            Song.frequency   : 0,
            Song.file_size   : 0,
        }

    @staticmethod
    def calculateFrequency(playcount, frequency, last_played):
        """ return the new frequency given the current freuquency and the
            last time the song was played

            return the current time (used to calculate days elapsed)
            with the new frequency value
        """
        N=4 # rough average over this many plays

        t1 = time.localtime(time.time())
        t2 = time.localtime(last_played)

        d1 = datetime.datetime(*t1[:6])
        d2 = datetime.datetime(*t2[:6])
        delta = d1-d2

        if playcount == 0:
            return timegm(t1), 0

        days = round(delta.days + delta.seconds/(60*60*24))

        if playcount < N:
            N = playcount

        return timegm(t1), int(((N-1)*frequency + days)/N)

    @ staticmethod
    def fromPath( path ):
        return read_tags( path )

    @staticmethod
    def supportedExtensions():
        return ext_mp3+ext_mp4+ext_asf+ext_flac

    @staticmethod
    def toString(song):
        return "%s - %s - %s"%(song[Song.artist],song[Song.album],song[Song.title])

    @staticmethod
    def toShortPath(song):
        tart = stripIllegalChars(song[Song.artist]).strip().replace(" ","_")
        tabm = stripIllegalChars(song[Song.album]).strip().replace(" ","_")
        tnam = os.path.split(song[Song.path])[1].replace(" ","_")
        tart = tart.rstrip(".") # windows...
        tabm = tabm.rstrip(".")
        tnam = tnam.rstrip(".")
        if tart == "":
            tart = "Unknown Artist"
        if tabm.lower() in ["none","unknown",""]:
            path = (tart,tnam);
        else:
            path = (tart,tabm,tnam);
        return path

    @staticmethod
    def getEqFactor(song):
        value = song[Song.equalizer]
        if value == 0:
            return 0
        ivalue = min(500,value);
        fvalue = ivalue/Song.eqfactor;
        return fvalue


def stripIllegalChars(x):
    return ''.join( [ c for c in x if c not in "<>:\"/\\|?*" ] )

# from kivy.logger import Logger

def read_tags( path ):

    song = Song.new()

    ext = os.path.splitext(path)[1].lower()

    if ext in ext_mp3:
        read_mp3_tags( song, path )
    elif ext in ext_flac:
        read_flac_tags( song, path )
    elif ext in ext_mp4:
        read_mp4_tags( song, path )
    elif ext in ext_asf:
        read_asf_tags( song, path )
    else:
        raise UnsupportedFormatError(ext)

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
    song[Song.length]       = int(audio.info.length)

def read_mp4_tags( song, path):

    audio = MP4( path )

    song[Song.artist] = get_str(audio,"\xA9ART","unkown artist")
    song[Song.album]  = get_str(audio,"\xA9alb","unkown album")
    song[Song.title]  = get_str(audio,"\xA9nam","unkown title")
    song[Song.genre]  = get_str(audio,"\xA9gen","unkown genre")
    try:
        song[Song.album_index]  = int(audio["trkn"][0][0])
    except:
        pass
    song[Song.length]       = int(audio.info.length)

def read_asf_tags( song, path):

    audio = ASF( path )

    song[Song.artist] = get_str(audio,"WM/AlbumArtist","unkown artist")
    song[Song.album]  = get_str(audio,"WM/AlbumTitle","unkown album")
    song[Song.title]  = get_str(audio,"Title","unkown title")
    song[Song.genre]  = get_str(audio,"WM/Genre","unkown genre")
    song[Song.album_index]  = get_int(audio,'WM/TrackNumber')
    song[Song.year]   = get_int(audio,"WM/Year",'-')
    song[Song.length] = int(audio.info.length)

def get_str(audio,tag,unkown=None):
    if tag in audio:
        return unicode(audio[tag][0])
    return unkown or ('unknown ' + tag)

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

def write_tags( song ):
    # raises: PermissionError, OSError, ValueError
    ext = os.path.splitext(song[Song.path])[1].lower()
    if ext in ext_mp3:
        return write_mp3_tags( song )

    raise UnsupportedFormatError(ext)

def write_mp3_tags(song):


    path = song[Song.path]
    try :
        audio = EasyID3(path)
    except ID3NoHeaderError:
        # if the tag does not exist create a new one
        audio = EasyID3()

    audio['artist'] = song[Song.artist]
    audio['title']  = song[Song.title]
    audio['album']  = song[Song.album]
    audio['length'] = str(song[Song.length])

    audio.save(path)

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

    raise ArtNotFound(song_path)

def get_album_art_data( song ):
    # song only needs to be a dictionary containing:
    #   Song.path
    #   Song.artist
    #   Song.album
    # the path could be to a file that does not exist, as long
    # as the directory does exist.
    song_path = song[Song.path]
    ext = os.path.splitext(song_path)[1].lower()

    data = None
    try:
        if ext == ".mp3":
            data = get_album_art_mp3( song_path )
        elif ext == '.flac':
            data = get_album_art_flac( song_path )
    except Exception as e:
        print("mutagen: %s"%e)

    if data is not None:
        return data

    dirname = os.path.dirname( song_path )

    names = ["cover.jpg","cover.png","folder.jpg","folder.png"]
    n = "%s - %s.jpg"%(song[Song.artist],song[Song.album])
    names.append(n)
    names.append(n.replace(" ","_"))

    for name in names:
        path = os.path.join(dirname,name)
        if os.path.exists( path ):
            with open(path,"rb") as rb:
                return rb.read()

    raise ArtNotFound(song_path)

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