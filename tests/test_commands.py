#!/usr/bin/env python
#
# Copyright (c) 2016-2020 InSeven Limited
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

import os
import sys
import tempfile
import unittest

import common

import paths
import utils


class CommandsTestCase(unittest.TestCase):
    
    def test_create_test_site(self):
        with common.TemporarySite(configuration={}) as site:
            self.assertIsNotNone(site.path)
            self.assertTrue(os.path.exists(os.path.join(site.path, "site.yaml")))
            self.assertTrue(os.path.isdir(os.path.join(site.path, "content")))
            self.assertTrue(os.path.isdir(os.path.join(site.path, "templates")))
            
    def test_build_and_clean_empty_site(self):
        configuration = {
            "config": {
                "title": "Example Site",
                "url": "https://example.com"
            },
            "paths": [],
            "build_steps": [
                {
                    "task": "process_files",
                    "args": {
                        "handlers": [],
                    }
                },
            ],
        }
        with common.TemporarySite(configuration=configuration) as site:
            self.assertFalse(os.path.exists(os.path.join(site.path, "build")))
            common.run_incontext(["build"], plugins_directory=paths.PLUGINS_DIR)
            self.assertTrue(os.path.isdir(os.path.join(site.path, "build")))
            common.run_incontext(["clean"], plugins_directory=paths.PLUGINS_DIR)
            self.assertFalse(os.path.exists(os.path.join(site.path, "build")))

    def test_build_documentation(self):
        with tempfile.TemporaryDirectory() as path:
            self.assertEqual(len(os.listdir(path)), 0)
            common.run_incontext(["build-documentation", path], plugins_directory=paths.PLUGINS_DIR)
            self.assertGreater(len(os.listdir(path)), 0)
