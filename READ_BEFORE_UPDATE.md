# Update Notes

## Update from 2.21 to 2.22

* Some combinations of installed packages may cause problems with the LDAP resolver:
  * ldap3 2.1.1, pyasn1 0.4.2: Attempts to use STARTTLS fail with an exception (Issue #885)
  * ldap3 >= 2.3: The user list appears to be empty, the log shows LDAPSizeLimitExceededResult exceptions. (Issue #887)
                  This can be mitigated by setting a size limit greater than the number of users in the LDAP directory.
  * ldap3 >= 2.4: User attributes are not retrieved properly (Issue #911)
  * ldap3 >= 2.4.1: UnicodeError on authentication, token view displays resolver errors (Issue #911)
  * ldap3 >= 2.4.1: Cannot search for non-ASCII characters in user view (#980)
* Depending on your requirements, you may consider using ldap3 2.1.1 and pyasn1 0.1.9.
  While this combination does not exhibit any of the problems listed above, both software
  releases are quite old and several security fixes have been incorporated since then!
* By default, Ubuntu installations will have ldap3 2.1.1 and pyasn1 0.1.9 installed,
  whereas pip/virtualenv installations will have ldap3 2.1.1 and pyasn1 0.4.2.
* The size of the ``serial`` column in the ``pidea_audit`` database table was increased from 20 to 40 characters.
  Please verify that your database can handle this increasing of the table size!
