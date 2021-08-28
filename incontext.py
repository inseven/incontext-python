#!/usr/bin/env python3 -u
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

import collections
import copy
import glob
import logging
import os
import sys

import cli
import paths
import utils

verbose = '--verbose' in sys.argv[1:] or '-v' in sys.argv[1:]
logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, format="[%(levelname)s] %(message)s")

PLUGIN_TYPE_CONTEXT_FUNCTION = "context_function"
PLUGIN_TYPE_COMMAND = "command"

CALLBACK_TYPE_SETUP = "setup"
CALLBACK_TYPE_STANDALONE = "standalone"


class _CommandPlugin(object):

    def __init__(self, name, help, callback, callback_type, arguments=[]):
        self.name = name
        self.help = help
        self.callback = callback
        self.callback_type = callback_type
        self.arguments = arguments
        self._runner = None

    def configure(self, incontext, parser):
        if self.callback_type == CALLBACK_TYPE_SETUP:
            self._runner = self.callback(incontext, parser)
            return self._runner
        elif self.callback_type == CALLBACK_TYPE_STANDALONE:
            for argument in self.arguments:
                argument.bind(parser)
            def callback(options):
                return self.callback(incontext, options)
            self._runner = callback
            return callback
        raise AssertionError("Unknown command callback type.")

    def run(self, **kwargs):
        return self._runner(Namespace(**kwargs))


class _Plugins(object):
    """
    Centralised mechanism for storing references to plugins by type.

    InContext allows for plugins to be registered either module-wide (via to `incontext` decorators), or by providing
    an implementation of the `initialize_plugin` function and registering plugins directly with the `InContext`
    instance passed in. In both of these situations, registered plugins are stored in an instance of the `_Plugins` class.

    Instances of the `incontext` have a module-scoped instance of `_Plugins` (`incontext._PLUGINS`) which is added to the
    runtime instance using the `extend` method when plugins are loaded.
    """

    def __init__(self):
        self._plugins_by_type = collections.defaultdict(dict)

    def add_plugin(self, plugin_type, name, plugin):
        self._plugins_by_type[plugin_type][name] = plugin

    def plugin_types():
        return self._plugins_by_type.values()

    def plugins(self, plugin_type):
        return self._plugins_by_type[plugin_type]

    def plugin(self, plugin_type, name):
        return self._plugins_by_type[plugin_type][name]

    def extend(self, plugins):
        """
        Add all of the plugins in `plugins` (type `_Plugins`) to the current instance.
        """
        for plugin_type, plugin_plugins in plugins._plugins_by_type.items():
            for name, plugin in plugin_plugins.items():
                self.add_plugin(plugin_type, name, plugin)


_PLUGINS = _Plugins()
"""
Module-scoped plugin instances (used with decorator-based plugin registration).

Should not be manipulated directly.
"""


def context_function(name=None):
    """
    Register a new Jinja context function, to be made available at template render as `name`.

    If `name` is not specified, the function name is used.
    """
    def decorator(f):
        _PLUGINS.add_plugin(PLUGIN_TYPE_CONTEXT_FUNCTION, name if name is not None else f.__name__, f)
        return f
    return decorator


def command(name, help=None, arguments=[]):
    """
    Register a new command.
    """
    def decorator(f):
        _PLUGINS.add_plugin(PLUGIN_TYPE_COMMAND, name, _CommandPlugin(name=name,
                                                                      help=help,
                                                                      callback=f,
                                                                      callback_type=CALLBACK_TYPE_STANDALONE,
                                                                      arguments=arguments))
        return f
    return decorator


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
        self.handlers = {}
        self.tasks = {}
        self.environment = {}
        self.arguments = []
        self.configuration_providers = {}
        self.configuration = Configuration()
        self._plugins = copy.deepcopy(_PLUGINS)
        self._loaded_plugin_directories = {}

        # Load and initialize the plugins.
        self.load_plugins(os.path.abspath(plugins_directory))

    def load_plugins(self, directory):
        """
        Load and initialize the plugins in a given directory, adding them to the incontext instance.
        """
        directory = os.path.abspath(directory)
        if directory in self._loaded_plugin_directories:
            return
        self._loaded_plugin_directories[directory] = True
        plugins = utils.load_plugins(directory)
        for plugin_name, plugin_instance in plugins.items():

            # Load the classic method-based plugins.
            if hasattr(plugin_instance, 'initialize_plugin'):
                logging.debug("Initializing legacy plugin '%s'...", plugin_name)
                plugin_instance.initialize_plugin(self)

            # Load the decorator-based plugins by copying in their 'global' state.
            if hasattr(plugin_instance, 'incontext'):
                logging.debug("Initializing plugin '%s'...", plugin_name)
                self._plugins.extend(plugin_instance.incontext._PLUGINS)

    @property
    def commands(self):
        return self._plugins.plugins(PLUGIN_TYPE_COMMAND)

    @property
    def context_functions(self):
        """
        Return a dictionary of additional context functions that will be available to the Jinja templating at render time.
        """
        return self._plugins.plugins(PLUGIN_TYPE_CONTEXT_FUNCTION)

    def add_plugin(self, domain, name, plugin):
        """
        Add a plugin, `plugin`, named `name`, in the specified domain, `domain`.

        This is the generic mechanism by which plugins are able to themselves add extension points to InContext. For
        example, the image handling plugin makes use of this to allow other plugins to register custom transforms.
        """
        self._plugins.add_plugin(plugin_type=domain, name=name, plugin=plugin)

    def plugin(self, domain, name):
        """
        Get the plugin `name` in the domain, `domain`.
        """
        return self._plugins.plugin(plugin_type=domain, name=name)

    def plugins(self, domain):
        """
        Return a dictionary of all plugins in a specific domain, keyed by their name.
        """
        return self._plugins.plugins(plugin_type=domain)

    def add_argument(self, *args, **kwargs):
        """
        Add a global command-line argument.

        Primarily intended to be used by configuration providers to allow them to specify a path to a configuration
        file, or configuration override.
        """
        self.arguments.append(cli.Argument(*args, **kwargs))

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
        self._plugins.add_plugin(PLUGIN_TYPE_COMMAND, name, _CommandPlugin(name=name,
                                                                           help=help,
                                                                           callback=function,
                                                                           callback_type=CALLBACK_TYPE_SETUP))

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

    # TODO: Consider using the plugin architecture for registering handlers
    #       https://github.com/inseven/incontext/issues/110
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

    def parser(self, add_subparsers=True):
        """
        Return a parser, configured with the currently loaded plugins.
        """
        # Create the argument parser.
        parser = cli.parser()

        # Add the top-level arguments.
        for argument in self.arguments:
            parser.add_argument(*(argument.args), **(argument.kwargs))

        # Prepare the commands for running (if requested).
        if add_subparsers:
            subparsers = parser.add_subparsers(help="command to run")
            for command_plugin in self._plugins.plugins(PLUGIN_TYPE_COMMAND).values():
                subparser = subparsers.add_parser(command_plugin.name, help=command_plugin.help)
                fn = command_plugin.configure(self, subparser)
                subparser.set_defaults(fn=fn)

        return parser

    def run(self, args=None):
        """
        Parse the command line arguments and execute the requested command.
        """

        # Parse the top-level arguments, ignoring unknown arguments.
        parser = self.parser(add_subparsers=False)
        options, unknown = parser.parse_known_args(args)

        # Check to see if there are any site-local plugins.
        plugins_directory = os.path.join(os.path.abspath(options.site), "plugins")
        if os.path.exists(plugins_directory):
            logging.debug("Loading site plugins...")
            self.load_plugins(plugins_directory)

        # Re-parse the arguments, along with the sub-commands / sub-parsers.
        logging.debug("Re-processing arguments with sub-commands...")
        parser = self.parser()
        options = parser.parse_args(args)

        # Explicit handling of the help functionality.
        if options.help:
            parser.print_help()
            exit(1)

        # Handle the arguments, running the command if specified.
        for name, configuration_provider in self.configuration_providers.items():
            self.configuration.add(name, configuration_provider(self, options))
        if 'fn' not in options:
            logging.error("No command specified.")
            exit(1)
        options.fn(options)


def main():
    """
    Entry-point for the command line. Should not be called directly.
    """
    instance = InContext(plugins_directory=paths.PLUGINS_DIR)
    instance.run(sys.argv[1:])


if __name__ == "__main__":
    main()
