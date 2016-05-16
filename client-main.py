#!python $this
"""
changelog

2016-xx-xx 1.1.1
    enable recording of history record changes

2016-05-03 1.1.0
    move to python3.5
    move to Qt 5.6
    use Visual Studio 2015 to build C libraries

"""
__version__ = "1.1.0"
__datetime__ = ""
import codecs,traceback
try:
    from yue.client.client import main
    main(__version__,__datetime__)
except Exception as e:
    with codecs.open("yue-error.log","w","utf-8") as wf:
        wf.write("%s\n"%e)
        wf.write(traceback.format_exc())
