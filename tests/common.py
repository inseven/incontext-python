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

import functools
import os
import sys
import tempfile

import yaml

import incontext
import paths
import utils


class Site(object):

    def __init__(self, testcase, path):
        self.testcase = testcase
        self.path = os.path.abspath(path)

    def run(self, args):
        with utils.Chdir(self.path):
            run_incontext(args, plugins_directory=paths.PLUGINS_DIR)

    def build(self):
        self.run(["build"])

    def clean(self):
        self.run(["clean"])

    def touch(self, path):
        utils.touch(os.path.join(self.temporary_directory.name, path))

    def assertExists(self, path):
        self.testcase.assertTrue(os.path.exists(os.path.join(self.path, path)))

    def assertNotExists(self, path):
        self.testcase.assertFalse(os.path.exists(os.path.join(self.path, path)))

    def assertIsDir(self, path):
        self.testcase.assertTrue(os.path.isdir(os.path.join(self.path, path)))


def with_temporary_directory(f):
    @functools.wraps(f)
    def inner(*args, **kwargs):
        with tempfile.TemporaryDirectory() as path, utils.Chdir(path):
                return f(*args, **kwargs)
    return inner


class TemporarySite(Site):
    """
    Context handler which creates a temporary site for testing.
    """

    def __init__(self, testcase, configuration):
        temporary_directory = tempfile.TemporaryDirectory()
        super().__init__(testcase, temporary_directory.name)
        self.temporary_directory = temporary_directory
        self.configuration = configuration

    def __enter__(self):
        self.pwd = os.getcwd()

        # Create the configuration file.
        with open(os.path.join(self.temporary_directory.name, "site.yaml"), "w") as fh:
            yaml.dump(self.configuration, fh)

        # Create the required directories.
        utils.makedirs(os.path.join(self.temporary_directory.name, "content"))
        utils.makedirs(os.path.join(self.temporary_directory.name, "templates"))

        os.chdir(self.temporary_directory.name)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        os.chdir(self.pwd)
        self.temporary_directory.cleanup()


def run_incontext(args, plugins_directory=None):
    instance = incontext.InContext(plugins_directory=plugins_directory)
    instance.run(args)
