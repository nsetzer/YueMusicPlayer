
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

def init_callback(message,*args):
    Logger.info("service: init: %s" % message[2:])

    SoundManager.init( message[2] )

    res=osc.sendMsg('/pong', dataArray=[], port=activityport)

def load_path_callback(message, *args):
    Logger.info("service: load_path: %s : %s" % (message,args))

    SoundManager.instance().load( {'path':message[2],} )
    SoundManager.instance().play()

if __name__ == '__main__':
    osc.init()
    oscid = osc.listen(ipAddr='127.0.0.1', port=serviceport)
    osc.bind(oscid, init_callback, '/init')
    osc.bind(oscid, load_path_callback, '/load_path')
    while True:
        osc.readQueue(oscid)
        time.sleep(.1)
    Logger.info("service: exit")
