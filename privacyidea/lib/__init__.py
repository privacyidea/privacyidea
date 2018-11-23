"""
Based on the database models, which are tested in tests/test_db_model.py,
there are different modules.

resolver.py contains functions to simply deal with resolver definitions.
On this level users and realms are not know, yet.

realm.py contains functions to deal with realm. Realms are a list of several
resolvers. So prior to bother the realm.py, the resolver.py should be
understood and working.
On this level, users are not known, yet.

user.py contains functions to deal with users. A user object is an entity
in a realm. And of course the user object itself can be found in a resolver.
But you need to have working resolver.py and realm.py to be able to
work with user.py
"""

from privacyidea.lib.framework import _

__all__ = ['_']
