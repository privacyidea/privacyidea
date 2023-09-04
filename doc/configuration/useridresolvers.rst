.. _useridresolvers:

UserIdResolvers
---------------

.. index:: useridresolvers, LDAP, Active Directory

Each organisation or company usually has its users managed at a central location.
This is why privacyIDEA does not provide its own user management but rather
connects to existing user stores.

UserIdResolvers are connectors to those user stores, the locations,
where the users are managed. Nowadays this can be LDAP directories or
especially Active Directory, some times FreeIPA or the Redhat 389 service.
But classically users are also located in files like /etc/passwd on
standalone unix systems. Web services often use SQL databases as
user store.

Today with many more online cloud services SCIM is also an uprising
protocol to access userstores.

privacyIDEA already comes with UserIdResolvers to talk to all these
user stores:

 * :ref:`flatfile_resolver`
 * :ref:`ldap_resolver`
 * :ref:`sql_resolver`
 * :ref:`scim_resolver`
 * :ref:`http_resolver`

.. note:: New resolver types (python modules) can be added easily. See the
   module section for this
   (:ref:`code_useridresolvers`).

You can create as many UserIdResolvers as you wish and edit existing resolvers.
When you have added all configuration data, most UIs of the UserIdResolvers have a
button "Test resolver", so that you can test your configuration before saving
it.

Starting with privacyIDEA 2.4 resolvers can be editable, i.e. you can edit
the users in the user store. Read more about this at :ref:`manage_users`.

.. note:: Using the authentication policy ``otppin=userstore`` users can
   authenticate with the password
   from their user store, being the LDAP password, SQL password or password
   from flat file.

.. _flatfile_resolver:

Flatfile resolver
.................

.. index:: flatfile resolver

Flatfile resolvers read files like ``/etc/passwd``.

.. note:: The file ``/etc/passwd`` does not contain the unix password.
   Thus, if you create a flatfile resolver from this file the functionality
   with ``otppin=userstore`` is not available. You can create a flatfile with
   passwords using the tool ``privacyidea-create-pwidresolver-user`` which is
   usually found in ``/opt/privacyidea/bin/``.

Create a flat file like this::

   privacyidea-create-pwidresolver-user -u user2 -i 1002 >> /your/flat/file


.. _ldap_resolver:

LDAP resolver
.............

.. index:: LDAP resolver, OpenLDAP, Active Directory, FreeIPA, Penrose,
   Novell eDirectory, SAML attributes, Kerberos

The LDAP resolver can be used to access any kind of LDAP service like
OpenLDAP, Active Directory, FreeIPA, Penrose, Novell eDirectory.

.. figure:: images/ldap-resolver.png
   :width: 500

   *LDAP resolver configuration*

Server settings
~~~~~~~~~~~~~~~
The ``Server URI`` can contain a comma separated list of servers.
The servers are used to create a server pool and are used with a round robin
strategy [#serverpool]_.

**Example**::

   ldap://server1, ldaps://server2:1636, server3, ldaps://server4

This will create LDAP requests to

 * server1 on port 389
 * server2 on port 1636 using SSL
 * server3 on port 389
 * server4 on port 636 using SSL.

TLS Version
"""""""""""

When using TLS, you may specify the TLS version to use. Starting from version 3.6, privacyIDEA offers
TLS v1.3 by default.


TLS certificates
""""""""""""""""

When using TLS with LDAP, you can tell privacyIDEA to verify the certificate. The according
checkbox is visible in the WebUI if the target URL starts with *ldaps* or when using STARTTLS.

You can specify a file with the trusted CA certificate, that signed the
TLS certificate. The default CA filename is */etc/privacyidea/ldap-ca.crt*
and can contain a list of base64 encoded CA certificates.
PrivacyIDEA will use the CA file if specified. If you leave the field empty
it will also try the system certificate store (*/etc/ssl/certs/ca-certificates.crt*
or */etc/ssl/certs/ca-bundle.crt*).

Binding
"""""""

The ``Bind Type`` for querying the LDAP-Server can be ``Anonymous``, ``Simple``,
``NTLM``, ``SASL Digest-MD5`` (Deprecated) or ``SASL Kerberos``.

.. note:: When using bind type ``Simple`` you can specify the Bind-DN like
   ``cn=administrator,cn=users,dc=domain,dc=name`` or ``administrator@domain.name``.
   When using bind type ``NTLM`` you need to specify Bind-DN like
   ``DOMAINNAME\\username``. In case of ``SASL Kerberos`` the Bind-DN needs to
   be the *PrincipalName* corresponding to the given *keytab*-file.

For the ``SASL Kerberos`` bind type, the privacyIDEA server needs to be
integrated into the AD Domain. A basic setup and more information on the Kerberos
authentication can be found in the corresponding
`GitHub Wiki <https://github.com/privacyidea/privacyidea/wiki/concept:-LDAP-resolver-with-Kerberos-auth>`_.

Caching
"""""""

The ``Cache Timeout`` configures a short living per process cache for LDAP users.
The cache is not shared between different Python processes, if you are running more processes
in Apache or Nginx. You can set this to ``0`` to deactivate this cache.

Server Pools
""""""""""""

The ``Server pool retry rounds`` and ``Server pool skip timeout`` settings configure the behavior of
the LDAP server pool. When establishing a LDAP connection, the resolver uses a round-robin
strategy to select a LDAP server from the pool. If the current server is not reachable, it is removed
from the pool and will be re-inserted after the number of seconds specified in the *skip timeout*.
If the pool is empty after a round, a timeout is added before the next round is started.
The ldap3 module defaults system wide to 10 seconds before starting the next round.
This timeout can be changed by setting ``PI_LDAP_POOLING_LOOP_TIMEOUT`` to an
integer in seconds in the :ref:`cfgfile`.
If no reachable server could be found after the number of rounds specified in the *retry rounds*,
the request fails.

By default, knowledge about unavailable pool servers is not persisted between requests.
Consequently, a new request may retry to reach unavailable servers, even though the *skip timeout*
has not passed yet. If the *Per-process server pool* is enabled, knowledge about unavailable
servers is persisted within each process. This setting may improve performance in situations in
which a LDAP server from the pool is down for extended periods of time.

Modifying users
"""""""""""""""

Starting with privacyIDEA 2.12, you can define the LDAP resolver as editable.
I.e. you can create and modify users from within privacyIDEA.

There are two additional configuration parameters for this case.

``DN Template`` defines how the DN of the new LDAP object should be created. You can use *username*, *surname*,
*givenname* and *basedn* to create the distinguished name.

**Examples**::

   CN=<givenname> <surname>,<basedn>

   CN=<username>,OU=external users,<basedn>

   uid=<username>,ou=users,o=example,c=com

``Object Classes`` defines which object classes the user should be assigned to. This is a comma separated list.
The usual object classes for Active Directory are::

   top, person, organizationalPerson, user, inetOrgPerson

Resolver settings
~~~~~~~~~~~~~~~~~
The ``LoginName attribute`` is the attribute that holds the login name. It
can be changed to your needs.

Starting with version 2.20 you can provide a list of attributes in
``LoginName Attribute`` like::

    sAMAccountName, userPrincipalName

This way a user can login with either his ``sAMAccountName`` or his ``principalName``.

The ``searchfilter`` is used to list all possible users, that can be used
in this resolver. The search filter is used for forward and backward
search the object in LDAP.

The ``attribute mapping`` maps LDAP object attributes to user attributes in
privacyIDEA. privacyIDEA knows the following attributes:

 * ``phone``,
 * ``mobile``,
 * ``email``,
 * ``surname``,
 * ``givenname``,
 * ``password``
 * ``accountExpires``.

The above attributes are used for privacyIDEA's normal functionality and are
listed in the :ref:`user_details`. However, with a SAML authentication request,
the user attributes can be returned. (see :ref:`return_saml_attributes`). To return
arbitrary attributes from the LDAP You can add additional keys to the
attribute mapping with a key, you make up and the LDAP attribute like::

   "homedir": "homeDirectory",
   "studentID": "objectGUID"

``"homeDirectory"`` and ``"objectGUID"`` being the attributes in the LDAP directory
and ``"homedir"`` and ``"studentID"`` the keys returned in a SAML authentication
request.

The ``MULTIVALUEATTRIBUTES`` config value can be used to specify a list of
user attributes, that should return a list of values. Imagine you have a user mapping like
``{ "phone" : "telephoneNumber", "email" : "mail", "surname" : "sn", "group": "memberOf"}``.
Then you could specify ``["email", "group"]`` as the multi value attribute and the user object
would return the emails and the group memberships of the user from the LDAP server as a list.

.. note:: If the ``MULTIVALUEATTRIBUTES`` is left blank the default setting is "mobile". I.e. the
   mobile number will be returned as a list.

The ``MULTIVALUEATTRIBUTES`` can be well used with the ``samlcheck`` endpoint (see :ref:`rest_validate`)
or with the policy
:ref:`policy_add_user_in_response`.


The ``UID Type`` is the unique identifier for the LDAP object. If it is left
blank, the distinguished name will be used. In case of OpenLDAP this can be
*entryUUID* and in case of Active Directory *objectGUID*. For FreeIPA you
can use *ipaUniqueID*.

.. note:: The attributes *entryUUID*, *objectGUID*, and *ipaUniqueID*
   are case sensitive!

In case of Active Directory connections you might need to check the box
``No anonymous referral chasing``. The underlying LDAP library is only
able to do anonymous referral chasing. Active Directory will produce an
error in this case [#adreferrals]_.

The option ``No retrieval of schema information`` can be used to
disable the retrieval of schema information [#ldapschema]_ in
order to improve performance. This checkbox is deactivated by default
and should only be activated after having ensured that schema information
are unnecessary.

Expired Users
~~~~~~~~~~~~~

.. index:: Expired Users

You may set::

    "accountExpires": "accountExpires"

in the attribute mapping for Microsoft Active Directories. You can then call
the user listing API with the parameter ``accountExpires=1`` and you will only
see expired accounts.

This functionality is used with the script *privacyidea-expired-users*.

.. _sql_resolver:

SQL resolver
............

.. index:: SQL resolver, MySQL, PostgreSQL, Oracle, DB2, sqlite

The SQL resolver can be used to retrieve users from any kind of
SQL database like MySQL, PostgreSQL, Oracle, DB2 or sqlite.

.. figure:: images/sql-resolver.png
   :width: 500

   *SQL resolver configuration*

In the upper frame you need to configure the SQL connection.
The SQL resolver uses `SQLAlchemy <http://sqlalchemy.org>`_ internally.
In the field ``Driver`` you need to set a driver name as defined by the
`SQLAlchemy  dialects <http://docs.sqlalchemy.org/en/rel_0_9/dialects/>`_
like "mysql" or "postgres".

In the ``SQL attributes`` frame you can specify how the users are
identified.

The ``Database table`` contains the users.

.. note:: At the moment, only one table
   is supported, i.e. if some of the user data like email address or telephone
   number is located in a second table, those data can not be retrieved.

The ``Limit`` is the SQL limit for a userlist request. This can be important
if you have several thousand user entries in the table.

The ``Attribute mapping`` defines which table column should be mapped to
which privacyIDEA attribute. The known attributes are:

 * userid *(mandatory)*,
 * username *(mandatory)*,
 * phone,
 * mobile,
 * email,
 * givenname,
 * surname,
 * password.

The ``password`` attribute is the database column that contains the user
password. This is used, if you are doing user authentication against the SQL
database.

.. note:: There is no standard way to store passwords in an SQL database.
   privacyIDEA supports the most
   common ways like Wordpress hashes starting with *$P* or *$S*. Secure hashes
   starting with *{SHA}* or salted secure hashes starting with *{SSHA}*,
   *{SSHA256}* or *{SSHA512}*. Password hashes of length 64 are interpreted as
   OTRS sha256 hashes.

You can mark the users as ``Editable``. The ``Password_Hash_Type`` can be
used to determine which hash algorithm should be used, if a password of an
editable user is written to the database.

You can add an additional ``Where statement`` if you do not want to use
all users from the table.

The ``poolSize`` and ``poolTimeout`` determine the pooling behaviour. The
``poolSize`` (default 5) determine how many connections are kept open in the
pool. The ``poolTimeout`` (default 10) specifies how long the application
waits to get a connection from the pool.

.. note:: The pooling parameters only have an effect if the ``PI_ENGINE_REGISTRY_CLASS``
   config option is set to ``"shared"`` (see :ref:`engine-registry`).
   If you then have several SQL resolvers with the same connection and pooling settings,
   they will use the same shared connection pool.
   If you change the connection settings of an existing connection, the connection pool
   for the old connection settings will persist until the respective connections
   are closed by the SQL server or the web server is restarted.

.. note:: The ``Additional connection parameters``
   refer to the SQLAlchemy connection but are not used at the moment.

.. _scim_resolver:

SCIM resolver
.............

.. index:: SCIM resolver

SCIM is a "System for Cross-domain Identity Management". SCIM is a REST-based
protocol that can be used to ease identity management in the cloud.

The SCIM resolver is tested in basic functions with OSIAM [#osiam]_,
the "Open Source Identity & Access Management".

To connect to a SCIM service you need to provide a URL to an authentication
server and a URL to the resource server. The authentication server is used to
authenticate the privacyIDEA server. The authentication is based on a ``Client``
name and the ``Secret`` for this client.

.. figure:: images/scim-resolver.png
   :width: 500

User information is then retrieved from the resource server.

The available attributes for the ``Attribute mapping`` are:

 * username *(mandatory)*,
 * givenname,
 * surname,
 * phone,
 * mobile,
 * email.

.. _http_resolver:

HTTP resolver
.............

.. index:: HTTP resolver, resolver, api, http

Starting with version 3.4 the HTTP resolver is available to retrieve user information from any kind
of web service API. privacyIDEA issues a request to the target service and expects a JSON object in return.
The configuration of the HTTP resolver sets the details of the request in the ``Request Mapping`` as well as the
mapping of the obtained information as a ``Response Mapping``.

.. figure:: images/http_resolver.png
   :width: 500

The ``Request Mapping`` is used to build the request issued to the remote API from privacyIDEA's user information.
For example an endpoint definition::

   POST /get-user
   customerId=<user_id>&accessKey="secr3t!"

will require a request mapping

.. code-block:: json

   { "customerId": "{userid}", "accessKey": "secr3t!" }

The ``Response Mapping`` follows the same rules as the attribute mapping of the SQL resolver. The known attributes are

 * username *(mandatory)*,
 * givenname,
 * surname,
 * phone,
 * mobile,
 * email.

Nested attributes are also supported using `pydash deep path <https://pydash.readthedocs.io/en/latest/deeppath.html>`_
for parsing, e.g.

.. code-block:: json

   { "username": "{Username}", "email": "{Email}", "phone": "{Phone_Numbers.Phone}" }

For APIs which return ``200 OK`` also for a negative response, ``Special error handling`` can be activated to treat
the request as unsuccessful if the response contains certain content.

The above configuration image will throw an error for a response

.. code-block:: json

   { "success": false, "message": "There was an error!" }

because privacyIDEA will match ``{ "success": false }``.

.. note:: If the HTTP response status is >= 400, the resolver will throw an exception.

.. _usercache:

User Cache
..........

.. index:: user cache, caching

privacyIDEA does not implement local user management by design and relies on UserIdResolvers to
connect to external user stores instead. Consequently, privacyIDEA queries user stores quite frequently,
e.g. to resolve a login name to a user ID while processing an authentication request, which
may introduce a significant slowdown.
In order to optimize the response time of authentication requests, privacyIDEA 2.19 introduces the *user cache*
which is located in the local database. It can be enabled in the system configuration (see :ref:`user_cache_timeout`).

A user cache entry stores the association of a login name in a specific UserIdResolver with a specific
user ID for a predefined time called the *expiration timeout*, e.g. for one week.
The processing of further authentication requests by the same user during this timespan
does not require any queries to the user store, but only to the user cache.

The user cache should only be enabled if the association of users and user ID is not expected to change often:
In case a user is deleted from the user store, but can still be found in the user cache and still has assigned
tokens, the user will still be able to authenticate during the expiration timeout! Likewise, any changes to the
user ID will not be noticed by privacyIDEA until the corresponding cache entry expires.

Expired cache entries are *not* deleted from the user cache table automatically. Instead, the tool
``privacyidea-usercache-cleanup`` should be used to delete expired cache entries from the database,
e.g. in a cronjob.

However, cache entries are removed at some defined events:

* If a UserIdResolver is modified or deleted, all cache entries belonging to this resolver are deleted.
* If a user is modified or deleted in an editable UserIdResolver, all cache entries belonging to this user
  are deleted.

.. note:: Realms with multiple UserIdResolvers are a special case: If a user ``userX`` tries to authenticate in a
   realm with two UserIdResolvers ``resolverA`` (with highest priority) and ``resolverB``, the user cache is queried
   to find the user ID of ``userX`` in the UserIdResolver ``resolverA``. If the cache contains no matching entry,
   ``resolverA`` itself is queried for a matching user ID! Only if ``resolverA`` does not find a corresponding
   user, the user cache is queried to determine the user ID of ``userX`` in ``resolverB``. If no matching entry
   can be found, ``resolverB`` is queried.

.. rubric:: Footnotes

.. [#serverpool] https://ldap3.readthedocs.io/en/latest/server.html#server-pool
.. [#adreferrals] https://techcommunity.microsoft.com/t5/azure-active-directory-identity/referral-chasing/ba-p/243177
.. [#osiam] http://osiam.github.io
.. [#ldapschema] https://ldap3.readthedocs.io/en/latest/schema.html
