from enum import Enum


class Surround(Enum):
    AROUND = 1
    ADJACENT = 2
    NONE = 3


class Query(object):

    def __init__(self):
        super().__init__()
        self.tags = {}

    def addTag(self, key, value, exactValue, surrounding):
        self.tags[key] = (value, exactValue, surrounding)

    def getQL(self):
        str = "(\n"
        if len(self.tags) > 0:
            str += "\tway"
            for key, (value, exact, s) in self.tags.items():
                str += "[\"" + key
                str += '"="' if exact else '"~"'
                str += value + ("\"]" if exact else "\",i]")
        return str + ";\n\t>;\n);\nout meta;"
