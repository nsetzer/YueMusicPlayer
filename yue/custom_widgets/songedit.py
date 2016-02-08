#! python2.7 ../../test/test_widget.py songinfo

from kivy.uix.label import Label

from yue.custom_widgets.view import ListElem, NodeWidget, ListViewWidget

class SongInfoElem(ListElem):
    """ Tree Element with unique id reference to an item in a database """
    def __init__(self, column, field, value):
        """ song as dictionary """
        super(SongInfoElem, self).__init__(column)
        self.column = column
        self.field = field
        self.value = unicode(value)

class SongNodeWidget(NodeWidget):
    """docstring for PlayListNodeWidget"""
    def __init__(self, height=32, font_size = 12, **kwargs):
        super(SongNodeWidget, self).__init__(**kwargs)

        self.elem = None

        #self.texture_default = Texture.create(size=(1, 2), colorfmt='rgb')
        #buf = bytearray([135,135,135,135,135,200])
        #self.texture_default.blit_buffer(buf, colorfmt='rgb', bufferfmt='ubyte')

        #self.texture_highlight = Texture.create(size=(1, 2), colorfmt='rgb')
        #buf = bytearray([100,100,100,100,100,240])
        #self.texture_highlight.blit_buffer(buf, colorfmt='rgb', bufferfmt='ubyte')

        with self.canvas:

            #self.rect_grad = Rectangle(texture=self.texture_default)

            self.lbl_field = Label(text="",
                                   font_size = font_size+1,
                                   halign='left',
                                   valign='middle',
                                   markup=True,
                                   shorten = True) # truncate long lines
            self.lbl_value = Label(text="",
                                    font_size = font_size-1,
                                    halign='left',
                                    valign='middle',
                                    markup=True,
                                    shorten = True) # truncate long lines
        self.add_widget(self.lbl_field,canvas=self.canvas)
        self.add_widget(self.lbl_value,canvas=self.canvas)

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
        self.lbl_field.text = elem.field
        self.lbl_value.text = elem.value
        # again, just hacking this feature for now
        #if bgtexture :
        #    self.rect_grad.texture = self.texture_highlight
        #else:
        #    self.rect_grad.texture = self.texture_default
        self.resizeEvent()

    def resizeEvent(self,*args):
        #super(PlayListNodeWidget, self).resizeEvent(*args)

        hpad = self.width/20
        self.lbl_field.x = self.x + hpad
        self.lbl_field.y = self.y + self.height // 2
        self.lbl_field.width = self.width - hpad
        self.lbl_field.height = self.height // 2
        self.lbl_field.text_size = self.lbl_field.size

        self.lbl_value.x = self.x + hpad
        self.lbl_value.y = self.y
        self.lbl_value.width = self.width - hpad
        self.lbl_value.height = self.height // 2
        self.lbl_value.text_size = self.lbl_value.size

        #self.rect_grad.size = self.size
        #self.rect_grad.pos  = self.pos

        self.pad_left = self.x
        self.pad_right = self.x + self.width

class SongEdit(ListViewWidget):
    """docstring for PayListView"""

    def __init__(self, song, row_height=None, font_size = 12, **kwargs):
        super(SongEdit, self).__init__(font_size, NodeFactory=SongNodeWidget, row_height=row_height, **kwargs)

        columns = ["artist","composer", "album","title","length","genre","playcount","year","country","lang","comment",]
        data = []
        for column in columns:
            data.append( SongInfoElem( column, column, song[column] ))

        self.enable_drag_and_drop = False
        self.setData(data)

