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

import hashlib
import os
import re
import shutil
import struct
import subprocess
import tempfile


class Chdir(object):
    """
    Context handler for changing directory.
    """

    def __init__(self, path):
        self.path = path

    def __enter__(self):
        self.pwd = os.getcwd()
        os.chdir(self.path)
        return self

    def __exit__(self, *args, **kwargs):
        os.chdir(self.pwd)


class TempDir(object):

    def __enter__(self):
        self.pwd = os.getcwd()
        self.path = tempfile.mkdtemp()
        os.chdir(self.path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.chdir(self.pwd)
        shutil.rmtree(self.path)


class FrontmatterDocument(object):
    """
    Convenience class for working with Front Matter and Markdown.
    
    The frontmatter module expects a named tuple with `content` and `metadata` properties when serialising Front Matter and Markdown. This class provides
    a lightweight solution.
    """

    def __init__(self, content="", metadata=None):
        self.content = content
        self.metadata = metadata


def tripple(root, path):
    dirname, basename = os.path.split(os.path.relpath(path, root))
    return (root, dirname, basename)


def hash_items(items):
    m = hashlib.md5()
    for item in items:
        if isinstance(item, float) or isinstance(item, int):
            m.update(struct.pack('d', item))
        elif isinstance(item, str):
            m.update(item.encode('utf-8'))
        else:
            raise AssertionError("Unsupported type %s", type(item))
    return m.hexdigest()


def matches_types(path, types):
    return bool([t for t in types if path.endswith("%s" % t)])


def find_files(path, types=None):
    result = []
    for root, dirs, files in os.walk(path, followlinks=True):
        result.extend([os.path.join(root, f) for f in files])
    if types is not None:
        result = [f for f in result if matches_types(f, types)]
    result.sort()
    result = [os.path.relpath(f, path) for f in result]
    result = [os.path.split(f) for f in result]
    result = [(path, base, file) for (base, file) in result]
    return result


def makedirs(path):
    """
    Ensure a directory exists at `path`, recursively creating all intermediate directories if necessary.
    
    Unlike `os.makedirs`, this does not raise an exception if the directory already exists.
    
    N.B. This will not raise an exception if the path exists, but is not a directory.
    """
    if not os.path.isdir(path):
        os.makedirs(path)


def safe_arg(arg):
    if ">" in arg:
        return "\"%s\"" % arg
    return arg


def safe_command(command):
    safe_command = [safe_arg(arg) for arg in command]
    return " ".join(safe_command)


def safe_basename(title):
    title = re.sub(r"[^a-z0-9]+", " ", title.lower())
    title = re.sub(r"\W+", "-", title.strip())
    return title


def sass(source, destination):
    subprocess.check_call(["sass",
                           "--trace",
                           source, destination])


def create_animated_thumbnail(input, output):
    with TempDir() as td:
        subprocess.check_call(["ffmpeg",
                               "-i", input,
                               "-vf", "fps=4",
                               os.path.join(td.path, "output%d.jpg")])
        subprocess.check_call(["convert",
                               "-resize", "1024x1024",
                               "-delay", "20",
                               "*.jpg",
                               "-coalesce",
                               "-layers", "OptimizeTransparency",
                               "-colors", "256",
                               output])
