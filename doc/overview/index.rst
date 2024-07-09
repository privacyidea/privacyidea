.. _overview:

Overview
========

.. index:: overview, token

privacyIDEA is a system that is used to manage devices for two
factor authentication. Using privacyIDEA you can enhance your existing
applications like local login,
VPN, remote access, SSH connections, access to web sites or web portals with
a second factor during authentication. Thus boosting the security of your
existing applications.

In the beginning privacyIDEA was used to manage OTP tokens, but
now also certificates, SSH keys, PUSH tokens, WebAuthn and more token
types are supported. You may follow the development on Github.

privacyIDEA is a web application written in Python based on the
`flask micro framework`_. You can use any webserver with a wsgi interface
to run privacyIDEA. E.g. this can be Apache, Nginx or even `werkzeug`_.

A device or item used to authenticate is still called a
"token". All token information is stored in an SQL database,
while you may choose, which database you want to use.
privacyIDEA uses `SQLAlchemy`_ to map the database to internal objects.
Datebases that are known to work well are MySQL, MariaDB, Galera Cluster
and PostgreSQL.

The code is divided into three layers, the API, the library and the
database layer. Read about it at :ref:`code_docu`.
privacyIDEA provides a clean :ref:`rest_api`.

Administrators can use a Web UI or a command line client to
manage authentication devices. Users can log in to the Web UI to manage their
own tokens.

Authentication is performed via the API or certain plugins for
FreeRADIUS, SSO IdPs (simpleSAMLphp, Keycloak, Shibboleth, ADFS, Gluu),
Windows Credential Provider, privacyIDEA PAM,
Wordpress, Contao, Dokuwiki... to
either provide default protocols like RADIUS or SAML or
to integrate into applications directly.

Due to this flexibility there are also many different ways to
install and setup privacyIDEA.
We will take a look at common ways to setup privacyIDEA
in the section :ref:`installation`
but there are still many others.

Productive Installation
-----------------------

To come to a productive installation, among other things, you need
to consider the following aspects:

* Configure your DNS and ensure to use **FQDN**.
  Avoid static IP addresses.

* Ensure a correct time. User **NTP**.

* Setup a reliable **database**. If you are planning a redundant setup
  the redundancy is done via the database cluster.  Manage your database
  and think about sizing - especially when it comes to collecting
  audit data.

* Define your **concept of roles** for administrators, operators, help desk
  users and normal users. Read more about it in the
  :ref:`admin_polices` and :ref:`user_policies`.

* In privacyIDEA you have a lot
  of possibilities to design automatation and **processes** like
  enrollment, revocation, leaving users and more. You will identify
  processes that are mandatory and others might not be relevant for you.
  You can use again :ref:`policies` and :ref:`event_handler`s to implement these.

* Authentication data is important. Plan your **backup** and **recovery**
  of your privacyIDEA system. You can use the database level but
  also need to take a closer look at the :ref`:`pimanage`.

* Think about update- and **upgrade**-processes. Both for privacyIDEA
  and for the OS.

* Manage **certificates**. For the privacyIDEA system itself and
  also for trusting e.g. LDAPS connections in your resolvers.

* Finally you will have to connect your **applications** like RADIUS,
  SSO with SAML or OpenID Connect or logins to Windows or via the
  Linux PAM stack. So think about, which application you need to protect
  with a second factor and which one not (yet).


.. _flask micro framework: https://flask.palletsprojects.com/
.. _SQLAlchemy: https://www.sqlalchemy.org/
.. _werkzeug: https://werkzeug.palletsprojects.com/
