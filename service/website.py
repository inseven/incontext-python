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
import base64
import collections
import copy
import datetime
import functools
import hashlib
import itertools
import json as js
import logging
import os
import pytz
import random
import re
import struct
import sys
import time
import urllib.parse
import uuid

import dateutil.parser
import jinja2
import lxml.html
import misaka

from flask import Flask, Response, render_template, send_from_directory, send_file, abort, jsonify, request

logging.basicConfig(stream=sys.stderr)

import config
import converters
import extensions
import store
import utils


app = Flask(__name__)


class MyRenderer(misaka.SaferHtmlRenderer):

    def __init__(self, page):
        super(MyRenderer, self).__init__(flags=(),
                                         sanitization_mode='',
                                         nesting_level=0,
                                         link_rewrite=None,
                                         img_src_rewrite=None)
        self._page = page

    def rewrite_url(self, url, is_image_src=False):
        if is_image_src:
            o = urllib.parse.urlparse(url)
            if o.scheme == '' and o.netloc == '':
                # Insert a marker in markdown images to allow us to replace them with the image template for local images.
                return "+" + fixup_relative_url(url, self._page["path"])
        return fixup_relative_url(url, self._page["path"])

    def check_url(self, url, is_image_src=False):
        return True

    def header(self, content, level):
        return "<h%d><a id=\"%s\"></a>%s</h%d>" % (level, content.replace(' ', '-').lower(), content, level);


app.config.from_object(config.Configuration)


def initialize(templates_path, store_path, config):
    app.jinja_loader = jinja2.FileSystemLoader(templates_path)
    app.template_mtime = directory_mtime(templates_path)
    app.config["CONFIG"] = config
    app.config["STORE_PATH"] = store_path

    app.jinja_env.extend(site=Site())
    app.jinja_env.extend(store=store.DocumentStore(app.config["STORE_PATH"]))

    app.jinja_env.add_extension('extensions.Gallery')
    app.jinja_env.add_extension('extensions.Video')
    app.jinja_env.add_extension('extensions.TemplateExtension')


def directory_mtime(path):
    mtimes = []
    for root, dirs, files in os.walk(path):
        for name in files:
            mtimes.append(os.path.getmtime(os.path.join(root, name)))
    return max(mtimes) if mtimes else 0


def wrap_document(document):
    if document is None:
        return None
    if not "template" in document:
        document["template"] = "post.html"
    return DocumentWrapper(document)


def sort_posts(posts, ascending=False):
    posts_with_date = [post for post in posts if post.date is not None]
    posts_without_date = [post for post in posts if post.date is None]
    return sorted(posts_with_date, key=lambda x: x.sort_date, reverse=not ascending) + posts_without_date


class Site(object):

    def __init__(self):
        self.config = app.config["CONFIG"]
        self._cache = None
        self._cache_by_parent = None

    def load_cache(self):
        if self._cache is not None:
            return
        self._cache = dict()
        self._cache_by_parent = collections.defaultdict(list)
        for document in [wrap_document(document) for document in app.jinja_env.store.getall()]:
            self._cache[document.url] = document
            self._cache_by_parent[document["parent"]].append(document)

    def posts(self, include=None, exclude=None, parent=None, search=None, ascending=False, **kwargs):
        self.load_cache()
        cached_posts = None
        if include is None and exclude is None and parent is None and search is None and not kwargs:
            cached_posts = self._cache.values()
        elif include is None and exclude is None and search is None and not kwargs:
            cached_posts = self._cache_by_parent[parent]
        if cached_posts is not None:
            return sort_posts(cached_posts, ascending=ascending)
        return [wrap_document(document) for document in app.jinja_env.store.getall(include=include,
                                                                                   exclude=exclude,
                                                                                   parent=parent,
                                                                                   search=search,
                                                                                   asc=ascending,
                                                                                   **kwargs)]

    def post(self, url):
        self.load_cache()
        try:
            return self._cache[url]
        except KeyError:
            return None

    # TODO: Dependencies are not tracked for included image files.

    def __getitem__(self, key):
        return self.config[key]

    @property
    def last_modified(self):
        return app.jinja_env.store.last_modified


def normpath(path):
    if path.endswith("/"):
        path = path[:-1]
    if not path.startswith("/"):
        path = "/" + path
    return path


class ValueCache(object):

    def __init__(self, value):
        self.value = value


class QueryTracker(object):

    def __init__(self):
        self.queries = {}

    def add(self, parameters, documents):
        mtimes = [document.mtime for document in documents]
        self.queries[js.dumps(parameters)] = utils.hash_items(mtimes)

class DocumentWrapper(object):

    def __init__(self, document):
        self._document = document
        self._thumbnail = None
        self._siblings = None
        self.query_tracker = QueryTracker()

    def __getitem__(self, key):
        return self._document[key]

    def __getattr__(self, name):
        try:
            return self._document[name]
        except KeyError:
            if name == "date":
                return None
            raise AttributeError

    @property
    def hash(self):
        return utils.hash_items([self.mtime])

    @property
    def last_modified(self):
        return time.ctime(self.mtime)

    @property
    def parent(self):
        document = self._record_query({"type": "post", "url": self._document["parent"]})
        return document[0] if document else None

    @property
    def children(self):
        sort = self._document["sort"] if "sort" in self._document else "ascending"
        return self._record_query({"type": "children", "parent": self.url, "sort": sort})

    @property
    def siblings(self):
        return self._record_query({"type": "siblings", "parent": self._document["parent"]})

    @property
    def previous(self):
        document = self._record_query({"type": "previous", "parent": self._document["parent"]})
        return document[0] if document else None

    @property
    def next(self):
        document = self._record_query({"type": "next", "parent": self._document["parent"]})
        return document[0] if document else None

    def _record_query(self, parameters):
        documents = self._run_query(parameters)
        self.query_tracker.add(parameters, documents)
        for document in documents:
            document.query_tracker = self.query_tracker
        return documents

    def evaluate_queries(self, queries):
        hashes = []
        for query, digest in queries.items():
            parameters = js.loads(query)
            documents = self._run_query(parameters)
            hashes.append(utils.hash_items([document.mtime for document in documents]))
        return hashes

    def _run_query(self, parameters):
        if "type" not in parameters or parameters["type"] == "posts":
            include = parameters["include"] if "include" in parameters else None
            exclude = parameters["exclude"] if "exclude" in parameters else None
            ascending = parameters["sort"] == "ascending" if "sort" in parameters else True
            return app.jinja_env.site.posts(include=include, exclude=exclude, ascending=ascending)
        elif parameters["type"] == "children":
            parent = parameters["parent"]
            ascending = parameters["sort"] == "ascending" if "sort" in parameters else True
            return app.jinja_env.site.posts(parent=parent, ascending=ascending)
        elif parameters["type"] == "post":
            url = parameters["url"]
            document = app.jinja_env.site.post(url)
            return [document] if document is not None else []
        elif parameters["type"] == "siblings":
            if parameters["parent"] is None:
                return []
            return app.jinja_env.site.posts(parent=parameters["parent"])
        elif parameters["type"] == "previous":
            if parameters["parent"] is None:
                return []
            previous = []
            for index, document in enumerate(app.jinja_env.site.posts(parent=parameters["parent"])):
                if document.url == self.url:
                    return previous
                previous = [document]
            return []
        elif parameters["type"] == "next":
            if parameters["parent"] is None:
                return []
            found = False
            for index, document in enumerate(app.jinja_env.site.posts(parent=parameters["parent"])):
                if found:
                    return [document]
                if document.url == self.url:
                    found = True
            return []
        exit("Unsupported query with parameters '%s'" % (parameters, ))

    def query(self, identifier):
        parameters = None
        try:
            parameters = self._document["queries"][identifier]
        except KeyError:
            exit("Unknown query '%s'." % (identifier, ))
        return self._record_query(parameters)

    def abspath(self, path):
        if path == '.':
            return self.url
        if not path.startswith("/"):
            return self.url + path
        return path

    @property
    def content(self):
        if self._document["content"]:
            content = app.jinja_env.from_string(self._document["content"]).render(site=app.jinja_env.site,
                                                                                  page=self,
                                                                                  url=self.url)
            return content
        return None

    @property
    def html(self):
        content = self.content
        if content:
            return markdown(self._document)(content)
        return None

    @property
    def thumbnail(self):
        if self._thumbnail is None:
            def get_thumbnail():
                # Images are their own thumbnails.
                try:
                    return self._document["image"]
                except KeyError:
                    pass
                # Use any manually specified thumbnail.
                try:
                    return self._document["thumbnail"]
                except KeyError:
                    pass
                # Parse the HTML and look for a suitable thumbnail.
                html = self.html
                if html:
                    document = lxml.html.fromstring(html)
                    images = document.xpath("//img")
                    if images:
                        return {'url': images[0].get('src')}
                # See if any of the children have thumbnails.
                for child in self.children:
                    thumbnail = child.thumbnail
                    if thumbnail is not None:
                        return thumbnail
                return None
            self._thumbnail = ValueCache(get_thumbnail())
        return self._thumbnail.value

    @property
    def sort_date(self):
        return self.date.replace(tzinfo=None)


# Filters


@app.add_template_filter
def date(value, format='%Y-%d-%m'):
    return value.strftime(format)


@app.add_template_filter
def prepend(value, prefix):
    return prefix + value


@app.add_template_filter
def sort_by(items, key):
    return sorted(items, key=lambda item: item[key])


@app.add_template_filter
def json(object):
    return js.dumps(object)


@app.add_template_filter
def text(html):
    return " ".join(lxml.html.fromstring(html).text_content().split(" ")[:40])


@app.add_template_filter
def slice_list(items, start=0, stop=0):
    return itertools.islice(items, start, stop)


@app.add_template_filter
def rfc3339(date):
    if date.tzinfo is None:
        return date.replace(tzinfo=pytz.utc).isoformat()
    return date.isoformat()


@app.add_template_filter
def tag(identifier):
    if identifier in app.jinja_env.site.config['tags']:
        details = copy.deepcopy(app.jinja_env.site.config['tags'][identifier])
        details['identifier'] = identifier
        return details
    title, _ = converters.title_and_scale_from_path(identifier)
    return {'title': title, 'description': None, 'identifier': identifier}


@app.add_template_filter
def date_or_now(date):
    if date is not None:
        return date
    return datetime.datetime.now()


class DefaultAttributeWrapper(object):

    def __init__(self, wrapped, name, value):
        self.wrapped = wrapped
        self.name = name
        self.value = value

    def __getitem__(self, key):
        return self.__getattr__(key)

    def __getattr__(self, name):
        if name == self.name:
            try:
                value = self.wrapped.__getattr__(name)
                if value is None:
                    return self.value
                return value
            except AttributeError:
                return self.value
        elif name == f"{self.name}_original":
            return self.wrapped.__getattr__(self.name)
        return self.wrapped.__getattr__(name)


@app.add_template_filter
def attribute_with_default(wrapped, attribute, value):
    return [DefaultAttributeWrapper(w, attribute, value) for w in wrapped]


def filter_base64(string):
    return base64.b64encode(string.encode('utf-8')).decode('utf-8')


def filter_render_template(template, **kwargs):
    template = app.jinja_env.get_template(template)
    content = template.render(site=app.jinja_env.site, **kwargs)
    return content


app.add_template_filter(filter_base64, name='base64')
app.add_template_filter(filter_render_template, name='render_template')


def fixup_relative_url(url, page_path):
    o = urllib.parse.urlparse(url)
    if o.scheme == '' and o.netloc == '' and not o.path.startswith('/') and not url.startswith('#'):
        result = os.path.join(os.path.dirname(page_path), o.path)
        return result
    return url


def fixup_relative_image_srcset(srcset, page_path):
    if srcset is None:
        return None
    srcs = [re.split("\s+", src) for src in re.split('\s*,\s*', srcset)]
    for src in srcs:
        src[0] = fixup_relative_image_url(src[0], page_path)
    return ", ".join([" ".join(src) for src in srcs])


def fixup_relative_image_url(url, page_path):
    o = urllib.parse.urlparse(url)
    if o.scheme == '' and o.netloc == '' and not o.path.startswith('/') and not url.startswith('#'):
        path = os.path.join(os.path.dirname(page_path), o.path)
        image = app.jinja_env.store.getall(path=path)[0]
        return image["image"]["url"]
    return url


def markdown(page):
    def render(text):
        renderer = MyRenderer(page)
        markdown = misaka.Markdown(renderer, extensions=('fenced-code',
                                                         'smartypants',
                                                         'strikethrough',
                                                         'superscript',
                                                         'tables',
                                                         'footnotes'))
        content = misaka.smartypants(markdown(text))
        if not content:
            return content
        document = lxml.html.fromstring(content)
        for image in document.xpath("//img"):
            src = image.get('src')
            if src.startswith("+"):
                image_url = (os.path.splitext(src[1:])[0] + "/").lower()
                image_document = app.jinja_env.site.post(image_url)
                if image_document is None:
                    logging.error("Failed to get document for image '%s'" % (image_url, ))
                    continue
                template = app.jinja_env.get_template("image.html")
                title = None
                try:
                    title = image_document['title']
                except KeyError:
                    pass
                html = template.render(site=app.jinja_env.site,
                                       image=image_document)
                replacement_image = lxml.html.fromstring(html)
                parent = image.getparent()
                parent.insert(parent.index(image) + 1, replacement_image)
                parent.remove(image)
            else:
                image.set('src', fixup_relative_image_url(src, page["path"]))
                image.set('srcset', fixup_relative_image_srcset(image.get('srcset'), page["path"]))
        for source in document.xpath("//picture/source"):
            srcset = source.get('srcset')
            source.set('srcset', fixup_relative_image_url(srcset, page["path"]))
        for anchor in document.xpath("//a"):
            anchor.set('href', fixup_relative_url(anchor.get('href'), page["path"]))
        results = lxml.html.tostring(document, method='html', encoding='unicode')
        return results
    return render


# Decorators


def get_document(path):
    page = app.jinja_env.site.post(path)
    if not page:
        abort(404)
    return page


def local_path(path):
    return os.path.join(os.path.join(os.path.expanduser(app.config[config.keys.ROOT]), "files"), path[1:])

@app.route("/")
@app.route("/<path:path>")
def documents(path=""):
    path = normpath(path)
    path = converters.ensure_trailing_slash(path)
    page = get_document(path)
    page.query_tracker = QueryTracker()

    template_filename = page.template
    if template_filename.endswith(".json"):
        template = app.jinja_env.get_template(page.template)
        content = template.render(site=app.jinja_env.site,
                                  page=page,
                                  args=request.args)
        return app.response_class(
            response=content,
            status=200,
            mimetype="application/json"
        ), page.query_tracker

    headers = {
        'Last-Modified': app.jinja_env.site.last_modified,
        'Cache-Control': 'no-cache, must-revalidate',
    }

    content = render_template(page.template,
                              site=app.jinja_env.site,
                              page=page,
                              args=request.args,
                              markdown=markdown(page._document))

    return Response(content, headers=headers), page.query_tracker
