
"""

common operations for converting between kivy types and
core song/library types.


"""
from yue.custom_widgets.view import TreeElem
from yue.custom_widgets.playlist import PlayListElem
from yue.custom_widgets.querybuilder import QueryKind
from yue.custom_widgets.tristate import TriState

from yue.core.search import PartialStringSearchRule, \
                       InvertedPartialStringSearchRule, \
                       ExactSearchRule, \
                       InvertedExactSearchRule, \
                       LessThanSearchRule, \
                       LessThanEqualSearchRule, \
                       GreaterThanSearchRule, \
                       GreaterThanEqualSearchRule, \
                       RangeSearchRule, \
                       NotRangeSearchRule, \
                       AndSearchRule, \
                       OrSearchRule, \
                       allTextRule

_kindToRule = {
    QueryKind.LIKE    : PartialStringSearchRule,
    QueryKind.NOTLIKE : InvertedPartialStringSearchRule,
    QueryKind.EQ : ExactSearchRule,
    QueryKind.NE : InvertedExactSearchRule,
    QueryKind.LT : LessThanSearchRule,
    QueryKind.LE : LessThanEqualSearchRule,
    QueryKind.GT : GreaterThanSearchRule,
    QueryKind.GE : GreaterThanEqualSearchRule,
    QueryKind.BETWEEN : RangeSearchRule,
    QueryKind.NOTBETWEEN : NotRangeSearchRule,
}

class TrackTreeElem(TreeElem):
    """ Tree Element with unique id reference to an item in a database """
    def __init__(self,uid,text):
        super(TrackTreeElem, self).__init__(text)
        self.uid = uid

def libraryToTree(lib):
    return libraryToTreeFromIterable( lib.iter() )

def libraryToTreeFromIterable( data ):
    """ data as an iterable, yielding dictionaries representing songs """
    artists = {}
    for song in data:

        if song['artist'] not in artists:
            artists[ song['artist'] ] = TreeElem(song['artist'])

        album = None
        for child in artists[ song['artist'] ]:
            if child.text == song['album']:
                album = child
                break;
        else:
            album = artists[ song['artist'] ].addChild(TreeElem(song['album']))

        album.addChild(TrackTreeElem(song['uid'],song['title']))

    out = list(artists.values())
    out.sort(key=lambda e : e.text)
    return out

def PlayListToViewList(lib,playlist):
    out = []
    for uid in playlist:
        song = lib.songFromId(uid)
        out.append(PlayListElem( uid, song ))
    return out

def PlayListFromTree(lib, tree ):

    out = []
    for art in tree:
        if art.check_state is not TriState.unchecked:
            for alb in art.children:
                if alb.check_state is not TriState.unchecked:
                    for ttl in alb.children:
                        if ttl.check_state is TriState.checked:
                            out.append(ttl.uid)
    return out

def queryParamToRule( library, query ):
    rules = []
    for c,a,v in query:

        if c == 'all-text':
            rule = createAllTextRule(a, *v)
        else:
            rule_type = _kindToRule[a]
            rule = rule_type(c,*v)
        rules.append( rule )

    if len(rules) == 0:
        # execute blank search
        return None

    return AndSearchRule(rules)



def kindToSearchRule( k ):
    return _kindToRule[ k ]


def createAllTextRule( action, string ):

    meta = OrSearchRule
    if action in (QueryKind.NOTLIKE, QueryKind.NE):
        meta = AndSearchRule
    rule = _kindToRule[ action ]

    return allTextRule( meta, rule, string)
