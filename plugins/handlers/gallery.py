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

import collections
import copy
import functools
import io
import json
import logging
import mimetypes
import os
import os.path
import subprocess

import dateutil
import pyheif
import whatimage
import yaml

from PIL import Image, ExifTags

import converters
import expression
import paths
import store
import utils

from schema import Default, Dictionary, Empty, EXIFDate, First, GPSCoordinate, Key, String
from expression import And, Glob, Metadata, Or


IMAGE_HANDLER_TRANSFORM_PLUGIN = "app.incontext.image.transform"


DEFAULT_CONFIGURATION = {
    "profiles": {
        "default": [{
            "where": "glob('*.{heic,tiff}')",
            "transforms": [
                "resize('image', width=1600, format='image/jpeg', sets=['image', 'previews'])",
                "resize('thumbnail', width=480, format='image/jpeg', sets=['thumbnail', 'previews'])",
            ],
        }, {
            "where": "glob('*')",
            "transforms": [
                "resize('image', width=1600, sets=['image', 'previews'])",
                "resize('thumbnail', width=480, sets=['thumbnail', 'previews'])",
            ],
        }],
    },
}


METADATA_SCHEMA = Dictionary({

    "title": String(First(Key("Title"), Key("DisplayName"), Key("ObjectName"), Empty())),
    "content": First(Key("ImageDescription"), Key("Description"), Key("ArtworkContentDescription"), Default(None)),
    "date": First(EXIFDate(First(Key("DateTimeOriginal"), Key("ContentCreateDate"), Key("CreationDate"))), Empty()),
    "projection": First(Key("ProjectionType"), Empty()),
    "location": First(Dictionary({
        "latitude": GPSCoordinate(Key("GPSLatitude")),
        "longitude": GPSCoordinate(Key("GPSLongitude")),
    }), Empty())

})


class TransformResult(object):

    def __init__(self, files=[], documents=[]):
        self.files = files
        self.documents = documents


class Resize(object):

    def __init__(self, basename, width, sets, format="*"):
        self.basename = basename
        self.width = width
        self.format = format
        self.sets = sets

    def perform(self, source, destination):
        document = resize_simple(source, destination, (self.width, None))
        return TransformResult(files=[destination], documents=[document])


def initialize_plugin(incontext):
    incontext.add_configuration_provider("media", configuration_provider_media)
    incontext.add_handler("import_photo", import_photo)
    incontext.add_plugin(IMAGE_HANDLER_TRANSFORM_PLUGIN, "resize", Resize)


def configuration_provider_media(incontext, options):

    configuration = copy.deepcopy(DEFAULT_CONFIGURATION)
    try:
        with open(os.path.join(options.site, "media.yaml")) as fh:
            configuration = yaml.load(fh, Loader=yaml.SafeLoader)
    except FileNotFoundError:
        pass

    profiles = {}
    transforms_lookup = incontext.plugins(IMAGE_HANDLER_TRANSFORM_PLUGIN)
    for name, transforms in configuration["profiles"].items():
        profiles[name] = parse_transforms(transforms_lookup, transforms)
    configuration["profiles"] = profiles

    return configuration


def import_photo(incontext, from_directory, to_directory, category, title_from_filename=True):

    @functools.wraps(import_photo)
    def inner(path):
        root, dirname, basename = utils.tripple(from_directory, path)
        return process_image(incontext, from_directory, to_directory, dirname, basename, category=category, title_from_filename=title_from_filename)

    return inner


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


def get_details(root, dirname, basename, scale=1):
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


class Size(object):

    def __init__(self, width, height):
        self.width = width
        self.height = height


RESIZE_METHODS = [

    (And(Glob("*.gif", key="source"), Glob("*.gif", key="destination")),
        gifsicle_resize),
    (Glob("*", key="source"),
        imagemagick_resize),

]

def parse_transform(transforms_lookup, transform):
    structure = expression.parse_method(transform)
    instance = expression.structure_to_instance(transforms_lookup, structure)
    return instance


def parse_transforms(transforms_lookup, configuration):
    result = []
    for t in configuration:
        where = expression.parse_condition(t["where"])
        transforms = [parse_transform(transforms_lookup, transform) for transform in t["transforms"]]
        result.append((where, transforms))
    return result


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
    resize_method = evaluate_tests(RESIZE_METHODS, {"source": os.path.basename(source),
                                                    "destination": os.path.basename(destination)})
    resize_method(source,
                  destination,
                  f"{size.width}x{size.height}")


def resize_simple(source, destination, size):
    destination_root, destination_basename = os.path.split(destination)
    return resize(source, destination_root, "", destination_basename, size, 1)


def resize(source, dest_root, dest_dirname, dest_basename, size, scale):

    with load_image(source) as image:
        (source_width, source_height) = image.size
        logging.debug("Image source dimensions = %sx%s", source_width, source_height)

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


def extension_for_format(source, format):
    name, ext = os.path.splitext(source)
    return ext if format == "*" else mimetypes.guess_extension(format)


# TODO: Support named profiles in the image handler #114
#       https://github.com/inseven/incontext/issues/114
def process_image(incontext, root, destination, dirname, basename, category, title_from_filename=True):
    source_path = os.path.join(root, dirname, basename)

    metadata = metadata_for_media_file(root, os.path.join(dirname, basename),
                                       title_from_filename=title_from_filename)

    name, _ = os.path.splitext(basename)
    name = name.lower()
    destination_path = os.path.join(destination, dirname, name)
    utils.makedirs(destination_path)
    transform_files = []
    transform_metadata = collections.defaultdict(list)
    transforms = evaluate_tests(incontext.configuration.media["profiles"]["default"],
                                {"basename": os.path.basename(source_path),
                                 "metadata": metadata})
    for transform in transforms:
        transform_extension = extension_for_format(source_path, transform.format)
        transform_destination = os.path.join(destination_path, transform.basename) + transform_extension
        result = transform.perform(source=source_path, destination=transform_destination)
        if not isinstance(result, TransformResult):
            raise AssertionError("Invalid result type.")
        transform_files.extend(result.files)
        transform_documents = []
        for document in result.documents:
            document["filename"] = os.path.join(name, document["filename"])
            document["url"] = os.path.join("/", dirname, name) + document["url"]
            transform_documents.append(document)
        for set in transform.sets:
            transform_metadata[set].extend(transform_documents)

    metadata["category"] = category
    metadata["template"] = "photo.html"  # TODO: Pass this in as a default.
    metadata["path"] = converters.ensure_leading_slash(os.path.join(dirname, basename))
    for key, value in transform_metadata.items():
        metadata[key] = value if len(value) > 1 else value[0]  # Single arrays should be direct values.
    if metadata["scale"] is None:  # Ensure images have a scale.
        metadata["scale"] = 1

    metadata_document = store.Document(metadata['url'], metadata, os.path.getmtime(source_path))
    incontext.environment["DOCUMENT_STORE"].add(metadata_document)

    return {'files': transform_files, 'urls': [metadata['url']]}
