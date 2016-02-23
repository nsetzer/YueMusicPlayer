from .song import Song

try:
    from functools import lru_cache
except:
    def lru_cache(maxsize=128):
        def lru_cache_decorator(func):
            cache = dict()
            def lru_cache_wrapper(*args):
                if args in cache:
                    return cache[args]
                result = func(*args);
                cache[args] = result
                while len(cache)>maxsize:
                    del cache[cache.keys()[0]]
                return result
            return lru_cache_wrapper
        return lru_cache_decorator

import calendar
from datetime import datetime, timedelta

import sys
isPython3 = sys.version_info[0]==3
if isPython3:
    unicode = str

class SearchRule(object):
    """docstring for SearchRule"""
    def __init__(self):
        super(SearchRule, self).__init__()

    def check(self,song):
        raise NotImplementedError()

    def __eq__(self,othr):
        return repr(self) == repr(othr)

class BlankSearchRule(SearchRule):
    """a rule that match all values"""

    def check(self,song):
        return True

    def sql(self):
        return "", tuple()

    def __repr__(self):
        return "<all>"%(self.value, self.column)

class ColumnSearchRule(SearchRule):
    """docstring for SearchRule"""
    def __init__(self, column, value):
        super(SearchRule, self).__init__()
        self.column = column
        self.value = value

class PartialStringSearchRule(ColumnSearchRule):
    """docstring for SearchRule"""
    def check(self,song):
        return self.value in song[self.column]

    def sql(self):
        return "%s LIKE ?"%(self.column,), ("%%%s%%"%self.value,)

    def __repr__(self):
        return "<%s in `%s`>"%(self.value, self.column)

class InvertedPartialStringSearchRule(ColumnSearchRule):
    """docstring for SearchRule"""
    def check(self,song):
        return self.value not in song[self.column]

    def sql(self):
        return "%s NOT LIKE ?"%(self.column,), ("%%%s%%"%self.value,)

    def __repr__(self):
        return "<%s not in `%s`>"%(self.value, self.column)

class ExactSearchRule(ColumnSearchRule):
    """docstring for SearchRule"""
    def check(self,song):
        return self.value == song[self.column]

    def __repr__(self):
        return "<%s equals `%s`>"%(self.value, self.column)

    def sql(self):
        return "%s = ?"%(self.column,), (self.value,)

class InvertedExactSearchRule(ColumnSearchRule):
    """docstring for SearchRule"""
    def check(self,song):
        return self.value != song[self.column]

    def __repr__(self):
        return "<%s not equals `%s`>"%(self.value, self.column)

    def sql(self):
        return "%s != ?"%(self.column,), (self.value,)

class LessThanSearchRule(ColumnSearchRule):
    """docstring for SearchRule"""
    def check(self,song):
        return song[self.column] < self.value

    def sql(self):
        return "%s < ?"%(self.column,), (self.value,)

    def __repr__(self):
        return "<%s less than `%s`>"%(self.value, self.column)

class LessThanEqualSearchRule(ColumnSearchRule):
    """docstring for SearchRule"""
    def check(self,song):
        return song[self.column] <= self.value

    def sql(self):
        return "%s <= ?"%(self.column,), (self.value,)

    def __repr__(self):
        return "<%s less than or equal `%s`>"%(self.value, self.column)

class GreaterThanSearchRule(ColumnSearchRule):
    """docstring for SearchRule"""
    def check(self,song):
        return song[self.column] > self.value

    def sql(self):
        return "%s > ?"%(self.column,), (self.value,)

    def __repr__(self):
        return "<%s greater than `%s`>"%(self.value, self.column)

class GreaterThanEqualSearchRule(ColumnSearchRule):
    """docstring for SearchRule"""
    def check(self,song):
        return song[self.column] >= self.value
    def sql(self):
        return "%s >= ?"%(self.column,), (self.value,)

    def __repr__(self):
        return "<%s greater than or equal `%s`>"%(self.value, self.column)

class RangeSearchRule(SearchRule):
    """docstring for SearchRule"""
    def __init__(self, column, value_low, value_high):
        super(RangeSearchRule, self).__init__()
        self.column = column
        self.value_low = value_low
        self.value_high = value_high

    def check(self,song):
        return self.value_low <= song[self.column] <= self.value_high

    def sql(self):
        return "%s BETWEEN ? AND ?"%(self.column,), (self.value_low,self.value_high)

    def __repr__(self):
        return "<`%s` in range (%s,%s)>"%(self.column,self.value_low,self.value_high)

class NotRangeSearchRule(RangeSearchRule):
    """docstring for SearchRule"""

    def check(self,song):
        return song[self.column] < self.value_low or self.value_high < song[self.column]

    def sql(self):
        return "%s NOT BETWEEN ? AND ?"%(self.column,), (self.value_low,self.value_high)

    def __repr__(self):
        return "<`%s` not in range (%s,%s)>"%(self.column,self.value_low,self.value_high)

class MetaSearchRule(SearchRule):
    """group one or more search rules"""
    def __init__(self, rules):
        super(MetaSearchRule, self).__init__()
        self.rules = rules

class AndSearchRule(MetaSearchRule):
    """MetaSearchRule which checks that all rules return true"""
    def check(self, song):
        for rule in self.rules:
            if not rule.check(song):
                break
        else:
            return True
        return False

    def sql(self):
        sql  = []
        vals = []
        sqlstr= ""
        for rule in self.rules:
            x = rule.sql()
            sql.append(x[0])
            vals.extend(x[1])
        if sql:
            sqlstr = '(' + ' AND '.join(sql) + ')'
        return sqlstr,vals

    def __repr__(self):
        return "<" + ' && '.join([ repr(r) for r in self.rules]) + ">"

class OrSearchRule(MetaSearchRule):
    """MetaSearchRule which checks that at least one rule returns true"""
    def check(self, song):
        for rule in self.rules:
            if rule.check(song):
                return True
        return False

    def sql(self):
        sql  = []
        vals = []
        sqlstr= ""
        for rule in self.rules:
            x = rule.sql()
            sql.append(x[0])
            vals.extend(x[1])
        if sql:
            sqlstr = '(' + ' OR '.join(sql) + ')'
        return sqlstr,vals

    def __repr__(self):
        return "<" + ' || '.join([ repr(r) for r in self.rules]) + ">"

def naive_search( sqldb, rule ):
    """ iterate through the database and yield songs which match a rule """
    for song in sqldb.iter():
        if rule.check(song):
            yield song

import time

def sql_search( db, rule, case_insensitive=True, orderby=None, reverse = False):
    """ convert a rule to a sql query and yield matching songs

    orderby must be given for reverse to have any meaning

    add support for 'LIMIT N'
    orderby can be "RANDOM()"
    ORDERBY RANDOM() LIMIT N
    """
    sql,vals = rule.sql()

    query = "SELECT * FROM %s"%db.name

    sql_valid = len(sql.strip())>0
    if sql_valid:
        query += " WHERE %s"%sql
        if case_insensitive:
            query += " COLLATE NOCASE"


    direction = " ASC"
    if reverse:
        direction = " DESC"
    if case_insensitive:
        direction = " COLLATE NOCASE" + direction

    if orderby is not None:

        if not isinstance(orderby,(tuple,list)):
            orderby = [ orderby, ]

        orderby = [ x+direction for x in orderby]
        query += " ORDER BY " + ", ".join(orderby)

    try:
        s = time.clock()
        result = list(db.query(query, *vals))
        e = time.clock()
        print(e-s,sql)
        return result
    except:
        print("`%s`"%sql)
        print(query)
        print(vals)
        raise

def allTextRule( join_rule, string_rule, string ):
    """
    returns a rule that will return true if
    any text field matches the given string

    join_rule: as OrSearchRule or AndSearchRule
    string_rule as : PartialStringSearchRule, etc

    """
    return join_rule([ string_rule(col,string) for col in Song.textFields() ])

class ParseError(Exception):
    pass

class TokenizeError(ParseError):
    pass

class RHSError(ParseError):
    def __init__(self, tok, value=""):
        msg = "Invalid Expression on RHS of `%s`"%tok
        if value:
            msg += " : %s"%value
        super(RHSError, self).__init__( msg )

class LHSError(ParseError):
    def __init__(self, tok, value=""):
        msg = "Invalid Expression on LHS of `%s`"%tok
        if value:
            msg += " : %s"%value
        super(LHSError, self).__init__( msg )

def tokenizeString( input ):
    """
    simple parser for nested queries

    'column = this'
    'column = this || column = that'
    '(column = this || column=that) && column > 0'

    supports old style queries:
    defaults to partial string matching, an operator
    changes the current operator used, negate flips the
    current operator. multiple tokens can be specified in a row
    '.col x y z'       is equal to 'col=x col=y col=z'
    '.col = x < y ! z' is equal to 'col=x col<y col>z'


    """
    idx = 0;

    output = []
    special = '~!=<>|&'
    # cause 'special' symbols to join together, separately
    # from all other character classes.
    join_special = False
    stack = [ output ]
    start = 0;
    quoted = False

    def append():
        text = input[start:idx].strip()
        if text:
            stack[-1].append(text)

    while idx < len( input ) and len(stack)>0:
        c = input[idx]

        if c == '\\':
            # skip the next character, by erasing the
            # current character from the input
            input = input[:idx] + input[idx+1:]
        elif c == '"' and not quoted:
            # quote detected, ignore all characters until
            # the next matching quote is found
            quoted = True
            append()
            start = idx+1
        elif c == '"' and quoted:
            append()
            start = idx+1
            quoted = False
        elif not quoted:
            s = c in special
            if c == '(':
                # start of parenthetical grouping,
                # push a new level on the stack.
                append()
                new_level = []
                stack[-1].append( new_level )
                stack.append( new_level )
                start = idx+1
            elif c == ')':
                append()
                start = idx+1
                stack.pop()
            elif c == ' ':
                append()
                start = idx
            elif s and not join_special:
                append()
                start = idx
                join_special = True
            elif not s and join_special:
                append()
                start = idx
                join_special = False
        idx += 1
    if len(stack) == 0:
        raise TokenizeError("empty stack (check parenthesis)")
    if len(stack) > 1:
        raise TokenizeError("unterminated parenthesis")
    if quoted:
        raise TokenizeError("unterminated quote")
    append()

    return output

# does not require left token
operators = {
    "=" :PartialStringSearchRule,
    "~" :PartialStringSearchRule,
    "==":ExactSearchRule,
    "!=":InvertedPartialStringSearchRule,
    "!==":InvertedExactSearchRule,
}

operators_invert = {
    InvertedPartialStringSearchRule :PartialStringSearchRule,
    InvertedExactSearchRule:ExactSearchRule,
    PartialStringSearchRule:InvertedPartialStringSearchRule,
    ExactSearchRule:InvertedExactSearchRule,
}
# require left/right token
special = {
    "<"  : LessThanSearchRule,
    ">"  : GreaterThanSearchRule,
    "<=" : LessThanEqualSearchRule,
    ">=" : GreaterThanEqualSearchRule,
}

special_invert = {
    GreaterThanSearchRule      : LessThanSearchRule,
    LessThanSearchRule         : GreaterThanSearchRule,
    GreaterThanEqualSearchRule : LessThanEqualSearchRule,
    LessThanEqualSearchRule    : GreaterThanEqualSearchRule,
}

old_style_operators = operators.copy()
old_style_operators.update(special)

old_style_operators_invert = operators_invert.copy()
old_style_operators_invert.update(special_invert)

flow = {
    "&&" : AndSearchRule,
    "||" : OrSearchRule
}

negate = "!"

@lru_cache(maxsize=16)
def parserFormatDays( days ):

    now = datetime.now()
    dt1 = datetime(now.year,now.month,now.day) - timedelta( days )
    dt2 = dt1 + timedelta( 1 )
    return calendar.timegm(dt1.timetuple()), calendar.timegm(dt2.timetuple())

@lru_cache(maxsize=16)
def parserFormatDate( value ):

    sy,sm,sd = value.split('/')

    y = int(sy)
    m = int(sm)
    d = int(sd)

    if y < 100:
        y += 2000

    dt1 = datetime(y,m,d)
    dt2 = dt1 + timedelta( 1 )

    return calendar.timegm(dt1.timetuple()), calendar.timegm(dt2.timetuple())

def parserRule(colid, rule ,value):

    try:
        col = Song.column( colid );
    except KeyError:
        raise ParseError("Invalid column name `%s`"%colid)

    if col == Song.all_text:
        meta = OrSearchRule
        if rule in (InvertedPartialStringSearchRule, InvertedExactSearchRule):
            meta = AndSearchRule
        return allTextRule(meta, rule, value)
    elif col in Song.textFields():
        return rule( col, value )
    elif col in Song.dateFields(): # is number (or date, todo)
        return parserDateRule(rule, col, value)
    else:
        # numeric fields do not require any special conversion at this time
        return rule( col, value )

def parserDateRule(rule , col, value):
    """
    There are two date fields, 'last_played' and 'date_added'

    queries can be run in two modes.

    providing an integer (e.g. date < N) performs a relative search
    from the current date, in this examples songs played since N days ago.

    providing a date string will run an exact search. (e.g. date < 15/3/12)
    the string is parsed y/m/d but otherwise behaves exactly the same way.

    < : closer to present day, including the date given
    > : farther into the past, excluding the given date
    = : exactly that day, from 00:00:00 to 23:59:59
    """
    c = value.count('/')

    try:
        if c == 2:
            epochtime,epochtime2 = parserFormatDate( value )
        elif c > 0:
            raise ParseError("Invalid Date format. Expected YY/MM/DD.")
        else:
            ivalue = int( value )
            epochtime,epochtime2 = parserFormatDays( ivalue )
            #epochtime2 = parserFormatDays( ivalue - 1 )
    except ValueError:
        # failed to convert istr -> int
        raise ParseError("Expected Integer or Date, found `%s`"%value)

    # flip the context of '<' and '>'
    # for dates, '<' means closer to present day
    # date < 5 is anything in the last 5 days
    if rule in special_invert:
        rule = special_invert[rule]

    # token '=' is partial string matching, in the context of dates
    # it will return any song played exactly n days ago
    # a value of '1' is yesterday
    if rule is PartialStringSearchRule:
        return RangeSearchRule(col, epochtime, epochtime2)

    # inverted range matching
    if rule is InvertedPartialStringSearchRule:
        return NotRangeSearchRule(col, epochtime, epochtime2)

    return rule( col, epochtime )

def parseTokensOldStyle( sigil, tokens ):

    sigil = '.'

    current_col = Song.all_text
    current_opr = PartialStringSearchRule

    i=0
    while i < len(tokens):
        tok = tokens[i]

        if isinstance(tokens[i],(str,unicode)):
            if tok.startswith(sigil):
                current_col = tok[1:]
                tokens.pop(i)
                i -= 1
            elif tok == negate:
                current_opr = old_style_operators_invert[current_opr]
                tokens.pop(i)
                i -= 1
            elif tok in old_style_operators:
                current_opr = old_style_operators[tok]
                tokens.pop(i)
                i -= 1
            elif tok not in flow:
                tokens[i] = parserRule(current_col,current_opr,tok)
        i+=1

    if len(tokens) == 1:
        return tokens[0]

    return AndSearchRule( tokens )

def parseTokens( tokens ):

    sigil = '.'

    i=0
    while i < len(tokens):
        tok = tokens[i]
        hasl = i>0
        hasr = i<len(tokens)-1

        if isinstance(tok,list):
            tokens[i] = parseTokens(tok)
        elif tok.startswith(sigil):
            # old style query
            s = i
            while i < len(tokens) and \
                not isinstance(tokens[i],list) and \
                tokens[i] not in flow:
                i += 1;
            toks = tokens[:s]
            toks.append( parseTokensOldStyle( sigil, tokens[s:i] )  )
            toks += tokens[i:]
            tokens = toks
            i = s + 1
            continue
        elif tok in operators:
            if not hasr:
                raise RHSError(tok, "expected value")
            r = tokens.pop(i+1)
            if not isinstance(r,(str,unicode)):
                raise RHSError(tok, "expected string")
            # left side is optional, defaults to all text
            if not hasl:
                tokens[i] = parserRule(Song.all_text,operators[tok],r)
            else:
                i -= 1
                l = tokens.pop(i)
                if not isinstance(l,(str,unicode)):
                    raise LHSError(tok, "expected string")
                tokens[i] = parserRule(l,operators[tok],r)
        elif tok in special:
            if not hasr:
                raise RHSError(tok, "expected value")
            if not hasl:
                raise LHSError(tok, "expected value")
            r = tokens.pop(i+1)
            if not isinstance(r,(str,unicode)):
                raise RHSError(tok, "expected string")
            i-=1
            l = tokens.pop(i)
            if not isinstance(l,(str,unicode)):
                raise LHSError(tok, "expected string")
            tokens[i] = parserRule(l,special[tok],r)
        i += 1

    # collect any old style tokens, which did not use a sigil
    parseTokensOldStyle( sigil, tokens )

    i=0
    while i < len(tokens):
        tok = tokens[i]
        hasl = i>0
        hasr = i<len(tokens)-1
        if isinstance(tok, (str, unicode)):
            if tok in flow:
                if not hasr:
                    raise RHSError(tok, "expected value")
                if not hasl:
                    raise LHSError(tok, "expected value")
                r = tokens.pop(i+1)
                i-=1
                l = tokens.pop(i)
                tokens[i] = flow[tok]([l,r])
        i+=1

    if len(tokens) == 1:
        return tokens[0]
    return AndSearchRule( tokens )

def ruleFromString( string ):
    """

    convert:
        '.art foo; .abm bar'
    to:
        AndSearchRule([
            PartialStringSearchRule("artist","foo"),
            PartialStringSearchRule("album","bar"),
        ])

    allow for ';' to mean '&&' but also allow for &&, || and
    parenthetical grouping

    allow for '.' + token to map to a column name.
        e.g. '.art' and '.artist' means 'artist'

    allow for artist="foo bar" or "art="foo bar" to mean the same.

    allow for '.art foo bar' to mean :
        AndSearchRule([
            PartialStringSearchRule("artist","foo"),
            PartialStringSearchRule("artist","bar"),
        ])

    """
    if not string.strip():
        return BlankSearchRule()
    tokens = tokenizeString( string )
    return parseTokens( tokens );


