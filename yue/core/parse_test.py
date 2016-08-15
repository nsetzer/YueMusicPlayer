#! cd ../.. && python3 setup.py test --test=parse
#! cd ../.. && python2.7 setup.py cover
import unittest

from yue.core.song import Song, SongSearchGrammar

from yue.core.search import Grammar, \
                       PartialStringSearchRule, \
                       InvertedPartialStringSearchRule, \
                       ExactSearchRule, \
                       InvertedExactSearchRule, \
                       RangeSearchRule, \
                       NotRangeSearchRule, \
                       LessThanSearchRule, \
                       LessThanEqualSearchRule, \
                       GreaterThanSearchRule, \
                       GreaterThanEqualSearchRule, \
                       NotSearchRule, \
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

    def _allText(self,v):
        return self.grammar.allTextRule(PartialStringSearchRule,v)

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

        self.parse("x&&\"y\"", ['x','&&','y'])

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

        # I'm slowly phasing out support for the old style format

        expected = self._allText( "foo")
        actual = self.grammar.ruleFromString("foo")
        self.assertEqual(expected,actual)

        expected = PartialStringSearchRule(Song.artist, "foo")
        actual = self.grammar.ruleFromString(".art foo")
        self.assertEqual(expected,actual)

        #expected = InvertedPartialStringSearchRule(Song.artist, "foo")
        #actual = self.grammar.ruleFromString(".art ! foo")
        #self.assertEqual(expected,actual)

        #expected = ExactSearchRule(Song.artist, "foo")
        #actual = self.grammar.ruleFromString(".art == foo")
        #self.assertEqual(expected,actual)

        #expected = AndSearchRule([
        #        InvertedExactSearchRule(Song.artist, "foo"),
        #        InvertedExactSearchRule(Song.artist, "bar")
        #        ])
        #actual = self.grammar.ruleFromString(".art !== foo bar")
        #self.assertEqual(expected,actual)

        # show that parameters can be changed
        expected = AndSearchRule([
                PartialStringSearchRule(Song.artist, "foo"),
                PartialStringSearchRule(Song.album, "bar")
                ])
        actual = self.grammar.ruleFromString(".art foo .abm bar")
        self.assertEqual(expected,actual)

        #expected = AndSearchRule([
        #        PartialStringSearchRule(Song.artist, "foo"),
        #        InvertedPartialStringSearchRule(Song.artist, "bar")
        #        ])
        #actual = self.grammar.ruleFromString(".art foo ! bar")
        #self.assertEqual(expected,actual)

    def test_parser_new_style(self):

        expected = BlankSearchRule()
        actual = self.grammar.ruleFromString("  ")
        self.assertEqual(expected,actual)

        expected = self._allText( "foo")
        actual = self.grammar.ruleFromString(" = foo")
        self.assertEqual(expected,actual)

        expected = self._allText( "foo")
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
                self._allText("foo"),
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

        expected = NotSearchRule([
                self._allText("x"),
                ])
        actual = self.grammar.ruleFromString("! = x")
        self.assertEqual(expected,actual)

        expected = NotSearchRule([
                PartialStringSearchRule(Song.artist, "x"),
                ])
        actual = self.grammar.ruleFromString("! artist = x")
        self.assertEqual(expected,actual)

    def test_parser_operator_precedence(self):
        # correct order is the C order for operators
        #

        expected = AndSearchRule([
                NotSearchRule([self._allText("foo"),]),
                self._allText("bar"),
                ])
        actual = self.grammar.ruleFromString("! foo && bar")
        self.assertEqual(expected,actual)

        expected = NotSearchRule([
                        NotSearchRule([
                            self._allText("x"),
                        ]),
                   ])
        actual = self.grammar.ruleFromString("! ! x")
        self.assertEqual(expected,actual)

        expected = OrSearchRule([
                AndSearchRule([self._allText("a"), self._allText("b"),]),
                AndSearchRule([self._allText("c"), self._allText("d"),]),
                ])
        actual = self.grammar.ruleFromString("a && b || c && d")
        self.assertEqual(expected,actual)

        # TODO: should "a b || c d" parse to the same thing

        return

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

    def test_parser_meta(self):

        expected = BlankSearchRule()
        value=0 # otherwise it will print
        actual = self.grammar.ruleFromString("%s=%s"%(Grammar.META_DEBUG,value))
        self.assertEqual(expected,actual)
        self.assertEqual(self.grammar.getMetaValue(Grammar.META_DEBUG),value)

        value=10
        actual = self.grammar.ruleFromString("%s=%s"%(Grammar.META_OFFSET,value))
        self.assertEqual(expected,actual)
        self.assertEqual(self.grammar.getMetaValue(Grammar.META_OFFSET),value)

        value=20
        actual = self.grammar.ruleFromString("%s=%s"%(Grammar.META_LIMIT,value))
        self.assertEqual(expected,actual)
        self.assertEqual(self.grammar.getMetaValue(Grammar.META_LIMIT),value)

    def test_regexp_errors(self):
        # show that a malformed regular expression is caught as
        # a ParseError, and not a re.error
        with self.assertRaises(ParseError):
            self.grammar.ruleFromString("artist =~ \"+[^a-z]\"")

        # show that a properly formed regex does not throw
        self.grammar.ruleFromString("artist =~ \".+[^a-z]\"")

    def test_parser_errors(self):

        # the lhs is optional for this token
        with self.assertRaises(RHSError):
            self.grammar.ruleFromString(" = ")

        self.grammar.ruleFromString("art < \"\"")

        # this is a RHSError only by implementation
        with self.assertRaises(ParseError):
            self.grammar.ruleFromString(" < ")

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
            self.grammar.ruleFromString("artist = &&")

        with self.assertRaises(RHSError):
            self.grammar.ruleFromString("artist < &&")

        with self.assertRaises(RHSError):
            self.grammar.ruleFromString("artist && &&")

        # these are valid operators, given the grammmar, but
        # are not used, so throw an error.
        with self.assertRaises(ParseError):
            self.grammar.ruleFromString("artist | two")

        with self.assertRaises(ParseError):
            self.grammar.ruleFromString("artist & two")

        with self.assertRaises(ParseError):
            self.grammar.ruleFromString("artist !< two")

        self.grammar.ruleFromString("artist \"!<\" two")

        with self.assertRaises(ParseError):
            self.grammar.ruleFromString("artist |& two")

        # token tagging allows for proper handling of quoted text
        self.grammar.ruleFromString("artist \"|&\" two")

        with self.assertRaises(ParseError):
            self.grammar.ruleFromString("artist &= two")

        with self.assertRaises(ParseError):
            self.grammar.ruleFromString("artist <| two")

        with self.assertRaises(ParseError):
            self.grammar.ruleFromString("artist = &|")

        with self.assertRaises(ParseError):
            self.grammar.ruleFromString("artist <= &|")

        self.grammar.ruleFromString("artist = \"&|\"")

        self.grammar.ruleFromString("artist=\"&|\"")

        # TODO: don't know how to handle this
        #self.grammar.ruleFromString("x&&=y");

        with self.assertRaises(TokenizeError):
            self.grammar.ruleFromString("x\\")

        # || = foo
        # foo = ||
        # old syle queries:
        #     .abm x y (a b c)