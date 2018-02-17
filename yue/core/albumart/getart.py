import requests
import json
from bs4 import BeautifulSoup

from urllib.parse import quote
from urllib.request import urlopen, Request
import codecs

def img_search_google(album):
    '''
    google image search
    '''

    album = album + " Album Art"
    url = ("https://www.google.com/search?q=" +
           quote(album.encode('utf-8')) + "&source=lnms&tbm=isch")
    header = {'User-Agent':
              '''Mozilla/5.0 (Windows NT 6.1; WOW64)
              AppleWebKit/537.36 (KHTML,like Gecko)
              Chrome/43.0.2357.134 Safari/537.36'''
             }

    soup = BeautifulSoup(urlopen(Request(url, headers=header)), "html.parser")

    albumart_div = soup.find("div", {"class": "rg_meta"})
    albumart = json.loads(albumart_div.text)["ou"]

    with codecs.open("result.html","w", "utf-8") as wf:
        wf.write(json.dumps(albumart_div.text, sort_keys=True,
                            indent=4, separators=(',', ': ')))

    return albumart

def main():
    print(img_search_google("stone temple pilots core"))

if __name__ == '__main__':
    main()
