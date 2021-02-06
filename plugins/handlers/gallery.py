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

import argparse
import codecs
import datetime
import fnmatch
import functools
import glob
import io
import json
import logging
import mimetypes
import os
import os.path
import re
import shutil
import subprocess
import sys
import time

import braceexpand
import dateutil
import frontmatter
import pyheif
import whatimage

from PIL import Image, ExifTags

import converters
import store
import utils

from schema import Default, Dictionary, Empty, EXIFDate, First, GPSCoordinate, Key


METADATA_SCHEMA = Dictionary({

    "title": First(Key("Title"), Key("DisplayName"), Key("ObjectName"), Empty()),
    "content": First(Key("ImageDescription"), Key("Description"), Key("ArtworkContentDescription"), Default(None)),
    "date": First(EXIFDate(First(Key("DateTimeOriginal"), Key("CreateDate"), Key("ContentCreateDate"), Key("CreationDate"), Key("FileModifyDate"))), Empty()),
    "projection": First(Key("ProjectionType"), Empty()),
    "location": First(Dictionary({
        "latitude": GPSCoordinate(Key("GPSLatitude")),
        "longitude": GPSCoordinate(Key("GPSLongitude")),
    }), Empty())

})

DEFAULT_PROFILES = {
    "image": {
        "width": 1600,
        "scale": 1
    },
    "thumbnail": {
        "height": 240,
        "scale": 2
    },
}

EQUIRECTANGULAR_PROFILES = {
    "image": {
        "width": 10000,
        "scale": 1
    },
    "thumbnail": {
        "height": 240,
        "scale": 2
    },
}


def initialize_plugin(incontext):
    incontext.add_handler("import_photo", import_photo)


def import_photo(incontext, from_directory, to_directory, category, title_from_filename=True):

    @functools.wraps(import_photo)
    def inner(path):
        root, dirname, basename = utils.tripple(from_directory, path)
        return process_image(incontext, from_directory, to_directory, dirname, basename, category=category, title_from_filename=title_from_filename)

    return inner


def generate_identifier(basename):
    return os.path.splitext(basename)[0]


def exif(path):
    data = json.loads(subprocess.check_output(["exiftool", "-j", "-c", "%.10f", path]).decode('utf-8'))[0]

    # Load data from an EXIF sidecar if it exists.
    basename, ext = os.path.splitext(path)
    sidecar_path = basename + ".exif"
    logging.debug("Checking for EXIF sidecar at '%s'...", sidecar_path)
    if os.path.exists(sidecar_path):
        with open(sidecar_path, "r") as fh:
            sidecar = json.loads(fh.read())
            data = converters.merge_dictionaries(data, sidecar)

    return data


def load_image(path):
    """
    Safe method for loading PIL.Image instances with additional support for HEIF files.
    """

    # Check to see if we need to do special-case HEIF handling.
    # If we do, then we convert the file to an in-memory JPEG, that can then be opened using PIL.
    with open(path, 'rb') as fh:
        image_data = fh.read()
        format = whatimage.identify_image(image_data)
        if format in ['heic', 'avif']:
            heif_image = pyheif.read_heif(image_data)
            pi = Image.frombytes(mode=heif_image.mode, size=heif_image.size, data=heif_image.data)
            exif = None
            for metadata in heif_image.metadata or []:
                if metadata['type'] == 'Exif':
                    exif = metadata['data']
            stream = io.BytesIO()
            pi.save(stream, format="jpeg", exif=exif)
            return Image.open(stream)

    return Image.open(path)


def get_orientation(exif):
    try:
        exif = dict(exif.items())
        for orientation in ExifTags.TAGS.keys():
            if ExifTags.TAGS[orientation] == 'Orientation':
                break
        return exif[orientation]
    except:
        logging.debug("Unable to get get EXIF data")
        pass
    return 1


def get_size(source, scale):
    with load_image(source) as img:
        width, height = img.size
        try:
            exif = dict(img._getexif().items())
            for orientation in ExifTags.TAGS.keys():
                if ExifTags.TAGS[orientation] == 'Orientation':
                    break
            if exif[orientation] == 6 or exif[orientation] == 8:
                (width, height) = (height, width)
        except:
            pass
        return {"width": width / scale, "height": height / scale}


def get_details(root, dirname, basename, scale):
    details = get_size(os.path.join(root, dirname, basename), scale)
    details["filename"] = basename
    details["url"] = os.path.join("/", dirname, basename)
    return details


def imagemagick_resize(source, destination, size):
    convert_path = 'convert'
    try:
        convert_path = os.environ['INCONTEXT_CONVERT_PATH']
    except KeyError:
        pass

    command = [convert_path,
               '-verbose',
               '-quality', '75',
               '-auto-orient',
               '-resize', size,
               source + "[0]",
               destination]
    try:
        logging.debug("Running command '%s'...", utils.safe_command(command))
        result = subprocess.run(command,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        logging.debug(result)
    except subprocess.CalledProcessError as e:
        logging.error("Failed to run command '%s' with error '%s' (%s).",
                      " ".utils.safe_command(command), e.output, e)
        raise e


def gifsicle_resize(source, destination, size):
    """
    Resize a gif using the `gifsicle` command line utility (see [](https://www.lcdf.org/gifsicle/)).

    Resizing using animated gifs using ImageMagick will often produce very large output files and, in the case of
    incrementally encoded images, result in completely broken output.
    """
    command = ['gifsicle',
               '--resize', size,
               '--colors', '256',
               source]
    try:
        logging.debug("Running command '%s'...", utils.safe_command(command))
        result = subprocess.check_output(command)
        with open(destination, 'wb') as fh:
            fh.write(result)
    except subprocess.CalledProcessError as e:
        logging.error("Failed to run command '%s' with error '%s' (%s).",
                      " ".utils.safe_command(command), e.output, e)
        raise e


# TODO: Use this.
class Size(object):

    def __init__(self, width, height):
        self.width = width
        self.height = height


class Regex(object):

    def __init__(self, pattern, flags=0):
        self.expression = re.compile(pattern, flags)

    def evaluate(self, data):
        return self.expression.match(data) is not None


class Equal(object):

    def __init__(self, value):
        self.value = value

    def evaluate(self, data):
        return data == self.value


class Or(object):

    def __init__(self, *tests):
        self.tests = tests

    def evaluate(self, data):
        for test in self.tests:
            if test.evaluate(data):
                return True
        return False


class Glob(Or):

    def __init__(self, glob):
        patterns = [fnmatch.translate(p) for p in braceexpand.braceexpand(glob)]
        tests = [Regex(pattern, re.IGNORECASE) for pattern in patterns]
        super().__init__(*tests)


RESIZE_METHODS = [
    (Glob("*.gif"), gifsicle_resize),
    (Glob("*"), imagemagick_resize),
]


OUTPUT_MIME_TYPES = [
    (Glob("*.heic"), "image/jpeg"),
    (Glob("*.tiff"), "image/jpeg"),
    (Glob("*"), "*"),
]


def evaluate_tests(tests, data):
    for test, result in tests:
        if test.evaluate(data):
            return result
    raise KeyError(f"Failed to find match for '{data}'.")


def safe_resize(source, destination, size):
    """
    Determine a suitable resize handler to use when resizing (and converting an image) and run it.

    This makes use of `RESIZE_METHODS` to determine which resize handler to use.
    """
    resize_method = evaluate_tests(RESIZE_METHODS, os.path.basename(source))
    resize_method(source,
                  destination,
                  f"{size.width}x{size.height}")


# TODO: Make the API for this much cleaner.
# It should simply have a source and a destination.
# TODO: Where should the destination extension be?
def resize(source, dest_root, dest_dirname, dest_basename, size, scale):

    # Determine the desired output MIME type and extension.
    name, ext = os.path.splitext(dest_basename)
    destination_mime_type = evaluate_tests(OUTPUT_MIME_TYPES, os.path.basename(source))
    destination_extension = ext if destination_mime_type == "*" else mimetypes.guess_extension(destination_mime_type)
    dest_basename = f"{name}{destination_extension}"

    # TODO: This is almost certainly inefficient.
    # TODO: Perhaps this should be moved into the resize method?
    with load_image(source) as image:
        (source_width, source_height) = image.size
        logging.debug("Image source dimensions = %sx%s", source_width, source_height)

        # TODO: Move this into a separate utility for testing.

        # Determine the target dimensions.
        source_ratio = source_width / source_height
        (destination_width, destination_height) = size
        if destination_width is None and destination_height is None:
            (destination_width, destination_height) = (source_width, source_height)
        elif destination_width is None:
            destination_width = int(destination_height * source_ratio)
        elif destination_height is None:
            destination_height = int(destination_width / source_ratio)

        # Never make images larger.
        destination_width = min(destination_width, source_width)
        destination_height = min(destination_height, source_height)

        logging.debug("Image target dimensions = %sx%s", destination_width, destination_height)

        safe_resize(source,
                    os.path.join(dest_root, dest_dirname, dest_basename),
                    Size(width=destination_width,
                         height=destination_height))

    return get_details(dest_root, dest_dirname, dest_basename, scale)


# TODO: Rename the generate_thumbnail method as it's misleading #45
def generate_thumbnail(source, dest_root, dest_dirname, dest_basename, size, source_scale, scale):
    destination = os.path.join(dest_root, dest_dirname, dest_basename)
    return resize(source, dest_root, dest_dirname, dest_basename, size, scale)


def get_image_data(root, dirname, basename):
    with Image.open(os.path.join(root, dirname, basename)) as img:
        width, height = img.size
        return {"filename": basename, "width": width, "height": height}


def metadata_from_exif(path):
    """
    Generate a metadata dictionary from just the EXIF data contained within the file at `path`, as specified within
    `METADATA_SCHEMA`.
    """
    exif_data = exif(path)
    return METADATA_SCHEMA(exif_data)


def metadata_for_media_file(root, path, title_from_filename):
    metadata = converters.parse_path(path, title_from_filename=title_from_filename)
    exif_metadata = metadata_from_exif(os.path.join(root, path))
    metadata = converters.merge_dictionaries(metadata, exif_metadata)
    return metadata


def process_image(incontext, root, destination, dirname, basename, category, title_from_filename=True):
    source_path = os.path.join(root, dirname, basename)
    identifier = generate_identifier(basename)
    destination_dir = os.path.join(destination, dirname)
    destination_path = os.path.join(destination_dir, basename)
    markdown_path = os.path.join(destination_dir, "%s.markdown" % identifier)
    name, ext = os.path.splitext(basename)
    utils.makedirs(destination_dir)

    metadata = metadata_for_media_file(root, os.path.join(dirname, basename),
                                       title_from_filename=title_from_filename)

    # Determine which profiles to use; we use a different profile for equirectangular projections.
    # TODO: In an ideal world we would allow all of this special case behaviour to be configured in site.yaml
    #       so there are no custom modifications required to the script.
    profiles = DEFAULT_PROFILES
    if "projection" in metadata and metadata["projection"] == "equirectangular":
        profiles = EQUIRECTANGULAR_PROFILES

    # Generate the various different image sizes.
    # TODO: Consider making this common code for all images.
    for profile_name, profile_details in profiles.items():

        filename = "%s-%s%s" % (identifier, profile_name.replace("_", "-"), ext)
        if profile_name == "image":
            filename = "%s%s" % (identifier, ext)

        scale = 1
        if "scale" in profile_details:
            scale = profile_details["scale"]
        width = None
        if "width" in profile_details:
            width = profile_details["width"]
        height = None
        if "height" in profile_details:
            height = profile_details["height"]

        source_scale = metadata["scale"] if metadata["scale"] is not None else 1

        # TODO: Rename generate_thumbnail.
        metadata[profile_name] = generate_thumbnail(source_path,
                                                    destination, dirname, filename,
                                                    (width, height),
                                                    source_scale, scale)  # TODO: Why two scales?

    # Configure the page details.
    metadata["category"] = category
    metadata["template"] = "photo.html"  # TODO: Pass this in as a default.
    metadata["path"] = converters.ensure_leading_slash(os.path.join(dirname, basename))

    metadata_document = store.Document(metadata['url'], metadata, os.path.getmtime(source_path))
    incontext.environment["DOCUMENT_STORE"].add(metadata_document)

    files = [markdown_path] + [os.path.join(destination, dirname, metadata[f]["filename"]) for f in profiles.keys()]
    files = [os.path.join(destination, dirname, metadata[f]["filename"]) for f in profiles.keys()]
    return {'files': files, 'urls': [metadata['url']]}
