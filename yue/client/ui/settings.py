#! python34 ../../../test/test_client.py $this

import os,sys

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from yue.client.widgets.LargeTable import LargeTable, TableColumn
from yue.client.widgets.TableEditColumn import EditColumn
from yue.core.sqlstore import SQLStore
from yue.core.search import ruleFromString, ParseError
from yue.client.SymTr import SymTr


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

        self.tabview.addTab(self.tab_preset, "Presets")

    def import_settings(self,settings):

        self.tab_preset.import_settings( settings )

    def export_settings(self,settings):

        self.tab_preset.export_settings( settings )


class SettingsPresetTab(QWidget):
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

        settings["playlist_preset_default"] = self.getDefaultPresetIndex()
        names,queries = self.getData()
        settings["playlist_preset_names"] = names
        settings["playlist_presets"] = queries

    def setData(self, names, queries):

        data = [ [x,y] for x,y in zip(names,queries) ]
        self.table.setData(data)
        for idx,query in enumerate(queries):
            if not validate_query( query ):
                self.table.parse_error_rows.add(idx)

    def getData(self):
        names   = [ x[0] for x in self.table.data ]
        queries = [ x[1] for x in self.table.data ]
        return names, queries

    def setDefaultPresetIndex(self, index):
        self.table.default_row = index

    def getDefaultPresetIndex(self):
        return self.table.default_row

class SettingsPresetTable(LargeTable):
    """docstring for SettingsPresetTable"""
    def __init__(self, parent=None):
        super(SettingsPresetTable, self).__init__(parent)
        self.setLastColumnExpanding( True )
        self.showColumnHeader( True )
        self.showRowHeader( True )
        self.setSelectionRule(LargeTable.SELECT_ONE)

        # TODO: this does not work if sorting is enabled, need
        # another way to store default internally
        self.default_row = 0

        self.parse_error_rows = set()
        self.rule_error = lambda row : row in self.parse_error_rows
        self.rule_default = lambda row : row == self.default_row

        self.addRowHighlightComplexRule(self.rule_error,QColor(240,75,75))
        self.addRowTextColorComplexRule(self.rule_default,QColor(30,75,240))

    def initColumns(self):
        self.columns.append( EditColumn(self,0 ,"Name") )
        self.columns[-1].setWidthByCharCount(30)
        self.columns.append( PresetEditColumn(self,1 ,"Query") )

    def mouseReleaseRight(self,event):

        index = self.getSelectionIndex()

        contextMenu = QMenu(self)

        print(index)
        # file manipulation options
        act = contextMenu.addAction("New Preset", self.action_new)
        act = contextMenu.addAction("Delete Preset", lambda : self.action_delete( index ))
        act.setDisabled( index is None or len(self.data) == 1 )

        contextMenu.addSeparator()

        act = contextMenu.addAction("Set Default", lambda : self.setDefaultPresetIndex( index ))
        act.setDisabled( index == self.default_row )

        action = contextMenu.exec_( event.globalPos() )

    def action_new(self):
        self.data.append( ["New Preset", ""] )
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
            if not validate_query( new_value ):
                self.parent.parse_error_rows.add(row)
            elif row in self.parent.parse_error_rows:
                self.parent.parse_error_rows.remove(row)

    def editor_insert(self,chara):
        # enable japanese character input
        self.editor.insert(chara)
        o = SymTr.SymTr(self.editor.buffer)
        if o.nstring != self.editor.buffer:
            self.editor.buffer = o.nstring
            self.editor.insert_index=o.position

def validate_query(query):
    try:
        ruleFromString(query)
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