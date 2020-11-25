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
import subprocess

import converters
import gallery
import store
import utils

LOG_LEVEL_PANIC = "panic"


def initialize_plugin(incontext):
    incontext.add_handler("import_video", import_video)


def import_video(incontext, from_directory, to_directory, category, title_from_filename=True):

    @functools.wraps(import_video)
    def inner(path):

        root, dirname, basename = utils.tripple(from_directory, path)
        destination = os.path.join(to_directory, dirname, basename)
        utils.makedirs(os.path.join(to_directory, dirname))

        data = converters.parse_path(os.path.join(dirname, basename), title_from_filename=title_from_filename)
        data['content'] = ''
        data["category"] = category
        data["template"] = "photo.html"  # TODO: Change this to be part of the configuration.

        exif = gallery.exif(path)

        if "Title" in exif:
            data["title"] = exif["Title"]

        if "Description" in exif:
            data["content"] = exif["Description"]

        if "ImageDescription" in exif:
            data["content"] = exif["ImageDescription"]

        if "CreationDate" in exif:
            data["date"] = exif["CreationDate"]

        if "ContentCreateDate" in exif:
            data["date"] = exif["ContentCreateDate"]

        name, _ = os.path.splitext(basename)

        mp4_name = "%s.mp4" % name
        mp4_path = os.path.join(to_directory, dirname, mp4_name)
        if not os.path.exists(mp4_path):
            subprocess.check_call(["ffmpeg",
                                   "-y",
                                   "-i", path,
                                   "-vcodec", "h264",
                                   "-acodec", "aac",
                                   "-strict", "-2",
                                   "-vf", "scale=1080:trunc(ow/a/2)*2",
                                   "-loglevel", LOG_LEVEL_PANIC,
                                   mp4_path])

        thumbnail_name = "%s-thumbnail.jpg" % name
        thumbnail_path = os.path.join(to_directory, dirname, thumbnail_name)
        if not os.path.exists(thumbnail_path):
            subprocess.check_call(["ffmpeg",
                                   "-y",
                                   "-i", path,
                                   "-ss", "00:00:1.000",
                                   "-vframes", "1",
                                   "-loglevel", LOG_LEVEL_PANIC,
                                   thumbnail_path])

        size = gallery.get_size(thumbnail_path, 1)
        data["thumbnail"] = converters.merge_dictionaries({'filename': thumbnail_name,
                                                           'url': os.path.join("/", dirname, thumbnail_name)},
                                                          size)
        data["video"] = converters.merge_dictionaries({'filename': mp4_name,
                                                       'url': os.path.join("/", dirname, mp4_name)},
                                                       size)

        data["path"] = converters.ensure_leading_slash(path)

        document = store.Document(data["url"], data, os.path.getmtime(path))
        incontext.environment["DOCUMENT_STORE"].add(document)

        return {'files': [mp4_path, thumbnail_path],
                'urls': [document.url]}

    return inner
