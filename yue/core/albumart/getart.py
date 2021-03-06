import json
from bs4 import BeautifulSoup

from urllib.parse import quote
from urllib.request import urlopen, Request
import ssl

def img_search_google(query):

    enc = quote(query.encode('utf-8'))
    url = "https://www.google.com/search?q=%s&source=lnms&tbm=isch" % enc

    header = {
        'User-Agent': "Mozilla/5.0 (Windows NT 6.1; WOW64)" +
                      " AppleWebKit/537.36 (KHTML,like Gecko)" +
                      " Chrome/43.0.2357.134 Safari/537.36"
    }

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    response = urlopen(Request(url, headers=header), context=ctx)
    soup = BeautifulSoup(response, "html.parser")

    g = soup.findAll("div", {"class": "rg_meta"})
    art_results = []
    for i, albumart_div in enumerate(g):

        dat = json.loads(albumart_div.text)

        art_results.append({
          "width": dat['ow'],
          "height": dat['oh'],
          "url": dat['ou'],
        })

    return art_results

def img_retrieve(url):

    header = {
        'User-Agent': "Mozilla/5.0 (Windows NT 6.1; WOW64)" +
                      " AppleWebKit/537.36 (KHTML,like Gecko)" +
                      " Chrome/43.0.2357.134 Safari/537.36"
    }

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    response = urlopen(Request(url, headers=header), context=ctx)
    return response.read()

def main():
    images = img_search_google("stone temple pilots core Album Art")

    for image in images:
        print(image)

    url = images[0]['url']
    with open("test.jpg", "wb") as wb:
        wb.write(img_retrieve(url))

if __name__ == '__main__':
    main()
