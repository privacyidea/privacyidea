.. _policy_condition_checks:

Where Policy Conditions Are Checked
-----------------------------------

.. index:: policy conditions, conditions, missing data

privacyIDEA checks the conditions of a policy against the data of the request. Not every
request has all data. A request for the WebUI start page has no user, and a request that
lists tokens names no single token. This page shows which data privacyIDEA uses for
which kind of request, and which actions have special rules.

Conditions without a value in the request
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The fields *realm*, *resolver* and *user* need a user from the request. The result
depends on the request:

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - The request
     - A policy for the realm *sales*
   * - has a user of the realm *sales*
     - applies
   * - has a user of another realm
     - does not apply
   * - has an empty user, for example an administrator acts on a token without an owner
     - does not apply. Only policies without realm, resolver and user apply.
   * - has no user at all, for example the WebUI start page
     - applies. privacyIDEA does not check the realm.

The fields *resolver* and *user* work the same way. Thus a policy for one realm also
applies to a request that has no user. The sections below list these requests.

The other fields are checked for every request:

* *admin realm* and *admin user* in the scope *admin*: the logged-in administrator. A
  local administrator has an empty admin realm, see :ref:`faq_admins`.
* *client*: the client IP of the request, see :ref:`client <client_policies>`.
* *User Agent*: the user agent of the request. A request without a user agent matches
  only policies without a user agent.
* *privacyIDEA Node*: the node that handles the request. Exception: the rights that
  the WebUI shows, see `WebUI`_.
* *time*: the current time of the node.

For the additional conditions, see `Data for the additional conditions`_.

In the scopes *admin* and *user*, an action is allowed if a policy allows it, or if the
scope has no active policy at all. Every active policy of the scope counts, also a policy
for another realm, client, user agent, node or time.

The user of a request
~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Request
     - User for *realm*, *resolver*, *user* and ``userinfo``
   * - Authentication with ``user`` (``/validate/check``, ``/validate/radiuscheck``,
       ``/validate/triggerchallenge``, ``/auth``)
     - The user of the parameters ``user`` and ``realm``. Without a realm, the default
       realm. The policies :ref:`policy_set_realm`, :ref:`policy_setrealm` and
       :ref:`policy_mangle` can change the user before the other policies.
   * - ``/validate/check`` with ``serial`` and without ``user``
     - The owner of the token. Exception: :ref:`application_tokentype_policy`,
       :ref:`policy_setrealm` and :ref:`policy_mangle` run before privacyIDEA knows the
       owner. For them, the user is empty.
   * - ``/validate/triggerchallenge`` with ``serial`` and without ``user``
     - An empty user.
   * - Administrator acts on a token: ``enable``, ``disable``, ``delete``, ``assign``,
       ``set``, ``tokenrealms`` and the other token actions, also
       ``container_add_token`` and ``container_remove_token``
     - The owner of the token. The realm field also matches the realms of the token.
       For a token without an owner: an empty user and the realms of the token.
   * - Administrator acts on a container
     - The owner of the container and the realms of the container.
       ``container_create``: the user of the parameters.
   * - Other administrator requests, for example the configuration, the audit log or the
       policies
     - The parameters ``user`` and ``realm``. Without a ``realm`` parameter, the first
       realm of the token of the ``serial`` parameter. ``userinfo`` has no user.
   * - User manages their own tokens
     - The logged-in user.
   * - WebUI start page, before the login
     - No user.
   * - WebUI login (``/auth``) of a user or of an administrator of an admin realm
     - The user who logs in, in their realm.
   * - WebUI login (``/auth``) of a local administrator
     - The login name with an empty realm. privacyIDEA does not check the resolver, and
       there are no user attributes. See :ref:`faq_admins`.
   * - Container client requests (``/container/register/finalize``,
       ``/container/register/terminate/client``, ``/container/challenge``,
       ``/container/synchronize``, ``/container/rollover``)
     - The owner of the container if it has exactly one owner. Otherwise an empty user
       and the realms of the container.
   * - Push token requests from the smartphone (``/ttype/push``)
     - No user.

Data for the additional conditions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The table shows if a request has the data for the sections ``userinfo``, ``token`` /
``tokeninfo`` and ``container`` / ``container_info``. "no" means missing data:
:ref:`policy_condition_handle_missing_data` decides. "not checked" means that privacyIDEA
does not check the condition, and the policy applies as if the condition is true.

.. list-table::
   :header-rows: 1
   :widths: 40 20 20 20

   * - Request and policies
     - ``userinfo``
     - ``token``, ``tokeninfo``
     - ``container``, ``container_info``
   * - Authentication with ``user`` and password: the policies of the token check, like
       :ref:`otppin_policy`, :ref:`passthru_policy`, :ref:`passonnotoken`,
       :ref:`passonnouser`, :ref:`policy_auth_cache`, the challenge texts and the SMS,
       email and push texts
     - yes
     - no
     - no
   * - Authentication with ``serial``: the same policies
     - yes, the owner
     - yes
     - no
   * - Authorization checks after the authentication, like :ref:`authorized_policy`
     - yes
     - the token of the result, see `Authentication and authorization`_
     - no
   * - Administrator or user acts on a token
     - yes, see `The user of a request`_
     - yes
     - not checked
   * - Administrator or user acts on a container
     - yes, see `The user of a request`_
     - not checked
     - yes, not for ``container_create``
   * - Token enrollment (``/token/init``)
     - yes
     - no, the token does not exist yet
     - no
   * - Default values for the enrollment, like :ref:`hotp-otplen` and
       :ref:`hotp-hashlib`
     - no
     - no
     - no
   * - Other administrator requests
     - no
     - only with a single ``serial`` parameter
     - no
   * - WebUI start page
     - no
     - no
     - no
   * - WebUI login (``/auth``), the WebUI settings of the session
     - yes, not for local administrators
     - no
     - no
   * - Container client requests
     - yes, if the container has one owner
     - no
     - yes
   * - Push token requests from the smartphone (``/ttype/push``)
     - no
     - yes
     - no

The sections ``HTTP Request header``, ``HTTP Environment`` and ``Request Data`` read the
HTTP request itself.

Actions with special rules
~~~~~~~~~~~~~~~~~~~~~~~~~~

Authentication and authorization
................................

* :ref:`policy_set_realm` runs before privacyIDEA resolves the user. privacyIDEA
  compares the login name and the realm of the request. It does not check the resolver
  of the policy. If the request has no user and no realm, it does not check the realm of
  the policy. The policy has no ``userinfo``.
* :ref:`policy_serial`, :ref:`policy_tokeninfo`, :ref:`policy_no_detail_on_success` and
  :ref:`policy_no_detail_on_fail` in the scope *authorization*: privacyIDEA does not
  check the realm, resolver and user of the policy. These policies have no ``userinfo``
  and no ``token``.
* The other authorization checks after the authentication read the token of the result.
  A successful authentication through :ref:`passthru_policy`,
  :ref:`passonnotoken`, :ref:`passonnouser` or :ref:`policy_auth_cache` has no token.
* ``/validate/triggerchallenge`` with only a ``serial`` uses an empty user. Only
  policies without realm, resolver and user apply.
* WebUI login with the login mode privacyIDEA: the token types read some values during
  the login, like the push texts, ``push_ssl_verify`` or the challenge texts. For these
  values, privacyIDEA does not check the realm, resolver and user of the policy.
* :ref:`policy_auth_push_allow_poll`, ``push_registration_url`` and
  ``push_ssl_verify`` for requests from the smartphone: privacyIDEA does not check the
  realm, resolver and user of the policy.

Administration
..............

* Token actions: privacyIDEA matches the owner and the realms of the token, not the
  ``user`` parameter of the request. ``container`` and ``container_info`` conditions are
  not checked.
* Container actions: privacyIDEA matches the owner and the realms of the container.
  ``token`` and ``tokeninfo`` conditions are not checked.
* ``assign``, ``copytokenuser`` and ``copytokenpin`` on a token without an owner:
  privacyIDEA checks only the realms of the token, not the user and the resolver of the
  policy. A ``userinfo`` condition has no user in this step, and only
  ``Condition is true`` allows the action. In a second step, privacyIDEA checks the
  policy with all conditions for the new owner. ``Condition is true`` also applies to the
  other actions of the policy on tokens without an owner.
* Default values for the enrollment (``hotp_otplen``, ``hotp_hashlib``,
  ``totp_otplen``, ``totp_hashlib``, ``totp_timestep``, ``daypassword_otplen``,
  ``daypassword_hashlib``, ``daypassword_timestep``, ``certificate_trusted_Attestation_CA_path``):
  privacyIDEA does not check the resolver. If an administrator sends no ``realm``
  parameter, it does not check the realm.
* :ref:`policy_max_token_per_realm`: privacyIDEA checks only the realm, not the user and
  the resolver.

WebUI
.....

* Start page: privacyIDEA checks some policies before a user is known. It does not check
  their realm, resolver and user, and they have no user, token and container data. These
  policies are ``realm_dropdown``, ``login_text``, ``gdpr_link``,
  :ref:`webui_custom_menu`, :ref:`webui_custom_baseline`, :ref:`policy_passkey_login`,
  ``show_node``, ``otp_pin_set_random`` (scope *user*) and ``hide_version`` (scope
  *hardening*).
* The WebUI settings of the session, like ``logout_time`` or the page sizes, are fixed at
  the login. A later change of the time or of the client IP does not change them.
* The WebUI shows the menus and buttons from the rights at the login. For these rights,
  privacyIDEA does not check the node. For administrators it checks no additional
  conditions, for users only ``userinfo``. privacyIDEA checks every request again with
  all conditions.

Hardening
.........

The policies of the scope :ref:`policies_hardening` have no user. A condition that needs a
user, a token or a container has missing data. With ``Raise an error`` or
``Condition is false``, the policy does not apply.
