from .song import Song

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
        for rule in self.rules:
            x = rule.sql()
            sql.append(x[0])
            vals.extend(x[1])
        sql = '(' + ' AND '.join(sql) + ')'
        return sql,vals

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
        for rule in self.rules:
            x = rule.sql()
            sql.append(x[0])
            vals.extend(x[1])
        sql = '(' + ' OR '.join(sql) + ')'
        return sql,vals

    def __repr__(self):
        return "<" + ' || '.join([ repr(r) for r in self.rules]) + ">"

def naive_search( sqldb, rule ):
    """ iterate through the database and yield songs which match a rule """
    for song in sqldb.iter():
        if rule.check(song):
            yield song

def sql_search( db, rule, case_insensitive=True):
    """ convert a rule to a sql query and yield matching songs """
    x = rule.sql()
    query = "SELECT * FROM %s WHERE "%db.name + x[0]
    if case_insensitive:
        query += " COLLATE NOCASE"
    return db.query(query, *x[1])

def allTextRule( join_rule, string_rule, string ):
    """
    returns a rule that will return true if
    any text field matches the given string

    join_rule: as OrSearchRule or AndSearchRule
    string_rule as : PartialStringSearchRule, etc

    """
    return join_rule([ string_rule(col,string) for col in Song.textFields() ])

def tokenizeString( input ):
    """
    simple parser for nested queries

    'column = this'
    'column = this || column = that'
    '(column = this || column=that) && column > 0'
    """
    idx = 0;

    output = []
    special = '!=<>~;|&'
    kind = False
    stack = [ output ]
    start = 0;
    quoted = False

    def append():
        text = input[start:idx].strip()
        if text:
            stack[-1].append(text)

    while idx < len( input ):
        c = input[idx]
        if c == '"' and not quoted:
            quoted = True
            append()
            start = idx+1
        elif c == '"' and quoted:
            append()
            start = idx+1
            quoted = False
        elif not quoted:
            s = c in special
            if c == '\\':
                input = input[:idx] + input[idx+1:]
            elif c == '(':
                append()
                new_level = []
                #cur_level = stack[-1]
                #if cur_level:
                #    if cur_level[-1] not in ['&&','||']:
                #        cur_level.append("&&")
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
            elif s and not kind:
                append()
                start = idx
                kind = True
            elif not s and kind:
                append()
                start = idx
                kind = False
        idx += 1
    append()

    return output

class ParseError(Exception):
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

# does not require left token
operators = {
    "=" :PartialStringSearchRule,
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

flow = {
    "&&" : AndSearchRule,
    "||" : OrSearchRule
}

def parserRule(colid, rule ,value):

    col = Song.column( colid );

    is_text = col in Song.textFields()

    if colid == Song.all_text:
        meta = OrSearchRule
        if rule in (InvertedPartialStringSearchRule, InvertedExactSearchRule):
            meta = AndSearchRule
        return allTextRule(meta, rule, value)
    elif is_text:
        return rule( col, value )
    else: # is number (or date, todo)
        return rule( col, value )

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
            while i < len(tokens) and tokens[i] not in flow:
                i += 1;
            continue
        elif tok in operators:
            if not hasr:
                raise RHSError(tok, "expected value")
            r = tokens.pop(i+1)
            if not isinstance(r,(str,unicode)):
                raise RHSError(tok, "expected string")
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

    current_col = Song.all_text
    current_opr = PartialStringSearchRule

    i=0
    while i < len(tokens):
        tok = tokens[i]
        hasl = i>0
        hasr = i<len(tokens)-1

        if isinstance(tok, (str, unicode)):
            # support old-style queries
            if tok in flow:
                if not hasr:
                    raise RHSError(tok, "expected value")
                if not hasl:
                    raise LHSError(tok, "expected value")
                r = tokens.pop(i+1)
                i-=1
                l = tokens.pop(i)
                tokens[i] = flow[tok]([l,r])

            elif tok.startswith(sigil):
                current_col = tok[1:]
                tokens.pop(i)
                i -= 1
            elif tok == "!":
                current_opr = operators_invert[current_opr]
                tokens.pop(i)
                i -= 1
            elif tok in operators:
                current_opr = operators[tok]
                tokens.pop(i)
                i -= 1
            else:
                tokens[i] = parserRule(current_col,current_opr,tok)

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
    tokens = tokenizeString( string )
    return parseTokens( tokens );


