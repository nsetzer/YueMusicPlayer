
# todo use argparse to get host/port from parent.
#   then:
#       1. send listening port back to the parent
#       2. or have the parent pass in the port to listen on.
# see PyOSC documentation
import os,sys
import time

from kivy.lib import osc
from kivy.logger import Logger


dirpath = os.path.dirname(os.path.abspath(__file__))
dirpath = os.path.dirname(dirpath)
sys.path.insert(0,dirpath)
print(dirpath)

serviceport = 15123
activityport = 15124

from yue.sound.manager import SoundManager

def someapi_callback(message, *args):
   Logger.info("service: got a message! %s" % message)

if __name__ == '__main__':
    osc.init()
    oscid = osc.listen(ipAddr='127.0.0.1', port=serviceport)
    osc.bind(oscid, someapi_callback, '/some_api')
    while True:
        osc.readQueue(oscid)
        time.sleep(.1)
    Logger.info("service: exit")
