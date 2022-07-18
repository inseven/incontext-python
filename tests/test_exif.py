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

import datetime
import os
import unittest
import sys

import paths

sys.path.append(os.path.join(paths.PLUGINS_DIR, "handlers"))

import gallery


IMG_4056_JPEG = os.path.join(paths.TEST_DATA_DIRECTORY, "exif/IMG_4056.jpeg")
IMG_4056_WITH_SIDECAR_JPEG = os.path.join(paths.TEST_DATA_DIRECTORY, "exif/IMG_4056_with_sidecar.jpeg")
IMAGE_WITH_FRONTMATTER_AND_LINE_SEPARATORS = os.path.join(paths.TEST_DATA_DIRECTORY, "exif/2022-07-02-14-20-38-coaltown.jpeg")
IMAGE_WITH_NEGATIVE_LATITUDE = os.path.join(paths.TEST_DATA_DIRECTORY, "exif/negative-latitude.jpg")
IMAGE_WITH_NUMERICAL_DESCRIPTION = os.path.join(paths.TEST_DATA_DIRECTORY, "exif/numerical-description.jpg")


class ExifTestCase(unittest.TestCase):

    def test_exif_title(self):
        metadata = gallery.metadata_from_exif(IMG_4056_JPEG)
        self.assertEqual(metadata["title"], "Wolf")

    def test_exif_date(self):
        metadata = gallery.metadata_from_exif(IMG_4056_JPEG)
        self.assertEqual(metadata["date"], datetime.datetime(2019, 9, 10, 6, 49, 11))

    def test_sidecar_overrides_title(self):
        metadata = gallery.metadata_from_exif(IMG_4056_WITH_SIDECAR_JPEG)
        self.assertEqual(metadata["title"], "Sunrise")

    def test_caption_with_frontmatter_and_line_separators(self):
        metadata = gallery.metadata_from_exif(IMAGE_WITH_FRONTMATTER_AND_LINE_SEPARATORS)
        self.assertEqual(metadata["title"], "Coaltown")

    def test_signed_latitude(self):
        metadata = gallery.metadata_from_exif(IMAGE_WITH_NEGATIVE_LATITUDE)
        print(metadata)
        self.assertEqual(metadata["location"]["latitude"], -33.8833)

    def test_numerical_description(self):
        metadata = gallery.metadata_from_exif(IMAGE_WITH_NUMERICAL_DESCRIPTION)
        self.assertEqual(metadata["content"], "20060326125236")
