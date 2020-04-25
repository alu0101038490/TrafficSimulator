from Shared.constants import TagComparison


class OverpassFilter(object):

    def __init__(self, key, comparison, value, negated, exactValue):
        super().__init__()
        self.__key = key
        self.__comparison = comparison
        self.__value = value
        self.__negated = negated
        self.__exactValue = exactValue

    @property
    def key(self):
        return self.__key

    @property
    def comparison(self):
        return self.__comparison

    @property
    def value(self):
        return self.__value

    @property
    def isNegated(self):
        return self.__negated

    @property
    def isExactValue(self):
        return self.__exactValue

    def getQL(self):
        if TagComparison.EQUAL == self.comparison:
            negation = "!" if self.__negated else ""
            accuracy = "=" if self.__exactValue else "~"
            return '["{}"{}{}"{}"]'.format(self.key, negation, accuracy, self.value)
        elif TagComparison.CONTAIN_ALL == self.comparison:
            ql = ""
            negation = "!" if self.__negated else ""
            insensitive = "" if self.__exactValue else ",i"
            for word in self.value.split():
                ql += '["{}"{}~"{}"{}]'.format(self.key, negation, word, insensitive)
            return ql
        elif TagComparison.IS_ONE_OF == self.comparison:
            negation = "!" if self.__negated else ""
            words = [word for word in self.value.split()]
            insensitive = "" if self.__exactValue else ",i"
            return '["{}"{}~"^({})$"{}]'.format(self.key, negation, "|".join(words), insensitive)
        elif TagComparison.HAS_KEY == self.comparison:
            return ('["{}"]' if self.__exactValue else '[~{}~".*",i]').format(self.key)
        elif TagComparison.HAS_NOT_KEY == self.comparison:
            return '[!"{}"]'.format(self.key)
        elif TagComparison.HAS_ONE_KEY == self.comparison:
            keys = [key for key in self.key.split()]
            if self.__exactValue:
                return '[~"^({})$"~".*"]'.format("|".join(keys))
            else:
                return '[~"({})"~".*",i]'.format("|".join(keys))
        else:
            comparisonSelection = (1 * self.__negated) | (2 * (TagComparison.AT_LEAST == self.comparison))
            comparisonSymbol = ["<=", ">", ">=", "<"][comparisonSelection]
            return '(if: is_number(t["{0}"]) && number(t["{0}"]) {1} {2})'.format(self.key,
                                                                                  comparisonSymbol,
                                                                                  self.value)

    def getDict(self):
        return {"key": self.key,
                "comparison": self.comparison.value,
                "value": self.value,
                "negated": self.__negated,
                "exactValue": self.__exactValue}

    @staticmethod
    def getFilterFromDict(filterDict):
        return OverpassFilter(filterDict["key"],
                              TagComparison(filterDict["comparison"]),
                              filterDict["value"],
                              filterDict["negated"],
                              filterDict["exactValue"])
