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

import functools
import os
import shutil
import utils


def initialize_plugin(incontext):
    incontext.add_handler("ignore", ignore)
    incontext.add_handler("copy_file", copy_file)
    incontext.add_handler("preprocess_stylesheet", preprocess_stylesheet)


def ignore(incontext, from_directory, to_directory):
    @functools.wraps(ignore)
    def inner(path):
        return {'files': []}
    return inner


def copy_file(incontext, from_directory, to_directory):
    @functools.wraps(copy_file)
    def inner(path):
        root, dirname, basename = utils.tripple(from_directory, path)
        destination = os.path.join(to_directory, dirname, basename)
        utils.makedirs(os.path.join(to_directory, dirname))
        shutil.copy(path, destination)
        return {'files': [destination]}
    return inner


def preprocess_stylesheet(incontext, from_directory, to_directory, path=None):
    @functools.wraps(preprocess_stylesheet)
    def inner(source):
        if path is not None:
            source = path
        root, dirname, basename = utils.tripple(from_directory, source)
        destination = os.path.join(to_directory, dirname, os.path.splitext(basename)[0] + ".css")
        if path is not None:
            destination = os.path.join(to_directory, os.path.splitext(path)[0] + ".css")
        utils.makedirs(os.path.dirname(destination))
        utils.sass(os.path.join(from_directory, source), destination)
        return {'files': [destination]}
    return inner
