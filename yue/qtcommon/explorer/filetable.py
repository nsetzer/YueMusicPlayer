
import os, sys, stat
import time
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from yue.qtcommon.LargeTable import LargeTable, TableColumn, TableDualColumn, TableColumnImage
from yue.qtcommon.TableEditColumn import EditColumn
from yue.qtcommon.ResourceManager import ResourceManager
from yue.qtcommon.explorer.jobs import Job, JobRunner, \
    RenameJob, CopyJob, MoveJob, DeleteJob, LoadDirectoryJob, \
    DropRequestJob, Dashboard, JobWidget

from yue.core.util import format_date, format_bytes, format_mode

from yue.core.explorer.source import DataSource, DirectorySource, SourceListView
from yue.core.explorer.ftpsource import parseFTPurl, FTPSource

from yue.core.song import Song

def exception_guard(fptr, table, index, what=""):
    # guard
    try:
        fptr(table[index])
    except FileNotFoundError as e:
        print("Exception Guard Unhandled Error:" + what + " - " + str(e))
        print(table[index])
    except Exception as e:
        print("Exception Guard Unhandled Error:" + what + " - " + str(e))
        print(table[index])

class ExplorerFileTable(LargeTable):
    """
    """
    renamePaths = pyqtSignal(object)  # given a list of jobs
    createFile = pyqtSignal(str)
    createDirectory = pyqtSignal(str)
    focusQuery = pyqtSignal()
    findFiles = pyqtSignal()
    findReplaceInFiles = pyqtSignal()
    deletePaths = pyqtSignal(list)  # list of items
    focusUp = pyqtSignal()
    editName = pyqtSignal()

    def __init__(self, view, parent=None):
        super(ExplorerFileTable, self).__init__(parent)
        self.view = view

        self.xcut_copy = QShortcut(QKeySequence(QKeySequence.Copy), self)
        self.xcut_copy.setContext(Qt.WidgetShortcut)
        self.xcut_copy.activated.connect(self.onShortcutCopy)

        self.xcut_cut = QShortcut(QKeySequence(QKeySequence.Cut), self)
        self.xcut_cut.setContext(Qt.WidgetShortcut)
        self.xcut_cut.activated.connect(self.onShortcutCut)

        self.xcut_paste = QShortcut(QKeySequence(QKeySequence.Paste), self)
        self.xcut_paste.setContext(Qt.WidgetShortcut)
        self.xcut_paste.activated.connect(self.onShortcutPaste)

        self.xcut_refresh = QShortcut(QKeySequence(QKeySequence.Refresh), self)
        self.xcut_refresh.setContext(Qt.WidgetShortcut)
        self.xcut_refresh.activated.connect(self.onShortcutRefresh)

        self.xcut_find = QShortcut(QKeySequence(QKeySequence.Find), self)
        self.xcut_find.setContext(Qt.WidgetShortcut)
        self.xcut_find.activated.connect(self.focusQuery.emit)

        self.xcut_edit = QShortcut(QKeySequence(Qt.CTRL + Qt.Key_E), self)
        self.xcut_edit.setContext(Qt.WidgetShortcut)
        self.xcut_edit.activated.connect(self.editName.emit)

        self.xcut_filter = QShortcut(QKeySequence(Qt.CTRL + Qt.SHIFT + Qt.Key_F), self)
        self.xcut_filter.setContext(Qt.WidgetShortcut)
        self.xcut_filter.activated.connect(self.findFiles.emit)

        self.xcut_replace = QShortcut(QKeySequence(Qt.CTRL + Qt.SHIFT + Qt.Key_H), self)
        self.xcut_replace.setContext(Qt.WidgetShortcut)
        self.xcut_replace.activated.connect(self.findReplaceInFiles.emit)

        # shortcuts must be disabled during editing
        self.xcuts_all = [self.xcut_copy, self.xcut_cut, self.xcut_paste,
                          self.xcut_refresh, self.xcut_filter]

        self.dragCompleted.connect(self.onShortcutRefresh)

        self.time_last_keypress = time.time()
        self.keysequence = ""

    def initColumns(self):
        """
        self.columns.append( TableColumnImage(self,'isDir',"Icon") )
        self.columns[-1].setShortName("")
        self.columns[-1].setTextTransform( lambda item,_ : self.item2img(item) )
        self.columns[-1].width = ResourceManager.instance().width() + 4 # arbitrary pad, image is centered

        self.columns.append( TableDualColumn(self,'name',"File Name") )
        self.columns[-1].setSecondaryTextTransform(lambda r,item : format_bytes(r['size']))
        """
        self.columns.append(TableColumnImage(self, 'type', "Icon"))
        self.columns[-1].setShortName("")
        self.columns[-1].setTextTransform(lambda item, _: self.item2img(item))
        self.columns[-1].width = ResourceManager.instance().width() + 4  # arbitrary pad, image is centered

        self.columns.append(EditTextColumn(self, 'name', "File Name"))
        self.columns[-1].setWidthByCharCount(35)
        self.columns[-1].commitText.connect(self._onCommitText)
        self.columns[-1].createFile.connect(self._onCreateFile)
        self.columns[-1].createDirectory.connect(self._onCreateDirectory)
        self.columns[-1].editorStart.connect(self.onEditorStart)
        self.columns[-1].editorFinished.connect(self.onEditorFinished)

        _rule1 = lambda item: "isHidden" in item or self.data.hidden(item['name'])
        rule1 = lambda row: exception_guard(_rule1, self.data, row, "is item hidden")
        self.addRowTextColorComplexRule(rule1, QColor(0, 0, 200))

        _rule2 = lambda item: item['isLink'] == DataSource.IS_LNK_BROKEN
        rule2 = lambda row: exception_guard(_rule2, self.data, row, "is item link")
        self.addRowTextColorComplexRule(rule2, QColor(200, 0, 0))

        _rule3 = lambda item: 'mode' in item and stat.S_IXUSR & item['mode'] and not item['isDir']
        rule3 = lambda row: exception_guard(_rule3, self.data, row, "is item dir")
        self.addRowTextColorComplexRule(rule3, QColor(30, 125, 45))

        self.columns.append(TableColumn(self, 'size', "Size"))
        self.columns[-1].setTextTransform(lambda item, _: format_bytes(item['size']))
        self.columns[-1].setTextAlign(Qt.AlignRight)
        self.columns[-1].setWidthByCharCount(7)

        self.columns.append(TableColumn(self, 'mtime', "Modified Date"))
        self.columns[-1].setTextTransform(lambda item, _: self.getFormatedDate(item))
        self.columns[-1].setShortName("Date")
        self.columns[-1].setDefaultSortReversed(True)
        self.columns[-1].setTextAlign(Qt.AlignRight)
        self.columns[-1].setWidthByCharCount(13)

        self.columns.append(TableColumn(self, 'mode', "Permissions"))
        self.columns[-1].setTextTransform(lambda _, v: format_mode(v))
        self.columns[-1].setShortName("Mode")
        self.columns[-1].setTextAlign(Qt.AlignRight)
        self.columns[-1].setWidthByCharCount(10)

    def onShortcutCopy(self):
        self.parent().controller.action_copy(self.parent(), self.getSelection())

    def onShortcutCut(self):

        self.parent().controller.action_cut(self.parent(), self.getSelection())

    def onShortcutPaste(self):

        self.parent().controller.action_paste(self.parent())

    def onShortcutRefresh(self):
        self.parent().refresh()

    def sortColumn(self, col_index):
        reverse = self.view.sort(self.columns[col_index].index, True)
        self.setSortColumn(col_index, -1 if reverse else 1)

    def selectionToMimeData(self):
        """
        return an instance of mimedata representing the current selection
        used when a drag is initiated from this
        """
        mimeData = MimeData()
        view = self.parent().view
        mimeData.setView(view)
        paths = []

        for row in self.selection:
            name = view[row]['name']
            path = view.realpath(name)
            paths.append(path)

        if view.islocal():
            urls = [QUrl.fromLocalFile(path) for path in paths]
            mimeData.setUrls(urls)
        else:
            mimeData.setText('\n'.join(paths))

        return mimeData

    def dragEnterEvent(self, event):

        print("==", self.parent().view.name())
        for f in event.mimeData().formats():
            print("\t", f)
            # print(event.mimeData().data(f))

        if event.mimeData().hasUrls():
            if event.source() is self:
                event.ignore()
                return
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            if event.source() is self:
                event.ignore()
                return
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):

        if event.mimeData().hasUrls():

            if event.source() is self:
                event.ignore()
                return

            urls = event.mimeData().urls()
            event.accept()

            src_view = None
            if event.mimeData().hasView():
                src_view = event.mimeData().view()

                if src_view.equals(self.parent().view) and \
                        src_view.pwd() == self.parent().view.pwd():
                    print("err drop same")
                    return

            # this might be  hack
            src = None
            if isinstance(event.source(), ExplorerFileTable):
                src = event.source().parent()

            self.parent().dropEvent(src, src_view, urls)

        else:
            event.ignore()

    def action_edit_column(self, row, col):
        opts = self.columns[col].get_default_opts(row)
        if opts:
            self.columns[col].editor_start(*opts)

    def mouseReleaseRight(self, event):
        self.parent().controller.contextMenu(
            event, self.parent(), self.getSelection())

    def mouseReleaseOther(self, event=None):

        # TODO: maintain a history, goback should go to previous
        # directory, and not the parent directory.
        if event is not None:
            if event.button() == Qt.XButton1:
                self.parent().chdir_prev()
            elif event.button() == Qt.XButton2:
                self.parent().chdir_next()
            else:
                print(event.button())

    def mouseDoubleClick(self, row, col, event=None):

        if event is None or event.button() == Qt.LeftButton:
            if 0 <= row < len(self.view):
                item = self.view[row]
                if item['isDir']:
                    self.open_child_directory(item)
                else:
                    self.parent().action_open_file(item)

    def open_child_directory(self, item):
        self.scrollTo(0)
        self.parent().chdir(item['name'])
        self.setSelection([])

    def item2img(self, item):
        return self.parent().item2img(item)

    def getFormatedDate(self, item):
        value = self.parent().getSlowData(item, "mtime")
        return format_date(value)

    def keyPressEvent(self, event=None):
        # focus up events allow for changing focus from
        # this table to whatever widget is above the table.
        if len(self.selection) == 1 and \
           list(self.selection)[0] == 0 and \
           event.key() == Qt.Key_Up:
            self.focusUp.emit()
        else:
            super(ExplorerFileTable, self).keyPressEvent(event)

    def keyPressOther(self, event):
        char = chr(event.key())
        if '0' <= char <= '9' or 'A' <= char <= 'Z' or char == " ":
            self.jump_to_letter(char)

    def keyPressDelete(self, event):
        if event.key() == Qt.Key_Backspace:
            self.parent().chdir_parent()
        else:
            self.deletePaths.emit(self.getSelection())

    def jump_to_letter(self, char):
        """
        select item in the list by typing a sequence of characters

        the first letter typed jumps to a file that begins with that letter
        subsequent letters will jump (Starting at that index) to any file
        that contains that sequence (including the file selected the first
        time).
        space will then jump between all files which match the current
        sequence.

        typing a letter after a timeout resets the sequence
        """
        time_current = time.time()

        if char != " ":
            if (time_current - self.time_last_keypress) > .5:
                self.keysequence = ""
            self.keysequence += char
            offset = list(self.selection)[0] if len(self.selection) else 0
        else:
            # TODO accessing self.selection is breaking a rule
            offset = 1 + list(self.selection)[0] if len(self.selection) else 0

        for idx in range(len(self.data)):
            item = self.data[(offset + idx) % len(self.data)]
            name = item['name'].upper()
            if len(self.keysequence) == 1 and name.startswith(self.keysequence) \
                    or (len(self.keysequence) > 1 and self.keysequence in name):
                sidx = (offset + idx) % len(self.data)
                self.setSelection([sidx, ])
                self.scrollTo(sidx)
                self.update()
                break

        self.time_last_keypress = time_current

    def onEditorStart(self):

        for xcut in self.xcuts_all:
            xcut.setEnabled(False)

    def onEditorFinished(self):

        for xcut in self.xcuts_all:
            xcut.setEnabled(True)

    def _onCommitText(self, jobs):
        self.renamePaths.emit(jobs)

    def _onCreateFile(self, name):
        self.createFile.emit(name)

    def _onCreateDirectory(self, name):
        self.createDirectory.emit(name)

    def update(self):
        # if self.parent().view:
        #    for x,c in self.parent().view._stat_data.items():
        #        print("    %4d"%c,x)
        #    self.parent().view._stat_data.clear()

        super().update()

class MimeData(QMimeData):
    custom_data = {}    # dictionary which houses the mimetype=>data
    custom_types = ["data/x-view", ]  # list of supported types

    def retrieveData(self, mimetype, prefered):
        if mimetype in self.custom_types:
            return self.custom_data.get(mimetype, None)
        else:
            return super(MimeData, self).retrieveData(mimetype, prefered)

    def hasFormat(self, mimetype):
        if mimetype in self.custom_types:
            return mimetype in self.custom_data
        else:
            return super(MimeData, self).hasFormat(mimetype)

    def formats(self):
        f = super(MimeData, self).formats()
        for key in self.custom_data.keys():
            f.append(key)
        return f

    def setView(self, view):
        self.custom_data['data/x-view'] = view

    def hasView(self):
        return 'data/x-view' in self.custom_data

    def view(self):
        return self.custom_data['data/x-view']

class EditTextColumn(EditColumn, QObject):
    # register a signal to update exif data when editing is done,.
    # this will enable searching on data that has been modified.
    commitText = pyqtSignal(object)  # given a list of jobs
    createFile = pyqtSignal(str)
    createDirectory = pyqtSignal(str)
    editorStart = pyqtSignal()
    editorFinished = pyqtSignal()

    def __init__(self, parent, index, name=None, data_type=str):
        EditColumn.__init__(self, parent, index, name, data_type)
        QObject.__init__(self, parent)
        # self.cell_modified.connect(self.editing_finished)

    def editor_start(self, rows, text, mode=0):
        self.edit_mode = mode
        super().editor_start(rows, text)
        self.editorStart.emit()

    def editor_save(self):
        """
            save the modified buffer to 'index; of each row in the data set
        """
        # print self.data_type,self.editor.buffer
        try:
            value = self.data_type(str(self.editor.buffer).strip())
        except:
            self.editor_close()
            return

        # TODO: this is now broken by the Load Dir Job
        ##changed = set()
        # for row in self.open_editors:
        ##    item = self.parent.data[row]
        # if item[self.index] != value:
        # changed.add(row)

        # only emits signals if a row changed, and only for rows
        # that did in fact change
        if self.edit_mode == 0:
            self.editing_rename_finished(self.open_editors, value)
        elif self.edit_mode == 1:
            self.editing_create_file_finished(self.open_editors, value)
        elif self.edit_mode == 2:
            self.editing_create_dir_finished(self.open_editors, value)

        self.parent.update()
        self.editor_close()

        # TODO: also broken for the same reason
        # if len(changed) > 0:
        # self.cell_modified.emit(changed,value)
        self.editorFinished.emit()
        return

    def editing_rename_finished(self, rows, new_value):
        # do the commit here,

        # todo: this should be done at a higher level
        jobs = []
        if len(rows) == 1:
            row = list(rows)[0]
            src_name = self.parent.data[row][self.index]
            if src_name != new_value:
                jobs.append((src_name, new_value))
        else:
            # TODO: need to use the view for this....
            # renaming multiple files to the same name is bad mmkay
            base_name, ext = os.path.splitext(new_value)

            for idx, row in enumerate(rows):
                src_name = self.parent.data[row][self.index]
                tgt_name = "%s (%d)%s" % (base_name, idx + 1, ext)
                if src_name != tgt_name:
                    jobs.append((src_name, tgt_name))

        # jobs contains a old_name.-> new_name map
        # that a view could act on to move files
        if len(jobs) > 0:
            self.commitText.emit(jobs)

    def editing_create_file_finished(self, rows, new_value):
        self.createFile.emit(new_value)

    def editing_create_dir_finished(self, rows, new_value):
        self.createDirectory.emit(new_value)
