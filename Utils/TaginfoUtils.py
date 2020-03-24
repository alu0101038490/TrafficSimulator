import requests


def getValuesByKey(keyName, maxTime=1):
    taginfoUrl = "https://taginfo.openstreetmap.org/api/4/key/values?key=" + keyName
    response = requests.get(taginfoUrl, timeout=maxTime)
    return [item["value"] for item in response.json()['data'] if item["in_wiki"]]

def getOfficialKeys():
    taginfoURL = "https://taginfo.openstreetmap.org/api/4/keys/all?filter=in_wiki&sortname=count_all&sortorder=desc"
    response = requests.get(taginfoURL)
    return [item["key"] for item in response.json()['data'][:100]]

def getKeyDescription(keyName):
    taginfoURL = "https://taginfo.openstreetmap.org/api/4/key/wiki_pages?key=" + keyName
    response = requests.get(taginfoURL)
    return response.json()['data']