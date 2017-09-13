
import codecs
import io
from collections import defaultdict
import re
"""
() denotes an empty list
{} denotes an empty dict
7, may be parsed incorrectly without some effort -- what is the expectation?

types: bool, int, float, null, list, dict
    true, false not True False? or both.

struct:
    !struct_name{}
    A yml instance can have a structure registered
        (automatically by dump) or manually prior to load)
    A struct is just a class that has its members dumped to a dictionary
    the dictionary is prefaced by the type of struct for de-serialization

"""

class YmlException(Exception):
    pass

class YmlSyntaxError(Exception):

    def __init__(self, line_num, position, message):
        msg="%d:%d %s"%(line_num,position,message)
        super(YmlSyntaxError,self).__init__(msg)

class StrPos(str):
    """ A string tagged with a position value"""
    def __new__(cls, strval, pos, end, quoted=False):
        inst = super(StrPos, cls).__new__(cls, strval)
        inst.pos = pos
        inst.end = end
        inst.quoted = quoted # weather the text came from a quoted string
        return inst

# match anything that remotely looks like a number
_re_string_number = re.compile("^[\d+-._honb]+$")

class YmlGrammar(object):

    class TokenState(object):
        """ state variables for tokenizer """
        def __init__(self,line_num):
            self.tokens = []
            self.stack = [ self.tokens ]
            self.line_num = line_num

            self.isList= True

            self.start = 0;
            self.tok = ""

            self.quoted = False
            self.join_special = False # join 'special' characters

            # for a dictionary, apppend must be called twice
            # first for the key then for the value
            self.dict_key = None

        def append(self,idx, new_start, force=False):
            """ append a token to the top of the stack
                clear all special states
            """

            if self.tok or force:
                if self.isDict():
                    if self.dict_key is None:
                        self.dict_key = StrPos(self.tok,self.start,idx,self.quoted)
                    else:
                        v = StrPos(self.tok,self.start,idx,self.quoted)
                        self.stack[-1][self.dict_key]=v
                        self.dict_key = None
                else:
                    v = StrPos(self.tok,self.start,idx,self.quoted)
                    self.stack[-1].append(v)
            self.join_special = False
            self.quoted = False

            self.tok = ""
            self.start=new_start

        def push(self,isList=True):
            new_level = [] if isList else {}
            if self.isDict() :
                if self.dict_key is None:
                    raise YmlException("Dictionary key not specified")
                self.stack[-1][self.dict_key] = new_level
                self.dict_key = None
            else:
                self.stack[-1].append(new_level)
            self.stack.append(new_level)

        def pop(self):

            if self.isDict() and self.dict_key is not None:
                raise YmlException("Unmatched dictionary key")

            self.stack.pop()

        def check(self):
            if len(self.stack) == 0:
                raise YmlException("Empty stack (check parenthesis)")
            if len(self.stack) > 1:
                raise YmlException("Unterminated Block")
            if self.quoted:
                raise YmlException("Unterminated Double Quote")

        def isDict(self):
            return isinstance(self.stack[-1],dict)

    def __init__(self):
        super(YmlGrammar, self).__init__()

        self.tok_escape = "\\"
        self.tok_quote = "\""
        self.tok_nest_begin = "({"
        self.tok_nest_end = ")}"
        self.tok_whitespace = " "
        self.tok_separator = ","
        self.tok_list_begin = '('
        self.tok_dict_separator = '='
        self.tok_comment = "#"

    def parse(self,rf, line_num,input):

        idx = 0;
        state = YmlGrammar.TokenState(line_num)

        state.lines = 1

        while idx < len( input ) and len(state.stack)>0:
            c = input[idx]
            optional_read = False # , acts as line continuation character

            if not state.quoted:
                if c == self.tok_quote:
                    state.append(idx,idx+1)
                    state.quoted = True
                elif c == self.tok_comment:
                    input = input[:idx-1]
                elif c in self.tok_nest_begin:
                    state.append(idx,idx+1)
                    state.push(c == self.tok_list_begin)
                elif c in self.tok_nest_end:
                    state.append(idx,idx+1)
                    state.pop()
                elif c == self.tok_separator:
                    state.append(idx,idx+1)
                    optional_read = True
                elif c in self.tok_whitespace:
                    state.append(idx,idx+1)
                elif state.isDict() and c in self.tok_dict_separator:
                    state.append(idx,idx+1)
                else:
                    state.tok += c
            else: # is quoted
                if c == self.tok_escape:
                    idx+=1
                    if idx >= len(input):
                        raise YmlException("Escape sequence expected character at position %d"%idx)
                    c = input[idx]
                    if c == 'n':
                        state.tok += "\n"
                        #idx += 1
                    elif c == 'x':
                        if idx+2 >= len(input):
                            raise YmlException("Escape sequence expected character at position %d"%idx)
                        state.tok+=chr(int(input[idx+1:idx+3],16))
                        idx += 2
                    elif c == 'u':
                        if idx+4 >= len(input):
                            raise YmlException("Escape sequence expected character at position %d"%idx)
                        state.tok+=chr(int(input[idx+1:idx+5],16))
                        idx += 4
                    else:
                        state.tok += input[idx]
                elif c == self.tok_quote:
                    state.append(idx,idx+1,True)
                else:
                    state.tok += c
            idx += 1
            if idx >= len(input):
                text = ""
                if len(state.stack) > 1 or \
                   optional_read:
                    text = rf.readline().strip()
                    state.lines += 1
                if state.quoted:
                    text = rf.readline().rstrip()
                    state.lines += 1
                input += text

        state.check()
        state.append(idx,idx) # collect anything left over

        if len(state.tokens) == 0: # empty string input
            return StrPos("",0,0,True), state.lines
        elif len(state.tokens) == 1:
            return state.tokens[0], state.lines

        return state.tokens, state.lines

class YML(object):
    """docstring for yoml

    version 1: dict-of-dict-of-basic-type
    version 2: allow infinite nesting of list/map

    # getitem should return a custom dict impl which, on assign
    # sets a dirty bit in the configuration

    # changing a setting should call a callback
    # the callback can be connected to Qt to emit a signal
    # the signal can notify a timer
    # the timer, if it times out should save the settings

    # settings should support sharding : separate sections  go to different
    # files, this involves a light weight wrapper which inspects the value
    # of the get_item and routes to the appropriate settings instance

    base_types = int float string None
    basic_types = int float string list-of-string:base_type dict-of-string:base_type

    grammar is looking something like this:
        [section]
        parameter_name=parameter_value

        parameter_value := int          (in order of precedence)
                           float
                           null
                           list
                           dict-list
                           quoted string

        {(" -- mark the beginning of a special section
        ")} -- mark the end of a special section
        ,   -- separates two special sections into a list
        quoted region -- take text literally, except for \" and \x00

        dict-list -- is a list of strings of the form
            "variable_name=parameter_value"

        are dictionaries ordered? (yes)


    """
    def __init__(self):
        super(YML, self).__init__()

        self.tab_width = 2
        self.max_width = 80

        self.yg = YmlGrammar()

    def loads(self,s):
        input = io.StringIO(s)
        return self.load(input)

    def load(self,rf):

        if isinstance(rf,str):
            with codecs.open(rf,"r","utf-8") as rf2:
                return self.load(rf2)

        cfg = dict()

        current_section = "default"
        cfg[current_section] = dict()

        line_num = 1
        for line in rf:
            line = line.strip();
            if not line:
                continue # skip blank lines


            if line.startswith('#'):
                continue # a comment has been found
            if line.startswith('['):
                # found the start of a section
                current_section = self._load_section_header(line)
                cfg[current_section] = dict()
            else:
                # found a new parameter to add to the current section
                param,value,lines = self._load_parameter_value(rf,line_num,line)
                cfg[current_section][param] = value
                line_num += lines

        if not cfg['default']:
            del cfg['default']

        return cfg

    def _load_section_header(self,line):
        idx = line.find(']')
        if idx < 0 :
            raise YmlException("unmateched section bracket")

        current_section = line[1:idx]

        return current_section

    def _load_parameter_value(self,rf,line_num,line):
        """
        read the line character by character,
        if a \ or , is encountered at EOL, read the next line of the file
        """

        idx = line.find('=')
        if idx < 0 :
            raise YmlException("parameter not well formed <%s>"%line)
        param,text = line.split("=",1)
        o,lines = self.yg.parse(rf,line_num,text)
        # convert the output based on string values
        param_value = self._convert(o)
        return param.strip(),param_value,lines

    def _convert(self,o):
        """
        converts a parsed value into the actual value

        convert a StrPos into a int,float or str
        recursivley convert list or dictioanry types
        """

        if isinstance(o,str):
            if o.quoted: # a literal string
                return str(o)

            if o == "null": # special case null value
                return None

            if o.lower() == "true":
                return True
            if o.lower() == "false":
                return False

            try:
                # remove underscores
                # check for 0b 0n 0o 0x, for base 2,4,8,16
                return int(o)
            except:
                pass
            try:
                return float(o)
            except:
                pass
            return str(o)
        elif isinstance(o,(list,tuple,set)):
            return [ self._convert(v) for v in o ]
        elif isinstance(o,dict):
            return { self._convert(k):self._convert(v) for k,v in o.items() }

        raise YmlException("type %s not supported in this context."%(type(o)))

    def dumps(self,o):

        output = io.StringIO()
        #codecinfo = codecs.lookup("utf8")
        #wrapper = codecs.getwriter("utf-8")(output)
        #self.dump(o,wrapper)
        self.dump(o,output)
        contents = output.getvalue()
        return contents

    def dump(self,o,wf):

        if isinstance(wf,str):
            with codecs.open(wf,"w","utf-8") as wf2:
                return self.dump(o,wf2)

        self._init_dump()

        #wf.write("hello \u3042")
        for section_name,section in o.items():
            self._dump_section(wf,section_name,section)
            wf.write("\n")

    def _init_dump(self):
        #self.listmark = ("%%%ss"%(self.tab_width))%("-")
        self.listmark = " "*self.tab_width
        self.space = (" "*self.tab_width)

    def _dump_section(self,wf,section_name,section):
        """
        here, a section is a dictionary of key:basic_type
        """
        wf.write("["+section_name+"]\n")
        if not hasattr(section,"items"):
            raise Exception("section `%s` not an dictionary."%section_name)
        for parameter_name,parameter_value in section.items():
            self._dump_parameter(wf,parameter_name,parameter_value)

    def _dump_parameter(self,wf,name,value):
        j = "\n" + " "*(len(name)+1)
        lines = self._stringify(value,0,self.max_width)
        s_value = j.join(lines)
        wf.write("%s=%s\n"%(name,s_value))

    def _stringify(self,item,depth,width):

        if isinstance(item,(list,tuple,set)):
            return self._stringify_list(item,depth+1,width)

        if isinstance(item,dict):
            return self._stringify_dict(item,depth+1,width)

        if isinstance(item,str):
            return self._stringify_string(item)

        if item is None:
            return ["null",]

        # todo: floats should have special consideration

        return [str(item),]

    def _stringify_list(self,item,depth,width):
        # coma turns a unquoted string into a list (csv)
        # the parenthesis are optional

        ts = "( "
        te = " )"
        tm = ", "
        sm = ","
        ss = " "*len(ts)
        se = " "*len(te)

        items_s=[]
        for v in item:
            vs = self._stringify(v,depth+1,width-len(ts))
            items_s += vs
        #l = sum([ len(item) for item in items_s ])


        i=0;
        while i < len(items_s):
            while len(items_s[i]) < width and len(items_s)>i+1:
                if len(items_s[i]+items_s[i+1]) < width:
                    items_s[i] += tm + items_s.pop(i+1)
                else:
                    break
            i+=1
        # add a line continuation character
        if len(items_s)>1 and not items_s[0].endswith(sm):
            items_s[0] += sm

        # everything byt the last line needs a line continuatio character
        # left pad the string with the offest introduced
        for i in range(1,len(items_s)-1):
            if not items_s[i].endswith(sm):
                items_s[i] += sm
            if depth > 1:
                items_s[i] = ss + items_s[i]

        if depth > 1:
            items_s[0] = ts + items_s[0]
            items_s[-1] += te

        if depth > 1 and len(items_s) > 1:
            items_s[-1] = ss + items_s[-1]
        return  items_s

    def _stringify_dict(self,item,depth,width):
        # dictionary is just a list, bookended by a brace
        # with the requirement that each term in the list
        # begins with a valid python variable name followed
        # by an equals sign

        ts = "{ "
        te = " }"
        tm = ", "
        ss = " "*len(ts)
        se = " "*len(te)

        items_s = []
        for k,v in item.items():
            ks = self._stringify(k,depth+1,width-len(ts))
            if len(ks)>1:
                raise YmlException("error")
            ks = ks[0]
            vs = self._stringify(v,depth+1,width-len(ts))

            items_s.append("%s=%s"%(ks,vs[0]))
            items_s += vs[1:]

        l = sum([ len(item) for item in items_s ])

        if l < width:
            items_s = [ ts + tm.join(items_s) + te]
        else:
            items_s[0] = ts+items_s[0]
            if not items_s[0].endswith(tm):
                items_s[0] += tm
            for i in range(1,len(items_s)-1):
                if not items_s[i].endswith(tm):
                    items_s[i] += tm
                items_s[i] = ss + items_s[i]
            items_s[-1] = ss + items_s[-1] + te
        return items_s

    def _stringify_string(self,item):
        # 0.0 .0 0.
        # 0o10 0x10 0n10 0b10
        # 10 123 1_23
        l_item = item.lower()
        item = item.replace("\"","\\\"")
        item = item.replace("\n","\\n")

        if l_item in ("null","false","true"):
            return ["\"" + item + "\"",]

        if _re_string_number.match(item) is not None:
            return ["\"" + item + "\"",]

        if not item.isalnum():
            return ["\"" + item + "\"",]

        return [item,]

def dump(o,wf):
    return YML().dump(o,wf)

def dumps(o):
    return YML().dumps(o)

def load(rf):
    return YML().load(rf)

def loads(s):
    return YML().loads(s)

def main():

    #cfg = YamlConfig("./test.yaml")
    #cfg = TomlConfig("./test.toml")

    cfg = {}
    cfg['sshconfig'] = {}
    cfg['sshconfig']['default'] = 0
    cfg['sshconfig']['test'] = {7:4,"7":4}
    cfg['sshconfig']['profiles'] = [
        {"user":"admin","password":"","port":22},
        {"user":"null","password":"a\"\u3042\"", "port":None} ]

    cfg['file_assoc'] = {}
    cfg['file_assoc']["ext_text"] = [".txt",".log",".c",".ctm",".h++",".yaml",".cfg"]
    cfg['file_assoc']["2d"] = [ [0,1], [2,3], [4,5], [6,7], \
         [8,9,[1,2,3,4,5,6,7,8,90210,0,1,2],] ]
    cfg['file_assoc']["bvalue"] = False

    s = dumps(cfg)
    print(s)
    o = loads(s)
    s = dumps(o)
    print(s)


if __name__ == '__main__':
    main()