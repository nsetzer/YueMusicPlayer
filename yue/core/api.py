
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

        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE

        self.key = None
        self.username = None

    def setApiKey(self,key):
        self.key = key

    def setApiUser(self,username):
        self.username = username

    def history_get(self,callback=None):
        """
        get all history records stored remotely
        """
        records = []
        num_pages = 0
        with self._get("api/history",{"page":0}) as r:
            data = json.loads(r.read().decode("utf-8"))
            records += data['records']
            num_pages = data['num_pages']

        for i in range(1,num_pages):
            if callback is not None:
                callback(i,num_pages)
            with self._get("api/history",{"page":i}) as r:
                data = json.loads(r.read().decode("utf-8"))
                records += data['records']

        return records

    def history_put(self,data,callback=None):
        """
        push a list of records to the remote server
        """
        # push the data in chunks
        headers = {
            "Content-Type" : "text/x-yue-history"
        }
        step_size = 50
        for i in range(0,len(data),step_size):
            temp = json.dumps(data[i:i+step_size]).encode("utf-8")
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

    def download_song(self,basedir,song,callback=None):
        path = Song.toShortPath(song)
        fname = os.path.join(basedir,*path)
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



