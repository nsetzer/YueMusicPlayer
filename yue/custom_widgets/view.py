#! python2.7 ../../test/test_widget.py list
"""

a Tree View data structure

This Widget works on a model - view pattern

    1. subclasss ListElem or TreeElem to represent your data type
    2. Create a NodeWidget To create a view of an element
    3. The View Widget manages the layout. Users interact with the
       NodeWidgets and ViewWidget to change values in the given Element.

OTHER:
    TrackTreeElem is given as an example on how to represent individual
    songs in the tree view. each artist, album can be represented as
    a TreeElem, while each track can be represented as a TrackTreeElem.
    The TrackTreeElem holds a reference for the database id of a track.
    The user can make selections, then all selected tracks can be extracted
    to determine the playlist data.

    row height is a constant multiplier on font size.

TODO:

    the number of node widgets is fixed at widget creation

    ListView should support slide-right (to remove elements from the list)
        extend ViewWidget to pass touch.dx to the underlying Node.
        possibly check the directional vector for touch dx,dy to prevent
        diagonal swipes

    This View Widget is generalized as much as possible, but the primary
    goal is to only display a tree of artist/album/track. I should test
    that it works for other data representations
        For example, TreeViewWidget, could accept a factory function
        for TreeNodeWidget to display different kinds of rows.
      * If generalized a little more TreeViewWidget can be a generic Scroll class
        for faking display of large tables. Using a different factory
        function, displaying a flat list will be very easy.

    ListViewWidget needs some work. It was thrown together only to show
    that it could be done.

    font_size is fixed on widget creation

    gradient background on each node element.
        will help as a visual guide for which checkbox goes with which label
        Gradient should be a different color for each level,
            maybe darker towards the top of the tree.
            maybe different colors from a palette for every level

    This widget draws ontop of widgets that are above
        is there a way to layer widgets, or set a clipping region for drawing?
        see  ScissorPush,ScissorPop
        because this widget is such a hack, it may not work.
        add_widget(...,canvas=self.canvas) does not work
        maybe Stencil
        https://kivy.org/docs/api-kivy.graphics.stencil_instructions.html

    may need a mutex to lock scroll events

    swipe currently activates when the user drags the widget 1/6 of the width.
        this is probably not ideal for all devices.
        unsure how to decide width correctly.

    instead of the view deciding the row height, each node should determine
        the height it needs.
        for now: i have no interest in enabling each row to have a different height

    during a drag, if the user holds the item near the edge of the screen
        scroll the window.

    nodes/elems setData() can i move self.elem = elem and resize event
    to the parent implementation and only call super in the child classes?


"""

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse, Rectangle
from kivy.properties import ObjectProperty, NumericProperty
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.graphics.texture import Texture
from kivy.graphics.scissor_instructions import ScissorPush,ScissorPop
from kivy.animation import Animation
from kivy.logger import Logger

import kivy.metrics

from expander import Expander
from tristate import TriState, TriStateCheckBox

import time

class ListElem(object):
    """docstring for ListElem"""
    def __init__(self, text):
        super(ListElem, self).__init__()
        self.text = text # text to display
        self.offset_x = 0

    def __repr__(self):
        return "<%s(%s)>"%(self.__class__.__name__,self.text)

class TreeElem(ListElem):
    """data element """
    def __init__(self, text):
        super(TreeElem, self).__init__(text)
        self.expanded = False # if true, display children
        self.check_state = TriState.unchecked # whether element is selected
        self.children = []
        self.parent = None

    def addChild(self,child):
        self.children.append(child)
        child.parent = self
        return child

    def __getitem__(self,idx):
        return self.children[idx]

    def setChecked(self,state):

        self._setChecked(state)

        parent = self.parent
        while parent is not None:
            count_checked = 0
            count_partial = 0
            for child in parent.children:
                if child.check_state == TriState.checked:
                    count_checked += 1
                elif child.check_state == TriState.partial:
                    count_partial += 1
            if count_checked == len(parent.children):
                parent.check_state = TriState.checked
            elif count_partial + count_checked > 0:
                parent.check_state = TriState.partial
            else:
                parent.check_state = TriState.unchecked
            parent = parent.parent

    def _setChecked(self,state):
        self.check_state = state
        for child in self.children:
            child._setChecked(state)

    def depth(self):
        depth = 0
        node = self
        while node is not None:
            depth += 1
            node = node.parent
        return depth

class NodeWidget(Widget):
    """ represents a single row in a view """
    # TODO these properties need to be renamed
    # they no represent that absolute x position, instead of relative
    # together, they define where the user can touch to initiate scrolling
    pad_left = NumericProperty() # gutter, width of space before text label
    pad_right = NumericProperty() # gutter, width of space after text label

    def setData(self,elem):
        raise NotImplementedError()

    def resizeEvent(self,*args):
        if self.parent is not None:
            if self.elem is not None and not self.parent.scroll_disabled:
                self.x = self.elem.offset_x

    def swipe(self,elem_idx, dx):
        if self.elem is not None and self.parent is not None:
            self.elem.offset_x += dx
            self.resizeEvent()

            if self.elem.offset_x > self.parent.width/6 and not self.parent.scroll_disabled:
                self.parent.setScrollDisabled(True)
                tx = self.parent.x+self.parent.width
                self.anim = Animation(x=tx,t='out_quad',duration=.3)
                self.anim.on_complete = lambda w : self.on_complete(w,elem_idx)
                self.anim.start(self)
                self.elem.offset_x = 0

    def swipe_reset(self):
        if self.elem is not None and self.parent is not None:
            self.elem.offset_x = 0
            self.resizeEvent()

    def on_complete(self,widget,elem_idx):
        self.parent.setScrollDisabled(False)
        self.x = self.parent.x
        self.parent.swipeEvent(elem_idx,self.elem,"right")
        self.resizeEvent()

    def setData(self,data):
        raise NotImplementedError()

class ListNodeWidget(NodeWidget):
    """ represents a single row in a list view """

    def __init__(self, height=32, font_size = 12, **kwargs):
        super(ListNodeWidget, self).__init__(**kwargs)

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
        super(ListNodeWidget,self).resizeEvent(*args)
        # attempt to draw gradient (fails, not correct place)
        #self.canvas.clear() # TODO: instead of clear, remove only the rectangle
        #with self.canvas.before:
        #    Rectangle(pos=self.pos, size=self.size, texture=self.texture)

        self.lbl1.pos = self.pos
        self.lbl1.size = self.size
        self.lbl1.text_size = self.lbl1.size

        self.pad_left = self.x
        self.pad_right = self.x + self.width

class TreeNodeWidget(NodeWidget):
    """ represents a single row in a tree view """

    depth = NumericProperty() # nesting level of current element to display

    def __init__(self, height=32, font_size = 12, **kwargs):
        super(TreeNodeWidget, self).__init__(**kwargs)

        self.expandable = True;
        self.elem = None # current TreeElem to display

        # create a button for expanding / contracting the tree
        self.btn1 = Expander()
        self.add_widget(self.btn1,canvas=self.canvas)
        self.btn1.bind(on_user=self.on_expand)

        # This 'button' is reserved for an icon to differentiate artist, album, song
        self.btn2 = Button(text="-")
        self.add_widget(self.btn2,canvas=self.canvas)

        # Checkbox to select artists, albums or individual tracks
        self.chk1 = TriStateCheckBox()
        self.add_widget(self.chk1,canvas=self.canvas)
        self.chk1.bind(on_user=self.on_select)

        # TODO: need to use a japanese font for japanese characters,
        # e.g. DroidSansJapanese.ttf
        self.lbl1 = Label(text="",
                font_size = font_size,
                #font_name ="DroidSansJapanese",
                halign='left',
                valign='middle',
                markup=True,
                shorten = True) # truncate long lines
        self.add_widget(self.lbl1,canvas=self.canvas)

        self.height = height
        # example texture to  create a gradient in the background (doesnt work)
        #self.texture = Texture.create(size=(1, 2), colorfmt='rgb')
        #buf = bytearray([64,128,192,0,0,80])
        #self.texture.blit_buffer(buf, colorfmt='rgb', bufferfmt='ubyte')

        self.bind(size=self.resizeEvent)
        self.bind(pos=self.resizeEvent)
        self.resizeEvent()

    def resizeEvent(self,*args):

        # attempt to draw gradient (fails, not correct place)
        #self.canvas.clear() # TODO: instead of clear, remove only the rectangle
        #with self.canvas.before:
        #    Rectangle(pos=self.pos, size=self.size, texture=self.texture)

        third = self.height//3

        xoff = self.depth * third

        if self.expandable :
            self.btn1.x = xoff + third
            self.btn1.y = self.y

        self.btn2.x = xoff + 2*third + self.height
        self.btn2.y = self.y

        self.chk1.x = self.width - self.chk1.width
        self.chk1.y = self.y
        self.chk1.size = (self.height,self.height)

        self.btn1.size = (self.height,self.height)
        self.btn2.size = (self.height,self.height)
        lpad = 3*third + xoff + 2*self.height
        rpad = third + self.height

        self.lbl1.pos = (self.x + lpad,self.y)
        self.lbl1.size = (self.width - lpad - rpad,self.height)
        self.lbl1.text_size = self.lbl1.size

        self.pad_left = self.x + lpad
        self.pad_right = self.chk1.x

    def setExpandable(self,b):
        """ set that this node (TreeElem) should display the expansion btn """
        if not b:
            self.remove_widget(self.btn1)
        elif self.expandable != b:
            self.add_widget(self.btn1,canvas=self.canvas)

        self.expandable = b

    def setText(self,text):
        self.lbl1.text = text

    def setData(self,elem):
        """
        update this node to display a TreeElem

        elem : the element containing data to display
        """

        self.depth = elem.depth()
        self.setExpandable( len(elem.children)>0 )

        text = elem.text # repr(elem)
        if self.depth == 0:
            self.setText("[b]"+text+"[/b]")
        else:
            self.setText(text)

        self.btn1.expanded = elem.expanded
        self.chk1.state = elem.check_state
        self.elem = elem

        self.resizeEvent()

    def on_expand(self,*args):
        """ user clicked the expansion button """
        expanded = self.btn1.expanded
        if self.parent is not None and self.elem is not None:
            self.elem.expanded = expanded
            self.parent.update_labels()
            self.parent.resize()

    def on_select(self,*args):
        """ user clicked the tristate button """
        state = self.chk1.state
        if self.parent is not None and self.elem is not None:
            #self.parent.select(self.elem,state)
            self.elem.setChecked(state)
            self.parent.update_labels()

class ViewWidget(Widget):
    offset = NumericProperty()
    offset_idx = NumericProperty()
    offset_pos = NumericProperty()
    offset_max = NumericProperty(1000)

    def __init__(self, font_size, NodeFactory, **kwargs):
        super(ViewWidget, self).__init__(**kwargs)

        self.font_size = font_size
        self.node_factory = NodeFactory
        self.data = []

        self.bind(size=self.resize)
        self.bind(offset=self.on_update_offset)

        self.row_height = 1.5 * kivy.metrics.sp( font_size )
        self.nodes = []
        self.create_rows(20) # TODO resize based on height

        self.scroll_disabled = False

        self.register_event_type('on_tap')
        self.register_event_type('on_double_tap')
        self.register_event_type('on_drop')

        self.tap_max_duration = .2 # cutoff between a tap and press

    def setData(self, data):
        self.data = data
        self.update_labels()

    def create_rows(self,n):
        for i in range(n):
            nd = self.node_factory(height=self.row_height,
                             font_size = self.font_size );
            self.add_widget( nd,canvas=self.canvas )
            self.nodes.append( nd )

    def update_labels(self):
        raise NotImplementedError()

    def on_update_offset(self,*args):
        new_idx,self.offset_pos = divmod(self.offset,self.row_height)

        # update nodes to reflow information
        if new_idx != self.offset_idx:
            self.offset_idx = int(new_idx)

            self.update_labels()
        self.resize()

    def on_tap(self,index,*args):
        """ index into self.data where a tap occured """
        print("tap",index)

    def on_double_tap(self,index,*args):
        """ index into self.data where a tap occured """
        print("double tap",index)

    def on_drop(self,idx_from,idx_to,*args):
        """ index into self.data where a drag initiated and ended """
        Logger.info("drop: from %d to %d"%(idx_from,idx_to))

    def on_touch_down(self,touch):

        if self.nodes[0].pad_left < touch.x < self.nodes[0].pad_right and \
           self.x < touch.y < self.x + self.height and \
           not self.scroll_disabled:
            touch.grab(self)
            self._touch_last_index = -1 # see on_touch_move for usage
            self._touch_dy = 0 # measure y delta during touch
            self._touch_t_s = time.clock() # measure y delta during touch
            self._touch_drag = False
            self._touch_drag_idx = -1
            self._touch_token = None
            return True
        return super(ViewWidget, self).on_touch_down(touch)

    def on_touch_up(self,touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            idx = self.pos_to_row_index(*self.to_widget(*touch.pos))
            if 0 <= idx < len(self.nodes) and self.nodes[idx].parent is not None:
                self.nodes[idx].swipe_reset()

            # todo need to test that pixels scale correctly
            # to detect a tap, I may want to measure time
            #  e.g. if it is less than N milliseconds
            t = time.clock() - self._touch_t_s
            if self._touch_drag == True:
                # correct the index for drop targets
                if idx > len(self.data):
                    idx = len(self.data) - 1
                self.dispatch('on_drop',self._touch_drag_idx,idx)
            # arbitrary time in milliseconds
            elif self._touch_dy < self.row_height//3 and t < .2:
                if touch.is_double_tap:
                    self.dispatch('on_double_tap',idx)
                else:
                    self.dispatch('on_tap',idx)

            if self._touch_token is not None:
                self.remove_widget(self._touch_token)
                self._touch_token = None

        return super(ViewWidget, self).on_touch_up(touch)

    def on_touch_move(self,touch):
        if touch.grab_current is self:
            self._touch_dy += abs(touch.dy)
            idx = self.pos_to_row_index(*self.to_widget(*touch.pos))
            if not self._touch_drag and \
                self._touch_dy < self.row_height//3 and \
                time.clock() - self._touch_t_s > .2 and \
                0 <= idx < len(self.data):
                Logger.info("drag start: %d"%idx)
                self._touch_drag_idx = idx
                self._touch_drag = True
                self._touch_token = self.node_factory( height=self.row_height,
                                            font_size = self.font_size )
                self._touch_token.setData( self.data[idx] )
                self.add_widget( self._touch_token )

            if not self._touch_drag:
                o = self.offset + round(touch.dy)
                self.offset = max(0,min(self.offset_max,o))
                idx = self.pos_to_row_index(*self.to_widget(*touch.pos))

                if 0 <= idx < len(self.nodes):
                    if self.nodes[idx].parent is not None:
                        self.nodes[idx].swipe(self.offset_idx+idx,touch.dx)
                    # if a diagonal drag selects a different row,
                    # reset the previous row.
                    if idx != self._touch_last_index:
                        self.nodes[self._touch_last_index].swipe_reset()
                    self._touch_last_index = idx
            else:
                self._touch_token.x = touch.px - self._touch_token.width//2
                self._touch_token.y = touch.py - self._touch_token.height//2
            return True
        return super(ViewWidget, self).on_touch_move(touch)

    def swipeEvent(self,elem_idx, elem, direction):
        """ direction is one of : "left", "right" """
        Logger.info("swipe right event no implemented")
        print(elem_idx,elem,direction)

    def setScrollDisabled(self,b):
        self.scroll_disabled = b

    def _pad_top(self):
        h = self.height
        rh = self.row_height
        n = (h // rh)
        pad = h - n * rh + self.offset_pos
        return n,pad

    def pos_to_row_index(self,x,y):
        """ convert y-coordinate to index in self.nodes """
        n,pad = self._pad_top()
        return int( - ((y - pad) // self.row_height) + n - 1 )

    def resize(self,*args):
        """
        move child widgets into position to create the illusion of
        an scrolling tree view
        """
        #with self.canvas.before:
        #    # before children
        #    x,y = self.pos #self.to_window(*self.pos)
        #    #x,y = self.to_window(*self.pos)
        #    width, height = self.size
        #    ScissorPush(x=int(round(x)), y=int(round(y)),
        #                width=int(round(width)), height=int(round(height)))

        n , pad = self._pad_top()
        for i,nd in enumerate(self.nodes):
            if nd.parent is not None:
                nd.width = self.width
                nd.y = self.y + (n-i-1)*self.row_height + pad


        #with self.canvas.after:
            # after children
        #    ScissorPop()

    def scrollTo(self,idx):
        """ scroll widget so that idx is displayed """
        pass

class ListViewWidget(ViewWidget):

    def __init__(self, font_size = 12, NodeFactory=ListNodeWidget, **kwargs):
        super(ListViewWidget, self).__init__(font_size, NodeFactory, **kwargs)

    def update_labels(self):

        index = 0
        while index < len(self.nodes):
            idx = self.offset_idx + index
            if idx < len(self.data):
                if self.nodes[index].parent is None:
                    self.add_widget(self.nodes[index],canvas=self.canvas)
                self.nodes[index].setData(self.data[idx])
            else:
                break
            index += 1

        self.offset_max = max(0, (len(self.data)-1)*self.row_height)

        while index < len(self.nodes):
            self.remove_widget(self.nodes[index])
            index += 1

class TreeViewWidget(ViewWidget):

    def __init__(self, font_size = 12, **kwargs):
        super(TreeViewWidget, self).__init__(font_size, TreeNodeWidget, **kwargs)

    def update_labels(self):
        # walk the tree and determine visible elements
        # for each visible element update the node
        # TODO: this is rather inefficient because every update
        # requires walking the entire tree
        idx = 0
        for p,elem in enumerate(self.data):
            idx = self.update_labels_main(idx,elem)
            idx += 1
        # update the offset maximum, which controls the range over which
        # the widget can scroll to display rows from the tree view.
        # TODO: instead of -1, pick a number equal to about 1/3 of the
        # visible rows.
        self.offset_max = max(0, (idx-1)*self.row_height)

        # hide rows which are not used to display data
        index = idx - self.offset_idx
        while index < len(self.nodes):
            self.remove_widget(self.nodes[index])
            index += 1

    def update_labels_main(self,idx,elem):
        index = idx - self.offset_idx
        if 0 <= index < len(self.nodes):
            if self.nodes[index].parent is None:
                self.add_widget(self.nodes[index],canvas=self.canvas)
            self.nodes[index].setData(elem)
        if elem.expanded:
            for j,child in enumerate(elem.children):
                idx += 1
                idx = self.update_labels_main(idx,child)
        return idx

