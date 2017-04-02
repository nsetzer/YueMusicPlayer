
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from yue.core.settings import Settings

from yue.client.widgets.explorer.controller import ExplorerController


class ExplorController(ExplorerController):

    def __init__(self):
        super(ExplorController,self).__init__()
        self.act_diff_left_path = None

    def contextMenu(self, event, model, items):

        is_files = all(not item['isDir'] for item in items)
        is_dirs  = all(item['isDir'] for item in items)

        ctxtmenu = QMenu(model)

        self._ctxtMenu_addFileOperations1(ctxtmenu,model,items)

        ctxtmenu.addSeparator()

        if model.view.islocal():
            if len(items) == 1:
                ctxtmenu.addAction("Edit", lambda : model.action_edit( items[0] ))

        ctxtmenu.addSeparator()

        if model.view.islocal() and Settings.instance()['cmd_diff_files']:
            ctxtmenu.addSeparator()

            if len(items) == 1:
                if self.act_diff_left_path is None:
                    ctxtmenu.addAction("Compare: Set Left", lambda : self.action_compare_set_left( model, items[0] ))
                else:
                    name = model.view.split(self.act_diff_left_path)[1]

                    ctxtmenu.addAction("Compare: Set Left", lambda : self.action_compare_set_left( model, items[0] ))
                    ctxtmenu.addAction("Compare to: %s"%name, lambda : self.action_compare( model, items[0] ))
            elif len(items) == 2:
                ctxtmenu.addAction("Compare 2 Items", lambda : self.action_compare_2( model, items ))

        self._ctxtMenu_addFileOperations2(ctxtmenu,model,items)

        if model.view.islocal():
            ctxtmenu.addAction(QIcon(":/img/app_open.png"),"Open in Explorer",model.action_open_directory)
            ctxtmenu.addAction("Open in Terminal",model.action_open_term)

        ctxtmenu.addAction("Refresh",model.action_refresh)

        action = ctxtmenu.exec_( event.globalPos() )

    def action_compare_set_left(self,model,item):
        self.act_diff_left_path = model.view.realpath(item['name'])

    def action_compare(self,model,item):

        lpath = self.act_diff_left_path
        rpath = model.view.realpath(item['name'])

        cmdstr = Settings.instance()['cmd_diff_files']
        cmd=cmdstr%(lpath,rpath)
        args=shlex.split(cmd)
        print(args)
        subprocess.Popen(args)

        self.act_diff_left_path = None

    def action_compare_2(self,model, items):

        lpath = model.view.realpath(items[0]['name'])
        rpath = model.view.realpath(items[1]['name'])

        cmdstr = Settings.instance()['cmd_diff_files']
        cmd=cmdstr%(lpath,rpath)
        args=shlex.split(cmd)
        print(args)
        subprocess.Popen(args)

        self.act_diff_left_path = None