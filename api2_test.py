
from yue.core.api2 import ApiClient, ApiClientWrapper
from yue.core.sqlstore import SQLStore
from yue.core.history import History
from yue.core.library import Library
import json

def mainx():

    db_path = "/Users/nsetzer/Music/Library/yue.db"
    sqlstore = SQLStore(db_path)
    History.init(sqlstore)
    Library.init(sqlstore)

    # get using sqlite db broswer
    username = "admin"
    apikey = "f45596be-5355-4cef-bd00-fb63f872b140"

    api = ApiClient("http://localhost:4200")
    api.setApiUser(username)
    api.setApiKey(apikey)

    apiw = ApiClientWrapper(api)

    # download the list of remote songs
    apiw.connect()

    songs = list(apiw.songs.values())
    with open("songs.JSON", "w") as wf:
        wf.write(json.dumps(songs))

    # get all records in the local database
    records = History.instance().export()

    # add these records to the remote database
    apiw.history_put(records)

    # get all records from remote, that are not in the local db
    r = apiw.history_get()

    print("found %d records " % len(r))
    print(r[:5])

def main():


    db_path = "/Users/nsetzer/Music/Library/yue.db"
    sqlstore = SQLStore(db_path)
    History.init(sqlstore)
    Library.init(sqlstore)

    username = "admin"
    apikey = "f45596be-5355-4cef-bd00-fb63f872b140"

    songs = Library.instance().search("beast")
    song = songs[0]

    api = ApiClient("http://localhost:4200")
    user = api.login("admin", "admin")
    print(user)
    api.setApiUser(username)
    api.setApiKey(user['apikey'])
    apiw = ApiClientWrapper(api)
    apiw.connect()

    song = {
        "uid": 1474,
        "artist": "Artist1",
        "album": "Album1",
        "title": "Title1",
        "path": song["path"],
    }
    song_id = apiw.library_create_song(song)

    print("song_id: %s" % song_id)

    song = {
        "id": song_id,
        "artist": "Artist2",
        "album": "Album2",
        "title": "Title2",
    }
    apiw.library_update_songs([song, ])

    print(apiw.library_get_song(1474))

if __name__ == '__main__':
    main()