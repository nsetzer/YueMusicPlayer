#! python34 $this

import os
import sys
import socket

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

"""
import os,sys,socket
def socket_send(host,port,msg):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    # messages use the \n as the end of message marker, and cannot contain it otehrwise
    sock.send(msg.encode('utf-8')) # len equals message length plus the new line
    sock.close();
if __name__ == "__main__":
    host="127.0.0.1"
    args=sys.argv
    port = 15123
    if port > 0:
        socket_send(host,port,' '.join( args[1:] ));
"""

class SocketListen(QThread):
    """docstring for SocketListen"""

    message_recieved = pyqtSignal(str)

    def __init__(self, host=None, port=0, parent=None):
        super(SocketListen, self).__init__(parent)

        self.host = host or 'localhost'#socket.gethostname()
        self.port = 0 if port <= 0 else port
        print(self.host,self.port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind( (self.host,self.port) ) # bind a new socket, to a random unused port.
        self.sock.listen(5)
        self.sock.settimeout(.5)
        print(self.sock.getsockname())
        self.alive = True

    def run(self):
        while self.alive:
            try:
                conn, addr = self.sock.accept()
                msg = conn.recv(4096);
                if msg:
                    self.message_recieved.emit( msg.decode("utf-8") )
            except socket.timeout as e:
                pass
            except Exception as e:
                print(type(e),e)


    def join(self):
        self.alive = False
        sys.stdout.write("closing socket\n")
        self.wait()

def main():

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    sockthread = SocketListen(port=15123)

    sockthread.run()

if __name__ == '__main__':
    main()