


class Song(object):
    """docstring for Song"""
    def __init__(self):
        super(Song, self).__init__()
        self.artist = "Unknown Artist"
        self.album  = "unknown Album"
        self.title  = "unknown Title"
        self.path = ""
        self.uid  = 0

    @staticmethod
    def New(artist,album,title,path):

        song = Song()
        song.artist = artist
        song.album  = album
        song.title  = title
        song.path   = path
        song.uid = 0

        return song
