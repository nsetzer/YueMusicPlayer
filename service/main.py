
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
from yue.sound.pybass import get_platform_path

def load_path_callback(message, *args):
    Logger.info("service: load_path: %s : %s" % (message,args))

    SoundManager.instance().load( {'path':message[2],} )
    SoundManager.instance().play()

def audio_action_callback(message,*args):
    action = message[2]

    Logger.info("action: %s"%action)
    inst = SoundManager.instance()
    if action == 'play':
        inst.play()
    elif action == 'pause':
        inst.pause()
    elif action == 'unload':
        inst.unload()

if __name__ == '__main__':
    osc.init()
    oscid = osc.listen(ipAddr='127.0.0.1', port=serviceport)
    osc.bind(oscid, load_path_callback, '/load_path')
    osc.bind(oscid, audio_action_callback, '/audio_action')

    libpath = get_platform_path()

    SoundManager.init( libpath )

    while True:
        osc.readQueue(oscid)
        time.sleep(.1)
    Logger.info("service: exit")
