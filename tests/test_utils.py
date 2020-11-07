#!/usr/bin/env python
#
# Copyright (c) 2016-2020 Jason Barrie Morley
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

import datetime
import os
import sys
import unittest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.dirname(TESTS_DIR)

sys.path.append(SCRIPTS_DIR)

import converters


class ParsePathTestCase(unittest.TestCase):

    def test_post_no_date(self):
        metadata = converters.parse_path("/posts/this-is-a-post.markdown")
        self.assertEqual(metadata["title"], "This Is a Post")
        self.assertFalse("date" in metadata)
        self.assertEqual(metadata["url"], "/posts/this-is-a-post/")
        self.assertEqual(metadata["parent"], "/posts/")

    def test_post_date(self):
        metadata = converters.parse_path("/posts/2017-12-11-this-is-a-post.markdown")
        self.assertEqual(metadata["title"], "This Is a Post")
        self.assertEqual(metadata["date"], datetime.datetime(2017, 12, 11, 0, 0))
        self.assertEqual(metadata["url"], "/posts/2017-12-11-this-is-a-post/")
        self.assertEqual(metadata["parent"], "/posts/")

    def test_post_index_no_date(self):
        metadata = converters.parse_path("/posts/this-is-a-post/index.markdown")
        self.assertEqual(metadata["title"], "This Is a Post")
        self.assertFalse("date" in metadata)
        self.assertEqual(metadata["url"], "/posts/this-is-a-post/")
        self.assertEqual(metadata["parent"], "/posts/")

    def test_post_index_date(self):
        metadata = converters.parse_path("/posts/2017-12-11-this-is-a-post/index.markdown")
        self.assertEqual(metadata["title"], "This Is a Post")
        self.assertEqual(metadata["date"], datetime.datetime(2017, 12, 11, 0, 0))
        self.assertEqual(metadata["url"], "/posts/2017-12-11-this-is-a-post/")
        self.assertEqual(metadata["parent"], "/posts/")

    def test_post_titlecase(self):
        metadata = converters.parse_path("2016-10-24-vision-of-the-future.markdown")
        self.assertEqual(metadata["title"], "Vision of the Future")

    def test_post_titlecase_with_number(self):
        metadata = converters.parse_path("2016-10-24-vision-of-the-future-2000.markdown")
        self.assertEqual(metadata["title"], "Vision of the Future 2000")

    def test_image_with_scale(self):
        metadata = converters.parse_path("2014-02-21-album-art@2x.jpg")
        self.assertEqual(metadata["title"], "Album Art")
        self.assertEqual(metadata["date"], datetime.datetime(2014, 2, 21, 0, 0))
        self.assertEqual(metadata["url"], "/2014-02-21-album-art@2x/")
        self.assertEqual(metadata["scale"], 2)

    def test_image_with_scale_time(self):
        metadata = converters.parse_path("2014-02-21-18-24-album-art@2x.jpg")
        self.assertEqual(metadata["title"], "Album Art")
        self.assertEqual(metadata["date"], datetime.datetime(2014, 2, 21, 18, 24))
        self.assertEqual(metadata["url"], "/2014-02-21-18-24-album-art@2x/")
        self.assertEqual(metadata["scale"], 2)

    def test_image_with_scale_time_seconds(self):
        metadata = converters.parse_path("2014-02-21-18-24-45-album-art@2x.jpg")
        self.assertEqual(metadata["title"], "Album Art")
        self.assertEqual(metadata["date"], datetime.datetime(2014, 2, 21, 18, 24, 45))
        self.assertEqual(metadata["url"], "/2014-02-21-18-24-45-album-art@2x/")
        self.assertEqual(metadata["scale"], 2)

    def test_time_no_title(self):
        metadata = converters.parse_path("photos/instagram/2016-03-09-17-48-00.jpg")
        self.assertFalse("title" in metadata)
        self.assertEqual(metadata["date"], datetime.datetime(2016, 3, 9, 17, 48, 00))
        self.assertEqual(metadata["url"], "/photos/instagram/2016-03-09-17-48-00/")
