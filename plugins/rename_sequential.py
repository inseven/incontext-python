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

import math
import os
import re

import utils

from paths import *


def initialize_plugin(generate):
    generate.add_task("rename_sequential", rename_sequential)


def rename_sequential(generate, options, when):

    directories = {}
    for root, dirname, basename in utils.find_files(CONTENT_DIR):
        path = os.path.join(dirname, basename)
        if re.search(r"^%s$" % when, path):
            if dirname not in directories:
                directories[dirname] = []
            directories[dirname].append(basename)

    for dirname, basenames in directories.items():
        digits = int(math.ceil(math.log(len(basenames) + 1, 10)))
        format_string = "%%0%dd%%s" % digits
        for basename in basenames:
            name, ext = os.path.splitext(basename)
            try:
                rename = format_string % (int(name), ext)
                if rename != basename:
                    print("Renaming '%s' to '%s'..." % (name, rename))
                    os.rename(os.path.join(CONTENT_DIR, dirname, basename), os.path.join(CONTENT_DIR, dirname, rename))
            except ValueError:
                pass
