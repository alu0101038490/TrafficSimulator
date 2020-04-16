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
            if self.value:
                return '["{}"{}{}"{}"]'.format(self.key, negation, accuracy, self.value)
            else:
                return '[{}"{}"]'.format(negation, self.key)
        elif TagComparison.CONTAIN_ALL == self.comparison:
            ql = ""
            negation = "!" if self.negated else ""
            for word in self.value.split():
                ql += '["{}"{}~"{}"]'.format(self.key, negation, word)
            return ql
        elif TagComparison.CONTAIN_ONE == self.comparison:
            negation = "!" if self.negated else ""
            words = [word for word in self.value.split()]
            return '["{}"{}~"^({})$"]'.format(self.key, negation, "|".join(words))
        else:
            comparisonSelection = (1 * self.negated) | (2 * (TagComparison.AT_LEAST == self.comparison))
            comparisonSymbol = ["<=", ">", ">=", "<"][comparisonSelection]
            return '(if: is_number(t["{0}"]) && number(t["{0}"]) {1} {2})'.format(self.key, comparisonSymbol, self.value)
