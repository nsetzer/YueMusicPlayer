
from yue.client.explorer.source import SourceView
from yue.client.explorer.ftpsource import FTPSource


host = "192.168.0.9"
port = 2121
src = FTPSource(host,port)

view = SourceView(src,src.root())


print(view.listdir("/"))

with view.open("/Music/test.txt","wb") as wb:
    wb.write(b"hello world\n");