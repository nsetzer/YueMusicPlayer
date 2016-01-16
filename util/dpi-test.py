#! python2.7 $this

"""
launch application with simulated pixel densities and dpi.
"""

import os,sys

# https://kivy.org/docs/api-kivy.metrics.html#kivy.metrics.MetricsBase.density

#os.environ['KIVY_DPI'] = "72"
#os.environ['KIVY_METRICS_DENSITY'] = "1"
#size = "1280x720"

# HTC One X
#os.environ['KIVY_DPI'] = "320"
#os.environ['KIVY_METRICS_DENSITY'] = "2"
#size = "1280x720"

# Motorola Droid 2
os.environ['KIVY_DPI'] = "240"
os.environ['KIVY_METRICS_DENSITY'] = "1.5"
size = "854x480"

os.chdir("..")

os.system("C:\\python27\\python.exe main.py --size %s"%size)