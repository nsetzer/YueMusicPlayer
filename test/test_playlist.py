#! python2.7 $this
import os,sys
dirpath = os.path.dirname(os.path.abspath(__file__))
dirpath = os.path.dirname(dirpath)
sys.path.insert(0,dirpath)

from yue.playlist import PlaylistManager
from yue.sqlstore import SQLStore



dbpath = "test.db"
if os.path.exists(dbpath):
    os.remove(dbpath)
store = SQLStore(dbpath)
PlaylistManager.init( store )

pl = PlaylistManager.instance().newPlaylist('current')

print(pl.size())
pl.append(1)
pl.append(2)
pl.append(3)
pl.append(4)
print(pl.size())

print("--")
for i,r in enumerate(pl.iter()):
    print(r)

pl.delete(1)
print(pl.size())

print("--")
for i,r in enumerate(pl.iter()):
    print(r)

