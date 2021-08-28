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

import contextlib
import http.server
import logging
import os
import signal
import subprocess
import sys
import urllib
import webbrowser

import watchdog.events
import watchdog.observers

import cli
import incontext
import paths
import utils

import commands.build


@incontext.command("serve", help="run a local web server for development", arguments=[
    cli.Argument("--port", "-p",
                 type=int, default=8000,
                 help="destination of the new site"),
    cli.Argument("--watch",
                 action="store_true", default=False,
                 help="watch for changes and rebuild automatically")
])
def command_serve(incontext, options):
    builder_context = commands.build.WatchingBuilder(incontext) if options.watch else contextlib.nullcontext()
    with builder_context, utils.Chdir(incontext.configuration.site.destination.files_directory):
        httpd = http.server.HTTPServer(('', options.port),
                                       http.server.SimpleHTTPRequestHandler)
        logging.info("Listening on %s...", options.port)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            return
