# -*- coding: utf-8 -*-
#  Copyright (C) 2014 Cornelius Kölbel
#  contact:  corny@cornelinux.de
#
#  2018-12-14 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add censored password functionality
#  2017-12-22 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add configurable multi-value-attributes
#             with the help of Nomen Nescio
#  2017-07-20 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Fix unicode usernames
#  2017-01-23 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add certificate verification
#  2017-01-07 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Use get_info=ldap3.NONE for binds to avoid querying of subschema
#             Remove LDAPFILTER and self.reversefilter
#  2016-07-14 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Adding getUserId cache.
#  2016-04-13 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add object_classes and dn_composition to configuration
#             to allow flexible user_add
#  2016-04-10 Martin Wheldon <martin.wheldon@greenhills-it.co.uk>
#             Allow user accounts held in LDAP to be edited, providing
#             that the account they are using has permission to edit
#             those attributes in the LDAP directory
#  2016-02-22 Salvo Rapisarda
#             Allow objectGUID to be a users attribute
#  2016-02-19 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Allow objectGUID to be the uid.
#  2015-10-05 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Remove reverse_map, so that one LDAP field can map
#             to several privacyIDEA fields.
#  2015-04-16 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add redundancy with LDAP3 Server pools. Round Robin Strategy
#  2015-04-15 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Increase test coverage
#  2014-12-25 Cornelius Kölbel <cornelius@privacyidea.org>
#             Rewrite for flask migration
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# License as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
__doc__ = """This is the resolver to find users in LDAP directories like
OpenLDAP and Active Directory.

The file is tested in tests/test_lib_resolver.py
"""

import logging
import yaml
import functools

from .UserIdResolver import UserIdResolver

import ldap3
from ldap3 import MODIFY_REPLACE, MODIFY_ADD, MODIFY_DELETE
from ldap3 import Server, Tls, Connection
from ldap3.core.exceptions import LDAPOperationResult
from ldap3.core.results import RESULT_SIZE_LIMIT_EXCEEDED
import ssl

import os.path

import traceback
from passlib.hash import ldap_salted_sha1
import hashlib
import binascii
from privacyidea.lib.crypto import urandom, geturandom
from privacyidea.lib.utils import is_true
import datetime

from privacyidea.lib import _
from privacyidea.lib.utils import to_utf8, to_unicode
from privacyidea.lib.error import privacyIDEAError
import uuid
from ldap3.utils.conv import escape_bytes
from operator import itemgetter
from six import string_types

CACHE = {}

log = logging.getLogger(__name__)
ENCODING = "utf-8"
# The number of rounds the resolver tries to reach a responding server in the
#  pool
SERVERPOOL_ROUNDS = 2
# The number of seconds a non-responding server is removed from the server pool
SERVERPOOL_SKIP = 30
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


def trim_objectGUID(userId):
    userId = uuid.UUID(u"{{{0!s}}}".format(userId)).bytes_le
    userId = escape_bytes(userId)
    return userId


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
            # If the generator is exceed, we stop
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
            now = datetime.datetime.now()
            tdelta = datetime.timedelta(seconds=self.cache_timeout)
            if not resolver_id in CACHE:
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


class IdResolver (UserIdResolver):

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
        self.timeout = 5.0  # seconds!
        self.sizelimit = 500
        self.loginname_attribute = [""]
        self.searchfilter = u""
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
        self.serverpool_rounds = SERVERPOOL_ROUNDS
        self.serverpool_skip = SERVERPOOL_SKIP
        self.serverpool = None

    def checkPass(self, uid, password):
        """
        This function checks the password for a given uid.
        - returns true in case of success
        -         false if password does not match

        """
        if self.authtype == AUTHTYPE.NTLM:  # pragma: no cover
            # fetch the PreWindows 2000 Domain from the self.binddn
            # which would be of the format DOMAIN\username and compose the
            # bind_user to DOMAIN\sAMAcountName
            domain_name = self.binddn.split('\\')[0]
            uinfo = self.getUserInfo(uid)
            # In fact we need the sAMAccountName. If the username mapping is
            # another attribute than the sAMAccountName the authentication
            # will fail!
            bind_user = u"{0!s}\{1!s}".format(domain_name, uinfo.get("username"))
        else:
            bind_user = self._getDN(uid)

        if not self.serverpool:
            self.serverpool = self.get_serverpool(self.uri, self.timeout,
                                                  get_info=ldap3.NONE,
                                                  tls_context=self.tls_context,
                                                  rounds=self.serverpool_rounds,
                                                  exhaust=self.serverpool_skip)

        try:
            log.debug("Authtype: {0!r}".format(self.authtype))
            log.debug("user    : {0!r}".format(bind_user))
            # Whatever happens. If we have an empty bind_user, we must break
            # since we must avoid anonymous binds!
            if not bind_user or len(bind_user) < 1:
                raise Exception("No valid user. Empty bind_user.")
            l = self.create_connection(authtype=self.authtype,
                                       server=self.serverpool,
                                       user=bind_user,
                                       password=password,
                                       receive_timeout=self.timeout,
                                       auto_referrals=not self.noreferrals,
                                       start_tls=self.start_tls)
            r = l.bind()
            log.debug("bind result: {0!r}".format(r))
            if not r:
                raise Exception("Wrong credentials")
            log.debug("bind seems successful.")
            l.unbind()
            log.debug("unbind successful.")
        except Exception as e:
            log.warning("failed to check password for {0!r}/{1!r}: {2!r}".format(uid, bind_user, e))
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
        uid = None
        if uidtype.lower() == "dn":
           uid = entry.get("dn")
        else:
            attributes = entry.get("attributes")
            if type(attributes.get(uidtype)) == list:
                uid = attributes.get(uidtype)[0]
            else:
                uid = attributes.get(uidtype)
            if uidtype.lower() == "objectguid":
                # For ldap3 versions <= 2.4.1, objectGUID attribute values are returned as UUID strings.
                # For versions greater than 2.4.1, they are returned in the curly-braced string
                # representation, i.e. objectGUID := "{" UUID "}"
                # In order to ensure backwards compatibility for user mappings,
                # we strip the curly braces from objectGUID values.
                # If we are using ldap3 <= 2.4.1, there are no curly braces and we leave the value unchanged.
                uid = uid.strip("{").strip("}")
        return uid

    def _trim_user_id(self, userId):
        """
        If we search for the objectGUID we can not search for the normal
        string representation but we need to search for the bytestring in AD.
        :param userId: The userId
        :return: the trimmed userId
        """
        if self.uidtype == "objectGUID":
            userId = trim_objectGUID(userId)
        return userId

    @cache
    def _getDN(self, userId):
        """
        This function returns the DN of a userId.
        Therefor it evaluates the self.uidtype.

        :param userId: The userid of a user
        :type userId: string

        :return: The DN of the object.
        """
        dn = ""
        if self.uidtype.lower() == "dn":
            dn = userId
        else:
            # get the DN for the Object
            self._bind()
            search_userId = self._trim_user_id(userId)
            filter = u"(&{0!s}({1!s}={2!s}))".format(self.searchfilter,
                                                     self.uidtype,
                                                     search_userId)
            self.l.search(search_base=self.basedn,
                          search_scope=self.scope,
                          search_filter=filter,
                          attributes=list(self.userinfo.values()))
            r = self.l.response
            r = self._trim_result(r)
            if len(r) > 1:  # pragma: no cover
                raise Exception("Found more than one object for uid {0!r}".format(userId))
            elif len(r) == 1:
                dn = r[0].get("dn")
            else:
                log.info("The filter {0!r} returned no DN.".format(filter))

        return dn

    def _bind(self):
        if not self.i_am_bound:
            if not self.serverpool:
                self.serverpool = self.get_serverpool(self.uri, self.timeout,
                                              get_info=self.get_info,
                                              tls_context=self.tls_context,
                                              rounds=self.serverpool_rounds,
                                              exhaust=self.serverpool_skip)
            self.l = self.create_connection(authtype=self.authtype,
                                            server=self.serverpool,
                                            user=self.binddn,
                                            password=self.bindpw,
                                            receive_timeout=self.timeout,
                                            auto_referrals=not
                                            self.noreferrals,
                                            start_tls=self.start_tls)
            #log.error("LDAP Server Pool States: %s" % server_pool.pool_states)
            if not self.l.bind():
                raise Exception("Wrong credentials")
            self.i_am_bound = True

    @cache
    def getUserInfo(self, userId):
        """
        This function returns all user info for a given userid/object.

        :param userId: The userid of the object
        :type userId: string
        :return: A dictionary with the keys defined in self.userinfo
        :rtype: dict
        """
        ret = {}
        self._bind()

        if self.uidtype.lower() == "dn":
            # encode utf8, so that also german umlauts work in the DN
            self.l.search(search_base=userId,
                          search_scope=self.scope,
                          search_filter=u"(&" + self.searchfilter + u")",
                          attributes=list(self.userinfo.values()))
        else:
            search_userId = to_unicode(self._trim_user_id(userId))
            filter = u"(&{0!s}({1!s}={2!s}))".format(self.searchfilter,
                                                     self.uidtype,
                                                     search_userId)
            self.l.search(search_base=self.basedn,
                              search_scope=self.scope,
                              search_filter=filter,
                              attributes=list(self.userinfo.values()))

        r = self.l.response
        r = self._trim_result(r)
        if len(r) > 1:  # pragma: no cover
            raise Exception("Found more than one object for uid {0!r}".format(userId))

        for entry in r:
            attributes = entry.get("attributes")
            ret = self._ldap_attributes_to_user_object(attributes)

        return ret

    def _ldap_attributes_to_user_object(self, attributes):
        """
        This helper function converts the LDAP attributes to a dictionary for
        the privacyIDEA user. The LDAP Userinfo mapping is used to do so.

        :param attributes:
        :return: dict with privacyIDEA users.
        """
        ret = {}
        for ldap_k, ldap_v in attributes.items():
            for map_k, map_v in self.userinfo.items():
                if ldap_k == map_v:
                    if ldap_k == "objectGUID":
                        # An objectGUID should be no list, since it is unique
                        if isinstance(ldap_v, string_types):
                            ret[map_k] = ldap_v.strip("{").strip("}")
                        else:
                            raise Exception("The LDAP returns an objectGUID, that is no string: {0!s}".format(type(ldap_v)))
                    elif type(ldap_v) == list and map_k not in self.multivalueattributes:
                        # lists that are not in self.multivalueattributes return first value
                        # as a string. Multi-value-attributes are returned as a list
                        if ldap_v:
                            ret[map_k] = ldap_v[0]
                        else:
                            ret[map_k] = ""
                    else:
                        ret[map_k] = ldap_v
        return ret

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
    def getUserId(self, LoginName):
        """
        resolve the loginname to the userid.

        :param LoginName: The login name from the credentials
        :type LoginName: string
        :return: UserId as found for the LoginName
        """
        userid = ""
        self._bind()
        LoginName = to_unicode(LoginName)
        login_name = self._escape_loginname(LoginName)

        if len(self.loginname_attribute) > 1:
            loginname_filter = u""
            for l_attribute in self.loginname_attribute:
                # Special case if we have a guid
                try:
                    if l_attribute.lower() == "objectguid":
                        search_login_name = trim_objectGUID(login_name)
                    else:
                        search_login_name = login_name
                    loginname_filter += u"({!s}={!s})".format(l_attribute.strip(),
                                                              search_login_name)
                except ValueError:
                    # This happens if we have a self.loginname_attribute like ["sAMAccountName","objectGUID"],
                    # the user logs in with his sAMAccountName, which can
                    # not be transformed to a UUID
                    log.debug(u"Can not transform {0!s} to a objectGUID.".format(login_name))

            loginname_filter = u"|" + loginname_filter
        else:
            if self.loginname_attribute[0].lower() == "objectguid":
                search_login_name = trim_objectGUID(login_name)
            else:
                search_login_name = login_name
            loginname_filter = u"{!s}={!s}".format(self.loginname_attribute[0],
                                                   search_login_name)

        log.debug("login name filter: {!r}".format(loginname_filter))
        filter = u"(&{0!s}({1!s}))".format(self.searchfilter, loginname_filter)

        # create search attributes
        attributes = list(self.userinfo.values())
        if self.uidtype.lower() != "dn":
            attributes.append(str(self.uidtype))

        log.debug("Searching user {0!r} in LDAP.".format(LoginName))
        self.l.search(search_base=self.basedn,
                      search_scope=self.scope,
                      search_filter=filter,
                      attributes=attributes)

        r = self.l.response
        r = self._trim_result(r)
        if len(r) > 1:  # pragma: no cover
            raise Exception("Found more than one object for Loginname {0!r}".format(
                            LoginName))

        for entry in r:
            userid = self._get_uid(entry, self.uidtype)

        return userid

    def getUserList(self, searchDict):
        """
        :param searchDict: A dictionary with search parameters
        :type searchDict: dict
        :return: list of users, where each user is a dictionary
        """
        ret = []
        self._bind()
        attributes = list(self.userinfo.values())
        ad_timestamp = get_ad_timestamp_now()
        if self.uidtype.lower() != "dn":
            attributes.append(str(self.uidtype))

        # do the filter depending on the searchDict
        filter = u"(&" + self.searchfilter
        for search_key in searchDict.keys():
            # convert to unicode
            searchDict[search_key] = to_unicode(searchDict[search_key])
            if search_key == "accountExpires":
                comperator = ">="
                if searchDict[search_key] in ["1", 1]:
                    comperator = "<="
                filter += u"(&({0!s}{1!s}{2!s})(!({3!s}=0)))".format(
                    self.userinfo[search_key], comperator,
                    get_ad_timestamp_now(), self.userinfo[search_key])
            else:
                filter += u"({0!s}={1!s})".format(self.userinfo[search_key],
                                                  searchDict[search_key])
        filter += ")"

        g = self.l.extend.standard.paged_search(search_base=self.basedn,
                                                search_filter=filter,
                                                search_scope=self.scope,
                                                attributes=attributes,
                                                paged_size=100,
                                                size_limit=self.sizelimit,
                                                generator=True)
        # returns a generator of dictionaries
        for entry in ignore_sizelimit_exception(self.l, g):
            # Simple fix for ignored sizelimit with Active Directory
            if len(ret) >= self.sizelimit:
                break
            # Fix for searchResRef entries which have no attributes
            if entry.get('type') == 'searchResRef':
                continue
            try:
                attributes = entry.get("attributes")
                user = self._ldap_attributes_to_user_object(attributes)
                user['userid'] = self._get_uid(entry, self.uidtype)
                ret.append(user)
            except Exception as exx:  # pragma: no cover
                log.error("Error during fetching LDAP objects: {0!r}".format(exx))
                log.debug("{0!s}".format(traceback.format_exc()))

        return ret

    def getResolverId(self):
        """
        Returns the resolver Id
        This should be an Identifier of the resolver, preferable the type
        and the name of the resolver.

        :return: the id of the resolver
        :rtype: str
        """
        s = u"{0!s}{1!s}{2!s}{3!s}".format(self.uri, self.basedn,
                                           self.searchfilter,
                                           sorted(self.userinfo.items(), key=itemgetter(0)))
        r = binascii.hexlify(hashlib.sha1(s.encode("utf-8")).digest())
        return r.decode('utf8')

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

        """
        self.uri = config.get("LDAPURI")
        self.basedn = config.get("LDAPBASE")
        self.binddn = config.get("BINDDN")
        # object_classes is a comma separated list like
        # ["top", "person", "organizationalPerson", "user", "inetOrgPerson"]
        self.object_classes = [cl.strip() for cl in config.get("OBJECT_CLASSES", "").split(",")]
        self.dn_template = config.get("DN_TEMPLATE", "")
        self.bindpw = config.get("BINDPW")
        self.timeout = float(config.get("TIMEOUT", 5))
        self.cache_timeout = int(config.get("CACHE_TIMEOUT", 120))
        self.sizelimit = int(config.get("SIZELIMIT", 500))
        self.loginname_attribute = [la.strip() for la in config.get("LOGINNAMEATTRIBUTE","").split(",")]
        self.searchfilter = config.get("LDAPSEARCHFILTER")
        userinfo = config.get("USERINFO", "{}")
        self.userinfo = yaml.safe_load(userinfo)
        self.userinfo["username"] = self.loginname_attribute[0]
        multivalueattributes = config.get("MULTIVALUEATTRIBUTES") or '["mobile"]'
        self.multivalueattributes = yaml.safe_load(multivalueattributes)
        self.map = yaml.safe_load(userinfo)
        self.uidtype = config.get("UIDTYPE", "DN")
        self.noreferrals = is_true(config.get("NOREFERRALS", False))
        self.start_tls = is_true(config.get("START_TLS", False))
        self.get_info = get_info_configuration(is_true(config.get("NOSCHEMAS", False)))
        self._editable = config.get("EDITABLE", False)
        self.scope = config.get("SCOPE") or ldap3.SUBTREE
        self.resolverId = self.uri
        self.authtype = config.get("AUTHTYPE", AUTHTYPE.SIMPLE)
        self.tls_verify = is_true(config.get("TLS_VERIFY", False))
        # Fallback to TLSv1. (int: 3, TLSv1.1: 4, v1.2: 5)
        self.tls_version = int(config.get("TLS_VERSION") or ssl.PROTOCOL_TLSv1)

        self.tls_ca_file = config.get("TLS_CA_FILE") or DEFAULT_CA_FILE
        if self.tls_verify and (self.uri.lower().startswith("ldaps") or
                                    self.start_tls):
            self.tls_context = Tls(validate=ssl.CERT_REQUIRED,
                                   version=self.tls_version,
                                   ca_certs_file=self.tls_ca_file)
        else:
            self.tls_context = None
        self.serverpool_rounds = int(config.get("SERVERPOOL_ROUNDS") or SERVERPOOL_ROUNDS)
        self.serverpool_skip = int(config.get("SERVERPOOL_SKIP") or SERVERPOOL_SKIP)
        # The configuration might have changed. We reset the serverpool
        self.serverpool = None
        self.i_am_bound = False

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
        ssl = False
        ldap_elems = uri.split(":")
        if len(ldap_elems) == 3:
            server = ldap_elems[1].strip("/")
            port = int(ldap_elems[2])
            if ldap_elems[0].lower() == "ldaps":
                ssl = True
            else:
                ssl = False
        elif len(ldap_elems) == 2:
            server = ldap_elems[1].strip("/")
            port = None
            if ldap_elems[0].lower() == "ldaps":
                ssl = True
            else:
                ssl = False
        else:
            server = uri

        return server, port, ssl

    @classmethod
    def get_serverpool(cls, urilist, timeout, get_info=None, tls_context=None, rounds=SERVERPOOL_ROUNDS,
                       exhaust=SERVERPOOL_SKIP):
        """
        This create the serverpool for the ldap3 connection.
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
        :return: Server Pool
        :rtype: LDAP3 Server Pool Instance
        """
        get_info = get_info or ldap3.SCHEMA
        server_pool = ldap3.ServerPool(None, ldap3.ROUND_ROBIN,
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
                                'SERVERPOOL_ROUNDS': 'int',
                                'SERVERPOOL_SKIP': 'int',
                                'OBJECT_CLASSES': 'string',
                                'DN_TEMPLATE': 'string'}
        return {typ: descriptor}

    @classmethod
    def testconnection(cls, param):
        """
        This function lets you test the to be saved LDAP connection.

        :param param: A dictionary with all necessary parameter to test
                        the connection.
        :type param: dict
        :return: Tuple of success and a description
        :rtype: (bool, string)

        Parameters are:
            BINDDN, BINDPW, LDAPURI, TIMEOUT, LDAPBASE, LOGINNAMEATTRIBUTE,
            LDAPSEARCHFILTER, USERINFO, SIZELIMIT, NOREFERRALS, CACERTIFICATE,
            AUTHTYPE, TLS_VERIFY, TLS_VERSION, TLS_CA_FILE, SERVERPOOL_ROUNDS, SERVERPOOL_SKIP
        """
        success = False
        uidtype = param.get("UIDTYPE")
        timeout = float(param.get("TIMEOUT", 5))
        ldap_uri = param.get("LDAPURI")
        size_limit = int(param.get("SIZELIMIT", 500))
        serverpool_rounds = int(param.get("SERVERPOOL_ROUNDS") or SERVERPOOL_ROUNDS)
        serverpool_skip = int(param.get("SERVERPOOL_SKIP") or SERVERPOOL_SKIP)
        if is_true(param.get("TLS_VERIFY")) \
                and (ldap_uri.lower().startswith("ldaps") or
                                    param.get("START_TLS")):
            tls_version = int(param.get("TLS_VERSION") or ssl.PROTOCOL_TLSv1)
            tls_ca_file = param.get("TLS_CA_FILE") or DEFAULT_CA_FILE
            tls_context = Tls(validate=ssl.CERT_REQUIRED,
                              version=tls_version,
                              ca_certs_file=tls_ca_file)
        else:
            tls_context = None
        get_info = get_info_configuration(is_true(param.get("NOSCHEMAS")))
        try:
            server_pool = cls.get_serverpool(ldap_uri, timeout,
                                             tls_context=tls_context,
                                             get_info=get_info,
                                             rounds=serverpool_rounds,
                                             exhaust=serverpool_skip)
            l = cls.create_connection(authtype=param.get("AUTHTYPE",
                                                          AUTHTYPE.SIMPLE),
                                      server=server_pool,
                                      user=param.get("BINDDN"),
                                      password=param.get("BINDPW"),
                                      receive_timeout=timeout,
                                      auto_referrals=not param.get(
                                           "NOREFERRALS"),
                                      start_tls=param.get("START_TLS", False))
            #log.error("LDAP Server Pool States: %s" % server_pool.pool_states)
            if not l.bind():
                raise Exception("Wrong credentials")
            # create searchattributes
            attributes = list(yaml.safe_load(param["USERINFO"]).values())
            if uidtype.lower() != "dn":
                attributes.append(str(uidtype))
            # search for users...
            g = l.extend.standard.paged_search(
                search_base=param["LDAPBASE"],
                search_filter=u"(&" + param["LDAPSEARCHFILTER"] + ")",
                search_scope=param.get("SCOPE") or ldap3.SUBTREE,
                attributes=attributes,
                paged_size=100,
                size_limit=size_limit,
                generator=True)
            # returns a generator of dictionaries
            count = 0
            uidtype_count = 0
            for entry in ignore_sizelimit_exception(l, g):
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
                desc = _("Your LDAP config found {0!s} user objects, but only {1!s} "
                         "with the specified uidtype").format(count, uidtype_count)
            else:
                desc = _("Your LDAP config seems to be OK, {0!s} user objects "
                         "found.").format(count)

            l.unbind()
            success = True

        except Exception as e:
            desc = "{0!r}".format(e)
            log.debug("{0!s}".format(traceback.format_exc()))

        return success, desc

    def add_user(self, attributes=None):
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
            self.l.add(dn, self.object_classes, params)

        except Exception as e:
            log.error("Error accessing LDAP server: {0!r}".format(e))
            log.debug("{0}".format(traceback.format_exc()))
            raise privacyIDEAError(e)

        if self.l.result.get('result') != 0:
            log.error("Error during adding of user {0!r}: "
                      "{1!r}".format(dn, self.l.result.get('message')))
            raise privacyIDEAError(self.l.result.get('message'))

        return self.getUserId(attributes.get("username"))

    def delete_user(self, uid):
        """
        Delete a user from the LDAP Directory.

        The user is referenced by the user id.
        :param uid: The uid of the user object, that should be deleted.
        :type uid: basestring
        :return: Returns True in case of success
        :rtype: bool
        """
        res = True
        try:
            self._bind()

            self.l.delete(self._getDN(uid))
        except Exception as exx:
            log.error("Error deleting user: {0!r}".format(exx))
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
                    except TypeError as e:
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
            self.l.modify(self._getDN(uid), params)
        except Exception as e:
            log.error("Error accessing LDAP server: {0!r}".format(e))
            log.debug("{0!s}".format(traceback.format_exc()))
            return False

        if self.l.result.get('result') != 0:
            log.error("Error during update of user {0!r}: "
                      "{1!r}".format(uid, self.l.result.get("message")))
            return False

        return True

    @staticmethod
    def create_connection(authtype=None, server=None, user=None,
                          password=None, auto_bind=False,
                          client_strategy=ldap3.SYNC,
                          check_names=True,
                          auto_referrals=False,
                          receive_timeout=5,
                          start_tls=False):
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
            since receive_timeout is not supported by ldap3 < 2.
        :return:
        """

        authentication = None
        if not user:
            authentication = ldap3.ANONYMOUS

        if authtype == AUTHTYPE.SIMPLE:
            if not authentication:
                authentication = ldap3.SIMPLE
            # SIMPLE works with passwords as UTF8 and unicode
            l = ldap3.Connection(server, user=user,
                                 password=password,
                                 auto_bind=auto_bind,
                                 client_strategy=client_strategy,
                                 authentication=authentication,
                                 check_names=check_names,
                                 # receive_timeout=receive_timeout,
                                 auto_referrals=auto_referrals)
        elif authtype == AUTHTYPE.NTLM:  # pragma: no cover
            if not authentication:
                authentication = ldap3.NTLM
            # NTLM requires the password to be unicode
            l = ldap3.Connection(server,
                                 user=user,
                                 password=password,
                                 auto_bind=auto_bind,
                                 client_strategy=client_strategy,
                                 authentication=authentication,
                                 check_names=check_names,
                                 # receive_timeout=receive_timeout,
                                 auto_referrals=auto_referrals)
        elif authtype == AUTHTYPE.SASL_DIGEST_MD5:  # pragma: no cover
            if not authentication:
                authentication = ldap3.SASL
            password = to_utf8(password)
            sasl_credentials = (str(user), str(password))
            l = ldap3.Connection(server,
                                 sasl_mechanism="DIGEST-MD5",
                                 sasl_credentials=sasl_credentials,
                                 auto_bind=auto_bind,
                                 client_strategy=client_strategy,
                                 authentication=authentication,
                                 check_names=check_names,
                                 # receive_timeout=receive_timeout,
                                 auto_referrals=auto_referrals)
        else:
            raise Exception("Authtype {0!s} not supported".format(authtype))

        if start_tls:
            l.open(read_server_info=False)
            log.debug("Doing start_tls")
            r = l.start_tls(read_server_info=False)

        return l

    @property
    def editable(self):
        """
        Return true, if the instance of the resolver is configured editable
        :return:
        """
        # Depending on the database this might look different
        # Usually this is "1"
        return is_true(self._editable)
