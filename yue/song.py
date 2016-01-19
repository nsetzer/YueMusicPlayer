
import os

from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3
from mutagen.flac import FLAC
from mutagen import mp3

from kivy.logger import Logger

def read_tags(path):

    ext = os.path.splitext(path)[1].lower()

    song = None
    if ext == ".mp3":
        song = read_mp3_tags( path )
    elif ext == '.flac':
        song = read_flac_tags( path )
    else:
        raise ValueError(ext)

    if song is None:
        raise ValueError("todo")

    song['playcount']=0
    song['last_played']=0
    song['rating']=0
    song['lang']=""
    song['country']=""
    song['path']=path

    return song

def read_mp3_tags(path):
    pass

    # album, artist, title, genre
    # tracknumber -> as int, parse 'x/y' and 'x' formats

    audio = EasyID3( path )

    song = {
        'artist' : get_str(audio,'artist'),
        'album'  : get_str(audio,'album'),
        'title'  : get_str(audio,'title'),
        'genre'  : get_str(audio,'genre'),
        'year'   : get_int(audio,'date','-'),
        'album_index'  : get_int(audio,'tracknumber','/'),
    }

    return song

def read_flac_tags(path):

    # album, artist, title, genre
    # tracknumber: '0x'
    # alternative: albumartist
    audio = FLAC( path )

    song = {
        'artist' : get_str(audio,'artist'),
        'album'  : get_str(audio,'album'),
        'title'  : get_str(audio,'title'),
        'genre'  : get_str(audio,'genre'),
        'year '  : get_int(audio,'year','-'),
        'album_index'  : get_int(audio,'tracknumber','/'),
    }

    return song

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
        Logger.error("mutagen: error reading %s: %s"%(tag,e))
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

    print(type(song_path))
    #if type(song_path) is str:
    #    song_path = str.decode("utf-8")

    data = None
    try:
        if ext == ".mp3":
            data = get_album_art_mp3( song_path )
        elif ext == '.flac':
            data = get_album_art_flac( song_path )
    except Exception as e:
        Logger.error("mutagen: %s"%e)

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