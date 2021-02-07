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
import logging
import os
import tempfile
import unittest
import subprocess
import sys

import common

import paths
import utils

sys.path.append(os.path.join(paths.PLUGINS_DIR, "handlers"))

import gallery

from gallery import Equal, Glob, Or, Regex


IMG_3857_HEIC = os.path.join(paths.TEST_DATA_DIRECTORY, "gallery/IMG_3857.heic")
IMG_3864_JPEG = os.path.join(paths.TEST_DATA_DIRECTORY, "gallery/IMG_3864.jpeg")
IMG_3870_HEIC = os.path.join(paths.TEST_DATA_DIRECTORY, "gallery/IMG_3870.heic")
IMG_3870_JPEG = os.path.join(paths.TEST_DATA_DIRECTORY, "gallery/IMG_3870.jpeg")
IMG_6218_TIFF = os.path.join(paths.TEST_DATA_DIRECTORY, "gallery/IMG_6218.tiff")
PREVIEW_GIF = os.path.join(paths.TEST_DATA_DIRECTORY, "gallery/preview.gif")


class GalleryTestCase(unittest.TestCase):

    def test_regex(self):
        self.assertTrue(Regex(r".*").evaluate("a"))
        self.assertTrue(Regex(r"hello").evaluate("hello"))
        self.assertFalse(Regex(r"hello").evaluate("goodbye"))
        self.assertTrue(Regex(r"hello").evaluate("hello world"))
        self.assertFalse(Regex(r"^hello$").evaluate("hello world"))

    def test_equal(self):
        self.assertTrue(Equal(True).evaluate(True))
        self.assertFalse(Equal(True).evaluate(False))
        self.assertTrue(Equal(12).evaluate(12))
        self.assertFalse(Equal(12).evaluate(13))
        self.assertFalse(Equal(18).evaluate("cheese"))
        self.assertTrue(Equal("cheese").evaluate("cheese"))
        self.assertFalse(Equal("cheese").evaluate("fromage"))
        self.assertFalse(Equal("cheese").evaluate(12))

    def test_or(self):
        self.assertTrue(Or(Equal(True)).evaluate(True))
        self.assertTrue(Or(Equal(True), Equal(False)).evaluate(True))
        self.assertTrue(Or(Equal(False), Equal(True)).evaluate(True))
        self.assertFalse(Or(Equal(False), Equal(False)).evaluate(True))
        self.assertTrue(Or(Equal(False), Equal(False)).evaluate(False))

    def test_glob(self):
        self.assertTrue(Glob("*.jpeg").evaluate("IMG_3875.jpeg"))
        self.assertFalse(Glob("*.tiff").evaluate("IMG_3875.jpeg"))
        self.assertTrue(Glob("*.{jpeg,tiff}").evaluate("IMG_3875.jpeg"))
        self.assertTrue(Glob("*.{jpeg,tiff}").evaluate("IMG_3875.tiff"))

    def test_evaluate_tests(self):
        tests = [
            (Glob("*.tiff"), "image/jpeg"),
            (Glob("*"), "*"),
        ]
        self.assertEqual(gallery.evaluate_tests(tests, "IMG_3875.jpeg"), "*")
        self.assertEqual(gallery.evaluate_tests(tests, "IMG_3875.tiff"), "image/jpeg")

    @common.with_temporary_directory
    def test_resize_heic_with_format_change(self):

        basename = os.path.basename(IMG_3870_HEIC)
        size = (1600, None)
        gallery.resize(IMG_3870_HEIC, os.getcwd(), "", basename, size, 1)

        expected_basename = utils.replace_extension(basename, ".jpg")
        self.assertTrue(os.path.exists(expected_basename))
        output_size = gallery.get_size(expected_basename, 1)
        self.assertEqual(output_size["width"], size[0])

    @common.with_temporary_directory
    def test_resize_tiff_with_format_change(self):

        basename = os.path.basename(IMG_6218_TIFF)
        size = (1600, None)
        gallery.resize(IMG_6218_TIFF, os.getcwd(), "", basename, size, 1)

        expected_basename = utils.replace_extension(basename, ".jpg")
        self.assertTrue(os.path.exists(expected_basename))
        output_size = gallery.get_size(expected_basename, 1)
        self.assertEqual(output_size["width"], size[0])

    @common.with_temporary_directory
    def test_resize_jpeg(self):

        basename = os.path.basename(IMG_3870_JPEG)
        size = (800, None)
        gallery.resize(IMG_3870_JPEG, os.getcwd(), "", basename, size, 1)

        self.assertTrue(os.path.exists(utils.replace_extension(basename, ".jpeg")))
        output_size = gallery.get_size(basename, 1)
        self.assertEqual(output_size["width"], size[0])

    @common.with_temporary_directory
    def test_resize_gif(self):

        basename = os.path.basename(PREVIEW_GIF)
        size = (200, None)
        gallery.resize(PREVIEW_GIF, os.getcwd(), "", basename, size, 1)

        self.assertTrue(os.path.exists(utils.replace_extension(basename, ".gif")))
        output_size = gallery.get_size(basename, 1)
        self.assertEqual(output_size["width"], size[0])


        # TODO: Test TIFF and GIF conversion
