#! python2.7 $this

import os, sys
dirpath = os.path.dirname(os.path.abspath(__file__))
dirpath = os.path.dirname(dirpath)
sys.path.insert(0,dirpath)


from yue.core.song import read_tags


path = r"D:\Music\Japanese\SAWA\The Death March\05.  DOO.mp3"
song = read_tags(path)

print(song)