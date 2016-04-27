#! python34 ../../../test/test_client.py $this

import os,sys

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from yue.client.widgets.LargeTable import LargeTable, TableColumn
from yue.client.widgets.TableEditColumn import EditColumn
from yue.core.song import SongSearchGrammar
from yue.core.sqlstore import SQLStore
from yue.core.search import ParseError
from yue.client.SymTr import SymTr

from yue.client.style import currentStyle


class SettingsDialog(QDialog):
    def __init__(self,parent=None):
        super(SettingsDialog,self).__init__(parent);
        self.setWindowTitle("Settings")
        self.resize(640,480)

        self.vbox_main = QVBoxLayout(self)
        self.hbox_main = QHBoxLayout()

        self.tabview = QTabWidget( self )
        self.btn_accept = QPushButton("Save Changes",self)
        self.btn_cancel = QPushButton("cancel",self)

        self.hbox_main.addWidget(self.btn_accept)
        self.hbox_main.addWidget(self.btn_cancel)
        self.vbox_main.addWidget(self.tabview)
        self.vbox_main.addLayout(self.hbox_main)

        self.btn_accept.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

        self.tab_preset = SettingsPresetTab(self)
        self.tab_music  = SettingsMusicTab(self)

        self.tabview.addTab(self.tab_preset, "Presets")
        self.tabview.addTab(self.tab_music, "Music")

    def import_settings(self,settings):

        self.tab_preset.import_settings( settings )

    def export_settings(self,settings):

        self.tab_preset.export_settings( settings )

class SettingsTab(QWidget):

    def import_settings(self,settings):
        raise NotImplementedError()

    def export_settings(self,settings):
        raise NotImplementedError()

class SettingsMusicTab(SettingsTab):
    """docstring for SettingsPresetTab"""
    def __init__(self, parent=None):
        super(SettingsMusicTab, self).__init__(parent)

        self.vbox = QVBoxLayout( self )
        self.hbox_size = QHBoxLayout( )

        self.spin_size = QSpinBox(self)
        self.spin_size.setRange(10,200)
        self.hbox_size.addWidget(QLabel("Default Playlist Size:"))
        self.hbox_size.addWidget(self.spin_size)

        self.table = SettingsMusicPrefixTable()
        self.chk_prefix = QCheckBox("Allow Relative Paths",self)

        self.vbox.addLayout(self.hbox_size)
        self.vbox.addWidget(self.chk_prefix)
        self.vbox.addWidget(QLabel("Path Prefix Alternatives:",self))
        self.vbox.addWidget(self.table.container)

class SettingsMusicPrefixTable(LargeTable):
    """docstring for SettingsMusicPrefixTable"""
    def __init__(self, parent=None):
        super(SettingsMusicPrefixTable, self).__init__(parent)
        self.setLastColumnExpanding( True )
        self.showColumnHeader( True )
        self.showRowHeader( False )
        self.setSelectionRule(LargeTable.SELECT_ONE)

    def initColumns(self):
        self.columns.append( EditColumn(self,0 ,"Prefix") )
        self.columns[-1].setTextTransform( lambda _,s : s if s else "<New Prefix>" )

    def mouseReleaseRight(self,event):

        index = self.getSelectionIndex()

        contextMenu = QMenu(self)

        act = contextMenu.addAction("New Prefix", self.action_new)
        act = contextMenu.addAction("Delete Prefix", lambda : self.action_delete( index ))
        act.setDisabled( index is None )

        action = contextMenu.exec_( event.globalPos() )

    def action_new(self):
        self.data.append( ["",] )
        self.update()

    def action_delete(self,index):
        self.data.pop(index)
        self.update()

class SettingsPresetTab(SettingsTab):
    """docstring for SettingsPresetTab"""
    def __init__(self, parent=None):
        super(SettingsPresetTab, self).__init__(parent)

        self.vbox = QVBoxLayout( self )
        self.table = SettingsPresetTable( self )

        self.vbox.addWidget( self.table.container )

    def import_settings(self,settings):
        """ set values from a key/value store """
        row = settings["playlist_preset_default"]
        names = settings["playlist_preset_names"]
        queries = settings["playlist_presets"]

        self.setData(names,queries)
        self.setDefaultPresetIndex(row)

    def export_settings(self,settings):
        """ update values in a key/value store """

        names,queries,index = self.getData()
        settings["playlist_preset_default"] = index
        settings["playlist_preset_names"] = names
        settings["playlist_presets"] = queries

    def setData(self, names, queries):

        data = [ [i,x,y] for i,(x,y) in enumerate(zip(names,queries)) ]
        self.table.setData(data)
        for idx,query in enumerate(queries):
            if not validate_query( query ):
                self.table.parse_error_rows.add(idx)
        self.table.next_index = len(data)

    def getData(self):
        names = []
        queries = []
        index=0
        # translate the given index (i), which is arbitrary
        # into the index that will be saved in the table
        for idx,(i,n,q) in enumerate(self.table.data):
            names.append(n)
            queries.append(q)
            if i == self.table.default_row:
                index = idx
        return names, queries, index

    def setDefaultPresetIndex(self, index):
        self.table.default_row = index

class SettingsPresetTable(LargeTable):
    """docstring for SettingsPresetTable"""
    def __init__(self, parent=None, qdctpalette=None):
        super(SettingsPresetTable, self).__init__(parent)
        self.setLastColumnExpanding( True )
        self.showColumnHeader( True )
        self.showRowHeader( False )
        self.setSelectionRule(LargeTable.SELECT_ONE)

        # TODO: this does not work if sorting is enabled, need
        # another way to store default internally
        self.default_row = 0
        self.next_index = 0

        self.parse_error_rows = set()
        self.rule_error = lambda row : self.data[row][0] in self.parse_error_rows
        self.rule_default = lambda row : self.data[row][0] == self.default_row

        qdct = currentStyle()
        if qdct:
            #self.addRowHighlightComplexRule(self.rule_error,qdct['color_invalid'])
            self.addRowTextColorComplexRule(self.rule_default,qdct['text_important1'])
            self.addRowTextColorComplexRule(self.rule_error,qdct['color_invalid'])
        else:
            self.addRowTextColorComplexRule(self.rule_default,QColor(30,75,240))
            self.addRowTextColorComplexRule(self.rule_error,QColor(240,75,75))

    def initColumns(self):
        #self.columns.append( EditColumn(self,0 ,"Index") )
        #self.columns[-1].setTextTransform( lambda _,i : str(i+1) )
        #self.columns[-1].setWidthByCharCount(10)
        self.columns.append( EditColumn(self,1 ,"Name") )
        self.columns[-1].setWidthByCharCount(20)
        self.columns.append( PresetEditColumn(self,2 ,"Query") )
        self.columns[-1].setTextTransform( lambda _,i : i if i else "<Blank Search>")

    def mouseReleaseRight(self,event):

        index = self.getSelectionIndex()

        contextMenu = QMenu(self)

        act = contextMenu.addAction("New Preset", self.action_new)
        act = contextMenu.addAction("Delete Preset", lambda : self.action_delete( index ))
        act.setDisabled( index is None or len(self.data) == 1 )

        contextMenu.addSeparator()

        act = contextMenu.addAction("Set Default", lambda : self.action_setindex( index ))
        act.setDisabled( index is not None and self.data[index][0] == self.default_row )

        action = contextMenu.exec_( event.globalPos() )

    def action_setindex(self,index):
        self.default_row = self.data[index][0]

    def action_new(self):
        self.data.append( [self.next_index,"New Preset", ""] )
        self.next_index += 1
        self.update()

    def action_delete(self,index):
        self.data.pop(index)
        if self.default_row >= len(self.data):
            self.default_row = len(self.data) - 1
        self.update()

class PresetEditColumn(EditColumn):
    # register a signal to update exif data when editing is done,.
    # this will enable searching on data that has been modified.
    def __init__(self,parent,index,name=None,data_type=str):
        super(PresetEditColumn,self).__init__(parent,index,name,data_type)
        self.cell_modified.connect(self.editing_finished)

    def editing_finished(self,rows,new_value):

        for row in rows: # SHOULD have ZERO or ONE elements
            idx = self.parent.data[row][0]
            if not validate_query( new_value ):
                self.parent.parse_error_rows.add( idx )
            elif row in self.parent.parse_error_rows:
                self.parent.parse_error_rows.remove( idx  )

    def editor_insert(self,chara):
        # enable japanese character input
        self.editor.insert(chara)
        o = SymTr.SymTr(self.editor.buffer)
        if o.nstring != self.editor.buffer:
            self.editor.buffer = o.nstring
            self.editor.insert_index=o.position

def validate_query(query):
    try:
        SongSearchGrammar().ruleFromString(query)
    except ParseError as e:
        sys.stdout.write("%s\n"%e)
        return False
    return True

def main():

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    db_path = "./yue.db"
    sqlstore = SQLStore(db_path)

    window = SettingsDialog()

    names   = [ "default", "test1"]
    queries = [ "length < 14", "woah" ]
    window.tab_preset.setData(names,queries)

    window.show()

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()