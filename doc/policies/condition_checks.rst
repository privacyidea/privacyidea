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
     - does not apply, unless the token is in the realm *sales*
   * - has no user at all, for example the WebUI start page
     - applies. privacyIDEA does not check the realm.

The fields *resolver* and *user* work the same way. Thus a policy for one realm also
applies to a request that has no user. The sections below list these requests.

An empty user matches a field that is blank or contains ``*``. In the field *user*, an
empty user also matches an expression that accepts an empty name, like ``.*``. A policy
with :ref:`check_all_resolvers <check_all_resolvers>` does not apply to an empty user.

If an administrator acts on a token or a container, privacyIDEA also compares the field
*realm* with the realms of the token or the container. This also applies to a token or a
container without an owner.

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
     - The user of the parameters ``user`` (``username`` for ``/auth``) and ``realm``.
       Without a realm, the default realm. :ref:`policy_set_realm` can change the realm
       before the other policies. On ``/validate/check`` and ``/validate/radiuscheck``,
       :ref:`policy_setrealm` and :ref:`policy_mangle` can also change the user. They do
       not run on ``/validate/triggerchallenge`` and ``/auth``.
   * - ``/validate/check`` with ``serial`` and without ``user``
     - The owner of the token. Exception: :ref:`application_tokentype_policy`,
       :ref:`policy_setrealm` and :ref:`policy_mangle` run before privacyIDEA knows the
       owner. For them, the user is empty.
   * - ``/validate/triggerchallenge`` with ``serial`` and without ``user``
     - An empty user.
   * - Administrator acts on a token: ``enable``, ``disable``, ``delete``, ``assign``,
       ``set``, ``tokenrealms`` and the other token actions
     - The owner of the token. The realm field also matches the realms of the token.
       For a token without an owner: an empty user and the realms of the token.
   * - Administrator acts on a container
     - The owner of the container and the realms of the container.
       ``container_create``: the user of the parameters.
   * - Administrator adds a token to a container or removes a token from a container
       (``container_add_token``, ``container_remove_token``)
     - Two checks: the owner and the realms of the token, and the owner and the realms
       of the container. Both checks must allow the action. ``/token/init`` with a
       ``container_serial`` checks only the container.
   * - Administrator reads the audit log or the authentication log (``auditlog``,
       ``auditlog_download``, ``authentication_log_read``)
     - No user. See `Administration`_.
   * - Other administrator requests, for example the configuration or the policies
     - The parameters ``user`` and ``realm``. Without a ``realm`` parameter, the first
       realm of the token of the ``serial`` parameter. ``userinfo`` has no user.
   * - User manages their own tokens
     - The logged-in user.
   * - WebUI start page, before the login
     - No user. Exception: :ref:`policy_remote_user`, see `WebUI`_.
   * - WebUI login (``/auth``) of a user or of an administrator of an admin realm
     - The user who logs in, in their realm.
   * - WebUI login (``/auth``) of a local administrator
     - The login name with an empty realm. privacyIDEA does not check the resolver, and
       there are no user attributes. Exception: :ref:`policy_remote_user` uses the
       default realm. See :ref:`faq_admins`.
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
     - only with a ``serial`` parameter
     - no
   * - Authentication with ``serial`` and without ``user``: the same policies
     - yes, the owner
     - yes
     - no
   * - Authentication: :ref:`policy_change_pin_via_validate`,
       :ref:`policy_resync_via_multichallenge` and the PIN change of
       :ref:`policy_change_pin_every`
     - yes, the owner of the token
     - yes
     - yes, if the token is in a container
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
     - yes, not for ``container_create``, ``container_list`` and the template actions
   * - Administrator or user adds a token to a container or removes a token from a
       container
     - yes, see `The user of a request`_
     - yes
     - yes
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
* ``/validate/triggerchallenge`` with only a ``serial`` uses an empty user. Only the
  policies whose realm, resolver and user accept an empty user apply, see
  `Conditions without a value in the request`_.
* :ref:`policy_change_pin_via_validate`, :ref:`policy_resync_via_multichallenge` and the
  PIN change of :ref:`policy_change_pin_every`: privacyIDEA matches the owner and the
  realms of the token, not the user of the request. The conditions have the data of the
  token and of its container.
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
* ``container_add_token`` and ``container_remove_token`` are token actions and container
  actions. privacyIDEA checks them twice, once as a token action and once as a container
  action. Both checks must allow the action. Thus the ``token`` conditions apply to the
  token, the ``container`` conditions to the container, and the ``userinfo`` conditions
  to both owners. If the token moves from another container, privacyIDEA also checks
  ``container_remove_token`` for the old container.
* :ref:`policy_auditlog`, :ref:`policy_auditlog_download` and
  :ref:`policy_authentication_log_read` for an administrator: privacyIDEA does not
  compare the realm, resolver and user of the policy with the request. It uses these
  fields to select the entries that the administrator can read. The description of each
  action explains the rules.
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
  ``show_node``, ``otp_pin_set_random`` and :ref:`policy_password_reset` (scope
  *user*) and ``hide_version`` (scope *hardening*).
* Start page, :ref:`policy_remote_user`: if the web server sends ``REMOTE_USER``,
  privacyIDEA checks this policy for the account that ``REMOTE_USER`` names. Without a
  realm in ``REMOTE_USER``, this is the default realm. The ``userinfo`` conditions read
  this account. For a local administrator or for a name that does not exist in the realm,
  privacyIDEA checks the login name and the realm. It does not check the resolver, and
  ``userinfo`` has no data.
* The WebUI settings of the session, like ``logout_time`` or the page sizes, are fixed at
  the login. A later change of the time or of the client IP does not change them.
* The WebUI shows the menus and buttons from the rights at the login. For these rights,
  privacyIDEA does not check the node. For administrators it checks no additional
  conditions, for users only ``userinfo``. privacyIDEA checks every request again with
  all conditions.

Hardening
.........

The policies of the scope :ref:`policies_hardening` have no user. A condition that needs a
user, a token or a container has missing data. With ``Condition is false``, the policy
does not apply. With ``Condition is true``, it applies.

On the API, an error in a hardening policy does not stop the request. The policy does not
apply instead. This includes ``Raise an error`` for missing data and an invalid condition.
Thus an error turns off the protection of the policy. The log file contains the details.
