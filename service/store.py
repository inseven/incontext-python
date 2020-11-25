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

import datetime
import json
import logging
import os.path
import sqlite3
import time

import dateutil.parser

METDATA_VERSION_KEY = 1


class Store(object):

    def __init__(self, path, version, update):
        self.path = path

        self.connection = sqlite3.connect(path)
        self.connection.execute("CREATE TABLE IF NOT EXISTS metadata (identifier INTEGER PRIMARY KEY, version INTEGER)")
        self.connection.commit()

        current_version = self.version()
        if current_version != version:
            success = update(self.connection, current_version)
            if not success:
                raise AssertionError("Unable to update database from version %d" % current_version)
            self.connection.execute("INSERT OR REPLACE INTO metadata VALUES (?, ?)", (METDATA_VERSION_KEY, version))
            self.connection.commit()

        self.last_modified = time.ctime(os.path.getmtime(path))

    def version(self):
        cursor = self.connection.cursor()
        cursor.execute("SELECT version FROM metadata WHERE identifier = ? LIMIT 1", (METDATA_VERSION_KEY,))
        row = cursor.fetchone()
        if row is not None:
            return row[0]
        return None


class Document(object):

    def __init__(self, url, data, mtime):
        self.url = url
        self.metadata = data
        self.date = None
        self.mtime = mtime
        self._fixup_metadata()

    def _fixup_metadata(self):
        if "category" in self.metadata:
            self.type = self.metadata["category"]
            del self.metadata["category"]
        else:
            # TODO: Consider removing this fix-up.
            self.type = "general"
        if "date" in self.metadata:
            self.date = self.metadata["date"]
            del self.metadata["date"]
        if "content" in self.metadata:
            self.content = self.metadata["content"]
            del self.metadata["content"]
        if "url" in self.metadata:
            self.url = self.metadata["url"]

    def __getitem__(self, key):
        return self.metadata[key]

    def __setitem__(self, key, value):
        self.metadata[key] = value
        self._fixup_metadata()

    def __getattr__(self, key):
        return self.metadata[key]


DOCUMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS documents (
    url TEXT PRIMARY KEY,
    parent TEXT,
    type TEXT,
    date DATETIME,
    metadata TEXT,
    contents TEXT,
    mtime DATETIME
)
"""


class DateTimeEncoder(json.JSONEncoder):
        #Override the default method
        def default(self, obj):
            if isinstance(obj, (datetime.date, datetime.datetime)):
                return obj.isoformat()
                logging.info(date)


def date_time_decoder(dictionary):
    result = {}
    for key, value in dictionary.items():
        result[key] = value
        if isinstance(value, str):
            try:
                result[key] = dateutil.parser.isoparse(value)
            except ValueError:
                pass
    return result


class DocumentStore(Store):

    def __init__(self, path):

        def update(connection, from_version):
            connection.execute(DOCUMENTS_TABLE)
            return True

        super(DocumentStore, self).__init__(path, 4, update)

    def add(self, *documents):
        for document in documents:
            try:
                self.connection.execute("INSERT OR REPLACE INTO documents VALUES (?, ?, ?, ?, ?, ?, ?)",
                                        (document.url,
                                         document.parent,
                                         document.type,
                                         document.date,
                                         DateTimeEncoder().encode(document.metadata),
                                         document.content,
                                         document.mtime))
                self.connection.commit()
            except sqlite3.InterfaceError:
                print(document)
                raise

    def deleteall(self):
        self.connection.execute("DELETE FROM documents")
        self.connection.commit()

    def delete(self, url):
        self.connection.execute("DELETE FROM documents WHERE url = ?", (url, ))
        self.connection.commit()

    def documents(self, query, *args):
        cursor = self.connection.cursor()
        cursor.execute(query, *args)
        rows = cursor.fetchall()
        results = []
        for row in rows:
            metadata = json.loads(row[4], object_hook=date_time_decoder)
            if row[3]:
                metadata["date"] = dateutil.parser.parse(row[3])
            metadata["category"] = row[2]
            metadata["content"] = row[5]
            metadata["url"] = row[0]
            metadata["parent"] = row[1]
            metadata["mtime"] = row[6]
            results.append(metadata)
        return results

    def get(self, url):
        documents = self.documents("SELECT * FROM documents WHERE url = ? LIMIT 1", (url,))
        if documents:
            return documents[0]
        return None

    def getall(self, parent=None, include=None, exclude=None, offset=None, count=None, search=None, asc=True, **kwargs):
        where = ""
        wheres = []
        bindings = []
        if exclude:
            excludes = ["type != ?" for e in exclude]
            wheres.append("(%s)" % " AND ".join(excludes))
            bindings.extend(exclude)
        if include:
            includes = ["type = ?" for i in include]
            wheres.append("(%s)" % " OR ".join(includes))
            bindings.extend(include)
        if parent:
            wheres.append("parent = ?")
            bindings.append(parent)
        if search:
            for word in search.split():
                wheres.append("contents like ?")
                bindings.append("%%%s%%" % word)
        if kwargs:
            for key, value in kwargs.items():
                wheres.append("json_extract(metadata, '$.%s') = ?" % key)
                bindings.append(value)

        if wheres:
            where = "WHERE " + " AND ".join(wheres)

        limit = ""
        if offset is not None and count is not None:
            limit = "LIMIT ?, ?"
            bindings.extend([offset, count])
        elif count is not None:
            limit = "LIMIT ?"
            bindings.append(count)

        order = "ASC" if asc else "DESC"

        statement = "SELECT * FROM documents %s ORDER BY date %s, json_extract(metadata, '$.title') ASC %s" % (where, order, limit)
        return self.documents(statement, bindings)
