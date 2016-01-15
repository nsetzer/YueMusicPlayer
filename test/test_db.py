

from kivy.storage.dictstore import DictStore

# .keys() : list of all keys in datastore
# get(), put() , exists(), delete(), find()
def main():

    ds = DictStore("./test.store")

    #ds.put("setting-foo",bar="baz")
    #ds.put(0,artist="stone")
    print(ds.keys())



if __name__ == '__main__':
    main()