
from .custom_widgets.view import TreeElem
from .song import Song

class TrackTreeElem(TreeElem):
    """ Tree Element with unique id reference to an item in a database """
    def __init__(self,uid,text):
        super(TrackTreeElem, self).__init__(text)
        self.uid = uid

class Library(object):
    """docstring for Library"""
    __instance = None
    def __init__(self):
        super(Library, self).__init__()
        self.songs = []

    @staticmethod
    def init():
        Library.__instance = Library()
        self.load()

    @staticmethod
    def test_init():
        Library.__instance = Library()

        lib = Library.__instance
                # for now, just create a dummy library of songs
        lib.songs.append(Song.New("Beast","Beast","City",""))
        lib.songs.append(Song.New("Beast","Beast","Devil",""))
        lib.songs.append(Song.New("Beast","Beast","Mr Hurricane",""))
        lib.songs.append(Song.New("The Chikitas","Butchery","Fizzy Whisky",""))
        lib.songs.append(Song.New("The Chikitas","Butchery","Anarschloch",""))
        lib.songs.append(Song.New("Myutant","Gothic Emily","Isolation",""))
        lib.songs.append(Song.New("Myutant","Gothic Emily","The Screen Behind the Pictures",""))
        #print ''.join(["\\u%0X"%ord(c) for c in u"..."])
        name=u"\u30C7\u30F3\u30B8\u30E3\u30FC\u2606\u30AE\u30E3\u30F3\u30B0"
        lib.songs.append(Song.New(name,"Gothic Emily",u"core -\u5FC3-",""))
        lib.songs.append(Song.New(name,"Unkown Story",u"Survive",""))
        lib.songs.append(Song.New(name,"Unkown Story",u"DUTY",""))
        lib.songs.append(Song.New(name,"Unkown Story",u"S -esu-",""))
        lib.songs.append(Song.New(name,"V.I.O.",u"RED DARKNESS",""))
        lib.songs.append(Song.New(name,"V.I.O.",u"bitter as death",""))
        lib.songs.append(Song.New("louna",
                u"\u0421\u0434\u0435\u043B\u0430\u0439\u0020\u0433\u0440\u043E\u043C\u0447\u0435\u0021",
                u"\u0410\u0440\u043C\u0430\u0433\u0435\u0434\u0434\u043E\u043D",""))

    @staticmethod
    def instance():
        return Library.__instance

    def load(self):

        pass
    def toTree(self):

        artists = {}

        for song in self.songs:
            if song.artist not in artists:
                artists[ song.artist ] = TreeElem(song.artist)

            album = None
            for child in artists[ song.artist ]:
                if child.text == song.album:
                    album = child
                    break;
            else:
                album = artists[ song.artist ].addChild(TreeElem(song.album))

            album.addChild(TrackTreeElem(song.uid,song.title))

        return list(artists.values())
