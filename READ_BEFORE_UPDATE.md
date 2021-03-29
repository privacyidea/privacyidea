# Update Notes

## Update from 3.5 to 3.6

* The default TLS_VERSION for LDAP resolvers has been changed from 1.0 to 1.3.
  Existing resolvers should not be changed. However, if an LDAP resolver has not
  TLS_VERSION configured, up to 3.5 TLS version 1.0 was used.
  A migration script will take care, that resolvers without a configured TLS_VERSION
  will have TLS_VERSION 1.0 configured to keep the existing behaviour.

Be sure to run the schema update script!

## Update from 3.4 to 3.5

* The audit log table now also records the start date and the duration
  of a request.

* The authcache database table gets a longer column "authentication" 
  to cope with the longer Argon2 hashes.

Be sure to run the schema update script.
The current database schema now is d5870fd2f2a4.

## Update from 3.3 to 3.4

* Policies can now contain the privacyIDEA node as condition.

  Be sure to run the schema updates in you pip installation.
  Ubuntu or CentOS installations will run the schema update automatically.

* The SMS Gateway database tables have been enhanced with an additional
  constraint on the type of the options.

  The data in the column "Type" of the database table "smsgatewayoption"
  will be migrated by the schema update script.
  If you are using SMS Gateways, check your gateway configurtion
  after the update.

## Update from 3.2 to 3.3

* Admin policies now do have a destinct admin username field.

  The normal username field will not be used for the admin user
  anymore but can be used for normal users.
  The SQL migration script migrates existing admin policies by moving
  the usernames of administrators to the new username field.

* PostgreSQL database adapter removed from default installation

  When installing privacyIDEA from github or via Pypi, the ``psycopg2`` package
  won't be installed anymore. Instead one can use
  ``pip install privacyIDEA[postgres]`` to also install the required packages.

* Internal signature of the tokenclass method

  ``get_default_settings`` changed.
  If you added your own tokenclass, please assure to update
  your function signature.

* Output of Logger Audit changed

  The log-message of the Logger Audit is now converted to a JSON-encoded string
  sorted by keywords. This could potentially mess up subsequent reporting
  configurations.

* Update of some HTML templates due to update of UI components

  Several HTML templates have changed and might render custom templates unusable.
  Please check your custom templates and compare to these changes:
   - File upload component changed
   - Switch ``pattern`` to ``ng-pattern`` to avoid error message in console
   - Accordion component changed
   - Pagination component changed
   - Tooltip component changed

## Update from 3.1 to 3.2

* Change to Python 3

  The built Ubuntu und CentOS packages are now built with Python 3.
  The virtual environments thus have changed.
  If you have any changes like customizations under
  /opt/privacyidea/lib/python2.7/ these will not be found anymore
  and the WebUI could result in not being accessable.
  This could be relevant when using ``PI_CUSTOM_CSS = True``
  or ``PI_CUSTOMIZATION`` in your pi.cfg file.

  You will have to move the corresponding files to
  /opt/privacyidea/lib/python3.x/...

* MySQL-python obsolete

  With the change to Python 3 the MySQL DB driver has become
  obsolete since it is not supported under Python 3 anymore.
  If your current DB URI starts with "mysql://", the
  update script will automatically change this to
  "mysql+pymysql://" to assure further operation under Python 3.

* REST API

  The endpoints "GET /event" has been changed to "GET /event/"
  since it returns a list of events.
  The endpoints "GET /smsgateway" has been changed to
  "GET /smsgateway/"  since it returns a list of events.

## Update from 3.0 to 3.1

* Policies

  In the scope admin a new action "tokenlist" was added. This
  action assures, that admins can only list tokens in certain realms.
  Without this action, and administrator can not view any tokens.
  To allow all administrators to still list tokens, during migration
  from 3.0 to 3.1 a new policy **pi-update-policy-b9131d0686eb** is
  automatically created.

  After the update you might want to review this policy and the
  token list rights of your administrators.

  **Note**, that due to the naming of this auto-generated policy, it is
  not possible to modify this policy. You can still disable and enable
  or delete this policy.

## Update from 2.23 to 3.0

* Database

  **WARNING**: Be sure to run a backup of your database before upgrading!
  The database schema in regards to the token assignment is changed.
  The token assignment is moved from the table "token" to the table
  "tokenowner". The user columns in the "token" table are deleted and
  migrated to the "tokenowner" table.   

* The packaging for ubuntu has changed. While privacyIDEA 2.23 was
  installed into the system environment, the ubuntu packages
  starting with privacyIDEA 3.0 will install the software in the
  Python virtual environment at /opt/privacyidea.
  However, the debian package update process will take care of this.

  But this also means that the apache configuration was changed slightly.
  In /etc/apache2/sites-available/privacyidea.conf a line
  "WSGIPythonHome /opt/privacyidea"
  was added.
  Unless you modified the file privacyidea.conf, the update process
  will take care of this automatically.

* Package dependencies:

  A lot of changes will be introduced in privacyIDEA 3.0, most notably the
  Python 3 compatibility.

  * Removed packages:
    * matplotlib
    * pandas
    * PyCrypto
  * Added packages:
    * cryptography (2.4.2)
  * Updated packages:
    * smpplib (0.1 -> 2.0)
    * pytest (3.6.0 -> 3.6.1)
    * requests (2.18.4 -> 2.20.0)
    * PyYAML (3.12 -> 5.1)

* Due to the switch from PyCrypto to cryptography, the calculation of signatures
  changed. In order to be able to verify old audit entry signatures,
   PI_CHECK_OLD_SIGNATURES must be set to "True" in your pi.cfg.

## Update from 2.22 to 2.23

* An additional dependency python-croniter was added.
  Thus you need to run "apt dist-upgrade" on Ubuntu systems,
  to also install this new dependency.

* When upgrading on Ubuntu using apt, you will be notified, that pi.cfg was changed by the maintainer.
  This is fine. You must keep your pi.cfg, so press "N"!
  This is due to the PI_ENGINE_REGISTRY_CLASS which is set to "shared" on new installations.
  If you want to, you can set PI_ENGINE_REGISTRY_CLASS = "shared"
  in your pi.cfg manually.

* The database schema was changed. The meta packages on Ubuntu
  privacyidea-apache2 and privacyidea-nginx should take care of this.
  The last version of the DB schema will be 1a0710df148b

## Update from 2.21 to 2.22

* There are currently version conflicts with the packages of ldap3 and pyasn1 that
  privacyIDEA depends on.

  **Our recommendations**:
  * Use either **ldap3 2.1.1** and **pyasn1 0.1.9**
    or **ldap3 2.1.1** and **pyasn1 0.4.2**.
    * The Ubuntu installation comes with ldap3 2.1.1 and pyasn1 0.1.9.
    * Virtualenv installation comes with ldap3 2.1.1 and pyasn1 0.4.2.
      With ldap3 2.1.1 and pyasn1 0.4.2, StartTLS will not work! LDAPS will work.
  * We added pull requests to ldap3 and also added workarounds in privacyIDEA 2.22. With the next
    release of ldap3 all version conflicts should be solved.
  * Here are some of the issues resulting from the version conflicts:
    * ldap3 2.1.1, pyasn1 0.4.2: Attempts to use STARTTLS fail with an exception (Issue #885)
    * ldap3 >= 2.4: User attributes are not retrieved properly (Issue #911)
    * ldap3 == 2.4.1: UnicodeError on authentication, token view displays resolver errors (Issue #911)
    * ldap3 == 2.4.1: Cannot search for non-ASCII characters in user view (#980)
* The size of the ``serial`` column in the ``pidea_audit`` database table was increased from 20 to 40 characters.
  Please verify that your database can handle this increasing of the table size!
