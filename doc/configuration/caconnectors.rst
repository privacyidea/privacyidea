.. _caconnectors:

CA Connectors
-------------

.. index:: caconnectors, CA, Certificate Authority, certificate token

You can use privacyIDEA to enroll certificates and assign certificates to users.

You can define connections to Certificate Authorities that are used when
enrolling certificates.

.. _fig_caconnector:

.. figure:: images/CA-connectors.png
   :width: 500

   *A local CA definition*

When you enroll a Token of type *certificate* the Certificate Signing Request
gets signed by one of the CAs attached to privacyIDEA by the CA connectors.

The first CA connector that ships with privacyIDEA is a connector to a local
OpenSSL based Certificate Authority as shown in figure :ref:`fig_caconnector`.

When enrolling a certificate token you can choose which CA should sign the
certificate request.

.. figure:: images/enroll-cert.png
   :width: 500

   *Enrolling a certificate token*

.. _local_caconnector:

Local CA Connector
~~~~~~~~~~~~~~~~~~

.. index:: openssl

The local CA connector calls a local OpenSSL configuration.

The Ubuntu packages install an example *openssl.cnf* in
*/etc/privacyidea/CA/*. Other installations (pip, Docker) do not ship one; use
the *Easy Setup* below, which writes an openssl.cnf for the new CA. If a local
CA connector has no openssl.cnf configured, */etc/ssl/openssl.cnf* is used.

.. note:: This configuration and also this
   description is meant as an example. When setting up a production CA, you
   should ask a PKI consultant for assistance.

Manual Setup
............

1. Modify the parameters in the file */etc/privacyidea/CA/openssl.cnf* according
   to your needs.

2. Create your CA certificate::

       openssl req -days 1500 -new -x509 -noenc -keyout /etc/privacyidea/CA/ca.key \
                   -out /etc/privacyidea/CA/ca.crt \
                   -config /etc/privacyidea/CA/openssl.cnf

       chmod 0600 /etc/privacyidea/CA/ca.key
       touch /etc/privacyidea/CA/index.txt
       echo 01 > /etc/privacyidea/CA/serial
       chown -R privacyidea /etc/privacyidea/CA

   ``-noenc`` requires OpenSSL 3; use ``-nodes`` with older versions. The local CA
   connector can not supply a passphrase for the CA key, so the key must be stored
   unencrypted and protected by its file permissions (``chmod 0600``, owned by the
   user privacyIDEA runs as). With an encrypted key every certificate request fails
   with "An error occurred during signing of the certificate".

3. Now set up a local CA connector within privacyIDEA with the directory
   */etc/privacyidea/CA* and the files accordingly.

Easy Setup
..........

You can use the :ref:`pimanage` tool to set up a new CA like this::

   pi-manage config ca create myCA

This will ask you for all necessary parameters for the CA and then automatically

1. Create the files for this new CA and
2. Create the CA connector in privacyIDEA.

Management
..........

There are different ways to enroll a certificate token. See :ref:`certificate_token`.

When an administrator *revokes* a certificate token, the certificate is
revoked and a CRL is created.

.. note:: privacyIDEA does not create the CRL regularly. The CRL usually has a
   validity period of 30 days. So you need to create the CRL on a regular
   basis. You can use OpenSSL to do so or the pi-manage command.

The pi-manage command has the sub-command ``config ca``. The command::

    pi-manage config ca list

lists all configured *CA connectors*. You can use the ``-v`` switch to get more
information.

You can create a new CRL with the command::

    pi-manage config ca create_crl <CA name>

This command will check the *overlap period* and only create a new CRL if it
is necessary. If you want to force the creation of the CRL, you can use the
switch ``-f``.

For more information on pi-manage see :ref:`pimanage`.

Templates
.........

.. index:: Certificate Templates

The *local CA* supports a kind of certificate templates. These "templates"
are predefined combinations of *extensions* and *validity days*, as they are
passed to OpenSSL via the parameters ``-extensions`` and ``-days``.

This way the administrator can define certificate templates with certain
X.509 extensions like keyUsage, extendedKeyUsage, CDPs or AIAs and
certificate validity periods.

The templates are defined in a YAML file whose location is part of the CA
connector definition (a relative path is relative to the working directory of
the connector). Each template gives the validity in days and the name of an
extension section of the openssl.cnf; the extensions themselves
(keyUsage, CDPs, ...) are defined in that section.

The file can look like this, defining three templates "user", "webserver" and
"template3"::

    user:
        days: 365
        extensions: "user"
    webserver:
        days: 750
        extensions: "server"
    template3:
        days: 10
        extensions: "user"


.. _msca_caconnector:

Microsoft CA Connector
~~~~~~~~~~~~~~~~~~~~~~

This CA connector communicates with the privacyIDEA MS CA worker, which is installed
on a Windows server in the Windows Domain. Through this worker, privacyIDEA can connect
potentially to all Microsoft CAs in the Windows Domain.

The Microsoft CA Connector has the following options.

**Hostname**

The hostname (FQDN) or IP address where the privacyIDEA MS CA worker is running.

.. note:: If you configure *Use SSL*, you need to provide the correct hostname as it is
   contained in the server certificate.

**Port**

The port on which the worker listens.

**Connect via Proxy**

Whether privacyIDEA connects to the worker through an HTTP proxy. There is no field for the
proxy address: it is taken from the environment variable ``grpc_proxy``, ``https_proxy`` or
``http_proxy`` of the privacyIDEA process. If unchecked, no proxy is used, even if these
variables are set.

**Domain CA**

The worker will provide a list of available CAs in the domain. This is the
actual CA to which privacyIDEA shall communicate. After providing the initial
connection information *Hostname* and *Port*, privacyIDEA can fetch the available
CAs in the Windows Domain. The CA is identified by the hostname where the Microsoft CA is
running and the name of the CA like ``<hostname>\<name of CA>``.

**Use SSL**

This is a boolean parameter. If it is checked, privacyIDEA connects to the CA worker via
TLS with client certificate authentication. *CA certificate*, *Client certificate* and
*Client private key* are then all required; if one is missing, the connector can not be
used ("Incomplete TLS configuration").

.. note:: In production use SSL should always be activated and a client certificate must
   be used for authentication.

**CA certificate**

This is the location of the file that contains the CA certificate that issued the
CA worker server certificate. This file is located on the privacyIDEA server in PEM format.

**Client certificate**

This is the file location of the certificate that privacyIDEA uses to authenticate against the CA worker.
It is in PEM format.

.. note:: The subject of this certificate must match the name of the privacyIDEA server as
   seen by the CA worker. It is a good idea to request the client certificate from the
   CA on the domain where the CA worker is running.

**Client private key**

This is the location of the file containing the private key that belongs to the *Client certificate*.
It is in PEM format and can either be password protected (encrypted) or not.

The key can be provided in PKCS1 or PKCS8 format.

.. note:: The PKCS1 format will start with ``-----BEGIN RSA PRIVATE KEY-----``, the PKCS8 format
   will start with ``-----BEGIN PRIVATE KEY-----``.

To convert between PKCS1 and PKCS8 format you can use::

    openssl pkcs8 -in private-p1.pem -topk8 -out private-p8.pem -nocrypt
    openssl pkcs8 -in private-p1.pem -topk8 -out private-p8-encrypted.pem

    openssl rsa -in private-p8.pem -out private-p1.pem

**Password of client certificate**

This is the password of the encrypted client private key.

.. note:: We strongly recommend protecting the file with a password. Encrypted keys can be in
   PKCS#8 or PKCS#1 (PEM) format.



Basic setup from the command line
.................................

Of course the MS CA Connector can be configured in the privacyIDEA WebUI.
For quick setup, you can also configure a connector at the command line using
:ref:`pimanage` like this::

    pi-manage config ca create -t microsoft <name-of-connector>

It asks for the hostname and port of the worker and whether to use an HTTP proxy, then lists the
available CAs to choose from. It does not configure TLS: the CA listing only works with a worker that
accepts connections without TLS, and the connector is saved with *Use SSL* off. Set *Use SSL* and the
certificate files afterwards in the WebUI (see the note on SSL above). If the worker can not be reached,
the command ends with an error.
