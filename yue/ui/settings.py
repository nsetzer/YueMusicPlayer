
"""

screen that displays optional settings

e.g.
    font size,
    import / export library

"""
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label

from yue.settings import Settings
from yue.sound import SoundManager
from yue.library import Library

class SettingsScreen(Screen):
    def __init__(self,**kwargs):
        super(SettingsScreen,self).__init__(**kwargs)

        self.vbox = BoxLayout(orientation='vertical')
        self.add_widget(self.vbox)

        self.btn_home = Button(text="home")
        self.btn_home.bind(on_press=Settings.instance().go_home)
        self.vbox.add_widget( self.btn_home )
