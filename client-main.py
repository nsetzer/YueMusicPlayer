#!python34 $this
__version__ = "1.0.2"
import codecs,traceback
try:
    from yue.client.client import main
    main(__version__)
except Exception as e:
    with codecs.open("yue-error.log","w","utf-8") as wf:
        wf.write("%s\n"%e)
        wf.write(traceback.format_exc())
