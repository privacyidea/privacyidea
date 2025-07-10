.. _policy_conditions:

Extended Policy Conditions
--------------------------

Since privacyIDEA 3.1, *extended policy conditions* allow defining more advanced
rules for policy matching, i.e. for determining which policies are valid for a
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
consists of the following parts:

 * ``Active`` determines if the condition is currently active.
 * ``Section`` refers to an aspect of the incoming request on which the condition is applied.
   The available sections are predefined, see `Sections`_.
 * The meaning of ``Key`` depends on the chosen ``Section``. Typically, it determines the exact property
   of the incoming request on which the condition is applied.
 * ``Comparator`` defines the comparison to be performed. The available comparators are predefined, see `Comparators`_.
 * ``Value`` determines the value the property should be compared against.
 * ``Handle Missing Data`` defines the behaviour of the system if the data required to check the condition is missing.
   See `Handle Missing Data`_ for more information.

Sections
~~~~~~~~

privacyIDEA implements the sections ``userinfo``, ``token``, ``tokeninfo``, ``HTTP Request Headers``,
``HTTP Environment``, ``Container``, and ``Container Info``.

userinfo
^^^^^^^^

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

   To avoid raising an error, define the :ref:`policy_condition_handle_missing_data` option.

As an example for a correct and useful ``userinfo`` condition, let us assume
that you have configured a realm *ldaprealm* with a single LDAP resolver called
*ldapres*. This resolver is configured to fetch users from a OpenLDAP server,
with the following attribute mapping:

.. code-block:: json

    {
      "phone": "telephoneNumber",
      "mobile": "mobile",
      "email": "mailPrimaryAddress",
      "groups": "memberOf",
      "surname": "sn",
      "givenname": "givenName"
    }


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
*  2) **additional condition** (active):

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

For the actions ``container_add_token`` and ``container_remove_token``, the user info condition is evaluated on the
token and container owner. Only if both conditions are true, the action is allowed.


tokeninfo
^^^^^^^^^

The tokeninfo condition works the same way as userinfo but matches the tokeninfo instead.

.. note:: Similar to the userinfo condition, a policy with an active tokeninfo condition will
   throw an exception whenever the token object cannot be determined (usually from the serial).
   To avoid raising an error, define the :ref:`policy_condition_handle_missing_data` option.

token
^^^^^

The token condition works on the database columns of the token. This would be
``description``, ``otplen``, ``count``, ``serial``, ``active`` but most importantly
also ``failcount`` and ``tokentype``.

.. note:: A policy with an active token condition will
   throw an exception whenever the token object cannot be determined.
   It will also throw an error, if the request ``Key`` does not exist
   as a database column.
   To avoid raising an error, define the :ref:`policy_condition_handle_missing_data` option.

.. note:: The matching is case-sensitive. Note, that e.g. token types are
   stored in lower case in the database.

**Example**: The administrator could define a dedicated policy in the scope *user* with the
action ``delete`` and the token condition ``active``, ``<``, ``1``. For an inactive token the attribute ``active``
would evaluate to ``0`` and thus be smaller than ``1``. An ``active`` token would evaluate to ``1``.
This would allow the user to delete only inactive tokens, but not still active tokens.

HTTP Request Header
^^^^^^^^^^^^^^^^^^^

The section ``HTTP Request header`` can be used to define conditions that are checked against
the request header key-value pairs.

The ``Key`` specifies the request header key. It is case-sensitive.

privacyIDEA uses the ``Comparator`` to check if the value of a header is equal or a substring
of the required value.

.. note:: privacyIDEA raises an error if ``Key`` refers to an unknown request header.
   If the header in question is missing, the policy can not get completely evaluated.
   Be aware that requests that do not contain the header ``Key`` will always fail!
   Thus, if you are using uncommon headers you should
   in addition restrict the policy e.g. to client IPs, to assure, that a request from
   this certain IP address will always contain the header, that is to be checked.
   To avoid raising an error, define the :ref:`policy_condition_handle_missing_data` option.

HTTP Environment
^^^^^^^^^^^^^^^^

The section ``HTTP Environment`` can be used to define conditions that are checked against
the HTTP environment key-value pairs.

The ``Key`` is case-sensitive.

The environment contains information like the ``PATH_INFO`` which contains the name of the
endpoint like ``/validate/check`` or ``/auth``.

.. note:: privacyIDEA raises an error if ``Key`` refers to an unknown environment key.
   The log file then contains information about the available keys.
   The behaviour is similar to the extended conditions of HTTP Request Header.
   To avoid raising an error, define the :ref:`policy_condition_handle_missing_data` option.

Container
^^^^^^^^^
For container requests, the section ``Container`` can be used to define conditions that are checked against the
container attributes. To get the container attributes, the function
:py:meth:`privacyidea.lib.containerclass.TokenContainerClass.get_as_dict()` is used. Hence, all defined
keys in the returned dictionary can also be used in the condition as key, e.g. ``type``, ``serial``, ``states``.

The condition can only be evaluated when a valid container serial is available which is the case for most container
endpoints. It does not work for the actions ``container_list`` (:http:get:`/container/`),
``container_create`` (:http:post:`/container/init`) and the template actions.


Container Info
^^^^^^^^^^^^^^

The ``Container Info`` condition works the same way as userinfo but matches the container info instead.

The condition can only be evaluated when a valid container serial is available which is the case for most container
endpoints. It does not work for the actions ``container_list`` (:http:get:`/container/`),
``container_create`` (:http:post:`/container/init`) and the template actions.


Comparators
~~~~~~~~~~~

The following comparators can be used in definitions of policy conditions:

* ``equals`` evaluates to true if the left value is equal to the right value, according to Python semantics.
  ``!equals`` evaluates to true if this is not the case.
* ``contains`` evaluates to true if the left value (a list) contains the right value as a member.
  ``!contains`` evaluates to true if this is not the case.
* ``in`` evaluates to true if the left value is contained in the list of values given by the right value.
  The right value is a comma-separated list of values. Individual values can be quoted using double-quotes.
  ``!in`` evaluates to true if the left value is not found in the list given by the right value.
* ``matches`` evaluates to true if the left value completely matches the regular expression given by the right value.
  ``!matches`` evaluates to true if this is not the case.
* ``<`` evaluates to true if the left value is smaller than the right value.
* ``>`` evaluates to true if the left value is greater than the right value.
* ``date_before`` evaluates to true if the left value is a date and time that occurs before the right value.
  Both values must be a date in ISO format (e.g. "YYYY-MM-DD hh:mm:ss±hh:mm").
* ``date_after`` evaluates to true if the left value is a date and time that occurs after the right value.
  Both values must be a date in ISO format (e.g. "YYYY-MM-DD hh:mm:ss±hh:mm").
* ``date_within_last`` evaluates to true if the left-hand value is a date and time that falls within the past time
  interval specified by the right-hand value. ``!date_within_last`` evaluates to true if this is not the case.
  The right-hand value must be a duration expressed as an integer
  immediately followed by a time unit:
    * ``y`` for years
    * ``d`` for days
    * ``h`` for hours
    * ``m`` for minutes
    * ``s`` for seconds
  For example, "7d" means "within the last 7 days", "2h" means "within the last 2 hours".
* ``string_contains`` evaluates to true if the left value (a string) contains the right value as a substring.
  ``!string_contains`` evaluates to true if this is not the case.


If you want to define a policy that e.g. only matches users from Active Directory that are in a
VPN User group, you would first need to map the `memberOf` attribute in the LDAP resolver to a certain
attribute like `"groups": "memberOf"`. Then you need to define the extended condition:

   "groups" contains "CN=VPN Users,OU=Groups,DC=example,DC=com"

If you however want to define a policy that matches e.g. a certain username from a list,
you would have to define an extended condition like:

   "username" in "alice,bob,charlie"


.. _policy_condition_handle_missing_data:

Handle Missing Data
~~~~~~~~~~~~~~~~~~~~

There might be the case, that a condition shall be evaluated, but the required data to check the condition is missing.
For example, an admin is doing a request and hence the user object is not available or even if the user object is
available, the defined key may not be included in the user attributes. This could be avoided with well thought out and
elaborated conditions. However, this might not hold for all scenarios.

There are three different options how the system should handle if the data is missing to check the condition:
    * ``Raise an error``: The system will raise a PolicyError and abort the request.
    * ``Condition is false``: The condition is evaluated to false, hence the policy will not be applied.
    * ``Condition is true``: The condition is evaluated to true, hence the policy will be applied.

The default behaviour is to raise an error. This is the most strict behaviour and prevents policy misconfigurations
from going unnoticed. It is also applied for policies defined in privacyIDEA versions < 3.12 and was the behaviour in
previous versions.

Generally, the usage of conditions is an advanced feature and requires further knowledge about the data available in
the related requests. We highly recommend to evaluate the correct behaviour of the policies in a test environment,
especially when using ``Condition is false/true``.


Error Handling
~~~~~~~~~~~~~~

privacyIDEA's error handling when checking policy conditions is quite strict,
in order to prevent policy misconfiguration from going unnoticed. If
privacyIDEA encounters a policy condition that evaluates neither to true nor
false, but simply *invalid* due to a misconfiguration, privacyIDEA throws an
error and the current request is aborted.

This behaviour can be changed by setting the `Handle Missing Data`_ option
to ``Condition is false`` or ``Condition is true``. However, this only avoids to throw an error if the required data
is missing (e.g. no token or user in the request). If an invalid section or comparator is used, an error will still be
raised.
