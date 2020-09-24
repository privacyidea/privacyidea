privacyIDEA configuration documentation
=======================================

* System: {{ context.system }}
* Date: {{ context.date }}

PI.cfg
------

{% for k, v in context.appconfig.items() %}
{% if k.startswith("PI_"): %}
{% if k == "PI_PEPPER": %}
{{k}}: **redacted**
{% else %}
{{k}}: **{{v}}**
{% endif %}
{% endif %}
{% if k == "SUPERUSER_REALM" %}
SUPERUSER_REALM: **{{v}}**

.. note:: The SUPERUSER_REALM is a list of defined realms where the users
   will have administrative rights when logging in to the web UI.
{% endif %}
{% if k == "SQLALCHEMY_DATABASE_URI" %}
For security reason we do not display the SQL URI, as it may contain the
database credentials.
{% endif %}
{% endfor %}

Local Admins
------------
In addition to the SUPERUSER_REALM there are local administrators stored in
the database. The following administrators are defined:

{% for admin in context.admins: %}
* **{{admin.username}}** <{{admin.email}}>
{% endfor %}

System Base Configuration
-------------------------

{% for k, v in context.systemconfig.items() %}
{{k}}: **{{v}}**
{% endfor %}

Resolver Configuration
----------------------
The following resolvers are defined. Resolvers are connections to user stores.
To learn more about resolvers read [#resolvers]_.

{% for resolvername, reso in context.resolverconfig.items() %}
{{ resolvername }}
~~~~~~~~~~~~~~~~~~
* Name of the resolver: {{ resolvername }}
* Type of the resolver: {{ reso.type }}

Configuration
.............
{% for k, v in reso.data.items() %}
{{k}}: **{{v}}**
{% endfor %}

{% endfor %}

Realm Configuration
-------------------
Several resolvers are grouped into realms.
To learn more about realms read [#realms]_.
The following realms have been defined from the resolvers:

{% for realmname, realm in context.realmconfig.items() %}
{{ realmname }}
~~~~~~~~~~~~~~~
* Name of the realm: {{ realmname }}

{% if realm.default: %}
**This is the default realm!**

Users in the default realm can authenticate without specifying the realm.
Users not in the default realm always need to specify the realm.
{% endif %}

The following resolvers are configured in this realm:

{% for reso in realm.resolver: %}
* Name: {{reso.name}}
  Priority: {{reso.priority}}
  Type: {{reso.type}}
{% endfor %}

{% endfor %}

Policy Configuration
--------------------
Policies define the behaviour of privacyIDEA.
To learn more about policies read [#policies]_.

The following policies are defined in your system:

{% for policy in context.policyconfig: %}
{{ policy.name }}
~~~~~~~~~~~~~~~~~
{% for k, v in policy.items(): %}
{% if k != "name": %}
{{k}}: **{{v}}**
{% endif %}
{% endfor %}
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
