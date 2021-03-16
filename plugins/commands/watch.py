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

import atexit
import http.server
import logging
import os
import signal
import subprocess
import sys
import threading
import time
import urllib
import webbrowser

import watchdog.events
import watchdog.observers

import incontext
import cli
import paths
import utils


class CallbackEventHandler(watchdog.events.FileSystemEventHandler):
    """Logs all the events captured."""

    def __init__(self, callback):
        self._callback = callback

    def on_moved(self, event):
        super(CallbackEventHandler, self).on_moved(event)
        self._callback()

    def on_created(self, event):
        self._callback()

    def on_deleted(self, event):
        self._callback()

    def on_modified(self, event):
        self._callback()


def watch_directory(paths, callback):
    observer = watchdog.observers.Observer()
    for path in paths:
        observer.schedule(CallbackEventHandler(callback=callback), path, recursive=True)
    observer.start()
    return observer


class Builder(threading.Thread):

    def __init__(self, incontext, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.incontext = incontext
        self.scheduled = False
        self.lock = threading.Lock()
        self.stopped = False

    def schedule(self):
        logging.info("Scheduling build...")
        with self.lock:
            self.scheduled = True

    def stop(self):
        logging.info("Stopping builder...")
        with self.lock:
            self.stopped = True

    def run(self):
        while True:
            time.sleep(1)
            scheduled = False
            with self.lock:
                if self.stopped:
                    return
                scheduled = self.scheduled
                self.scheduled = False
            if scheduled:
                try:
                    self.incontext.commands["build"].run()
                    logging.info("Done.")
                except Exception as e:
                    logging.error("Failed: %s", e)


def docker(command):
    prefix = []
    if sys.platform == "linux":
        prefix = ["sudo"]
    return subprocess.run(prefix + ["docker"] + command)


class WatchingBuilder(object):

    def __init__(self, incontext):
        self.incontext = incontext

    def start(self):
        self.builder = Builder(self.incontext)
        self.builder.start()
        logging.info("Watching directory...")
        self.observer = watch_directory([self.incontext.configuration.site.paths.content,
                                         self.incontext.configuration.site.paths.templates],
                                        self.builder.schedule)
        logging.info("Performing initial build...")
        self.builder.schedule()

    def stop(self):
        self.builder.stop()
        self.observer.stop()
        self.observer.join()
        self.builder.join()


@incontext.command("watch", help="watch for changes and automatically build the website")
def command_watch(incontext, options):
    builder = WatchingBuilder(incontext)
    builder.start()
    try:
        while True:
            time.sleep(0.2)
    except KeyboardInterrupt:
        builder.stop()


@incontext.command("serve", help="run a local web server for development", arguments=[
    cli.Argument("--port", "-p",
                 type=int, default=8000,
                 help="destination of the new site"),
    cli.Argument("--watch",
                 action="store_true", default=False,
                 help="watch for changes and rebuild automatically")
])
def command_serve(incontext, options):

    builder = None
    if options.watch:
        builder = WatchingBuilder(incontext)
        builder.start()

    with utils.Chdir(incontext.configuration.site.destination.files_directory):
        httpd = http.server.HTTPServer(('', options.port),
                                       http.server.SimpleHTTPRequestHandler)
        logging.info("Listening on %s...", options.port)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            if builder is not None:
                builder.stop()
