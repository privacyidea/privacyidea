# -*- coding: utf-8 -*-
"""
This callback file contains code scripts that are called if they exist to
provide additional processing over and above the standard functionality
provided by privacyidea.

This enables a easy route for customisation of functionality.
"""

def before_LDAP_Add(uid, object_class, attributes):
    """
    Example callback where modification of the LDAP objectClases and/or
    LDAP attributes can be maniplulated prior to being added to the LDAP
    directory.

    :param uid: The uid of the user object in the resolver
    :type uid: string
    :param object_class: Attributes according to the attribute mapping
    :type object_class: list
    :param attributes: Attributes according to the attribute mapping
    :type attributes: dict
    :return: uid, object_class, attributes
    """

    # Example usage:
    # Adding posixAccount data to the LDAP add

    #object_class.append("posixAccount")
    #attributes["uidNumber"] = 1005
    #attributes["gidNumber"] = 1005
    #attributes["homeDirectory"] = "/home/%s" % attributes.get("cn")

    return uid, object_class, attributes

