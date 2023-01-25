# Copyright (c) 2016-2023 InSeven Limited
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

import logging
import uuid

import jinja2

from jinja2 import nodes
from jinja2.ext import Extension

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


class TemplateExtension(Extension):

    tags = {"template"}

    def __init__(self, environment):
        super(TemplateExtension, self).__init__(environment)

    def parse(self, parser):
        lineno = next(parser.stream).lineno
        parameters = [parser.parse_expression()]

        while parser.stream.look().type != "data" and parser.stream.look().type != "eof":
            key = parser.parse_expression()
            assert parser.stream.skip_if("colon")
            value = parser.parse_expression()
            parameters.extend([jinja2.nodes.Const(key.name), value])
            parser.stream.skip_if("comma")

        context = jinja2.nodes.ContextReference()
        args = [context, jinja2.nodes.List(parameters)]
        return nodes.CallBlock(self.call_method('render', args), [], [], "").set_lineno(lineno)

    def render(self, context, parameters, caller):
        template = parameters.pop(0)
        args = {}
        while parameters:
            key = parameters.pop(0)
            value = parameters.pop(0)
            args[key] = value
        template = self.environment.get_template(template)
        return template.render(site=self.environment.site, page=context["page"], **args)
