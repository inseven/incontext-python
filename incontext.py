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

import argparse
import collections
import glob
import importlib
import logging
import os
import sys

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
                parser.add_argument(*(argument.args), **(argument.kwargs))
            def callback(options):
                return self.callback(incontext, options)
            self._runner = callback
            return callback
        raise AssertionError("Unknown command callback type.")
        
    def run(self, **kwargs):
        return self._runner(Namespace(**kwargs))


class Argument(object):
    
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


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
        self.plugins_directory = os.path.abspath(plugins_directory)
        self.handlers = {}
        self.tasks = {}
        self.environment = {}
        self.parser = None
        self.subparsers = []
        self.configuration_providers = {}
        self.configuration = Configuration()
        self.plugins = _PLUGINS
        """
        Returns the registered plugins stored in a `_Plugins` instance.
        """

        # Load the plugins.
        sys.path.append(self.plugins_directory)
        plugins = {}
        for plugin in utils.find_files(self.plugins_directory, [".py"]):
            plugin = os.path.join(*plugin)
            (module, _) = os.path.splitext(os.path.relpath(plugin, self.plugins_directory))
            module = module.replace("/", ".")
            logging.debug("Importing '%s'...", module)
            plugins[module] = importlib.import_module(module)

        # Create the argument parser.
        self.parser = argparse.ArgumentParser(prog="incontext", description="Generate website.")
        self.parser.add_argument('--site', '-s', default=os.getcwd(), help="path to the root of the site")
        self.parser.add_argument('--verbose', '-v', action='store_true', default=False, help="show verbose output")
        self.parser.add_argument('--volume', action='append', help="mount an additional volume in the Docker container")
        self.subparsers = self.parser.add_subparsers(help="command to run")

        # Initialize the plugins.
        for plugin_name, plugin_instance in plugins.items():
            
            # Load the classic method-based plugins.
            if hasattr(plugin_instance, 'initialize_plugin'):
                logging.debug("Initializing legacy plugin '%s'...", plugin_name)
                plugin_instance.initialize_plugin(self)

            # Load the decorator-based plugins by copying in their 'global' state.
            if hasattr(plugin_instance, 'incontext'):
                logging.debug("Initializing plugin '%s'...", plugin_name)
                self.plugins.extend(plugin_instance.incontext._PLUGINS)
                
    @property
    def commands(self):
        return self.plugins.plugins(PLUGIN_TYPE_COMMAND)
                
    @property
    def context_functions(self):
        """
        Return a dictionary of additional context functions that will be available to the Jinja templating at render time.
        """
        return self.plugins.plugins(PLUGIN_TYPE_CONTEXT_FUNCTION)

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
        self.plugins.add_plugin(PLUGIN_TYPE_COMMAND, name, _CommandPlugin(name=name,
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

    def run(self, args=None):
        """
        Parse the command line arguments and execute the requested command.
        """
        
        # Prepare the commands for running.
        for command_plugin in self.plugins.plugins(PLUGIN_TYPE_COMMAND).values():
            parser = self.subparsers.add_parser(command_plugin.name, help=command_plugin.help)
            fn = command_plugin.configure(self, parser)
            parser.set_defaults(fn=fn)

        # Parse the arguments.       
        options = self.parser.parse_args(args)
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
