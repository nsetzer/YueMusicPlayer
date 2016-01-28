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
from kivy.graphics import Color
from kivy.graphics.texture import Texture
from kivy.graphics import Color, Ellipse, Rectangle


from yue.custom_widgets.view import ListElem, NodeWidget, ListViewWidget

def fmttime(s):
    m,s = divmod(int(s),60)
    h,m = divmod(m,60)
    return "%02d:%02d:%02d"%(h,m,s)

class PlayListElem(ListElem):
    """ Tree Element with unique id reference to an item in a database """
    def __init__(self,uid,song):
        """ song as dictionary """
        text = song['artist'] + " - " + song['title']
        super(PlayListElem, self).__init__(text)
        self.title = song['title']
        self.artist = song['artist']
        self.length = fmttime(song['length'])
        self.uid = uid

class PlayListNodeWidget(NodeWidget):
    """docstring for PlayListNodeWidget"""
    def __init__(self, height=32, font_size = 12, **kwargs):
        super(PlayListNodeWidget, self).__init__(**kwargs)

        self.elem = None

        self.texture_default = Texture.create(size=(1, 2), colorfmt='rgb')
        buf = bytearray([135,135,135,135,135,200])
        self.texture_default.blit_buffer(buf, colorfmt='rgb', bufferfmt='ubyte')

        self.texture_highlight = Texture.create(size=(1, 2), colorfmt='rgb')
        buf = bytearray([100,100,100,100,100,240])
        self.texture_highlight.blit_buffer(buf, colorfmt='rgb', bufferfmt='ubyte')

        with self.canvas:

            self.rect_grad = Rectangle(texture=self.texture_default)

            self.lbl_title = Label(text="",
                                   font_size = font_size+1,
                                   halign='left',
                                   valign='middle',
                                   markup=True,
                                   shorten = True) # truncate long lines
            self.lbl_artist = Label(text="",
                                    font_size = font_size-1,
                                    halign='left',
                                    valign='middle',
                                    markup=True,
                                    shorten = True) # truncate long lines
            self.lbl_length = Label(text="",
                                    font_size = font_size,
                                    halign='right',
                                    valign='middle',
                                    markup=True,
                                    shorten = True) # truncate long lines
        self.add_widget(self.lbl_title,canvas=self.canvas)
        self.add_widget(self.lbl_artist,canvas=self.canvas)
        self.add_widget(self.lbl_length,canvas=self.canvas)

        self.height = 2 * height # given height is currently a suggestion

        self.bind(size=self.resizeEvent)
        self.bind(pos=self.resizeEvent)
        self.resizeEvent()

    def setData(self,elem,bgtexture=None):
        """
        update this node to display a TreeElem

        elem : the element containing data to display
        """
        self.elem = elem
        self.lbl_title.text = "[b]"+elem.title+"[/b]"
        self.lbl_artist.text = elem.artist
        self.lbl_length.text = elem.length
        # again, just hacking this feature for now
        if bgtexture :
            self.rect_grad.texture = self.texture_highlight
        else:
            self.rect_grad.texture = self.texture_default
        self.resizeEvent()

    def resizeEvent(self,*args):
        #super(PlayListNodeWidget, self).resizeEvent(*args)

        hpad = self.width/20
        self.lbl_title.x = self.x + hpad
        self.lbl_title.y = self.y + self.height // 2
        self.lbl_title.width = self.width - hpad
        self.lbl_title.height = self.height // 2
        self.lbl_title.text_size = self.lbl_title.size

        self.lbl_artist.x = self.x + hpad
        self.lbl_artist.y = self.y
        self.lbl_artist.width = self.width - hpad
        self.lbl_artist.height = self.height // 2
        self.lbl_artist.text_size = self.lbl_artist.size

        self.lbl_length.x = self.x + self.width - self.width//4
        self.lbl_length.y = self.y + self.height//4
        self.lbl_length.width = self.width//4 - hpad
        self.lbl_length.height = self.height // 2
        self.lbl_length.text_size = self.lbl_length.size

        self.rect_grad.size = self.size
        self.rect_grad.pos  = self.pos

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