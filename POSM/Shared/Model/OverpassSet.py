class OverpassSet(object):

    def __init__(self, name=""):
        super().__init__()
        self.__name = name

    @property
    def name(self):
        return self.__name
