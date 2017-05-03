
from .song import Song

class QuickListRecord(object):
    key=0 # data key
    cnt=1 # song count
    ply=2 # total play count
    skp=3 # total skip count
    len=4 # total play time
    tme=5 # total listen time
    frq=6 # average frequency
    art=7 # unique set of artists belonging to category `key`
    SIZE=8
    map = {
        key:"Key",
        cnt:"Song Count",
        ply:"Play Count",
        skp:"Skip Count",
        len:"Play Time",
        tme:"Listen Time",
        frq:"Average Frequency",
        art:"Artists",
    }

    def __init__(self,key):
        super(QuickListRecord,self).__init__()
        self.data = [0]*(int(QuickListRecord.SIZE))
        self.data[QuickListRecord.key] = key
        self.data[QuickListRecord.art] = set()

    def __getitem__(self,idx):
        return self.data[idx]

    def __setitem__(self,idx,val):
        self.data[idx]=val

    @staticmethod
    def idx2str(idx):
        return QuickListRecord.map[idx]

def buildQuickList(songs,key_index,text_transform=None,minimum=2,filterGenre=False):

    """
    build a quick list given a set of songs
    An array of Records is returned, with each index corresponding
    to the Record enum. This produces statistics based on either
    a artist or genre.

    key_index : either Song.artist or Song.genre

    text_transform:
        a function which takes a string and returns a list of strings.

        for key_index=Song.artist use text_transform=lambda x:[x,]
        for key_index=Song.genre, split on ',' or ';'
            returns a list of all genre tags for a given song

    minimum : records are dropped if they do not meet the minimum song
              count requirment.

    filterGenre : if True, and key_index == Song.genre, filter
        genres which do not give a good artist covering.


    """

    if text_transform is None:
        text_transform = lambda x : [x,]

    data = {}

    # collect initial statistics using all songs
    for song in songs:
        skey = song[key_index]
        key_list = text_transform(skey)
        for key in key_list :
            if key not in data:
                data[key] = QuickListRecord(key)
            data[key][QuickListRecord.cnt] += 1
            data[key][QuickListRecord.ply] += song[Song.play_count]
            data[key][QuickListRecord.skp] += song[Song.skip_count]
            data[key][QuickListRecord.len] += song[Song.length]
            data[key][QuickListRecord.tme] += song[Song.play_count] * song[Song.length]
            data[key][QuickListRecord.frq] += song[Song.frequency]
            data[key][QuickListRecord.art].add(song[Song.artist])
            #data[key][c_rte] += song[Song.rating]
            #if song[MpMusic.RATING] > 0:
            #    data[key][c_rct] += 1

    # filter statistics into a sortable list
    records = []
    for key, record in data.items():
        if record[QuickListRecord.cnt] < minimum:
            continue

        if filterGenre and \
           key_index == Song.genre and \
           len(record[QuickListRecord.art])==1:
            continue

        record[QuickListRecord.frq] = int(record[QuickListRecord.frq]/record[QuickListRecord.cnt])
        records.append( record )

    return records
