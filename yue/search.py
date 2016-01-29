

class SearchRule(object):
    """docstring for SearchRule"""
    def __init__(self):
        super(SearchRule, self).__init__()

    def check(self,song):
        raise NotImplementedError()

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
        return "%s like ?"%(self.column,), ("%%%s%%"%self.value,)

    def __repr__(self):
        return "Rule<%s in `%s`>"%(self.value, self.column)

class ExactSearchRule(ColumnSearchRule):
    """docstring for SearchRule"""
    def check(self,song):
        return self.value == song[self.column]

    def __repr__(self):
        return "Rule<%s equals `%s`>"%(self.value, self.column)

    def sql(self):
        return "%s = ?"%(self.column,), (self.value,)

class LessThanSearchRule(ColumnSearchRule):
    """docstring for SearchRule"""
    def check(self,song):
        return song[self.column] < self.value

    def sql(self):
        return "%s < ?"%(self.column,), (self.value,)

    def __repr__(self):
        return "Rule<%s less than `%s`>"%(self.value, self.column)

class LessThanEqualSearchRule(ColumnSearchRule):
    """docstring for SearchRule"""
    def check(self,song):
        return song[self.column] <= self.value

    def sql(self):
        return "%s <= ?"%(self.column,), (self.value,)

    def __repr__(self):
        return "Rule<%s less than or equal `%s`>"%(self.value, self.column)

class GreaterThanSearchRule(ColumnSearchRule):
    """docstring for SearchRule"""
    def check(self,song):
        return song[self.column] > self.value

    def sql(self):
        return "%s > ?"%(self.column,), (self.value,)

    def __repr__(self):
        return "Rule<%s greater than `%s`>"%(self.value, self.column)

class GreaterThanEqualSearchRule(ColumnSearchRule):
    """docstring for SearchRule"""
    def check(self,song):
        return song[self.column] >= self.value
    def sql(self):
        return "%s >= ?"%(self.column,), (self.value,)

    def __repr__(self):
        return "Rule<%s greater than or equal `%s`>"%(self.value, self.column)

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
        return "Rule<`%s` in range (%s,%s)>"%(self.column,self.value_low,self.value_high)

class NotRangeSearchRule(RangeSearchRule):
    """docstring for SearchRule"""

    def check(self,song):
        return song[self.column] < self.value_low or self.value_high < song[self.column]

    def sql(self):
        return "%s NOT BETWEEN ? AND ?"%(self.column,), (self.value_low,self.value_high)

    def __repr__(self):
        return "Rule<`%s` not in range (%s,%s)>"%(self.column,self.value_low,self.value_high)

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
        sql = '(' + ' and '.join(sql) + ')'
        return sql,vals

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
        sql = '(' + ' or '.join(sql) + ')'
        return sql,vals

def naive_search( sqldb, rule ):
    """ iterate through the database and yield songs which match a rule """
    for song in sqldb.iter():
        if rule.check(song):
            yield song

def sql_search( sqlview, rule):
    """ convert a rule to a sql query and yield matching songs """
    x = rule.sql()
    query = "select * from %s where "%sqlview.name + x[0]
    return sqlview.query(query, *x[1])