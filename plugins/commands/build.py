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

import codecs
import functools
import importlib.util
import json
import logging
import os
import re
import shutil
import subprocess

import fnmatch
import yaml

import converters
import handlers.gallery as gallery
import incontext
import paths
import store
import tracker
import utils


DOCUMENT_STORE = "DOCUMENT_STORE"


def initialize_plugin(incontext):
    incontext.add_argument("--set", type=str, help="override configuration parameters")
    incontext.add_configuration_provider("site", configuration_provider_site)
    incontext.add_handler("import_markdown", import_markdown)
    incontext.add_task("process_files", process_files)


class SiteConfiguration(object):

    def __init__(self, path, overrides={}):
        self._path = os.path.abspath(path)
        self._root = os.path.dirname(self._path)
        self._overrides = overrides
        self._loaded = False
            
    def _load_configuration(self):
        if self._loaded:
            return
        self._loaded = True
        with open(self._path) as fh:
            self._config = yaml.load(fh, Loader=yaml.SafeLoader)
        for key, value in self._overrides.items():
            logging.info("%s=%s" % (key, value))
            keys = key.split(".")
            destination = self._config
            for key in keys[:-1]:
                destination = destination[key]
            destination[keys[-1]] = value

    @property
    def root(self):
        return self._root

    @property
    def build_steps(self):
        self._load_configuration()
        return self._config["build_steps"]

    @property
    def config(self):
        self._load_configuration()
        return self._config["config"]

    @property
    def paths(self):
        self._load_configuration()
        paths = {
            "content": "content",
            "build": "build",
            "templates": "templates",
        }
        paths.update(self._config["paths"])
        # TODO: Ensure the paths in site.yaml are under the root (https://github.com/inseven/incontext/issues/60)
        return utils.PropertyDictionary({name: os.path.join(self._root, os.path.expanduser(path))
                                         for name, path in paths.items()})

    @property
    def destination(self):
        self._load_configuration()
        return utils.PropertyDictionary({
            "root_directory": self.paths.build,
            "files_directory": os.path.join(self.paths.build, "files"),
            "store_path": os.path.join(self.paths.build, "store.sqlite"),
        })


def touch(path):
    with open(path, 'a'):
        os.utime(path)


def configuration_provider_site(incontext, options):
    overrides = {}

    # Process overrides from the environment.
    try:
        environment_config = os.environ["INCONTEXT_CONFIG"]
        environment_sets = environment_config.split(";")
        overrides = {key: value for key, value in [set.split("=", 1) for set in environment_sets]}
    except KeyError:
        pass

    # Process overrides from the command line.
    if options.set:
        sets = [options.set]
        for key, value in [set.split("=", 1) for set in sets]:
            overrides[key] = value

    return SiteConfiguration(os.path.join(os.path.abspath(options.site), "site.yaml"), overrides)


def process_files(incontext, options, handlers):
    document_store = store.DocumentStore(incontext.configuration.site.destination.store_path)
    incontext.environment[DOCUMENT_STORE] = document_store

    logging.info("Generating intermediates...")
    phase1 = Phase(os.path.join(incontext.configuration.site.destination.root_directory, "phase-1-generate-intermediates.json"),
                   incontext.configuration.site.paths.content,
                   document_store)
    for task in handlers:
        fn = incontext.get_handler(task["then"])
        args = task["args"] if "args" in task else {}
        phase1.add_task(task['when'], fn(incontext,
                                         from_directory=incontext.configuration.site.paths.content,
                                         to_directory=incontext.configuration.site.destination.files_directory,
                                         **args))
    phase1.process()

    # Renders are dependent on the templates, so we hash all the templates and add this into the hash for the page
    # renders to ensure everything is re-rendered whenever a template changes. It should be possible to track the
    # templates used in render in the future if we need to make this faster.
    templates = [os.path.join(*paths) for paths in utils.find_files(incontext.configuration.site.paths.templates)]
    template_mtimes = [os.path.getmtime(path) for path in templates]
    template_hash = utils.hash_items(template_mtimes)

    logging.info("Render content cache...")
    cache_path = os.path.join(incontext.configuration.site.destination.root_directory, "phase-6-render-content.json")
    render_change_tracker = tracker.ChangeTracker(cache_path)
    website = Website(incontext=incontext)
    for document in website.documents():
        def render_outer(document):
            def render(url):
                path, queries, hashes = website.render(document=document)
                return {"files": [path],
                        "queries": queries,
                        "mtime": utils.hash_items([template_hash, document.hash] + hashes)}
            return render
        queries = {}
        try:
            queries = render_change_tracker.get_info(path=document.url)["queries"]
        except KeyError:
            pass
        hash = utils.hash_items([template_hash, document.hash] + document.evaluate_queries(queries))
        render_change_tracker.add(path=document.url, create=render_outer(document), mtime=hash)
    render_change_tracker.commit(cleanup(root=incontext.configuration.site.destination.root_directory,
                                         document_store=document_store))

    touch(incontext.configuration.site.destination.store_path)


class Website(object):

    def __init__(self, incontext):
        self.incontext = incontext
        self.service_directory = paths.SERVICE_DIR
        self.templates_path = incontext.configuration.site.paths.templates
        self.service_path = os.path.join(self.service_directory, "website.py")
        self.files_directory = incontext.configuration.site.destination.files_directory
        with utils.Chdir(self.service_directory):
            website_spec = importlib.util.spec_from_file_location("website", self.service_path)
            website = importlib.util.module_from_spec(website_spec)
            website_spec.loader.exec_module(website)
            self.website = website
            for name, f in incontext.context_functions.items():
                self.website.app.jinja_env.globals.update(**{name: f})
            self.website.initialize(templates_path=self.templates_path,
                                    store_path=incontext.configuration.site.destination.store_path,
                                    config=incontext.configuration.site.config)

    def documents(self):
        with utils.Chdir(self.service_directory):
            return self.website.app.jinja_env.site.posts()

    def render(self, document):
        with utils.Chdir(self.service_directory) as current_directory, self.website.app.test_request_context():
            logging.info("[render] %s", document.url)
            response, query_tracker = self.website.documents(path=document.url)
            hashes = [hash for query, hash in query_tracker.queries.items()]
            _, extension = os.path.splitext(document.template)
            destination_directory = os.path.join(self.files_directory, document.url[1:])
            destination = os.path.join(destination_directory, "index" + extension)
            utils.makedirs(destination_directory)
            with open(destination, "wb") as fh:
                fh.write(response.data)
            return destination, query_tracker.queries, hashes


@incontext.command("build", help="build the website")
def command_build(incontext, options):

    # Create the build directory.
    utils.makedirs(incontext.configuration.site.destination.root_directory)

    # Run the build tasks.
    for task in incontext.configuration.site.build_steps:
        identifier, args = task["task"], task["args"] if "args" in task else {}
        logging.info("Running task '%s'..." % identifier)
        incontext.get_task(identifier)(incontext, options, **args)


@incontext.command("clean", help="remove the build directory")
def command_clean(incontext, options):

    build_dir = incontext.configuration.site.destination.root_directory
    if not os.path.exists(build_dir):
        logging.info("Nothing to do.")
        return

    logging.info("Removing '%s'..." % build_dir)
    shutil.rmtree(build_dir)


def import_markdown(incontext, from_directory, to_directory, default_category='general'):

    @functools.wraps(import_markdown)
    def inner(path):
        root, dirname, basename = utils.tripple(from_directory, path)
        document = converters.frontmatter_document(root,
                                                   os.path.join(dirname, basename),
                                                   default_category=default_category)

        files = []

        # Thumbnail.
        try:
            if isinstance(document["thumbnail"], str):  # work-around for legacy photo handling
                thumbnail_src = os.path.normpath(os.path.join(from_directory, dirname, document["thumbnail"]))
                name, ext = os.path.splitext(basename)
                thumbnail_basename = "%s-thumbnail.jpg" % (name, )

                # Ensure the destination directory exists.
                # This is designed to fail if the destination path exists, but is not a directory.
                target_directory = os.path.join(to_directory, dirname)
                utils.makedirs(target_directory)

                document.metadata['thumbnail'] = gallery.resize(thumbnail_src,
                                                                to_directory,
                                                                dirname,
                                                                thumbnail_basename,
                                                                (None, 500),
                                                                2)
                files.append(os.path.join(to_directory, dirname, thumbnail_basename))
        except KeyError:
            pass

        incontext.environment[DOCUMENT_STORE].add(document)
        return {'files': files, 'urls': [document.url]}

    return inner


def cleanup(root, document_store):
    def inner(info):
        if 'files' in info:
            for file in info['files']:
                if isinstance(file, str) and os.path.exists(file):
                    logging.info("[clean] %s" % os.path.relpath(file, root))
                    os.remove(file)
        if 'urls' in info:
            for url in info['urls']:
                logging.info("[clean] %s" % url)
                document_store.delete(url)
    return inner


class Phase(object):

    def __init__(self, cache, root, document_store):
        self.cache = cache
        self.root = root
        self.document_store = document_store
        self.tasks = []
        self.tracker = tracker.ChangeTracker(self.cache)

    def add_task(self, pattern, task):
        self.tasks.append((pattern, task))

    @property
    def paths(self):
        return self.tracker.paths

    def process(self):
        for root, dirname, basename in utils.find_files(self.root):
            relpath = os.path.join(dirname, basename)
            for pattern, task in self.tasks:
                if re.search("^%s$" % pattern, relpath, re.IGNORECASE):
                    def debug_task(task, relpath):
                        @functools.wraps(task)
                        def inner(path):
                            logging.info("[%s] %s" % (task.__name__, relpath))
                            return task(path)
                        return inner
                    self.tracker.add(os.path.join(root, dirname, basename), debug_task(task, relpath))
                    break
        self.tracker.commit(cleanup(self.root, self.document_store))
