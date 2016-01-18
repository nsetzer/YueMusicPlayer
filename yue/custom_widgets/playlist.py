#! python2.7 ../../test/test_widget.py playlist

"""

todo:
    i want each row to display two lines of text, artist, title
    artist should be bold.
    title may need to be tabbed in a small amount
    left side a square should be reserved for album art. square has
    a height equal to the two lines of text

    touch a row and drag should swap elements

    touching a row should display two buttons, side by side for moving
    the element, up or down in the list.

    swiping right deletes an element from the list

    support album art

"""

from kivy.uix.label import Label


from yue.custom_widgets.view import ListElem, NodeWidget, ListViewWidget

class PlayListElem(ListElem):
    """ Tree Element with unique id reference to an item in a database """
    def __init__(self,uid,song):
        """ song as dictionary """
        text = song['artist'] + " - " + song['title']
        super(PlayListElem, self).__init__(text)
        self.uid = uid

class PlayListNodeWidget(NodeWidget):
    """docstring for PlayListNodeWidget"""
    def __init__(self, height=32, font_size = 12, **kwargs):
        super(PlayListNodeWidget, self).__init__(**kwargs)

        self.elem = None

        self.lbl1 = Label(text="",
                    font_size = font_size,
                    halign='left',
                    valign='middle',
                    markup=True,
                    shorten = True) # truncate long lines
        self.add_widget(self.lbl1,canvas=self.canvas)

        self.height = height

        self.bind(size=self.resizeEvent)
        self.bind(pos=self.resizeEvent)
        self.resizeEvent()

    def setText(self,text):
        self.lbl1.text = text

    def setData(self,elem):
        """
        update this node to display a TreeElem

        elem : the element containing data to display
        """
        self.elem = elem
        self.setText( elem.text )
        self.resizeEvent()

    def resizeEvent(self,*args):
        super(PlayListNodeWidget, self).resizeEvent(*args)

        self.lbl1.pos = self.pos
        self.lbl1.size = self.size
        self.lbl1.text_size = self.lbl1.size

        self.pad_left = self.x
        self.pad_right = self.x + self.width


class PlayListViewWidget(ListViewWidget):
    """docstring for PayListView"""

    def __init__(self, font_size = 12, **kwargs):
        super(PlayListViewWidget, self).__init__(font_size, NodeFactory=PlayListNodeWidget, **kwargs)

    def swipeEvent(self,elem_idx, elem,direction):
        """ direction is one of : "left", "right" """
        del self.data[elem_idx]
        self.update_labels()