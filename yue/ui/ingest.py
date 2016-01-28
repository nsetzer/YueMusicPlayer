
"""

screen that is displayed while searching the file system
for music to add to the library.

on first time use (before there is a database) this should
be the default home screen.

by default, scan the entire sdcard for supported file types

for the first time, after ~ 50 songs are found, build a playlist
and jump to now playing while this runs in the background. display
a pop up message that his is happening. maybe ask the user if it
is ok to jump.

allowing the user to use the app while loading creates a few ui issues
    a map is needed for 'artist' -> TreeElem, so that the library
    view can be updated.
    when calling settings go_library, the screen would need to be updated.
    this will inevitably slow down the loading process.

need a way to prevent duplicates, paths are case sensitive on linux,
    so matching by path should be sufficient. a hash table works
    but a bloom filter may be better.

"""
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.clock import mainthread
from kivy.logger import Logger
from kivy.lib import osc

from yue.settings import Settings
from yue.library import Library
from yue.sqlstore import SQLStore

from threading import Thread
import traceback
import os
import time


class IngestScreen(Screen):
    def __init__(self,**kwargs):
        super(IngestScreen,self).__init__(**kwargs)

        self.vbox = BoxLayout(orientation='vertical')
        self.add_widget(self.vbox)

        self.lbl_dirname = Label(text="/")
        self.lbl_count   = Label(text="#") # display number of keys found

        self.btn_start = Button(text="start")
        self.btn_start.bind(on_press=self.start_ingest)

        self.btn_home = Button(text="home")
        self.btn_home.bind(on_press=Settings.instance().go_home)

        self.vbox.add_widget( self.btn_start )
        self.vbox.add_widget( self.lbl_dirname )
        self.vbox.add_widget( self.lbl_count )
        self.vbox.add_widget( self.btn_home )

    def start_ingest(self,*args):

        self.vbox.remove_widget( self.btn_start )
        #self.vbox.remove_widget( self.btn_home )
        #self.thread = Ingest(self,  )
        #self.thread.start()
        data = [Settings.instance().default_ingest_path,]
        port = Settings.instance().service_info.serviceport
        print("ingest start",data,port)
        osc.sendMsg('/ingest_start', dataArray=data, port=port)

    @mainthread
    def update_labels(self,dirname,count):
        self.lbl_dirname.text = dirname
        self.lbl_count.text = count

    @mainthread
    def ingest_finished(self):
        self.vbox.add_widget( self.btn_start, index = 4 )
        #self.vbox.add_widget( self.btn_home , index = 0 )

