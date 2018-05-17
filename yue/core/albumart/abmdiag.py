#! python $this

import os
import sys
import argparse


from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from ..song import Song
from ..sqlstore import SQLStore
from ..library import Library
from ..playlist import PlaylistManager
from ...client.ui.art_view import AlbumArtView
from ...qtcommon.LibraryTree import LibraryTree

from .getart import img_search_google, img_retrieve



class ArtLibraryTree(LibraryTree):
    """docstring for ArtLibraryTree"""

    search_rule = pyqtSignal(object)

    def __init__(self, parent=None):
        super(ArtLibraryTree, self).__init__(parent)

        self.selection_changed.connect(self.onSelectionChanged)

    def onSelectionChanged(self):

        if not self.isAlbumSelected():
            rule = None
        else:
            rule = self.formatSelectionAsQueryString()

        self.search_rule.emit(rule)

class FlowLayout(QLayout):

    # https://forum.qt.io/topic/11938/solved-flowlayout-in-a-qscrollarea
    # http://doc.qt.io/qt-5/qtwidgets-layouts-flowlayout-example.html
    def __init__(self, margin=-1, hSpacing=-1, vSpacing=-1, parent=None):
        super(FlowLayout, self).__init__()

        self.setContentsMargins(margin,margin,margin,margin)

        self._itemList = []
        self._hSpace = hSpacing
        self._vSpace = vSpacing
        self._margin = 4 if margin < 0 else margin

    def addItem(self, item):
        print(item)
        self._itemList.append(item)

    def horizontalSpacing(self):

        if self._hSpace >= 0 :
            return self._hSpace
        return self._smartSpacing(QStyle.PM_LayoutHorizontalSpacing)

    def verticalSpacing(self):

        if self._vSpace >= 0 :
            return self._vSpace
        return self._smartSpacing(QStyle.PM_LayoutVerticalSpacing)

    def expandingDirections(self):

        return 0;

    def hasHeightForWidth(self):

        return True;

    def heightForWidth(self, width):

        return self._doLayout(QRect(0,0,width,0), True)

    def count(self):

        return len(self._itemList)

    def itemAt(self, index):

        if index >= 0 and index < len(self._itemList):
            return self._itemList[index]
        return None

    def minimumSize(self):

        size = QSize()

        for item in self._itemList:
            size = size.expandedTo(item.minimumSize())

        size += QSize(2*self._margin, 2*self._margin)

        return size

    def setGeometry(self, rect):

        super().setGeometry(rect)
        self._doLayout(rect, False)

    def sizeHint(self):

        return self.minimumSize()

    def takeAt(self, index):

        if index >= 0 and index < len(self._itemList):
            return self._itemList.pop(index)
        return None

    def _doLayout(self, rect, testOnly):

        l,t,r,b = self.getContentsMargins()

        effective = rect.adjusted(l,t,-r,-b)
        x = effective.x()
        y = effective.y()
        lineHeight = 0

        for item in self._itemList:
            widget = item.widget()
            spaceX = self.horizontalSpacing()
            if spaceX == -1:
                spaceX = widget.style().layoutSpacing(
                    QSizePolicy.PushButton, QSizePolicy.PushButton,
                    Qt.Horizontal)
            spaceY = self.verticalSpacing()
            if spaceY == -1:
                spaceY = widget.style().layoutSpacing(
                    QSizePolicy.PushButton, QSizePolicy.PushButton,
                    Qt.Horizontal)

            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > effective.right() and lineHeight > 0:
                x = effective.x()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0

            if not testOnly:
                item.setGeometry(QRect(QPoint(x,y), item.sizeHint()))

            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())

        return y + lineHeight - rect.y() + b

    def _smartSpacing(self, pm):

        parent = self.parent()

        if parent is None:
            return -1

        elif isinstance(parent, QWidget):
            return parent.style().pixelMetric(pm, None, parent)

        else:
            # is layout
            return parent.spacing()

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()

        self.setWindowTitle("Roke")

        if sys.platform == "darwin":
            self.setUnifiedTitleAndToolBarOnMac(True)

        self.toolbar = QToolBar(self)
        self.toolbar.setMovable(False)
        self.toolbar.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.addToolBar(self.toolbar)

        self.btn_options = self.toolbar.addAction(self._makeOptionsIcon(), "Options",
            self.showOptionDialog)
        self.btn_options.setToolTip("Manage Roke Options")

        self.splitter = QSplitter(Qt.Horizontal, self)

        self.setCentralWidget(self.splitter)

        self.table = ArtLibraryTree(self)
        self.table.refreshData()
        self.table.search_rule.connect(self.onSearchRuleChanged)

        self._defaultArt = self._makeDefaultAlbumArt()
        self.artview = AlbumArtView(self)
        self.artview.setFixedHeight(128)
        self.artview.setFixedWidth(128)
        self.artview.setDefaultArt(self._defaultArt)

        self.pane_left = QWidget(self)
        self.vbox_left = QVBoxLayout(self.pane_left)
        self.vbox_left.addWidget(self.table.container)
        self.vbox_left.addWidget(self.artview)

        self.pane_right = QWidget(self)
        self.vbox_right = QVBoxLayout(self.pane_right)
        self.hbox_right = QHBoxLayout()
        self.edit_search = QLineEdit(self)
        self.btn_search = QPushButton("Search", self)
        # self.flow = QVBoxLayout()
        self.flow = FlowLayout()
        self.scroll_widget = QWidget(self)
        self.scroll_search = QScrollArea(self)
        self.scroll_search.setWidget(self.scroll_widget)
        self.scroll_search.setWidgetResizable(True)
        self.scroll_search.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll_search.widget().setLayout(self.flow)

        self.vbox_right.addLayout(self.hbox_right)
        self.vbox_right.addWidget(self.scroll_search)
        self.hbox_right.addWidget(self.edit_search)
        self.hbox_right.addWidget(self.btn_search)


        self.splitter.addWidget( self.pane_left )
        self.splitter.addWidget( self.pane_right )

        for i in range(14):
            lbl = QLabel("A" * (i+1), self)
            self.flow.addWidget(lbl)
            lbl.show()
        self.flow.update()

    def _makeOptionsIcon(self):
        # no icon? make an icon!
        # 3 horizontal bars, "hamburger icon" to open the options
        pixmap = QPixmap(64,64)
        pixmap.fill(QColor(0,0,0,0))
        painter = QPainter(pixmap)
        font = painter.font()
        font.setPixelSize(int(pixmap.height()*.75))
        painter.setFont(font)
        h=int(pixmap.height()/5)
        path= QPainterPath();
        path.addRoundedRect(0,0,pixmap.width(),h,h/2,h/2)
        path.addRoundedRect(0,h*2,pixmap.width(),h,h/2,h/2)
        path.addRoundedRect(0,h*4,pixmap.width(),h,h/2,h/2)
        scale = 0.8
        xt = (1-scale)*pixmap.height() / 2
        t = QTransform().translate(xt, xt).scale(scale,scale)
        painter.setTransform(t)
        painter.fillPath(path, Qt.black);
        painter.drawPath(path)
        painter.end()
        return QIcon(pixmap)

    def _makeDefaultAlbumArt(self):
        pixmap = QPixmap(128, 128)
        pixmap.fill(QColor(0,0,0,0))
        painter = QPainter(pixmap)
        font = painter.font()
        font.setPixelSize(int(pixmap.height()*.75))
        painter.setFont(font)
        w = pixmap.width()
        h=int(pixmap.height()/5)
        path= QPainterPath();
        path.addRoundedRect(w/2 - w/5,0, w/2 + w/5,h,h/2,h/2)
        path.addRoundedRect(0, w/2 - w/5, h, w/2 + w/5, h/2,h/2)
        scale = 0.8
        xt = (1-scale)*pixmap.height() / 2
        t = QTransform().translate(xt, xt).scale(scale,scale)
        painter.setTransform(t)
        painter.fillPath(path, Qt.black);
        painter.drawPath(path)
        painter.end()
        return pixmap

    def showOptionDialog(self):
        pass

    def onSearchRuleChanged(self, rule):

        song = {}
        if rule is not None:
            songs=Library.instance().search(rule, orderby=Song.album_index)
            if len(songs)>0:
                song = songs[0]

        self.artview.setArt(song)

def handle_exception(exc_type, exc_value, exc_traceback):
    for line in traceback.format_exception(exc_type, exc_value, exc_traceback):
        sys.stderr.write(line)

def main():

    parser = argparse.ArgumentParser(description='')

    parser.add_argument('db', type=str,
                        help='path to yue database')

    args = parser.parse_args()

    app = QApplication([sys.argv[0]])
    app.setQuitOnLastWindowClosed(True)

    sqlstore = SQLStore(args.db)
    Library.init(sqlstore)
    PlaylistManager.init( sqlstore )

    window = MainWindow()

    window.resize(768,512)
    window.show()

    sys.excepthook = handle_exception

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()