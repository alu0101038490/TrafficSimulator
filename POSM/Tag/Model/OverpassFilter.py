class OverpassFilter(object):

    def __init__(self, key, value, negated, exactValue):
        super().__init__()
        self.key = key
        self.value = value
        self.negated = negated
        self.exactValue = exactValue

    def getQL(self):
        negation = "!" if self.negated else ""
        comparison = "=" if self.exactValue else "~"
        if self.value:
            ql = '["{}"{}{}"{}"]'.format(self.key, negation, comparison, self.value)
        else:
            ql = '[{}"{}"]'.format(negation, self.key)
        return ql

    def getDict(self):
        return {"key": self.key,
                "value": self.value,
                "negated": self.negated,
                "exactValue": self.exactValue}

    @staticmethod
    def getFilterFromDict(dict):
        return OverpassFilter(dict["key"],
                              dict["value"],
                              dict["negated"],
                              dict["exactValue"])
