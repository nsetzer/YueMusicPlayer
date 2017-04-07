
import os, sys

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from yue.client.widgets.LargeTable import LargeTable, TableColumn, TableDualColumn, TableColumnImage
from yue.client.widgets.TableEditColumn import EditColumn

from yue.client.widgets.explorer.jobs import Job, JobRunner, \
    RenameJob, CopyJob, MoveJob, DeleteJob, LoadDirectoryJob, \
    DropRequestJob, Dashboard, JobWidget

from yue.core.util import format_date, format_bytes, format_mode

from yue.core.explorer.source import DataSource,DirectorySource,SourceListView
from yue.core.explorer.ftpsource import parseFTPurl, FTPSource

from yue.core.song import Song

class ResourceManager(object):
    """docstring for ResourceManager"""
    _instance = None

    LINK      = 0x100
    DIRECTORY = 0x001
    FILE      = 0x002
    SONG      = 0x003
    ARCHIVE   = 0x004
    IMAGE     = 0x005
    MOVIE     = 0x006

    LINK_DIRECTORY = 0x101
    LINK_FILE      = 0x102
    LINK_SONG      = 0x103
    LINK_ARCHIVE   = 0x104
    LINK_IMAGE     = 0x105
    LINK_MOVIE     = 0x106

    @staticmethod
    def instance():
        # TODO: not thread safe....
        if ResourceManager._instance is None:
            ResourceManager._instance = ResourceManager()
        return ResourceManager._instance

    def __init__(self):
        super(ResourceManager, self).__init__()
        self.resources = {}
        self.resources[ResourceManager.FILE]      = QPixmap(':/img/app_file.png')
        self.resources[ResourceManager.SONG]      = QPixmap(':/img/app_song.png')
        self.resources[ResourceManager.DIRECTORY] = QPixmap(':/img/app_folder.png')
        self.resources[ResourceManager.ARCHIVE]   = QPixmap(':/img/app_archive.png')
        self.resources[ResourceManager.IMAGE]     = QPixmap(':/img/app_media.png')
        self.resources[ResourceManager.MOVIE]     = QPixmap(':/img/app_movie.png')

        self.img_link = QPixmap(':/img/app_shortcut.png')

        for res in [ResourceManager.FILE,ResourceManager.SONG,
                    ResourceManager.DIRECTORY,ResourceManager.ARCHIVE,
                    ResourceManager.IMAGE]:
            img = self.compose(self.resources[res],self.img_link)
            self.resources[ResourceManager.LINK|res] = img

        self.map_ext = dict()

        for ext in Song.supportedExtensions():
            self.map_ext[ext] = ResourceManager.SONG

        for ext in [".gz",".zip",".7z",".rar",".iz"]:
            self.map_ext[ext] = ResourceManager.ARCHIVE

        for ext in [".jpg",".png",".bmp",".jpeg"]:
            self.map_ext[ext] = ResourceManager.IMAGE

        for ext in [".avi",".mp4",".webm",".gif",".mkv"]:
            self.map_ext[ext] = ResourceManager.MOVIE

    def compose(self,imga,imgb):

        imgc = QImage(imga.size(), QImage.Format_ARGB32_Premultiplied);
        painter = QPainter(imgc);

        painter.setCompositionMode(QPainter.CompositionMode_Source);
        painter.fillRect(imgc.rect(), Qt.transparent);

        painter.setCompositionMode(QPainter.CompositionMode_SourceOver);
        painter.drawPixmap(0, 0, imga);

        painter.setCompositionMode(QPainter.CompositionMode_SourceOver);
        painter.drawPixmap(0, 0, imgb);

        painter.end();

        return QPixmap.fromImage(imgc);

    def get(self,kind):
        return self.resources[kind]

    def getExtType(self,ext):
        return self.map_ext.get(ext.lower(),ResourceManager.FILE)

    def width(self):
        return self.resources[ResourceManager.FILE].width()

class ExplorerFileTable(LargeTable):
    """
    """
    renamePaths = pyqtSignal(object) # given a list of jobs
    createFile = pyqtSignal(str)
    createDirectory = pyqtSignal(str)


    def __init__(self, view, parent=None):
        super(ExplorerFileTable,self).__init__(parent)
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

        self.dragCompleted.connect(self.onShortcutRefresh)

    def initColumns(self):

        """
        self.columns.append( TableColumnImage(self,'isDir',"Icon") )
        self.columns[-1].setShortName("")
        self.columns[-1].setTextTransform( lambda item,_ : self.item2img(item) )
        self.columns[-1].width = ResourceManager.instance().width() + 4 # arbitrary pad, image is centered

        self.columns.append( TableDualColumn(self,'name',"File Name") )
        self.columns[-1].setSecondaryTextTransform(lambda r,item : format_bytes(r['size']))
        """
        self.columns.append( TableColumnImage(self,'name',"Icon") )
        self.columns[-1].setShortName("")
        self.columns[-1].setTextTransform( lambda item,_ : self.item2img(item) )
        self.columns[-1].width = ResourceManager.instance().width() + 4 # arbitrary pad, image is centered

        self.columns.append( EditTextColumn(self,'name',"File Name") )
        self.columns[-1].setWidthByCharCount(35)
        self.columns[-1].commitText.connect(self._onCommitText)
        self.columns[-1].createFile.connect(self._onCreateFile)
        self.columns[-1].createDirectory.connect(self._onCreateDirectory)
        self.columns[-1].editorStart.connect(self.onEditorStart)
        self.columns[-1].editorFinished.connect(self.onEditorFinished)

        _rule1 = lambda item : "isHidden" in item or self.data.hidden(item['name'])
        rule1 = lambda row: _rule1(self.data[row])
        self.addRowTextColorComplexRule(rule1,QColor(0,0,200))

        _rule2 = lambda item : item['isLink'] == DataSource.IS_LNK_BROKEN
        rule2 = lambda row: _rule2(self.data[row])
        self.addRowTextColorComplexRule(rule2,QColor(200,0,0))

        self.columns.append( TableColumn(self,'size',"Size") )
        self.columns[-1].setTextTransform( lambda item,_ : format_bytes(item['size']) )
        self.columns[-1].setTextAlign(Qt.AlignRight)
        self.columns[-1].setWidthByCharCount(7)

        self.columns.append( TableColumn(self,'mtime',"Modified Date") )
        self.columns[-1].setTextTransform( lambda item,_ : self.getFormatedDate(item) )
        self.columns[-1].setShortName("Date")
        self.columns[-1].setDefaultSortReversed(True)
        self.columns[-1].setTextAlign(Qt.AlignRight)
        self.columns[-1].setWidthByCharCount(13)

        self.columns.append( TableColumn(self,'mode',"Permissions") )
        self.columns[-1].setTextTransform( lambda _,v : format_mode(v) )
        self.columns[-1].setShortName("Mode")
        self.columns[-1].setTextAlign(Qt.AlignRight)
        self.columns[-1].setWidthByCharCount(10)

    def onShortcutCopy(self):
        self.parent().controller.action_copy( self.parent(),self.getSelection() )

    def onShortcutCut(self):

        self.parent().controller.action_cut( self.parent(),self.getSelection() )

    def onShortcutPaste(self):

        self.parent().controller.action_paste( self.parent() )

    def onShortcutRefresh(self):
        self.parent().refresh()

    def sortColumn(self,col_index):
        reverse=self.view.sort(self.columns[col_index].index,True)
        self.setSortColumn(col_index,-1 if reverse else 1)

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
            urls = [ QUrl.fromLocalFile(path) for path in paths ]
            mimeData.setUrls(urls)
        else:
            mimeData.setText('\n'.join(paths))

        return mimeData

    def dragEnterEvent(self, event):

        print("==",self.parent().view.name())
        for f in event.mimeData().formats():
            print("\t",f)
            #print(event.mimeData().data(f))

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
            if isinstance(event.source(),ExplorerFileTable):
                src = event.source().parent()

            self.parent().dropEvent( src, src_view, urls )

        else:
            event.ignore()

    def action_edit_column(self, row, col):
        opts = self.columns[col].get_default_opts(row)
        if opts:
            self.columns[col].editor_start(*opts)

    def mouseReleaseRight(self,event):
        self.parent().controller.contextMenu( event, self.parent(), self.getSelection() )

    def mouseReleaseOther(self,event=None):

        # TODO: maintain a history, goback should go to previous
        # directory, and not the parent directory.
        if event is not None:
            if event.button()==Qt.XButton1:
                self.parent().chdir_prev()
            elif event.button()==Qt.XButton2:
                self.parent().chdir_next()
            else:
                print(event.button())

    def mouseDoubleClick(self,row,col,event=None):

        if event is None or event.button() == Qt.LeftButton:
            if 0<= row < len(self.view):
                item = self.view[row]
                if item['isDir']:
                    self.open_child_directory(item)
                else:
                    self.parent().action_open_file( item )

    def open_child_directory(self,item):
        self.scrollTo( 0 )
        self.parent().chdir( item['name'] )
        self.setSelection([])

    def item2img(self,item):
        return self.parent().item2img( item )

    def getFormatedDate(self,item):
        value = self.parent().getSlowData(item,"mtime")
        return format_date(value)

    def onEditorStart(self):

        for xcut in [self.xcut_copy,self.xcut_cut,
                     self.xcut_refresh,self.xcut_paste]:
            xcut.setEnabled(False)

    def onEditorFinished(self):
        for xcut in [self.xcut_copy,self.xcut_cut,
                     self.xcut_refresh,self.xcut_paste]:
            xcut.setEnabled(True)

    def _onCommitText(self,jobs):
        self.renamePaths.emit(jobs)

    def _onCreateFile(self,name):
        self.createFile.emit(name)

    def _onCreateDirectory(self,name):
        self.createDirectory.emit(name)

    def update(self):
        #if self.parent().view:
        #    for x,c in self.parent().view._stat_data.items():
        #        print("    %4d"%c,x)
        #    self.parent().view._stat_data.clear()

        super().update()


class MimeData(QMimeData):
    custom_data = {}    # dictionary which houses the mimetype=>data
    custom_types= ["data/x-view",] # list of supported types

    def retrieveData(self,mimetype,prefered):
        if mimetype in self.custom_types:
            return self.custom_data.get(mimetype,None);
        else:
            return super(MimeData,self).retrieveData(mimetype,prefered)

    def hasFormat (self, mimetype):
        if mimetype in self.custom_types:
            return mimetype in self.custom_data
        else:
            return super(MimeData,self).hasFormat(mimetype)

    def formats(self):
        f = super(MimeData,self).formats()
        for key in self.custom_data.keys():
            f.append(key)
        return f

    def setView(self,view):
        self.custom_data['data/x-view'] = view

    def hasView(self):
        return 'data/x-view' in self.custom_data

    def view(self):
        return self.custom_data['data/x-view']

class EditTextColumn(EditColumn,QObject):
    # register a signal to update exif data when editing is done,.
    # this will enable searching on data that has been modified.
    commitText = pyqtSignal(object) # given a list of jobs
    createFile = pyqtSignal(str)
    createDirectory = pyqtSignal(str)
    editorStart = pyqtSignal()
    editorFinished = pyqtSignal()

    def __init__(self,parent,index,name=None,data_type=str):
        EditColumn.__init__(self,parent,index,name,data_type)
        QObject.__init__(self,parent)
        #self.cell_modified.connect(self.editing_finished)

    def editor_start(self,rows,text,mode=0):
        self.edit_mode = mode
        super().editor_start(rows,text)
        self.editorStart.emit()

    def editor_save(self):
        """
            save the modified buffer to 'index; of each row in the data set
        """
        #print self.data_type,self.editor.buffer
        try:
            value = self.data_type(str(self.editor.buffer).strip())
        except:
            self.editor_close()
            return

        ## TODO: this is now broken by the Load Dir Job
        ##changed = set()
        ##for row in self.open_editors:
        ##    item = self.parent.data[row]
        ##    if item[self.index] != value:
        ##        changed.add(row)


        # only emits signals if a row changed, and only for rows
        # that did in fact change
        if self.edit_mode == 0:
            self.editing_rename_finished(self.open_editors,value)
        elif self.edit_mode==1:
            self.editing_create_file_finished(self.open_editors,value)
        elif self.edit_mode==2:
            self.editing_create_dir_finished(self.open_editors,value)

        self.parent.update()
        self.editor_close()

        # TODO: also broken for the same reason
        ##if len(changed) > 0:
        ##    self.cell_modified.emit(changed,value)
        self.editorFinished.emit()
        return

    def editing_rename_finished(self,rows,new_value):
        # do the commit here,

        # todo: this should be done at a higher level
        jobs = []
        if len(rows) == 1:
            row = list(rows)[0]
            src_name = self.parent.data[row][self.index]
            if src_name != new_value:
                jobs.append( (src_name,new_value) )
        else:
            # TODO: need to use the view for this....
            # renaming multiple files to the same name is bad mmkay
            base_name, ext = os.path.splitext(new_value)

            for idx,row in enumerate(rows):
                src_name = self.parent.data[row][self.index]
                tgt_name = "%s (%d)%s"%(base_name,idx+1,ext)
                if src_name != tgt_name:
                    jobs.append( (src_name,tgt_name) )

        # jobs contains a old_name.-> new_name map
        # that a view could act on to move files
        if len(jobs) > 0:
            self.commitText.emit(jobs)

    def editing_create_file_finished(self,rows,new_value):
        self.createFile.emit(new_value)

    def editing_create_dir_finished(self,rows,new_value):
        self.createDirectory.emit(new_value)
