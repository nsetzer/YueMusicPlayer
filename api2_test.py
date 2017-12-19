
from yue.core.api2 import ApiClient, ApiClientWrapper
from yue.core.sqlstore import SQLStore
from yue.core.history import History

def main():

    db_path = "/Users/nsetzer/Music/Library/yue.db"
    sqlstore = SQLStore(db_path)
    History.init(sqlstore)

    # get using sqlite db broswer
    username = "admin"
    apikey = "f45596be-5355-4cef-bd00-fb63f872b140"

    api = ApiClient("http://localhost:4200")
    api.setApiUser(username)
    api.setApiKey(apikey)

    apiw = ApiClientWrapper(api)

    # download the list of remote songs
    apiw.connect()

    # get all records in the local database
    records = History.instance().export()

    # add these records to the remote database
    apiw.history_put(records)

    # get all records from remote, that are not in the local db
    r = apiw.history_get()

    print("found %d records " % len(r))
    print(r[:5])


if __name__ == '__main__':
    main()