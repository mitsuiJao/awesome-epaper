import requests
import urllib.parse

def request_API(url, **kwargs):
    requestURL = url
    if kwargs:
        requestURL += "?"
    for key in kwargs.keys():
        requestURL += key
        requestURL += "="
        requestURL += urllib.parse.quote(kwargs[key])

    res = requests.get(requestURL)
    if res.status_code == 200:
        dirdate = res.json()
    else:
        return

    res.close()

    return dirdate