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

import logging
import os
import shutil
import subprocess
import tempfile

import incontext


@incontext.command("new", help="Create a new site", arguments=[
    incontext.Argument("path", help="destination of the new site")
])
def command_tests(incontext, options):
    print(os.path.abspath(options.site))
    with tempfile.TemporaryDirectory() as path:
        logging.info("Cloning site...")
        subprocess.check_call(["git", "clone",
                               "--depth", "1",
                               "https://github.com/inseven/incontext-starter-site.git",
                               path])
        logging.info("Creating '%s'...", options.path)
        shutil.rmtree(os.path.join(path, ".git"))
        shutil.rmtree(os.path.join(path, ".github"))
        shutil.copytree(path, os.path.abspath(options.path))
