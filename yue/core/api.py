
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

    def history_get(self,page=0):

        with self._get("api/history",{page:0}) as r:
            data = json.loads(r.read().decode("utf-8"))

            records = data['records']
            print(len(records))
            print(data['page'])
            print(data['num_pages'])

    def history_put(self,data,callback=None):
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

        self._delete("api/history")

    def download_song(self,basedir,song):
        path = Song.toShortPath(song)
        print(str(path).encode("utf-8"))
        fname = os.path.join(basedir,*path)
        dname, _ = os.path.split(fname)
        if not os.path.exists(dname):
            os.makedirs(dname)
        urlpath = "api/library/%s"%song[Song.uid]
        print(fname.encode("utf-8"))

        self._retrieve(fname,urlpath)

    def get_library(self,page=0):
        r=self._get("api/library",params={page:"%d"%page})
        if r.getcode()!=200:
            raise Exception("%s %s"%(r.getcode(),r.msg))

        result = json.loads(r.read().decode("utf-8"))
        #songs_ = result['songs']
        #songs = []
        #for _,v in sorted(songs_.items(),key=lambda x:int(x[0])):
        #    songs.append(v)
        #result['songs'] = songs
        return result

    def _put(self,urlpath,params=None,data=None,headers={}):
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

    def _retrieve(self,path,urlpath,params=None):
        with self._get(urlpath) as r:
            if r.getcode() != 200:
                raise Exception("%s %s"%(r.getcode(),r.msg))
            with open(path,"wb") as wf:
                wf.write(r.read())


