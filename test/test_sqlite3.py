
import os,sys
dirpath = os.path.dirname(os.path.abspath(__file__))
dirpath = os.path.dirname(dirpath)
sys.path.insert(0,dirpath)

from yue.sqlstore import SQLStore, SQLView

library_columns = [
    ('uid','integer PRIMARY KEY AUTOINCREMENT'),
    ('path',"text"),
    ('artist',"text"),
    ('composer',"text DEFAULT ''"),
    ('album','text'),
    ('title','text'),
    ('genre',"text DEFAULT ''"),
    ('year','integer DEFAULT 0'),
    ('country',"text DEFAULT ''"),
    ('lang',"text DEFAULT ''"),
    ('comment',"text DEFAULT ''"),
    ('album_index','integer DEFAULT 0'),
    ('length','integer DEFAULT 0'),
    ('last_played','integer DEFAULT 0'),
    ('playcount','integer DEFAULT 0'),
    ('rating','integer DEFAULT 0'),
]

dbpath = "test.db"
if os.path.exists(dbpath):
    os.remove(dbpath)
create = not os.path.exists(dbpath)

store = SQLStore(dbpath)
view = SQLView(store,"library", library_columns)

# self.store.conn.execute("INSERT INTO library (artist, album, title, path) VALUES ('artist1','album1','title1','path1')")

view.insert(artist="fooa",album="bar",title="baz")
view.insert(artist="foob",album="bar",title="baz")

res = view.get(1)
print(res)

res = view.update(1,composer="none")
print(res)

res = view.get(1)
print(res)

print("---")

for res in view.select(album="bar"):
    print(">",res)