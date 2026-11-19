# Update from 3.13 to 3.14.1

This page lists what changes when you update from 3.13 to 3.14.1. It has four parts:

1. [Every installation](#1-every-installation): the steps before, during and after the update.
2. [Find your topics](#2-find-your-topics): a table of features. Read only the topics of the features that you use.
3. [Changes by topic](#3-changes-by-topic): one item for each change. Each item starts with the installations it
   affects and what to do.
4. [Already on 3.14.0](#4-already-on-3140): read this part first if you run 3.14.0.

The heading of each item names the version that brought the change. "Before" means 3.13, and in part 4 it means
3.14.0.

## 1. Every installation

**Before the update**

1. Test the update on a test system first, with a copy of your configuration and your database. Do not update a
   production system before the test passes.
2. Make a backup of the program directory, the database and the configuration. Add `-e` to `pi-manage backup create`,
   or keep a copy of the encryption key in a different place. Without `-e`, the backup does not include the key. See
   [Upgrading](https://privacyidea.readthedocs.io/en/stable/installation/upgrade.html).
3. Make sure that no important challenge-response login is open. The schema update deletes all open challenges,
   because challenges use a new format.
4. Stop privacyIDEA on every node before the schema update starts. Do not let a node of the old version serve the
   updated database. See [Internal user attributes move to a new table](#internal-user-attributes-move-to-a-new-table-3140)
   and [Secrets in configuration responses are censored](#secrets-in-configuration-responses-are-censored-3140-changed-in-3141).
5. If you use MySQL or MariaDB, plan the time for the rebuild of the audit table. See
   [The audit `serial` column holds 200 characters](#the-audit-serial-column-holds-200-characters-3140).
6. If you set `PI_HASH_ALGO_LIST` or `PI_HASH_ALGO_PARAMS`, check both settings. A wrong value stops the server and the
   schema update. See [privacyIDEA checks the hash settings at start](#privacyidea-checks-the-hash-settings-at-start-3140).
7. Make sure that your database has a schema revision stamp. See
   [The schema update stops on a database without a schema revision stamp](#the-schema-update-stops-on-a-database-without-a-schema-revision-stamp-3141).
8. Do the checks of these items before the update:
   - [Policies with a User Agent condition count as configured](#policies-with-a-user-agent-condition-count-as-configured-3140).
     Administrators can lose all rights.
   - [Request header, environment and request data conditions apply on the WebUI start page and the push poll](#request-header-environment-and-request-data-conditions-apply-on-the-webui-start-page-and-the-push-poll-3141)
   - [Container conditions of PIN change and resync policies check the container of the token](#container-conditions-of-pin-change-and-resync-policies-check-the-container-of-the-token-3141)
   - [`date_within_last` does not match a date in the future](#date_within_last-does-not-match-a-date-in-the-future-3141)
   - [Passkey and WebAuthn logins apply the token limits](#passkey-and-webauthn-logins-apply-the-token-limits-3141)
   - [A user store error fails the request](#a-user-store-error-fails-the-request-3141), for HTTP resolvers
   - [The validity time of Email and SMS OTP values applies to every login](#the-validity-time-of-email-and-sms-otp-values-applies-to-every-login-3141)
   - [The token janitors read `1`, `yes` and `on` as true](#the-token-janitors-read-1-yes-and-on-as-true-3140-changed-in-3141)
   - [Custom audit modules get `exact_params`](#custom-audit-modules-get-exact_params-3141)
   - [Entra ID resolvers apply their TLS settings to the sign-in](#entra-id-resolvers-apply-their-tls-settings-to-the-sign-in-3141)

**During the update**

1. Run the schema update with `privacyidea-schema-upgrade`. `privacyidea-pip-update` runs it for you. Without the
   schema update, SSH key tokens refuse their keys.
2. Save the output of the schema update. It prints the database and its schema revision before and after the update.
   It names the policies that the update changes or deletes, and it counts the u2f tokens and the event handlers that
   the update changes. The output goes to the terminal, not to the privacyIDEA log.

**After the update**

1. Check each policy that the output of the schema update names. See
   [Boolean policy actions with a false value are stored as excluded actions](#boolean-policy-actions-with-a-false-value-are-stored-as-excluded-actions-3141)
   and [The u2f token type is removed](#the-u2f-token-type-is-removed-3140-changed-in-3141).
2. If you have `admin` or `user` policies, grant the new actions where you need them: `token_rollover`,
   `cancelchallenge`, `get_user_internal_attributes`, `serviceid_list` and `configread`. See
   [Policies and rights](#31-policies-and-rights).
3. Check the audit entries of your request and response manglers. See
   [An error of an event handler fails the request only with *Abort on error*](#an-error-of-an-event-handler-fails-the-request-only-with-abort-on-error-3140-changed-in-3141).
4. If your realm administrators create containers from templates, check the templates. See
   [Tokens from a container template are checked with their own user and realm](#tokens-from-a-container-template-are-checked-with-their-own-user-and-realm-3141).
5. If you install from PyPI, add the metrics cleanup to your crontab. See
   [The metrics table needs a regular cleanup](#the-metrics-table-needs-a-regular-cleanup-3140).
6. If you enabled the preview of the new WebUI, remove two lines from `pi.cfg`. See
   [The new WebUI is the default](#the-new-webui-is-the-default-3140).
7. If you use `auth_cache` with challenge-response tokens, push tokens, `passOnNoToken` or `passOnNoUser`, clear the
   cache. See [`auth_cache` holds only complete credentials](#auth_cache-holds-only-complete-credentials-3140).

## 2. Find your topics

| If your installation ... | Read |
|---|---|
| has policies in the `admin` or `user` scope, or policies with conditions, `check_all_resolvers`, nodes or user agents | [Policies and rights](#31-policies-and-rights) |
| uses passkey, WebAuthn, Email, SMS, RADIUS, SSH key, push, application specific password, u2f or container tokens, container templates, `passOnNoUser` or HTTP resolvers | [Tokens and authentication](#32-tokens-and-authentication) |
| uses PIN policies (`otp_pin_*`, `otp_pin_random`, `change_pin_via_validate`, `otppin`), a PIN handler or simple pass tokens | [PINs](#33-pins) |
| has event handlers | [Event handlers](#34-event-handlers) |
| has scripts or integrations that call the HTTP API | [HTTP API](#35-http-api) |
| runs `pi-manage`, the token janitors or other tools in custom scripts or custom cron jobs. The default cron jobs of the Ubuntu packages are not affected | [Command line tools](#36-command-line-tools) |
| uses MySQL, MariaDB, Oracle, a separate audit database or more than one node, or has a database without a schema revision stamp | [Database and audit log](#37-database-and-audit-log) |
| sets the hash settings, or uses Entra ID, resolvers with the same priority, the local CA or `PI_CHECK_RELOAD_CONFIG` | [Resolvers, connectors and configuration](#38-resolvers-connectors-and-configuration) |
| runs behind a proxy, sets *Override Authorization Client*, or has policies or event handlers with IP conditions | [Client IP and proxies](#39-client-ip-and-proxies) |
| uses Redis or the `auth_cache` policy | [Caches](#310-caches) |
| uses a custom audit module, SMS provider or PIN handler | [Custom modules](#311-custom-modules) |
| uses the preview of the new WebUI or the old WebUI, or changes the WebUI sources | [WebUI](#312-webui) |

## 3. Changes by topic

### 3.1 Policies and rights

#### Policies with a User Agent condition count as configured (3.14.0)

- **Affects you if:** a policy in the `admin` or `user` scope has a User Agent condition.
- **Do before the update:** make sure that at least one active `admin` policy grants your administrators their rights
  without a User Agent condition. A condition that names their client also works, for example `privacyIDEA-WebUI`
  for the WebUI.

The `admin` and `user` scopes allow every action while they hold no policy. A scope that held only policies with a
User Agent condition counted as empty, so it allowed everything. Now such a scope counts as configured. A request from
another client gets only the actions that a policy grants to it.

If every `admin` policy has a User Agent condition, administrators can lose all rights, also the right to change the
policy. In the `user` scope, users lose self-service rights. To recover from a lockout, disable the policy on the
server:

    pi-manage config policy list
    pi-manage config policy disable <name>

The configuration export and `GET /system/documentation` now also show the policies with a User Agent condition.

#### A token rollover needs the new action `token_rollover` (3.14.0, changed in 3.14.1)

- **Affects you if:** you have `admin` or `user` policies, and administrators or users roll tokens over.
- **Do after the update:** add `token_rollover` to the policies of these administrators and users.

`POST /token/init` with the serial of a token in use gives the token a new secret. This rollover now needs
`token_rollover` in the `admin` or `user` scope. While the enrollment of a token is not complete, `enroll<TOKENTYPE>`
is enough. Examples are the second request of a two-step or a FIDO2 enrollment, and a token that waits for its
verification. The enrollment of a new token does not change.

Both actions match the policy against the stored token: its owner or one of its realms, not a realm in the request.
For a token that exists, the server checks `enroll<TOKENTYPE>` for the type of that token and refuses another `type`.
A user can only name a token that the user owns. Without any policy in the scope, nothing changes.

The `token_rollover` action of the `webui` scope only decides for which token types the WebUI shows a rollover
button. The WebUI checks both actions.

#### The new action `cancelchallenge` cancels a challenge (3.14.0)

- **Affects you if:** an `admin` policy grants `getchallenges`.
- **Do after the update:** add `cancelchallenge` to the administrators who cancel open challenges.

`DELETE /token/challenges/transaction/<transaction_id>` needed `getchallenges`. Now it needs `cancelchallenge`.
`getchallenges` only shows the open challenges.

#### The new action `get_user_internal_attributes` reads internal user attributes (3.14.0)

- **Affects you if:** you have `admin` policies.
- **Do after the update:** add `get_user_internal_attributes` to the administrators who read these attributes.

The internal user attributes, for example `fido2_user_id` and `last_used_token`, are available through
`GET /user/internal_attribute` and the *Internal attributes* panel of the user details. Without any `admin` policy,
every administrator reads them.

#### Self-service enrollment of application specific passwords needs `serviceid_list` (3.14.0)

- **Affects you if:** you have `user` policies, and users enroll application specific password tokens.
- **Do after the update:** grant `serviceid_list` together with `enrollAPPLSPEC`.

The enrollment offers the service IDs of the server. Users read them through `GET /serviceid/` if a `user` policy
grants `serviceid_list`. Without it, the WebUI reports that the service IDs are not available. Without any `user`
policy, every self-service user reads the names and descriptions of the service IDs. Only administrators define,
change and delete service IDs.

#### The health panels of the dashboard need `configread` (3.14.1)

- **Affects you if:** you have `admin` policies.
- **Do after the update:** grant `configread` to the administrators who use the panels *Certificate Health*,
  *Resolver Timing* and *Notification Delivery*.

The dashboard of the new WebUI has these panels. Their endpoints `GET /system/health/...` check the admin action
`configread`, and the WebUI shows the panels only to administrators with this action.

#### `user` and `resolver` of a `userlist` policy limit the user list (3.14.0)

- **Affects you if:** an `admin` policy with `userlist` names users or resolvers.
- **Do:** if `user` holds the login name of the administrator, move it to `adminuser`.

The administrator sees only the users and resolvers that these fields name. The fields name the users in the list,
not the administrator. With the login name of the administrator in `user`, the administrator sees only the user with
that name. With `adminuser` empty, such a policy applies to every administrator.

#### An `auditlog` policy that names users or resolvers grants no realm (3.14.0)

- **Affects you if:** an `admin` policy with `auditlog` names users or resolvers.
- **Do:** to keep the audit entries visible, grant the realms in a policy without users and resolvers. Move the login
  name of an administrator from `user` to `adminuser`.

The audit log can only be limited by realm. Such a policy showed all entries of its realms, or of every realm. Now
the administrator sees only their own entries, unless another policy grants realms.

#### The audit log download holds the realms that both audit policies grant (3.14.1)

- **Affects you if:** an `admin` policy grants `auditlog_download`.
- **Do:** grant `auditlog_download` together with an `auditlog` policy for the same realms.

`GET /audit/<file>.csv` holds the entries of the realms that both `auditlog_download` and `auditlog` grant, and the
entries that the administrator caused. Before, only the realms of the `auditlog` policies limited the download. Without
such a realm, the download held every entry. An administrator with `auditlog_download` but no matching `auditlog`
policy now downloads only their own entries. A `realm` parameter filters within the granted realms. Nothing changes
without admin policies.

#### `hide_tokeninfo` and `hide_audit_columns` with realms, resolvers or users apply in every list (3.14.1)

- **Affects you if:** one of these policies names realms, resolvers or users.
- **Do:** nothing. Administrators with such a policy see fewer token info entries and audit columns.

Such a policy hides its token info keys for the tokens whose owner or token realm it names. It hides its audit columns
for the entries of the users and realms it names. This also applies to the token list, the container list and the
audit log without a filter. Before, these lists showed everything unless a filter named a user of the policy.
Policies without realm, resolver and user work as before.

#### A realm-restricted administrator sees the users of every granted realm (3.14.0)

- **Affects you if:** an administrator holds `userlist` for more than one realm.
- **Do:** make sure that the `userlist` policies grant only the realms that you intend.

`GET /user/` without `realm` returned the users of one realm only: the first realm of the first `userlist` policy
that matched. Now it returns the users of every realm that the policies grant.

#### Excluded resolvers in policies apply (3.14.0)

- **Affects you if:** a policy excludes a resolver with `!` or `-` in front of its name, for example `*, !ldap`.
- **Do:** check these policies. They now apply to fewer users.

The policy match ignored the excluded resolver, so the policy applied to it. Now the match leaves the resolver out,
as it always did for excluded realms and users.

#### Policies with `check_all_resolvers` match only users that one of their resolvers contains (3.14.1)

- **Affects you if:** a policy has `check_all_resolvers`.
- **Do:** make sure that the resolvers of these policies answer.

As documented, such a policy applies to a user only if one of its resolvers contains the user. This is the resolver that
found the user, or a resolver of the realm with a lower priority. Before, the policy applied if the realm of the user
held one of its resolvers. To check this, privacyIDEA asks the named resolvers that rank below the resolver of the user.
If one of them does not answer, the request fails, and the log names the policy and the resolver.

#### Policies that name users apply to tokens and containers in more than one realm (3.14.1)

- **Affects you if:** an `admin`, `change_pin_on_first_use` or `change_pin_every` policy names users without a realm,
  or with `*`, regular expressions or case-insensitive names.
- **Do:** check these policies. They now apply to more tokens and containers.

For a token or container in more than one realm, such a policy matches the owner by the rules for a token in one realm.
A policy without a realm matches the owner in every realm. `*`, regular expressions and case-insensitive user
names match the owner as well. The user still matches only together with the realm of the user.

#### Resolvers and realms are configured within the realms of the admin policy (3.14.1)

- **Affects you if:** an `admin` policy grants `resolverread`, `resolverwrite` or `resolverdelete` for named realms or
  resolvers.
- **Do after the update:** find the administrators who manage shared resolvers or the default realm. Grant them the
  actions for all realms that are involved, or in a policy without `realm` and `resolver`.

The realms and resolvers of the policy now also decide which resolvers and realms the administrator configures:

- `resolverread` lists the resolvers of the realms of the policy, the resolvers that the policy names, and the
  resolvers in no realm.
- To change, test or delete a resolver, the administrator needs the action for every realm that holds the resolver.
- To change or delete a realm, the administrator needs the action for every resolver of the realm, before and after
  the change. A resolver of a realm outside the policy can not be added. A new resolver, or a resolver in no realm,
  can be added.
- To set or remove the default realm, the administrator needs the action for the whole current and the whole new
  default realm. This policy must not name a resolver or a user. The same applies when a realm becomes the default realm
  because it is the only realm.

Apart from the default realm, the `user` field does not limit these actions. `*` names no realm, and `*, !realm_b`
names every realm except `realm_b`. The WebUI still offers the actions and shows the error of the server. Nothing
changes without `admin` policies, or for policies without realm and resolver.

#### Boolean policy actions with a false value are stored as excluded actions (3.14.1)

- **Affects you if:** a policy holds a boolean action with a value other than `true` or `1`, for example
  `policywrite=false` or `triggerchallenge=hotp`.
- **Do after the update:** check each policy that the schema update names. Exclude the actions that you want to
  disable, for example `-policywrite`.

A boolean action with the value `false` (in any case) or `0` is now stored as the excluded action, for example
`-policywrite`. This applies to the WebUI, the API, `pi-manage` and the policy import. A policy template in the WebUI
leaves out the actions that it sets to `false`.

The schema update removes the value of each stored boolean action whose value is not `true`, `True`, `TRUE` or `1`.
It also removes the earlier copies of an action that a policy holds more than once. **The policies grant the same
rights as before.** The schema update prints a warning for each policy that it changes.

A container policy with `disable_client_token_deletion` set to `false` or `0` is the exception. It becomes
`-disable_client_token_deletion`, because the authenticator app reads the action as disabled. For the other container
client actions, the app then offers the container rollover and the unregistration as the server allows them. Boolean
actions of token types that privacyIDEA does not ship keep their value until the policy is saved again.

#### A policy without actions applies to every action only in the `admin`, `user` and `container` scopes (3.14.1)

- **Affects you if:** a policy in another scope has no actions.
- **Do:** give such a policy its actions, or delete it.

In the other scopes, a policy without actions has no effect. Before, such a policy made authentication, login and
token enrollment requests fail. In the `webui` scope, it turned on every WebUI setting that can be on or off.

#### Request header, environment and request data conditions apply on the WebUI start page and the push poll (3.14.1)

- **Affects you if:** a `webui` policy or a push poll policy, such as `push_allow_polling`, has a header, environment
  or request data condition.
- **Do before the update:** check these policies.

Before, these conditions had no data on the WebUI start page. Header and environment conditions also had no data on
the poll of the smartphone (`GET /ttype/push`). *Handle Missing Data* decided the result: the policy applied to every
request (*Condition is true*) or to none (*Condition is false*). With *Raise an error*, the start page and each poll
failed with 403.

Now these conditions read the data of the request. The new WebUI reads its policies with a request to `/config` and
adds the parameters of its start URL to this request.

#### Container conditions of PIN change and resync policies check the container of the token (3.14.1)

- **Affects you if:** `change_pin_on_first_use`, `change_pin_every`, `change_pin_via_validate` or
  `resync_via_multichallenge` has a `container` or `container_info` condition.
- **Do before the update:** check these policies.

These conditions now compare the container that holds the token. Before, they never got container data, so
*Handle Missing Data* alone decided whether the policy applied. For a token without a container, the option still
decides. A policy with *Condition is true* no longer applies to tokens in a container that does not match the
condition. A policy with *Condition is false* now applies to tokens in a container that matches the condition.

#### `date_within_last` does not match a date in the future (3.14.1)

- **Affects you if:** a policy or an event handler has a `date_within_last` or `!date_within_last` condition.
- **Do before the update:** look for values that can lie in the future, for example the token info
  `validity_period_end`. Replace each negative duration.

A date in the future is not within the past duration. Before, `date_within_last` matched every date in the future,
and `!date_within_last` matched none. A negative duration such as `-1d` is now an error. A policy with such a
condition fails the request with "Invalid comparison". An event handler condition with it is always false.

#### Policy nodes and user agents that can never match are refused when you save a policy (3.14.1)

- **Affects you if:** a policy node holds `*`, `!` or `-`, or a user agent holds a version, a space, `*` or `!`.
- **Do:** correct these values before you export your policies, or in the file before you import it.

A node is compared exactly with the node name. A user agent must be a plain name like `privacyidea-cp`. Such values
never matched, and now the server refuses them. To apply a policy on every node, leave the node field empty.

A stored policy with such a value keeps working: the other entries of the list still match. For example,
`pinode: node1, -node2` still applies on *node1*. You can save, copy or import such a policy only after you correct
the value.

#### Realm-scoped WebAuthn and passkey policies apply to their realm only (3.14.1)

- **Affects you if:** a policy for a realm, resolver or user holds `webauthn_user_verification_requirement`,
  `webauthn_authenticator_attestation_form`, `webauthn_authenticator_attestation_level`, or a challenge text of
  WebAuthn or passkey.
- **Do:** check these policies if they are meant for every user.

These actions match the policy with the user again, as documented. Users of other realms get their own policy or the
default.

#### The `remote_user` WebUI policy matches the account that REMOTE_USER names (3.14.1)

- **Affects you if:** a `remote_user` policy names a realm, resolver or user.
- **Do:** check the `remote_user` policies that name a resolver.

The realm, resolver and user of the policy apply to the REMOTE_USER account. A policy for one resolver admits only the
users of that resolver. A login request whose `realm` names another realm than REMOTE_USER does not use the
REMOTE_USER login.

#### Users assign only tokens and containers of their own realm (3.14.1)

- **Affects you if:** users assign tokens or containers themselves (`assign`, `container_assign_user`).
- **Do:** put spare tokens into no realm, or into the realm of the users.

As documented, the token or the container must be in the realm of the user or in no realm. Users can not assign tokens
from a pool in a separate realm.

#### Self-registration is deprecated (3.14.0)

- **Affects you if:** you have a policy in the `register` scope.
- **Do:** if you need self-registration, tell us before a future version removes it.

Registration works as before. If the feature is configured, `GET` and `POST /register` write a warning to the log,
once per process. Search the log for `is deprecated`. The new WebUI does not offer registration. Set `requiredemail`,
so that the registration mail goes only to addresses that you accept.

### 3.2 Tokens and authentication

#### Passkey and WebAuthn logins apply the token limits (3.14.1)

- **Affects you if:** you have passkey or WebAuthn tokens.
- **Do before the update:** check these tokens for a validity period or an authentication limit. These limits apply
  from 3.14.1 on.

A login with a credential ID is now checked like every other authentication. The server refuses a token that is
revoked or disabled, outside its validity period, over its fail counter or past its authentication limits. A
successful login increases the authentication counters of the token.

#### A passkey login without a username needs a unique login name (3.14.1)

- **Affects you if:** users log in with a passkey and no username, and a realm holds a login name in more than one
  resolver.
- **Do:** nothing.

Only the user that the resolver order of the realm finds first can log in this way. A passkey of another user with
this login name is refused. The authentication log records `LOGIN_NAME_NOT_UNIQUE`. Logins that name the user,
password logins and REMOTE_USER do not change.

#### Authentication by serial or FIDO2 credential applies the policies of the token owner (3.14.1)

- **Affects you if:** clients authenticate at `/validate/check` by `serial` or FIDO2 `credential_id`, and policies for
  the actions below name realms, resolvers or users.
- **Do:** check these policies. They now also apply to such requests.

The server matches such a request for the owner of the token, like a request that names the user:

- By serial: `last_auth`, `disabled_token_types`, `increase_failcounter_on_challenge`, `challenge_text`, `push_wait`,
  the WebAuthn and passkey settings, `auth_max_fail` and `auth_max_success`. The two limits also apply to the answer to
  a challenge and to `otponly`.
- By FIDO2 credential: `last_auth`, `auth_max_fail` and `auth_max_success`. The limits also apply to the registration
  that completes an enrollment via multichallenge. A passkey login at `/auth` without a username also matches
  `last_auth` for the owner.

#### A user store error fails the request (3.14.1)

- **Affects you if:** you use `passOnNoUser`, a realm holds more than one resolver, or you use HTTP resolvers.
- **Do before the update:** make sure that HTTP resolvers answer an unknown user with `404` or with a successful
  response that matches *Special Error Handling*.

If the SQL, LDAP, Keycloak, HTTP or Entra ID user store returns an error for the lookup of a login name, the request
fails. The user no longer counts as unknown. `passOnNoUser` does not apply, and the realm does not go on with its next
resolver. The authentication log records `USER_STORE_UNAVAILABLE`. During an outage of a user store, clients get an
error.

An HTTP resolver treats only a `404`, or a successful response that matches its *Special Error Handling*, as an
unknown user. Before, every error status meant an unknown user. Now every other error status, and every response that
is not JSON, is an error.

#### The validity time of Email and SMS OTP values applies to every login (3.14.1)

- **Affects you if:** you use Email or SMS tokens.
- **Do before the update:** make sure that `email.validtime` and `sms.providerTimeout` give users enough time to log
  in. Check the clients that send OTP PIN and OTP value in one request, for example RADIUS.

The server refuses a sent value after its validity time. This also applies when the client sends OTP PIN and OTP value
together, or the OTP value alone (`otponly`), without `transaction_id`. A refused value counts as a wrong value and
increases the fail counter. The validity time starts before the server sends the value, so it includes the time of the
SMTP server or the SMS gateway.

Values from `emailautosend` or `smsautosend`, and values for the verification of an enrollment, have no time limit.
They stay valid until somebody uses them, or until the server sends or accepts a newer value.

#### `/validate/check` with `otponly=1` needs a session and checks the token (3.14.1)

- **Affects you if:** administrators use *test OTP* in the WebUI, or scripts or other clients send `otponly=1`.
- **Do:** change such a script to send the OTP PIN with the OTP value and without `otponly`. Or let it send the
  session token of an administrator with `tokenlist` for the token.

The request needs a session token from `/auth` in the `PI-Authorization` or `Authorization` header. The session must
belong to an administrator with the admin right `tokenlist` for the token, or to the owner of the token. The server
refuses other requests with `otponly`. The WebUI sends the session token.

The server refuses a token that is disabled, expired, revoked or past its fail counter. A wrong value increases the
fail counter of the token.

#### A RADIUS token needs a RADIUS user (3.14.0)

- **Affects you if:** scripts enroll RADIUS tokens, or you have RADIUS tokens with an empty RADIUS user.
- **Do:** add the RADIUS user to the scripts that enroll RADIUS tokens.

`POST /token/init` refuses a RADIUS token with an empty `radius.user` with ERR905. Before, it stored the empty value.
A RADIUS token that has an empty RADIUS user keeps sending an empty user name to the RADIUS server, as before. To give
such a token a RADIUS user, send `radius.user` with `POST /token/set`.

#### SSH key tokens hold a checksum (3.14.0)

- **Affects you if:** you have SSH key tokens.
- **Do:** run the schema update. Enroll again the tokens that the schema update skips.

SSH key tokens now store a checksum of the key data (serial, key type, public key and comment) in the encrypted OTP key
field. The server checks it each time a client fetches the public key, for example `privacyidea-authorizedkeys`. If
the data in the database does not match the checksum, the server refuses the key.

The schema update computes the checksum for every SSH key token. Without the schema update, SSH key tokens refuse
their keys. The schema update skips tokens whose encrypted key can not be decrypted. To change the SSH key, enroll the
token again, because the token info endpoint no longer changes it.

#### The u2f token type is removed (3.14.0, changed in 3.14.1)

- **Affects you if:** you have u2f tokens, policies with `enrollU2F` or `u2f_*` actions, or configuration exports
  that hold them.
- **Do after the update:**
  - Check the policies that the schema update names in a warning.
  - When you are ready, delete the u2f tokens with `pi-tokenjanitor deprecated delete u2f`.
  - Import old exports with `pi-manage config import --skip-invalid`.

The schema update changes u2f tokens to the type `deprecated` and disables them. It keeps the old type in
`tokeninfo['original_tokentype']`, and its output warns with the number of tokens. The tokens stay in the token list,
but they can not authenticate.

The schema update also removes `enrollU2F` and the actions that start with `u2f_` from the policies. It deletes a
policy that holds only these actions, together with its conditions and its description. It prints the names of the
changed and the deleted policies.

The update keeps such a policy if it is the last active policy of the `admin` or the `user` scope. Without an active
policy, everybody gets all rights of that scope. The update names these policies in a warning. They allow
nothing. Replace their actions, or add another active policy to the scope and then delete them. Do not save them
without actions, because a policy without actions allows every action of its scope.

`--skip-invalid` drops these actions and skips a policy that holds only these actions. Without the option, the import
refuses such a policy.

#### Tokens of a deleted resolver are listed on every node (3.14.0, changed in 3.14.1)

- **Affects you if:** you deleted resolvers, or removed them from all realms, while they still owned tokens, or you
  have tokens whose user assignment names no resolver.
- **Do after the update:** unassign or delete these tokens. The token janitors find them as orphaned, for example
  with `pi-tokenjanitor find --orphaned true list`.

The token lists left out a token whose owner belongs to a resolver in no realm, or whose user assignment names no
resolver. The WebUI, the API and the token janitors did not find it, so nobody deleted it, but the subscription
counted it. Such a token belongs to no node, so it is now listed on every node. Its user shows as
`**resolver error**`.

#### Two-step enrollment applies to every token rollover (3.14.1)

- **Affects you if:** a `hotp_2step` or `totp_2step` policy has the value `force`.
- **Do:** make sure that scripts that roll over such tokens send the client component in a second request.

Every rollover of an enrolled token now uses the two-step enrollment, with or without the `rollover` parameter. The
policy is matched for the owner of the token. Before, it applied only with the `rollover` parameter. Also, an admin
policy for a realm, resolver or user did not apply to a request that names only the serial of the token. The rollover
in the WebUI sends such a request, so under such a policy it now uses the two-step enrollment as well.

The server refuses a request that sends its own key (`otpkey`) for such a token, as for a new token.

#### A push token that can not create a challenge is left out (3.14.1)

- **Affects you if:** you use push tokens.
- **Do:** nothing.

If no push gateway is configured for the token, or the push gateway fails while polling is not allowed, the token gets
no challenge. It is no longer part of `multi_challenge` and of the serials in the audit log. If it was the only token
to trigger a challenge, the response is `authentication` `REJECT` instead of `CHALLENGE`, also in the audit log. Event
handler conditions on `result_authentication` match accordingly.

With `push_wait`, such a request no longer waits. It fails at once with the message "The PIN was correct, but the push
notification was not sent." The fail counter of the push token increases only with
`increase_failcounter_on_challenge`.

#### `/validate/triggerchallenge` checks the token state before it raises the fail counter (3.14.1)

- **Affects you if:** clients use `/validate/triggerchallenge`, or you use `increase_failcounter_on_challenge`.
- **Do:** nothing.

Like `/validate/check`, the trigger challenges only the tokens that pass the usual checks. A token must be below its
fail counter, within its authentication counters and validity period, and fully enrolled. The trigger also applies
`disabled_token_types`. With `increase_failcounter_on_challenge`, only the fail counter of these tokens increases. A
fail counter whose reset timeout (`failcounter_clear_timeout`) is over is reset before the check.

Why a token was refused, for example "Failcounter exceeded", is the response message only if no token got a
challenge. It is no longer in `detail.messages` next to the challenge texts. At `/validate/check` and `/auth`, this
also applies to a token whose fail counter the trigger itself raised to the maximum.

#### An authentication answered with an error is audited as a failure (3.14.1)

- **Affects you if:** you use `auth_max_success` or `auth_max_fail`, or you evaluate the audit log.
- **Do:** nothing.

Some authentications succeed or trigger a challenge but then get an error response, for example because a policy refuses
them. The audit log records them with `success` false and `authentication` `REJECT`. The authentication that starts an
enrollment via multichallenge is recorded as a challenge. `auth_max_success` and `auth_max_fail` count these requests
accordingly: as a failed authentication, and the start of the enrollment not as a successful one.

#### The challenge step of a login at `/auth` does not count for `auth_max_fail` (3.14.0)

- **Affects you if:** you use `auth_max_fail`, and users log in to the WebUI with challenge-response tokens.
- **Do:** nothing.

With `login_mode=privacyIDEA`, the first step of such a login checks the password and triggers the challenge. Before,
`auth_max_fail` counted this step as a failed authentication. Now it does not count, as at `/validate/check`. The
audit log records the `/auth` entries with `authentication` `CHALLENGE`, `ACCEPT` or `REJECT`.

#### Tokens from a container template are checked with their own user and realm (3.14.1)

- **Affects you if:** administrators with admin policies for certain realms create containers from templates.
- **Do after the update:** check the container templates that these administrators use. Select *Assign to user* for
  the tokens that they need to create.

When a container is created from a template, the server checks the enrollment policies of each token as for a single
token enrollment. It checks them against the user and the realm that the token gets, not against the user of the
container. A token
without *Assign to user* gets neither a user nor a realm. So an administrator whose admin policies name certain realms
can not create it from a template.

Such a token is skipped, and the container is created with the remaining tokens. The response of
`POST /container/init` lists each skipped token in `tokens_not_created`, and the WebUI shows them.

#### Application specific password tokens need a defined service ID (3.14.0)

- **Affects you if:** scripts, token event handlers or container templates enroll application specific password
  tokens.
- **Do:** make sure that the service IDs they use are defined under *Config -> Service IDs*. Check your container
  templates.

`POST /token/init` with `type=applspec` now looks up the `service_id` among the defined service IDs, case-insensitive.
If it does not exist, the server refuses the request with a 400. Before, it stored any name, and such a token never
authenticated.

An event handler with an undefined service ID enrolls no token and records the failure in its audit entry. A container
template with an undefined service ID creates the container without that token, and `tokens_not_created` names it. A
rollover also needs a defined service ID. Tokens keep the service ID that they have.

#### The first synchronization of a smartphone container takes over only related tokens (3.14.0)

- **Affects you if:** you use the policy `initially_add_tokens_to_container`.
- **Do:** put the tokens that you prepare in advance and the container into a realm.

On the first synchronization, the server adds the tokens that the client reports, with these limits:

- A token of a user is added only if the user owns the container.
- A token without a user is added only if it shares a realm with the container.
- A token without user and realm, or a token in another container, is not added. To move a container with all its
  tokens to a new device, use the container rollover.

#### Only administrators mark a token as lost (3.14.0)

- **Affects you if:** users mark tokens as lost, or a token event handler is bound to `token_lost`.
- **Do:** nothing.

`POST /token/lost` now follows its `losttoken` action, which is an admin action. A token event handler on
`token_lost` runs only for requests of an administrator.

### 3.3 PINs

#### The PIN change via `/validate/check` has the checks of every authentication (3.14.1)

- **Affects you if:** you use `change_pin_via_validate`.
- **Do:** nothing.

Each of the two challenges of the PIN change can be answered once, and only while it is valid. The token must be
usable, that is not disabled, below its fail counter and within its validity period. The authorization policies, for
example `tokentype`, must allow the token.

A confirmation that does not match the new PIN counts as a failed authentication and ends the PIN change. The PIN
change starts again with the next login. The login that starts the PIN change does not count for `count_auth` and
`count_auth_success`. The confirmation of the new PIN counts.

#### The PIN policies check the PIN that the server stores (3.14.1)

- **Affects you if:** you use `otp_pin_minlength`, `otp_pin_maxlength` or `otp_pin_contents`.
- **Do:** nothing.

The policies check `pin` for `/token/init`, `/token/assign` and container templates, and `otppin` for
`/token/setpin`. They also check a PIN that a request sends together with `rollover` or `verify`. The PIN policies of
a token type apply whatever the case of the `type` parameter. The server refuses a request whose PIN does not match
the policies.

#### Simple pass tokens under `otppin=none` check their PIN (3.14.1)

- **Affects you if:** users of simple pass tokens fall under an `otppin=none` policy.
- **Do:** make sure that these users log in with the PIN of their token.

`otppin=none` drops the PIN in front of an OTP value. A simple pass token has no OTP value, and its PIN is the whole
password. So the server checks its PIN as usual. Simple pass tokens with `otppin=userstore` work as before.

#### `POST /container/init` with a template returns only the PIN of the template (3.14.1)

- **Affects you if:** scripts read the PINs from the response of `POST /container/init` under `otp_pin_random`.
- **Do:** give random PINs to the users with a PIN handler (policy `pinhandling`).

A PIN that the server generates is not part of the `init_params` of a token, as with `/token/init`.

#### The base PIN handler logs only the token and the user (3.14.1)

- **Affects you if:** you use `otp_pin_random` without a `pinhandling` policy, or with the base PIN handler.
- **Do:** to give random PINs to users, use a PIN handler class that sends them (policy `pinhandling`).

`privacyidea.lib.pinhandling.base.PinHandler` logs the token and the user for which the server set a random PIN.

#### PIN handler classes get the token type in lower case (3.14.1)

- **Affects you if:** a custom PIN handler class reads the token type.
- **Do:** nothing, if the class compares the type in lower case.

`PinHandler.send` gets the type as privacyIDEA stores it, for example `hotp`. Before, it got the type as the request
sent it, for example `HOTP`. If a request for a new token has no type, the PIN handler gets `hotp`.

### 3.4 Event handlers

#### An error of an event handler fails the request only with *Abort on error* (3.14.0, changed in 3.14.1)

- **Affects you if:** you have event handlers.
- **Do after the update:**
  - Review your handlers under *Config -> Events*. Decide for each one if a failure must fail the request.
  - Check the audit entries of your request and response manglers.

Before, an error of any handler failed the request. Now a handler that fails writes `success=False` and the reason to
the `info` column of its audit entry. The other handlers run, and the request goes on. The new option
*Abort on error* (`abort_on_error`) fails the request instead.

The schema update sets *Abort on error* for these handlers:

- Federation handlers. Without the remote response, the client gets the local response as if the remote server sent
  it.
- Request manglers and response manglers. Without them, the endpoint uses the values that the client sent, and the
  client gets the response without the change.
- Script handlers that are configured to raise an error.

New request mangler and response mangler bindings start with the option set. Clear it for a handler whose failure must
not fail the request.

A handler also counts as failed if it can not do what it is configured for. Examples:

- a notification without a recipient
- a script that exits with an error
- a webhook that gets an HTTP error
- a token action with an option that does not exist, for example a token group

A handler whose conditions can not be evaluated, for example because the user store does not answer, fails as well. A
mangler with an error in its configuration never changed anything, and
now it fails every request that it matches.

A post-event handler runs after the endpoint did its work. If it fails the request, the client gets an error for an
operation that partly happened.

#### Request mangler with *reset user* (3.14.0, changed in 3.14.1)

- **Affects you if:** a request mangler uses *reset user*.
- **Do:** review these handlers.

*Reset user* now also works when the handler sets a fixed value, without a match parameter. A pre-event handler on
`/validate/check` that sets `realm` with *reset user* authenticates the user in that realm, with its policies and
tokens.

A login name of the form `user@realm` is split by the Split@Sign setting, and the user is looked up in that realm.
This does not apply if the client sent a `realm` parameter or a handler set one. A login name without a realm stays in
the realm of the original request.

#### Tags in event handler texts render differently (3.14.0, changed in 3.14.1)

- **Affects you if:** handler texts use tags, or a webhook uses *replace*.
- **Do:** check these texts and the webhook data.

- `{ua_browser}` is the name of the client application, for example `privacyidea-cp`. It rendered `None` before.
- A tag without a value renders an empty string, not `None`. An example is `{serial}` for an event without a token.
- In *set description* and *set tokeninfo* of the token handler, `{username}` and `{userrealm}` name the owner of the
  token. `{admin}` and `{realm}` name the administrator, so `{realm}` is empty for `/validate/check`. `{username}`
  and `{realm}` rendered `N/A` before.
- With *replace*, the webhook handler sends the complete JSON data. Before, it sent only the first key of each level. A
  stored *replace* value of `False` no longer enables the replacement.
- The webhook tags `{serial}` and `{token_serial}` name the token of the event, from the request, the response or the
  audit entry. They are empty if the event has no token.
- The value of the custom user attributes handler, and the description and info values of the container handler,
  render tags as well. Write `{{` and `}}` for a literal brace.

#### Event conditions `challenge_session` and `challenge_expired` need a challenge (3.14.1)

- **Affects you if:** you have event handlers.
- **Do:** if a definition uses `challenge_session` or `challenge_expired` to act on a declined push in `push_wait`
  mode, use the condition `result_authentication` `DECLINED` instead.

A definition with `challenge_session` or `challenge_expired` fires only if exactly one challenge of the token matches
the request. Without a challenge, it does not fire. Examples are a normal successful login, and a successful answer,
which removes the challenge.

Definitions without these conditions now also fire if more than one open challenge of the token matches the request.
Before, they did not fire in this case.

#### The `rollout_state` of enrolled tokens is `enrolled` (3.14.0)

- **Affects you if:** event handlers have a `rollout_state` condition, or scripts compare `rollout_state` with an empty
  string.
- **Do:** add a `tokentype` condition to the handlers for particular token types. Update the scripts so that they
  accept `enrolled`.

The schema update sets the `rollout_state` of every token with an empty or `NULL` value to `enrolled`. Before, only
push, WebAuthn, passkey and certificate tokens got `enrolled`.

For the `rollout_state` condition, an empty string and `enrolled` mean the same. So a condition `enrolled` now also
matches HOTP, TOTP, SMS, Email and all other tokens. A condition with an empty string also matches push, WebAuthn,
passkey and certificate tokens. To find these handlers, look for `rollout_state` in the conditions under
*Config -> Events*.

### 3.5 HTTP API

- **Affects you if:** scripts, integrations or monitoring call these endpoints.
- **Do:** update them as the table says.

| Endpoint | Change | Version |
|---|---|---|
| `GET /token/challenges/`, `GET /token/challenges/<serial>`, `GET /token/challenges/user` | No `id` field. Use `transaction_id` | 3.14.0 |
| `/healthz`, `/healthz/livez`, `/healthz/readyz`, `/healthz/startupz` | No `version` and `versionnumber`. Read the version from an authenticated endpoint | 3.14.0 |
| `GET /user/` with `resolver` | Only the users of that resolver. With `realm`, only within the realm, and empty if the resolver is not in the realm | 3.14.0 |
| `GET /container/` with `realm` and without `user` | The containers of all users of the realm. Before, an empty list. A `user` that does not resolve gets a 400 | 3.14.0 |
| `GET /token/` with `resolver` or `userid` | The filters apply. Before, all tokens. `resolver` is case-insensitive, and `*` is a wildcard in both. Tokens without an owner do not match | 3.14.0 |
| `GET /token/?realm=<name>` for a realm that does not exist | An empty list, not a 404 | 3.14.0 |
| `POST /container/<serial>/realms` | The status of each realm is in `result.value.realms.<realm>`. `deleted` stays where it was | 3.14.0 |
| `POST /container/init` with a template | `tokens_not_created` lists the tokens of the template that the server did not create | 3.14.1 |
| `POST /auth`, failed login | The message is `Authentication failed.`. The error id `4031` and the status `401` stay | 3.14.0 |
| `GET /machine/` | `hostname` is always a list | 3.14.0 |
| `POST /token/lost` | Administrators only | 3.14.0 |
| `POST /defaultrealm/<realm>`, `DELETE /realm/<realm>` | The realm name is read as `POST /realm/<realm>` stores it: lowercase, with `-` for each space. `DELETE /realm/<realm>` accepts any spelling of the name | 3.14.1 |
| `POST /defaultrealm/` with an empty realm name | A 400. Use `DELETE /defaultrealm` | 3.14.1 |

#### Searches use `*` as the only wildcard (3.14.0)

- **Affects you if:** saved filters, scripts or integrations use `%` or `_` as wildcards in audit, token or SQL user
  searches.
- **Do:** replace `%` with `*`, for example `serial="OATH*"` or `action="*/token/init"`.

`%` and `_` now match only themselves. A search that uses them as wildcards returns no result.

#### Secrets in configuration responses are censored (3.14.0, changed in 3.14.1)

- **Affects you if:** tools read or write secrets through `/caconnector`, `/machineresolver`, `/radiusserver`,
  `/smsgateway` or `/smtpserver`.
- **Do:** keep these secrets in the tools themselves. To change the server or the port of an SMTP or RADIUS server,
  send the password or the secret again, also in the WebUI.

The responses hold the placeholder `__CENSORED__` instead of a password or secret. A PUT or POST with the placeholder
keeps the stored value. To set a new secret, send the new value.

For SMTP and RADIUS servers, the placeholder keeps the stored value only if the request keeps the server and the port.
For SMTP, it must also keep the user name and the TLS setting. Otherwise, the request fails. This applies to saving a
server, to the test request and to `pi-manage config import`.

The schema update also encrypts the options of an SMS gateway whose name contains `PASSWORD` or `SECRET`. A node of
the old version sends the encrypted value to the SMS gateway, so do not let it serve the updated database.

#### `/validate/samlcheck` is removed (3.14.0)

- **Affects you if:** clients use `/validate/samlcheck`, or you set `ReturnSamlAttributes` or
  `ReturnSamlAttributesOnFail`.
- **Do:** switch these clients to `/validate/check` with the policies `add_user_in_response` and
  `add_resolver_in_response`.

The user attributes are then in `detail.user`, and the resolver and the realm in `detail.user-resolver` and
`detail.user-realm`. The two configuration options are removed, and stored values have no effect.

`ReturnSamlAttributesOnFail` has no replacement, because `add_user_in_response` applies only to a successful
authentication. An application that needs the user attributes after a failed login must look up the user through the
user API.

#### Token info that a token type maintains is read-only for the token info endpoints (3.14.0)

- **Affects you if:** scripts call `POST` or `DELETE /token/info/<serial>/<key>`.
- **Do:** set the changeable entries with `POST /token/set`.

Each token type declares the entries that it maintains, for example the public key of a passkey or the server of a
RADIUS token. The token info endpoints answer with a 403 for these entries. Free-form entries, and per-token switches
that privacyIDEA never writes itself, work as before. Examples of such switches are `multichallenge` of an indexed
secret token and `polling_allowed` of a push token.

`POST /token/set` and its `set` action set these entries:

- `count_auth_max`, `count_auth_success_max`, `hashlib`, `validity_period_start` and `validity_period_end`, as
  before.
- The entries that a token type declares as settable, under their own name. Examples are `timeWindow` and `timeStep`
  of a TOTP token, `phone` of an SMS token, `email` of an Email token, `remote.user` and `radius.server`. Only a token
  of a type that declares the entry gets it.
- The offline refill token of an HOTP, WebAuthn or passkey token. You can delete it, but you can not set it to a value.

Entries that hold what a token authenticates with have no way to be set. Examples are TANs, the public id of a
Yubikey, the answers of a questionnaire token and the public key of an SSH key token. They change with a
new enrollment or a rollover. A repeated `POST /token/init` for an enrolled token no longer rewrites its
`<tokentype>.*` entries.

`GET /token/` reports these entries for each token as `readonly_info_keys`, `undeletable_info_keys` and
`settable_info_keys`. The token event handler and the command line tools still write every entry.

#### A policy update keeps the fields that the request does not send (3.14.1)

- **Affects you if:** scripts update policies with `POST /policy/<name>` or `pi-manage config policy create`.
- **Do:** send the value of each field that the script must reset.

A disabled policy stays disabled, and its priority and description stay. Before, these fields went back to their
defaults, and the policy was active again.

#### Event definitions are checked when they are saved (3.14.0)

- **Affects you if:** scripts or integrations save event definitions with `POST /event`.
- **Do:** to clear the conditions, send an empty dictionary as `conditions`. To clear the options, send
  `clear_options=True`.

`POST /event` checks `action` and `position` against the handler module. It refuses other values with an error that
lists the valid values. An update keeps the conditions and the options that the request does not send, and it stores a
changed `name`. The WebUI offers only valid values. `pi-manage config import` does not change.

#### The version can be hidden from unauthenticated requests (3.14.0)

- **Affects you if:** you want to hide the version of privacyIDEA.
- **Do:** set the `hide_version` action in the `hardening` scope.

With this policy, the responses to unauthenticated requests hold no `version` or `versionnumber`, for example the
responses of `/validate/check`. Authenticated requests and the WebUI still get the version. To decide what a server
supports, a client must use the capability flags of the response, not the version.

### 3.6 Command line tools

These changes affect custom scripts and custom cron jobs. The default cron jobs of the Ubuntu packages are not
affected.

#### The token janitors read `1`, `yes` and `on` as true (3.14.0, changed in 3.14.1)

- **Affects you if:** scripts or cron jobs call `privacyidea-token-janitor` or `pi-tokenjanitor`.
- **Do before the update:** check the values of `--active`, `--assigned` and `--orphaned` in these scripts.

- `privacyidea-token-janitor` read `1`, `yes` and `on` as false for `--active` and `--assigned`. Now they mean true.
  For example, `find --assigned 1 --orphaned 1 --action delete` selected no token, and now it deletes the assigned
  orphaned tokens.
- Both token janitors accept `true` and `false`, `1` and `0`, `yes` and `no`, and `on` and `off` for these options.
  They refuse every other value, also `None`.
- `privacyidea-token-janitor find --orphaned-on-error` is `False` by default. A token whose user lookup fails, for
  example because the LDAP server does not answer, no longer counts as orphaned.
- `update` writes only the OTP key, the OTP length, the description and the encrypted token info of each entry,
  encrypted with the current key. It keeps everything else of the token, also the OTP counter, the fail counter and
  the token kind. The PIN of mOTP tokens and encrypted PINs are not encrypted again, so set them again after a key
  change.
- The banner goes to stderr, so the output of `--action listuser` and `--action export` no longer starts with it.
- `--action export --csv` writes the time step of a TOTP token as a sixth column.
- In the output of `pi-tokenjanitor find ... list`, `realms` is a list.
- `pi-tokenjanitor findcontainer ... set_realm` also reports a realm named `deleted`. Before, it left such a realm
  out.

#### `pi-manage setup create_tables` stops on an existing database (3.14.1)

- **Affects you if:** scripts run `pi-manage setup create_tables`, for example on every start.
- **Do:** run `create_tables` only on an empty database. Update an existing database with `pi-manage db upgrade`.

If the database holds privacyIDEA tables or a schema revision stamp, the command exits with an error and changes
nothing. Before, it created the missing tables and stamped the database with the newest revision. `--force` keeps
that behavior.

#### `pi-manage setup encrypt_enckey -o` creates the file readable only by its owner (3.14.1)

- **Affects you if:** you encrypt the key file with `pi-manage setup encrypt_enckey -o`.
- **Do:** if you run the command as root, change the owner of the new file to the user that privacyIDEA runs as.

A new output file gets the permissions `0600`. Before, it got the default permissions of the system, for example
`0644`. `-o` can not name the key file itself.

#### `pi-manage config export` and `pi-manage config import` (3.14.0)

- **Affects you if:** you export and import the configuration.
- **Do:** after you import an export from 3.13, set the password entries of the global configuration again.

- The export writes the password entries of the global configuration decrypted, like every other secret. The target
  then encrypts them with its own key. An export from 3.13 holds them encrypted with the key of its instance. The
  import stores them in a form that can not be used.
- `--censor` also censors the client secret of a SCIM resolver.
- The import exits with status 1 if it can not import a type of configuration in the file completely. It imports
  each policy on its own, so a refused policy does not stop the next ones.
- `--skip-invalid` drops the policy actions that do not exist, for example the u2f actions. The import then
  does not refuse the policy.

#### `pi-manage config realm delete` (3.14.0, changed in 3.14.1)

- **Affects you if:** scripts delete realms with this command.
- **Do:** pass `--delete-custom-attributes` in scripts. Check the exit status.

The command asks for a confirmation to delete the custom user attributes of the realm. Without a terminal, it ends with
status 1. It also exits with status 1 if the realm does not exist or can not be deleted, for example because it still
holds tokens. Before, it exited with status 0.

#### `pi-manage audit rotate` with watermarks keeps exactly `--lowwatermark` entries (3.14.0)

- **Affects you if:** you rotate the audit log with watermarks.
- **Do:** nothing.

The command counted back from the id of the newest entry. It kept one entry more, and on Galera only a part of the
entries, for example a third with an id increment of 3. On Galera, the audit table now keeps more entries. A negative
`--lowwatermark` is refused.

#### `pi-manage config authcache cleanup` follows the `auth_cache` policies (3.14.0)

- **Affects you if:** a custom cron job runs `pi-manage config authcache cleanup` without `--minutes`.
- **Do:** nothing. To keep the behavior of 3.13, pass `--minutes 480`.

Without `--minutes`, the command now deletes the entries that no active `auth_cache` policy accepts any more. These
are the entries that were not used for longer than the longest idle limit of the active policies. The idle limit of a
policy is its interval, or for a value like `4h/5m` the shorter of the two intervals. If no such policy exists, the
command deletes all entries. Before, it deleted the entries that were not used for 480 minutes. So the entries now
stay longer if the longest idle limit is above 8 hours, and go sooner if it is below. A negative `--minutes` is
refused.

#### `privacyidea-pip-update -f` runs the schema update (3.14.0, changed in 3.14.1)

- **Affects you if:** scripts call `privacyidea-pip-update`.
- **Do:** to skip the schema update, pass `-n`. Check the exit status.

`-f` only skips the confirmation question. `privacyidea-pip-update` ends with the exit code of the step that failed.
Before, it always ended with 0.

#### Scripts that are no longer installed (3.14.0)

- **Affects you if:** you use `reset-privacyidea`, `privacyidea-create-certificate`,
  `privacyidea-export-linotp-counter.py`, `privacyidea-export-privacyidea-counter.py`, `privacyidea-migrate-linotp.py`,
  `privacyidea-sync-owncloud.py`, `creategoogleauthenticator-file` or `getgooglecodes`.
- **Do:** nothing. These scripts did not work with the current dependencies.

### 3.7 Database and audit log

#### The schema update stops on a database without a schema revision stamp (3.14.1)

- **Affects you if:** the `alembic_version` table of your database holds no revision. Versions before 3.10 created
  their tables without a stamp by default, and `pi-manage setup create_tables --no-stamp` does the same.
- **Do before the update:** run `pi-manage db current`. If it shows no revision, stamp the database with the newest
  revision of the version that created its tables.

`privacyidea-schema-upgrade`, which `privacyidea-pip-update` and the Ubuntu packages run, and `pi-manage db upgrade`
stop with an error and leave such a database unchanged. Before, the script stamped such a database with the revision
of 2.0 and ran every migration since 2.0.

For tables that the installed version created with `--no-stamp`, use `pi-manage db stamp head`. The upgrade
documentation lists the revisions of older versions, for example `pi-manage db stamp 5cb310101a1f` for 3.9. Then run
the update again. The option `-s`/`--skipstamp` of both scripts is accepted and has no effect. Set up an empty
database with `pi-manage setup create_tables`.

#### The audit `serial` column holds 200 characters (3.14.0)

- **Affects you if:** you use MySQL or MariaDB, or a separate audit database (`PI_AUDIT_SQL_URI`).
- **Do before the update:**
  - On MySQL and MariaDB, plan the time for the rebuild of `pidea_audit`. To make it shorter, delete old entries first,
    for example with `pi-manage audit rotate --age 365`.
  - On a separate audit database, change the column yourself, before the update or together with it.

An audit entry names every token of a request. Before, three tokens with default serials filled the 40 characters of
the column. The schema update widens the column.

On MySQL and MariaDB, the schema update copies the whole `pidea_audit` table and blocks writes to it while the copy
runs. On local SSD storage, count about 20 seconds for each million entries with a signature. Ten million entries take
about three minutes. Slow or network storage can take several times longer. `--dryrun` shows what `audit rotate`
deletes, and `--chunksize` deletes in batches. PostgreSQL changes only the column definition.

The schema update does not reach a separate audit database. Change the column there:

    ALTER TABLE pidea_audit MODIFY serial VARCHAR(200);              -- MySQL, MariaDB
    ALTER TABLE pidea_audit ALTER COLUMN serial TYPE VARCHAR(200);   -- PostgreSQL

Without this change, privacyIDEA works, but it writes shortened serial lists.

#### Audit entries are always shortened to fit their column (3.14.0)

- **Affects you if:** you did not set `PI_AUDIT_SQL_TRUNCATE = True`, or you set `PI_AUDIT_SQL_COLUMN_LENGTH`.
- **Do:** nothing. privacyIDEA ignores `PI_AUDIT_SQL_TRUNCATE`.

privacyIDEA shortens a value that is longer than its audit column, for example a long user name or user agent, and
writes the entry. Before, without `PI_AUDIT_SQL_TRUNCATE = True`, the database refused such an entry, and the entry
was lost. `PI_AUDIT_SQL_COLUMN_LENGTH` still works. You need it only if you made columns wider than privacyIDEA ships
them.

#### Internal user attributes move to a new table (3.14.0)

- **Affects you if:** you run more than one node.
- **Do:** stop privacyIDEA on every node during the schema update.

The schema update moves `fido2_user_id` and the `last_used_token_*` entries from `customuserattribute` to the new
table `internaluserattribute`, and deletes them from the old table. A node of the old version can write these values
back into `customuserattribute`, and the cleanup then deletes them.

#### The metrics table needs a regular cleanup (3.14.0)

- **Affects you if:** you install from PyPI.
- **Do after the update:** add `pi-manage config metrics cleanup` to your crontab, for example once a day.

The new table `metric_aggregate` holds the data of the dashboard panels *Resolver Timing* and *Notification
Delivery*. Without a cleanup, it grows without limit. The cleanup deletes the rows older than 24 hours, which is the
most that the panels show. The Ubuntu packages run it daily.

To record no metrics, set `PI_NO_INTERNAL_METRICS = True` in `pi.cfg`. The panels then show no data.

#### Oracle stores `chr(0)` in some columns (3.14.1)

- **Affects you if:** you use Oracle.
- **Do:** nothing.

The [Oracle section of the database documentation](https://privacyidea.readthedocs.io/en/stable/faq/mysqldb.html#oracledb)
names the columns of `user_lock_state` and `metric_aggregate` that store `chr(0)` instead of an empty string.

### 3.8 Resolvers, connectors and configuration

#### privacyIDEA checks the hash settings at start (3.14.0)

- **Affects you if:** `pi.cfg` sets `PI_HASH_ALGO_LIST` or `PI_HASH_ALGO_PARAMS`.
- **Do before the update:** check both settings.

The server and `pi-manage` stop at start if a setting names an unknown algorithm or parameter. They also stop for a
parameter of an algorithm that is not in the list, and if PassLib adjusts a value. So the schema update stops as well.
Before, a wrong setting failed only when the server made or checked a hash, and PassLib adjusted a value without an
error. So a setting that worked with 3.13 can now stop the server.

#### Entra ID resolvers apply their TLS settings to the sign-in (3.14.1)

- **Affects you if:** an Entra ID resolver has its own CA file.
- **Do before the update:** make sure that the CA file covers the authority and the Graph API host. The authority is
  `login.microsoftonline.com` by default.

"Verify TLS" and the CA file of an Entra ID resolver now also apply to the requests that get the access token from the
authority. Before, they applied only to the Graph API requests.

#### `PI_CHECK_RELOAD_CONFIG` checks the configuration once per interval (3.14.1)

- **Affects you if:** `PI_CHECK_RELOAD_CONFIG` is above 0.
- **Do:** nothing.

Each process reads the configuration timestamp from the database at most once per interval, also while the
configuration does not change. A change can take up to that many seconds to apply in a process, also on the node that
saved it.

#### `clientapplication.lastseen` is written again, with an interval (3.14.0)

- **Affects you if:** you read the client list in the WebUI or the metering of plugin traffic.
- **Do:** nothing. To write on every request, set the two intervals to `0` in `pi.cfg`.

Before, the column kept the time when the server first saw the client. Now the time moves again, which can look like
new activity. Two intervals in seconds reduce the writes, and both are active by default:

- `PI_CLIENTAPPLICATION_WRITE_INTERVAL` (default `60`): each worker process refreshes `lastseen` at most once per
  interval.
- `PI_SUBSCRIPTION_COUNT_INTERVAL` (default `60`): the subscription check uses the number of users with active tokens
  for up to one interval. Before a subscription counts as exceeded, the server counts again, so no login is refused
  because of an old number.

#### Resolvers with the same priority are sorted by name (3.14.0)

- **Affects you if:** a realm holds resolvers with the same priority.
- **Do:** if the order matters, give each resolver a different priority.

Resolvers of a realm with the same priority are sorted alphabetically by name. Before, the order depended on the
database.

#### The local CA chooses the file names of requests and certificates (3.14.1)

- **Affects you if:** scripts look for certificate requests or certificates in `CSRDir` or `CertificateDir` by the
  subject.
- **Do:** adapt these scripts.

The local CA connector stores each request and certificate under a name that the server chooses. The name is a readable
part of the subject and a random suffix, for example `DE_Hessen_privacyidea_usercert_3f2a9c1e0b7d5a64.pem`. The token
keeps the certificate as before.

### 3.9 Client IP and proxies

#### A proxy entry without a mapping target also maps IPv6 clients (3.14.1)

- **Affects you if:** an entry of *Override Authorization Client* has no mapping target, for example `172.16.0.1`.
- **Do:** to keep such a proxy restricted to IPv4 clients, write the entry as `172.16.0.1 > 0.0.0.0/0`.

Before, such an entry allowed the proxy to report IPv4 clients only. Now it covers IPv6 clients as well, as
documented.

#### An X-Forwarded-For entry that is not an IP address ends the proxy path (3.14.1)

- **Affects you if:** you set *Override Authorization Client*, and a proxy writes values such as `unknown` into
  X-Forwarded-For.
- **Do:** configure the proxy to write the client address.

The entries after such a value never become the client IP, so the client IP of these requests is the address of the
proxy. Before, such a request failed with an error. Entries with a port (`192.0.2.43:51234`) or in brackets
(`[2001:db8::1]`) are now read as addresses. How privacyIDEA determines the client IP is described in
[Override Authorization Client](https://privacyidea.readthedocs.io/en/latest/configuration/system_config.html#override-client).

#### The client IP of an IPv4 client is always its IPv4 address (3.14.1)

- **Affects you if:** your audit log shows client IPs that start with `::ffff:`.
- **Do:** check the policies and the event handler conditions that name IP networks.

A dual-stack listener reports an IPv4 client as `::ffff:10.0.0.5`. privacyIDEA now uses `10.0.0.5` as the client IP,
with and without *Override Authorization Client*. So IPv4 networks such as `10.0.0.0/8` in policies and event handler
conditions now contain these clients. IPv6 networks such as `::/0` no longer contain them. IPv4 networks in
*Override Authorization Client* now also contain the mapped form of a proxy address.

### 3.10 Caches

#### `auth_cache` holds only complete credentials (3.14.0)

- **Affects you if:** you use the `auth_cache` policy.
- **Do after the update:** if you used it with challenge-response tokens, push tokens, `passOnNoToken` or
  `passOnNoUser`, clear the cache:

      pi-manage config authcache cleanup --minutes 0

The cache now holds only a complete credential that the server checked in one `/validate/check` request. These logins
no longer go into the cache, and the cache no longer answers them:

- Requests with a `transaction_id` (or `state`), that is, the answer to a challenge. Users of challenge-response
  tokens now authenticate against their token on every login. This includes Email, SMS and push tokens, and HOTP or
  TOTP tokens with the `challenge_response` policy. Expect one LDAP bind, SMS or email for each login again.
- Requests with an empty or absent `pass`.
- Logins that `passOnNoToken` or `passOnNoUser` decided.

The update does not remove the entries that 3.13 wrote. They stay valid until they expire or you clear the cache. With
`PI_REDIS_CACHE_AUTH`, the entries expire after the interval of the policy that wrote them.

`passthru` to a RADIUS server still caches what the remote server accepted. For the interval of the policy, the replay
protection of the remote system does not apply. Keep the interval short in this combination.

#### New Redis caches (3.14.0)

- **Affects you if:** you plan to use Redis.
- **Do:** nothing. Each cache has its own setting and is off by default.

- `PI_REDIS_CACHE_CHALLENGES`: the challenges. Logins that are open during a later update can need a new start.
- `PI_REDIS_CACHE_USERS`: the user store lookups. The `CACHE_TIMEOUT` of a resolver still limits how fast
  privacyIDEA sees a change of a user, because this cache of each process comes first.
- `PI_REDIS_CACHE_AUTH`: the entries of the `auth_cache` policy. They expire in Redis. An entry that is written
  while Redis can not be reached goes to the `authcache` table, and the entries that are already in the table stay
  there. So run `pi-manage config authcache cleanup` regularly also with this cache.
- `PI_REDIS_CACHE_HEALTH`: the certificate health results of the dashboard panel.

See the "Redis cache" section of the documentation.

### 3.11 Custom modules

#### Custom audit modules get `exact_params` (3.14.1)

- **Affects you if:** `PI_AUDIT_MODULE` names an audit module of your own.
- **Do before the update:** add the keyword argument `exact_params` to `search`, `search_query`, `get_total` and
  `get_count`.

`exact_params` is a dict of audit columns and values. Return only the entries whose columns equal these values,
without the `!` and `*` search operators. The audit modules that privacyIDEA ships accept the argument.

#### Configured Python classes are checked against an allowlist (3.14.0)

- **Affects you if:** an SMS gateway `module` or the `pinhandling` policy action names a class that privacyIDEA does
  not ship.
- **Do:** nothing. To refuse classes that you did not declare, declare your classes and set `enforce`:

      PI_SMS_PROVIDER_MODULES = ["mycompany.smsprovider.MyProvider"]
      PI_PIN_HANDLER_MODULES = ["mycompany.pinhandler.LetterPinHandler"]
      PI_MODULE_ALLOWLIST_MODE = "enforce"

The default mode is `warn`. A class on neither list works as before, and the log names it and the setting to declare
it in. Read the log for these warnings first, declare what they name, and then set `enforce`. The classes that
privacyIDEA ships need no declaration. `privacyidea.lib.smsprovider.SMSProvider.ISMSProvider` is the abstract base
class, so a gateway that names it needs a declaration.

For custom PIN handler classes, see also
[PIN handler classes get the token type in lower case](#pin-handler-classes-get-the-token-type-in-lower-case-3141).

### 3.12 WebUI

#### The new WebUI is the default (3.14.0)

- **Affects you if:** you enabled the preview of the new WebUI, or you want to keep the old WebUI.
- **Do after the update:**
  - If you enabled the preview, remove these lines from `pi.cfg`:

        PI_STATIC_FOLDER = "static_new/"
        PI_TEMPLATE_FOLDER = "static_new/dist/privacyidea-webui/browser/"

  - To keep the old WebUI, set `PI_STATIC_FOLDER = "static_old/"`.

The new WebUI moved from `static_new/` to `static/`, and the old WebUI moved to `static_old/`. A `pi.cfg` that names
`static_new` still works, and the log shows a warning. A future version stops this.

With the old WebUI, the server reads its own templates from `static_old/templates/`. Set
`PI_TEMPLATE_FOLDER = "static_old/templates/"` only if your `pi.cfg` points it to a folder of your own. A future
version removes the old WebUI, so use it only to gain time for a problem report.

#### The WebUI sources are not part of a release (3.14.0)

- **Affects you if:** you change the WebUI.
- **Do:** build the WebUI from the repository.

The Python packages hold the compiled WebUI (`static/dist/`) and its assets (`static/public/`), but not the Angular
sources. The sources are no longer reachable under `/static/`.

## 4. Already on 3.14.0

If you run 3.14.0, the items with "(3.14.0)" are done. Read the items with "3.14.1" in their heading. "Before" in these
items means 3.13. These changes apply only to installations that run 3.14.0:

- **Conditional access and the authentication log:**
  - Failed passkey and WebAuthn answers are logged as `CHALLENGE_ANSWERED_FAIL`, not `MFA_FAIL`. A conditional access
    policy that counts `MFA_FAIL`, for example from the *MFA Brute-Force* template, no longer counts them. To count
    them, add `CHALLENGE_ANSWERED_FAIL` to the policy.
  - An authentication that succeeds or triggers a challenge but then gets an error response is logged as
    `POST_AUTHENTICATION_FAIL`, not `LOGIN_SUCCESS` or `CHALLENGE_TRIGGERED`. A conditional access policy that counts
    `LOGIN_SUCCESS` or `CHALLENGE_TRIGGERED` no longer counts these requests. Examples are the policies from the
    *Per-User Rate Limit* and *Per-IP Rate Limit (Distinct Accounts)* templates. To count them, add
    `POST_AUTHENTICATION_FAIL` to the policy. Policies that you create from these templates after the update count it.
  - A request whose PIN matched but for which no token got a challenge is logged as `CHALLENGE_TRIGGER_FAIL`, not
    `CHALLENGE_TRIGGERED`. At `/validate/triggerchallenge`, such a request is no longer logged as `NO_TOKEN`, and a
    user whose tokens are all unusable is logged as `NO_USABLE_TOKEN`. A conditional access policy counts these
    requests only if `CHALLENGE_TRIGGER_FAIL` is one of its *Tracked Event Types*. So a policy that tracks
    `CHALLENGE_TRIGGERED` or `NO_TOKEN` no longer counts them. Examples are the policies from the templates *Per-User
    Failed-Attempt Rate Limit* and *Per-IP Failed-Attempt Rate Limit (Distinct Accounts)*. To count these requests,
    add `CHALLENGE_TRIGGER_FAIL` to the *Tracked Event Types* of the policy.
  - The steps of a PIN change via `/validate/check` (`change_pin_via_validate`) are logged as follows. The login that
    starts the PIN change is logged as `CHALLENGE_TRIGGERED`, or as `CHALLENGE_CONTINUED` if it answers a challenge.
    The new PIN is logged as `CHALLENGE_CONTINUED`, and its confirmation as `LOGIN_SUCCESS`. A refused answer is
    logged with the event type and the reason of its failure, for example `CHALLENGE_ANSWERED_FAIL` with
    `CHALLENGE_WRONG_RESPONSE` for a confirmation that does not match the new PIN.
  - A conditional access policy with *Reset the count on a successful login* resets its count only on a successful
    login that its conditions cover. Before, any successful login of the user reset a policy in the count mode
    `PER_ATTEMPT`. Check these policies.
  - IP blocks of addresses that start with `::ffff:` no longer apply. Block the IPv4 address instead. Per-IP counts
    start again for these clients. The authentication log keeps the reported address in `peer_ip` and `ip_chain`.
- **Event handlers:**
  - The schema update sets *Abort on error* for request manglers, response manglers and Script handlers that raise an
    error, also where you cleared the option. Before, only Federation handlers had it. Clear it for a handler whose
    failure must not fail the request.
  - The token event handler writes every token info entry again, for example `next_pin_change`. The same applies to
    `pi-tokenjanitor find ... set_tokeninfo` and `remove_tokeninfo`, `privacyidea-token-janitor` and
    `privacyidea-get-unused-tokens mark`. Only the token info endpoints of the API refuse the entries that a token
    type maintains.
  - With *replace*, the webhook tags `{serial}` and `{token_serial}` named all tokens of the user if the request named
    no serial. Now they name the token of the event.
  - *Reset user* with a login name of the form `user@realm` looked the user up in the realm of the original request.
    Now it uses the realm of the login name.
- **Policies and rights:**
  - Every administrator saw the health panels of the dashboard. Now they need `configread`.
  - A rollover was matched only against the realm of the owner of the token, and the second request of an enrollment
    not against the token. Now both are matched against the stored token.
- **Token lists:** With node-specific resolvers, a token whose owner has a resolver in no realm was listed only on the
  nodes that serve the realm of the owner. Now it is listed on every node.
- **Client IP:** privacyIDEA skipped an X-Forwarded-For entry that is not an IP address. Now such an entry ends the
  proxy path.
