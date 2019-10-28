# Update Notes

## Update from 3.1 to 3.2

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
