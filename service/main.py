
# todo use argparse to get host/port from parent.
#   then:
#       1. send listening port back to the parent
#       2. or have the parent pass in the port to listen on.
# see PyOSC documentation

import os,sys
from kivy.logger import Logger

#android
app_path = '/data/data/com.github.nsetzer.yue/files'
if not os.path.exists(app_path):
    # other
    #dirpath = os.path.dirname(os.path.abspath(__file__))
    #dirpath = os.path.dirname(dirpath)
    app_path = os.getcwd()
# update system path with path to yue package
sys.path.insert(0,app_path)

from yue.server.server import YueServer

if __name__ == '__main__':


    server = YueServer( app_path )
    server.main()

    Logger.error("service: exit")

