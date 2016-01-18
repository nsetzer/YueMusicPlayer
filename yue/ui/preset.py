
"""
display a list of 'preset' / 'dynamic' playlist options

selecting a preset should go to the prest modifier screen.
which displays the set of selected songs as a tree view,
and allows for modifying the preset, creating a playist

e.g.
    songs that have not been played in the last two weeks.
    artist of the day
    album of the day

TODO:
    after writing 'preset' everywhere, i want to change it to
        'Dynamic Playlists'

"""
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label

from yue.settings import Settings
from yue.sound import SoundManager
from yue.library import Library

class PresetScreen(Screen):
    def __init__(self,**kwargs):
        super(PresetScreen,self).__init__(**kwargs)

        self.vbox = BoxLayout(orientation='vertical')
        self.add_widget(self.vbox)

        self.btn_home = Button(text="home")
        self.btn_home.bind(on_press=Settings.instance().go_home)
        self.vbox.add_widget( self.btn_home )


class ModifyPresetScreen(Screen):
    def __init__(self,**kwargs):
        super(ModifyPresetScreen,self).__init__(**kwargs)

        self.vbox = BoxLayout(orientation='vertical')
        self.add_widget(self.vbox)

        self.btn_home = Button(text="home")
        self.btn_home.bind(on_press=Settings.instance().go_home)
        self.vbox.add_widget( self.btn_home )

