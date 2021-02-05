class TransformFailure(Exception):
    pass


class Skip(Exception):
    pass


class Key(object):

    def __init__(self, key):
        self.key = key

    def __call__(self, dictionary):
        if self.key in dictionary:
            return dictionary[self.key]
        raise TransformFailure()


class First(object):

    def __init__(self, *transforms):
        self.transforms = transforms

    def __call__(self, data):
        for transform in self.transforms:
            try:
                return transform(data)
            except TransformFailure:
                pass
        raise TransformFailure()


class Default(object):

    def __init__(self, value):
        self.value = value

    def __call__(self, data):
        return self.value


class Empty(object):

    def __call__(self, data):
        raise Skip()


class Dictionary(object):

    def __init__(self, schema):
        self.schema = schema

    def __call__(self, data):
        result = {}
        for key, transform in self.schema.items():
            try:
                result[key] = transform(data)
            except Skip:
                pass
        return result
