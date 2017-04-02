
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from yue.client.widgets.LargeTree import LargeTree
from yue.client.widgets.Leaf import Leaf
from yue.core.settings import Settings
class ShortcutEditDialog(QDialog):
    """docstring for ShortcutEditDialog"""
    def __init__(self, qpath, ipath, lpath, parent=None):
        super(ShortcutEditDialog, self).__init__(parent)

        self.vbox=QVBoxLayout(self)
        self.vbox.setContentsMargins(16,0,16,0)

        self.grid = QGridLayout()
        self.grid.addWidget(QLabel("qpath"),0,0)
        self.grid.addWidget(QLabel("ipath"),1,0)
        self.grid.addWidget(QLabel("lpath"),2,0)

        self.edit_qpath = QLineEdit(self)
        self.edit_qpath.setText(qpath)
        self.cbox_ipath = QComboBox(self)
        # dont make the cbox editable, instead, have an option for custom and
        # then insert a line edit below for the custom path
        #self.cbox_ipath.setEditable(True)
        supported_icons = [
            (":/img/app_folder.png","Folder"),
            (":/img/app_fav.png","Favorite"),
        ]
        for i,(p,t) in enumerate(supported_icons):
            self.cbox_ipath.addItem(QIcon(p),t,p)
            if ipath == p:
                self.cbox_ipath.setCurrentIndex(i)

        self.edit_lpath = QLineEdit(self)
        self.edit_lpath.setText(lpath)

        self.grid.addWidget(self.edit_qpath,0,1)
        self.grid.addWidget(self.cbox_ipath,1,1)
        self.grid.addWidget(self.edit_lpath,2,1)

        self.btn_accept = QPushButton("Save",self)
        self.btn_cancel = QPushButton("Cancel",self)

        self.btn_accept.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

        self.hbox_btns = QHBoxLayout()
        self.hbox_btns.setContentsMargins(0,0,0,0)
        self.hbox_btns.addStretch(1)
        self.hbox_btns.addWidget(self.btn_accept)
        self.hbox_btns.addWidget(self.btn_cancel)

        self.vbox.addLayout(self.grid)
        self.vbox.addLayout(self.hbox_btns)

    def getSpecifierString(self):

        qpath = self.edit_qpath.text()
        ipath = self.cbox_ipath.currentData()
        lpath = self.edit_lpath.text()

        return '='.join([qpath,ipath,lpath])

class QuickAccessTable(LargeTree):

    changeDirectory = pyqtSignal(str)
    changeDirectoryRight = pyqtSignal(str)

    def __init__(self, parent=None):
        super(QuickAccessTable,self).__init__(parent)

        self.setLastColumnExpanding( True )
        self.showColumnHeader( False )
        self.showRowHeader( False )
        self.checkable = False

        self.refreshData()

    def mouseReleaseRight(self,event):

        mx = event.x()
        my = event.y()
        cx,cy = self._mousePosToCellPos(mx,my)
        row,cur_c = self.positionToRowCol(mx,my)

        path = None
        child = self.root
        if row < len(self.data):
            child = self.data[row]
            path = child.data

        menu = QMenu(self)

        if path:
            act = menu.addAction("Open Directory (Left Side)", lambda : self.action_chdir(path,False))
            act = menu.addAction("Open Directory (Right Side)", lambda : self.action_chdir(path,True))
            menu.addSeparator()

        act = menu.addAction("Refresh",self.refreshData)
        act = menu.addAction("Collapse All",self.collapse_all)
        act = menu.addAction("Expand All",self.expand_all)
        menu.addSeparator()

        act = menu.addAction("Add Shortcut",lambda : self.action_add_child(child))
        if path:
            menu.addAction("Edit Shortcut",lambda : self.action_edit_child(child))
        else:
            menu.addAction("Edit Group",lambda : self.action_edit_child(child))
        menu.addAction("Remove Shortcut",lambda : self.action_remove_child(child))

        action = menu.exec_( event.globalPos() )

    def refreshData(self):

        # convert the data to a tree
        root = Leaf(None,"Quick Access",None)

        items = Settings.instance()['quick_access_paths']
        for item in items:
            # qpath : path in the quick list
            # ipath : internal resource or file path for the icon
            # lpath : localpath for the shortcut
            qpath,ipath,lpath = item.split("=",3)
            child = root
            for dname in qpath.split("/")[1:]:
                child.collapsed = False
                child = child.getChild(dname)
                if not hasattr(child,ipath):
                    child.ipath=""
                    child.data=""

            child.data = lpath
            child.ipath = ipath
            child.setIcon(QPixmap(ipath))

        root.checkable = False
        root.collapsed = False
        root.collapsible = False
        self.setRoot(root)

    def keyPressRight(self,event):
        row = self.selection_last_row_added
        item = self.data[row]
        if item.hasChildren() and item.collapsed:
            item.collapsed = False
            self.setData( self.root.toList() )
            self.update();

    def keyPressLeft(self,event):
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

    def mouseDoubleClick(self,row,posx,posy):
        if row >= len(self.data):
            return
        item = self.data[row]
        path = item.data
        if path:
            self.changeDirectory.emit(path)

    def action_chdir(self,path,on_right):

        if on_right:
            self.changeDirectoryRight.emit(path)
        else:
            self.changeDirectory.emit(path)

    def collapse_all(self):
        self.root.collapse_all();
        self.root.collapsed = False
        self.setData( self.root.toList() )
        self.update();

    def expand_all(self):
        self.root.expand_all();
        self.setData( self.root.toList() )
        self.update();

    def action_add_child(self, node):
        # node is the currently selected node in the tree

        qpath=node.path(1)
        ipath=node.ipath
        lpath=node.data
        data = '='.join([qpath,ipath,lpath])
        print(data)

        dialog = ShortcutEditDialog(qpath,ipath,lpath,self)
        accept = dialog.exec_()

        if accept:
            new_spec = dialog.getSpecifierString()
            q,_,_ = new_spec.split("=")
            items = Settings.instance()['quick_access_paths']
            for item in items:
                p,_,_ = item.split("=")
                if p==q:
                    break
            else:
                items.append(new_spec)
                Settings.instance()['quick_access_paths'] = items
                self.refreshData()
        # each child has a file-like path name
        # and a system level file path
        return

    def action_edit_child(self, node):
        # node is the currently selected node in the tree
        # if node is not a leaf, changing it could modify many shortcuts
        print(type(node),node)
        qpath=node.path(1)
        ipath=node.ipath
        lpath=node.data
        print(node,"<%s>"%node.ipath)
        old_spec = '='.join([qpath,ipath,lpath])

        dialog = ShortcutEditDialog(qpath,ipath,lpath,self)
        accept = dialog.exec_()

        if accept:
            new_spec = dialog.getSpecifierString()

            items = Settings.instance()['quick_access_paths']
            print(old_spec,new_spec)

            for i in range(len(items)):
                if items[i] == old_spec:
                    items[i] = new_spec
                    Settings.instance()['quick_access_paths'] = items
                    break
            else:
                # this path does not exist for some reason, so add it
                items.append(new_spec)
                Settings.instance()['quick_access_paths'] = items

            self.refreshData()
        return

    def action_remove_child(self, node):

        print(type(node),node)
        qpath=node.path(1)
        ipath=node.ipath
        lpath=node.data
        old_spec = '='.join([qpath,ipath,lpath])

        items = Settings.instance()['quick_access_paths']
        i=0
        while i < len(items):
            item=items[i]
            p,_,_ = item.split("=")
            if p==qpath:
                items.pop(i)
                Settings.instance()['quick_access_paths'] = items
                self.refreshData()
                return
            i+=1
