# Copyright (c) 2016-2020 InSeven Limited
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

import subprocess

import glob
import os

import jinja2

import incontext
import paths
import utils

INDEX_TEMPLATE = """
<!DOCTYPE html>
<html>
    <head>
    </head>
    <body>
        <h1>InContext<h1>
        <h2>Plugin Interface</h2>
        <ul>
        {% for module in modules %}
            <li><a href="{{ module }}.html">{{ module }}</a></li>
        {% endfor %}
        </ul>
    </body>
</html>
"""


@incontext.command("build-documentation", help="Build the documentation.",
                   arguments=[
                       incontext.CommandArgument("output", help="output directory"),
                   ])
def command_build_documentation(incontext, options):
    documentation_directory = os.path.abspath(options.output)
    
    with utils.Chdir(paths.SCRIPTS_DIR):
        
        # Look up the python files to document.
        files = glob.glob("*.py") + glob.glob("plugins/*.py")
        modules = [os.path.splitext(f)[0] for f in files]
        
        # Generate the Python documentation.
        for f in files:
            output_directory = os.path.join(documentation_directory, os.path.dirname(f))
            utils.makedirs(output_directory)
            subprocess.check_call(["pdoc", 
                                   "--html",
                                   "--output-dir", output_directory,
                                   "--force",
                                   f])
                              
        # Create an index page.
        with open(os.path.join(documentation_directory, "index.html"), "w") as fh:
            template = jinja2.Template(INDEX_TEMPLATE)
            fh.write(template.render(modules=modules))
