#! cd ../.. && python2.7 setup.py test --test=parse
#! cd ../.. && python2.7 setup.py cover
import unittest

from yue.core.song import Song
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
                       allTextRule, \
                       tokenizeString, \
                       ruleFromString, \
                       ParseError, RHSError, LHSError, TokenizeError

DB_PATH = "./unittest.db"

class TestSearchParse(unittest.TestCase):
    """test case for search feature
    """

    def setUp(self):
        #if os.path.exists(DB_PATH):
        #    os.remove(DB_PATH)
        pass

    def tearDown(self):
        #if os.path.exists(DB_PATH):
        #    os.remove(DB_PATH)
        pass

    def parse(self,input,expected):
        actual = tokenizeString(input)
        try:
            self.assertEqual( len(actual), len(expected) )
            for i,(x,y) in enumerate(zip(actual,expected)):
                self.assertEqual(x,y, "%d: %s %s"%(i,x,y))
        except AssertionError:
            print(input)
            print(actual)
            print(expected)
            raise

    def test_parse_simple(self):

        self.parse("artist=foo", ['artist','=','foo'])
        self.parse(" artist = foo ", ['artist','=','foo'])
        self.parse(" artist =\"foo\"", ['artist','=','foo'])
        self.parse(" artist =\"foo \\\" bar \\\"\"", ['artist','=','foo " bar "'])


    def test_parse_generic(self):

        self.parse(" foo", ['foo'])
        self.parse(" ! foo", ['!','foo'])

        self.parse(" ttl = \"this\"", ['ttl','=', 'this'])
        self.parse(" ttl = \\\"", ['ttl','=', '"'])

    def test_parse_join(self):

        # x and y or w and z

        self.parse(" foo bar || baz", ['foo', "bar", "||", "baz"])
        self.parse(" title!=foo artist=bar || artist=baz",
                    ['title','!=','foo', 'artist','=',"bar",
                     "||", 'artist','=',"baz"])

    def test_parser_old_style(self):

        expected = allTextRule(OrSearchRule,PartialStringSearchRule, "foo")
        actual = ruleFromString("foo")
        self.assertEqual(expected,actual)

        expected = PartialStringSearchRule(Song.artist, "foo")
        actual = ruleFromString(".art foo")
        self.assertEqual(expected,actual)

        expected = InvertedPartialStringSearchRule(Song.artist, "foo")
        actual = ruleFromString(".art ! foo")
        self.assertEqual(expected,actual)

        expected = ExactSearchRule(Song.artist, "foo")
        actual = ruleFromString(".art == foo")
        self.assertEqual(expected,actual)

        expected = AndSearchRule([
                InvertedExactSearchRule(Song.artist, "foo"),
                InvertedExactSearchRule(Song.artist, "bar")
                ])
        actual = ruleFromString(".art !== foo bar")
        self.assertEqual(expected,actual)

        # show that parameters can be changed
        expected = AndSearchRule([
                PartialStringSearchRule(Song.artist, "foo"),
                PartialStringSearchRule(Song.album, "bar")
                ])
        actual = ruleFromString(".art foo .abm bar")
        self.assertEqual(expected,actual)

        expected = AndSearchRule([
                PartialStringSearchRule(Song.artist, "foo"),
                InvertedPartialStringSearchRule(Song.artist, "bar")
                ])
        actual = ruleFromString(".art foo ! bar")
        self.assertEqual(expected,actual)

    def test_parser_new_style(self):

        expected = allTextRule(OrSearchRule,PartialStringSearchRule, "foo")
        actual = ruleFromString(" = foo")
        self.assertEqual(expected,actual)

        expected = allTextRule(OrSearchRule,PartialStringSearchRule, "foo")
        actual = ruleFromString("text = foo")
        self.assertEqual(expected,actual)

        expected = allTextRule(AndSearchRule,InvertedPartialStringSearchRule, "foo")
        actual = ruleFromString(" != foo")
        self.assertEqual(expected,actual)

        expected = PartialStringSearchRule(Song.artist, "foo")
        actual = ruleFromString("art = foo")
        self.assertEqual(expected,actual)

        expected = InvertedPartialStringSearchRule(Song.artist, "foo")
        actual = ruleFromString("art != foo")
        self.assertEqual(expected,actual)

        expected = PartialStringSearchRule( Song.title, "hello world")
        actual = ruleFromString("ttl = \"hello world\"")
        self.assertEqual(expected,actual)

    def test_parser_special(self):

        expected = LessThanSearchRule(Song.play_count, "5")
        actual = ruleFromString("pcnt < 5")
        self.assertEqual(expected,actual)

        expected = GreaterThanEqualSearchRule(Song.play_count, "5")
        actual = ruleFromString("pcnt >= 5")
        self.assertEqual(expected,actual)

    def test_parser_nested(self):

        expected = AndSearchRule([
                PartialStringSearchRule(Song.artist, "foo"),
                OrSearchRule([
                    PartialStringSearchRule(Song.album, "bar"),
                    PartialStringSearchRule(Song.album, "baz")
                    ])
                ])
        actual = ruleFromString("artist=foo && (album=bar || album=baz)")
        self.assertEqual(expected,actual)

        actual = ruleFromString("artist=foo (album=bar || album=baz)")
        self.assertEqual(expected,actual)

        actual = ruleFromString(".art foo (.abm bar || .abm baz)")
        self.assertEqual(expected,actual)


    def test_parser_errors(self):

        # the lhs is optinal for this token
        with self.assertRaises(RHSError):
            ruleFromString(" = ")

        # right hand side is required
        with self.assertRaises(RHSError):
            ruleFromString("pcnt < ")

        # left hand side is required.
        with self.assertRaises(LHSError):
            ruleFromString("< 6")

        with self.assertRaises(RHSError):
            ruleFromString("x &&")

        with self.assertRaises(LHSError):
            ruleFromString("|| y")

        with self.assertRaises(RHSError):
            ruleFromString(" artist = (album = bar) ")

        with self.assertRaises(LHSError):
            ruleFromString(" (album = bar) = value")

        with self.assertRaises(RHSError):
            ruleFromString(" artist >= (album = bar) ")

        with self.assertRaises(LHSError):
            ruleFromString(" (album = bar) <= value")

        with self.assertRaises(TokenizeError):
            ruleFromString(" ( album ")

        with self.assertRaises(TokenizeError):
            ruleFromString(" albumn )")

        with self.assertRaises(TokenizeError):
            ruleFromString(" \" foo ")

        # || = foo
        # foo = ||
        # old syle queries:
        #     .abm x y (a b c)