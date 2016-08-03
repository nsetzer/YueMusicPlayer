from .nlpdatesearch import NLPDateRange
from .util import lru_cache, format_delta, format_date
import re
import calendar
from datetime import datetime, timedelta
import time


import sys
isPython3 = sys.version_info[0]==3
if isPython3:
    unicode = str

# classes to tag an integer as a specific type for later formating
# any arithmetic on these types returns int

class IntDate(int):
    def __new__(cls, *args, **kwargs):
        return  super(IntDate, cls).__new__(cls, args[0])

class IntTime(int):
    def __new__(cls, *args, **kwargs):
        return  super(IntTime, cls).__new__(cls, args[0])

class SearchRule(object):
    """docstring for SearchRule"""

    def __init__(self):
        super(SearchRule, self).__init__()

    def check(self,elem):
        raise NotImplementedError()

    def __eq__(self,othr):
        return repr(self) == repr(othr)

    def sql(self):
        """ return string representation and a list of values
            the string should have question marks (?) in place
            of the values, which will be filled in when the sql
            is executed.
            each value in the returned list of values should
            correspond with 1 question mark, from left to right.

            see sqlstr()
        """
        raise NotImplementedError()

    def __repr__(self):
        return "<%s>"%self.__class__.__name__

    def fmtval(self,v):
        if isinstance(v,IntDate):
            return "\"%s\""%format_date(v)
        elif isinstance(v,IntTime):
            return "\"%s\""%format_delta(v)
        elif isinstance(v,str):
            return "\"%s\""%v
        return v;

    def sqlstr(self):
        """ like sql() but returns a single string representing the rulw"""
        s,v = self.sql()
        # at this point all values should be strings, ints or floats right?
        v = map(self.fmtval,v)
        return s.replace("?","{}").format(*v)

class BlankSearchRule(SearchRule):
    """a rule that match all values"""

    def check(self,elem):
        return True

    def sql(self):
        return "", tuple()

    def __repr__(self):
        return "<all>"

class ColumnSearchRule(SearchRule):
    """docstring for SearchRule"""
    def __init__(self, column, value):
        super(SearchRule, self).__init__()
        self.column = column
        self.value = value

@lru_cache(maxsize=128)
def rexcmp(expr):
    return re.compile(expr,re.IGNORECASE)

def regexp(expr, item):
    reg = rexcmp(expr)
    return reg.search(item) is not None

class RegExpSearchRule(ColumnSearchRule):
    """docstring for SearchRule"""
    def check(self,elem):
        return regexp(self.value,elem[self.column])

    def __repr__(self):
        return "<%s =~ \"%s\""%(self.column,self.fmtval(self.value))

    def sql(self):
        return "%s REGEXP ?"%(self.column,), (self.value,)

class PartialStringSearchRule(ColumnSearchRule):
    """docstring for SearchRule"""
    def check(self,elem):
        return self.value in elem[self.column]

    def __repr__(self):
        return "<%s in `%s`>"%(self.fmtval(self.value), self.column)

    def sql(self):
        return "%s LIKE ?"%(self.column,), ("%%%s%%"%self.value,)

class InvertedPartialStringSearchRule(ColumnSearchRule):
    """docstring for SearchRule"""
    def check(self,elem):
        return self.value not in elem[self.column]

    def __repr__(self):
        return "<%s not in `%s`>"%(self.fmtval(self.value), self.column)

    def sql(self):
        return "%s NOT LIKE ?"%(self.column,), ("%%%s%%"%self.value,)

class ExactSearchRule(ColumnSearchRule):
    """docstring for SearchRule"""
    def check(self,elem):
        return self.value == elem[self.column]

    def __repr__(self):
        return "<%s == %s>"%(self.column, self.fmtval(self.value))

    def sql(self):
        return "%s = ?"%(self.column,), (self.value,)

class InvertedExactSearchRule(ColumnSearchRule):
    """docstring for SearchRule"""
    def check(self,elem):
        return self.value != elem[self.column]

    def __repr__(self):
        return "<%s != %s>"%(self.column, self.fmtval(self.value))

    def sql(self):
        return "%s != ?"%(self.column,), (self.value,)

class LessThanSearchRule(ColumnSearchRule):
    """docstring for SearchRule"""
    def check(self,elem):
        return elem[self.column] < self.value

    def __repr__(self):
        return "<%s < %s>"%(self.column, self.fmtval(self.value))

    def sql(self):
        return "%s < ?"%(self.column,), (self.value,)

class LessThanEqualSearchRule(ColumnSearchRule):
    """docstring for SearchRule"""
    def check(self,elem):
        return elem[self.column] <= self.value

    def __repr__(self):
        return "<%s <= %s>"%(self.column, self.fmtval(self.value))

    def sql(self):
        return "%s <= ?"%(self.column,), (self.value,)

class GreaterThanSearchRule(ColumnSearchRule):
    """docstring for SearchRule"""
    def check(self,elem):
        return elem[self.column] > self.value

    def __repr__(self):
        return "<%s > %s>"%(self.column, self.fmtval(self.value))

    def sql(self):
        return "%s > ?"%(self.column,), (self.value,)

class GreaterThanEqualSearchRule(ColumnSearchRule):
    """docstring for SearchRule"""
    def check(self,elem):
        return elem[self.column] >= self.value

    def __repr__(self):
        return "<%s >= %s>"%(self.column, self.fmtval(self.value))

    def sql(self):
        return "%s >= ?"%(self.column,), (self.value,)

class RangeSearchRule(SearchRule):
    """docstring for SearchRule"""
    def __init__(self, column, value_low, value_high):
        super(RangeSearchRule, self).__init__()
        self.column = column
        self.value_low = value_low
        self.value_high = value_high

    def check(self,elem):
        return self.value_low <= elem[self.column] <= self.value_high

    def __repr__(self):
        return "<`%s` in range (%s,%s)>"%(self.column,self.fmtval(self.value_low),self.fmtval(self.value_hight))

    def sql(self):
        return "%s BETWEEN ? AND ?"%(self.column,), (self.value_low,self.value_high)

class NotRangeSearchRule(RangeSearchRule):
    """docstring for SearchRule"""

    def check(self,elem):
        return elem[self.column] < self.value_low or self.value_high < elem[self.column]

    def __repr__(self):
        return "<`%s` not in range (%s,%s)>"%(self.column,self.fmtval(self.value_low),self.fmtval(self.value_hight))

    def sql(self):
        return "%s NOT BETWEEN ? AND ?"%(self.column,), (self.value_low,self.value_high)

class MetaSearchRule(SearchRule):
    """group one or more search rules"""
    def __init__(self, rules):
        super(MetaSearchRule, self).__init__()
        self.rules = rules

class AndSearchRule(MetaSearchRule):
    """MetaSearchRule which checks that all rules return true"""
    def check(self, elem):
        for rule in self.rules:
            if not rule.check(elem):
                break
        else:
            return True
        return False

    def __repr__(self):
        return "<" + ' && '.join(map(repr,self.rules)) + ">"

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

class OrSearchRule(MetaSearchRule):
    """MetaSearchRule which checks that at least one rule returns true"""
    def check(self, elem):
        for rule in self.rules:
            if rule.check(elem):
                return True
        return False

    def __repr__(self):
        return "<" + ' || '.join(map(repr,self.rules))  + ">"

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

class NotSearchRule(MetaSearchRule):
    """MetaSearchRule which checks that inverts result from rule"""
    def check(self, elem):
        assert len(self.rules)==1
        assert self.rules[0] is not BlankSearchRule
        if self.rules[0].check(elem):
            return False
        return True

    def __repr__(self):
        assert len(self.rules)==1
        assert self.rules[0] is not BlankSearchRule
        return "<!" + repr(self.rules[0]) + ">"

    def sql(self):
        assert len(self.rules)==1
        assert self.rules[0] is not BlankSearchRule
        sql,vals = self.rules[0].sql()
        sql = '( NOT ' + sql + ')'
        return sql,vals

def naive_search( sqldb, rule ):
    """ iterate through the database and yield elems which match a rule """
    # this does not support, case sensitivity, order, reverse or limit
    # it exists only to show that the basic rule concept
    # maps in an expected way between sql and python.
    for elem in sqldb.iter():
        if rule.check(elem):
            yield elem

def sqlFromRule(rule, db_name, case_insensitive, orderby, reverse, limit):

    sql,vals = rule.sql()

    query = "SELECT * FROM %s"%db_name

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
        # orderby can be:
        # "random"
        #  Song.column
        #  (Song.column, Song.column)
        #  ( (Song.column, dir) , (Song.column, dir) )
        if not isinstance(orderby,(tuple,list)):
            orderby = [ orderby, ]

        if isinstance(orderby[0],str) and orderby[0].lower()=="random":
            query += " ORDER BY RANDOM()"
        else:
            query += " ORDER BY "

            x=orderby[0]
            if isinstance(x,(tuple,list)):
                query += x[0] # orderby field
                if case_insensitive:
                    query += " COLLATE NOCASE "
                query += x[1] # orderby direction
            else:
                query += x + direction

            for x in orderby[1:]:
                if isinstance(x,(tuple,list)):
                    query += ", " + x[0] # orderby field
                    if case_insensitive:
                        query += " COLLATE NOCASE "
                    query += x[1] # orderby direction
                else:
                    query += ", " + x + direction
            #orderby = [ x+direction for x in orderby]
            #query += " ORDER BY " + ", ".join(orderby)

    if limit is not None:
        query += " LIMIT %d"%limit

    return query, vals

def sql_search( db, rule, case_insensitive=True, orderby=None, reverse = False, limit=None, echo=False):
    """ convert a rule to a sql query and yield matching elems

    orderby must be given for reverse to have any meaning

    """

    query,vals = sqlFromRule(rule,db.name,case_insensitive, orderby, reverse, limit)

    if echo:
        print(query)

    try:
        s = time.clock()
        result = list(db.query(query, *vals))
        e = time.clock()
        if echo:
            print(e-s,sql)
        return result
    except:
        print(query)
        print(vals)
        raise

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

class SearchGrammar(object):
    """SearchGrammar is a generic class for building a db search engine

        This defines a query syntax for querying records by text, date, or time
        fields.

        new-style queries use boolean logic and a `column = value` syntax
            for example, "artist=Aldious" can turn into a sql query for
            searching the artist column for the string Aldious

            These types of queries can be grouped using parenthesis and
            operators && and || can be used to group them in powerful ways

        old-style queries are used for user friendly text searching.
            and text that does not fit into the rigid new-style framework
            is interpretted as an old style query.

            Just typing a string, e.g. "Aldious" will search ALL text fields
            for the given string. multiple strings can be typed in a row,
            separated by white space and will automatically be ORed together.
            so called 'Implicit Or', or you can use an explicit && .
            if a word begins with the sigil, it will be used to denote a
            column to search for, which is applied to each word after
            the sigil word. e.g. ".artist Aldious" is the same as the new-style
            "artist=Aldious". and "Blind Melon" is the same as the new-style
            "Blind || Melon"

            old style supports negate and modifiers, for example
                ".date < 5 > 3" is equivalent to "date < 5 && date > 3"
                ".date ! < 5" is equivalent to "date >= 6"

        Text Searches

            todo, use quotes, etc
        Date Searches

            todo date modifiers, NLP, etc

        Time Searches

            todo, in seconds, minutes or hours, x:y:z, etc


        TODO: add support for negate in new-style queries.
    """
    def __init__(self):
        super(SearchGrammar, self).__init__()

        # set these to names of columns of specific data types
        self.text_fields = set();
        self.date_fields = set(); # column represents a date in seconds since jan 1st 1970
        self.time_fields = set(); # column represents a duration, in seconds

        self.all_text = 'text'
        # sigil is used to define the oldstyle syntax marker
        self.sigil = '.'

        # tokens control how the grammar is parsed.
        self.tok_special = '~!=<>|&'
        self.tok_negate = "!"
        self.tok_nest_begin = '('
        self.tok_nest_end = ')'
        self.tok_whitespace = " "
        self.tok_quote = "\""
        self.tok_escape = "\\"

        self.autoset_datetime = True
        self.datetime_now = datetime.now()

        self.compile_operators();

    def compile_operators(self):

        # does not require left token
        self.operators = {
            "=" :PartialStringSearchRule,
            "~" :PartialStringSearchRule,
            "==":ExactSearchRule,
            "=~":RegExpSearchRule,
            "!=":InvertedPartialStringSearchRule,
            "!==":InvertedExactSearchRule,
        }

        self.operators_invert = {
            InvertedPartialStringSearchRule :PartialStringSearchRule,
            InvertedExactSearchRule:ExactSearchRule,
            PartialStringSearchRule:InvertedPartialStringSearchRule,
            ExactSearchRule:InvertedExactSearchRule,
        }

        # require left/right token
        self.special = {
            "<"  : LessThanSearchRule,
            ">"  : GreaterThanSearchRule,
            "<=" : LessThanEqualSearchRule,
            ">=" : GreaterThanEqualSearchRule,
        }

        self.special_invert = {
            GreaterThanSearchRule      : LessThanSearchRule,
            LessThanSearchRule         : GreaterThanSearchRule,
            GreaterThanEqualSearchRule : LessThanEqualSearchRule,
            LessThanEqualSearchRule    : GreaterThanEqualSearchRule,
        }

        # meta optins can be used to control the query results
        # by default, limit could be used to limit the number of results
        self.meta_columns = set(["limit","debug"])
        self.meta_options = dict()

        self.old_style_operators = self.operators.copy()
        self.old_style_operators.update(self.special)

        self.old_style_operators_invert = self.operators_invert.copy()
        self.old_style_operators_invert.update(self.special_invert)

        self.operators_flow = {
            "&&" : AndSearchRule,
            "||" : OrSearchRule
        }

    def translateColumn(self,colid):
        """ convert a column name, as input by the user to the internal name

            overload this function to provide shortcuts for different columns

            raise ParseError if colid is invalid
        """
        if colid not in self.text_fields and \
           colid not in self.date_fields and \
           colid not in self.time_fields and \
           colid != self.all_text:
            raise ParseError("Invalid column name `%s`"%colid)
        return colid

    def ruleFromString( self, string ):
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
        if self.autoset_datetime:
            self.datetime_now =  datetime.now()

        # reset meta options
        self.meta_options = dict()

        if not string.strip():
            return BlankSearchRule()
        tokens = self.tokenizeString( string )
        rule = self.parseTokens( tokens );
        if self.getMetaValue("debug") == 1:
            sys.stdout.write("%r\n"%(rule))
        elif self.getMetaValue("debug") == 2:
            #s,v = rule.sql()
            #v = [ ("\"%s\""%s) if isinstance(s,str) else s for s in v]
            #s = s.replace("?","{}").format(*v)
            sys.stdout.write("%s\n"%(rule.sqlstr()))
        return rule;

    def tokenizeString(self, input ):
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

            if c == self.tok_escape:
                # skip the next character, by erasing the
                # current character from the input
                # to allow escape characters in strings
                # first check that we are quoted here
                # then look at the next character to decide
                # mode (e.g. \\ -> \, \a -> bell \x00 -> 0x00, etc)

                input = input[:idx] + input[idx+1:]
            elif c == self.tok_quote and not quoted:
                # quote detected, ignore all characters until
                # the next matching quote is found
                quoted = True
                append()
                start = idx+1
            elif c == self.tok_quote and quoted:
                append()
                start = idx+1
                quoted = False
            elif not quoted:
                s = c in self.tok_special
                if c == self.tok_nest_begin:
                    # start of parenthetical grouping,
                    # push a new level on the stack.
                    append()
                    new_level = []
                    stack[-1].append( new_level )
                    stack.append( new_level )
                    start = idx+1
                elif c == self.tok_nest_end:
                    append()
                    start = idx+1
                    stack.pop()
                elif c in self.tok_whitespace:
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

    def parseTokens( self, tokens, top=True ):

        i=0
        while i < len(tokens):
            tok = tokens[i]
            hasl = i>0
            hasr = i<len(tokens)-1

            if isinstance(tok,list):
                tokens[i] = self.parseTokens(tok, top=False)
                if isinstance(tokens[i],BlankSearchRule):
                    tokens.pop(i)
                    continue
            elif tok.startswith(self.sigil):
                # old style query
                s = i
                while i < len(tokens) and \
                    not isinstance(tokens[i],list) and \
                    tokens[i] not in self.operators_flow:
                    i += 1;
                toks = tokens[:s]
                toks.append( self.parseTokensOldStyle( tokens[s:i] )  )
                toks += tokens[i:]
                tokens = toks
                i = s + 1
                continue
            elif tok in self.operators:
                if not hasr:
                    raise RHSError(tok, "expected value [V01]")
                r = tokens.pop(i+1)
                if not isinstance(r,(str,unicode)):
                    raise RHSError(tok, "expected string [S01]")
                if r in self.operators_flow:
                    raise RHSError(tok, "unexpected operator [U01]")
                # left side is optional, defaults to all text
                if not hasl or \
                    (not isinstance(tokens[i-1],(str,unicode)) or tokens[i-1] in self.operators_flow):
                    # no left side, or left side has been processed and is not a column label
                    tokens[i] = self.parserRule(self.all_text,self.operators[tok],r)
                else:
                    # left side token exists
                    i-=1
                    l = tokens.pop(i)
                    if l in self.meta_columns:
                        # and remove the column name
                        tokens.pop(i) # remove token
                        self.parserMeta(l,tok,r,top)
                        continue
                    else:
                        tokens[i] = self.parserRule(l,self.operators[tok],r)
            elif tok in self.special:
                if not hasr:
                    raise RHSError(tok, "expected value [V02]")
                if not hasl:
                    raise LHSError(tok, "expected value [V03]")
                r = tokens.pop(i+1)
                if not isinstance(r,(str,unicode)):
                    raise RHSError(tok, "expected string [S02]")
                if r in self.operators_flow:
                    raise RHSError(tok, "unexpected operator [U02]")
                i-=1
                l = tokens.pop(i)
                if not isinstance(l,(str,unicode)):
                    raise LHSError(tok, "expected string [S03]")
                if l in self.meta_columns:
                    # and remove the column name
                    tokens.pop(i) # remove token
                    self.parserMeta(l,tok,r,top)
                    continue
                tokens[i] = self.parserRule(l,self.special[tok],r)
            i += 1

        # collect any old style tokens, which did not use a sigil
        self.parseTokensOldStyle( tokens )

        i=0
        while i < len(tokens):
            tok = tokens[i]
            hasl = i>0
            hasr = i<len(tokens)-1
            if isinstance(tok, (str, unicode)):
                if tok ==  self.tok_negate:
                    if not hasr:
                        raise RHSError(tok, "expected value [V04]")
                    r = tokens.pop(i+1)
                    tokens[i] = NotSearchRule([r,]);
                elif tok in self.operators_flow:
                    if not hasr:
                        raise RHSError(tok, "expected value [V05]")
                    if not hasl:
                        raise LHSError(tok, "expected value [V06]")
                    r = tokens.pop(i+1)
                    if isinstance(r, (str, unicode)) and r in self.operators_flow:
                        raise RHSError(tok, "unexpected operator [U03]")
                    i-=1
                    l = tokens.pop(i)
                    tokens[i] = self.operators_flow[tok]([l,r])
            i+=1

        if len(tokens) == 0:
            return BlankSearchRule()

        elif len(tokens) == 1:
            if isinstance(tokens[0],(str,unicode)):
                raise ParseError("unexpected error")
            return tokens[0]

        return AndSearchRule( tokens )

    def parseTokensOldStyle( self, tokens ):

        current_col = self.all_text
        current_opr = PartialStringSearchRule

        allow_negate = False;
        i=0
        while i < len(tokens):
            tok = tokens[i]

            if isinstance(tokens[i],(str,unicode)):
                if tok.startswith(self.sigil):
                    current_col = tok[1:]
                    tokens.pop(i)
                    continue
                #    allow_negate = True;
                #elif tok == self.tok_negate and allow_negate:
                #    current_opr = self.old_style_operators_invert[current_opr]
                #    tokens.pop(i)
                #    i -= 1
                elif tok in self.old_style_operators:
                    current_opr = self.old_style_operators[tok]
                    tokens.pop(i)
                    continue
                elif tok not in self.operators_flow and tok != self.tok_negate:
                    tokens[i] = self.parserRule(current_col,current_opr,tok)
            i+=1

        if len(tokens) == 1:
            return tokens[0]

        return AndSearchRule( tokens )

    def parserDateDelta(self,y,m,d,dy,dm):
        """ semantically simple and more obvious behavior than _m and _y variants
            and it works for negative deltas!
        """
        y = y - (m - dm)//12 - dy
        m = (m - dm)%12

        # modulo fix the day by rolling up, feb 29 to march 1
        # or july 32 to aug 1st, if needed
        days = calendar.monthrange(y,m)[1]
        if d>days:
            d -= days
            m += 1
        if m > 12:
            m -= 12;
            y += 1
        return datetime(y,m,d)

    def parserFormatDateDelta( self, sValue ):
        """
        parse strings of the form
            "12d" (12 days)
            "1y2m" (1 year 2 months)
            "1y2m3w4d" (1 year, 2 months, 3 weeks, 4 days)
            negative sign in front creates a date IN THE FUTURE
        """

        negate = False
        num=""
        dy=dm=dd=0
        for c in sValue:
            if c == "-":
                negate = not negate
            elif c == "y":
                dy = int(num)
                num=""
            elif c == "m":
                dm = int(num)
                num=""
            elif c == "w":
                dd += 7*int(num)
                num=""
            elif c == "d":
                dd += int(num)
                num=""
            else:
                num += c
        if num:
            dd += int(num) # make 'd' optional, and capture remainder

        if negate:
            dy *= -1
            dm *= -1
            dd *= -1

        dtn = self.datetime_now

        dt1 = self.parserDateDelta(dtn.year,dtn.month,dtn.day,dy,dm) - timedelta( dd )
        #dt1 = datetime(ncy,cm,cd) - timedelta( days )
        dt2 = dt1 + timedelta( 1 )
        return calendar.timegm(dt1.timetuple()), calendar.timegm(dt2.timetuple())

    def parserFormatDate( self, value ):

        sy,sm,sd = value.split('/')

        y = int(sy)
        m = int(sm)
        d = int(sd)

        if 50 < y < 100 :
            y += 1900
        if y < 50:
            y += 2000

        dt1 = datetime(y,m,d)
        dt2 = dt1 + timedelta( 1 )

        return calendar.timegm(dt1.timetuple()), calendar.timegm(dt2.timetuple())

    def parserNLPDate( self, value ):
        dt = NLPDateRange(self.datetime_now).parse( value )
        if dt:
            cf = calendar.timegm(dt[0].utctimetuple())
            if cf < 0:
                cf = 0
            rf = calendar.timegm(dt[1].utctimetuple())
            return cf,rf
        return None

    def parserDuration( self, value ):
        # input as "123" or "3:21"
        # convert hours:minutes:seconds to seconds
        m=1
        t = 0
        for x in reversed(value.split(":")):
            t += int(x)*m
            m *= 60
        return IntTime(t)

    def parserDateRule( self, rule , col, value):
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
                epochtime,epochtime2 = self.parserFormatDate( value )
            elif c > 0:
                raise ParseError("Invalid Date format. Expected YY/MM/DD.")
            else:
                epochtime,epochtime2 = self.parserFormatDateDelta( value )
        except ValueError as e:

            result = self.parserNLPDate( value )

            if result is None:
                # failed to convert istr -> int
                raise ParseError("Expected Integer or Date, found `%s`"%value)

            epochtime,epochtime2 = result

        # flip the context of '<' and '>'
        # for dates, '<' means closer to present day
        # date < 5 is anything in the last 5 days
        if rule in self.special_invert:
            rule = self.special_invert[rule]

        # token '=' is partial string matching, in the context of dates
        # it will return any song played exactly n days ago
        # a value of '1' is yesterday
        if rule is PartialStringSearchRule:
            return RangeSearchRule(col, IntDate(epochtime), IntDate(epochtime2))

        # inverted range matching
        if rule is InvertedPartialStringSearchRule:
            return NotRangeSearchRule(col, IntDate(epochtime), IntDate(epochtime2))

        if rule is LessThanEqualSearchRule:
            return rule( col, IntDate(epochtime2))

        return rule( col, IntDate(epochtime) )

    def parserRule(self, colid, rule ,value):
        """
        this must be expanded to support new data formats.
        """
        col = self.translateColumn( colid )
        if col == self.all_text:
            return self.allTextRule(rule, value)
        elif col in self.text_fields:
            return rule( col, value )
        elif col in self.date_fields:
            return self.parserDateRule(rule, col, value)
        # numeric field
        # partial rules don't make sense, convert to exact rules
        if col in self.time_fields:
            value = self.parserDuration( value )

        if rule is PartialStringSearchRule:
            return ExactSearchRule(col, value)
        if rule is InvertedPartialStringSearchRule:
            return InvertedExactSearchRule(col, value)
        return rule( col, value )

    def allTextRule(self, rule, string ):
        """
        returns a rule that will return true if
        any text field matches the given string
        or if no text field contains the string
        """
        meta = OrSearchRule
        if rule in (InvertedPartialStringSearchRule, InvertedExactSearchRule):
            meta = AndSearchRule
        return meta([ rule(col,string) for col in self.text_fields ])

    def parserMeta(self, colid, tok, value, top):
        """ meta options control sql parameters of the query
        They are independant of any database.
        """
        if not top:
            raise ParseError("Option `%s` can only be provided at the top level."%colid)

        if colid in self.meta_options:
            raise ParseError("Option `%s` can not be provided twice"%colid)

        if tok not in self.operators:
            raise ParseError("Operator `%s` not valid in this context"%tok)

        rule = self.operators[tok]

        if colid == "debug":
            self.meta_options[colid] = int(value)
        elif colid == "limit":

            if rule in (PartialStringSearchRule, ExactSearchRule):
                self.meta_options[colid] = int(value)
            else:
                raise ParseError("Illegal operation `%s` for option `%s`"%(tok,colid))

    def getMetaValue(self,colid,default=None):
        """ returns parsed value of a meta option, or default """
        return self.meta_options.get(colid,default)

