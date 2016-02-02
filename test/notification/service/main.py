



from kivy.lib import osc
from kivy.logger import Logger

import time

serviceport = 15123
activityport = 15124

def main():

    #self.oscid = osc.listen(ipAddr='127.0.0.1', port=serviceport)
    #osc.init()

    while True:
        Logger.info("service: ping")
        time.sleep( 2.0 )

if __name__ == '__main__':
    main()