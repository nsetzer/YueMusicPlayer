
import traceback
from argparse import ArgumentError
import shlex
import sys

from .library import Library
from .history import History
from .song import Song
from .util import format_delta

from collections import defaultdict

class ReplArgumentParser(object):
    """docstring for ArgParse"""
    def __init__(self,  args, shortcuts=None):
        super(ReplArgumentParser, self).__init__()



        self.shortcuts = shortcuts or dict()
        self.switch = set()
        self.kwargs = dict()

        i=0;
        parse_opts=True
        while i < len(args):
            tmp = args[i]
            if tmp=='--':
                parse_opts = False;
                args.pop(i)
            elif parse_opts and tmp.startswith("--"):
                args.pop(i)
                if '=' not in tmp:
                    self.kwargs[tmp[2:]] = True
                else:
                    k,v = tmp[2:].split('=',1)
                    self.kwargs[k]=v
            elif parse_opts and tmp.startswith("-"):
                args.pop(i)
                tmp = tmp[1:]
                for c in tmp[:-1]:
                    self.switch.add(c)
                if tmp[-1] in self.shortcuts:
                    value = True
                    if len(args) > i:
                        value = args.pop(i)
                    key = self.shortcuts[tmp[-1]]
                    print(key,value)
                    self.kwargs[key]=value
            else:
                parse_opts = False;
                i+=1

        self.args = args

    def assertMinArgs(self,n):
        if len(self.args) < n :
            raise ArgumentError("Expected at least %d args"%n)

    def __contains__(self,x):
        return x in self.kwargs

    def __getitem__(self,x):
        if isinstance(x,str):
            return self.kwargs[x]
        return self.args[x]

    def __len__(self):
        return len(self.args)

    def __iter__(self):
        for arg in self.args:
            yield arg

class YueRepl(object):
    """docstring for YueRepl"""
    def __init__(self, device=None):
        super(YueRepl, self).__init__()
        self.root = None
        self.device = device
        self.alive = True

        self.helptopics = {}
        self.actions = {}

        if device is not None:
            self.actions["play"] = self.explay
            self.actions["pause"] = self.expause
            self.actions["stop"] = self.exstop
            self.actions["next"] = self.exnext
            self.actions["prev"] = self.exprev
            self.actions["status"] = self.excurrent
            self.actions["current"] = self.excurrent
            self.actions["pos"] = self.exposition
            self.actions["position"] = self.exposition
            self.actions["vol"] = self.exvolume
            self.actions["volume"] = self.exvolume
            self.actions["playpause"] = self.explaypause

        self.actions["stat"]    = self.exstat

        self.actions["help"]    = self.exhelp
        self.actions["exit"]    = lambda x : None
        self.actions["quit"]    = lambda x : None
        self.actions["exit"].__doc__ = " exit this program, save any changes"
        self.actions["quit"].__doc__ = self.actions["exit"].__doc__

    def registerAction( self, actname, actfunc):
        self.actions[actname] = actfunc

    def registerTopic( self, helpname, helpstring):
        self.helptopics[helpname] = helpstring

    def exec_(self,line):

        comments=False
        posix=True
        cmd, *args = shlex.split( line , comments, posix )

        act = self.actions.get(cmd,None)

        try:
            if act is not None:
                return act( args )
        except ArgumentError as e:

            sys.stdout.write(str(e))
            sys.stdout.write("\n")
        except Exception as e:
            traceback.print_exc()
            sys.stdout.write(str(e))
            sys.stdout.write("\n")

        return self.exhelp( [cmd,] )

    def repl(self):

        sys.stdout.write( "Block Archive Repl\n" )
        inp = ""
        while self.alive:

            #sys.stdout.write("\n%s\n"%self.pwd)
            inp = input("$ ").strip()

            if inp == "quit" or inp == "exit":
                break;
            elif inp:
                self.exec_(inp)

    def exhelp(self,args):
        """display this message
        $0 [name ...]
        """
        if len(args)==0:
            for name in sorted(self.actions.keys()):
                act = self.actions[name]
                desc = ""
                if act.__doc__ is not None:
                    desc = act.__doc__.split("\n")[0]
                sys.stdout.write( "%-16s : %s\n"%(name,desc) )

            if len(self.helptopics):
                sys.stdout.write( "Other Topics:\n" )
                for name in sorted(self.helptopics.keys()):
                    desc = self.helptopics[name]
                    desc = desc.split("\n")[0]
                    sys.stdout.write( "%-16s : %s\n"%(name,desc) )

            return
        for name in args:
            if name in self.actions:
                act = self.actions[name]
                doc = act.__doc__ or ""
                doc = doc.replace("$0",name)
                doc = doc.replace("        ","\n")
                sys.stdout.write(doc+"\n")
            elif name in self.helptopics:
                msg = self.helptopics[name]
                sys.stdout.write(msg+"\n")
            else:
                sys.stdout.write("unknown action `%s`\n"%name)

    #TODO play by index
    def explay(self,args):
        """ play song
        $0 [-n idx]
        """
        self.device.play()

    def expause(self,args):
        """ pause playback of current song
        $0
        """
        self.device.pause()

    def exstop(self,args):
        """ stop playback of current song
        $0
        """
        self.device.unload()

    def explaypause(self,args):
        """ play / pause current song
        $0
        """
        self.device.playpause()

    def exnext(self,args):
        """ play the next song in the playlist
        $0
        """
        self.device.next()

    def exprev(self,args):
        """ play the previous song in the playlist
        $0
        """
        self.device.prev()

    def exposition(self,args):
        """ seek to a time within the current playing song
        $0 [ t ]
        """
        args = ReplArgumentParser(args)

        if len(args) > 0:
            self.device.seek( int(args[0]) )

        text = "%d / %d\n"%(self.device.position(), self.device.duration())
        sys.stdout.write( text)

    def exvolume(self,args):
        """ set the current volume
        $0 [ value ]

        value: 0..100
        """
        args = ReplArgumentParser(args)

        if len(args) > 0:
            self.device.setVolume( int(args[0])/100.0 )

        text = "volume: %d\n"%(int(self.device.getVolume()*100))
        sys.stdout.write(text)

    def excurrent(self,args):
        """ display information on current song
        $0
        """
        idx,song = self.device.current()

        sys.stdout.write( "%d/-- %s\n"%(idx,self.device.state()) )
        text = "%s - %s\n"%(song['artist'], song['title'])
        sys.stdout.write( text)
        text = "%d / %d\n"%(self.device.position(), self.device.duration())
        sys.stdout.write( text)

    def exstat(self,args):
        """ print library statistics """
        # term will execute a search, contraining the statistics
        c_ply=0 # total play count
        c_len=0 # total play time
        c_frq=0

        args = ReplArgumentParser(args,{'s':'search'})

        query = None
        if 'search' in args:
            query = str(args['search'])
        lib = Library.instance().search(query)
        count = len(lib);

        for song in lib:
            c_ply += song[Song.play_count]
            c_len += song[Song.length]*song[Song.play_count]
            c_frq += song[Song.frequency]
        c_frq /= count;

        sys.stdout.write( "Song Count        : %d\n"%count)
        sys.stdout.write( "Play Time         : %s\n"%format_delta(c_len))
        sys.stdout.write( "Play Time (raw)   : %s\n"%c_len)
        sys.stdout.write( "Play Count        : %d\n"%c_ply)
        sys.stdout.write( "Play Count (AVG)  : %s\n"%(c_ply/count))
        sys.stdout.write( "Frequency         : %d\n"%(c_frq))



        hist_arts = defaultdict(int)
        hist_records = History.instance().search(None);
        hist_count=len(hist_records)
        for r in hist_records:
            hist_arts[r['artist']] += 1

        lib_arts = defaultdict(int)
        lib_records=Library.instance().search(None)
        lib_count=len(lib_records)
        for r in lib_records:
            lib_arts[r['artist']] += 1

        items = sorted(list(hist_arts.items()),key=lambda x:x[1],reverse=True)
        scaled=[]
        for key,value in items[:10]:
            print("%3d/%3d %.4f/%.4f %s "%(value,hist_count,value/hist_count,lib_arts[key]/lib_count,key))
            g = lambda a,b : (a-b)
        for key,value in items:
            scaled.append(  (key,g(value/hist_count , lib_arts[key]/lib_count))  )
        scaled.sort(key=lambda x:x[1],reverse = True)
        for key,value in scaled[:10]:
          print("%.4f %s"%(value,key))
        for key,value in scaled[-10:]:
          print("%.4f %s"%(value,key))
