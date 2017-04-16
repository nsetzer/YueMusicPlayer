#! python34 ../../../test/test_client.py $this

import sys

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from yue.core.song import Song
from yue.core.library import Library, getSortKey
from yue.core.playlist import PlaylistManager
from yue.core.sqlstore import SQLStore
from yue.core.util import string_quote
from yue.core.search import BlankSearchRule,PartialStringSearchRule,AndSearchRule,OrSearchRule

from .Leaf import Leaf
from .LargeTree import LargeTree

import time

class LibraryTree(LargeTree):

    def __init__(self,parent=None):
        super(LibraryTree,self).__init__(parent)
        self.setLastColumnExpanding(True)
        self.checkable = True

    def refreshData(self):

        data = Library.instance().getArtistAlbums()
        # convert the data to a tree
        root = Leaf(None,"Library (%d)"%len(data),None)
        for art, albs in data:
            a = Leaf(root, art, None)
            for alb in albs:
                Leaf(a, alb, None)

        root.checkable = True
        root.collapsed = False
        root.collapsible = False
        self.setRoot(root)

    def keyPressOther(self,event):
        self.jump_to_letter(chr(event.key()))

    def keyPressEnter(self,event):
        rule = self.formatCheckedAsQueryRule()
        print(rule.sql())

    def jump_to_letter(self,key):
        """
        scan the tree view for an artist that starts with the given letter
        set the selection to the first artist found, repeated presses
        should select the next artist with that letter, eventually looping
        back to the start.
        """

        if '0' <= key <= '9' or 'A' <= key <= 'Z':

            # TODO accessing self.selection is breaking a rule
            offset= 1 + list(self.selection)[0] if len(self.selection) else 0
            idx = 0
            while idx < len(self.data):
                item = self.data[(offset+idx)%len(self.data)]
                # only scroll to artists.
                if not self.index_is_album(idx):
                    if getSortKey(str(item)).upper().startswith(key):
                        idx=(offset+idx)%len(self.data)
                        self.setSelection([idx,])
                        self.scrollTo(idx)
                        self.update();
                        break
                idx += 1

    def keyPressRight(self,event):
        #super(LTree_Library,self).keyPressRight(event)
        row = self.selection_last_row_added
        item = self.data[row]
        if item.hasChildren() and item.collapsed:
            item.collapsed = False
            self.setData( self.root.toList() )
            self.update();

    def keyPressLeft(self,event):
        #super(LTree_Library,self).keyPressRight(event)
        row = self.selection_last_row_added
        item = self.data[row]

        if item != None:

            # collapse the selected artist
            if item.hasChildren() and item.collapsed==False:
                item.collapsed = True
                self.setData( self.root.toList() )
                self.update();
            # collapse an artist if the artists album is selected
            elif not item.hasChildren() \
                and item.parent != None \
                and item.parent.collapsed == False:
                    item.parent.collapsed = True
                    self.setData( self.root.toList() )
                    self.update();
                    #TODO: grab the parents index.
                    # assign each list an index when toList is called.
                    self.setSelection([self.selection_last_row_added,])

    def index_is_album(self,idx):

        item = self.data[idx]

        if item==self.root:
            return False

        if item.parent != None and item.parent == self.root:
            return False

        return True

    def formatItemAsQueryString(self,item):
        if item==self.root:
            return ""
        elif item.parent != None and item.parent == self.root:
            text = str(item)
            return "artist==%s"%string_quote(text)
        else:
            text1 = str(item.parent)
            text2 = str(item)
            return "artist==%s album==%s"%(string_quote(text1),string_quote(text2))

    def formatSelectionAsQueryString(self):

        temp = list(self.selection)
        s = ""
        if len(temp) > 0:
            i = temp[0]
            return self.formatItemAsQueryString(self.data[i])
        raise IndexError("nothing selected")

    def formatItemAsQueryRule(self,item):
        if item==self.root:
            return BlankSearchRule()
        elif item.parent != None and item.parent == self.root:
            text = str(item)
            return PartialStringSearchRule(Song.artist,text)
        else:
            text1 = str(item.parent)
            text2 = str(item)
            return AndSearchRule([
                        PartialStringSearchRule(Song.artist,text1),
                        PartialStringSearchRule(Song.album,text2)])

    def formatCheckedAsQueryRule(self):
        checked = self.root.getChecked()
        sys.stdout.write("create query with %d terms\n"%len(checked))
        rule = OrSearchRule([ self.formatItemAsQueryRule(x) for x in checked ])
        return rule

    def showArtist(self,artist):
        artist = artist.lower()
        # search thru top level children which are artists.
        for child in ( x for x in self.data if x.parent is self.root):
            if child.text.lower() == artist:
                index = self.data.index(child)
                child.collapsed = False
                self.setData( self.root.toList() )
                # scrollTo takes an integer N, which is the number
                # of rows it will try to center in the window
                self.scrollTo(index,len(child.children)+1)
                self.setSelection([index,])
                self.update()

    def clear_checked(self):
        for leaf in self.root.getChecked():
            leaf.setCheckState(False)
            self.update();

    def collapse_all(self):
        self.root.collapse_all();
        self.root.collapsed = False
        self.setData( self.root.toList() )
        self.update();

    def expand_all(self):
        self.root.expand_all();
        self.setData( self.root.toList() )
        self.update();

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    db_path = "./yue.db"
    sqlstore = SQLStore(db_path)
    Library.init( sqlstore )
    PlaylistManager.init( sqlstore )

    table = LibraryTree()

    table.refreshData()

    table.container.resize(640,320)
    table.container.show()
    #table.checkable= True
    #table.setStyleSheet('font-size: 12pt;')

    sys.exit(app.exec_())

if __name__ == '__main__':


    main()
