# Update Notes

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
