import re

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
            return '[{}{}{}{}]'.format(repr(self.key), negation, accuracy, repr(self.value))
        elif TagComparison.CONTAIN_ALL == self.comparison:
            ql = ""
            negation = "!" if self.__negated else ""
            for word in self.value:
                ql += '[{}{}~{}]'.format(repr(self.key), negation, repr(re.escape(word) if self.__exactValue else word))
            return ql
        elif TagComparison.IS_ONE_OF == self.comparison:
            negation = "!" if self.__negated else ""
            return '[{}{}~^({})$]'.format(repr(self.key), negation, repr("|".join([re.escape(word) if self.__exactValue else word for word in self.value])))
        elif TagComparison.HAS_KEY == self.comparison:
            return ('[{}]' if self.__exactValue else '[~{}~".*",i]').format(repr(self.key))
        elif TagComparison.HAS_NOT_KEY == self.comparison:
            return '[!{}]'.format(repr(self.key))
        elif TagComparison.HAS_ONE_KEY == self.comparison:
            return '[~^({})$~".*"]'.format(repr("|".join([re.escape(word) if self.__exactValue else word for word in self.key])))
        else:
            comparisonSelection = (1 * self.__negated) | (2 * (TagComparison.AT_LEAST == self.comparison))
            comparisonSymbol = ["<=", ">", ">=", "<"][comparisonSelection]
            # ERROR: is too weak, Overpass does not allow a query that has only this tag
            return '(if: is_number(t[{0}]) && number(t[{0}]) {1} {2})'.format(repr(self.key),
                                                                                  comparisonSymbol,
                                                                                  repr(self.value))

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

