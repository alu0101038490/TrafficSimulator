from enum import Enum

class Surrounding(Enum):
    AROUND = 1
    ADJACENT = 2
    NONE = 3

class Query(object):

    def __init__(self):
        super().__init__()
        self.tags = {}

    def addTag(self, key, value, exactValue, surrounding):
        self.tags[key] = (value, exactValue, surrounding)

    def __repr__(self):
        return self.__str__()

    def next_string(self, s):
        strip_zs = s.rstrip('z')
        if strip_zs:
            return strip_zs[:-1] + chr(ord(strip_zs[-1]) + 1) + 'a' * (len(s) - len(strip_zs))
        else:
            return 'a' * (len(s) + 1)

    def __str__(self):
        str = "(\n"
        if len(self.tags) > 0:
            str += "\tway"
            for key, (value, exact, s) in self.tags.items():
                str += "[\"" + key
                str += '"="' if exact else '"~"'
                str += value + ("\"]" if exact else "\",i]")
        return str + ";\n\t>;\n);\nout meta;"