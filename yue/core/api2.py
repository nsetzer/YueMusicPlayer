
import os
import ssl
import urllib
import urllib.request
import json
from io import BytesIO
import gzip
import base64

from .song import Song
from .history import History

_key_map = {
    "uid": "ref_id",
    "playcount": "play_count",
    "lang": "language",
    "path": "file_path"
}
def remap_keys(song):
    """convert the old song format to the new format"""
    for akey, bkey in _key_map.items():
        if akey in song:
            song[bkey] = song[akey]
            del song[akey]
    del song["opm"]
    del song["file_size"]
    return song

def remap_keys_r(song):
    """ convert the new song format to the old format"""
    for akey, bkey in _key_map.items():
        if bkey in song:
            song[akey] = song[bkey]
            del song[bkey]
    song["opm"] = 0
    song["file_size"] = 0
    return song

class ApiClient(object):
    """docstring for ApiClient"""
    def __init__(self, hostname):
        super(ApiClient, self).__init__()

        self.hostname = hostname
        self.key = ""
        self.username = ""
        self.token = ""

        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE

    def setApiKey(self, key):
        self.key = key
        self.token = "APIKEY %s" % key

    def setApiUser(self, username):
        self.username = username

    def getHostName(self):
        return self.hostname

    def getUserName(self):
        return self.username

    def getApiKey(self):
        return self.key

    def login(self, username, password):
        urlpath = "api/user"
        headers = dict()
        s = ("%s:%s" % (username, password)).encode("utf-8")
        self.token = "Basic %s" % (base64.b64encode(s).decode("utf-8"))
        headers['Authorization'] = self.token
        url = "%s/%s" % (self.hostname, urlpath)
        request = urllib.request.Request(url, method='GET', headers=headers)
        r = urllib.request.urlopen(request, context=self.ctx)
        result = json.loads(r.read().decode("utf-8"))
        return result['result']

    def history_get(self, start=0, end=None, page=0, page_size=500, callback=None):
        params = {
            "start": 0,
            "page": page,
            "page_size": page_size
        }
        if end:
            params['end'] = end

        r = self._get("api/library/history", params)
        result = json.loads(r.read().decode("utf-8"))
        return result

    def history_put(self, data, page_size=500, callback=None):
        """
        data as a list of records for a particular user
            {timestamp:number, song_id: string}
        """
        headers = {"Content-Type": "application/json"}
        for i in range(0, len(data), page_size):
            temp = json.dumps(data[i:i + page_size]).encode("utf-8")
            r = self._post("api/library/history", data=temp, headers=headers)
            if callback is not None:
                callback(i, len(data))
            if r.getcode() != 200:
                raise Exception("%s %s" % (r.getcode(), r.msg))

    def history_delete(self):
        pass

    def library_update_songs(self, songs, callback=None):
        headers = {"Content-Type": "application/json"}

        r = self._put("api/library",
            data=json.dumps(songs).encode("utf-8"),
            headers=headers)

        if r.getcode() != 200:
            raise Exception("%s %s" % (r.getcode(), r.msg))

    def library_create_song(self, song, callback=None):

        headers = {"Content-Type": "application/json"}

        r = self._post("api/library",
            data=json.dumps(song).encode("utf-8"),
            headers=headers)

        if r.getcode() != 200:
            raise Exception("%s %s" % (r.getcode(), r.msg))

        result = json.loads(r.read().decode("utf-8"))
        return result['result']

    def library_get_song(self, song_id, callback=None):
        r = self._get("api/library/" + song_id)

        if r.getcode() != 200:
            raise Exception("%s %s" % (r.getcode(), r.msg))

        result = json.loads(r.read().decode("utf-8"))
        return result['result']

    def library_get(self, query="", page_size=100, callback=None):
        pass

    def download_song(self, fname, song_id, callback=None):
        urlpath = "api/library/%s/audio" % (song_id)
        return self._retrieve(fname, urlpath, callback=callback)

    # --------------------------

    def _get_songs(self, query="", page=0, page_size=100, callback=None):
        """
        returns page_size song records from the remote database

        query:
            a standard library query string
        page:
            the page index of the results from the query string
        page_size:
            the number of records to return with the request.
        callback : function(bytes,total)
            a callback function returning the progress of the request
        """
        r = self._get("api/library", params={
                      "query": query,
                      "page": page,
                      "limit": page_size})
        if r.getcode() != 200:
            raise Exception("%s %s" % (r.getcode(), r.msg))

        total_size = int(r.info()['Content-Length'].strip())
        bytes_read = 0
        bufsize    = 4 * 1024

        data = b""
        buf = r.read(bufsize)
        while buf:
            data += buf
            bytes_read += len(buf)
            if callback:
                callback(bytes_read, total_size)
            buf = r.read(bufsize)

        result = json.loads(data.decode("utf-8"))

        return result['result'], total_size

    # --------------------------

    def _post(self, urlpath, params=None, data=None, headers=None):
        params = params or dict()
        headers = headers or dict()
        headers['Authorization'] = self.token
        s = '&'.join(["%s=%s" % (k, v) for k, v in params.items()])
        url = "%s/%s?%s" % (self.hostname, urlpath, s)
        request = urllib.request.Request(url, data=data,
            method='POST', headers=headers)
        return urllib.request.urlopen(request, context=self.ctx)

    def _put(self, urlpath, params=None, data=None, headers=None):
        params = params or dict()
        headers = headers or dict()
        headers['Authorization'] = self.token
        s = '&'.join(["%s=%s" % (k, v) for k, v in params.items()])
        url = "%s/%s?%s" % (self.hostname, urlpath, s)
        request = urllib.request.Request(url, data=data,
            method='PUT', headers=headers)
        return urllib.request.urlopen(request, context=self.ctx)

    def _get(self, urlpath, params=None, headers=None):
        params = params or dict()
        headers = headers or dict()
        headers['Authorization'] = self.token
        s = '&'.join(["%s=%s" % (k, v) for k, v in params.items()])
        url = "%s/%s?%s" % (self.hostname, urlpath, s)
        request = urllib.request.Request(url, method='GET', headers=headers)
        return urllib.request.urlopen(request, context=self.ctx)

    def _delete(self, urlpath, params=None):
        params = params or dict()
        headers = headers or dict()
        headers['Authorization'] = self.token
        s = '&'.join(["%s=%s" % (k, v) for k, v in params.items()])
        url = "%s/%s?%s" % (self.hostname, urlpath, s)
        request = urllib.request.Request(url, method='DELETE', headers=headers)
        return urllib.request.urlopen(request, context=self.ctx)

    def _retrieve(self, path, urlpath, params=None, callback=None):
        params = params or dict()
        params['apikey'] = self.key
        with self._get(urlpath, params) as r:
            if r.getcode() != 200:
                raise Exception("%s %s" % (r.getcode(), r.msg))

            total_size = r.info()['Content-Length'].strip()
            total_size = int(total_size)
            bytes_read = 0
            bufsize    = 32 * 1024

            with open(path, "wb") as wf:
                buf = r.read(bufsize)
                while buf:
                    bytes_read += len(buf)
                    if callback:
                        callback(bytes_read, total_size)
                    wf.write(buf)
                    buf = r.read(bufsize)
            if callback:
                callback(bytes_read, total_size)

class ApiClientWrapper(object):
    """docstring for ApiClientWrapper

    used to translate song_ids between old and new databases
    """
    def __init__(self, api):
        super(ApiClientWrapper, self).__init__()
        self.api = api

    def local_path(self, basedir, song):
        path = Song.toShortPath(song)
        fname = os.path.join(basedir, *path)
        return fname

    def getUserName(self):
        return self.api.username

    def setApiKey(self, key):
        self.api.setApiKey(key)

    def setApiUser(self, username):
        self.api.setApiUser(username)

    def getHostName(self):
        return self.api.hostname

    def getUserName(self):
        return self.api.username

    def getApiKey(self):
        return self.api.key

    def login(self, username, password):

        user = self.api.login(username, password)

        self.api.setApiUser(username)
        self.api.setApiKey(user['apikey'])

        return user

    def connect(self, callback=None, mapReferences=True):

        songs = []
        page = 0
        page_size = 500
        total_size = 0
        while True:

            tmp, size = self.api._get_songs(page=page,
                page_size=page_size,
                callback=callback)

            if len(tmp) == 0:
                break

            songs += [remap_keys_r(s) for s in tmp]
            page += 1
            total_size += size

        if mapReferences:
            self.songs = {s['id']: s for s in songs}  # new format
            self.songs_r = {s['uid']: s for s in songs}   # old format
        else:
            self.songs = {}
            self.songs_r = {}

        return songs

    def download_song(self, basedir, song, callback=None):

        if 'id' in song:
            song_id = song['id']
        elif "uid" in song:
            song_id = self.songs_r[song['uid']]['id']
        else:
            print(song)
            raise Exception("invalid song")

        fname = self.local_path(basedir, song)
        dname, _ = os.path.split(fname)
        if not os.path.exists(dname):
            os.makedirs(dname)
        self.api.download_song(fname, song_id, callback=callback)
        return fname

    def library_update_songs(self, songs, callback=None):
        self.api.library_update_songs([remap_keys(s) for s in songs], callback)

    def library_create_song(self, song, callback=None):

        song = remap_keys(song)
        song_id = self.api.library_create_song(song, callback)

        song['id'] = song_id
        self.songs_r[song['ref_id']] = song
        self.songs[song['id']] = song

        return song_id

    def library_get_song(self, uid, callback=None):
        """ get a song given a uid """
        song_id = self.songs_r[uid]['id']
        song = self.api.library_get_song(song_id, callback)

        # update the local record for the song
        self.songs_r[song['ref_id']] = song
        self.songs[song['id']] = song

        return remap_keys_r(song)

    def history_get(self, start=0, end=None, page=0, page_size=500, callback=None):
        # determine start and end, deduplicate results retrieved from remote
        db_records = History.instance().export_date_range(start, end)
        records_set = set((r['date'] for r in db_records))

        results = self.api.history_get(start, end, page, page_size, callback=callback)
        results = results['result']

        # if song references are mapped, translate json to old-style format
        if len(self.songs) > 0:
            n = len(results)
            results = [{"date": r['timestamp'], "column": Song.playtime,
                "uid": self.songs[r['song_id']]['ref_id'], 'value': None}
                for r in results if (r['song_id'] in self.songs and
                    r['timestamp'])]
            if n != len(results):
                print("got %d results, filtered to %d." % (n, len(results)))

        return results

    def history_put(self, records, callback=None):
        """
        put records to the remote database
        only support Song.playtime type records
        """

        # if song references are mapped, translate json to old-style format
        if len(self.songs) > 0:
            n = len(records)
            records = [{"timestamp": r['date'],
                "song_id": self.songs_r[r['uid']]['id']}
                for r in records if (r['uid'] in self.songs_r and
                    r['column'] == Song.playtime)]
            if n != len(records):
                print("put %d results, filtered to %d." % (n, len(records)))

        self.api.history_put(records, callback=callback)

