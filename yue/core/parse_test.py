#! cd ../.. && python2.7 setup.py test --test=parse
#! cd ../.. && python2.7 setup.py cover
import unittest

from yue.core.song import Song, SongSearchGrammar

from yue.core.search import PartialStringSearchRule, \
                       InvertedPartialStringSearchRule, \
                       ExactSearchRule, \
                       InvertedExactSearchRule, \
                       RangeSearchRule, \
                       NotRangeSearchRule, \
                       LessThanSearchRule, \
                       LessThanEqualSearchRule, \
                       GreaterThanSearchRule, \
                       GreaterThanEqualSearchRule, \
                       AndSearchRule, \
                       OrSearchRule, \
                       BlankSearchRule, \
                       ParseError, RHSError, LHSError, TokenizeError

DB_PATH = "./unittest.db"

class TestSearchParse(unittest.TestCase):
    """test case for search feature
    """

    def setUp(self):
        #if os.path.exists(DB_PATH):
        #    os.remove(DB_PATH)
        self.grammar = SongSearchGrammar()

    def tearDown(self):
        #if os.path.exists(DB_PATH):
        #    os.remove(DB_PATH)
        pass

    def parse(self,input,expected):
        actual = self.grammar.tokenizeString(input)
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

        expected = self.grammar.allTextRule(PartialStringSearchRule, "foo")
        actual = self.grammar.ruleFromString("foo")
        self.assertEqual(expected,actual)

        expected = PartialStringSearchRule(Song.artist, "foo")
        actual = self.grammar.ruleFromString(".art foo")
        self.assertEqual(expected,actual)

        expected = InvertedPartialStringSearchRule(Song.artist, "foo")
        actual = self.grammar.ruleFromString(".art ! foo")
        self.assertEqual(expected,actual)

        expected = ExactSearchRule(Song.artist, "foo")
        actual = self.grammar.ruleFromString(".art == foo")
        self.assertEqual(expected,actual)

        expected = AndSearchRule([
                InvertedExactSearchRule(Song.artist, "foo"),
                InvertedExactSearchRule(Song.artist, "bar")
                ])
        actual = self.grammar.ruleFromString(".art !== foo bar")
        self.assertEqual(expected,actual)

        # show that parameters can be changed
        expected = AndSearchRule([
                PartialStringSearchRule(Song.artist, "foo"),
                PartialStringSearchRule(Song.album, "bar")
                ])
        actual = self.grammar.ruleFromString(".art foo .abm bar")
        self.assertEqual(expected,actual)

        expected = AndSearchRule([
                PartialStringSearchRule(Song.artist, "foo"),
                InvertedPartialStringSearchRule(Song.artist, "bar")
                ])
        actual = self.grammar.ruleFromString(".art foo ! bar")
        self.assertEqual(expected,actual)

    def test_parser_new_style(self):

        expected = BlankSearchRule()
        actual = self.grammar.ruleFromString("  ")
        self.assertEqual(expected,actual)

        expected = self.grammar.allTextRule(PartialStringSearchRule, "foo")
        actual = self.grammar.ruleFromString(" = foo")
        self.assertEqual(expected,actual)

        expected = self.grammar.allTextRule(PartialStringSearchRule, "foo")
        actual = self.grammar.ruleFromString("text = foo")
        self.assertEqual(expected,actual)

        expected = self.grammar.allTextRule(InvertedPartialStringSearchRule, "foo")
        actual = self.grammar.ruleFromString(" != foo")
        self.assertEqual(expected,actual)

        expected = PartialStringSearchRule(Song.artist, "foo")
        actual = self.grammar.ruleFromString("art = foo")
        self.assertEqual(expected,actual)

        expected = InvertedPartialStringSearchRule(Song.artist, "foo")
        actual = self.grammar.ruleFromString("art != foo")
        self.assertEqual(expected,actual)

        expected = PartialStringSearchRule( Song.title, "hello world")
        actual = self.grammar.ruleFromString("ttl = \"hello world\"")
        self.assertEqual(expected,actual)

    def test_parser_special(self):

        expected = LessThanSearchRule(Song.play_count, "5")
        actual = self.grammar.ruleFromString("pcnt < 5")
        self.assertEqual(expected,actual)

        expected = GreaterThanEqualSearchRule(Song.play_count, "5")
        actual = self.grammar.ruleFromString("pcnt >= 5")
        self.assertEqual(expected,actual)

    def test_parser_text_edge(self):
        # for = != == !==, LHS should be infered as all text when not given
        expected = AndSearchRule([
                self.grammar.allTextRule(PartialStringSearchRule,"foo"),
                self.grammar.allTextRule(InvertedPartialStringSearchRule,"bar"),
                ])
        actual = self.grammar.ruleFromString("foo && !=bar")
        self.assertEqual(expected,actual)

        expected = AndSearchRule([
                PartialStringSearchRule(Song.artist, "foo"),
                self.grammar.allTextRule(InvertedPartialStringSearchRule,"bar"),
                ])
        actual = self.grammar.ruleFromString("artist=foo !=bar")
        self.assertEqual(expected,actual)

        expected = AndSearchRule([
                self.grammar.allTextRule(InvertedPartialStringSearchRule,"foo"),
                self.grammar.allTextRule(InvertedPartialStringSearchRule,"bar"),
                ])
        actual = self.grammar.ruleFromString("!=foo && !=bar")
        self.assertEqual(expected,actual)

        expected = AndSearchRule([
                self.grammar.allTextRule(InvertedPartialStringSearchRule,"foo"),
                self.grammar.allTextRule(InvertedPartialStringSearchRule,"bar"),
                ])
        actual = self.grammar.ruleFromString("!=foo !=bar")
        self.assertEqual(expected,actual)

    def test_parser_nested(self):

        expected = AndSearchRule([
                PartialStringSearchRule(Song.artist, "foo"),
                OrSearchRule([
                    PartialStringSearchRule(Song.album, "bar"),
                    PartialStringSearchRule(Song.album, "baz")
                    ])
                ])
        actual = self.grammar.ruleFromString("artist=foo && (album=bar || album=baz)")
        self.assertEqual(expected,actual)

        actual = self.grammar.ruleFromString("artist=foo (album=bar || album=baz)")
        self.assertEqual(expected,actual)

        actual = self.grammar.ruleFromString(".art foo (.abm bar || .abm baz)")
        self.assertEqual(expected,actual)

    def test_parser_errors(self):

        # the lhs is optional for this token
        with self.assertRaises(RHSError):
            self.grammar.ruleFromString(" = ")

        # right hand side is required
        with self.assertRaises(RHSError):
            self.grammar.ruleFromString("pcnt < ")

        # left hand side is required.
        with self.assertRaises(LHSError):
            self.grammar.ruleFromString("< 6")

        with self.assertRaises(RHSError):
            self.grammar.ruleFromString("x &&")

        with self.assertRaises(LHSError):
            self.grammar.ruleFromString("&& y")

        with self.assertRaises(LHSError):
            self.grammar.ruleFromString("|| y")

        with self.assertRaises(RHSError):
            self.grammar.ruleFromString(" artist = (album = bar) ")

        #with self.assertRaises(LHSError):
        #    self.grammar.ruleFromString(" (album = bar) = value")

        with self.assertRaises(RHSError):
            self.grammar.ruleFromString(" artist >= (album = bar) ")

        with self.assertRaises(LHSError):
            self.grammar.ruleFromString(" (album = bar) <= value")

        with self.assertRaises(TokenizeError):
            self.grammar.ruleFromString(" ( album ")

        with self.assertRaises(TokenizeError):
            self.grammar.ruleFromString(" albumn )")

        with self.assertRaises(TokenizeError):
            self.grammar.ruleFromString(" \" foo ")

        with self.assertRaises(RHSError):
            self.grammar.ruleFromString("one = &&")

        with self.assertRaises(RHSError):
            self.grammar.ruleFromString("one < &&")

        with self.assertRaises(RHSError):
            self.grammar.ruleFromString("one && &&")

        # || = foo
        # foo = ||
        # old syle queries:
        #     .abm x y (a b c)