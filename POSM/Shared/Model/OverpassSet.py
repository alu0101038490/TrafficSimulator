from Shared.Utils.GenericUtils import nextString


class OverpassSet(object):

    def __init__(self, name=""):
        super().__init__()
        self.setName = name

    @property
    def name(self):
        return self.setName
