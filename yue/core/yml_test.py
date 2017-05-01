

import unittest, time

import os,io
from yue.core.yml import YmlGrammar, YML, StrPos, YmlException

def compare(x,y):
    """ deep comparison of elements """
    if isinstance(x,dict) and isinstance(y,dict):
        if len(x) != len(y):
            return False
        for (k1,v1),(k2,v2) in zip(sorted(x.items()),sorted(y.items())):
            if k1!=k2:
                return False
            if not compare(v1,v2):
                return False
        return True
    elif isinstance(x,list) and isinstance(y,list):
        if len(x) != len(y):
            return False
        for v1,v2 in zip(x,y):
            if not compare(v1,v2):
                return False
        return True
    else:
        return x==y

class TestYml(unittest.TestCase):
    """
    """

    def __init__(self,*args,**kwargs):
        super(TestYml,self).__init__(*args,**kwargs)

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_grammar(self):
        """
        Test that the grammar for parsing parameter values works
        correctly.
        """
        yg = YmlGrammar()


        def test_grammar(extra,text,expected):
            o,l = yg.parse(io.StringIO(extra),1,text)
            self.assertTrue(compare(o,expected),
                msg="\nfound:    %s\nexpected: %s"%(o,expected))

        # basic types
        test_grammar("","1474",StrPos('1474',0,4))
        test_grammar("",'"abc"',StrPos('abc',0,3))
        test_grammar("",'abc',StrPos('abc',0,3))
        test_grammar("",'true',StrPos('true',0,4))
        test_grammar("",'1.23',StrPos('1.23',0,4))
        test_grammar("",'.23'   ,StrPos('.23',0,3))
        test_grammar("",'1.'   ,StrPos('1.',0,2))

        # lists
        test_grammar("","(1,2,3)", ['1','2','3'] )
        test_grammar("","1,2,3", ['1','2','3'] )
        test_grammar("","(0,1),(2,3)", [['0','1'],['2','3']] )

        # dictionaries
        test_grammar("","{a=2,b=4}", {"a":'2',"b":'4'} )
        test_grammar("","{ a = 2 , b = 4 }", {"a":'2',"b":'4'} )
        test_grammar("","{a=2}, { a = 4 }", [{"a":'2'},{"a":'4'}] )
        test_grammar("","{a= (1,2) }", {"a":['1','2']} )

        # string with comment
        test_grammar("","1474 # comment", StrPos('1474',0,4))
        test_grammar("","\"abc#123\" # comment", StrPos('abc#123',0,7))

        # multi-line statements
        test_grammar(" 3)\n","(1,2,", ['1','2','3'] )
        test_grammar("World\"","\"Hello ", StrPos("Hello World",0,11) )
        test_grammar("{a=4}","{a=2},", [{"a":'2'},{"a":'4'}] )

    def test_serialization(self):
        """
        test the round trip serializing an object, then deserializing.
        """
        yml = YML()
        def test_serialization(o):
            s = yml.dumps(o)
            try:
                o2 = yml.loads(s)
                self.assertTrue(compare(o,o2),
                    msg="\nfound:    %s\nexpected: %s"%(o2,o))
            except:
                print(s)
                raise;

        test_serialization({"section":{"param":123}})
        test_serialization({"section":{"param":"a\"あ\"\n"}})

    def test_deserialization(self):
        """
        test deserializing str->object
        """
        yml = YML()
        def test_deserialization(s,o):
            o2 = yml.loads(s)
            self.assertTrue(compare(o2,o),
                msg="\nfound:    %s\nexpected: %s"%(o2,o))

        test_deserialization("""
        [section]
        param=123""", {"section":{"param":123}})

        test_deserialization("""
        [section]
        param="\\n\\x0A\\u3042" """, {"section":{"param":"\n\n\u3042"}})

    def test_syntax_error(self):

        yml = YML()
        def test_syntax_error(s):
            with self.assertRaises(YmlException):
                yml.loads(s)

        test_syntax_error("""
            [section]
            param={ {} : {} }
            """)



