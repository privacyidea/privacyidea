# (c) NetKnights GmbH 2025,  https://netknights.it
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-FileCopyrightText: 2024 Raphael Topel <raphael.topel@esh.essen.de>
# SPDX-FileCopyrightText: 2018 Cornelius Kölbel <cornelius@privacyidea.org>
# SPDX-FileCopyrightText: 2016 Martin Wheldon <martin.wheldon@greenhills-it.co.uk>
# SPDX-FileCopyrightText: 2016 Salvo Rapisarda
# SPDX-License-Identifier: AGPL-3.0-or-later

__doc__ = """This is the resolver to find users in LDAP directories like
OpenLDAP and Active Directory.

The file is tested in tests/test_lib_resolver.py
"""

import logging

import yaml
import threading
import functools

from .UserIdResolver import UserIdResolver

import ldap3
from ldap3 import MODIFY_REPLACE, MODIFY_ADD, MODIFY_DELETE
from ldap3 import Tls
from ldap3.core.exceptions import LDAPOperationResult
from ldap3.core.results import RESULT_SIZE_LIMIT_EXCEEDED
import ssl

import os.path

import traceback
from passlib.hash import ldap_salted_sha1
import hashlib
import binascii
from privacyidea.lib.framework import get_app_local_store, get_app_config_value
import datetime

from privacyidea.lib import _
from privacyidea.lib.log import log_with
from privacyidea.lib.utils import (is_true, to_bytes, to_unicode,
                                   convert_column_to_unicode)
from privacyidea.lib.error import privacyIDEAError, ResolverError
import uuid
from ldap3.utils.conv import escape_bytes
from operator import itemgetter

log = logging.getLogger(__name__)

try:
    import gssapi
    have_gssapi = True
except ImportError:
    log.info('Could not import gssapi package. Kerberos authentication not available')
    have_gssapi = False

CACHE = {}

ENCODING = "utf-8"
# The number of rounds the resolver tries to reach a responding server in the
#  pool
SERVERPOOL_ROUNDS = 2
# The number of seconds a non-responding server is removed from the server pool
SERVERPOOL_SKIP = 30
# The pooling strategy for the ldap servers
LDAP_STRATEGY = {"ROUND_ROBIN": ldap3.ROUND_ROBIN, "FIRST": ldap3.FIRST, "RANDOM": ldap3.RANDOM}
SERVERPOOL_STRATEGY = "ROUND_ROBIN"

# 1 sec == 10^9 nano secs == 10^7 * (100 nano secs)
MS_AD_MULTIPLYER = 10 ** 7
MS_AD_START = datetime.datetime(1601, 1, 1)

if os.path.isfile("/etc/privacyidea/ldap-ca.crt"):
    DEFAULT_CA_FILE = "/etc/privacyidea/ldap-ca.crt"
elif os.path.isfile("/etc/ssl/certs/ca-certificates.crt"):
    DEFAULT_CA_FILE = "/etc/ssl/certs/ca-certificates.crt"
elif os.path.isfile("/etc/ssl/certs/ca-bundle.crt"):
    DEFAULT_CA_FILE = "/etc/ssl/certs/ca-bundle.crt"
else:
    DEFAULT_CA_FILE = "/etc/privacyidea/ldap-ca.crt"

TLS_NEGOTIATE_PROTOCOL = ssl.PROTOCOL_TLS

DEFAULT_TLS_PROTOCOL = TLS_NEGOTIATE_PROTOCOL

TLS_OPTIONS_1_3 = (ssl.OP_NO_TLSv1_2, ssl.OP_NO_TLSv1_1, ssl.OP_NO_TLSv1, ssl.OP_NO_SSLv3)


class LockingServerPool(ldap3.ServerPool):
    """
    A ``ServerPool`` subclass that uses a RLock to synchronize invocations of
    ``initialize``, ``get_server`` and ``get_current_server``.

    We synchronize invocations to rule out race conditions when multiple threads
    try to manipulate the server pool state concurrently.

    We use a ``RLock`` instead of a simple ``Lock`` to avoid locking ourselves.
    """
    def __init__(self, *args, **kwargs):
        ldap3.ServerPool.__init__(self, *args, **kwargs)
        self._lock = threading.RLock()

    def initialize(self, connection):
        with self._lock:
            return ldap3.ServerPool.initialize(self, connection)

    def get_server(self, connection):
        with self._lock:
            return ldap3.ServerPool.get_server(self, connection)

    def get_current_server(self, connection):
        with self._lock:
            return ldap3.ServerPool.get_current_server(self, connection)


def get_ad_timestamp_now():
    """
    returns the current UTC time as it is used in Active Directory in the
    attribute accountExpires.
    This is 100-nano-secs since 1.1.1601

    :return: time
    :rtype: int
    """
    utc_now = datetime.datetime.utcnow()
    elapsed_time = utc_now - MS_AD_START
    total_seconds = elapsed_time.total_seconds()
    # convert this to (100 nanoseconds)
    return int(MS_AD_MULTIPLYER * total_seconds)


def trim_objectGUID(user_id):
    user_id = uuid.UUID("{{{0!s}}}".format(user_id)).bytes_le
    user_id = escape_bytes(user_id)
    return user_id


def get_info_configuration(noschemas):
    """
    Given the value of the NOSCHEMAS config option, return the value that should
    be passed as ldap3's `get_info` argument.
    :param noschemas: a boolean
    :return: one of ldap3.SCHEMA or ldap3.NONE
    """
    get_schema_info = ldap3.SCHEMA
    if noschemas:
        get_schema_info = ldap3.NONE
    log.debug("Get LDAP schema info: {0!r}".format(get_schema_info))
    return get_schema_info


def ignore_sizelimit_exception(conn, generator):
    """
    Wrapper for ``paged_search``, which (since ldap3 2.3) throws an exception if the size limit has been
    reached. This function wraps the generator and ignores this exception.

    Additionally, this checks ``conn.response`` for any leftover entries that were not yet returned
    by the generator and yields them.
    """
    last_entry = None
    while True:
        try:
            last_entry = next(generator)
            yield last_entry
        except StopIteration:
            # If the generator is exceeded, we stop
            break
        except LDAPOperationResult as e:
            # If the size limit has been reached, we stop. All other exceptions are re-raised.
            if e.result == RESULT_SIZE_LIMIT_EXCEEDED:
                # Workaround: In ldap3 <= 2.4.1, the generator may "forget" to yield some entries that
                # were transmitted just before the "size limit exceeded" message. In other words,
                # the exception is raised *before* the generator has yielded those entries.
                # These leftover entries can still be found in ``conn.response``, so we
                # just yield them here.
                # However, as future versions of ldap3 may fix this behavior and
                # may actually yield those elements as well, this workaround may result in
                # duplicate entries.
                # Thus, we check if the last entry we got from the generator can be found
                # in ``conn.response``. If that is the case, we assume the generator works correctly
                # and *all* of ``conn.response`` have been yielded already.
                if last_entry is None or last_entry not in conn.response:
                    for entry in conn.response:
                        yield entry
                break
            else:
                raise


def cache(func):
    """
    cache the user with his loginname, resolver and UID in a local
    dictionary cache.
    This is a per process cache.
    """
    @functools.wraps(func)
    def cache_wrapper(self, *args, **kwds):
        # Only run the code, in case we have a configured cache!
        if self.cache_timeout > 0:
            # If it does not exist, create the node for this instance
            resolver_id = self.getResolverId()
            now = datetime.datetime.now(tz=datetime.timezone.utc)
            tdelta = datetime.timedelta(seconds=self.cache_timeout)
            if resolver_id not in CACHE:
                CACHE[resolver_id] = {"getUserId": {},
                                      "getUserInfo": {},
                                      "_getDN": {}}
            else:
                # Clean up the cache in the current resolver and the current function
                _to_be_deleted = []
                try:
                    for user, cached_result in CACHE[resolver_id].get(func.__name__).items():
                        if now > cached_result.get("timestamp") + tdelta:
                            _to_be_deleted.append(user)
                except RuntimeError:
                    # This might happen if thread A evicts an expired
                    # cache entry while thread B looks for expired cache entries
                    pass
                for user in _to_be_deleted:
                    try:
                        del CACHE[resolver_id][func.__name__][user]
                    except KeyError:
                        pass
                del _to_be_deleted

            # get the portion of the cache for this very LDAP resolver
            r_cache = CACHE.get(resolver_id).get(func.__name__)
            entry = r_cache.get(args[0])
            if entry and now < entry.get("timestamp") + tdelta:
                log.debug("Reading {0!r} from cache for {1!r}".format(args[0], func.__name__))
                return entry.get("value")

        f_result = func(self, *args, **kwds)

        if self.cache_timeout > 0:
            # now we cache the result
            CACHE[resolver_id][func.__name__][args[0]] = {
                "value": f_result,
                "timestamp": now}

        return f_result

    return cache_wrapper


class AUTHTYPE(object):
    SIMPLE = "Simple"
    SASL_DIGEST_MD5 = "SASL Digest-MD5"
    NTLM = "NTLM"
    SASL_KERBEROS = "SASL Kerberos"


class IdResolver(UserIdResolver):
    # If the resolver could be configured editable
    updateable = True

    def __init__(self):
        self.i_am_bound = False
        self.uri = ""
        self.basedn = ""
        self.binddn = ""
        self.bindpw = ""
        self.object_classes = []
        self.dn_template = ""
        self.timeout = 5  # seconds!
        self.sizelimit = 500
        self.loginname_attribute = [""]
        self.searchfilter = ""
        self.userinfo = {}
        self.multivalueattributes = []
        self.uidtype = ""
        self.noreferrals = False
        self._editable = False
        self.resolverId = self.uri
        self.scope = ldap3.SUBTREE
        self.cache_timeout = 120
        self.tls_context = None
        self.start_tls = False
        self.serverpool_persistent = False
        self.serverpool_rounds = SERVERPOOL_ROUNDS
        self.serverpool_skip = SERVERPOOL_SKIP
        self.serverpool_strategy = SERVERPOOL_STRATEGY
        self.serverpool = None
        self.keytabfile = None
        self.recursive_group_search = False
        self.group_name_attribute = ""
        self.group_search_filter = ""
        self.group_attribute_mapping_key = ""
        # The number of seconds that ldap3 waits if no server is left in the pool, before
        # starting the next round
        pooling_loop_timeout = get_app_config_value("PI_LDAP_POOLING_LOOP_TIMEOUT", 10)
        log.debug("Setting system wide POOLING_LOOP_TIMEOUT to {0!s}.".format(pooling_loop_timeout))
        ldap3.set_config_parameter("POOLING_LOOP_TIMEOUT", pooling_loop_timeout)

    @log_with(log, hide_args=[2])
    def checkPass(self, uid, password):
        """
        This function checks the password for a given uid.
        - returns true in case of success
        -         false if password does not match

        """
        if self.authtype == AUTHTYPE.SASL_KERBEROS:
            if not have_gssapi:
                log.warning('gssapi module not available. Kerberos authentication not possible')
                return False
            # We need to check credentials with kerberos differently since we
            # can not use bind for every user
            upn = self.getUserInfo(uid).get('upn')
            if upn is not None and upn != "None" and upn != "":
                name = gssapi.Name(upn.upper())
            else:
                name = gssapi.Name(self.getUserInfo(uid).get('username'))
            try:
                gssapi.raw.ext_password.acquire_cred_with_password(name, to_bytes(password))
            except gssapi.exceptions.GSSError as e:
                log.info('Failed to authenticate user {0!s} with GSSAPI: {1!r}'.format(name, e))
                log.debug(traceback.format_exc())
                return False
            return True
        elif self.authtype == AUTHTYPE.NTLM:  # pragma: no cover
            # fetch the PreWindows 2000 Domain from the self.binddn
            # which would be of the format DOMAIN\username and compose the
            # bind_user to DOMAIN\sAMAccountName
            domain_name = self.binddn.split('\\')[0]
            uinfo = self.getUserInfo(uid)
            # In fact, we need the sAMAccountName. If the username mapping is
            # another attribute than the sAMAccountName the authentication
            # will fail!
            bind_user = "{0!s}\\{1!s}".format(domain_name, uinfo.get("username"))
        else:
            bind_user = self._getDN(uid)

        if not self.serverpool:
            self.serverpool = self.get_serverpool_instance(get_info=ldap3.NONE)

        try:
            log.debug("Authtype: {0!r}".format(self.authtype))
            log.debug("user    : {0!r}".format(bind_user))
            # Whatever happens. If we have an empty bind_user, we must break
            # since we must avoid anonymous binds!
            if not bind_user or len(bind_user) < 1:
                raise ResolverError("No valid user. Empty bind_user.")
            connection = self.create_connection(authtype=self.authtype,
                                                server=self.serverpool,
                                                user=bind_user,
                                                password=password,
                                                receive_timeout=self.timeout,
                                                auto_referrals=not self.noreferrals,
                                                start_tls=self.start_tls)
            if not connection.bind():
                raise ResolverError(f"Bind failed with: {connection.result.get('description')} "
                                    f"({connection.result.get('result')})")
            log.debug(f"LDAP bind operation took {connection.usage.elapsed_time}")
            connection.unbind()
            log.debug("unbind successful.")
        except Exception as e:
            log.info(f"Failed to check password for {uid!r}/{bind_user!r}: {e}")
            log.debug(traceback.format_exc())
            return False

        return True

    def _trim_result(self, result_list):
        """
        The resultlist can contain entries of type:searchResEntry and of
        type:searchResRef. If self.noreferrals is true, all type:searchResRef
        will be removed.

        :param result_list: The result list of a LDAP search
        :type result_list: resultlist (list of dicts)
        :return: new resultlist
        """
        if self.noreferrals:
            new_list = []
            for result in result_list:
                if result.get("type") == "searchResEntry":
                    new_list.append(result)
                elif result.get("type") == "searchResRef":
                    # This is a Referral
                    pass
        else:
            new_list = result_list

        return new_list

    @staticmethod
    def _escape_loginname(loginname):
        """
        This function escapes the loginname according to
        https://msdn.microsoft.com/en-us/library/aa746475(v=vs.85).aspx
        This is to avoid username guessing by trying to login as user
           a*
           ac*
           ach*
           achm*
           achme*
           achemd*

        :param loginname: The loginname
        :return: The escaped loginname
        """
        return loginname.replace("\\", "\\5c").replace("*", "\\2a").replace(
            "(", "\\28").replace(")", "\\29").replace("/", "\\2f")

    @staticmethod
    def _get_uid(entry, uidtype):
        if uidtype.lower() == "dn":
            uid = entry.get("dn")
        else:
            attributes = entry.get("attributes")
            if isinstance(attributes.get(uidtype), list):
                uid = attributes.get(uidtype)[0]
            else:
                uid = attributes.get(uidtype)

        try:
            uid = convert_column_to_unicode(uid)
        except UnicodeDecodeError as e:
            # in some cases ldap3 fails to decode the uid and return it as a byte-array
            # if the utf-8 decoding fails, we try the UUID conversion
            if uidtype.lower() == "objectguid":
                # Active Directory uses little endian byte order
                log.debug(f"Found a byte-array as uid ({binascii.hexlify(uid)}), trying to convert it to a UUID "
                          f"assuming little endian byte order. ({e})")
                log.debug(traceback.format_exc())
                uid = str(uuid.UUID(bytes_le=uid))
            else:
                # ldap3 defines a standard formatter using big endian byte order for GUID (eDirectory), entryUUID
                # (openLDAP), and UUID. Hence, we assume it as the default byte order here.
                log.debug(f"Found a byte-array as uid ({binascii.hexlify(uid)}), trying to convert it to a UUID "
                          f"assuming big endian byte order. ({e})")
                log.debug(traceback.format_exc())
                uid = str(uuid.UUID(bytes=uid))

        if uidtype.lower() == "objectguid":
            # For ldap3 versions <= 2.4.1, objectGUID attribute values are returned as UUID strings.
            # For versions greater than 2.4.1, they are returned in the curly-braced string
            # representation, i.e. objectGUID := "{" UUID "}"
            # In order to ensure backwards compatibility for user mappings,
            # we strip the curly braces from objectGUID values.
            # If we are using ldap3 <= 2.4.1, there are no curly braces and we leave the value unchanged.
            uid = uid.strip("{").strip("}")

        return uid

    def _trim_user_id(self, user_id):
        """
        If we search for the objectGUID we can not search for the normal
        string representation, but we need to search for the bytestring in AD.

        :param user_id: The userId
        :return: the trimmed userId
        """
        if self.uidtype == "objectGUID":
            user_id = trim_objectGUID(user_id)
        return user_id

    @cache
    def _getDN(self, user_id):
        """
        This function returns the DN of a userId.
        Therefor it evaluates the self.uidtype.

        :param user_id: The userid of a user
        :type user_id: string
        :return: The DN of the object.
        """
        dn = ""
        if self.uidtype.lower() == "dn":
            dn = user_id
        else:
            # get the DN for the Object
            search_userid = self._trim_user_id(user_id)
            search_filter = f"(&{self.searchfilter}({self.uidtype}={search_userid}))"
            result = self._search(search_base=self.basedn, search_filter=search_filter,
                                  attributes=list(self.userinfo.values()))
            if len(result) > 1:  # pragma: no cover
                raise ResolverError(f"Found more than one object for uid {user_id!r}")
            elif len(result) == 1:
                dn = result[0].get("dn")
            else:
                log.info(f"The filter '{search_filter}' returned no DN.")
        return dn

    def _bind(self):
        """
        Perform LDAP bind operation on a connection.
        Create the connection if it doesn't exist yet
        """
        if not self.i_am_bound:
            if not self.serverpool:
                self.serverpool = self.get_serverpool_instance(self.get_info)
            try:
                self.connection = self.create_connection(authtype=self.authtype,
                                                         server=self.serverpool,
                                                         user=self.binddn,
                                                         password=self.bindpw,
                                                         receive_timeout=self.timeout,
                                                         auto_referrals=not
                                                         self.noreferrals,
                                                         start_tls=self.start_tls,
                                                         keytabfile=self.keytabfile)
                bound = self.connection.bind()
            except Exception as ex:
                log.error(f"Error performing bind operation: {ex}!")
                raise ResolverError(f"Error performing bind operation: {ex}")
            if not bound:
                result = self.connection.result
                log.error(f"LDAP Bind unsuccessful: "
                          f"{result.get('description')} ({result.get('result')})!")
                raise ResolverError(f"Unable to perform bind operation: "
                                    f"{result.get('description')} ({result.get('result')})")
            self.i_am_bound = True

    def _search(self, search_base, search_filter, attributes):
        self._bind()
        self.connection.search(search_base=search_base,
                               search_scope=self.scope,
                               search_filter=search_filter,
                               attributes=attributes)
        result = self.connection.response
        result = self._trim_result(result)
        log.debug(f"LDAP search operation took {self.connection.usage.elapsed_time}")
        return result

    @staticmethod
    def _get_tls_context(ldap_uri=None, start_tls=False, tls_version=None, tls_verify=None,
                         tls_ca_file=None, tls_options=None):
        """
        This method creates the Tls object to be used with ldap3.
        """
        if ldap_uri.lower().startswith("ldaps") or is_true(start_tls):
            if not tls_version:
                tls_version = int(DEFAULT_TLS_PROTOCOL)
            # If TLS_VERSION is 2, set tls_options to use TLS v1.3
            if not tls_options:
                tls_options = TLS_OPTIONS_1_3 if int(tls_version) == int(TLS_NEGOTIATE_PROTOCOL) else None
            if tls_verify:
                tls_ca_file = tls_ca_file or DEFAULT_CA_FILE
            else:
                tls_verify = ssl.CERT_NONE
                tls_ca_file = None
            tls_context = Tls(validate=tls_verify,
                              version=int(tls_version),
                              ssl_options=tls_options,
                              ca_certs_file=tls_ca_file)
        else:
            tls_context = None

        return tls_context

    @cache
    def getUserInfo(self, user_id):
        """
        This function returns all user info for a given userid/object.

        :param user_id: The userid of the object
        :type user_id: string
        :return: A dictionary with the keys defined in self.userinfo
        :rtype: dict
        """
        user_info = {}

        if self.uidtype.lower() == "dn":
            # encode utf8, so that also german umlauts work in the DN
            search_filter = f"(&{self.searchfilter})"
            search_base = user_id
        else:
            search_uid = to_unicode(self._trim_user_id(user_id))
            search_filter = f"(&{self.searchfilter}({self.uidtype}={search_uid}))"
            search_base = self.basedn

        result = self._search(search_base=search_base, search_filter=search_filter,
                              attributes=list(self.userinfo.values()))

        if len(result) > 1:  # pragma: no cover
            raise ResolverError(f"Found more than one object for uid {user_id!r}")

        for entry in result:
            attributes = entry.get("attributes")
            user_info = self._ldap_attributes_to_user_object(attributes)

        return user_info

    def _get_user_groups_recursive(self, user_info: dict) -> list[str]:
        """
        Do a separate search to retrieve the groups of a user. This can be done recursively to all groups including
        nested groups.
        The search filter can contain the tags ``{base_dn}`` and all keys from the user_info dictionary such as
        ``{username}``. This function replaces the tags with the corresponding values from the user_info dictionary.
        A simple filter could be for example
        ``(&(sAMAccountName=*)(objectCategory=group)(member:1.2.840.113556.1.4.1941:=cn={username},{base_dn}))``.
        The OID "1.2.840.113556.1.4.1941" stands for the ``LDAP_MATCHING_RULE_IN_CHAIN`` flag indicating that the
        search should be done recursively.

        :param user_info: The user information dictionary containing the user's attributes.
        :return: A list of group names the user is a member of.
        """
        groups = []

        # replace tags in search filter
        search_filter = self.group_search_filter
        search_filter = search_filter.replace("{base_dn}", self.basedn)
        for key, value in user_info.items():
            if isinstance(value, str):
                search_filter = search_filter.replace(f"{{{key}}}", value)
        log.debug(f"Searching for groups with filter: {search_filter}")

        try:
            search_result = self._search(search_base=self.basedn, search_filter=search_filter,
                                         attributes=[self.group_name_attribute])
        except Exception as error:
            search_result = []
            log.debug(f"Failed to get the groups of the user: {error}")

        for entry in search_result:
            groups.append(entry.get("attributes").get(self.group_name_attribute))

        return groups

    def _ldap_attributes_to_user_object(self, attributes):
        """
        This helper function converts the LDAP attributes to a dictionary for
        the privacyIDEA user. The LDAP Userinfo mapping is used to do so.

        :param attributes:
        :return: dict with privacyIDEA user info.
        :rtype: dict
        """
        user_info = {}
        for ldap_k, ldap_v in attributes.items():
            for map_k, map_v in self.userinfo.items():
                if ldap_k == map_v:
                    if ldap_k == "objectGUID":
                        # An objectGUID should be no list, since it is unique
                        if isinstance(ldap_v, str):
                            user_info[map_k] = ldap_v.strip("{").strip("}")
                        else:
                            raise Exception("The LDAP returns an objectGUID, "
                                            "that is no string: {0!s}".format(type(ldap_v)))
                    elif isinstance(ldap_v, list) and map_k not in self.multivalueattributes:
                        # lists that are not in self.multivalueattributes return first value
                        # as a string. Multi-value-attributes are returned as a list
                        if ldap_v:
                            user_info[map_k] = ldap_v[0]
                        else:
                            user_info[map_k] = ""
                    else:
                        user_info[map_k] = ldap_v
        if self.recursive_group_search:
            # get all groups with recursive search
            groups = self._get_user_groups_recursive(user_info)
            user_info[self.group_attribute_mapping_key] = groups

        return user_info

    def getUsername(self, user_id):
        """
        Returns the username/loginname for a given user_id

        :param user_id: The user_id in this resolver
        :type user_id: string
        :return: username
        :rtype: string
        """
        info = self.getUserInfo(user_id)
        return info.get('username', "")

    @cache
    def getUserId(self, login_name):
        """
        resolve the loginname to the userid.

        :param login_name: The login name from the credentials
        :type login_name: str
        :return: UserId as found for the LoginName
        :rtype: str
        """
        userid = ""
        login_name = to_unicode(login_name)
        login_name = self._escape_loginname(login_name)

        if len(self.loginname_attribute) > 1:
            loginname_filter = ""
            for l_attribute in self.loginname_attribute:
                # Special case if we have a guid
                try:
                    if l_attribute.lower() == "objectguid":
                        search_login_name = trim_objectGUID(login_name)
                    else:
                        search_login_name = login_name
                    loginname_filter += "({!s}={!s})".format(l_attribute.strip(),
                                                             search_login_name)
                except ValueError:
                    # This happens if we have a self.loginname_attribute like ["sAMAccountName","objectGUID"],
                    # the user logs in with his sAMAccountName, which can
                    # not be transformed to a UUID
                    log.debug("Can not transform {0!s} to a objectGUID.".format(login_name))

            loginname_filter = "|" + loginname_filter
        else:
            if self.loginname_attribute[0].lower() == "objectguid":
                search_login_name = trim_objectGUID(login_name)
            else:
                search_login_name = login_name
            loginname_filter = "{!s}={!s}".format(self.loginname_attribute[0],
                                                  search_login_name)

        log.debug("login name filter: {!r}".format(loginname_filter))
        search_filter = f"(&{self.searchfilter}({loginname_filter}))"

        # create search attributes
        attributes = list(self.userinfo.values())
        if self.uidtype.lower() != "dn":
            attributes.append(str(self.uidtype))

        log.debug("Searching user {0!r} in LDAP.".format(login_name))
        result = self._search(search_base=self.basedn, search_filter=search_filter,
                              attributes=attributes)
        if len(result) > 1:  # pragma: no cover
            raise ResolverError(f"Found more than one object for Login {login_name!r}")

        for entry in result:
            userid = self._get_uid(entry, self.uidtype)

        return userid

    def getUserList(self, search_dict=None):
        """
        :param search_dict: A dictionary with search parameters
        :type search_dict: dict
        :return: list of users, where each user is a dictionary
        """
        user_list = []
        attributes = list(self.userinfo.values())
        if self.uidtype.lower() != "dn":
            attributes.append(str(self.uidtype))

        # do the filter depending on the searchDict
        search_filter = "(&" + self.searchfilter
        for search_key in search_dict.keys():
            # convert to unicode
            search_dict[search_key] = to_unicode(search_dict[search_key])
            if search_key == "accountExpires":
                comperator = ">="
                if search_dict[search_key] in ["1", 1]:
                    comperator = "<="
                search_filter += "(&({0!s}{1!s}{2!s})(!({3!s}=0)))".format(
                    self.userinfo[search_key], comperator,
                    get_ad_timestamp_now(), self.userinfo[search_key])
            else:
                search_filter += "({0!s}={1!s})".format(self.userinfo[search_key],
                                                        search_dict[search_key])
        search_filter += ")"

        self._bind()
        try:
            search_generator = self.connection.extend.standard.paged_search(search_base=self.basedn,
                                                                            search_filter=search_filter,
                                                                            search_scope=self.scope,
                                                                            attributes=attributes,
                                                                            paged_size=100,
                                                                            size_limit=self.sizelimit,
                                                                            generator=True)
            log.debug(f"LDAP paged search operation took {self.connection.usage.elapsed_time}")
        except Exception as e:
            log.error(f"Error performing paged search: {e}")
            raise ResolverError(f"Error performing paged search: {e}")
        # returns a generator of dictionaries
        for entry in ignore_sizelimit_exception(self.connection, search_generator):
            # Simple fix for ignored sizelimit with Active Directory
            if len(user_list) >= self.sizelimit:
                break
            # Fix for searchResRef entries which have no attributes
            if entry.get('type') == 'searchResRef':
                continue
            try:
                attributes = entry.get("attributes")
                user = self._ldap_attributes_to_user_object(attributes)
                user['userid'] = self._get_uid(entry, self.uidtype)
                user_list.append(user)
            except Exception as ex:  # pragma: no cover
                log.error(f"Error during fetching LDAP objects: {ex}")
                log.debug("{0!s}".format(traceback.format_exc()))

        return user_list

    def getResolverId(self):
        """
        Returns the resolver Id
        This should be an Identifier of the resolver, preferable the type
        and the name of the resolver.

        :return: the id of the resolver
        :rtype: str
        """
        id_string = (f"{self.uri}{self.basedn}{self.searchfilter}"
                     f"{sorted(self.userinfo.items(), key=itemgetter(0))}")
        result = binascii.hexlify(hashlib.sha1(id_string.encode("utf-8")).digest())  # nosec B324 # hash used as unique identifier
        return result.decode('utf8')

    @staticmethod
    def getResolverClassType():
        return 'ldapresolver'

    @staticmethod
    def getResolverDescriptor():
        return IdResolver.getResolverClassDescriptor()

    @staticmethod
    def getResolverType():
        return IdResolver.getResolverClassType()

    def loadConfig(self, config):
        """
        Load the config from conf.

        :param config: The configuration from the Config Table
        :type config: dict


        '#ldap_uri': 'LDAPURI',
        '#ldap_basedn': 'LDAPBASE',
        '#ldap_binddn': 'BINDDN',
        '#ldap_password': 'BINDPW',
        '#ldap_timeout': 'TIMEOUT',
        '#ldap_sizelimit': 'SIZELIMIT',
        '#ldap_loginattr': 'LOGINNAMEATTRIBUTE',
        '#ldap_searchfilter': 'LDAPSEARCHFILTER',
        '#ldap_mapping': 'USERINFO',
        '#ldap_uidtype': 'UIDTYPE',
        '#ldap_noreferrals' : 'NOREFERRALS',
        '#ldap_editable' : 'EDITABLE',
        '#ldap_certificate': 'CACERTIFICATE',
        '#ldap_keytabfile': 'KEYTABFILE',

        """
        self.uri = config.get("LDAPURI")
        self.basedn = config.get("LDAPBASE")
        self.binddn = config.get("BINDDN")
        # object_classes is a comma separated list like
        # ["top", "person", "organizationalPerson", "user", "inetOrgPerson"]
        self.object_classes = [cl.strip() for cl in config.get("OBJECT_CLASSES", "").split(",")]
        self.dn_template = config.get("DN_TEMPLATE", "")
        self.bindpw = config.get("BINDPW")
        self.timeout = int(config.get("TIMEOUT", 5))
        self.cache_timeout = int(config.get("CACHE_TIMEOUT", 120))
        self.sizelimit = int(config.get("SIZELIMIT", 500))
        self.loginname_attribute = [la.strip() for la in config.get("LOGINNAMEATTRIBUTE", "").split(",")]
        self.searchfilter = config.get("LDAPSEARCHFILTER")
        userinfo = config.get("USERINFO", "{}")
        self.userinfo = yaml.safe_load(userinfo)
        self.userinfo["username"] = self.loginname_attribute[0]
        multivalueattributes = config.get("MULTIVALUEATTRIBUTES") or '["mobile"]'
        self.multivalueattributes = yaml.safe_load(multivalueattributes)
        self.map = yaml.safe_load(userinfo)
        self.uidtype = config.get("UIDTYPE", "DN")
        self.noreferrals = is_true(config.get("NOREFERRALS", False))
        self.start_tls = is_true(config.get("START_TLS", False)) and not self.uri.lower().startswith("ldaps")
        self.get_info = get_info_configuration(is_true(config.get("NOSCHEMAS", False)))
        self._editable = config.get("EDITABLE", False)
        self.scope = config.get("SCOPE") or ldap3.SUBTREE
        self.resolverId = self.uri
        self.authtype = config.get("AUTHTYPE", AUTHTYPE.SIMPLE)
        self.keytabfile = config.get('KEYTABFILE', None)
        self.tls_verify = is_true(config.get("TLS_VERIFY", False))
        # Fallback to DEFAULT_TLS_PROTOCOL (TLSv1: 3, TLSv1.1: 4, v1.2: 5, TLS negotiation: 2)
        self.tls_version = int(config.get("TLS_VERSION") or DEFAULT_TLS_PROTOCOL)
        self.tls_ca_file = config.get("TLS_CA_FILE")
        self.tls_context = self._get_tls_context(ldap_uri=self.uri, start_tls=self.start_tls,
                                                 tls_version=self.tls_version,
                                                 tls_verify=self.tls_verify,
                                                 tls_ca_file=self.tls_ca_file)
        self.serverpool_persistent = is_true(config.get("SERVERPOOL_PERSISTENT", False))
        self.serverpool_rounds = int(config.get("SERVERPOOL_ROUNDS") or SERVERPOOL_ROUNDS)
        self.serverpool_skip = int(config.get("SERVERPOOL_SKIP") or SERVERPOOL_SKIP)
        self.serverpool_strategy = config.get("SERVERPOOL_STRATEGY") or SERVERPOOL_STRATEGY
        # The configuration might have changed. We reset the serverpool
        self.serverpool = None
        self.i_am_bound = False

        # settings for recursive search of groups
        self.recursive_group_search = is_true(config.get("recursive_group_search", False))
        self.group_name_attribute = config.get("group_name_attribute")
        self.group_search_filter = config.get("group_search_filter")
        self.group_attribute_mapping_key = config.get("group_attribute_mapping_key")

        if self.recursive_group_search:
            if not self.group_name_attribute or not self.group_search_filter or not self.group_attribute_mapping_key:
                log.info("Incomplete configuration for recursive user group search. Recursive search is not applied.")
                self.recursive_group_search = False

        return self

    @property
    def has_multiple_loginnames(self):
        """
        Return if this resolver has multiple loginname attributes
        :return: bool
        """
        return len(self.loginname_attribute) > 1

    @staticmethod
    def split_uri(uri):
        """
        Splits LDAP URIs like:
        * ldap://server
        * ldaps://server
        * ldap[s]://server:1234
        * server
        :param uri: The LDAP URI
        :return: Returns a tuple of Servername, Port and SSL(bool)
        """
        port = None
        use_ssl = False
        ldap_elems = uri.split(":")
        if len(ldap_elems) == 3:
            server = ldap_elems[1].strip("/")
            port = int(ldap_elems[2])
            if ldap_elems[0].lower() == "ldaps":
                use_ssl = True
            else:
                use_ssl = False
        elif len(ldap_elems) == 2:
            server = ldap_elems[1].strip("/")
            port = None
            if ldap_elems[0].lower() == "ldaps":
                use_ssl = True
            else:
                use_ssl = False
        else:
            server = uri

        return server, port, use_ssl

    @classmethod
    def create_serverpool(cls, urilist, timeout, get_info=None, tls_context=None, rounds=SERVERPOOL_ROUNDS,
                          exhaust=SERVERPOOL_SKIP, pool_cls=ldap3.ServerPool, strategy=SERVERPOOL_STRATEGY):
        """
        This creates the serverpool for the ldap3 connection.
        The URI from the LDAP resolver can contain a comma separated list of
        LDAP servers. These are split and then added to the pool.

        See
        https://github.com/cannatag/ldap3/blob/master/docs/manual/source/servers.rst#server-pool

        :param urilist: The list of LDAP URIs, comma separated
        :type urilist: basestring
        :param timeout: The connection timeout
        :type timeout: float
        :param get_info: The get_info type passed to the ldap3.Sever
            constructor. default: ldap3.SCHEMA, should be ldap3.NONE in case
            of a bind.
        :param tls_context: A ldap3.tls object, which defines if certificate
            verification should be performed
        :param rounds: The number of rounds we should cycle through the server pool
            before giving up
        :param exhaust: The seconds, for how long a non-reachable server should be
            removed from the serverpool
        :param pool_cls: ``ldap3.ServerPool`` subclass that should be instantiated
        :param strategy: The pooling strategy of the server-pool
        :type strategy: str
        :return: Server Pool
        :rtype: ldap3.ServerPool
        """
        get_info = get_info or ldap3.SCHEMA
        strategy = LDAP_STRATEGY.get(strategy, SERVERPOOL_STRATEGY)
        server_pool = pool_cls(None, strategy,
                               active=rounds,
                               exhaust=exhaust)
        for uri in urilist.split(","):
            uri = uri.strip()
            host, port, ssl = cls.split_uri(uri)
            server = ldap3.Server(host, port=port,
                                  use_ssl=ssl,
                                  connect_timeout=float(timeout),
                                  get_info=get_info,
                                  tls=tls_context)
            server_pool.add(server)
            log.debug("Added {0!s}, {1!s}, {2!s} to server pool.".format(host, port, ssl))
        return server_pool

    def get_serverpool_instance(self, get_info=None):
        """
        Return a ``ServerPool`` instance that should be used. If ``SERVERPOOL_PERSISTENT``
        is enabled, invoke ``get_persistent_serverpool`` to retrieve a per-process
        server pool instance. If it is not enabled, invoke ``create_serverpool``
        to retrieve a per-request server pool instance.

        :param get_info: one of ldap3.SCHEMA, ldap3.NONE, ldap3.ALL
        :return: a ``ServerPool``/``LockingServerPool`` instance
        """
        if self.serverpool_persistent:
            return self.get_persistent_serverpool(get_info)
        else:
            return self.create_serverpool(self.uri, self.timeout, get_info, self.tls_context,
                                          self.serverpool_rounds, self.serverpool_skip,
                                          strategy=self.serverpool_strategy)

    def get_persistent_serverpool(self, get_info=None):
        """
        Return a process-level instance of ``LockingServerPool`` for the current LDAP resolver
        configuration. Retrieve it from the app-local store. If such an instance does not exist
        yet, create one.

        :param get_info: one of ldap3.SCHEMA, ldap3.NONE, ldap3.ALL
        :return: a ``LockingServerPool`` instance
        """
        if not get_info:
            get_info = ldap3.SCHEMA
        pools = get_app_local_store().setdefault('ldap_server_pools', {})
        # Create a hashable tuple that describes the current server pool configuration
        pool_description = (self.uri,
                            self.timeout,
                            get_info,
                            repr(self.tls_context),  # this is the string representation of the TLS context
                            self.serverpool_rounds,
                            self.serverpool_skip)
        if pool_description not in pools:
            log.debug("Creating a persistent server pool instance for {!r} ...".format(pool_description))
            # Create a suitable instance of ``LockingServerPool``
            server_pool = self.create_serverpool(self.uri, self.timeout, get_info,
                                                 self.tls_context, self.serverpool_rounds, self.serverpool_skip,
                                                 pool_cls=LockingServerPool, strategy=self.serverpool_strategy)
            # It may happen that another thread tries to add an instance to the dictionary concurrently.
            # However, only one of them will win, and the other ``LockingServerPool`` instance will be
            # garbage-collected eventually.
            return pools.setdefault(pool_description, server_pool)
        else:
            # If there is already a ``LockingServerPool`` instance, return it.
            # We never remove instances from the dictionary, so a ``KeyError`` cannot occur.
            # As a side effect, when we change the LDAP Id resolver configuration,
            # outdated ``LockingServerPool`` instances will survive until the next server restart.
            return pools[pool_description]

    @classmethod
    def getResolverClassDescriptor(cls):
        """
        return the descriptor of the resolver, which is
        - the class name and
        - the config description

        :return: resolver description dict
        :rtype:  dict
        """
        descriptor = {}
        typ = cls.getResolverType()
        descriptor['clazz'] = "useridresolver.LDAPIdResolver.IdResolver"
        descriptor['config'] = {'LDAPURI': 'string',
                                'LDAPBASE': 'string',
                                'BINDDN': 'string',
                                'BINDPW': 'password',
                                'KEYTABFILE': 'string',
                                'TIMEOUT': 'int',
                                'SIZELIMIT': 'int',
                                'LOGINNAMEATTRIBUTE': 'string',
                                'LDAPSEARCHFILTER': 'string',
                                'USERINFO': 'string',
                                'UIDTYPE': 'string',
                                'NOREFERRALS': 'bool',
                                'NOSCHEMAS': 'bool',
                                'CACERTIFICATE': 'string',
                                'EDITABLE': 'bool',
                                'SCOPE': 'string',
                                'AUTHTYPE': 'string',
                                'TLS_VERIFY': 'bool',
                                'TLS_VERSION': 'int',
                                'TLS_CA_FILE': 'string',
                                'START_TLS': 'bool',
                                'CACHE_TIMEOUT': 'int',
                                'SERVERPOOL_STRATEGY': 'string',
                                'SERVERPOOL_ROUNDS': 'int',
                                'SERVERPOOL_SKIP': 'int',
                                'SERVERPOOL_PERSISTENT': 'bool',
                                'OBJECT_CLASSES': 'string',
                                'DN_TEMPLATE': 'string',
                                'MULTIVALUEATTRIBUTES': 'string',
                                'group_name_attribute': 'string',
                                'group_search_filter': 'string',
                                'group_attribute_mapping_key': 'string',
                                'recursive_group_search': 'bool'}
        return {typ: descriptor}

    @classmethod
    def testconnection(cls, param):
        """
        This function lets you test the to be saved LDAP connection.

        Parameters are:
            BINDDN, BINDPW, LDAPURI, TIMEOUT, LDAPBASE, LOGINNAMEATTRIBUTE,
            LDAPSEARCHFILTER, USERINFO, SIZELIMIT, NOREFERRALS, CACERTIFICATE,
            AUTHTYPE, TLS_VERIFY, TLS_VERSION, TLS_CA_FILE, SERVERPOOL_ROUNDS,
            SERVERPOOL_SKIP, SERVERPOOL_STRATEGY

        :param param: A dictionary with all necessary parameter to test
                        the connection.
        :type param: dict
        :return: Tuple of success and a description
        :rtype: (bool, string)
        """
        success = False
        uidtype = param.get("UIDTYPE")
        timeout = int(param.get("TIMEOUT", 5))
        ldap_uri = param.get("LDAPURI")
        size_limit = int(param.get("SIZELIMIT", 500))
        serverpool_rounds = int(param.get("SERVERPOOL_ROUNDS") or SERVERPOOL_ROUNDS)
        serverpool_skip = int(param.get("SERVERPOOL_SKIP") or SERVERPOOL_SKIP)
        pool_strat = param.get("SERVERPOOL_STRATEGY") or SERVERPOOL_STRATEGY
        serverpool_strategy = LDAP_STRATEGY.get(pool_strat, SERVERPOOL_STRATEGY)
        start_tls = is_true(param.get("START_TLS", False)) and not ldap_uri.lower().startswith("ldaps")
        tls_verify = is_true(param.get("TLS_VERIFY"))
        tls_context = cls._get_tls_context(ldap_uri=ldap_uri,
                                           start_tls=start_tls,
                                           tls_version=param.get("TLS_VERSION"),
                                           tls_verify=tls_verify,
                                           tls_ca_file=param.get("TLS_CA_FILE"),
                                           tls_options=None)
        get_info = get_info_configuration(is_true(param.get("NOSCHEMAS")))
        try:
            server_pool = cls.create_serverpool(ldap_uri, timeout,
                                                tls_context=tls_context,
                                                get_info=get_info,
                                                rounds=serverpool_rounds,
                                                exhaust=serverpool_skip,
                                                strategy=serverpool_strategy)
            conn = cls.create_connection(authtype=param.get("AUTHTYPE", AUTHTYPE.SIMPLE),
                                         server=server_pool,
                                         user=param.get("BINDDN"),
                                         password=param.get("BINDPW"),
                                         receive_timeout=timeout,
                                         auto_referrals=not param.get("NOREFERRALS"),
                                         start_tls=start_tls,
                                         keytabfile=param.get('KEYTABFILE', None))

            if not conn.bind():
                log.error(f"LDAP Bind unsuccessful: "
                          f"{conn.result.get('description')} ({conn.result.get('result')})!")
                raise ResolverError(f"Unable to perform bind operation: "
                                    f"{conn.result.get('description')} ({conn.result.get('result')})!")
            # create searchattributes
            attributes = list(yaml.safe_load(param["USERINFO"]).values())
            if uidtype.lower() != "dn":
                attributes.append(str(uidtype))
            # search for users...
            search_generator = conn.extend.standard.paged_search(
                search_base=param["LDAPBASE"],
                search_filter="(&" + param["LDAPSEARCHFILTER"] + ")",
                search_scope=param.get("SCOPE") or ldap3.SUBTREE,
                attributes=attributes,
                paged_size=100,
                size_limit=size_limit,
                generator=True)
            # returns a generator of dictionaries
            elapsed_time = conn.usage.elapsed_time.total_seconds()
            count = 0
            uidtype_count = 0
            for entry in ignore_sizelimit_exception(conn, search_generator):
                # Fix for searchResRef entries which have no attributes
                if entry.get('type') == 'searchResRef':
                    continue
                try:
                    userid = cls._get_uid(entry, uidtype)
                    count += 1
                    if userid:
                        uidtype_count += 1
                except Exception as exx:  # pragma: no cover
                    log.warning("Error during fetching LDAP objects:"
                                " {0!r}".format(exx))
                    log.debug("{0!s}".format(traceback.format_exc()))

            if uidtype_count < count:  # pragma: no cover
                message = _("Your LDAP config found {0!s} user objects in {2:.4f}s, "
                            "but only {1!s} with the specified "
                            "uidtype.").format(count, uidtype_count, elapsed_time)
            else:
                message = _("Your LDAP config seems to be OK, {0!s} user objects "
                            "found in {1:.4f}s.").format(count, elapsed_time)

            conn.unbind()
            success = True

        except Exception as e:
            message = f"{e}"
            log.debug("{0!s}".format(traceback.format_exc()))

        return success, message

    def add_user(self, attributes: dict=None):
        """
        Add a new user to the LDAP directory.
        The user can only be created in the LDAP using a DN.
        So we have to construct the DN out of the given attributes.

        attributes are these
        "username", "surname", "givenname", "email",
        "mobile", "phone", "password"

        :param attributes: Attributes according to the attribute mapping
        :type attributes: dict
        :return: The new UID of the user. The UserIdResolver needs to
                 determine the way how to create the UID.
        """
        # TODO: We still have some utf8 issues creating users with special characters.
        attributes = attributes or {}

        dn = self.dn_template
        dn = dn.replace("<basedn>", self.basedn)
        dn = dn.replace("<username>", attributes.get("username", ""))
        dn = dn.replace("<givenname>", attributes.get("givenname", ""))
        dn = dn.replace("<surname>", attributes.get("surname", ""))

        try:
            self._bind()
            params = self._attributes_to_ldap_attributes(attributes)
            self.connection.add(dn, self.object_classes, params)
            log.debug(f"LDAP add operation took {self.connection.usage.elapsed_time}")

        except Exception as e:
            log.warning("Error accessing LDAP server: {0!r}".format(e))
            log.debug("{0}".format(traceback.format_exc()))
            raise privacyIDEAError(e)

        if self.connection.result.get("result") != 0:
            log.warning(f"Error during adding of user {dn}: "
                        f"{self.connection.result.get('description')} ({self.connection.result.get('result')})")
            raise privacyIDEAError(self.connection.result.get('message'))

        return self.getUserId(attributes.get("username"))

    def delete_user(self, uid):
        """
        Delete a user from the LDAP Directory.
        The user is referenced by the user id.

        :param uid: The uid of the user object, that should be deleted.
        :type uid: str
        :return: Returns True in case of success
        :rtype: bool
        """
        res = True
        try:
            self._bind()

            self.connection.delete(self._getDN(uid))
            log.debug(f"LDAP delete operation took {self.connection.usage.elapsed_time}")
        except Exception as ex:
            log.warning(f"Failed to delete user with uid {uid}: {ex}")
            res = False
        return res

    def _attributes_to_ldap_attributes(self, attributes):
        """
        takes the attributes and maps them to the LDAP attributes
        :param attributes: Attributes to be updated
        :type attributes: dict
        :return: dict with attribute name as keys and values
        """
        ldap_attributes = {}
        for fieldname, value in attributes.items():
            if self.map.get(fieldname):
                if fieldname == "password":
                    # Variable value may be either a string or a list
                    # so catch the TypeError exception if we get the wrong
                    # variable type
                    try:
                        pw_hash = ldap_salted_sha1.hash(value[1][0])
                        value[1][0] = pw_hash
                        ldap_attributes[self.map.get(fieldname)] = value
                    except TypeError as _e:
                        pw_hash = ldap_salted_sha1.hash(value)
                        ldap_attributes[self.map.get(fieldname)] = pw_hash
                else:
                    ldap_attributes[self.map.get(fieldname)] = value

        return ldap_attributes

    def _create_ldap_modify_changes(self, attributes, uid):
        """
        Identifies if an LDAP attribute already exists and if the value needs to be updated, deleted or added.

        :param attributes: Attributes to be updated
        :type attributes: dict
        :param uid: The uid of the user object in the resolver
        :type uid: basestring
        :return: dict with attribute name as keys and values
        """
        modify_changes = {}
        uinfo = self.getUserInfo(uid)

        for fieldname, value in attributes.items():
            if value:
                if fieldname in uinfo:
                    modify_changes[fieldname] = [MODIFY_REPLACE, [value]]
                else:
                    modify_changes[fieldname] = [MODIFY_ADD, [value]]
            else:
                modify_changes[fieldname] = [MODIFY_DELETE, [value]]

        return modify_changes

    def update_user(self, uid, attributes=None):
        """
        Update an existing user.
        This function is also used to update the password. Since the
        attribute mapping know, which field contains the password,
        this function can also take care for password changing.

        Attributes that are not contained in the dict attributes are not
        modified.

        :param uid: The uid of the user object in the resolver.
        :type uid: basestring
        :param attributes: Attributes to be updated.
        :type attributes: dict
        :return: True in case of success
        """
        attributes = attributes or {}
        try:
            self._bind()

            mapped = self._create_ldap_modify_changes(attributes, uid)
            params = self._attributes_to_ldap_attributes(mapped)
            self.connection.modify(self._getDN(uid), params)
            log.debug(f"LDAP modify operation took {self.connection.usage.elapsed_time}")
        except Exception as e:
            log.error("Error accessing LDAP server: {0!r}".format(e))
            log.debug("{0!s}".format(traceback.format_exc()))
            return False

        if self.connection.result.get('result') != 0:
            log.error("Error during update of user {0!r}: "
                      "{1!r}".format(uid, self.connection.result.get("message")))
            return False

        return True

    @staticmethod
    def create_connection(authtype=None, server=None, user=None,
                          password=None, auto_bind=ldap3.AUTO_BIND_NONE,
                          client_strategy=ldap3.SYNC,
                          check_names=True,
                          auto_referrals=False,
                          receive_timeout=5,
                          start_tls=False,
                          keytabfile=None):
        """
        Create a connection to the LDAP server.

        :param authtype:
        :param server:
        :param user:
        :param password:
        :param auto_bind:
        :param client_strategy:
        :param check_names:
        :param auto_referrals:
        :param receive_timeout: At the moment we do not use this,
                                since receive_timeout is not supported by ldap3 < 2
        :type receive_timeout: float
        :param start_tls: Use startTLS for connection to server
        :type start_tls: bool
        :param keytabfile: Path to keytab file for service account
        :type keytabfile: str or None
        :return:
        """
        conn_opts = {'auto_bind': auto_bind,
                     'client_strategy': client_strategy,
                     'check_names': check_names,
                     'receive_timeout': receive_timeout,
                     'auto_referrals': auto_referrals,
                     'collect_usage': True}

        if not user:
            # without a user we can only use an anonymous binds
            conn_opts.update({'authentication': ldap3.ANONYMOUS})
        elif authtype == AUTHTYPE.SIMPLE:
            # SIMPLE works with passwords as UTF8 and unicode
            password = to_unicode(password)
            conn_opts.update({'user': user,
                              'password': password,
                              'authentication': ldap3.SIMPLE})
        elif authtype == AUTHTYPE.NTLM:  # pragma: no cover
            # NTLM requires the password to be unicode
            password = to_unicode(password)
            conn_opts.update({'user': user,
                              'password': password,
                              'authentication': ldap3.NTLM})
        elif authtype == AUTHTYPE.SASL_DIGEST_MD5:  # pragma: no cover
            password = to_unicode(password)
            sasl_credentials = (str(user), str(password))
            conn_opts.update({'sasl_mechanism': ldap3.DIGEST_MD5,
                              'sasl_credentials': sasl_credentials,
                              'authentication': ldap3.SASL})
        elif authtype == AUTHTYPE.SASL_KERBEROS:
            cred_store = {'client_keytab': keytabfile} if keytabfile else None
            conn_opts.update({'sasl_mechanism': ldap3.KERBEROS,
                              'authentication': ldap3.SASL,
                              'user': user,
                              'cred_store': cred_store})
        else:
            raise ResolverError(f"Authtype {authtype} not supported")

        connection = ldap3.Connection(server, **conn_opts)
        if start_tls:
            connection.open(read_server_info=False)
            log.debug("Doing start_tls")
            try:
                if not connection.start_tls(read_server_info=False):
                    err_msg = (f"Unable to create connection with StartTLS: "
                               f"{connection.result.get('description')} "
                               f"({connection.result.get('error')})")
                    log.error(err_msg)
                    raise ResolverError(err_msg)
            except Exception as e:
                err_msg = f"Unable to create connection with StartTLS: {e}"
                log.error(err_msg)
                raise ResolverError(err_msg)

        return connection

    @property
    def editable(self):
        """
        Return true, if the instance of the resolver is configured editable
        :return:
        """
        # Depending on the database this might look different
        # Usually this is "1"
        return is_true(self._editable)
