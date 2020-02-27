import requests


def getValuesByKey(keyName):
    taginfoUrl = "https://taginfo.openstreetmap.org/api/4/key/values?key=" + keyName
    response = requests.get(taginfoUrl)
    return [item["value"] for item in response.json()['data'] if item["in_wiki"]]


def getOfficialKeys():
    taginfoURL = "https://taginfo.openstreetmap.org/api/4/keys/all?filter=in_wiki"
    response = requests.get(taginfoURL)
    return [item["key"] for item in response.json()['data']]
