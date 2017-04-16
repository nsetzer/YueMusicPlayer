#! python $this
from __future__ import unicode_literals
import re
# 2to3 -w $this
import sys
if sys.version_info >= (3, 0):
    unicode=str

_consonants_ = set(__import__('string').ascii_lowercase) - set("aeioun")

class SymTr(object):
    """ Use this object to convert a user input string from plain ascii
        phonetics to hiragana or katakana. if string is from a QLineEdit
        this is as easy as passing the string to this object. setting
        the text of the lineedit to nstring, then calling QLineEdit.cursorBackward
        with the argument SymTr.rposition to reset the cursor
    """
    Hiragana = None;
    HiraganaUpper = None;
    Katakana = None;

    ReverseKatakana = None;
    ReverseHiragana = None;
    ReverseHiraganaUpper = None;
    Reverse = None

    def __init__(self,unistr,live=True,hu=False):

        self.live=live # used to quarenteen things that should happen
                       # only when characters are being typed in vs
                       # when we are given a whole word

        #self.ostring = u""       # the original string
        #self.nstring = u""       # the resulting string
        #self.rstring = ""        # roman string, no kana
        self.ostring = unicode(unistr)# force type to unicode
        self.nstring = unicode(unistr)
        self.rstring = unicode(unistr)
        self.position = 0        # index after the last change
                                 # where the cursor should be moved to
        self.rposition = 0       # positon from the right edge of the string
        self.success = False     # whether anything changed

        self.Hiragana = SymTr.HiraganaUpper
        self.Reverse = SymTr.ReverseKatakana.copy()
        self.Reverse.update(SymTr.ReverseHiraganaUpper)

        self._transform()

    def _init_rex(self):

        rex_mk_new = r";;[a-z|\-]+"
        rex_mk_old = r"[\u30A0-\u30ff][a-z|\-]+"

        rex_mh_new = r';;[A-Z|\*]+'
        rex_mh_old = r"[\u3040-\u309f][A-Z|\*]+"

        # old refers to inserting ascii letters next unicode characters
        # that were already in the string
        mk_old = re.search(rex_mk_old,self.ostring)
        mh_old = re.search(rex_mh_old,self.ostring)

        # new refers to finding two semicolons or colons, and replaceing
        # that, and the following ascii with kana
        mk_new = re.search(rex_mk_new,self.ostring)
        mh_new = re.search(rex_mh_new,self.ostring)

        rexset = ( ((mk_old,0),(mk_new,2)) , ((mh_old,0),(mh_new,2)) )
        return rexset

    def _transform(self):
        idx = self.ostring.find("::")
        if idx >= 0:
        # ######################################################
        # reverse process
            output = input = ""
            mns = re.compile(r"^([^\s]+).*$").search(self.ostring[idx:])
            if mns:
                input = mns.group(1)
                output=input[2:]

            if output:
                output=self.convertFrom(output)
                self.nstring = self.ostring.replace(input, output)
                self.success = True
                self.position = idx + len(output)
        else:
        # ######################################################
        # forward process
            funcs=[self.convertToKatakana,self.convertToHiragana]
            rexset= self._init_rex();
            for func,data in zip(funcs,rexset):
                for match,i in data:
                    if match == None:
                        continue
                    substr = match.group()
                    input = substr[i:]
                    repstr = func(input)
                    if repstr and input!=repstr:
                        self.nstring = self.nstring.replace(substr,repstr)
                        self.position = self.ostring.index(substr) + len(repstr)
                        self.success = True
                        break;

        # calculate the distance from the end of the str to the last character changed
        self.rposition = len(self.nstring) - self.position

    def _transform_match(self,table,string):
        # test portions of the string to see if they
        # can be SymTrd into Japanese. start with a 3 character
        # chunk, work down to a single character. cut away matches
        # or remove a single character then repeat until the string
        # is empty
        match = 0
        kana = ""
        for i in range(3,0,-1):
            input = string[0:i]
            kana = self.substringToSymbol(table,input)
            if kana != "" and kana!=input:
                match = i
                break
        return match,kana

    def _transform_to(self,table,string):
        nstr = ""
        match = 0
        kana = ""
        while len(string) > 0 : # 2014 06 10 changed from > 0
            match,kana = self._transform_match(table,string)
            # cut out the matched portion of the string
            # or cut out a single character
            if match > 0 :
                #if there was a match add it to the new str
                if nstr and nstr[-1]==string[0]:
                    nstr = nstr[:-1]+table['dd']+kana
                else:
                    nstr += kana
                string = string[match:]
            else:
                nstr += string[0]
                string = string[1:]
        return nstr

    def _transform_from(self,table,string):
        nstr = ""
        match = 0
        kana = ""
        duplicate_next = False
        while len(string) > 0 : # 2014 06 10 changed from > 0
            match,chara = self._transform_match(table,string)
            if match > 0 :
                if duplicate_next:
                    nstr += chara[:1]
                    duplicate_next = False

                if chara=='dd' or chara=="DD":
                    duplicate_next = True
                else:
                    nstr += chara

                string = string[match:]
            else:
                nstr += string[0]
                string = string[1:]
        return nstr

    def convertToHiragana(self,string):
        return self._transform_to(self.Hiragana,string)

    def convertToKatakana(self,string):
        return self._transform_to(self.Katakana,string)

    def convertFrom(self,string):
        return self._transform_from(self.Reverse,string)

    def substringToSymbol(self,symtbl,substr):
        if substr in symtbl:
            return symtbl[substr]
        return substr

# https://en.wikipedia.org/wiki/Romanization_of_Russian
# Passport (2013), ICAO

def init_KanaTables():
    """
        dictionary version
    """

    Hiragana = {}
    Katakana = {}

    Hiragana["a"   ] = "\u3042"
    Hiragana["i"   ] = "\u3044"
    Hiragana["u"   ] = "\u3046"
    Hiragana["e"   ] = "\u3048"
    Hiragana["o"   ] = "\u304a"
    Hiragana["ka"  ] = "\u304b"
    Hiragana["ki"  ] = "\u304d"
    Hiragana["ku"  ] = "\u304f"
    Hiragana["ke"  ] = "\u3051"
    Hiragana["ko"  ] = "\u3053"
    Hiragana["kya" ] = "\u304d\u3083"
    Hiragana["kyu" ] = "\u304d\u3085"
    Hiragana["kyo" ] = "\u304d\u3087"
    Hiragana["sa"  ] = "\u3055"
    Hiragana["shi" ] = "\u3057"
    Hiragana["su"  ] = "\u3059"
    Hiragana["se"  ] = "\u305b"
    Hiragana["so"  ] = "\u305d"
    Hiragana["sha" ] = "\u3057\u3083"
    Hiragana["shu" ] = "\u3057\u3085"
    Hiragana["sho" ] = "\u3057\u3087"
    Hiragana["ta"  ] = "\u305f"
    Hiragana["chi" ] = "\u3061"
    Hiragana["tsu" ] = "\u3064"
    Hiragana["te"  ] = "\u3066"
    Hiragana["to"  ] = "\u3068"
    Hiragana["cha" ] = "\u3061\u3083"
    Hiragana["chu" ] = "\u3061\u3085"
    Hiragana["cho" ] = "\u3061\u3087"
    Hiragana["na"  ] = "\u306a"
    Hiragana["ni"  ] = "\u306b"
    Hiragana["nu"  ] = "\u306c"
    Hiragana["ne"  ] = "\u306d"
    Hiragana["no"  ] = "\u306e"
    Hiragana["nya" ] = "\u306b\u3083"
    Hiragana["nyu" ] = "\u306b\u3085"
    Hiragana["nyo" ] = "\u306b\u3087"
    Hiragana["ha"  ] = "\u306f"
    Hiragana["hi"  ] = "\u3072"
    Hiragana["fu"  ] = "\u3075"
    Hiragana["he"  ] = "\u3078"
    Hiragana["ho"  ] = "\u307b"
    Hiragana["hya" ] = "\u3072\u3083"
    Hiragana["hyu" ] = "\u3072\u3085"
    Hiragana["hyo" ] = "\u3072\u3087"
    Hiragana["ma"  ] = "\u307e"
    Hiragana["mi"  ] = "\u307f"
    Hiragana["mu"  ] = "\u3080"
    Hiragana["me"  ] = "\u3081"
    Hiragana["mo"  ] = "\u3082"
    Hiragana["mya" ] = "\u307f\u3083"
    Hiragana["myu" ] = "\u307f\u3085"
    Hiragana["myo" ] = "\u307f\u3087"
    Hiragana["ya"  ] = "\u3084"
    Hiragana["yu"  ] = "\u3086"
    Hiragana["yo"  ] = "\u3088"
    Hiragana["ra"  ] = "\u3089"
    Hiragana["ri"  ] = "\u308a"
    Hiragana["ru"  ] = "\u308b"
    Hiragana["re"  ] = "\u308c"
    Hiragana["ro"  ] = "\u308d"
    Hiragana["rya" ] = "\u308a\u3083"
    Hiragana["ryu" ] = "\u308a\u3085"
    Hiragana["ryo" ] = "\u308a\u3087"
    Hiragana["wa"  ] = "\u308f"
    Hiragana["wo"  ] = "\u3092"
    Hiragana["nn"  ] = "\u3093"
    Hiragana["ga"  ] = "\u304c"
    Hiragana["gi"  ] = "\u304e"
    Hiragana["gu"  ] = "\u3050"
    Hiragana["ge"  ] = "\u3052"
    Hiragana["go"  ] = "\u3054"
    Hiragana["gya" ] = "\u304e\u3083"
    Hiragana["gyu" ] = "\u304e\u3085"
    Hiragana["gyo" ] = "\u304e\u3087"
    Hiragana["za"  ] = "\u3056"
    Hiragana["ji"  ] = "\u3058"
    Hiragana["zu"  ] = "\u305a"
    Hiragana["ze"  ] = "\u305c"
    Hiragana["zo"  ] = "\u305e"
    Hiragana["ja"  ] = "\u3058\u3083"
    Hiragana["ju"  ] = "\u3058\u3085"
    Hiragana["jo"  ] = "\u3058\u3087"
    Hiragana["da"  ] = "\u3060"
    Hiragana["ji"  ] = "\u3062"
    Hiragana["zu"  ] = "\u3065"
    Hiragana["de"  ] = "\u3067"
    Hiragana["do"  ] = "\u3069"
    Hiragana["ba"  ] = "\u3070"
    Hiragana["bi"  ] = "\u3073"
    Hiragana["bu"  ] = "\u3076"
    Hiragana["be"  ] = "\u3079"
    Hiragana["bo"  ] = "\u307c"
    Hiragana["bya" ] = "\u3073\u3083"
    Hiragana["byu" ] = "\u3073\u3085"
    Hiragana["byo" ] = "\u3073\u3087"
    Hiragana["pa"  ] = "\u3071"
    Hiragana["pi"  ] = "\u3074"
    Hiragana["pu"  ] = "\u3077"
    Hiragana["pe"  ] = "\u307a"
    Hiragana["po"  ] = "\u307d"
    Hiragana["pya" ] = "\u3074\u3083"
    Hiragana["pyu" ] = "\u3074\u3085"
    Hiragana["pyo" ] = "\u3074\u3087"
    Hiragana["*"   ] = "\u309c"
    Hiragana["dd"   ] = "\u3063" # Sokuon

    Katakana["a"   ] = "\u30a2"
    Katakana["i"   ] = "\u30a4"
    Katakana["u"   ] = "\u30a6"
    Katakana["e"   ] = "\u30a8"
    Katakana["o"   ] = "\u30aa"
    Katakana["ka"  ] = "\u30ab"
    Katakana["ki"  ] = "\u30ad"
    Katakana["ku"  ] = "\u30af"
    Katakana["ke"  ] = "\u30b1"
    Katakana["ko"  ] = "\u30b3"
    Katakana["kya" ] = "\u30ad\u30e3"
    Katakana["kyu" ] = "\u30ad\u30e5"
    Katakana["kyo" ] = "\u30ad\u30e7"
    Katakana["sa"  ] = "\u30b5"
    Katakana["shi" ] = "\u30b7"
    Katakana["su"  ] = "\u30b9"
    Katakana["se"  ] = "\u30bb"
    Katakana["so"  ] = "\u30bd"
    Katakana["sha" ] = "\u30b7\u30e3"
    Katakana["shu" ] = "\u30b7\u30e5"
    Katakana["sho" ] = "\u30b7\u30e7"
    Katakana["ta"  ] = "\u30bf"
    Katakana["chi" ] = "\u30c1"
    Katakana["tsu" ] = "\u30c4"
    Katakana["te"  ] = "\u30c6"
    Katakana["to"  ] = "\u30c8"
    Katakana["cha" ] = "\u30c1\u30e3"
    Katakana["chu" ] = "\u30c1\u30e5"
    Katakana["cho" ] = "\u30c1\u30e7"
    Katakana["na"  ] = "\u30ca"
    Katakana["ni"  ] = "\u30cb"
    Katakana["nu"  ] = "\u30cc"
    Katakana["ne"  ] = "\u30cd"
    Katakana["no"  ] = "\u30ce"
    Katakana["nya" ] = "\u30cb\u30e3"
    Katakana["nyu" ] = "\u30cb\u30e5"
    Katakana["nyo" ] = "\u30cb\u30e7"
    Katakana["ha"  ] = "\u30cf"
    Katakana["hi"  ] = "\u30d2"
    Katakana["fu"  ] = "\u30d5"
    Katakana["he"  ] = "\u30d8"
    Katakana["ho"  ] = "\u30db"
    Katakana["hya" ] = "\u30d2\u30e3"
    Katakana["hyu" ] = "\u30d2\u30e5"
    Katakana["hyo" ] = "\u30d2\u30e7"
    Katakana["ma"  ] = "\u30de"
    Katakana["mi"  ] = "\u30df"
    Katakana["mu"  ] = "\u30e0"
    Katakana["me"  ] = "\u30e1"
    Katakana["mo"  ] = "\u30e2"
    Katakana["mya" ] = "\u30df\u30e3"
    Katakana["myu" ] = "\u30df\u30e5"
    Katakana["myo" ] = "\u30df\u30e7"
    Katakana["ya"  ] = "\u30e4"
    Katakana["yu"  ] = "\u30e6"
    Katakana["yo"  ] = "\u30e8"
    Katakana["ra"  ] = "\u30e9"
    Katakana["ri"  ] = "\u30ea"
    Katakana["ru"  ] = "\u30eb"
    Katakana["re"  ] = "\u30ec"
    Katakana["ro"  ] = "\u30ed"
    Katakana["rya" ] = "\u30ea\u30e3"
    Katakana["ryu" ] = "\u30ea\u30e5"
    Katakana["ryo" ] = "\u30ea\u30e7"
    Katakana["wa"  ] = "\u30ef"
    Katakana["wi"  ] = "\u30f0"
    Katakana["we"  ] = "\u30f1"
    Katakana["wo"  ] = "\u30f2"
    Katakana["nn"  ] = "\u30f3"
    Katakana["ga"  ] = "\u30ac"
    Katakana["gi"  ] = "\u30ae"
    Katakana["gu"  ] = "\u30b0"
    Katakana["ge"  ] = "\u30b2"
    Katakana["go"  ] = "\u30b4"
    Katakana["gya" ] = "\u30ae\u30e3"
    Katakana["gyu" ] = "\u30ae\u30e5"
    Katakana["gyo" ] = "\u30ae\u30e7"
    Katakana["za"  ] = "\u30b6"
    #Katakana["dzi" ] = u"\u30b8" # ---------------------------
    #Katakana["dzu" ] = u"\u30ba" # ---------------------------
    Katakana["dzi" ] = "\u30c2" # ---------------------------
    Katakana["dzu" ] = "\u30c5" # ---------------------------
    Katakana["ze"  ] = "\u30bc"
    Katakana["zo"  ] = "\u30be"
    Katakana["ja"  ] = "\u30b8\u30e3"
    Katakana["ju"  ] = "\u30b8\u30e5"
    Katakana["jo"  ] = "\u30b8\u30e7"
    Katakana["da"  ] = "\u30c0"
    Katakana["ji"  ] = "\u30b8" # ---------------------------
    Katakana["zu"  ] = "\u30ba" # ---------------------------
    Katakana["de"  ] = "\u30c7"
    Katakana["do"  ] = "\u30c9"
    Katakana["ba"  ] = "\u30d0"
    Katakana["bi"  ] = "\u30d3"
    Katakana["bu"  ] = "\u30d6"
    Katakana["be"  ] = "\u30d9"
    Katakana["bo"  ] = "\u30dc"
    Katakana["bya" ] = "\u30d3\u30e3"
    Katakana["byu" ] = "\u30d3\u30e5"
    Katakana["byo" ] = "\u30d3\u30e7"
    Katakana["pa"  ] = "\u30d1"
    Katakana["pi"  ] = "\u30d4"
    Katakana["pu"  ] = "\u30d7"
    Katakana["pe"  ] = "\u30da"
    Katakana["po"  ] = "\u30dd"
    Katakana["pya" ] = "\u30d4\u30e3"
    Katakana["pyu" ] = "\u30d4\u30e5"
    Katakana["pyo" ] = "\u30d4\u30e7"
    Katakana["ye"  ] = "\u30a4\u30a7"
    #Katakana["wi"  ] = u"\u30a6\u30a3"
    #Katakana["we"  ] = u"\u30a6\u30a7"
    #Katakana["wo"  ] = u"\u30a6\u30a9"
    Katakana["va"  ] = "\u30F7"
    #Katakana["va"  ] = u"\u30f4\u30a1"
    Katakana["vi"  ] = "\u30F8"
    #Katakana["vi"  ] = u"\u30f4\u30a3"
    Katakana["vu"  ] = "\u30F4"
    #Katakana["vu"  ] = u"\u30f4"
    Katakana["ve"  ] = "\u30f4\u30a7"
    #Katakana["ve"  ] = u"\u30F9"
    Katakana["vo"  ] = "\u30FA"
    #Katakana["vo"  ] = u"\u30f4\u30a9"
    Katakana["she" ] = "\u30b7\u30a7"
    Katakana["je"  ] = "\u30b8\u30a7"
    Katakana["che" ] = "\u30c1\u30a7"
    Katakana["ti"  ] = "\u30c6\u30a3"
    Katakana["tu"  ] = "\u30c8\u30a5"
    Katakana["tyu" ] = "\u30c6\u30e5"
    Katakana["di"  ] = "\u30c7\u30a3"
    Katakana["du"  ] = "\u30c9\u30a5"
    Katakana["dyu" ] = "\u30c7\u30e5"
    Katakana["tsa" ] = "\u30c4\u30a1"
    Katakana["tsi" ] = "\u30c4\u30a3"
    Katakana["tse" ] = "\u30c4\u30a7"
    Katakana["tso" ] = "\u30c4\u30a9"
    Katakana["fa"  ] = "\u30d5\u30a1"
    Katakana["fi"  ] = "\u30d5\u30a3"
    Katakana["fe"  ] = "\u30d5\u30a7"
    Katakana["fo"  ] = "\u30d5\u30a9"
    Katakana["-"   ] = "\u30fc"
    Katakana["."   ] = "\u30FB"
    Katakana["*"   ] = "\u309C"
    Katakana["\\"   ] = "\u30FD"
    Katakana["|"   ] = "\u30FE"
    Katakana["dd"  ] = "\u30c3"  # Sokuon
    Katakana["pp"  ] = "\u30fd"

    #Katakana["dza" ] = u"\u30c2\u30e3" # what are these from?
    #Katakana["dzu" ] = u"\u30c2\u30e5"
    #Katakana["dzo" ] = u"\u30c2\u30e7"
    return (Hiragana,Katakana)

(SymTr.Hiragana,SymTr.Katakana) = init_KanaTables()
SymTr.HiraganaUpper = { k.upper():v for k,v in SymTr.Hiragana.items() }
SymTr.HiraganaUpper['dd'] = SymTr.HiraganaUpper['DD']
del SymTr.HiraganaUpper['DD']
SymTr.ReverseKatakana = { v:k for k,v in SymTr.Katakana.items() }
SymTr.ReverseHiragana = { v:k for k,v in SymTr.Hiragana.items() }
SymTr.ReverseHiraganaUpper = { v:k for k,v in SymTr.HiraganaUpper.items() }
