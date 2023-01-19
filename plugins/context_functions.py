# Copyright (c) 2016-2023 Jason Barrie Morley
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

import datetime
import uuid

import dateutil
import pytz

import incontext


@incontext.context_function(name="now")
def now():
    """
    Return the current date in UTC.

    For example,

    ```
    <p>Rendered at {{ now() }}.</p>
    ```

    If you need to use the exact same date more than once in a render, set it as a variable as follows:

    ```
    {% set d = now() %}
    {{ d }}
    ```

    This ensures the date has an associated timezone so it can be compared with other dates with timezone (as are found
    in fully specified [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) dates).
    """
    return datetime.datetime.utcnow().replace(tzinfo=pytz.utc)


@incontext.context_function(name="generate_uuid")
def generate_uuid():
    """
    Return a new UUID.

    Intended to make it easy to generate unique identifiers when writing inline HTML and JavaScript.

    For example,

    ```
    {% set uuid = generate_uuid() %}
    <div id="{{ uuid }}">
        Your content here.
    </div>
    <button onclick="toggleVisibility('{{ uuid }}')">Toggle Content</button>
    ```
    """
    return str(uuid.uuid1())


@incontext.context_function(name="date")
def date(timestr, timezone_aware=True):
    """
    Return a date corresponding with a specific string representation, `timestr`.

    For example,

    ```
    {% set d = date("1982-12-28") %}
    {{ d }}
    ```

    Like `now`, this guarantees that the returned date has an associated timezone to allow safe comparison.
    """
    date = dateutil.parser.parse(timestr)
    if timezone_aware:
        return date.replace(tzinfo=pytz.utc)
    return date.replace(tzinfo=None)


@incontext.context_function(name="distant_past")
def distant_past(timezone_aware=True):
    return date("1900-01-01", timezone_aware=timezone_aware)
