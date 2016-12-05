# -*- coding: utf-8 -*-
"""
2016-12-05 Martin Wheldon <martin.wheldon@greenhills-it.co.uk>
           Fixed issue creating ldap entries with objectClasses defined
           Fix problem when searching for attribute values containing the
           space character.
2016-05-26 Martin Wheldon <martin.wheldon@greenhills-it.co.uk>
           Rewrite of search functionality to add recursive parsing
           of ldap search filters
           Fixed issue searching for attributes with multiple values
           Added ability to use ~= in searches
           Created unittests for mock
2016-02-19 Cornelius Kölbel <cornelius.koelbel@netknights.it>
           Add the possibility to check objectGUID
2015-01-31 Change responses.py to be able to run with SMTP
        Cornelius Kölbel <cornelius@privacyidea.org>

Original responses.py is:
Copyright 2013 Dropbox, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from __future__ import (
    absolute_import, print_function, division, unicode_literals
)

DIRECTORY = "tests/testdata/tmp_directory"
import six
from ast import literal_eval
import hashlib
import ldap3
from ldap3.utils.conv import check_escape, escape_bytes
import re
import pyparsing

try:
    from six import cStringIO as BufferIO
except ImportError:
    from six import StringIO as BufferIO

import inspect
from collections import namedtuple, Sequence, Sized
from functools import update_wrapper

Call = namedtuple('Call', ['request', 'response'])

_wrapper_template = """\
def wrapper%(signature)s:
    with ldap3mock:
        return func%(funcargs)s
"""


def get_wrapped(func, wrapper_template, evaldict):
    # Preserve the argspec for the wrapped function so that testing
    # tools such as pytest can continue to use their fixture injection.
    args, a, kw, defaults = inspect.getargspec(func)
    values = args[-len(defaults):] if defaults else None

    signature = inspect.formatargspec(args, a, kw, defaults)
    is_bound_method = hasattr(func, '__self__')
    if is_bound_method:
        args = args[1:]     # Omit 'self'
    callargs = inspect.formatargspec(args, a, kw, values,
                                     formatvalue=lambda v: '=' + v)

    ctx = {'signature': signature, 'funcargs': callargs}
    six.exec_(wrapper_template % ctx, evaldict)

    wrapper = evaldict['wrapper']

    update_wrapper(wrapper, func)
    if is_bound_method:
        wrapper = wrapper.__get__(func.__self__, type(func.__self__))
    return wrapper


class CallList(Sequence, Sized):
    def __init__(self):
        self._calls = []

    def __iter__(self):
        return iter(self._calls)

    def __len__(self):
        return len(self._calls)

    def __getitem__(self, idx):
        return self._calls[idx]

    def setdata(self, request, response):
        self._calls.append(Call(request, response))

    def reset(self):
        self._calls = []


class Connection(object):

    class Extend(object):

        class Standard(object):

            def __init__(self, connection):
                self.connection = connection

            def paged_search(self, **kwargs):
                self.connection.search(search_base=kwargs.get("search_base"),
                                       search_scope=kwargs.get("search_scope"),
                                       search_filter=kwargs.get(
                                           "search_filter"),
                                       attributes=kwargs.get("attributes"),
                                       paged_size=kwargs.get("page_size"),
                                       size_limit=kwargs.get("size_limit"),
                                       paged_cookie=None)
                return self.connection.response

        def __init__(self, connection):
            self.standard = self.Standard(connection)

    def __init__(self, directory=None):
        if directory is None:
                directory = []
        import copy
        self.directory = copy.deepcopy(directory)
        self.bound = False
        self.extend = self.Extend(self)

        self.operation = {
                    "!" : self._search_not,
                    "&" : self._search_and,
                    "|" : self._search_or,
            }

    def set_directory(self, directory):
        self.directory = directory

    def _find_user(self, dn):
        return next(i for (i, d) in enumerate(self.directory) if d["dn"] == dn)

    @staticmethod
    def open():
        return

    def bind(self):
        return self.bound

    def add(self, dn, object_class=None, attributes=None):

        self.result = { 'dn' : '',
                        'referrals' : None,
                        'description' : 'success',
                        'result' : 0,
                        'message' : '',
                        'type' : 'addResponse'}

        # Check to see if the user exists in the directory
        try:
            index = self._find_user(dn)
        except StopIteration:
            # If we get here the user doesn't exist so continue
	    # Create a entry object for the new user
	    entry = {}
	    entry['dn'] = dn
	    entry['attributes'] = attributes
            if object_class != None:
                entry['attributes'].update( {'objectClass': object_class} )
        else:
            # User already exists
            self.result["description"] = "failure"
            self.result["result"] = 68
            self.result["message"] = \
                    "Error entryAlreadyExists for {0}".format(dn)
            return False

        # Add the user entry to the directory
        self.directory.append(entry)

        # Attempt to write changes to disk
        with open(DIRECTORY, 'w+') as f:
            f.write(str(self.directory))

        return True

    def delete(self, dn, controls=None):

        self.result = { 'dn' : '',
                        'referrals' : None,
                        'description' : 'success',
                        'result' : 0,
                        'message' : '',
                        'type' : 'addResponse'}

        # Check to see if the user exists in the directory
        try:
            index = self._find_user(dn)
        except StopIteration:
            # If we get here the user doesn't exist so continue
            self.result["description"] = "failure"
            self.result["result"] = 32
            self.result["message"] = "Error no such object: {0}".format(dn)
            return False

        # Delete the entry object for the user
        self.directory.pop(index)

        # Attempt to write changes to disk
        with open(DIRECTORY, 'w+') as f:
            f.write(str(self.directory))

        return True

    def modify(self, dn, changes, controls=None):

        self.result = { 'dn' : '',
                        'referrals' : None,
                        'description' : 'success',
                        'result' : 0,
                        'message' : '',
                        'type' : 'modifyResponse'}

        # Check to see if the user exists in the directory
        try:
            index = self._find_user(dn)
        except StopIteration:
            # If we get here the user doesn't exist so continue
            self.result["description"] = "failure"
            self.result["result"] = 32
            self.result["message"] = "Error no such object: {0!s}".format(dn)
            return False

        # extract the hash we are interested in
        entry = self.directory[index].get("attributes")

        # Loop over the changes hash and apply them
        for k, v in changes.iteritems():
            if v[0] == "MODIFY_DELETE":
                entry.pop(k)
            elif v[0] == "MODIFY_REPLACE" or v[0] == "MODIFY_ADD":
                entry[k] = v[1][0]
            else:
                self.result["result"] = 2
                self.result["message"] = "Error bad/missing/not implemented" \
                    "modify operation: %s" % k[1]

        # Place the attributes back into the directory hash
        self.directory[index]["attributes"] = entry

        # Attempt to write changes to disk
        with open(DIRECTORY, 'w+') as f:
            f.write(str(self.directory))

        return True

    @staticmethod
    def _match_greater_than_or_equal(search_base, attribute, value, candidates):
        matches = list()
        for entry in candidates:
            dn = entry.get("dn")
            if not dn.endswith(search_base):
                continue

            value_from_directory = entry.get("attributes").get(attribute)
            if str(value_from_directory) >= str(value):
                entry["type"] = "searchResEntry"
                matches.append(entry)

        return matches

    @staticmethod
    def _match_greater_than(search_base, attribute, value, candidates):
        matches = list()
        for entry in candidates:
            dn = entry.get("dn")
            if not dn.endswith(search_base):
                continue

            value_from_directory = entry.get("attributes").get(attribute)
            if str(value_from_directory) > str(value):
                entry["type"] = "searchResEntry"
                matches.append(entry)

        return matches

    @staticmethod
    def _match_less_than_or_equal(search_base, attribute, value, candidates):
        matches = list()
        for entry in candidates:
            dn = entry.get("dn")
            if not dn.endswith(search_base):
                continue

            value_from_directory = entry.get("attributes").get(attribute)
            if str(value_from_directory) <= str(value):
                entry["type"] = "searchResEntry"
                matches.append(entry)

        return matches

    @staticmethod
    def _match_less_than(search_base, attribute, value, candidates):
        matches = list()
        for entry in candidates:
            dn = entry.get("dn")
            if not dn.endswith(search_base):
                continue

            value_from_directory = entry.get("attributes").get(attribute)
            if str(value_from_directory) < str(value):
                entry["type"] = "searchResEntry"
                matches.append(entry)

        return matches

    @staticmethod
    def _match_equal_to(search_base, attribute, value, candidates):
        matches = list()
        match_using_regex = False

        if "*" in value:
            match_using_regex = True
            #regex = check_escape(value)
            regex = value.replace('*', '.*')
            regex = "^{0}$".format(regex)

        for entry in candidates:
            dn = entry.get("dn")

            if not attribute in entry.get("attributes") \
                or not dn.endswith(search_base):

                continue

            values_from_directory = entry.get("attributes").get(attribute)
            if isinstance(values_from_directory, list):
                for item in values_from_directory:
                    if attribute == "objectGUID":
                        item = escape_bytes(item)

                    if match_using_regex:
                        m = re.match(regex, str(item), re.I)
                        if m:
                            entry["type"] = "searchResEntry"
                            matches.append(entry)
                    else:
                        if item == value:
                            entry["type"] = "searchResEntry"
                            matches.append(entry)

            else:
                if attribute == "objectGUID":
                    values_from_directory = escape_bytes(values_from_directory)
                if match_using_regex:
                    m = re.match(regex, str(values_from_directory), re.I)
                    if m:
                        entry["type"] = "searchResEntry"
                        matches.append(entry)
                else:
                    if str(value) == str(values_from_directory):
                        entry["type"] = "searchResEntry"
                        matches.append(entry)

        return matches

    @staticmethod
    def _match_notequal_to(search_base, attribute, value, candidates):
        matches = list()
        match_using_regex = False

        if "*" in value:
            match_using_regex = True
            #regex = check_escape(value)
            regex = value.replace('*', '.*')
            regex = "^{0}$".format(regex)

        for entry in candidates:
            found = False
            dn = entry.get("dn")

            if not dn.endswith(search_base):
                continue

            values_from_directory = entry.get("attributes").get(attribute)
            if isinstance(values_from_directory, list):
                for item in values_from_directory:
                    if attribute == "objectGUID":
                        item = escape_bytes(item)

                    if match_using_regex:
                        m = re.match(regex, str(item), re.I)
                        if m:
                            found = True
                    else:
                        if item == value:
                            found = True
                if found == False:
                    entry["type"] = "searchResEntry"
                    matches.append(entry)
            else:
                if attribute == "objectGUID":
                    values_from_directory = escape_bytes(values_from_directory)
                if match_using_regex:
                    m = re.match(regex, str(values_from_directory), re.I)
                    if not m:
                        entry["type"] = "searchResEntry"
                        matches.append(entry)
                else:
                    if str(value) != str(values_from_directory):
                        entry["type"] = "searchResEntry"
                        matches.append(entry)

        return matches

    @staticmethod
    def _parse_filter():
        op = pyparsing.oneOf('! & |')
        lpar  = pyparsing.Literal('(').suppress()
        rpar  = pyparsing.Literal(')').suppress()

        k = pyparsing.Word(pyparsing.alphanums)
        # NOTE: We may need to expand on this list, but as this is not a real
        # LDAP server we should be OK.
        # Value to contain:
        #   numbers, upper/lower case letters, astrisk, at symbol, full stop
        #   backslash or a space
        v = pyparsing.Word(pyparsing.alphanums + "*@.\\ ")
        rel = pyparsing.oneOf("= ~= >= <=")

        expr = pyparsing.Forward()
        atom = pyparsing.Group(lpar + op + expr + rpar) \
                            | pyparsing.Combine(lpar + k + rel + v + rpar)
        expr << atom + pyparsing.ZeroOrMore( expr )

        return expr

    @staticmethod
    def _deDuplicate(results):
        found = dict()
        deDuped = list()
        for entry in results:
            dn = entry.get("dn")
            if not dn in found.keys():
                found[dn] = 1
                deDuped.append(entry)

        return deDuped

    def _invert_results(self, candidates):
        inverted_candidates = list(self.directory)

        for candidate in candidates:
            try:
                inverted_candidates.remove(candidate)
            except ValueError:
                pass

        return inverted_candidates

    def _search_not(self, base, search_filter, candidates=None):
        # Create empty candidates list as we need to use self.directory for
        # each search
        candidates = list()
        this_filter = list()

        index = 0
        search_filter.remove("!")
        for condition in search_filter:
            if not isinstance(condition, list):
                this_filter.append(condition)
            index +=1

        # Remove this_filter items from search_filter list
        for condition in this_filter:
            search_filter.remove(condition)

        try:
            search_filter = list(search_filter[0])
            for sub_filter in search_filter:
                if not isinstance(sub_filter, list):
                    candidates = self.operation.get(sub_filter)(base,
                                                                search_filter,
                                                                candidates)
                else:
                    candidates = self.operation.get(sub_filter[0])(base,
                                                                   sub_filter,
                                                                   candidates)
        except IndexError:
            pass

        candidates = self._invert_results(candidates)

        for item in this_filter:
            if ">=" in item:
                k, v = item.split(">=")
                candidates = Connection._match_less_than(base, k, v,
                                                            self.directory)
            elif "<=" in item:
                k, v = item.split("<=")
                candidates = Connection._match_greater_than(base, k, v,
                                                         self.directory)
            # Emulate AD functionality, same as "="
            elif "~=" in item:
                k, v = item.split("~=")
                candidates = Connection._match_notequal_to(base, k, v,
                                                         self.directory)
            elif "=" in item:
                k, v = item.split("=")
                candidates = Connection._match_notequal_to(base, k, v,
                                                         self.directory)
        return candidates

    def _search_and(self, base, search_filter, candidates=None):
        # Load the data from the directory, if we arn't passed any
        if candidates == [] or candidates == None:
            candidates = self.directory
        this_filter = list()

        index = 0
        search_filter.remove("&")
        for condition in search_filter:
            if not isinstance(condition, list):
                this_filter.append(condition)
            index +=1

        # Remove this_filter items from search_filter list
        for condition in this_filter:
            search_filter.remove(condition)

        try:
            search_filter = list(search_filter[0])
            for sub_filter in search_filter:
                if not isinstance(sub_filter, list):
                    candidates = self.operation.get(sub_filter)(base,
                                                                search_filter,
                                                                candidates)
                else:
                    candidates = self.operation.get(sub_filter[0])(base,
                                                                   sub_filter,
                                                                   candidates)
        except IndexError:
            pass

        for item in this_filter:
            if ">=" in item:
                k, v = item.split(">=")
                candidates = Connection._match_greater_than_or_equal(base, k, v,
                                                                     candidates)
            elif "<=" in item:
                k, v = item.split("<=")
                candidates = Connection._match_less_than_or_equal(base, k, v,
                                                                  candidates)
            # Emulate AD functionality, same as "="
            elif "~=" in item:
                k, v = item.split("~=")
                candidates = Connection._match_equal_to(base, k, v,
                                                         candidates)
            elif "=" in item:
                k, v = item.split("=")
                candidates = Connection._match_equal_to(base, k, v,
                                                         candidates)
        return candidates

    def _search_or(self, base, search_filter, candidates=None):
        # Create empty candidates list as we need to use self.directory for
        # each search
        candidates = list()
        this_filter = list()

        index = 0
        search_filter.remove("|")
        for condition in search_filter:
            if not isinstance(condition, list):
                this_filter.append(condition)
            index +=1

        # Remove this_filter items from search_filter list
        for condition in this_filter:
            search_filter.remove(condition)

        try:
            search_filter = list(search_filter[0])
            for sub_filter in search_filter:
                if not isinstance(sub_filter, list):
                    candidates += self.operation.get(sub_filter)(base,
                                                                 search_filter,
                                                                 candidates)
                else:
                    candidates += self.operation.get(sub_filter[0])(base,
                                                                    sub_filter,
                                                                    candidates)
        except IndexError:
            pass

        for item in this_filter:
            if ">=" in item:
                k, v = item.split(">=")
                candidates += Connection._match_greater_than_or_equal(base, k, v,
                                                             self.directory)
            elif "<=" in item:
                k, v = item.split("<=")
                candidates += Connection._match_less_than_or_equal(base, k, v,
                                                          self.directory)
            # Emulate AD functionality, same as "="
            elif "~=" in item:
                k, v = item.split("~=")
                candidates += Connection._match_equal_to(base, k, v,
                                                         self.directory)
            elif "=" in item:
                k, v = item.split("=")
                candidates += Connection._match_equal_to(base, k, v,
                                                         self.directory)
        return candidates

    def search(self, search_base=None, search_scope=None,
               search_filter=None, attributes=None, paged_size=5,
               size_limit=0, paged_cookie=None):
        s_filter = list()
        candidates = list()
        self.response = list()
        self.result = dict()

        try:
            expr = Connection._parse_filter()
            s_filter = expr.parseString(search_filter).asList()[0]
        except pyparsing.ParseBaseException:
            pass

        for item in s_filter:
            if item[0] in self.operation:
                candidates = self.operation.get(item[0])(search_base,
                                                         s_filter)
        self.response = Connection._deDuplicate(candidates)

        return True

    def unbind(self):
        return True


class Ldap3Mock(object):

    def __init__(self):
        self._calls = CallList()
        self.directory = []
        self.reset()

    def reset(self):
        self._calls.reset()

    def setLDAPDirectory(self, directory=None):
        if directory is None:
                self.directory = []
        else:
            try:
                with open(DIRECTORY, 'w+') as f:
                    f.write(str(directory))
                    self.directory = directory
            except OSError as e:
                raise

    def _load_data(self, directory):
        try:
            with open(directory, 'r') as f:
                data = f.read()
                return literal_eval(data)
        except OSError as e:
            raise

    @property
    def calls(self):
        return self._calls

    def __enter__(self):
        self.start()

    def __exit__(self, *args):
        self.stop()
        self.reset()

    def activate(self, func):
        evaldict = {'ldap3mock': self, 'func': func}
        return get_wrapped(func, _wrapper_template, evaldict)

    def _on_Server(self, host, port,
                              use_ssl,
                              connect_timeout):
        # mangle request packet

        return "FakeServerObject"

    @staticmethod
    def _check_password(user_supplied_pw, reference_pw):
        # Strip the label from the string
        label_removed = reference_pw[6:]

        # Decode base64 and strip salt
        digest_salt = label_removed.decode('base64')
        reference_pw_sha = digest_salt[:20]
        # Strip off the salt for use encoding the user supplied password
        salt = digest_salt[20:]

        # Encode the user supplied password so we can compare the two
        user_supplied_sha = hashlib.sha1(user_supplied_pw)
        user_supplied_sha.update(salt)

        return user_supplied_sha.digest() == reference_pw_sha


    def _on_Connection(self, server, user, password,
                       auto_bind=None, client_strategy=None,
                       authentication=None, check_names=None,
                       auto_referrals=None, receive_timeout=None):
        """
        We need to create a Connection object with
        methods:
            add()
            modify()
            search()
            unbind()
        and object
            response
        """
        # check the password
        correct_password = False
        # Anonymous bind
        # Reload the directory just incase a change has been made to 
        # user credentials
        self.directory = self._load_data(DIRECTORY)
        if authentication == ldap3.ANONYMOUS and user == "":
            correct_password = True
        for entry in self.directory:
            if entry.get("dn") == user:
                pw = entry.get("attributes").get("userPassword")
                if pw == password:
                    correct_password = True
                elif pw.startswith('{SSHA}'):
                    correct_password = self._check_password(password, pw)
                else:
                    correct_password = False
        self.con_obj = Connection(self.directory)
        self.con_obj.bound = correct_password
        return self.con_obj

    def start(self):
        import mock

        def unbound_on_Server(host, port,
                              use_ssl,
                              connect_timeout, *a, **kwargs):
            return self._on_Server(host, port,
                              use_ssl,
                              connect_timeout, *a, **kwargs)
        self._patcher = mock.patch('ldap3.Server',
                                   unbound_on_Server)
        self._patcher.start()

        def unbound_on_Connection(server, user,
                                  password,
                                  auto_bind,
                                  client_strategy,
                                  authentication,
                                  check_names,
                                  auto_referrals, *a, **kwargs):
            return self._on_Connection(server, user,
                                       password,
                                       auto_bind,
                                       client_strategy,
                                       authentication,
                                       check_names,
                                       auto_referrals, *a,
                                       **kwargs)

        self._patcher2 = mock.patch('ldap3.Connection',
                                    unbound_on_Connection)
        self._patcher2.start()

    def stop(self):
        self._patcher.stop()
        self._patcher2.stop()

# expose default mock namespace
mock = _default_mock = Ldap3Mock()
__all__ = []
for __attr in (a for a in dir(_default_mock) if not a.startswith('_')):
    __all__.append(__attr)
    globals()[__attr] = getattr(_default_mock, __attr)
