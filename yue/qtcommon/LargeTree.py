#! python34 ../../../test/test_client.py $this

"""
TODO: after a certain depth there are graphical glitches
        that depend on font size
"""
import sys

from .Leaf import Leaf
from .LargeTable import LargeTable, TableColumn
isPython3 = sys.version_info[0]==3
if isPython3:
    unicode = str
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

class LargeTree(LargeTable):

    def __init__(self,parent=None):
        super(LargeTree,self).__init__(parent)
        self.columns = [ TreeColumn(self,Leaf.column_token,""), ] + self.columns
        self.columns[0].setWidthByCharCount(48)

        self.setSelectionRule(LargeTree.SELECT_ONE)

        self.setRowHeight(19)
        self.showRowHeader(False)

        self.checkable = False; # whether rows can be checked/unchecked
                               # checking enables multi select for a tree view

    def initColumns(self):
        pass # this disables the creation of a column by LargeTable

    def setRoot(self,root):
        self.root = root

        self.data = root.toList()

    def getRoot(self):
        return self.root

    def getCheckedItems(self):
        return self.root.getChecked()

class TreeColumn(TableColumn):

    def __init__(self,parent,index,name=None):
        super(TreeColumn,self).__init__(parent,index,name)
        self.text_transform = lambda row_item,cell_item : unicode(row_item.text)
        self.bool_display_root = True
        self.paint_control_width = 14; # width of drawing area for tree controls
        self.paint_image_scale = 1

        #self.text_transform = lambda r,i : "%04X : %d : %d : %s"%(r.fold,r.tempid,len(r.children),i)

    def painter_get_xmid(self,x,depth):

        offset = ((depth - (not self.bool_display_root) ) * self.paint_control_width)/2
        xmid = x +  self.paint_control_width//2 +(offset) + depth
        return offset,xmid

    def paintItem(self,col,painter,row,item,x,y,w,h):

        fnt_h = QFontMetrics(self.parent.font()).height()
        self.paint_image_scale = max(1,int(fnt_h/10))
        # 13 is not a magic number, it is the sum of all the x-offsets
        # due to all of the drawing below, for a scale of 1
        self.paint_control_width = 12*self.paint_image_scale

        row_item = self.parent.data[row]


        #for i in range(0,row_item.depth):
        #    offset = ((i - (not self.bool_display_root) ) * self.paint_control_width)/2
        #    xmid = x +  self.paint_control_width/2 +(offset)
        #    painter.drawLine(xmid,y+1,xmid,y+h-1)
        # get how much space the text should be offset by

        # THIS OFFSET CALC IS WRONG for FNOT H > 20

        offset , xmid = self.painter_get_xmid( x, row_item.depth  )
        ymid = y+(h//2)
        wxh = 0
        icon_offset_x=5
        icon_offset_y=2
        if row_item.icon != None or row_item.checkable:
            wxh_a = self.parent.row_height-1
            wxh_b = row_item.icon.height()
            wxh = min(wxh_a,wxh_b)
            icon_offset_x += (row_item.icon.width()-wxh+.5)//2
            icon_offset_y += (row_item.icon.height()-wxh+.5)//2
        ################################################
        # draw the icon

        if row_item.icon != None and not self.parent.checkable:
            x_ = x+offset+self.paint_control_width
            painter.drawPixmap(x_+icon_offset_x,y+icon_offset_y,wxh,wxh,row_item.icon)
        ################################################
        # draw text
        rr = 4*self.paint_image_scale # rect radius
        ri = 2*self.paint_image_scale # item radius
        rc = 5*self.paint_image_scale # check box radius
        sc = int((2.5*rr))            # check box start
        ss = self.paint_image_scale + 1 # scale + 1

        self.paintItem_text(col,painter,row,item,x+wxh+offset+self.paint_control_width+rr,y,w,h)

        # rect is ...
        # x+self.parent.row_height+(((row_item.depth - (not self.bool_display_root) ) * self.paint_control_width)/2)self.paint_control_width+1

        default_pen = painter.pen()
        linecolor = QPen(QColor(164,164,164))


        ################################################
        # draw the visual aid
        if (row_item.fold&(1<<Leaf.fold_HAS_CHILDREN) or row_item.folder_empty):
            # draw box
            painter.drawRect(xmid-rr,ymid-rr,2*rr,2*rr)
            #painter.setPen(linecolor)
            #painter.drawRect(xmid+-3,ymid-3,6,6)
            #painter.setPen(default_pen)
            # draw --
            if  row_item.collapsible and not row_item.folder_empty:
                # draw a minus when not empty
                painter.drawLine(xmid-ri,ymid,xmid+ri,ymid)
            if row_item.collapsible and  row_item.fold&(1<<Leaf.fold_COLLAPSED):
                # turn the minus into a plus
                painter.drawLine(xmid,ymid-ri,xmid,ymid+ri)
            elif not row_item.folder_empty:
                painter.setPen(linecolor)
                # draw 'has children and expanded' '7'
                painter.drawLine(xmid+(rr+1),ymid,xmid+(2*rr+1),ymid)
                painter.drawLine(xmid+(int(1.5*rr)+1),ymid,xmid+(int(1.5*rr)+1),y+h-1)
            # draw 'has sibling above', req'd
            painter.setPen(linecolor)
            if row_item.parent != None:
                painter.drawLine(xmid,y+1,xmid,ymid-(rr+1))
            # draw 'has sibling below'
            if row_item.fold&(1<<Leaf.fold_SIBLINGB):
                painter.drawLine(xmid,ymid+(rr+1),xmid,y+h-1)
        else:
            painter.setPen(linecolor)
            #  draw 'is'
            painter.drawLine(xmid,ymid,xmid+ri+1,ymid)
            # draw 'has sibling above'
            painter.drawLine(xmid,y+1,xmid,ymid)
            if row_item.fold&(1<<Leaf.fold_SIBLINGB):
                painter.drawLine(xmid,ymid,xmid,y+h-1)
        ################################################
        # if the widget needs check boxes
        if row_item.checkable and self.parent.checkable:
            # draw box
            painter.setPen(default_pen)
            painter.drawRect(xmid+sc,ymid-rc,2*rc+1,2*rc+1)
            painter.setPen(linecolor)
            #painter.drawRect(xmid+11,ymid-4,9,9)

            default_pen.setWidth(ss)
            painter.setPen(default_pen)
            if row_item._isChecked == Leaf.PARTIALLY_CHECKED:
                painter.fillRect(xmid+sc+ss,ymid-rc+ss,2*(rc-ss+1),2*(rc-ss+1),default_pen.color())
            elif row_item._isChecked == Leaf.CHECKED:
                painter.drawLine(xmid+(sc+1),ymid+2,xmid+(sc+1)+rc//2,ymid+rc)
                painter.drawLine(xmid+(sc+1)+rc//2,ymid+rc,xmid+sc+2*rc,ymid-(rc-1))
            default_pen.setWidth(1)
            painter.setPen(default_pen)
        ################################################
        # draw continuation decender for higher leaves
        painter.setPen(linecolor)
        i = row_item.depth-1
        p = row_item.parent
        while p != None:

            if p.fold&(1<<Leaf.fold_SIBLINGB):
                offset , xmid = self.painter_get_xmid( x, i )
                painter.drawLine(xmid,y+1,xmid,y+h-1)
            p = p.parent
            i -= 1;
        painter.setPen(default_pen)

    def mouseHover(self,row_index,posx,posy):
        #print posx,posy
        if row_index  < len(self.parent.data):
            row_item = self.parent.data[int(row_index)]
            depth = row_item.depth
        #print depth,posx,posy
        return False

    def mouseClick(self,row_index,posx,posy):

        row_index = int(row_index)
        rr = 4*self.paint_image_scale # rect radius
        ri = 2*self.paint_image_scale # item radius
        rc = 5*self.paint_image_scale # check box radius
        sc = int((2.5*rr)) # check box start

        if row_index  < len(self.parent.data):
            row_item = self.parent.data[row_index]
            if row_item == None: return False;
            depth = row_item.depth
            offset , xmid = self.painter_get_xmid( 0, depth)

            #if row_item.collapsible and xmid - (rr+1) < posx < xmid + (rr+1): # mouse on the expander
            if row_item.collapsible and 0 < posx < xmid + (rr+1): # mouse on the expander
                if row_item.hasChildren():
                    row_item.collapsed = not row_item.collapsed
                    self.parent.setData( self.parent.root.toList() )
                return True
            #elif row_item.checkable and self.parent.checkable and xmid + sc < posx < xmid + 2*rc+1: # mouse click box
            elif row_item.checkable and self.parent.checkable and  xmid + (rr+1) < posx < xmid + sc + 2*rc+1: # mouse click box

                #row_item.toggleChecked();
                row_item.setCheckState(not row_item.isChecked(),True);

                return True

        return False

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    table = LargeTree()
    table.setLastColumnExpanding(True)

    leaf = Leaf()

    # insert a number of leaves into the existing tree
    p = leaf
    for i in range(10):
        p=Leaf(p,"-%d"%i,[])
        if i==4:
            q = p
            for j in range(6):
                q=Leaf(q,"-0-%d"%(j),[])
            q = p
            for j in range(6):
                q=Leaf(q,"-9-%f"%(j),[])

    # modify the root leaf
    leaf.text="Library"
    leaf.checkable = True
    leaf.collapsed = False
    leaf.collapsible = False
    table.setRoot(leaf)
    table.container.resize(640,320)
    table.container.show()
    table.checkable= True
    #table.setStyleSheet('font-size: 12pt;')

    sys.exit(app.exec_())

if __name__ == '__main__':


    main()
