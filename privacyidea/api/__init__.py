"""
This is the REST API for privacyidea. It lets you create the system
configuration, which is denoted in the system endpoints.

Special system configuration is the configuration of

 * the resolvers
 * the realms
 * the defaultrealm
 * the policies.

Resolvers are dynamic links to existing user sources. You can find users in
LDAP directories, SQL databases, flat files or SCIM services.
A resolver translates a loginname to a user object in the user source and
back again. It is also responsible for fetching all additional needed
information from the user source.

Realms are collections of resolvers that can be managed by administrators and
where policies can be applied.

Defaultrealm is a special endpoint to define the default realm. The default
realm is used if no user realm is specified. If a user from realm1 tries to
authenticate or is addressed, the notation user@realm1 is used.
If the @realm1 is ommitted, the user is searched in the default realm.

Policies are rules how privacyidea behaves and which user and administrator
is allowed to do what.

"""

