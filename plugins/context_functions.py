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

import datetime
import uuid

import dateutil
import pytz

import incontext


@incontext.context_function(name="now")
def now():
    """
    Return the current date in UTC.
    
    ```
    {% set d = now() %}
    {{ d }}
    ```
    
    This ensures the date has an associated timezone so it can be compared with other dates with timezone (as are found
    in fully specified [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) dates.
    """
    return datetime.datetime.utcnow().replace(tzinfo=pytz.utc)


@incontext.context_function(name="generate_uuid")
def generate_uuid():
    return str(uuid.uuid1())
    

@incontext.context_function(name="date")
def date(date):
    return dateutil.parser.parse(date).replace(tzinfo=pytz.utc)
