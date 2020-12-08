.. _policy_conditions:

Policy conditions
-----------------

Since privacyIDEA 3.1, *policy conditions* allow to define more advanced rules
for policy matching, i.e. for determining which policies are valid for a
specific request.

Conditions can be added to a policy via the WebUI. In order for a policy to
take effect during the processing of a request, the request has to match not
only the ordinary policy attributes (see :ref:`policies`), but also *all*
additionally defined conditions that are currently active. If no active
conditions are defined, only the ordinary policy attributes are taken into
account.

Each policy condition performs a comparison of two values. The left value is
taken from the current request. The comparison operator (called *Comparator*)
and the right value are entered in the policy definition. Each condition
consists of five parts:

 * ``Active`` determines if the condition is currently active.
 * ``Section`` refers to an aspect of the incoming request on which the condition is applied.
   The available sections are predefined, see `Sections`_.
 * The meaning of ``Key`` depends on the chosen ``Section``. Typically, it determines the exact property
   of the incoming request on which the condition is applied.
 * ``Comparator`` defines the comparison to be performed. The available comparators are predefined, see `Comparators`_.
 * ``Value`` determines the value the property should be compared against.

Sections
~~~~~~~~

privacyIDEA 3.1 implements only one section, which is called ``userinfo``.
The class ``tokeninfo`` is first supported with privacyIDEA 3.5.

``userinfo``
^^^^^^^^^^^^

The section ``userinfo`` can be used to define conditions that are checked against attributes of the
current user in the request (the so-called *handled user*).
The validity of a policy condition with section ``userinfo`` is determined as follows:

* privacyIDEA retrieves the userinfo of the currently handled user. These are the user attributes as they are
  determined by the respective resolver. This is configured via the attribute mappings of resolvers
  (see :ref:`useridresolvers`).
* Then, it retrieves the userinfo attribute given by ``Key``
* Finally, it uses the ``Comparator`` to compare the contents of the userinfo attribute with the given ``Value``.
  The result of the comparison determines if the request matches the condition or not.

.. note:: There are situations in which the currently handled user
   cannot be determined.  If privacyIDEA encounters a policy with ``userinfo``
   conditions in such a situation, it throws an error and the current request is
   aborted.

   Likewise, privacyIDEA raises an error if ``Key`` refers to an unknown userinfo
   attribute, or if the condition definition is invalid due to some other reasons.
   More detailed information are then written to the logfile.

As an example for a correct and useful ``userinfo`` condition, let us assume
that you have configured a realm *ldaprealm* with a single LDAP resolver called
*ldapres*. This resolver is configured to fetch users from a OpenLDAP server,
with the following attribute mapping:

.. code-block:: json

    { "phone": "telephoneNumber",
      "mobile": "mobile",
      "email": "mailPrimaryAddress",
      "groups": "memberOf",
      "surname": "sn",
      "givenname": "givenName" }

You can further define ``groups`` to be a multi-value attribute by setting the
*Multivalue Attributes* option to ``["groups"]``.

According to this mapping, users of *ldaprealm* will have userinfo entries
``phone``, ``mobile``, ``email``, ``groups``, ``surname`` and ``givenname``
which are filled with the respective values from the LDAP directory.

You can now configure a policy that disables the WebUI login for all users in
the LDAP group ``cn=Restricted Login,cn=groups,dc=test,dc=intranet`` with an
email address ending in ``@example.com``:

* **Scope**: webui
* **Action**: ``login_mode=disable``
* 1) **additional condition** (active):
    * **Section**: ``userinfo``
    * **Key**: ``email``
    * **Comparator**: ``matches``
    * **Value**: ``.*@example.com``
  2) **additional condition** (active):
    * **Section**: ``userinfo``
    * **Key**: ``groups``
    * **Comparator:** ``contains``
    * **Value**: ``cn=Restricted Login,cn=groups,dc=test,dc=intranet``

The policy only takes effect if the user that is trying to log in has a matching
email address *and* is a member of the specified group. In other words, members
of the group with an email address ending in ``@privacyidea.org`` will still be
allowed to log in.

.. note:: Keep in mind that changes in the LDAP directory may not be
   immediately visible to privacyIDEA due to caching settings (see
   :ref:`ldap_resolver`).

If the userinfo of the user that is trying to log in does not contain attributes
``email`` or ``groups`` (due to a resolver misconfiguration, for example), privacyIDEA
throws an error and the request is aborted.


``tokeninfo``
^^^^^^^^^^^^

The tokeninfo condition works the same way as userinfo but matches the tokeninfo instead.

.. note:: In contrast to the userinfo condition, a missing token in the request, does not cancel it.
   Instead the condition is effectively **disabled** for the request.


``HTTP Request Header``
^^^^^^^^^^^^^^^^^^^^^^^

The section ``HTTP Request header`` can be used to define conditions that are checked against
the request header key-value pairs.

The ``Key`` specifies the request header key. It is case-sensitive.

privacyIDEA uses the ``Comparator`` to check if the value of a header is equal or a substring
of the required value.

.. note:: privacyIDEA raises an error if ``Key`` refers to an unknown request header.
   If the header in question is missing, the policy can not get completely evaluated.
   Be aware that requests, that do not contain the header ``Key`` will always fail!
   Thus, if you are using uncommon headers you should
   in addition restrict the policy e.g. to client IPs, to assure, that a request from
   this certain IP address will always contain the header, that is to be checked.


Comparators
~~~~~~~~~~~

The following comparators can be used in definitions of policy conditions:

* ``equals`` evaluates to true if the left value is equal to the right value, according to Python semantics.
  ``!equals`` evaluates to true if this is not the case.
* ``contains`` evaluates to true if the left value (a list) contains the right value as a member.
  ``!contains`` evaluates to true if this is not the case.
* ``in`` evaluates to true if the left value is contained in the list of values given by the right value.
  The right value is a comma-separated list of values. Individual
  values can be quoted using double-quotes.
  ``!in`` evaluates to true if the left value is not found in the list given by the right value.
* ``matches`` evaluates to true if the left value completely matches the regular expression given by the right value.
  ``!matches`` evaluates to true if this is not the case.

Error Handling
~~~~~~~~~~~~~~

privacyIDEA's error handling when checking policy conditions is quite strict,
in order to prevent policy misconfiguration from going unnoticed. If
privacyIDEA encounters a policy condition that evaluates neither to true nor
false, but simply *invalid* due to a misconfiguration, privacyIDEA throws an
error and the current request is aborted.
