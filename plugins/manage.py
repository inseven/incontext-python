# Copyright (c) 2016-2022 InSeven Limited
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
import frontmatter
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile

import handlers.gallery as gallery
import paths
import utils


def initialize_plugin(incontext):
    incontext.add_command("add", command_add, help="add a new post")
    incontext.add_command("publish", command_publish, help="publish a draft post")


def subcommand_add_draft(incontext, parser):
    parser.add_argument("title", help="title")

    def add_draft(options):
        basename = utils.safe_basename(options.title)
        directory = os.path.join(incontext.configuration.site.paths.drafts, basename)
        index = os.path.join(directory, "index.markdown")
        os.makedirs(directory)
        with open(index, "w") as fh:
            document = utils.FrontmatterDocument(metadata={"title": options.title})
            fh.write(frontmatter.dumps(document))
            fh.write("\n")

    return add_draft


THOUGHT_TEMPLATE = """
---
date: %s
category: thoughts
template: post.html

---
"""


def subcommand_add_thought(incontext, parser):
    parser.add_argument("--message", "-m", type=str, default=None, help="message")

    def add_thought(options):
        date = datetime.datetime.utcnow()
        directory = incontext.configuration.site.paths.thoughts
        path = os.path.join(directory, "%s.markdown" % (date.strftime("%Y-%m-%d-%H-%M"), ))
        with open(path, "w") as fh:
            fh.write(THOUGHT_TEMPLATE.lstrip() % (date, ))
            if options.message is not None:
                fh.write(options.message)
                fh.write("\n")
        if options.message is None:
            subprocess.check_call(["emacs", path])

    return add_thought


def subcommand_add_snapshot(incontext, parser):
    parser.add_argument("file", type=str, help="image file to add")
    parser.add_argument("--title", "-t", type=str, help="title")
    parser.add_argument("--description", "-d", type=str, help="description")

    def add_snapshot(options):
        path = os.path.abspath(options.file)

        # Working directory.
        with tempfile.TemporaryDirectory() as temporary_directory:

            # InContext doesn't handle TIFF files well, so we convert them to JPEG if necessary.
            filename = os.path.basename(path)
            basename, ext = os.path.splitext(filename)
            if ext.lower() == ".tiff":
                logging.info("Converting TIFF to JPEG...")

                jpeg_path = os.path.join(temporary_directory, f"{basename}.jpeg")
                subprocess.check_call(["convert", path, "-quality", "100", jpeg_path])

                # Unfortunately we also need to copy the metadata in a separate step.
                subprocess.check_call(["exiftool", "-TagsFromFile", path, "-all:all>all:all", jpeg_path])

                path = jpeg_path

            exif_metadata = gallery.metadata_from_exif(path)
            date = exif_metadata["date"].strftime("%Y-%m-%d-%H-%M-%S")

            title = ""
            try:
                title = exif_metadata["title"]
            except KeyError:
                pass
            if options.title:
                title = options.title
            title = utils.safe_basename(title)
            basename, ext = os.path.splitext(path)
            dirname = os.path.dirname(basename)
            filename = date
            if title:
                filename = f"{date}-{title}"

            if options.title or options.description:
                sidecar_path = os.path.join(incontext.configuration.site.paths.snapshots, filename + ".exif")
                sidecar = {}
                if options.title:
                    sidecar["Title"] = options.title
                if options.description:
                    sidecar["Description"] = options.description
                with open(sidecar_path, "w") as fh:
                    fh.write(json.dumps(sidecar, indent=4))
                    fh.write("\n")

            destination = os.path.join(incontext.configuration.site.paths.snapshots, filename + ext)
            shutil.copyfile(path, destination)

    return add_snapshot


ALBUM_TEMPLATE = """
---
title: %s
date: %s
category: albums
template: album.html
---
"""


def subcommand_add_album(incontext, parser):
    parser.add_argument("date", help="date (in the form YYYY-mm-dd)")
    parser.add_argument("title", type=str, help="title")

    def add_album(options):
        basename = utils.safe_basename(options.title)
        date = datetime.datetime.strptime(options.date, "%Y-%m-%d")
        directory = os.path.join(incontext.configuration.site.paths.photos, date.strftime("%Y"), date.strftime("%m"), basename)
        os.makedirs(directory)
        with open(os.path.join(directory, "index.markdown"), "w") as fh:
            fh.write(ALBUM_TEMPLATE % (options.title, options.date))

    return add_album


CONTENT_TYPES = {
    "album": subcommand_add_album,
    "draft": subcommand_add_draft,
    "snapshot": subcommand_add_snapshot,
    "thought": subcommand_add_thought,
}


def command_add(incontext, parser):
    subparsers = parser.add_subparsers(title="content type", required=True)
    for content_type, function in CONTENT_TYPES.items():
        parser = subparsers.add_parser(content_type)
        parser.set_defaults(add_function=function(incontext, parser))

    def add(options):
        options.add_function(options)

    return add

def command_publish(incontext, parser):
    parser.add_argument("path", help="path to post to publish")

    def publish(options):

        # Read the title and determine a suitable basename.
        document = incontext.load_frontmatter_document(os.path.join(options.path, "index.markdown"))
        basename = utils.safe_basename(document.title)
        date = datetime.datetime.now().strftime("%Y-%m-%d")
        destination = os.path.join(incontext.configuration.site.paths.posts, "%s-%s" % (date, basename))

        # Ensure the destination directory exists.
        utils.makedirs(incontext.configuration.site.paths.posts)

        # Move the file to the new location.
        logging.info("Publishing to '%s'..." % (os.path.relpath(destination, incontext.configuration.site.root), ))
        shutil.move(os.path.abspath(options.path), destination)

    return publish
