import argparse
import os


PREFLIGHT_PLUGINS = {}


class Command(object):

    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments
        def dummy_preflight(*args, **kwargs):
            pass
        self.preflight_callback = dummy_preflight

    def perform_preflight(self, container, args):
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("--port", "-p", default=8000)
        options, unknown = parser.parse_known_args(args)
        self.preflight_callback(container, options)


class Argument(object):

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def bind(self, parser):
        parser.add_argument(*(self.args), **(self.kwargs))


def parser():
    parser = argparse.ArgumentParser(prog="incontext", description="Generate website.", add_help=False)
    parser.add_argument('--help', '-h', default=False, action='store_true', help="show this help message and exit")
    parser.add_argument('--site', '-s', default=os.getcwd(), help="path to the root of the site")
    parser.add_argument('--verbose', '-v', action='store_true', default=False, help="show verbose output")
    parser.add_argument('--volume', action='append', help="mount an additional volume in the Docker container")
    parser.add_argument('--no-cache', action='store_true', default=False, help="skip Docker container cache")
    return parser


def preflight_plugin(name, arguments=[]):
    """
    Register a new preflight plugin.
    """
    def decorator(f):
        command = Command(name, arguments)
        command.preflight_callback = f
        PREFLIGHT_PLUGINS[name] = command
        return f
    return decorator
