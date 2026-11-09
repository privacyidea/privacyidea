.. _policy_conditions:

Additional Policy Conditions
----------------------------

*Additional policy conditions* compare a value of the request with a value that you
enter in the policy. A policy applies to a request only if the request matches the
ordinary policy attributes (see :ref:`policies`) and *all* active additional
conditions. Inactive conditions are not checked.

.. versionadded:: 3.1

Each condition consists of these parts:

* ``Active`` turns the condition on or off. An inactive condition can contain values
  that are not valid.
* ``Section`` names the kind of data that the condition reads, see `Sections`_.
* ``Key`` names the value in that data, for example the user attribute ``email``.
* ``Comparator`` is the comparison, see `Comparators`_.
* ``Value`` is the right side of the comparison. It is always text.
* ``Handle Missing Data`` decides what happens if the request has no data for the
  condition, see `Handle Missing Data`_.

The data for a section is not available in every request. For example, a request that
lists all tokens names no single token. Before you add a condition, read
:ref:`policy_condition_checks`. It shows which data each kind of request has.

Sections
~~~~~~~~

privacyIDEA has the sections ``userinfo``, ``token``, ``tokeninfo``,
``HTTP Request header``, ``HTTP Environment``, ``container``, ``container_info`` and
``Request Data``.

userinfo
^^^^^^^^

The section ``userinfo`` reads an attribute of the user of the request. The user is the
user who authenticates, the user who manages their own tokens, or the user on whom an
administrator acts. :ref:`policy_condition_checks` shows which user that is for each
kind of request.

The attributes are the attributes of the attribute mapping of the resolver (see
:ref:`useridresolvers`) and the additional user attributes that privacyIDEA stores (see
:ref:`user_attributes`). An additional user attribute replaces a resolver attribute with
the same name. If users can set their own additional attributes (policy
:ref:`user_set_custom_user_attributes`), they can also set the value that your condition
compares. Use keys for which users have no such right.

An attribute is text, or a list of texts if the resolver defines it as a multi-value
attribute. Use ``contains`` for a list.

As an example, the realm *ldaprealm* has the LDAP resolver *ldapres* with this
attribute mapping:

.. code-block:: json

    {
      "phone": "telephoneNumber",
      "mobile": "mobile",
      "email": "mailPrimaryAddress",
      "groups": "memberOf",
      "surname": "sn",
      "givenname": "givenName"
    }

You must define ``groups`` as a multi-value attribute with the option
*Multivalue Attributes* ``["groups"]``. Otherwise ``groups`` is text, and the
``contains`` condition below raises an error.

This policy disables the WebUI login for the users in the LDAP group
``cn=Restricted Login,cn=groups,dc=test,dc=intranet`` who have an email address that ends
with ``@example.com``:

* **Scope**: webui
* **Action**: ``login_mode=disable``
* 1) **additional condition** (active):

    * **Section**: ``userinfo``
    * **Key**: ``email``
    * **Comparator**: ``matches``
    * **Value**: ``.*@example\.com``
*  2) **additional condition** (active):

    * **Section**: ``userinfo``
    * **Key**: ``groups``
    * **Comparator:** ``contains``
    * **Value**: ``cn=Restricted Login,cn=groups,dc=test,dc=intranet``

The policy applies only if the user has a matching email address *and* is a member of
the group. Members of the group with another email address can still log in.

.. note:: privacyIDEA can read the user attributes from a cache. A change in the LDAP
   directory is then not immediately visible (see :ref:`ldap_resolver`).

A user can lack the attribute ``email`` or ``groups``, for example because of an error
in the attribute mapping. The condition then has missing data, see
`Handle Missing Data`_.

For the actions ``container_add_token`` and ``container_remove_token``, privacyIDEA
checks the userinfo condition for the owner of the token and for the owner of the
container. The action is allowed only if both checks are successful.

.. versionadded:: 3.1

token
^^^^^

The section ``token`` reads a value of the token of the request. These keys are
available:

.. list-table::
   :header-rows: 1
   :widths: 60 40

   * - Key
     - Kind of value
   * - ``serial``, ``tokentype``, ``description``, ``rollout_state``, ``resolver``,
       ``user_id``
     - text
   * - ``id``, ``otplen``, ``count``, ``count_window``, ``sync_window``, ``maxfail``,
       ``failcount``
     - number
   * - ``active``, ``revoked``, ``locked``
     - yes or no
   * - ``realms``, ``tokengroup``
     - list of texts

``resolver`` and ``user_id`` belong to the owner of the token. privacyIDEA stores token
types in lower case, for example ``hotp``.

For numbers, use the comparators ``<`` and ``>``. For a yes-or-no value, *yes* counts
as ``1`` and *no* as ``0``. ``equals`` and ``in`` never match a number or a yes-or-no
value, see `Comparators`_.

**Example**: a policy in the scope *user* with the action ``delete`` and the token
condition ``active``, ``<``, ``1`` allows users to delete inactive tokens, but not
active tokens.

.. versionadded:: 3.6

tokeninfo
^^^^^^^^^

The section ``tokeninfo`` reads a value of the token info of the token of the request,
for example ``tokenkind`` or ``hashlib``. All token info values are text.

.. versionadded:: 3.5

HTTP Request header
^^^^^^^^^^^^^^^^^^^

The section ``HTTP Request header`` reads a header of the HTTP request. The ``Key`` is
the name of the header. Upper and lower case in the name do not matter. The value is
text.

Not every client sends every header. A request without the header has missing data. If
you check such a header, also restrict the policy to the clients that send it, for
example by their client IPs.

.. versionadded:: 3.2

HTTP Environment
^^^^^^^^^^^^^^^^

The section ``HTTP Environment`` reads a value of the WSGI environment of the request.
The ``Key`` is case-sensitive. Examples:

* ``PATH_INFO`` is the endpoint, like ``/validate/check`` or ``/auth``.
* ``REQUEST_METHOD`` is the HTTP method, like ``POST``.
* ``REMOTE_ADDR`` is the address of the direct peer, for example of a reverse proxy.
  It is not the client IP of the policy, see :ref:`client <client_policies>`.

Most values are text. If the ``Key`` does not exist and the log level is ``DEBUG``, the
log file lists the available keys.

.. versionadded:: 3.7

container
^^^^^^^^^

The section ``container`` reads a value of the container of the request. The keys are
the keys of :py:meth:`privacyidea.lib.containerclass.TokenContainerClass.get_as_dict()`,
for example:

.. list-table::
   :header-rows: 1
   :widths: 60 40

   * - Key
     - Kind of value
   * - ``type``, ``serial``, ``description``, ``template``
     - text
   * - ``last_authentication``, ``last_synchronization``
     - date and time in ISO format with the time zone UTC (``+00:00``), or no value if it
       did not happen yet
   * - ``states``, ``realms``
     - list of texts

A container that never authenticated or synchronized has no value for
``last_authentication`` or ``last_synchronization``. The condition then has missing
data. These dates have a time zone, so the ``Value`` of ``date_before`` and
``date_after`` must also have one, for example ``2025-01-31T00:00:00+00:00``.

The actions ``container_create`` and ``container_list`` and the template actions have no
single container. A ``container`` or ``container_info`` condition then has missing data.

.. versionadded:: 3.12

container_info
^^^^^^^^^^^^^^

The section ``container_info`` reads a value of the container info of the container of
the request. All container info values are text.

.. versionadded:: 3.12

Request Data
^^^^^^^^^^^^

The section ``Request Data`` reads a parameter of the request. This is a query
parameter, a parameter in the body, or a part of the URL path, like the serial in
``/token/disable/<serial>``. The :ref:`rest_api` documentation lists the parameters of
each endpoint.

* privacyIDEA removes the parameters ``pass`` and ``password``. You can not use them in
  a condition.
* The values are the values that the client sent. Changes of the request by privacyIDEA
  are not visible. This applies to a realm from :ref:`policy_set_realm` or
  :ref:`policy_setrealm`, to a value from :ref:`policy_mangle` or the
  :ref:`requestmanglerhandler`, and to the default realm. It also applies to the user and
  the realm that privacyIDEA sets for a user who manages their own tokens.
* When privacyIDEA creates the tokens of a container template, Request Data holds the
  values of the template for each token, as in a token enrollment. It does not hold the
  parameters of the request.
* A client can send any parameter with any value. Do not use a Request Data condition
  to grant a right. Use the ordinary policy attributes for the user and the realm.
* A request with a JSON body keeps the JSON types. ``{"genkey": 1}`` sends a number,
  ``{"genkey": "1"}`` sends text. The WebUI sends JSON.

.. versionadded:: 3.12

Comparators
~~~~~~~~~~~

The left value comes from the request, the right value is the ``Value`` of the
condition. The right value is always text.

* ``equals`` is true if the left value is the same text as the right value.
  ``!equals`` is true if this is not the case. privacyIDEA does not convert the left
  value. A number, a yes-or-no value or a list is never equal to the right value. For
  such a value, ``equals`` is always false and ``!equals`` is always true. Thus a policy
  that restricts something with ``!equals`` on such a value applies to every request. Use
  ``<`` and ``>`` for numbers and yes-or-no values, and ``contains`` for lists.
* ``contains`` is true if the left value is a list that contains the right value.
  ``!contains`` is true if this is not the case. If the left value is not a list,
  privacyIDEA raises an error.
* ``in`` is true if the left value is in the comma-separated list of the right value.
  You can put a value in double quotes, for example ``"Doe, John",alice``.
  ``!in`` is true if this is not the case. The left value must be text. For a number, a
  yes-or-no value or a list, ``in`` is always false and ``!in`` is always true.
* ``matches`` is true if the left value completely matches the regular expression of the
  right value. ``!matches`` is true if this is not the case. For a match that ignores
  upper and lower case, start the expression with ``(?i)``. If the left value is not
  text or the expression is not valid, privacyIDEA raises an error.
* ``<`` is true if the left value is smaller than the right value. ``>`` is true if the
  left value is bigger. privacyIDEA converts both values to whole numbers. A left value
  without content counts as ``0``. If a value is not a whole number, privacyIDEA raises
  an error.

  .. versionadded:: 3.6 ``<`` and ``>``

* ``date_before`` is true if the left date and time is before the right date and time.
  ``date_after`` is true if it is after. Both values must be in ISO format, at least
  ``YYYY-MM-DD``, for example ``2025-01-31 12:00:00+01:00``. Either both values have a
  time zone or none of them. Otherwise privacyIDEA raises an error.

  .. versionadded:: 3.12 ``date_before`` and ``date_after``

* ``date_within_last`` is true if the left date and time is within the time span of the
  right value before now. ``!date_within_last`` is true if this is not the case. The
  right value is a whole number and a unit: ``s`` (seconds), ``m`` (minutes), ``h``
  (hours), ``d`` (days) or ``y`` (years of 365 days). For example, ``7d`` means "within
  the last 7 days". A left date without time zone counts as UTC.

  .. versionadded:: 3.12

* ``string_contains`` is true if the left value contains the right value as part of the
  text. ``!string_contains`` is true if this is not the case. Upper and lower case do not
  matter. All other comparators are case-sensitive. If the left value is not text,
  privacyIDEA raises an error.

  .. versionadded:: 3.12

To match the users of the Active Directory group *VPN Users*:

#. Map the attribute ``memberOf`` in the LDAP resolver, for example
   ``"groups": "memberOf"``.
#. Define ``groups`` as a multi-value attribute.
#. Add this condition::

      "groups" contains "CN=VPN Users,OU=Groups,DC=example,DC=com"

To match some users by their login name, add this condition::

   "username" in "alice,bob,charlie"

.. versionadded:: 3.1

.. _policy_condition_handle_missing_data:

Handle Missing Data
~~~~~~~~~~~~~~~~~~~

The data for a condition is missing in these cases:

* The request has no object for the section. For example, the request has no user for a
  ``userinfo`` condition, or no single token for a ``token`` condition.
* The object has no value for the ``Key``. For example, the user has no ``email``
  attribute, or the request has no header with this name. A value without content, like
  an empty description, is not missing.

:ref:`policy_condition_checks` shows which data each kind of request has.

``Handle Missing Data`` has three options:

* ``Raise an error``: privacyIDEA stops the request with a policy error. This is the
  default. It also applies to conditions from privacyIDEA versions before 3.12. For two
  exceptions, see `Error Handling`_.
* ``Condition is false``: the policy does not apply.
* ``Condition is true``: the policy applies.

The option applies to every request that checks the policy. With ``Raise an error``, a
condition that has no data in some requests stops all of these requests. For example,
a WebUI policy with a ``userinfo`` condition stops the login of local administrators,
because they have no user attributes.

Select the option from the effect of the policy:

* If the policy gives a right or turns on a function, ``Condition is false`` keeps the
  right off when privacyIDEA can not check the condition.
* If the policy restricts something, like ``login_mode=disable`` or a ``hide_*``
  action, ``Condition is true`` keeps the restriction on when privacyIDEA can not check
  the condition.

Use of conditions is an advanced feature. Test the policies in a test environment
before you use them in production.

.. versionadded:: 3.12

Error Handling
~~~~~~~~~~~~~~

If a condition is not valid, privacyIDEA raises a policy error and stops the request.
``Handle Missing Data`` does not change this. privacyIDEA raises an error in these cases:

* The section or the comparator is unknown.
* The comparison is not possible:

  * ``contains`` on a value that is not a list,
  * ``<`` or ``>`` on a value that is not a whole number,
  * ``matches`` or ``string_contains`` on a value that is not text,
  * ``matches`` with an expression that is not valid,
  * a date that is not in ISO format,
  * ``date_before`` or ``date_after`` with only one time zone.

The log file contains the details.

In two cases, a policy error does not stop the request. This applies to an invalid
condition and to ``Raise an error`` for missing data:

* A policy of the scope :ref:`policies_hardening` on the API: the policy does not apply.
  Thus the error turns off the protection of the policy.
* A token that privacyIDEA creates from a container template: if a policy check before
  the creation fails, privacyIDEA does not create this token. Examples are a token limit,
  the right to enroll the token type, or a default value. privacyIDEA creates the other
  tokens of the template, and the response lists only the created tokens.
