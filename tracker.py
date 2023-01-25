# Copyright (c) 2016-2023 InSeven Limited
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

import copy
import json
import logging
import os
import os.path

import utils


class ChangeTracker(object):

    def __init__(self, name, path):
        self._name = name
        self._path = path
        self._cache = {}
        if os.path.exists(self._path):
            with open(self._path) as f:
                self._cache = json.load(f)
        self._actions = []
        self._deletions = copy.deepcopy(self._cache)

    def _save(self):
        with open(self._path, "w") as f:
            json.dump(self._cache, f)

    def add(self, path, create, mtime=None):
        if mtime is None:
            mtime = os.path.getmtime(path)

        # Mark the file as present.
        if path in self._deletions and self._cache[path]['mtime'] == mtime:
            del self._deletions[path]
            return

        def action():
            info = create(path)
            self._cache[path] = {'mtime': info["mtime"] if "mtime" in info else mtime, 'info': info}
        self._actions.append(action)

    def get_info(self, path):
        return self._cache[path]['info']

    @property
    def paths(self):
        return self._cache.keys()

    def commit(self, cleanup):
        if self._deletions:
            with utils.measure("[%s] Cleaning %d items" % (self._name, len(self._deletions))):
                for path in self._deletions.keys():
                    cleanup(self._cache[path]['info'])
                    del self._cache[path]
        if self._actions:
            with utils.measure("[%s] Processing %d items" % (self._name, len(self._actions))):
                for action in self._actions:
                    action()
        self._save()
