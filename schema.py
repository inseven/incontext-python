#!/usr/bin/env python
#
# Copyright (c) 2016-2021 InSeven Limited
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


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
