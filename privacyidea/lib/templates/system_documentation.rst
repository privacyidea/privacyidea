privacyIDEA configuration documentation
=======================================

* System: {{ rst_text(context.system) }}
* Date: {{ context.date }}
* privacyIDEA version: {{ rst_text(context.version) }}
* Database schema revision: {{ rst_text(context.schema_revision) }}
* Nodes: {{ rst_text(context.nodes|join(", ")) if context.nodes else "none registered" }}

PI.cfg
------
Only selected settings are listed. Paths, URLs and credentials are left out,
a connect string is listed by its driver and a URL by whether it is set.

::

{% for k, v in context.appconfig.items() if k != "SUPERUSER_REALM" %}
    {{ (k ~ ": " ~ v)|indent(8) }}
{%- endfor %}

{% if "SUPERUSER_REALM" in context.appconfig %}
::

    {{ ("SUPERUSER_REALM: " ~ context.appconfig["SUPERUSER_REALM"])|indent(8) }}

.. note:: The SUPERUSER_REALM is a list of defined realms where the users
   will have administrative rights when logging in to the web UI.
{% endif %}

Local Admins
------------
In addition to the SUPERUSER_REALM there are local administrators stored in
the database. The following administrators are defined:

{% if context.admins %}
::

{% for admin in context.admins %}
    {{ (admin.username ~ " <" ~ admin.email ~ ">")|indent(8) }}
{%- endfor %}
{% endif %}

System Base Configuration
-------------------------

{% if context.systemconfig %}
::

{% for k, v in context.systemconfig.items() %}
    {{ (k ~ ": " ~ v)|indent(8) }}
{%- endfor %}
{% endif %}

Resolver Configuration
----------------------
The following resolvers are defined. Resolvers are connections to user stores.
To learn more about resolvers read [#resolvers]_.
Only the settings that describe how privacyIDEA uses a user store are listed,
none that names the user store or an account in it.

{% for resolvername, reso in context.resolverconfig.items() %}
{{ rst_text(resolvername) }}
{{ "~" * rst_text(resolvername)|length }}
* Name of the resolver: {{ rst_text(resolvername) }}
* Type of the resolver: {{ rst_text(reso.type) }}

Configuration
.............

{% if reso.data %}
::

{% for k, v in reso.data.items() %}
    {{ (k ~ ": " ~ v)|indent(8) }}
{%- endfor %}
{% endif %}

{% endfor %}

Realm Configuration
-------------------
Several resolvers are grouped into realms.
To learn more about realms read [#realms]_.
The following realms have been defined from the resolvers:

{% for realmname, realm in context.realmconfig.items() %}
{{ rst_text(realmname) }}
{{ "~" * rst_text(realmname)|length }}
* Name of the realm: {{ rst_text(realmname) }}

{% if realm.default: %}
**This is the default realm!**

Users in the default realm can authenticate without specifying the realm.
Users not in the default realm always need to specify the realm.
{% endif %}

The following resolvers are configured in this realm:

{% if realm.resolver %}
::

{% for reso in realm.resolver: %}
    {{ ("Name: " ~ reso.name)|indent(8) }}
    {{ ("Priority: " ~ reso.priority)|indent(8) }}
    {{ ("Type: " ~ reso.type)|indent(8) }}
{%- if reso.node %}
    {{ ("Node: " ~ context.nodenames.get(reso.node, reso.node))|indent(8) }}
{%- endif %}
{% endfor %}
{% endif %}

{% endfor %}

Policy Configuration
--------------------
Policies define the behaviour of privacyIDEA.
To learn more about policies read [#policies]_.

The following policies are defined in your system:

{% for policy in context.policyconfig: %}
{{ rst_text(policy.name) }}
{{ "~" * rst_text(policy.name)|length }}

::

{% for k, v in policy.items() if k != "name" %}
    {{ (k ~ ": " ~ v)|indent(8) }}
{%- endfor %}
{% else %}
No policies are defined.
{% endfor %}

Event Handler Configuration
---------------------------
Event handlers perform actions when the requests they are defined for are
handled. To learn more about event handlers read [#events]_.
A value of a condition or an option is listed if it is one of the choices the
handler offers, a yes or no, or a number. Free text, like the URL of a
WebHook or the body of a notification, is censored.

The following event handlers are defined in your system:

{% for event in context.eventconfig %}
{{ rst_text(event.name) }}
{{ "~" * rst_text(event.name)|length }}

::

{% for k, v in event.items() if k not in ("name", "conditions", "options") %}
    {{ (k ~ ": " ~ v)|indent(8) }}
{%- endfor %}
{%- for section in ("conditions", "options") if event[section] %}
    {{ section }}:
{%- for k, v in event[section]|dictsort %}
        {{ (k ~ ": " ~ v)|indent(12) }}
{%- endfor %}
{%- endfor %}
{% else %}
No event handlers are defined.
{% endfor %}

SMTP Server Configuration
-------------------------
SMTP servers send the emails of privacyIDEA, e.g. for email tokens and
notifications. They are listed by how they are connected, not by the host,
the sender or the account.

{% for server in context.smtpservers %}
{{ rst_text(server.identifier) }}
{{ "~" * rst_text(server.identifier)|length }}

::

{% for k, v in server.items() if k != "identifier" %}
    {{ (k ~ ": " ~ v)|indent(8) }}
{%- endfor %}
{% else %}
No SMTP servers are defined.
{% endfor %}

SMS Gateway Configuration
-------------------------
SMS gateways send the text messages of privacyIDEA. A value of an option is
listed if it is one of the choices the provider offers. Other values, like
the URL and the credentials of the gateway, and the headers are censored.

{% for gateway in context.smsgateways %}
{{ rst_text(gateway.identifier) }}
{{ "~" * rst_text(gateway.identifier)|length }}

::

    {{ ("providermodule: " ~ gateway.providermodule)|indent(8) }}
{%- for section in ("options", "headers") if gateway[section] %}
    {{ section }}:
{%- for k, v in gateway[section]|dictsort %}
        {{ (k ~ ": " ~ v)|indent(12) }}
{%- endfor %}
{%- endfor %}
{% else %}
No SMS gateways are defined.
{% endfor %}

RADIUS Server Configuration
---------------------------
RADIUS servers are queried by RADIUS tokens. They are listed by how they are
queried, not by the host or the shared secret.

{% for server in context.radiusservers %}
{{ rst_text(server.identifier) }}
{{ "~" * rst_text(server.identifier)|length }}

::

{% for k, v in server.items() if k != "identifier" %}
    {{ (k ~ ": " ~ v)|indent(8) }}
{%- endfor %}
{% else %}
No RADIUS servers are defined.
{% endfor %}

CA Configuration
----------------
CA connectors issue the certificates of certificate tokens. They are listed
by their type.

{% if context.caconnectors %}
::

{% for connector in context.caconnectors %}
    {{ (connector.name ~ ": " ~ connector.type)|indent(8) }}
{%- endfor %}
{% else %}
No CA connectors are defined.
{% endif %}

Machine Configuration
---------------------
Machine resolvers connect privacyIDEA to the machines that tokens are
attached to. The following machine resolvers are defined:

{% if context.machines.resolvers %}
::

{% for resolver in context.machines.resolvers %}
    {{ (resolver.name ~ ": " ~ resolver.type)|indent(8) }}
{%- endfor %}
{% else %}
No machine resolvers are defined.
{% endif %}

The number of tokens attached to machines per application:

{% if context.machines.attachments %}
::

{% for application, count in context.machines.attachments|dictsort %}
    {{ (application ~ ": " ~ count)|indent(8) }}
{%- endfor %}
{% else %}
No tokens are attached to machines.
{% endif %}

Token Configuration
-------------------
The number of tokens per token type, in total, active and assigned to a user:

{% if context.tokens.tokens %}
::

{% for token_type, counts in context.tokens.tokens|dictsort %}
    {{ (token_type ~ ": " ~ counts.total ~ " total, " ~ counts.active ~ " active, "
        ~ counts.assigned ~ " assigned")|indent(8) }}
{%- endfor %}
{% else %}
No tokens are enrolled.
{% endif %}

The number of containers per container type:

{% if context.tokens.containers %}
::

{% for container_type, count in context.tokens.containers|dictsort %}
    {{ (container_type ~ ": " ~ count)|indent(8) }}
{%- endfor %}
{% else %}
No containers are defined.
{% endif %}


.. [#resolvers] http://privacyidea.readthedocs.org/en/latest/configuration/useridresolvers.htm
.. [#realms] http://privacyidea.readthedocs.org/en/latest/configuration/realms.html
.. [#policies] http://privacyidea.readthedocs.org/en/latest/policies/index.html
.. [#events] http://privacyidea.readthedocs.org/en/latest/eventhandler/index.html
