#! python34 $this

from yue.core.song import Song, write_tags, read_tags;

def main():
    path = "ml.mp3"

    song = read_tags( path )
    song[Song.artist] = "artist"
    song[Song.title]  = "title"
    song[Song.album]  = "album"

    write_tags( song )


if __name__ == '__main__':
    main()
