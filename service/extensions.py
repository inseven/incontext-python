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

import jinja2
import uuid

from jinja2 import nodes
from jinja2.ext import Extension

import converters
import converters


class SimpleExtension(Extension):

    def __init__(self, environment):
        super(SimpleExtension, self).__init__(environment)

    def parse(self, parser):
        lineno = next(parser.stream).lineno
        context = jinja2.nodes.ContextReference()
        return nodes.CallBlock(self.call_method('render',
                                                [context, parser.parse_expression()]),
                               [], [], "").set_lineno(lineno)


class Gallery(SimpleExtension):

    tags = set(['gallery'])

    def render(self, context, identifier, caller):
        template = self.environment.get_template("extensions/gallery.html")
        if identifier == '.':
            identifier = context["page"]["url"]
        identifier = converters.ensure_trailing_slash(identifier)
        if not identifier.startswith("/"):
            identifier = context["page"]["url"] + identifier
        return template.render(site=self.environment.site,
                               photos=self.environment.store.getall(parent=identifier))


class Video(SimpleExtension):

    tags = set(['video'])

    def render(self, context, path, caller):
        if not path.startswith("/"):
            path = context["page"]["url"] + path
        url = converters.parse_path(path)['url']
        template = self.environment.get_template("extensions/video.html")
        return template.render(site=self.environment.site,
                               video=self.environment.store.get(url))


class STL(SimpleExtension):

    tags = set(['stl'])

    def render(self, context, path, caller):
        if not path.startswith("/"):
            path = context["page"]["url"] + path
        template = self.environment.get_template("extensions/stl.html")
        return template.render(site=self.environment.site,
                               path=path,
                               uuid=str(uuid.uuid1()))
