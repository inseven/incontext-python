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

import datetime
import dateutil
import frontmatter
import os
import re
import sys
import titlecase

import paths

sys.path.append(paths.SERVICE_DIR)

import store


def read_frontmatter(path):
    fm = frontmatter.load(path)
    data = fm.metadata
    data["content"] = fm.content
    return data


# TODO: Move this until utils.
def merge_dictionaries(a, b):
    result = dict(a)
    for key, value in b.items():
        result[key] = value
    return result


def clean_name(path):
    basename, ext = os.path.splitext(os.path.basename(path))
    if basename.lower() == "index":
        return ""
    return basename.lower()


def is_index(path):
    basename, _ = os.path.splitext(os.path.basename(path))
    if basename.lower() == "index":
        return True
    return False


def strip_trailing_index(path):
    if is_index(path):
        return os.path.dirname(path)
    return path


def title_and_scale_from_path(path):
    dirname, basename = os.path.split(path)
    if is_index(path):
        basename = os.path.basename(dirname)

    scale = None
    match_scale = re.match(r"^(.+?)@(\d+)x$", basename)
    if match_scale:
        scale = int(match_scale.group(2))
        basename = match_scale.group(1)

    name, ext = os.path.splitext(basename)

    return (titlecase.titlecase(name.replace("-", " ")), scale)


def ensure_leading_slash(path):
    return path if path.startswith("/") else "/" + path


def ensure_trailing_slash(path):
    return path if path.endswith("/") else path + "/"


def parent(path):
    return ensure_trailing_slash(ensure_leading_slash(os.path.normpath(os.path.dirname(path))))


def parse_path(path, title_from_filename=True):
    """
    Parse a path, returning a dictionary containing all derived information.

    @param path: Path for which to generate the URL, relative to the root of the site.
    @type path: str

    @return: Dictionary containing url, parent, date and inferred title, where possible.
    @rtype: dict
    """
    clean_path = strip_trailing_index(path)
    basename = clean_name(clean_path)  # TODO: Remove this?

    data = {}
    data["title"], data["scale"] = title_and_scale_from_path(clean_path)
    data["parent"] = parent(clean_path)
    data["url"] = ensure_trailing_slash(os.path.normpath(ensure_leading_slash(os.path.join(os.path.dirname(clean_path), basename))))

    match = re.match(r"(\d{4}-\d{2}-\d{2})-(.+)", basename)
    match = re.match(r"^(\d{4}-\d{2}-\d{2}(-\d{2}-\d{2})?(-\d{2})?)(-(.+?))?$", basename)
    if match:
        if match.group(5):  # filename only contains a date
            data["title"], data["scale"] = title_and_scale_from_path(match.group(5))
        else:
            del data["title"]
        date = match.group(1)
        if len(date) == 10:
            data["date"] = datetime.datetime.strptime(date, "%Y-%m-%d")
        elif len(date) == 16:
            data["date"] = datetime.datetime.strptime(date, "%Y-%m-%d-%H-%M")
        elif len(date) == 19:
            data["date"] = datetime.datetime.strptime(date, "%Y-%m-%d-%H-%M-%S")

    if not title_from_filename:
        try:
            del data["title"]
        except KeyError:
            pass

    return data


def frontmatter_document(root, path, default_category='general'):
    """
    Parse the contents of a frontmatter document as a DocumentStore Document.

    @param root: Root of the site.
    @type root: str
    @param path: Document path, relative to the root of the site.
    @type path: str

    @return: Document representing the contents of the frontmatter document.
    @rtype: store.Document
    """
    data = {}
    data = merge_dictionaries(data, read_frontmatter(os.path.join(root, path)))
    data = merge_dictionaries(data, {key: value for key, value in parse_path(path).items()
                                     if ((key != "title" or "title" not in data) and
                                         (key != "date" or "date" not in data))})
    data["path"] = ensure_leading_slash(path)
    if "category" not in data:
        data["category"] = default_category
    return store.Document(data['url'], data, os.path.getmtime(os.path.join(root, path)))
