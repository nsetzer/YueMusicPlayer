#! python34 ../../test/test_client.py $this

try:
    import PIL
except ImportError:
    sys.stderr.write("PIL unsupported")
    PIL = None

import os,sys
import codecs
import subprocess

from yue.core.song import Song
from yue.core.library import Library
from yue.core.playlist import PlaylistManager
from yue.core.sqlstore import SQLStore

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

def ChangeExt(path,ext):
    return os.path.splitext(path)[0] + ext

def ExtIs(path,ext):
    return os.path.splitext(path)[1].lower() == ext.lower()

def makedirs(path):
    if not os.path.exists( path ):
        os.makedirs( path )

def copy_file(src,dst):
    b = 1<<17;
    with open(src,"rb") as rf:
        with open(dst,"wb") as wf:
            buffer = rf.read(b);
            while buffer:
                wf.write(buffer)
                buffer = rf.read(b);

def walk(target, extensions):
    """ walk is a generator for media files in a directory
        It will return files in all sub directories as well.
    """
    for dirname,_,files in os.walk(target):
        for file in files:
            ext = os.path.splitext(file)[1]
            if ext in extensions:
                yield os.path.join(dirname,file)

class FFmpegEncoder(object):
    def __init__(self,ffmpeg_path,logger=None,no_exec=False):
        super(FFmpegEncoder,self).__init__();
        self.ffmpeg = ffmpeg_path
        self.logger = logger
        if self.logger == None:
            self.logger = sys.stderr
        self.no_exec = no_exec

    def args_add_metadata(self,args,keyname,keyvalue):
        args.append(u"-metadata")

        args.append( "%s=%s"%(keyname,keyvalue) )

    def args_add_input(self,args,path):
        args.append("-i")
        args.append(path)

    def args_add_output(self,args,b,sr,c,vol,path):
        if b > 0:
            args.append("-ab")
            args.append(str(b)+'k')
        if c > 0:
            args.append(u"-ac")
            args.append(str(c))
        if sr > 0:
            args.append("-ar")
            args.append(str(sr))

        if vol != 1 and vol > .2:
            vol = max(0.2,vol)
            vol = min(2.0,vol)
            args.append("-vol")
            args.append("%d"%( 256 * vol))

        args.append("-y") # force writing to output file
        args.append(path)

    # old function, for old style sync
    def transcode(self,input,output,bitrate=0,samplerate=0,channels=-1,vol=1.0,metadata={}):

        try:
            args = [self.ffmpeg,]
            self.args_add_input(args,input)

            self.args_add_metadata(args,"artist",metadata.get("artist","Unknown"))
            self.args_add_metadata(args,"title",metadata.get("title","Unknown"))
            self.args_add_metadata(args,"album",metadata.get("album","Unknown"))
            args.append("-id3v2_version")
            args.append("3")
            args.append("-write_id3v1")
            args.append("1")
            self.args_add_output(args,bitrate,samplerate,channels,vol,output)
        except Exception as e:
            print (str(e).encode('utf-8'))
            print (("error building args for %s"%input).encode('utf-8'))
            return;

        try:
            self.call(args)
        except Exception as e:
            print (str(e).encode('utf-8'))
            print (("error transcoding %s"%input).encode('utf-8'))

        return

    def call(self,args):
        argstr = u' '.join(args)
        if self.logger == sys.stderr:
            argstr = argstr.encode('utf-8')
        #self.logger.write( argstr )
        with open(os.devnull, 'w') as nul:
            #return subprocess.Popen(args,shell=True)
            self.logger.write("transcode: "+" ".join(args) + "\n")
            if not self.no_exec:
                subprocess.check_call(args,stdout=nul,stderr=nul)

class IterativeProcess(object):
    """docstring for IterativeProcess"""
    def __init__(self, parent):
        super(IterativeProcess, self).__init__()
        self.parent = parent

class DeleteProcess(IterativeProcess):
    """docstring for DeleteProcess"""

    def __init__(self, parent=None, filelist=None, no_exec=False):
        super(DeleteProcess,self).__init__( parent )
        self.filelist = filelist
        self.no_exec = no_exec

    def begin(self):
        self.parent.log("delete: %d"%len(self.filelist))
        self.errors = 0;
        total = len(self.filelist)
        self.execute = True
        # give the user a chance to cancel the operation
        if total > 0:
            self.execute = self.parent.getYesOrNo("Delete %d files?"%total)

        if not self.execute:
            return 0

        return total;

    def step(self,idx):

        try:
            filepath = self.filelist[idx]
            self.parent.remove_path(filepath)
        except:
            self.delete_errors += 1
        return True

    def end(self):
        return self.errors

class CopyProcess(IterativeProcess):
    """docstring for CopyProcess"""

    def __init__(self, parent=None, datalist=None, no_exec=False):
        super(CopyProcess,self).__init__( parent )
        # datalist = list(self.parent.data.items_copy())
        self.datalist = datalist
        self.no_exec = no_exec

    def begin(self):
        self.parent.log("copy: %d"%len(self.datalist))
        return len(self.datalist)

    def step(self,idx):
        key = self.datalist[idx]
        self.parent.log(key)

        self.parent.copy_path( key )


    def end(self):
        return

class TranscodeProcess(IterativeProcess):
    """docstring for TranscodeProcess"""

    def __init__(self, parent=None, datalist=None, no_exec=False):
        super(TranscodeProcess,self).__init__( parent )
        self.datalist = datalist
        self.no_exec = no_exec

    def begin(self):
        self.parent.log("transcode: %d"%len(self.datalist))
        return len(self.datalist)

    def step(self,idx):
        key = self.datalist[idx]
        self.parent.transcode_path( key )

    def end(self):
        return

class ParallelTranscodeProcess(IterativeProcess):
    """

    transcode is slower than file copy, and the target device is usally
    bottlenecked on IO. It should then be faster to run multiple transcodes
    in parallel on the local device then copy the resulting file

    use subprocess to launch N processes at once, writing to and from the
    same local drive.

    then copy the files in serial to the target directory.

    write to a temporary directory.
    """

    def __init__(self, parent=None, datalist=None, no_exec=False):
        super(TranscodeProcess,self).__init__( parent )
        self.datalist = datalist
        self.no_exec = no_exec
        self.N = 5

    def begin(self):
        return 1+len(self.datalist)//self.N

    def step(self,idx):
        pass

    def end(self):
        return

class WritePlaylistProcess(IterativeProcess):
    """docstring for WritePlaylistProcess

    datalist: as list-of-2-tuple, (name,query)"""

    def __init__(self,  library, datalist, format=0, parent=None, no_exec=False):
        super(WritePlaylistProcess,self).__init__( parent )
        self.library = library
        self.datalist = datalist
        self.no_exec = no_exec

    def begin(self):
        self.parent.log("write playlist: %d"%len(self.datalist))
        # open a thread local instance of the library
        return len(self.datalist)

    def step(self,idx):
        name,query = self.datalist[idx]
        name = name.replace(" ","_") + ".m3u"

        songs = self.library.search(query,orderby=[Song.artist,Song.album])

        sys.stdout.write("save playlist: %s:%s\n"%(name,len(songs)))
        path = os.path.join(self.parent.target,name)
        saveCowonPlaylist(path,songs)

    def end(self):
        return

class SyncManager(object):
    T_NONE=0        # don't transcode file
    T_NON_MP3=1     # transcode non-mp3 to mp3
    T_ALL=2         # transcode all files, to a target bitrate
    T_SPECIAL=3     # like ALL, but use default bitrate for existing mp3 files
                    # special forces the use of ffmpeg, and therefore
                    # should set tag information correctly.

    def __init__(self,library,song_ids,target,enc_path,
        transcode=0,
        player_directory=None,
        equalize=False,
        bitrate=0,
        dynamic_playlists=None,
        no_exec=False):
        super(SyncManager,self).__init__()
        """
        library: instance of Library()
        playlist: instance of PlaylistView()
        target: root directory to sync files to
        enc_path: path to ffmpeg (todo: or sox)
        transcode: one of {NONE,NON_MP3,ALL,SPECIAL}
        player_directory: ...
        equalize: use ffmpeg to adjust relative volume during transcode
        bitrate: mp3 bitrate (128, 192, 256, 320)
        no_exec: run process. but take no action, log output
        """

        self.library = library
        self.song_ids = song_ids
        self.target = target
        self.transcode = transcode
        self.no_exec = no_exec
        self.player_directory = player_directory
        self.queries = []
        self.equalize = equalize
        self.save_playlists = dynamic_playlists is not None
        self.dynamic_playlists = dynamic_playlists # as list-of-2-tuples: name,query

        self.target_library = None # list of songs

        self.encoder = FFmpegEncoder(enc_path,no_exec=no_exec)

        self.data =  SyncData(self.encoder)
        self.data.force_transcode = self.transcode in (SyncManager.T_ALL,SyncManager.T_SPECIAL)
        self.data.transcode_special = self.transcode == SyncManager.T_SPECIAL
        self.data.equalize = equalize
        self.data.bitrate = bitrate

    # main process

    def run(self):

        self.message("Scanning Directory")
        makedirs(self.target)
        self.data_init()
        delete_list = self.walk_target()
        copylist = list(self.data.items_copy())
        transcodelist =  list(self.data.items_transcode())

        d = len(delete_list)
        c = len(copylist)
        t = len(transcodelist)
        p = 0 if self.dynamic_playlists is None else len(self.dynamic_playlists)

        self.setOperationsCount(d+c+t+p)

        self.message("Delete Files")
        proc = DeleteProcess(parent=self,filelist=delete_list,no_exec=self.no_exec)
        self.run_proc( proc )

        self.message("Copy Files")
        proc = CopyProcess(parent=self,datalist=copylist,no_exec=self.no_exec)
        self.run_proc( proc )

        self.message("Transcode Files")
        proc = TranscodeProcess(parent=self,datalist=transcodelist,no_exec=self.no_exec)
        self.run_proc( proc )

        if self.save_playlists:
            self.message("Save Dynamic Playlists")

            target_library = self.createTargetLibrary()
            format=0
            proc = WritePlaylistProcess(target_library,self.dynamic_playlists, \
                        format,self,no_exec=self.no_exec)
            self.run_proc( proc )

        self.message("Finished %d/%d/%d"%(d,c,t))

    def run_proc(self,proc):
        n = proc.begin()
        for i in range(n):
            proc.step(i)
        proc.end()

    # functions to reimplement in UI

    def setOperationsCount(self,count):
        """ reimplement this """
        pass

    def message(self,msg):
        """ reimplement this """
        self.log(msg)

    def getYesOrNo(self,msg):
        """ reimplement this """
        if self.no_exec:
            return True
        sys.stdout.write("%s: "%msg)
        x = input().lower()
        while not (x.startswith("y") or x.startswith("n")):
            sys.stdout.write("%s: "%msg)
            x = input().lower()
        return x.startswith("y")

    def log(self,msg):
        """ reimplement this """
        try:
            sys.stdout.write(msg+"\n")
        except UnicodeEncodeError:
            sys.stdout.write("<>\n")

    # core file operations
    # these could be reimplemented, for example, for an MTP device
    # instead of a normal file system

    def walk_target(self):
        # walk the target directory looking for media files
        # determine exactly which songs need to be copied
        # and any songs that should be deleted.
        # return a list of files to delete.

        lst_delete = []
        for path in walk(self.target,Song.supportedExtensions()):
            if not self.data.exists(path):
                # need to remove this file as it is not on the list
                lst_delete.append(path)
            else:
                # dont need to copy file that exists
                # if the if statement is enabled
                # then songs that should be transcoded
                # will be deleted
                #if not self.data.transcode(path):
                self.data.delete(path)
        return lst_delete

    def remove_path(self,filepath):
        self.log("delete: %s\n"%filepath)
        if not self.no_exec:
            os.remove(filepath)

    def copy_path(self, tgtpath):
        song, transcode = self.data.getValue( tgtpath )
        self.log("copy: %s -> %s\n"%(song[Song.path],tgtpath))
        if not self.no_exec:
            makedirs(os.path.split(tgtpath)[0])

            # TODO, COPY, TRANSCODE new FORCE OVERWRITE option
            if not self.no_exec and os.path.exists(tgtpath):
                return
            copy_file(song[Song.path],tgtpath)

    def transcode_path(self, tgtpath):
        song, transcode = self.data.getValue( tgtpath )
        self.log("transcode: %s -> %s\n"%(song[Song.path],tgtpath))
        if not self.no_exec:
            makedirs(os.path.split(tgtpath)[0])
        self.transcode_song(song,tgtpath)

    def transcode_song(self,song,tgtpath):
        metadata=dict(
            artist=song[Song.artist],
            album=song[Song.album],
            title=song[Song.title])
        vol=1.0
        if self.data.equalize:
            vol = song[Song.equalizer] / Song.eqfactor
        srcpath = song[Song.path]
        bitrate = self.data.bitrate
        if srcpath.lower().endswith('mp3') and self.transcode_special:
            bitrate=0

        # TODO, COPY, TRANSCODE new FORCE OVERWRITE option
        if not self.no_exec and os.path.exists(tgtpath):
            return
        self.encoder.transcode(srcpath,tgtpath,bitrate,vol=vol,metadata=metadata)

    # sync functions

    def data_init(self):

        songs = self.library.songFromIds( self.song_ids )
        for i,song in enumerate(songs):
            path = os.path.join(self.target,Song.toShortPath(song))
            if self.transcode == SyncManager.T_NON_MP3 and not ExtIs(path,".mp3"):
                path = ChangeExt(path,".mp3")
                self.data.add(path,song,True)
            else:
                self.data.add(path,song,False)

    def getTargetLibraryPath(self):
        # todo windows only
        #drive = os.path.splitdrive(self.target)[0] + os.sep
        #player_path = self.player_directory or \
        #              os.path.join(drive,"Player","user","");
        libpath = os.path.join(self.target,"library.db")
        #if os.path.exists(player_path):
        #    libpath = os.path.join(player_path,"music.xml")
        return libpath

    def createTargetLibrary(self):
        if self.target_library is not None:
            return self.target_library;

        sys.stdout.write("Generating target playlist & library\n")
        new_playlist= self.data.getTargetPlaylist()

        db_path = self.getTargetLibraryPath()
        if os.path.exists(db_path):
            os.remove(db_path)
        sqlstore = SQLStore(db_path)
        library = Library( sqlstore )

        with library.sqlstore.conn:
            c = library.sqlstore.conn.cursor()
            for song in new_playlist:
                if "artist_key" in song:
                    del song['artist_key']
                library._insert(c, **song)

        self.target_library = library

        sys.stdout.write("finished creating target library\n")

        return library

    #def save_cover_images(self):
    #    if self.target_library is None:
    #        self.compute_target_library();
    #        #self.target_library.save()
    #    srcai = AudioServer.AlbumIndex(self.library)
    #    dstai = AudioServer.AlbumIndex(self.target_library)
    #    for key in dstai.keys():
    #        path = srcai.cover_image_path( key )
    #        if path:
    #            for p in dstai.cover_image_out_path(key,path,ext='.jpg'):
    #                p,_ = os.path.split(p)
    #                p = os.path.join(p,'cover.jpg')
    #                if not os.path.exists(p):
    #                    copy_image(path,p)
    #                else:
    #                    print("skipping...")

    #def save_zen_query_list(self,library,m3ufile,query,zen = True):
    #    subset = library.search(query);
    #    print(m3ufile,":",len(subset))
    #    if zen:
    #        save_ZEN_playlist(m3ufile,subset);
    #    else:
    #        pl = AudioServer.Playlist(library,subset)
    #        pl.save(m3ufile)

class SyncData(object):
    """
        maintains a case-insensitive list of songs to
        sync, and whether they need to be transcoded before
        being copied
    """
    def __init__(self,encoder):
        self.encoder = encoder
        self.data = {}
        self.force_transcode = False
        self.transcode_special = False
        self.bitrate = 320

        self.data_copy = None
        self.playlist_dst = None
        self.playlist_src = None

    def add(self,path,song,transcode=False):
        if self.force_transcode:
            path = ChangeExt(path,".mp3")
        self.data[path] = (song,transcode)

    def exists(self,path):
        if path in self.data:
            return True;
        for key in self.data.keys():
            if key.lower() == path.lower():
                return True;
        return False;

    def delete(self,path):
        if self.data_copy == None:
            self.data_copy = dict(self.data)
        if path in self.data:
            del self.data[path]
            return
        rmkeys = []
        for key in self.data.keys():
            if key.lower() == path.lower():
                rmkeys.append(key)
        for key in rmkeys:
            del self.data[key]
        return

    def items_copy(self):
        """ yield all items that must be copied"""
        if self.force_transcode:
            pass
        else:
            for key in self.data.keys():
                 if self.data[key][1]==False:
                    yield key

    def items_transcode(self):
        """ yield all items that must be transcoded"""
        if self.force_transcode:
            for x in self.data.keys():
                yield x
        else:
            for key in self.data.keys():
                if self.data[key][1]==True:
                    yield key

    def getValue(self, tgtpath ):

        if tgtpath not in self.data:
            for key in self.data.keys():
                if key.lower() == tgtpath.lower():
                    return self.data[key]
        else:
            return self.data[tgtpath]

        raise KeyError( key )

    def getTargetPlaylist(self):
        """ list of songs, where Song.path references the sync path """
        if self.data_copy == None:
            self.data_copy = dict(self.data)
        if self.playlist_dst is None:
            self.playlist_dst = []
            for path,(song,_) in self.data_copy.items():
                new_song = song.copy()
                new_song[Song.path] = path
                self.playlist_dst.append(new_song)
        return self.playlist_dst

    def getSourcePlaylist(self):
        """ list of songs, where Song.path references the local path """
        if self.data_copy == None:
            self.data_copy = dict(self.data)
        if self.playlist_src is None:
            self.playlist_src = [ song for song,_ in self.data_copy.values() ]
        return self.playlist_src

if sys.platform == 'win32':
    # 2015-05-23 python33->python34 problems with win32api
    # I found this short path alternative on stack overflow
    import ctypes
    from ctypes import wintypes
    _GetShortPathNameW = ctypes.windll.kernel32.GetShortPathNameW
    _GetShortPathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
    _GetShortPathNameW.restype = wintypes.DWORD

    def get_short_path_name(long_name):
        """
        Gets the short path name of a given long path.
        http://stackoverflow.com/a/23598461/200291
        """
        output_buf_size = 0
        while True:
            output_buf = ctypes.create_unicode_buffer(output_buf_size)
            needed = _GetShortPathNameW(long_name, output_buf, output_buf_size)
            if output_buf_size >= needed:
                return output_buf.value
            else:
                output_buf_size = needed

def getShortName_COWON(path):
    if os.path.exists(path):
        out = path
        if sys.platform == 'win32':
            out=get_short_path_name(path)
            #out = win32api.GetShortPathName(path)
        out = out.replace("/","\\")
        return out[2:]; # remove drive letter
    raise OSError('file not found: %s'%path)

def getShortName_ZEN(path):
    # fore ZEN M3U
    if os.path.exists(path):
        out=get_short_path_name(path)
        #out = win32api.GetShortPathName(path)
        out = out.upper();
        out = out.replace("\\","/")
        return out[2:]; # remove drive letter
    return "";

def saveCowonPlaylist(filename,songs):
    with codecs.open(filename,"w","utf-8") as wf :
        #http://anythingbutipod.com/forum/showthread.php?t=67351
        wf.write("#EXTM3U\r\n")
        print(len(songs))
        print(songs)
        for song in songs:
            try:
                path = getShortName_COWON(song[Song.path]);
            except OSError as e:
                sys.stdout.write("error saving song to playlist - %s"%e)

            else:
                if path :
                    dur=song[Song.length]
                    a=song[Song.artist]
                    t=song[Song.title]
                    wf.write("#EXTINF:%d,%s - %s\r\n"%(dur,a,t));
                    wf.write(path+"\r\n");
                else:
                    print("error "+path)


#def save_ZEN_playlist(filename,library):
#    """
#        saves songs as a list to the specified list
#        the format is the 8.3 shortname of the song
#        with the drive letter and colon removed.
#    """
#    sel=lambda x:sort_parameter_str(x,AudioServer.Song.ALBUM)
#    data = sorted(library,key=sel)
#    data.sort(key=lambda x:sort_parameter_str(x,AudioServer.Song.ARTIST))
#    with codecs.open(filename,"w","utf-8") as wf :
#        #http://anythingbutipod.com/forum/showthread.php?t=67351
#        wf.write("#EXTM3U\r\n")
#        for song in data:
#            path = getShortName_COWON(song[AudioServer.Song.PATH]);
#            if path :
#                dur=song[AudioServer.Song.LENGTH]
#                txt=song[AudioServer.Song.TITLE]
#                wf.write("#EXTINF:%d,Title\r\n"%(dur));
#                wf.write(path+"\r\n");

def copy_image(src,dst,size=500):
    """ copy img src to dst, changing fileformat as needed"""
    if PIL is None:
        raise RuntimeError("PIL not supported")
    try:
        # convert to solve occasional P mode problems
        img = PIL.Image.open(src).convert('RGB')
        w1,h1 = img.size
        if w1 > size:
            w=size
            h = int((h1/float(w1))*w)
        else:
            w,h = w1,h1
        img.resize((w,h),PIL.Image.ANTIALIAS).save(dst)
    except Exception as e:
        print(str(e).encode('utf-8'))

def sort_parameter_str(song,index):
    """
        when searching by string parameters
        check to see if the string starts with certain words,
        and remove them
    """
    s = song[index].upper()
    if s.lower().startswith("the "):
        return s[4:]
    return s

def main():

    ffmpeg=r"C:\ffmpeg\bin\ffmpeg.exe"
    db_path = "yue.db"

    target = "test"
    transcode = SyncManager.T_NON_MP3
    equalize = False
    bitrate = 320
    run = True
    no_exec = False

    sqlstore = SQLStore(db_path)
    Library.init( sqlstore )
    PlaylistManager.init( sqlstore )

    library = Library.instance()
    playlist = PlaylistManager.instance().openPlaylist("current")
    uids = list(playlist.iter())

    print(os.path.realpath(db_path))
    print("lib",len(library))

    dp = [("blind melon","blind melon"),]

    sm = SyncManager(library,uids,target,ffmpeg,
            transcode=transcode,
            equalize=equalize,
            dynamic_playlists = dp,
            no_exec=no_exec)
    sm.run()

if __name__ == '__main__':
    main()