import argparse
import os


class Command(object):

    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments


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
    return parser
