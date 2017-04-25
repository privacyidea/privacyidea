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

 * Flatfile resolver,
 * LDAP resolver,
 * SQL resolver,
 * SCIM resolver.

.. note:: New resolver types (python modules) can be added easily. See the
   module section for this
   (:ref:`code_useridresolvers`).

You can create as many UserIdResolvers as you wish and edit existing resolvers.
When you have added all configuration data, most UIs of the UserIdResolvers have a
button "Test resolver", so that you can test your configuration before saving
it.

Starting with privacyIDEA 2.4 resolvers can be editable, i.e. you can edit
the users in the user store. Read more about this at :ref:`manage_users`.

.. note:: Using the policy ``authentication:otppin=userstore`` users can
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
   passwords using the tool ``privacyidea-create-pwidresolver-user``.

Create a flat file like this::
   
   privacyidea-create-pwidresolver-user -u user2 -i 1002 >> /your/flat/file


.. _ldap_resolver:

LDAP resolver
.............

.. index:: LDAP resolver, OpenLDAP, Active Directory, FreeIPA, Penrose,
   Novell eDirectory, SAML attributes

The LDAP resolver can be used to access any kind of LDAP service like
OpenLDAP, Active Directory,
FreeIPA, Penrose, Novell eDirectory.

.. figure:: images/ldap-resolver.png
   :width: 500

   *LDAP resolver configuration*

In case of Active Directory connections you might need to check the box
``No anonymous referral chasing``. The underlying LDAP library is only
able to do anonymous referral chasing. Active Directory will produce an
error in this case [#adreferrals]_.

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

The ``Bind Type`` with Active Directory can either be chosen as "Simple" or
as "NTLM".

.. note:: When using bind type "Simple" you need to specify the Bind DN like
   *cn=administrator,cn=users,dc=domain,dc=name*. When using bind type "NTLM"
   you need to specify Bind DN like *DOMAINNAME\\username*.

The ``LoginName`` attribute is the attribute that holds the loginname. It
can be changed to your needs.

The searchfilter is used for forward and backward
search the object in LDAP.

The ``searchfilter`` is used to list all possible users, that can be used
in this resolver.

The ``attribute mapping`` maps LDAP object attributes to user attributes in
privacyIDEA. privacyIDEA knows the following attributes:

 * phone,
 * mobile,
 * email,
 * surname,
 * givenname,
 * password
 * accountExpires.

The above attributes are used for privacyIDEA's normal functionality and are
listed in the userview. However, with a SAML authentication request user
attributes can be returned. (see :ref:`return_saml_attributes`). To return
arbitrary attributes from the LDAP you can add additional keys to the
attribute mapping with a key, you make up and the LDAP attribute like:

   "homedir": "homeDirectory",
   "studentID": "objectGUID"

"homeDirectory" and "objectGUID" being the attributes in the LDAP directory
and "homedir" and "studentID" the keys returned in a SAML authentication
request.
  
The ``UID Type`` is the unique identifier for the LDAP object. If it is left
blank, the distinguished name will be used. In case of OpenLDAP this can be
*entryUUID* and in case of Active Directory *objectGUID*. For FreeIPA you
can use *ipaUniqueID*.

.. note:: The attributes *entryUUID*, *objectGUID*, and *ipaUniqueID*
are case sensitive!

The option ``No retrieval of schema information`` can be used to
disable the retrieval of schema information [#ldapschema]_ in
order to improve performance. This checkbox is deactivated by default
and should only be activated after having ensured that schema information
are unnecessary.

TLS certificates
~~~~~~~~~~~~~~~~

Starting with privacyIDEA 2.18 in case of encrypted LDAPS
connections privacyIDEA can verify  the TLS
certificate. (Python >= 2.7.9 required)
To have privacyIDEA verify the TLS certificate you need to check the
according checkbox.

You can specify a file with the trusted CA certificate, that signed the
TLS certificate. The default CA filename is */etc/privacyidea/ldap-ca.crt*
and can contain a list of base64 encoded CA certificates.
PrivacyIDEA will use the CA file if specifed. If you leave the field empty
it will also try the system certificate store (*/etc/ssl/certs/ca-certificates.crt*
or */etc/ssl/certs/ca-bundle.crt*).

Modifying users
~~~~~~~~~~~~~~~

Starting with privacyIDEA 2.12 you can define the LDAP resolver as editable.
I.e. you can create and modify users from within privacyIDEA.

There are two additional configuration parameters for this case.

``DN Template`` defines how the DN of the new LDAP object should be created. You can use *username*, *surname*,
*givenname* and *basedn* to create the distiguished name.

**Examples**:

   CN=<givenname> <surname>,<basedn>

   CN=<username>,OU=external users,<basedn>

   uid=<username>,ou=users,o=example,c=com

``Object Classes`` defines which object classes the user should be assigned to. This is a comma separated list.
The usual object classes for Active Directory are

   top, person, organizationalPerson, user, inetOrgPerson

Expired Users
~~~~~~~~~~~~~

.. index:: Expired Users

You may set

    "accountExpires": "accountExpires"

in the attribute mapping for Microsoft Active Directories. You can then call
the user listing API with the parameter *accountExpires=1* and you will only
see expired accounts.

This functionality is used with the script *privacyidea-expired-users*.

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

.. note:: At the moment only one table 
   is supported, i.e. if some of the user data like email address or telephone
   number is located in a second table, those data can not be retrieved.
  
The ``Limit`` is the SQL limit for a userlist request. This can be important
if you have several thousand user entries in the table.

The ``Attribute mapping`` defines which table column should be mapped to
which privayIDEA attribute. The known attributes are:

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
   There are several different ways to do this. privacyIDEA supports the most
   common ways like Wordpress hashes starting with *$P* or *$S*. Secure hashes
   starting with *{SHA}* or salted secure hashes starting with *{SSHA}*,
   *{SSHA256}* or *{SSHA512}*. Password hashes of length 64 are interpreted as
   OTRS sha256 hashes.

You can add an additional ``Where statement`` if you do not want to use
all users from the table.

The ``poolSize`` and ``poolTimeout`` determine the pooling behaviour. The
``poolSize`` (default 5) determine how many connections are kept open in the
pool. The ``poolTimeout`` (default 10) specifies how long the application
waits to get a connection from the pool.

.. note:: The ``Additional connection parameters``
   refer to the SQLAlchemy connection but are not used at the moment.

SCIM resolver
.............

.. index:: SCIM resolver

SCIM is a "System for Cross-domain Identity Management". SCIM is a REST-based 
protocol that can be used to ease identity management in the cloud.

The SCIM resolver is tested in basic functions with OSIAM [#osiam]_,
the "Open Source Idenitty & Access Management".

To connect to a SCIM service you need to provide a URL to an authentication 
server and a URL to the resource server. The authentication server is used to
authenticate the privacyIDEA server. The authentication is based on a ``client``
name and the ``Secret`` for this client.

Userinformation is then retrieved from the resource server.

The available attributes for the ``Attribute mapping`` are:

 * username *(mandatory)*,
 * givenname,
 * surname,
 * phone,
 * mobile,
 * email.

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

.. [#adreferrals] http://blogs.technet.com/b/ad/archive/2009/07/06/referral-chasing.aspx
.. [#osiam] http://www.osiam.org
.. [#serverpool] https://github.com/cannatag/ldap3/blob/master/docs/manual/source/servers.rst#server-pool
.. [#ldapschema] http://ldap3.readthedocs.io/schema.html