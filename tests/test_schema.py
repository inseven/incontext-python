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

import unittest

from schema import Dictionary, Empty, First, GPSCoordinate, Identity, Key, Skip, TransformFailure


class SchemaTestCase(unittest.TestCase):

    def assertSchema(self, schema, data, result):
        self.assertEquals(schema(data), result)

    def test_key(self):
        s = Key("foo")
        self.assertEqual(s({"foo": "cheese"}), "cheese")
        with self.assertRaises(TransformFailure):
            s({"bar": "cheese"})

    def test_first_match_first(self):
        s = First(Key("foo"), Key("bar"))
        self.assertEqual(s({"foo": "cheese"}), "cheese")
        self.assertEqual(s({"bar": "cheese"}), "cheese")
        with self.assertRaises(TransformFailure):
            s({"baz": "cheese"})

    def test_empty(self):
        s = Empty()
        with self.assertRaises(Skip):
            s("anything")

    def test_dictionary_with_empty(self):
        s = Dictionary({
            "field": Empty()
        })
        self.assertEquals(s({"field": "cheese"}), {})

    def test_dictionary_matching_key(self):
        self.assertSchema(
            Dictionary({
                "foo": Key("foo")
            }),
            {"foo": "cheese"},
            {"foo": "cheese"}
        )

    def test_dictionary_different_key(self):
        self.assertSchema(
            Dictionary({
                "foo": Key("bar")
            }),
            {"bar": "cheese"},
            {"foo": "cheese"}
        )

    def test_dictionary_multiple_keys(self):
        self.assertSchema(
            Dictionary({
                "foo": First(Key("foo"), Key("bar"))
            }),
            {"bar": "cheese"},
            {"foo": "cheese"}
        )

    def test_identity(self):
        s = Identity()
        self.assertEqual(s("Hello, World!"), "Hello, World!")
        self.assertEqual(s({}), {})

    def test_gps_coordinate(self):
        s = GPSCoordinate(Identity())
        self.assertEqual(s("45.5283694444 N"), 45.5283694444)
        self.assertEqual(s("45.5283694444 S"), 45.5283694444)
        self.assertEqual(s("119.3941638889 W"), -119.3941638889)
        self.assertEqual(s("119.3941638889 E"), 119.3941638889)
        with self.assertRaises(AssertionError):
            s("45 deg 31' 42.13\" N")
