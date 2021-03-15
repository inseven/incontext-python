#!/usr/bin/env python
#
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

import datetime
import logging
import os
import tempfile
import unittest
import subprocess
import sys

import common

import paths
import utils

sys.path.append(os.path.join(paths.PLUGINS_DIR, "handlers"))

import expression
import gallery

from expression import And, Equal, Glob, Metadata, Or, Regex


IMG_3857_HEIC = os.path.join(paths.TEST_DATA_DIRECTORY, "gallery/IMG_3857.heic")
IMG_3864_JPEG = os.path.join(paths.TEST_DATA_DIRECTORY, "gallery/IMG_3864.jpeg")
IMG_3870_HEIC = os.path.join(paths.TEST_DATA_DIRECTORY, "gallery/IMG_3870.heic")
IMG_3870_JPEG = os.path.join(paths.TEST_DATA_DIRECTORY, "gallery/IMG_3870.jpeg")
IMG_6218_TIFF = os.path.join(paths.TEST_DATA_DIRECTORY, "gallery/IMG_6218.tiff")
PREVIEW_GIF = os.path.join(paths.TEST_DATA_DIRECTORY, "gallery/preview.gif")


SITE_CONFIGURATION_WITH_IMAGE_HANDLER = {
    "config": {
        "title": "Example Site",
        "url": "https://example.com",
    },
    "paths": [],
    "build_steps": [{
        "task": "process_files",
        "args": {
            "handlers": [{
                "when": '.*',
                "then": "import_photo",
                "args": {
                    "category": "photos",
                }
            }]
        }
    }]
}


SITE_CONFIGURATION_WITH_COMMON_HANDLERS = {
    "config": {
        "title": "Example Site",
        "url": "https://example.com",
    },
    "paths": [],
    "build_steps": [{
        "task": "process_files",
        "args": {
            "handlers": [{
                "when": '.*\.(jpeg|jpg|png|tiff|)',
                "then": "import_photo",
                "args": {
                    "category": "photos",
                }
            }, {
                "when": "(.*/)?.*\.markdown",
                "then": "import_markdown",
            }]
        }
    }]
}


class GalleryTestCase(unittest.TestCase):

    def test_regex(self):

        self.assertEqual(Regex(r".*"), Regex(r".*"))
        self.assertNotEqual(Regex(r".*"), Regex(r".*", key="property"))
        self.assertEqual(Regex(r".*", key="property"), Regex(r".*", key="property"))
        self.assertNotEqual(Regex(r".*"), Regex(r"^.*"))

        self.assertTrue(Regex(r".*").evaluate("a"))
        self.assertTrue(Regex(r"hello").evaluate("hello"))
        self.assertFalse(Regex(r"hello").evaluate("goodbye"))
        self.assertTrue(Regex(r"hello").evaluate("hello world"))
        self.assertFalse(Regex(r"^hello$").evaluate("hello world"))
        self.assertTrue(Regex(r"hello", key="property").evaluate({"property": "hello"}))
        self.assertFalse(Regex(r"hello", key="property").evaluate({"property": "goodbye"}))

    def test_equal(self):
        self.assertTrue(Equal(True).evaluate(True))
        self.assertFalse(Equal(True).evaluate(False))
        self.assertTrue(Equal(12).evaluate(12))
        self.assertFalse(Equal(12).evaluate(13))
        self.assertFalse(Equal(18).evaluate("cheese"))
        self.assertTrue(Equal("cheese").evaluate("cheese"))
        self.assertFalse(Equal("cheese").evaluate("fromage"))
        self.assertFalse(Equal("cheese").evaluate(12))

    def test_or(self):
        self.assertTrue(Or(Equal(True)).evaluate(True))
        self.assertTrue(Or(Equal(True), Equal(False)).evaluate(True))
        self.assertTrue(Or(Equal(False), Equal(True)).evaluate(True))
        self.assertFalse(Or(Equal(False), Equal(False)).evaluate(True))
        self.assertTrue(Or(Equal(False), Equal(False)).evaluate(False))

    def test_glob(self):
        self.assertTrue(Glob("*.jpeg").evaluate({"basename": "IMG_3875.jpeg"}))
        self.assertFalse(Glob("*.tiff").evaluate({"basename": "IMG_3875.jpeg"}))
        self.assertTrue(Glob("*.{jpeg,tiff}").evaluate({"basename": "IMG_3875.jpeg"}))
        self.assertTrue(Glob("*.{jpeg,tiff}").evaluate({"basename": "IMG_3875.tiff"}))
        self.assertTrue(Glob("*.txt", key="source").evaluate({"source": "random.txt"}))
        self.assertFalse(Glob("*.ini", key="source").evaluate({"source": "random.txt"}))

    def test_glob_equality(self):
        self.assertEqual(Glob("*"), Glob("*"))
        self.assertNotEqual(Glob("*"), Glob("*.jpeg"))
        self.assertNotEqual(Glob("*"), Glob("*.{jpeg,heic}"))
        self.assertEqual(Glob("*.{jpeg,heic}"), Glob("*.{jpeg,heic}"))

    def test_evaluate_tests(self):
        tests = [
            (Glob("*.tiff"), "image/jpeg"),
            (Glob("*"), "*"),
        ]
        self.assertEqual(gallery.evaluate_tests(tests, {"basename": "IMG_3875.jpeg"}), "*")
        self.assertEqual(gallery.evaluate_tests(tests, {"basename": "IMG_3875.tiff"}), "image/jpeg")

    @common.with_temporary_directory
    def test_resize_heic(self):

        basename = os.path.basename(IMG_3870_HEIC)
        size = (1600, None)
        gallery.resize(IMG_3870_HEIC, os.getcwd(), "", basename, size, 1)

        expected_basename = utils.replace_extension(basename, ".heic")
        self.assertTrue(os.path.exists(expected_basename))
        output_size = gallery.get_size(expected_basename, 1)
        self.assertEqual(output_size["width"], size[0])

    @common.with_temporary_directory
    def test_resize_tiff(self):

        basename = os.path.basename(IMG_6218_TIFF)
        size = (1600, None)
        gallery.resize(IMG_6218_TIFF, os.getcwd(), "", basename, size, 1)

        expected_basename = utils.replace_extension(basename, ".tiff")
        self.assertTrue(os.path.exists(expected_basename))
        output_size = gallery.get_size(expected_basename, 1)
        self.assertEqual(output_size["width"], size[0])

    @common.with_temporary_directory
    def test_resize_jpeg(self):

        basename = os.path.basename(IMG_3870_JPEG)
        size = (800, None)
        gallery.resize(IMG_3870_JPEG, os.getcwd(), "", basename, size, 1)

        self.assertTrue(os.path.exists(utils.replace_extension(basename, ".jpeg")))
        output_size = gallery.get_size(basename, 1)
        self.assertEqual(output_size["width"], size[0])

    @common.with_temporary_directory
    def test_resize_gif(self):

        basename = os.path.basename(PREVIEW_GIF)
        size = (200, None)
        gallery.resize(PREVIEW_GIF, os.getcwd(), "", basename, size, 1)

        self.assertTrue(os.path.exists(utils.replace_extension(basename, ".gif")))
        output_size = gallery.get_size(basename, 1)
        self.assertEqual(output_size["width"], size[0])

    def test_parser_method(self):
        self.assertEqual(
            expression.parse_method("always()"),
            {"method": "always"}
        )
        self.assertEqual(
            expression.parse_method("glob('*')"),
            {"method": "glob", "args": ["*"]}
        )
        self.assertEqual(
            expression.parse_method("glob('*.{tiff,heic}')"),
            {"method": "glob", "args": ["*.{tiff,heic}"]}
        )
        self.assertEqual(
            expression.parse_method("glob(\"*\")"),
            {"method": "glob", "args": ["*"]}
        )
        self.assertEqual(
            expression.parse_method("glob(1024)"),
            {"method": "glob", "args": [1024]}
        )
        self.assertEqual(
            expression.parse_method("glob(1.5)"),
            {"method": "glob", "args": [1.5]}
        )
        self.assertEqual(
            expression.parse_method("glob(a='b')"),
            {"method": "glob", "kwargs": {"a": "b"}}
        )
        self.assertEqual(
            expression.parse_method("glob(a=\"b\")"),
            {"method": "glob", "kwargs": {"a": "b"}}
        )
        self.assertEqual(
            expression.parse_method("glob(a=12)"),
            {"method": "glob", "kwargs": {"a": 12}}
        )
        self.assertEqual(
            expression.parse_method("glob(a=3.142)"),
            {"method": "glob", "kwargs": {"a": 3.142}}
        )
        self.assertEqual(
            expression.parse_method("metadata(Projection='equirectangular', input='Cheese')"),
            {"method": "metadata", "kwargs": {"Projection": "equirectangular", "input": "Cheese"}}
        )
        self.assertEqual(
            expression.parse_method("metadata('cheese', Projection='equirectangular', input='Cheese')"),
            {"method": "metadata", "args": ["cheese"], "kwargs": {"Projection": "equirectangular", "input": "Cheese"}}
        )
        self.assertEqual(
            expression.parse_method("metadata('cheese', 42, Projection='equirectangular', input='Cheese')"),
            {"method": "metadata", "args": ["cheese", 42], "kwargs": {"Projection": "equirectangular", "input": "Cheese"}}
        )

        self.assertEqual(
            expression.parse_method("plugin([])"),
            {"method": "plugin", "args": [[]]}
        )

        self.assertEqual(
            expression.parse_method("plugin(1)"),
            {"method": "plugin", "args": [1]}
        )

        self.assertEqual(
            expression.parse_method("plugin('Hello')"),
            {"method": "plugin", "args": ["Hello"]}
        )

        self.assertEqual(
            expression.parse_method("plugin(13432.232)"),
            {"method": "plugin", "args": [13432.232]}
        )

        self.assertEqual(
            expression.parse_method("plugin([13432.232])"),
            {"method": "plugin", "args": [[13432.232]]}
        )

        self.assertEqual(
            expression.parse_method("plugin([13432.232, 3434, 'Hi!'])"),
            {"method": "plugin", "args": [[13432.232, 3434, "Hi!"]]}
        )

        self.assertEqual(
            expression.parse_method("plugin([13432.232, 3434, ['Hi!', 'Goodbye']])"),
            {"method": "plugin", "args": [[13432.232, 3434, ["Hi!", "Goodbye"]]]}
        )

    def test_parser(self):
        self.assertEqual(
            expression.parse_structure("always('hello') and never('goodbye') or maybe()"),
            {
                "method": "or",
                "args": [
                    {
                        "method": "and",
                        "args": [
                            {
                                "method": "always",
                                "args": ["hello"]
                            },
                            {
                                "method": "never",
                                "args": ["goodbye"]
                            }
                        ]
                    },
                    {
                        "method": "maybe"
                    }
                ]
            }
        )

        self.assertEqual(
            expression.parse_structure("(always('hello') and never('goodbye')) or maybe()"),
            {
                "method": "or",
                "args": [
                    {
                        "method": "and",
                        "args": [
                            {
                                "method": "always",
                                "args": ["hello"]
                            },
                            {
                                "method": "never",
                                "args": ["goodbye"]
                            }
                        ]
                    },
                    {
                        "method": "maybe"
                    }
                ]
            }
        )

        self.assertEqual(
            expression.parse_structure("always('hello') and (never('goodbye') or maybe())"),
            {
                "method": "and",
                "args": [
                    {
                        "method": "always",
                        "args": ["hello"]
                    },
                    {
                        "method": "or",
                        "args": [
                            {
                                "method": "never",
                                "args": ["goodbye"]
                            },
                            {
                                "method": "maybe",
                            }
                        ]
                    }
                ]
            }
        )

        self.assertEqual(
            expression.parse_condition("glob('*')"),
            Glob("*")
        )

        self.assertEqual(
            expression.parse_condition("glob('*') and metadata(projection='equirectangular')"),
            And(
                Glob("*"),
                Metadata(projection="equirectangular")
            )
        )

    def test_transform_image_heic_default_configuration(self):
        with common.TemporarySite(self) as site:
            site.add("templates/photo.html", "{{ page.title }}\n")
            site.add("site.yaml", SITE_CONFIGURATION_WITH_IMAGE_HANDLER)
            site.copy(IMG_3857_HEIC, "content/image.heic")
            site.build()
            site.assertBuildFiles(
                {
                    "image/thumbnail.jpg",
                    "image/image.jpg",
                    "image/index.html"
                }
            )
            site.assertMIMEType("build/files/image/image.jpg", "image/jpeg")
            site.assertImageSize("build/files/image/image.jpg", (1600, 2133))
            site.assertMIMEType("build/files/image/thumbnail.jpg", "image/jpeg")
            site.assertImageSize("build/files/image/thumbnail.jpg", (480, 640))

    def test_transform_image_jpeg_default_configuration(self):
        with common.TemporarySite(self) as site:
            site.add("templates/photo.html", "{{ page.title }}\n")
            site.add("site.yaml", SITE_CONFIGURATION_WITH_IMAGE_HANDLER)
            site.copy(IMG_3870_JPEG, "content/image.jpeg")
            site.build()
            site.assertBuildFiles(
                {
                    "image/thumbnail.jpeg",
                    "image/image.jpeg",
                    "image/index.html"
                }
            )
            site.assertMIMEType("build/files/image/image.jpeg", "image/jpeg")
            site.assertImageSize("build/files/image/image.jpeg", (1600, 1200))
            site.assertMIMEType("build/files/image/thumbnail.jpeg", "image/jpeg")
            site.assertImageSize("build/files/image/thumbnail.jpeg", (480, 360))

    def test_transform_image_tiff_default_configuration(self):
        with common.TemporarySite(self) as site:
            site.add("templates/photo.html", "{{ page.title }}\n")
            site.add("site.yaml", SITE_CONFIGURATION_WITH_IMAGE_HANDLER)
            site.copy(IMG_6218_TIFF, "content/image.tiff")
            site.build()
            site.assertBuildFiles(
                {
                    "image/thumbnail.jpg",
                    "image/image.jpg",
                    "image/index.html"
                }
            )
            site.assertMIMEType("build/files/image/image.jpg", "image/jpeg")
            site.assertImageSize("build/files/image/image.jpg", (1600, 1200))
            site.assertMIMEType("build/files/image/thumbnail.jpg", "image/jpeg")
            site.assertImageSize("build/files/image/thumbnail.jpg", (480, 360))

    def test_transform_image_gif_default_configuration(self):
        with common.TemporarySite(self) as site:
            site.add("templates/photo.html", "{{ page.title }}\n")
            site.add("site.yaml", SITE_CONFIGURATION_WITH_IMAGE_HANDLER)
            site.copy(PREVIEW_GIF, "content/image.gif")
            site.assertImageSize("content/image.gif", (800, 520))
            site.build()
            site.assertBuildFiles(
                {
                    "image/thumbnail.gif",
                    "image/image.gif",
                    "image/index.html"
                }
            )
            site.assertMIMEType("build/files/image/image.gif", "image/gif")
            site.assertImageSize("build/files/image/image.gif", (800, 520))  # Images shouldn't be get larger than the initial size.
            site.assertMIMEType("build/files/image/thumbnail.gif", "image/gif")
            site.assertImageSize("build/files/image/thumbnail.gif", (480, 312))

    def test_transform_image_jpeg_to_gif(self):
        with common.TemporarySite(self) as site:
            site.add("templates/photo.html", "{{ page.title }}\n")
            site.add("site.yaml", SITE_CONFIGURATION_WITH_IMAGE_HANDLER)
            site.add("media.yaml", {
                "profiles": {
                    "default": [{
                        "where": "glob('*')",
                        "transforms": [
                            "resize('preview', width=100, format='image/gif', sets=['preview'])",
                        ],
                    }],
                },
            })
            site.copy(IMG_3864_JPEG, "content/image.jpeg")
            site.build()
            site.assertBuildFiles({
                "image/preview.gif",
                "image/index.html"
            })
            site.assertMIMEType("build/files/image/preview.gif", "image/gif")
            self.assertEqual(site.store.get("/image/")['preview'], {
                'width': 100.0,
                'height': 133.0,
                'filename': 'image/preview.gif',
                'url': '/image/preview.gif'
            })
            site.assertImageSize("build/files/image/preview.gif", (100, 133))

    def test_transform_image_gif_to_jpeg(self):
        with common.TemporarySite(self) as site:
            site.add("templates/photo.html", "{{ page.title }}\n")
            site.add("site.yaml", SITE_CONFIGURATION_WITH_IMAGE_HANDLER)
            site.add("media.yaml", {
                "profiles": {
                    "default": [{
                        "where": "glob('*')",
                        "transforms": [
                            "resize('preview', width=100, format='image/jpeg', sets=['preview'])",
                        ],
                    }],
                },
            })
            site.copy(PREVIEW_GIF, "content/image.gif")
            site.build()
            site.assertBuildFiles({
                "image/preview.jpg",
                "image/index.html"
            })
            site.assertMIMEType("build/files/image/preview.jpg", "image/jpeg")
            self.assertEqual(site.store.get("/image/")['preview'], {
                'width': 100.0,
                'height': 65.0,
                'filename': 'image/preview.jpg',
                'url': '/image/preview.jpg'
            })
            site.assertImageSize("build/files/image/preview.jpg", (100, 65))

    def test_transform_image_with_no_matching_transform(self):
        with common.TemporarySite(self) as site:
            site.add("templates/photo.html", "{{ page.title }}\n")
            site.add("site.yaml", SITE_CONFIGURATION_WITH_IMAGE_HANDLER)
            site.add("media.yaml", {
                "profiles": {
                    "default": [{
                        "where": "glob('*.tiff')",
                        "transforms": [
                            "resize('preview', width=100, format='image/jpeg', sets=['preview'])",
                        ],
                    }],
                },
            })
            site.copy(IMG_3864_JPEG, "content/image.jpeg")
            with self.assertRaises(KeyError):
                site.build()

    def test_transform_image_with_no_transforms(self):
        with common.TemporarySite(self) as site:
            site.add("templates/photo.html", "{{ page.title }}\n")
            site.add("site.yaml", SITE_CONFIGURATION_WITH_IMAGE_HANDLER)
            site.add("media.yaml", {
                "profiles": {
                    "default": [],
                },
            })
            site.copy(IMG_3864_JPEG, "content/image.jpeg")
            with self.assertRaises(KeyError):
                site.build()

    def test_image_title_from_exif(self):
        with common.TemporarySite(self) as site:
            site.add("templates/photo.html", "{{ page.title }}")
            site.add("site.yaml", SITE_CONFIGURATION_WITH_IMAGE_HANDLER)
            site.copy(IMG_6218_TIFF, "content/image.tiff")
            site.build()
            site.assertExists("build/files/image/index.html")
            site.assertFileContents("build/files/image/index.html", "Theophany")

    def test_relative_img_src_rewrite(self):
        with common.TemporarySite(self) as site:
            site.add("site.yaml", SITE_CONFIGURATION_WITH_COMMON_HANDLERS)
            site.add("templates/photo.html", '{{ page.title }}')
            site.add("templates/post.html", '{{ page.html | safe }}')
            site.makedirs("content/gallery")
            site.copy(IMG_3864_JPEG, "content/gallery/image.jpeg")
            site.add("content/gallery/index.markdown", '<img src="image.jpeg">')
            site.build()
            site.assertExists("build/files/gallery/image/index.html")
            site.assertExists("build/files/gallery/image/image.jpeg")
            site.assertExists("build/files/gallery/image/thumbnail.jpeg")
            site.assertExists("build/files/gallery/index.html")
            site.assertFileContents("build/files/gallery/index.html", '<p><img src="/gallery/image/image.jpeg" srcset></p>\n')

    def test_relative_picture_source_srcset_rewrite(self):
        with common.TemporarySite(self) as site:
            site.add("site.yaml", SITE_CONFIGURATION_WITH_COMMON_HANDLERS)
            site.add("templates/photo.html", '{{ page.title }}')
            site.add("templates/post.html", '{{ page.html | safe }}')
            site.makedirs("content/gallery")
            site.copy(IMG_3864_JPEG, "content/gallery/image.jpeg")
            site.add("content/gallery/index.markdown", '<picture><source srcset="image.jpeg" media="(prefers-color-scheme: dark)" /><source srcset="image.jpeg" media="(prefers-color-scheme: light), (prefers-color-scheme: no-preference)" /><img src="image.jpeg" loading="lazy" /></picture>')
            site.build()
            site.assertExists("build/files/gallery/image/index.html")
            site.assertExists("build/files/gallery/image/image.jpeg")
            site.assertExists("build/files/gallery/image/thumbnail.jpeg")
            site.assertExists("build/files/gallery/index.html")
            site.assertFileContents("build/files/gallery/index.html", '<p><picture><source srcset="/gallery/image/image.jpeg" media="(prefers-color-scheme: dark)"></source><source srcset="/gallery/image/image.jpeg" media="(prefers-color-scheme: light), (prefers-color-scheme: no-preference)"></source><img src="/gallery/image/image.jpeg" loading="lazy" srcset></picture></p>\n')

    def test_relative_markdown_image_rewrite(self):
        with common.TemporarySite(self) as site:
            site.add("site.yaml", SITE_CONFIGURATION_WITH_COMMON_HANDLERS)
            site.add("templates/photo.html", '{{ page.title }}')
            site.add("templates/post.html", '{{ page.html | safe }}')
            site.add("templates/image.html", '<img src="{{ image.image.url }}">')
            site.makedirs("content/gallery")
            site.copy(IMG_3864_JPEG, "content/gallery/image.jpeg")
            site.add("content/gallery/index.markdown", '![](image.jpeg)')
            site.build()
            site.assertExists("build/files/gallery/image/index.html")
            site.assertExists("build/files/gallery/image/image.jpeg")
            site.assertExists("build/files/gallery/image/thumbnail.jpeg")
            site.assertExists("build/files/gallery/index.html")
            site.assertFileContents("build/files/gallery/index.html", '<p><img src="/gallery/image/image.jpeg"></p>\n')

# TODO: Check that images that don't exist don't break renders (in both regular tags and todos)
# TODO: Test that thumbnails have been created
# TODO: Test the srcsets
# TODO: Test that absolute path image URLs are not incorrectly fixed up
# TODO: Test that full URLs are not fixed up
# TODO: Test multiple images in a custom profile
# TODO: Test custom handler plugins
# TODO: Add end-to-end tests for metadata filtering
# TODO: Test that regular pages generate thumbnails and they exist correctly in the metadata
# TODO: Test default configuration
# TODO: Add a test for a page with a thumbnail (as this invokes special magic)
