from Shared.Utils.GenericUtils import nextString


class OverpassSet(object):

    usedNames = []
    nextName = "a"

    def __init__(self, name=""):
        super().__init__()
        self.setName = name
        if name != "":
            if name in OverpassSet.usedNames:
                raise ValueError()
        else:
            self.setName = OverpassSet.getUniqueSetName()
        OverpassSet.usedNames.append(self.setName)

    @classmethod
    def getUniqueSetName(cls):
        setName = cls.nextName
        cls.nextName = nextString(setName)
        while setName in OverpassSet.usedNames:
            setName = cls.nextName
            cls.nextName = nextString(setName)
        return setName

    @property
    def name(self):
        return self.setName

    def __del__(self):
        OverpassSet.usedNames.remove(self.name)
