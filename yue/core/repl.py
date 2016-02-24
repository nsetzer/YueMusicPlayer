
import shlex
import sys

class ReplArgumentParser(object):
    """docstring for ArgParse"""
    def __init__(self, line):
        super(ReplArgumentParser, self).__init__()

        comments=False
        posix=True
        cmd, *args = shlex.split( line , comments, posix )

        self.switch = set()
        self.kwargs = {}

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
                for c in tmp[1:]:
                    self.switch.add(c)
            else:
                parse_opts = False;
                i+=1

        self.cmd = cmd
        self.args = args

    def assertMinArgs(self,n):
        if len(self.args) < n :
            raise ArgumentError("Expected at least %d args"%n)

    def __getitem__(self,x):
        return self.args[x]

    def __len__(self):
        return len(self.args)

    def __iter__(self):
        for arg in self.args:
            yield arg

class YueRepl(object):
    """docstring for EBFSRepl"""
    def __init__(self, device):
        super(YueRepl, self).__init__()
        self.device = device
        self.alive = True

        self.actions = {}

        self.actions["help"]    = self.exhelp
        self.actions["exit"]    = lambda x : None
        self.actions["quit"]    = lambda x : None
        self.actions["exit"].__doc__ = "exit this program, save any changes"
        self.actions["quit"].__doc__ = self.actions["exit"].__doc__

    def exec_(self,line):

        args = ReplArgumentParser(line)

        act = self.actions.get(args.cmd,None)

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

        return self.exhelp( [args.cmd,] )

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
            return
        for name in args:
            if name in self.actions:
                act = self.actions[name]
                doc = act.__doc__ or ""
                doc = doc.replace("$0",name)
                doc = doc.replace("        ","\n")
                sys.stdout.write(doc+"\n")
            else:
                sys.stdout.write("unknown action %s\n"%name)
