import fnmatch
import re

import braceexpand
import pyparsing as pp

from pyparsing import Combine, delimitedList, Dict, Forward, Group, infixNotation, Keyword, LineEnd, Literal, Optional, Or, QuotedString, Suppress, Word, ZeroOrMore


class Regex(object):

    def __init__(self, pattern, flags=0, key=None):
        self.pattern = pattern
        self.flags = flags
        self.key = key
        self.expression = re.compile(pattern, flags)

    def evaluate(self, data):
        data = data if self.key is None else data[self.key]
        return self.expression.match(data) is not None

    def __eq__(self, other):
        if not isinstance(other, Regex):
            return False
        return (self.pattern == other.pattern and
                self.flags == other.flags and
                self.key == other.key)


class Equal(object):

    def __init__(self, value):
        self.value = value

    def evaluate(self, data):
        return data == self.value


class Or(object):

    def __init__(self, *tests):
        self.tests = tests

    def evaluate(self, data):
        for test in self.tests:
            if test.evaluate(data):
                return True
        return False

    def __eq__(self, other):
        if not isinstance(other, Or):
            return False
        return self.tests == other.tests


class And(object):

    def __init__(self, *tests):
        self.tests = tests

    def evaluate(self, data):
        for test in self.tests:
            if not test.evaluate(data):
                return False
        return True

    def __eq__(self, other):
        if not isinstance(other, And):
            return False
        return self.tests == other.tests


class Glob(Or):

    def __init__(self, glob, key="basename"):
        patterns = [fnmatch.translate(p) for p in braceexpand.braceexpand(glob)]
        tests = [Regex(pattern, flags=re.IGNORECASE, key=key) for pattern in patterns]
        super().__init__(*tests)

    def evaluate(self, data):
        return super().evaluate(data)


# TODO: Consider making this an explicit metadata key test.
class Metadata(object):

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def evaluate(self, data):
        for key, value in self.kwargs.items():
            metadata = data["metadata"]
            if key not in metadata or metadata[key] != value:
                return False
        return True

    def __eq__(self, other):
        if not isinstance(other, Metadata):
            return False
        return self.kwargs == other.kwargs


LEFT_PARENTHESIS = Literal("(").suppress()
RIGHT_PARENTHESIS = Literal(")").suppress()
LEFT_SQUARE_BRACKET = Literal("[").suppress()
RIGHT_SQUARE_BRACKET = Literal("]").suppress()
INTEGER = Word(pp.nums).setParseAction(lambda tokens: int(tokens[0]))
FLOAT = Combine(Word(pp.nums) + "." + Word(pp.nums)).setParseAction(lambda tokens: float(tokens[0]))
QUOTED_STRING = QuotedString("'") | QuotedString('"')
ARG = Forward()
ARG << (QUOTED_STRING | FLOAT | INTEGER | Group(LEFT_SQUARE_BRACKET + Optional(delimitedList(ARG)) + RIGHT_SQUARE_BRACKET))
ARGS = delimitedList(ARG).setResultsName("args")
KWARG = Group(Word(pp.alphas) + Suppress("=") + ARG)
KWARGS = Dict(delimitedList(KWARG)).setResultsName("kwargs")
PARAMETERS = (ARGS + Optional(Suppress(",") + KWARGS)) | KWARGS
OR = Literal("or")
AND = Literal("and")
LINE_END = LineEnd().suppress()
METHOD = Word(pp.alphas).setResultsName("method") + LEFT_PARENTHESIS + Optional(PARAMETERS) + RIGHT_PARENTHESIS
METHOD_PARSER = METHOD + LINE_END


# TODO: Check for noise at the end of the line.
NUMBER = Word(pp.nums)
OPERATION = OR | AND
EXPRESSION = Forward()
ATOM = Group(NUMBER) | Group(LEFT_PARENTHESIS + EXPRESSION + RIGHT_PARENTHESIS)
EXPRESSION << Group(ATOM + ZeroOrMore(OPERATION + Group(ATOM)))
EXPRESSION_PARSER = EXPRESSION + LINE_END

EXPRESSION_PARSER = infixNotation(
    Group(METHOD),
    [
        (AND, 2, pp.opAssoc.LEFT),
        (OR, 2, pp.opAssoc.LEFT),
    ]
) + LINE_END


def parse_method(string):
    return METHOD_PARSER.parseString(string).asDict()


def to_dict(expression):
    # If it has a method, then it's method.
    if "method" in expression:
        return expression.asDict()
    lhs, op, rhs = expression
    return {
        "method": op,
        "args": [to_dict(lhs), to_dict(rhs)]
    }


def parse_structure(string):
    result = EXPRESSION_PARSER.parseString(string)
    return to_dict(result[0])

BUILTIN_CONDITION_LOOKUP = {
    "glob": Glob,
    "and": And,
    "or": Or,
    "metadata": Metadata,
}


def structure_to_instance(lookup, structure):
    if not isinstance(structure, dict):
        return structure
    cls = lookup[structure["method"]]
    args = [structure_to_instance(lookup, arg) for arg in structure["args"]] if "args" in structure else []
    kwargs = structure["kwargs"] if "kwargs" in structure else {}
    return cls(*args, **kwargs)


def parse_condition(string):
    structure = parse_structure(string)
    return structure_to_instance(BUILTIN_CONDITION_LOOKUP, structure)
