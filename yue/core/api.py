
import os
import ssl
import urllib
import urllib.request
import json
from yue.core.song import Song

class ApiClient(object):
    """docstring for ApiClient"""
    def __init__(self, hostname):
        super(ApiClient, self).__init__()

        self.hostname = hostname
        self.key = ""
        self.username = ""

        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE

    @staticmethod
    def generate_hmac(key,params={},payload=None):
        h = hmac.new(key.encode('utf-8'), digestmod=hashlib.sha256)
        for key,value in sorted(params.items()):
            h.update(str(value).encode("utf-8"))
            h = hmac.new(h.digest(), digestmod=hashlib.sha256)
        if isinstance(payload,bytes):
            h.update(payload)
        elif payload:
            h.update(str(payload).encode("utf-8"))
        d=h.digest()
        return base64.b64encode(d).decode()

    @staticmethod
    def compare_hmac(digest,key,params={},payload=None):
        temp = ApiClient.generate_hmac(key,params,payload)
        return hmac.compare_digest(digest,temp)


    def setApiKey(self,key):
        self.key = key

    def setApiUser(self,username):
        self.username = username

    def getHostName(self):
        return self.hostname

    def getUserName(self):
        return self.username

    def getApiKey(self):
        return self.key

    def history_get(self,page=0,page_size=25):
        """
        get all history records stored remotely
        """
        r = self._get("api/history",{"page":page,"page_size":page_size})
        result = json.loads(r.read().decode("utf-8"))
        return result

    def history_put(self,data,page_size=250,callback=None):
        """
        push a list of records to the remote server
        """
        # push the data in chunks
        headers = {
            "Content-Type" : "text/x-yue-history"
        }
        for i in range(0,len(data),page_size):
            temp = json.dumps(data[i:i+page_size]).encode("utf-8")
            r = self._put("api/history",data=temp,headers=headers);
            if callback is not None:
                callback(i,len(data))
            if r.getcode() != 200:
                raise Exception("%s %s"%(r.getcode(),r.msg))

    def history_delete(self):
        """
        delete all records stored remotely
        """
        self._delete("api/history")

    def local_path(self,basedir,song):
        path = Song.toShortPath(song)
        fname = os.path.join(basedir,*path)
        return fname

    def download_song(self,basedir,song,callback=None):

        fname = self.local_path(basedir,song)
        dname, _ = os.path.split(fname)
        if not os.path.exists(dname):
            os.makedirs(dname)
        urlpath = "api/library/%s"%song[Song.uid]
        self._retrieve(fname,urlpath,callback=callback)
        return fname

    def get_songs(self,query="",page=0,page_size=25):
        r=self._get("api/library",params={
                    "query":query,
                    "page":page,
                    "page_size":page_size})
        if r.getcode()!=200:
            raise Exception("%s %s"%(r.getcode(),r.msg))
        result = json.loads(r.read().decode("utf-8"))
        return result

    def get_all_songs(self,callback = None):

        songs = []
        result = self._get_songs(0)
        num_pages = result['num_pages']
        songs += result['songs']
        for i in range(1,num_pages):
            if callback is not None:
                callback(i,num_pages)
            result = self._get_songs(i)
            songs += result['songs']

    # --------------------------

    def _put(self,urlpath,params=None,data=None,headers={}):
        # TODO: timeouts

        params = params or dict()
        params['username'] = self.username
        params['key'] = self.key
        s = '&'.join(["%s=%s"%(k,v) for k,v in params.items()])
        url = "%s/%s?%s"%(self.hostname,urlpath,s)
        request = urllib.request.Request(url,data=data,headers=headers,method='PUT')
        return urllib.request.urlopen(request,context=self.ctx)

    def _get(self,urlpath,params=None):
        params = params or dict()
        params['username'] = self.username
        params['key'] = self.key
        s = '&'.join(["%s=%s"%(k,v) for k,v in params.items()])
        url = "%s/%s?%s"%(self.hostname,urlpath,s)
        request = urllib.request.Request(url,method='GET')
        return urllib.request.urlopen(request,context=self.ctx)

    def _delete(self,urlpath,params=None):
        params = params or dict()
        params['username'] = self.username
        params['key'] = self.key
        s = '&'.join(["%s=%s"%(k,v) for k,v in params.items()])
        url = "%s/%s?%s"%(self.hostname,urlpath,s)
        request = urllib.request.Request(url,method='DELETE')
        return urllib.request.urlopen(request,context=self.ctx)

    def _retrieve(self,path,urlpath,params=None,callback=None):
        with self._get(urlpath,params) as r:
            if r.getcode() != 200:
                raise Exception("%s %s"%(r.getcode(),r.msg))

            total_size = r.info()['Content-Length'].strip()
            total_size = int(total_size)
            bytes_read = 0
            bufsize    = 32*1024

            with open(path,"wb") as wf:
                buf = r.read(bufsize)
                while buf:
                    bytes_read += len(buf)
                    if callback:
                        callback(bytes_read,total_size)
                    wf.write(buf)
                    buf = r.read(bufsize)
            if callback:
                callback(bytes_read,total_size)



