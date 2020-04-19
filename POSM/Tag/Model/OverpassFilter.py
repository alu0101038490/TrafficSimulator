from Shared.constants import TagComparison


class OverpassFilter(object):

    def __init__(self, key, comparison, value, negated, exactValue):
        super().__init__()
        self.key = key
        self.comparison = comparison
        self.value = value
        self.negated = negated
        self.exactValue = exactValue

    def getQL(self):
        if TagComparison.EQUAL == self.comparison:
            negation = "!" if self.negated else ""
            accuracy = "=" if self.exactValue else "~"
            return '["{}"{}{}"{}"]'.format(self.key, negation, accuracy, self.value)
        elif TagComparison.CONTAIN_ALL == self.comparison:
            ql = ""
            negation = "!" if self.negated else ""
            insensitive = "" if self.exactValue else ",i"
            for word in self.value.split():
                ql += '["{}"{}~"{}"{}]'.format(self.key, negation, word, insensitive)
            return ql
        elif TagComparison.IS_ONE_OF == self.comparison:
            negation = "!" if self.negated else ""
            words = [word for word in self.value.split()]
            insensitive = "" if self.exactValue else ",i"
            return '["{}"{}~"^({})$"{}]'.format(self.key, negation, "|".join(words), insensitive)
        elif TagComparison.HAS_KEY == self.comparison:
            return ('["{}"]' if self.exactValue else '[~{}~".*",i]').format(self.key)
        elif TagComparison.HAS_NOT_KEY == self.comparison:
            return '[!"{}"]'.format(self.key)
        elif TagComparison.HAS_ONE_KEY == self.comparison:
            keys = [key for key in self.key.split()]
            if self.exactValue:
                return '[~"^({})$"~".*"]'.format("|".join(keys))
            else:
                return '[~"({})"~".*",i]'.format("|".join(keys))
        else:
            comparisonSelection = (1 * self.negated) | (2 * (TagComparison.AT_LEAST == self.comparison))
            comparisonSymbol = ["<=", ">", ">=", "<"][comparisonSelection]
            return '(if: is_number(t["{0}"]) && number(t["{0}"]) {1} {2})'.format(self.key,
                                                                                  comparisonSymbol,
                                                                                  self.value)
