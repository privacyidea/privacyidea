privacyIDEA configuration documentation
=======================================

* System: {{ rst_text(context.system) }}
* Date: {{ context.date }}

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
{% endfor %}


Machine Configuration
---------------------

**TODO**

Token Configuration
-------------------

**TODO**

CA Configuration
----------------

**TODO**


.. [#resolvers] http://privacyidea.readthedocs.org/en/latest/configuration/useridresolvers.htm
.. [#realms] http://privacyidea.readthedocs.org/en/latest/configuration/realms.html
.. [#policies] http://privacyidea.readthedocs.org/en/latest/policies/index.html
.. [#events] http://privacyidea.readthedocs.org/en/latest/eventhandler/index.html
