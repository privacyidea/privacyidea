.. _rlm_rest:

Configuration of rlm_rest
=========================

Starting with version 3.0.x FreeRADIUS is shipped with the ``rlm_rest`` module, which can be used to transform
RADIUS authentication requests to HTTP requests to a suitable REST endpoint. Starting with version 2.19,
privacyIDEA implements such an endpoint (``/validate/radiuscheck``, see :ref:`rest_validate`). However, the endpoint
currently does not implement all features of the :ref:`rlm_perl` such as challenge-response authentication
and attribute mapping.

Please note that Ubuntu 17.04 and Debian 9 are the first releases to include FreeRADIUS 3.0.x. Here, the required
packages can be installed as follows::

    apt-get install freeradius freeradius-rest


Setup
-----

First, the ``rlm_rest`` module needs to be enabled::

    cd /etc/freeradius/mods-enabled
    ln -s ../mods-available/rest .


The authentication type needs to be configured in the ``/etc/freeradius/users`` file::

    DEFAULT Auth-Type := rest

and the site configuration should invoke the module as follows::

   authenticate {
        Auth-Type rest {
           rest
        }
        digest
        unix
   }

The module itself is then configured via the file ``/etc/freeradius/mods-enabled/rest``. First, ``connect_uri``
needs to point to your privacyIDEA instance::

    connect_uri = "https://127.0.0.1/"

The ``authenticate`` section needs to be modified as follows::

    authenticate
        uri = "${..connect_uri}/validate/radiuscheck"
        method = 'post'
        body = 'post'
        data = "user=%{urlquote:%{User-Name}}&pass=%{urlquote:%{User-Password}}"
        force_to = 'plain'
        tls = ${..tls}
    }

Assuming ``clients.conf`` has been edited accordingly, the FreeRADIUS server should already respond
to authentication requests::

   echo "User-Name=user, Password=password" | radclient -sx yourRadiusServer \
      auth topsecret


For instructions how to configure more advanced features of ``rlm_rest`` such as the connection pool or
TLS certificate validation, please consult the documentation in the configuration file.