#! python

"""
create a table backed by a database
display contents of a query

may neeed to create a special view for playlist.
"""
import os,sys

dirpath = os.path.dirname(os.path.abspath(__file__))
dirpath = os.path.dirname(dirpath)
sys.path.insert(0,dirpath)

from yue.client.widgets.LargeTable import LargeTable

class DBTable(LargeTable):
    """docstring for DBTable"""
    def __init__(self, arg):
        super(DBTable, self).__init__()
        self.arg = arg

def main():
    print("0")

if __name__ == '__main__':
    main()