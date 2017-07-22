#!python $this
"""
changelog

2016-05-03 1.1.0
    move to python3.5
    move to Qt 5.6
    use Visual Studio 2015 to build C libraries

"""
__version__ = "1.1.11"
__datetime__ = ""
__builddate__ = ""
import codecs,traceback,sys
if (sys.version_info[0]==2):
    raise RuntimeError("python2 not supported")
try:
    from yue.client.client import main
    main(__version__,__datetime__,__builddate__)
except Exception as e:
    with codecs.open("yue-error.log","w","utf-8") as wf:
        msg = "%s\n\n"%e
        msg += traceback.format_exc()
        wf.write(msg)
        sys.stderr.write(msg)
