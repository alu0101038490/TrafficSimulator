from Shared.Utils.GenericUtils import nextString


class SetNameManagement(object):
    
    usedNames = []
    nextName = "a"

    @classmethod
    def getUniqueSetName(cls):
        setName = cls.nextName
        cls.nextName = nextString(setName)
        while setName in cls.usedNames:
            setName = cls.nextName
            cls.nextName = nextString(setName)
        return setName

    @classmethod
    def isAvailable(cls, name):
        return name not in cls.usedNames

    @classmethod
    def assign(cls, name):
        if name not in cls.usedNames:
            cls.usedNames.append(name)

    @classmethod
    def releaseName(cls, name):
        try:
            cls.usedNames.remove(name)
        except ValueError:
            return
