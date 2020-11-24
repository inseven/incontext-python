#!/usr/bin/env python3 -u
#
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

import argparse
import glob
import importlib
import logging
import os
import sys

SCRIPT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
PLUGINS_DIRECTORY = os.path.join(SCRIPT_DIRECTORY, "plugins")

verbose = '--verbose' in sys.argv[1:] or '-v' in sys.argv[1:]
logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, format="[%(levelname)s] %(message)s")

sys.path.append(PLUGINS_DIRECTORY)

class Configuration(object):

    def __init__(self):
        self._values = {}

    def add(self, name, value):
        self._values[name] = value

    def __getattr__(self, name):
        return self._values[name]


class Namespace:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class InContext(object):

    def __init__(self, plugins_directory):
        """
        Create a new InContext instance.

        @param plugins_directory: Path to the plugins directory.
        @type plugins_directory: str
        """
        self.plugins_directory = os.path.abspath(plugins_directory)
        self.plugins = {}
        self.handlers = {}
        self.tasks = {}
        self.environment = {}
        self.parser = None
        self.subparsers = []
        self.configuration_providers = {}
        self.configuration = Configuration()
        self.commands = {}

        # Load the plugins.
        for plugin in glob.glob(os.path.join(self.plugins_directory, "*.py")):
            identifier = os.path.splitext(os.path.relpath(plugin, self.plugins_directory))[0].replace('/', '_')
            self.plugins[identifier] = importlib.import_module(identifier, plugin)

        # Create the argument parser.
        self.parser = argparse.ArgumentParser(prog="incontext", description="Generate website.")
        self.parser.add_argument('--site', '-s', default=os.getcwd(), help="path to the root of the site")
        self.parser.add_argument('--verbose', '-v', action='store_true', default=False, help="show verbose output")
        self.parser.add_argument('--volume', action='append', help="mount an additional volume in the Docker container")
        self.subparsers = self.parser.add_subparsers(help="command to run")

        # Initialize the plugins.
        for plugin_name, plugin_instance in self.plugins.items():
            if hasattr(plugin_instance, 'initialize_plugin'):
                logging.debug("Initializing '%s'...", plugin_name)
                plugin_instance.initialize_plugin(self)
            else:
                logging.debug("Ignoring '%s'...", plugin_name)

    def add_argument(self, *args, **kwargs):
        """
        Add a global command-line argument.
        
        Primarily intended to be used by configuration providers to allow them to specify a path to a configuration
        file, or configuration override.
        """
        self.parser.add_argument(*args, **kwargs)

    def add_command(self, name, function, help=""):
        """
        Register a new command line command.

        The callable, function, will be called with the `argparse.ArgumentParser` sub-parser instance for that command as
        the first argument to allow the command to register any command-line arguments it requires. The command function
        must return a new callable which will be called if the the command is selected from the command line.

        @param name: The command identifier.
        @type name: str
        @param function: The function to be called to perform the registration.
        @type function: callable
        @param help: The help string that describes the command to be printed when the user passes the '--help' flag.
        @type help: str
        """
        parser = self.subparsers.add_parser(name, help=help)
        fn = function(self, parser)
        parser.set_defaults(fn=fn)

        def command_runner(**kwargs):
            fn(Namespace(**kwargs))

        self.commands[name] = command_runner

    def add_configuration_provider(self, name, function):
        """
        Add a named configuration provider.
        """
        self.configuration_providers[name] = function

    def add_task(self, name, function):
        if name in self.tasks:
            raise AssertionError("Task '%s' is already defined." % name)
        self.tasks[name] = function

    def get_task(self, name):
        """
        Return the task associated with `name`.
        
        Raises `KeyError` if no task has been registered with `name`.
        """
        return self.tasks[name]

    def add_handler(self, name, function):
        """
        Register a new handler.

        @param name: The handler identifier.
        @type name: str
        @param function: The function to be called.
        @type function: callable
        """
        if name in self.handlers:
            raise AssertionError("Handler '%s' is already defined." % name)
        self.handlers[name] = function

    def get_handler(self, name):
        """
        Return the handler for a given name.

        @param name: The handler identifier.
        @type name: str

        @return: Handler for a given name.
        @rtype: callable
        """
        return self.handlers[name]

    def run(self):
        """
        Parse the command line arguments and execute the requested command.
        """
        options = self.parser.parse_args()
        for name, configuration_provider in self.configuration_providers.items():
            self.configuration.add(name, configuration_provider(self, options))
        if 'fn' not in options:
            logging.error("No command specified.")
            exit(1)
        options.fn(options)


def main():
    """
    Entry-point for the InContext cli. Should not be called directly.
    """
    instance = InContext(plugins_directory=PLUGINS_DIRECTORY)
    instance.run()


if __name__ == "__main__":
    main()
