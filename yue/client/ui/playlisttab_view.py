#! python34 $this

import os,sys

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

import yue
from yue.client.widgets.LargeTable import LargeTable
from yue.client.widgets.SongTable import SongTable
from yue.client.widgets.LineEdit import LineEdit
from yue.client.widgets.TableEditColumn import EditColumn

from yue.client.ui.rename_dialog import RenameDialog
from yue.client.ui.openpl_dialog import OpenPlaylistDialog
from yue.client.ui.playlistedit_view import PlaylistEditView
from yue.client.ui.plexport_dialog import ExportM3uDialog
from yue.client.ui.plimport_dialog import ImportM3uDialog
from yue.client.ui.sync_dialog import SyncProfileDialog, SyncDialog

from yue.core.song import Song
from yue.core.search import ParseError
from yue.core.sqlstore import SQLStore
from yue.core.settings import Settings
from yue.core.library import Library
from yue.core.playlist import PlaylistManager

from yue.client.widgets.Tab import TabWidget


class SelectTable(LargeTable):
    """docstring for SelectTable"""
    newPlaylist = pyqtSignal();
    openPlaylist = pyqtSignal(str);
    savePlaylist = pyqtSignal(str);
    renamePlaylist = pyqtSignal(str,str);
    deletePlaylist = pyqtSignal(str);
    def __init__(self, parent=None):
        super(SelectTable, self).__init__(parent)

        self.setSelectionRule(LargeTable.SELECT_ONE)
        self.setLastColumnExpanding( True )
        self.setAlwaysHideScrollbar(True,False)
        self.showColumnHeader( False )
        self.showRowHeader( True )

    def mouseDoubleClick(self,row,col,event):

        if event is None or event.button() == Qt.LeftButton:
            if 0<= row < len(self.data):
                self.open_list(self.data[row][0]);

    def mouseReleaseRight(self,event):

        items = self.getSelection()
        print(items)
        menu = QMenu(self)

        act = menu.addAction("New List",self.newPlaylist.emit)

        menu.addSeparator()

        act = menu.addAction(QIcon(":/img/app_open.png"),"Open",lambda:self.save_list(items[0]))
        act.setDisabled( len(items) != 1 ) # in case selection is zero?

        act = menu.addAction(QIcon(":/img/app_save.png"),"Save",lambda:self.save_list(items[0]))
        act.setDisabled( len(items) != 1 ) # in case selection is zero?

        act = menu.addAction("Rename",lambda:self.rename_list(items[0]))
        act.setDisabled( len(items) != 1 ) # in case selection is zero?

        act = menu.addAction(QIcon(":/img/app_trash.png"),"Delete",lambda:self.delete_list(items[0]))
        act.setDisabled( len(items) != 1 ) # in case selection is zero?

        menu.exec_( event.globalPos() )

    def open_list(self,listname):
        self.openPlaylist.emit(listname);

    def save_list(self,listname):
        self.savePlaylist.emit(listname)

    def rename_list(self,listname):
        dialog = RenameDialog(listname,"Rename List")

        if dialog.exec_():
            name = dialog.text().strip()
            if name:
                self.renamePlaylist.emit(listname,name)

    def delete_list(self,listname):

        title = "Delete Playlist"
        msg = "Are you sure you want to delete `%s`."%listname
        # I would prefer to use "delete" and "cancel", but this does not seem to accept strings
        result = QMessageBox.warning(self, title, msg, QMessageBox.Ok, QMessageBox.Cancel)
        if result==QMessageBox.Ok:
            self.deletePlaylist.emit(listname)

class PlModel(object):
    def __init__(self,name,playlist,data):
        self.name = name
        self.playlist = playlist
        self.data = data
        self.dirty = False

class PlaylistTabView(QWidget):
    """docstring for PlaylistTabView"""
    defaultName="New Playlist"
    def __init__(self, parent=None):
        super(PlaylistTabView, self).__init__(parent)

        self.playlist_names = [ ]
        self.active_list = None # name of the current open playlist
        self.open_playlists = dict() # data name->model for all open playlists

        self.hbox = QHBoxLayout(self)

        self.splitter = QSplitter(Qt.Horizontal, self)

        self.tableList = SelectTable(self);
        self.viewEdit = PlaylistEditView(None,parent=self);

        self.splitter.addWidget(self.tableList.container)
        self.splitter.addWidget(self.viewEdit)
        self.hbox.addWidget(self.splitter)

        self.tableList.newPlaylist.connect(self.onNewPlaylist)
        self.tableList.openPlaylist.connect(self.onOpenPlaylist)
        self.tableList.savePlaylist.connect(self.onSavePlaylist)
        self.tableList.renamePlaylist.connect(self.onRenamePlaylist)
        self.tableList.deletePlaylist.connect(self.onDeletePlaylist)

        self.viewEdit.dirtyChanged.connect(self.onDirtyChanged)


        self._rule_act = lambda row: self.tableList.data[row][0] == self.active_list
        self.tableList.addRowTextColorComplexRule(self._rule_act,QColor(0,0,200))

        self._rule_open = lambda row: self.tableList.data[row][0] in self.open_playlists
        self.tableList.addRowTextColorComplexRule(self._rule_open,QColor(0,0,200))

        self.tableList.columns[-1].setTextTransform(self._rule_text)

        self.post_init()


    def _rule_text(self,r,x):
        if x in self.open_playlists and self.open_playlists[x].dirty:
            return x + "***"
        return x

    def post_init(self):
        # create a new empty playlist
        self.active_list = PlaylistTabView.defaultName
        pl = PlaylistManager.instance().openPlaylist(self.active_list)
        data = set()
        self.open_playlists[self.active_list] = PlModel(self.active_list,pl,data)
        self.viewEdit.setData(self.active_list,pl,data,False)
        self.refresh()

    def refresh(self):
        blacklist = ("current",)
        self.playlist_names = [ x for x in sorted(PlaylistManager.instance().names()) if x not in blacklist ]
        self.tableList.setData( [ [x,] for x in self.playlist_names ] )

    def onDirtyChanged(self,b):
        if self.active_list in self.open_playlists:
            self.open_playlists[self.active_list].dirty = b
        self.refresh()

    def onNewPlaylist(self):

        name = PlaylistTabView.defaultName
        count = 1
        while name in self.playlist_names:
            name = PlaylistTabView.defaultName + " (%d)"%count
            count += 1

        # create, but then open through normal means
        print(name)
        PlaylistManager.instance().openPlaylist(name)
        self.onOpenPlaylist(name)
        self.refresh()

    def onOpenPlaylist(self,name):

        n,_,d,r = self.viewEdit.getData();
        if n in self.open_playlists:
            print("saving data for "+n,len(d))
            self.open_playlists[n].data = d
            self.open_playlists[n].dirty = r

        if name not in self.open_playlists:
            print("open data for "+name)
            pl = PlaylistManager.instance().openPlaylist(name)
            data = set(pl.iter())
            model = PlModel(name,pl,data)
            self.open_playlists[name] = model
        else:
            model = self.open_playlists[name]
            print("restore data for "+name,len(model.data))

        self.viewEdit.setData(name,model.playlist,model.data,model.dirty)
        self.active_list = name

    def onSavePlaylist(self,name):
        model = self.open_playlists.get(name,None)
        if model is not None:
            print("Saving playlist `%s`"%name)
            model.playlist.set( list(model.data) )

    def onDeletePlaylist(self,name):

        PlaylistManager.instance().deletePlaylist(name)
        self.refresh()

    def onRenamePlaylist(self,old_name,new_name):
        print("boo")

        PlaylistManager.instance().renamePlaylist(old_name,new_name)
        self.refresh()

        if old_name not in self.open_playlists:
            return

        print("boo")

        # update the internal data model
        mdl = self.open_playlists[old_name]
        del self.open_playlists[old_name]
        self.open_playlists[new_name] = mdl

        if self.active_list == old_name:
            n,p,d,r = self.viewEdit.getData();
            self.viewEdit.setData(new_name,p,d,r)

    def setRuleColors(self,imp1,imp2,mid,special):

        self.viewEdit.tbl_lib.setRuleColors(imp1,imp2,mid,special)
        self.viewEdit.tbl_pl.setRuleColors(imp1,imp2,mid,special)

        self._rule_open = lambda row: self.tableList.data[row][0] in self.open_playlists
        self.tableList.setRowTextColorComplexRule(0,None,imp1)
        self.tableList.setRowTextColorComplexRule(1,None,imp2)
