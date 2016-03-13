#! python34
# prove that there are not changes between versions of PyCrypto
from __future__ import unicode_literals
import unittest

from yue.client.SymTr.SymTr import SymTr

class TestSymTr(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def main_test(self,src,tar=None):
        o = SymTr(src)
        res=o.nstring
        msg=("\nFail:     '%s'\nFound:    '%s'\nExpected: '%s'"%(src,res,tar)).encode("unicode-escape")
        self.assertEqual(res,tar,msg)

    def pos_test(self,src,pos=None,rpos=None):
        o = SymTr(src)

        if pos is not None:
            msg=("Fail pos : '%s'"%(src)).encode('unicode-escape')
            self.assertEqual(o.position,pos,msg)

        if rpos is not None:
            msg=("Fail rpos:'%s'"%(src)).encode('unicode-escape')
            self.assertEqual(o.rposition,rpos,msg)

    def test_katakana(self):
        self.main_test(';',';')
        self.main_test(';;',';;')
        self.main_test(';;j',';;j')
        self.main_test(';;ja','\u30b8\u30e3')
        self.main_test(';;na','\u30ca')

        self.main_test(';;minnna','\u30df\u30f3\u30ca')
        self.main_test(';;kka','\u30c3\u30ab')
        self.main_test(';;hatto','\u30cf\u30c3\u30c8')
        self.main_test(';;pokki-','\u30dd\u30c3\u30ad\u30fc')

    def test_hiragana(self):
        self.main_test(';',';')
        self.main_test(';;',';;')
        self.main_test(';;J',';;J')
        self.main_test(';;JA','\u3058\u3083')
        self.main_test(';;NA','\u306a')

        self.main_test(';;MINNNA','\u307f\u3093\u306a')
        self.main_test(';;HATTO','\u306f\u3063\u3068')
        self.main_test(';;POKKII','\u307d\u3063\u304d\u3044')

    def test_extra(self):
        # a few random tests
        self.main_test(';;a','\u30a2')
        self.main_test(';;ja','\u30b8\u30e3')

        self.main_test(';;dennja','\u30c7\u30f3\u30b8\u30e3')
        self.main_test('\u30c7\u30f3j','\u30c7\u30f3j')
        self.main_test('\u30c7\u30f3ja','\u30c7\u30f3\u30b8\u30e3')
        self.main_test(';;dennjagyanngu','\u30c7\u30f3\u30b8\u30e3\u30ae\u30e3\u30f3\u30b0')
        self.main_test(';;kuro','\u30af\u30ed')

    def test_hard(self):
        # dzi dzu ji zu
        # zu  : \u30ba su + "
        # dzu : \u30c5 tsu + "
        # ji  : \u30b8
        # dzi : \u30c2

        self.main_test(';;zu','\u30ba')
        self.main_test(';;dzu','\u30c5')

        self.main_test(';;ji','\u30b8')
        self.main_test(';;dzi','\u30c2')

        self.main_test(';;di','\u30c7\u30a3')

        #self.main_test(u';;dza',u"\u30c2\u30e3")
        #self.main_test(u';;dzu',u"\u30c2\u30e5")
        #self.main_test(u';;dzo',u"\u30c2\u30e7")

    def test_reverse(self):
        # test a simple case
        self.main_test('::\u30af\u30ed','kuro')
        # test a sokuon case
        self.main_test('::\u30dd\u30c3\u30ad\u30fc','pokki-')
        # more complicated because two glyphs map to correct form
        self.main_test('::\u30c7\u30f3\u30b8\u30e3',"dennja")

        self.main_test('::\u304f\u308d',"KURO")
        self.main_test('::\u307d\u3063\u304d\u3044',"POKKII")
        self.main_test('::\u3067\u3093\u3058\u3083',"DENNJA")

    def test_position(self):
        # assuming insertion cursor was at EOT before typing last char
        # I had to cheat to figure out the correct 'pos' values
        # ultimatley, the important value is 'rpos', which is easy to count
        # backwards.

        self.pos_test(";;su",pos=1,rpos=0)
        self.pos_test(";;sute",pos=2,rpos=0)

        # pos=4 because ja converts to two characters.
        self.pos_test('\u30c7\u30f3ja',pos=4,rpos=0)

        self.pos_test("foo ;;bi bar",pos=5,rpos=4)     # pos = 4 + num output chars
        self.pos_test("foo ;;biba bar",pos=6,rpos=4)   # or strlen - 4.
        self.pos_test("foo ;;bibara bar",pos=7,rpos=4)

        # check position updates correctly when multiple same characters exist.
        self.pos_test("fu x ;;fu",pos=6,rpos=0)
        self.pos_test("\u30d5 x ;;fu",pos=5,rpos=0)
        self.pos_test(";;fu x \u30d5",pos=1,rpos=4)
        self.pos_test(";;fu x fu",pos=1,rpos=5)

if __name__ == '__main__':
    unittest.main()
