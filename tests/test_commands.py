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
import os
import sys
import tempfile
import unittest

import common

import paths
import utils


class CommandsTestCase(unittest.TestCase):

    def test_create_test_site(self):
        with common.TemporarySite(self, configuration={}) as site:
            self.assertIsNotNone(site.path)
            self.assertTrue(os.path.exists(os.path.join(site.path, "site.yaml")))
            self.assertTrue(os.path.isdir(os.path.join(site.path, "content")))
            self.assertTrue(os.path.isdir(os.path.join(site.path, "templates")))

    def test_build_and_clean_empty_site(self):
        with common.TemporarySite(self) as site:
            site.add("site.yaml", {
                "config": {
                    "title": "Example Site",
                    "url": "https://example.com"
                },
                "paths": {},
                "build_steps": [{
                    "task": "process_files",
                    "args": {
                        "handlers": [],
                    }
                }],
            })
            site.assertNotExists("build")
            site.build()
            site.assertIsDir("build")
            site.clean()
            site.assertNotExists("build")

    def test_build_documentation(self):
        with tempfile.TemporaryDirectory() as path:
            self.assertEqual(len(utils.find(path)), 0)
            common.run_incontext(["build-documentation", path], plugins_directory=paths.PLUGINS_DIR)
            self.assertEqual(len(utils.find(path)), 31)

    def test_add_draft_and_publish_with_build(self):
        with common.TemporarySite(self) as site:
            site.add("site.yaml", {
                "config": {
                    "title": "Example Site",
                    "url": "https://example.com"
                },
                "paths": {
                    "drafts": "content/drafts",
                    "posts": "content/posts",
                },
                "build_steps": [{
                    "task": "process_files",
                    "args": {
                        "handlers": [{
                            "when": "(.*/)?.*\.markdown",
                            "then": "import_markdown",
                        }],
                    }
                }],
            })
            site.add("templates/post.html", "{{ page.title }}\n")
            site.assertNotExists("build")
            site.run(["add", "draft", "Cheese is wonderful"])
            site.assertExists("content/drafts/cheese-is-wonderful/index.markdown")
            site.build()
            self.assertTrue(os.path.exists(os.path.join(site.path, "build/files/drafts/cheese-is-wonderful/index.html")))
            site.run(["publish",
                      os.path.join(site.path, "content/drafts/cheese-is-wonderful")])
            today = datetime.date.today().strftime("%Y-%m-%d")
            site.assertIsDir(f"content/posts/{today}-cheese-is-wonderful")
            site.assertExists(f"content/posts/{today}-cheese-is-wonderful/index.markdown")
            site.build()
            site.assertNotExists("build/files/drafts/cheese-is-wonderful/index.html")
            site.assertExists(f"build/files/posts/{today}-cheese-is-wonderful/index.html")

    def test_copy_file_regex_syntax(self):
        with common.TemporarySite(self) as site:
            site.add("site.yaml", {
                "config": {
                    "title": "Example Site",
                    "url": "https://example.com"
                },
                "paths": {},
                "build_steps": [{
                    "task": "process_files",
                    "args": {
                        "handlers": [{
                            "when": "(.*/)?.*\.txt",
                            "then": "copy_file",
                        }],
                    }
                }],
            })
            site.touch("content/foo.txt")
            site.touch("content/example.markdown")
            site.build()
            site.assertExists("build/files/foo.txt")
            site.assertNotExists("build/files/example.markdown")

    def test_copy_file_multiple_regex_syntax(self):
        with common.TemporarySite(self) as site:
            site.add("site.yaml", {
                "config": {
                    "title": "Example Site",
                    "url": "https://example.com"
                },
                "paths": {},
                "build_steps": [{
                    "task": "process_files",
                    "args": {
                        "handlers": [{
                            "when": [
                                ".*\.txt",
                                ".*\.jpeg",
                            ],
                            "then": "copy_file",
                        }],
                    }
                }],
            })
            site.touch("content/foo.txt")
            site.touch("content/example.markdown")
            site.touch("content/image.jpeg")
            site.build()
            site.assertExists("build/files/foo.txt")
            site.assertExists("build/files/image.jpeg")
            site.assertNotExists("build/files/example.markdown")

    def test_ignore(self):
        with common.TemporarySite(self) as site:
            site.add("site.yaml", {
                "config": {
                    "title": "Example Site",
                    "url": "https://example.com"
                },
                "paths": {},
                "build_steps": [{
                    "task": "process_files",
                    "args": {
                        "handlers": [{
                            "when": [
                                ".*\.txt",
                            ],
                            "then": "ignore",
                        }, {
                            "when": [
                                ".*\.txt",
                            ],
                            "then": "copy_file",
                        }],
                    }
                }],
            })
            site.touch("content/foo.txt")
            site.build()
            site.assertNotExists("build/files/foo.txt")

    def test_loads_empty_site_plugin(self):
        with common.TemporarySite(self) as site:
            site.add("site.yaml", {
                "config": {
                    "title": "Example Site",
                    "url": "https://example.com"
                },
                "paths": {},
                "build_steps": [],
            })
            site.makedirs("plugins")
            site.add("plugins/example.py", """

def initialize_plugin(incontext):
    pass

""")
            site.build()

    def test_fail_to_load_invalid_site_plugin(self):
        with common.TemporarySite(self) as site:
            site.add("site.yaml", {
                "config": {
                    "title": "Example Site",
                    "url": "https://example.com"
                },
                "paths": {},
                "build_steps": [],
            })
            site.makedirs("plugins")
            site.add("plugins/example.py", """

def initialize_plugin(incontext):
    raise AssertionError("Boom!")

""")
            with self.assertRaises(AssertionError):
                site.build()

    # TODO: Test the decorator-based API for registering commands from site-plugins #117
    #       https://github.com/inseven/incontext/issues/117
    def test_site_plugin_with_additional_command(self):
        with common.TemporarySite(self) as site:
            site.add("site.yaml", {
                "config": {
                    "title": "Example Site",
                    "url": "https://example.com"
                },
                "paths": {},
                "build_steps": [],
            })
            site.makedirs("plugins")
            site.add("plugins/test_command.py", """

import logging

import incontext


def initialize_plugin(incontext):
    incontext.add_command("new-command", command_new_command)


def command_new_command(incontext, parser):
    def new_command(options):
        logging.info("success!")
    return new_command

""")
            site.run(["new-command"])

    @common.with_temporary_directory
    def test_new_site(self):
        common.run_incontext(["new", "example"], plugins_directory=paths.PLUGINS_DIR)
        site = common.Site(self, "example")
        site.assertExists("README.md")
        site.assertNotExists(".git")
        site.assertNotExists(".github")
        site.build()
        site.assertExists("build/files/index.html")
