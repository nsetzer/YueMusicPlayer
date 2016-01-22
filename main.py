#!/usr/bin/python
__version__ = "1.0"

from yue.app import YueApp

# to play music while the app is in the background i need
# a background service
#https://kivy.org/planet/2014/01/building-a-background-application-on-android-with-kivy/

YueApp().run()
