#! python34 ../../test/test_client.py $this

"""
TODO:
    delete process should clean up empty directories

    make deleting empty directories an option
        what happens if the only file in a directory is a cover img?

    these errors are related to calling ftplib functions from another thread
        ftplib.error_reply: 200 TYPE is now ASCII
        ftplib.error_reply: 226 15 matches total

    TODO: sync overwrites the remote DB
        import history clones the remote db locally
        settings from the cloned db should be copied to the remote db
        provide a way to clone a table between two databases
        preferibly under sqlstore.py as a util funciton, provide
        two sqlstyore instances and the name of the table
            drop from b if exists
            select * from a
            insert item into b
"""
import os,sys
try:
    # TODO: i don't need PIL with PyQT
    import PIL
except ImportError:
    sys.stderr.write("PIL unsupported\n")
    PIL = None


import codecs
import subprocess
import tempfile, shutil

from yue.core.song import Song
from yue.core.library import Library
from yue.core.history import History
from yue.core.playlist import PlaylistManager
from yue.core.sqlstore import SQLStore
from yue.core.settings import Settings

from yue.core.explorer.source import DirectorySource
from yue.core.explorer.fsutil import source_copy_file
from yue.core.explorer.ftpsource import FTPSource, parseFTPurl

# TODO: move to source
def ChangeExt(path,ext):
    return os.path.splitext(path)[0] + ext
def ExtIs(path,ext):
    return os.path.splitext(path)[1].lower() == ext.lower()

def run_async(func):
    """
        run_async(func)
            function decorator, intended to make "func" run in a separate
            thread (asynchronously).
            Returns the created Thread object

            E.g.:
            @run_async
            def task1():
                do_something

            @run_async
            def task2():
                do_something_too

            t1 = task1()
            t2 = task2()
            ...
            t1.join()
            t2.join()
    """
    from threading import Thread
    from functools import wraps

    @wraps(func)
    def async_func(*args, **kwargs):
        func_hl = Thread(target = func, args = args, kwargs = kwargs)
        func_hl.start()
        return func_hl

    return async_func

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
        self.logger.write("transcode-f: "+" ".join(args) + "\n")
        # when run under windows (under gui)
        # std in/out/err must be given a PIPE/nul
        # otherwise: '[WinError 6] The handle is invalid'
        # shell must be true to prevent a cmd window from opening
        if not self.no_exec:
            with open(os.devnull, 'r') as nulr:
                with open(os.devnull, 'w') as nulw:
                    subprocess.check_call(args,stdin=nulr,shell=False)

class IterativeProcess(object):
    """docstring for IterativeProcess"""
    def __init__(self, parent):
        super(IterativeProcess, self).__init__()
        self.parent = parent

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        return # return true to supress exception

class DeleteProcess(IterativeProcess):
    """docstring for DeleteProcess"""

    def __init__(self, parent=None, filelist=None, no_exec=False):
        super(DeleteProcess,self).__init__( parent )
        self.filelist = filelist
        self.no_exec = no_exec
        self.delete_errors = 0

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
        except Exception as e:
            sys.stderr.write("del error: %s"%e)
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

class ImportHistoryProcess(IterativeProcess):
    """import history from a library"""

    def __init__(self, parent=None, no_exec=False):
        super(ImportHistoryProcess,self).__init__( parent )
        self.no_exec = no_exec

    def begin(self):
        return 1

    def step(self,idx):

        dbpath = os.path.join(os.getcwd(),"remote.db")
        if not isinstance(self.parent.target_source,DirectorySource):
            # target is not a local directory
            tgtdb = self.parent.getTargetLibraryPath()
            self.parent.log("remote db path: %s"%tgtdb)
            if self.parent.target_source.exists(tgtdb):
                with self.parent.target_source.open(tgtdb,"rb") as rb:
                    with self.parent.local_source.open(dbpath,"wb") as wb:
                        wb.write(rb.read())
        else:
            dbpath = self.parent.getTargetLibraryPath()

        self.remote_path = dbpath

        self.parent.log("db local path: %s %s"%(dbpath,os.path.exists(dbpath)))

        if not self.parent.local_source.exists(dbpath):
            self.parent.log("import history: no database")
            return

        remote_store = SQLStore( dbpath )
        remote_history = History( remote_store )
        local_history = History( self.parent.library.sqlstore )

        size = remote_history.size()
        self.parent.log("import history: num records %d"%size)

        if self.no_exec or size==0:
            self.parent.log("import history: nothing to do")
            return

        self.execute = self.parent.getYesOrNo("Import %d records?"%size,btn2="import")

        if not self.execute:
            return

        conn = self.parent.library.sqlstore.conn
        with conn:
            c = conn.cursor()
            for record in remote_history.export():
                self.parent.library._import_record( c, record )


    def end(self):
        return

@run_async
def async_transcode(obj,src,dst):
    if obj.local_source.exists(dst):
        obj.local_source.delete(dst)
    obj.transcode_local(src,dst)

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

    def __init__(self, parent=None, datalist=None,NPARALLEL=5, no_exec=False):
        super(ParallelTranscodeProcess,self).__init__( parent )
        self.datalist = datalist
        self.no_exec = no_exec
        self.N = NPARALLEL # num actions to take in parallel

        self.tempdir = ""
        self.nsteps=0

    @staticmethod
    def num_steps(n,NPARALLEL):
        return (n+NPARALLEL-1) // NPARALLEL

    def __enter__(self):
        if not self.no_exec:
            self.tempdir = tempfile.mkdtemp(prefix="yuesync_")
        sys.stdout.write("create temp directory: %s\n"%self.tempdir)
        return self

    def __exit__(self, type, value, traceback):
        if not self.no_exec:
            shutil.rmtree(self.tempdir)
        return # return true to supress exception

    def begin(self):
        self.nsteps = ParallelTranscodeProcess.num_steps(len(self.datalist),self.N)
        sys.stdout.write("transcode requires %d steps for %d files.\n"%(self.nsteps,len(self.datalist)))
        return self.nsteps

    def step(self,idx):
        s=idx*self.N
        tasks = []

        self.parent.message("Transcode: (%d/%d)"%(idx+1,self.nsteps))

        # launch N threads to perform transcode in parallel
        for k in range(self.N):
            i = idx*self.N + k
            if i >= len(self.datalist):
                break;
            tgtpath = self.datalist[i]
            trpath = os.path.join(self.tempdir,"yuesync-%d.mp3"%k)
            # current encoder does not support parallel execution
            t = async_transcode(self.parent, tgtpath, trpath)
            tasks.append( (t,trpath,tgtpath) )

        # join the threads and copy in serial, target may be bandwidth
        # limited, so throughput may only allow one file at a time.
        # as it is, transcode is the slowest part (compared to copy)
        for t,trpath,tgtpath in tasks:

            self.parent.log("join %s -> %s"%(trpath,tgtpath))

            try:
                if not self.no_exec:
                    t.join()

                    # keep going but log an error when the transcode fails
                    # to produce a file
                    if not self.parent.local_source.exists( trpath ):
                        self.parent.log("transcode failed: %s -> %s"%(trpath,tgtpath))
                        continue

                    p = self.parent.target_source.parent(tgtpath)
                    self.parent.target_source.mkdir( p )

                    source_copy_file(self.parent.local_source, trpath,
                                     self.parent.target_source, tgtpath, 1<<15)
            except Exception as e:
                self.parent.log("join error: %s %s"%(trpath,str(e)))


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
        self.format = format

    def begin(self):
        self.parent.log("write playlist: %d"%len(self.datalist))
        # open a thread local instance of the library
        return len(self.datalist)

    def step(self,idx):
        name,query = self.datalist[idx]
        alt_name = name.replace(" ","_") + ".m3u"

        if self.format == SyncManager.P_YUE:
            self.save_yue(name, query)
        elif self.format == SyncManager.P_M3U:
            self.save_m3u(alt_name, query)
        else:
            self.save_cowon(alt_name, query)

    def save_yue(self, name, query):
        songs = self.library.search(query,orderby=[Song.artist,Song.album])
        uids = [song[Song.uid] for song in songs]
        pm = PlaylistManager(self.library.sqlstore)
        pl=pm.openPlaylist(name)
        pl.set(uids)

    def save_m3u(self, name, query):
        songs = self.library.search(query,orderby=[Song.artist,Song.album])
        sys.stdout.write("save playlist (m3u): (exec:%s) %s:%s\n"%(not self.no_exec,name,len(songs)))
        if not self.no_exec:
            try:
                path = self.parent.target_source.join(self.parent.target_path,name)
                print("%s"%path)
                with self.parent.target_source.open(path,"wb") as wb:
                    w = codecs.getwriter("utf-8")(wb)
                    saveM3uPlaylist(w,songs)
            except Exception as e:
                print(type(e))
                print("%s"%e)

    def save_cowon(self, name, query):
        # COWON has a bug related to file size of the playlist
        # but i have never had a problem with 400 songs,
        # usually around 450 is when problems start to happen, sometimes
        # I can get as high as 500. 400 is just playling it safe.
        songs = self.library.search(query,orderby=Song.random,limit=400)
        sys.stdout.write("save playlist (cowon): (exec:%s) %s:%s\n"%(not self.no_exec,name,len(songs)))
        if not self.no_exec:
            try:
                path = self.parent.target_source.join(self.parent.target_path,name)
                print("%s"%path)
                with self.parent.target_source.open(path,"wb") as wb:
                    w = codecs.getwriter("utf-8")(wb)
                    saveCowonPlaylist(w,songs)
            except Exception as e:
                print(type(e))
                print("%s"%e)

    def end(self):
        return

class SyncManager(object):
    T_NONE=0        # don't transcode file
    T_NON_MP3=1     # transcode non-mp3 to mp3
    T_ALL=2         # transcode all files, to a target bitrate
    T_SPECIAL=3     # like ALL, but use default bitrate for existing mp3 files
                    # special forces the use of ffmpeg, and therefore
                    # should set tag information correctly.

    P_YUE   = 1 # internal format
    P_M3U   = 1 # standard m3u format
    P_COWON = 2 # m3u specific to COWON devices

    def __init__(self,library,song_ids,target,enc_path,
        transcode=0,
        player_directory=None,
        equalize=False,
        bitrate=0,
        dynamic_playlists=None,
        target_prefix="",
        playlist_format=1,
        no_exec=False):
        super(SyncManager,self).__init__()
        """
        library: instance of Library()
        playlist: instance of PlaylistView()
        target: root directory to sync files to
        target_prefix_path: prefix path for target device:
                            if target is a relative path, this is
                            prefixed to the target path in the library
        enc_path: path to ffmpeg (todo: or sox)
        transcode: one of {NONE,NON_MP3,ALL,SPECIAL}
        player_directory: ...
        equalize: use ffmpeg to adjust relative volume during transcode
        bitrate: mp3 bitrate (128, 192, 256, 320)
        no_exec: run process. but take no action, log output
        """

        self.library = library
        self.song_ids = song_ids
        self.target_input = target
        self.target_prefix_path = target_prefix # "/storage/emulated/0"
        self.transcode = transcode
        self.no_exec = no_exec
        self.player_directory = player_directory
        self.queries = []
        self.equalize = equalize
        self.bitrate = bitrate
        self.save_playlists = dynamic_playlists is not None
        self.dynamic_playlists = dynamic_playlists # as list-of-2-tuples: name,query
        self.playlist_format = playlist_format
        self.encoder_path = enc_path

        self.target_library = None # list of songs

    def openTargetSource(self,target):

        self.local_source = DirectorySource()

        if target.startswith("ftp"):
            data = parseFTPurl(target)
            print(data)
            self.target_path = data["path"]
            self.target_source = FTPSource(data["hostname"],
                                           data["port"],
                                           data["username"],
                                           data["password"])

        else:
            self.target_source = self.local_source
            self.target_path = target

    def closeSource(self):

        self.target_source.close()
        if self.local_source is not self.target_source:
            self.local_source.close()
    # main process

    def run(self):

        self.encoder = FFmpegEncoder(self.encoder_path,no_exec=self.no_exec)

        try:

            self.openTargetSource( self.target_input )

        except ConnectionRefusedError as e:
            self.message("%s"%e)
            return

        try:
            self.run_main()
        except Exception as e:
            sys.stderr.write("%s\n"%e)
            self.closeSource()
            raise e

        self.closeSource()

    def run_main(self):

        self.data =  SyncData(self.encoder)
        self.data.force_transcode = self.transcode in (SyncManager.T_ALL,SyncManager.T_SPECIAL)
        self.data.transcode_special = self.transcode == SyncManager.T_SPECIAL
        self.data.equalize = self.equalize
        self.data.bitrate = self.bitrate

        self.message("Scanning Directory")
        self.target_source.mkdir(self.target_path)

        # import history, so local library will be up-to-date
        proc = ImportHistoryProcess(parent=self,no_exec=self.no_exec)
        self.run_proc( proc )
        remote_path = proc.remote_path # TODO

        # build target lists
        self.data_init()
        delete_list = self.walk_target()
        copylist = list(self.data.items_copy())
        transcodelist =  list(self.data.items_transcode())

        NPARALLEL=5

        d = len(delete_list)
        c = len(copylist)
        t = nsteps = ParallelTranscodeProcess.num_steps(len(transcodelist),NPARALLEL)
        p = 0 if self.dynamic_playlists is None else len(self.dynamic_playlists)

        count=d+c+t+p
        if not count:
            count+=1
        self.setOperationsCount(count)

        self.message("Delete Files")
        if d>0:
            proc = DeleteProcess(parent=self,filelist=delete_list,no_exec=self.no_exec)
            self.run_proc( proc )

        self.message("Copy Files")
        if c>0:
            proc = CopyProcess(parent=self,datalist=copylist,no_exec=self.no_exec)
            self.run_proc( proc )

        self.message("Transcode Files")
        if t>0:
            proc = ParallelTranscodeProcess(parent=self,datalist=transcodelist,
                        NPARALLEL=NPARALLEL,no_exec=self.no_exec)
            self.run_proc( proc )

        target_library = self.createTargetLibrary()

        if self.save_playlists:
            self.message("Save Dynamic Playlists")


            fmt=self.playlist_format
            proc = WritePlaylistProcess(target_library,self.dynamic_playlists, \
                        fmt,self,no_exec=self.no_exec)
            self.run_proc( proc )

        self.copy_remote_settings( remote_path, target_library )

        # close the target library, then copy to remote device
        target_library.sqlstore.close()
        libpath=self.getTargetLibraryPath()
        if not self.no_exec:
            source_copy_file(self.local_source,target_library.sqlstore.filepath,
                         self.target_source, libpath, 1<<15)
        else:
            self.log("no_exec: not copying target library")

        db_path = os.path.join(os.getcwd(),"target.db")
        if os.path.exists(db_path):
            os.remove(db_path)

        self.message("Finished %d/%d/%d"%(d,c,t))

    def run_proc(self,proc):
        with proc:
            n = proc.begin()
            for i in range(n):
                proc.step(i)
            proc.end()

    def copy_remote_settings(self, dbpath, target_library ):
        # if a remote database was copied locally, copy
        # the settings from that database to the new database
        # the next step will copy the new database back
        # to the target directory.
        #db_path = os.path.join(os.getcwd(),"remote.db")
        self.log("remote path: %s %s"%(dbpath,os.path.exists(dbpath)))
        if os.path.exists(dbpath):
            remote_sqlstore = SQLStore( dbpath )
            remote_settings = Settings( remote_sqlstore )
            remote_settings['_sync']=1 # token setting
            target_settings = Settings( target_library.sqlstore )
            for key,value in remote_settings.items():
                target_settings[key] = value
            remote_sqlstore.close()
            os.remove(dbpath)

    def setOperationsCount(self,count):
        """ reimplement this """
        pass

    def message(self,msg):
        """ reimplement this """
        self.log(msg)

    def getYesOrNo(self,msg,btn2="fixme"):
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
        for path in self.source_walk_ext(self.target_path,
                                         Song.supportedExtensions(),
                                         not self.no_exec):
            res=not self.data.exists(path)
            if 'candlebox' in path.lower() or 'tad' in path.lower():
                print(res,path)
            if res:
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

    def source_walk_ext(self, dirpath, extensions, delete_dirs=False):
        """ return all files from target source directory """
        #TODO: write without recursion
        x=self.target_source.breakpath( dirpath )[-3:]
        x=self.target_source.join(*x)
        self.message("Scanning Directory: %s"%x)
        items = self.target_source.listdir(dirpath)

        for item in items:
            if item == ".." or item == ".":
                continue
            path = self.target_source.join(dirpath,item)
            ext = os.path.splitext(item)[1]
            if ext in extensions:
                yield path
            elif self.target_source.isdir(path):
                for x in self.source_walk_ext(path, extensions, delete_dirs ):
                    yield x

        # this solution is less than ideal, since we have to list twice,
        # but it is the only way to delete a directory at the moment
        # if a child directory is deleted, this will result in the parent
        # being cleaned up if the parent becomes empty.
        # it would be better to run this AFTER the delete process.
        if len(items):
            items = self.target_source.listdir(dirpath)
        if len(items)==0 and delete_dirs:
            try:
                self.target_source.delete( dirpath )
            except PermissionError:
                sys.stderr.write("unable to delete %s\n"%dirpath)
            return


    def remove_path(self,filepath):
        self.log("delete: %s"%filepath)
        if not self.no_exec:
            self.target_source.delete(filepath)

    def copy_path(self, tgtpath):
        song, transcode = self.data.getValue( tgtpath )
        msg="copy: %s -> %s"%(song[Song.path],tgtpath)
        msg=''.join([ a if ord(a)<128 else "%02X"%ord(a) for a in msg])
        self.log(msg)
        if not self.no_exec:
            p = self.target_source.parent(tgtpath)
            self.target_source.mkdir( p )

            # TODO, COPY, TRANSCODE new FORCE OVERWRITE option
            if not self.no_exec and self.target_source.exists(tgtpath):
                return

            #copy_file(song[Song.path],tgtpath)
            source_copy_file(self.local_source,song[Song.path],
                             self.target_source, tgtpath, 1<<15)

    def transcode_path(self, tgtpath):
        song, transcode = self.data.getValue( tgtpath )
        self.log("Transcode  : %s -> %s"%(song[Song.path],tgtpath))
        if not self.no_exec:
            p = self.target_source.parent(tgtpath)
            self.target_source.mkdir( p )

        self.transcode_song(song,tgtpath)

    def transcode_local(self, tgtpath, outpath):
        song, transcode = self.data.getValue( tgtpath )
        self.log("Transcode-l: %s -> %s"%(song[Song.path],tgtpath))
        self.transcode_song(song,outpath)

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
        if srcpath.lower().endswith('mp3') and self.data.transcode_special:
            bitrate=0

        # TODO, COPY, TRANSCODE new FORCE OVERWRITE option
        if self.no_exec:# and self.target_source.exists(tgtpath):
            return
        self.encoder.transcode(srcpath,tgtpath,bitrate,vol=vol,metadata=metadata)

    # sync functions

    def data_init(self):

        songs = self.library.songFromIds( self.song_ids )
        for i,song in enumerate(songs):
            path = self.target_source.join(self.target_path,*Song.toShortPath(song))

            path = self.target_source.fix( path )
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
        name = "library.db"
        if isinstance(self.target_source,DirectorySource):
            name = "yue.db"

        libpath = self.target_source.join(self.target_path,name)
        #if os.path.exists(player_path):
        #    libpath = os.path.join(player_path,"music.xml")
        return libpath

    def createTargetLibrary(self):
        if self.target_library is not None:
            return self.target_library;

        sys.stdout.write("Generating target playlist & library\n")
        new_playlist= self.data.getTargetPlaylist()

        # TODO create local then COPY to target path
        db_path = os.path.join(os.getcwd(),"target.db")
        if os.path.exists(db_path):
            os.remove(db_path)
        sqlstore = SQLStore(db_path)
        library = Library( sqlstore )

        with library.sqlstore.conn:
            c = library.sqlstore.conn.cursor()
            for song in new_playlist:
                if "artist_key" in song:
                    del song['artist_key']
                if self.target_prefix_path:
                    song[Song.path] = self.target_source.join( \
                                      self.target_prefix_path,song[Song.path])
                library._insert(c, **song)

        self.target_library = library

        #db_path = self.getTargetLibraryPath()
        #source_copy_file(self.local_source ...,
         #                    self.target_source, ...)

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

    def _exists(self,path):
        if path in self.data:
            return path;
        for key in self.data.keys():
            if key.lower() == path.lower():
                return key;
        return None;

    def exists(self,path):
        return self._exists(path) is not None

    def delete(self,path):
        if self.data_copy == None:
            self.data_copy = dict(self.data)
        key = self._exists(path)
        if key is not None:
            del self.data[ key ]
        else:
            print("error deleteing: %s"%path)
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

def saveM3uPlaylist(wf,songs):
    """
    wf: as codecs.open(path,"w","utf-8") or equivalent
    songs: a playlist, list of song-dictionaries
    """
    songs.sort(key=lambda x:x[Song.album])
    songs.sort(key=lambda x:sort_parameter_str(x,Song.artist))
    #with codecs.open(filename,"w","utf-8") as wf :
    #http://anythingbutipod.com/forum/showthread.php?t=67351
    wf.write("#EXTM3U\r\n")
    for song in songs:
        dur=song[Song.length]
        a=song[Song.artist]
        t=song[Song.title]
        wf.write("#EXTINF:%d,%s - %s\r\n"%(dur,a,t));
        wf.write(song[Song.path]+"\r\n");

def saveCowonPlaylist(wf,songs):
    """
    wf: as codecs.open(path,"w","utf-8") or equivalent
    songs: a playlist, list of song-dictionaries
    """
    songs.sort(key=lambda x:x[Song.album])
    songs.sort(key=lambda x:sort_parameter_str(x,Song.artist))
    #with codecs.open(filename,"w","utf-8") as wf :
    #http://anythingbutipod.com/forum/showthread.php?t=67351
    wf.write("#EXTM3U\r\n")
    for song in songs:
        try:
            path = getShortName_COWON(song[Song.path]);
        except OSError as e:
            sys.stdout.write("error saving song to playlist - %s\n"%e)
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

    #target = "ftp://nsetzer:password@192.168.0.9:2121/Music"
    target = "test"
    transcode = SyncManager.T_NON_MP3
    equalize = True
    bitrate = 320
    run = True
    no_exec = False
    format=SyncManager.P_M3U
    target_prefix=os.getcwd()

    sqlstore = SQLStore(db_path)
    Library.init( sqlstore )
    PlaylistManager.init( sqlstore )

    library = Library.instance()
    playlist = library.search("(.abm 0 limited execution)")
    uids = [s[Song.uid] for s in playlist]

    print(os.path.realpath(db_path))
    print("lib",len(library))

    dp = [("limited","limited"),]

    sm = SyncManager(library,uids,target,ffmpeg,
            transcode=transcode,
            equalize=equalize,
            dynamic_playlists = dp,
            target_prefix=target_prefix,
            playlist_format=format,
            no_exec=no_exec)
    sm.run()

if __name__ == '__main__':
    main()
