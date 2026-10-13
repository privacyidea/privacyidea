:orphan:

.. _rlm_rest:

Configuration of rlm_rest
=========================

FreeRADIUS 3 is shipped with the ``rlm_rest`` module, which can be used to transform
RADIUS authentication requests to HTTP requests to a suitable REST endpoint.
privacyIDEA implements such an endpoint (``/validate/radiuscheck``, see :ref:`rest_validate`). However, the endpoint
currently does not implement all features of the :ref:`rlm_perl` such as challenge-response authentication
and attribute mapping.

On Debian and Ubuntu, the required packages can be installed as follows::

    apt-get install freeradius freeradius-rest

On Debian and Ubuntu, the FreeRADIUS configuration is located in ``/etc/freeradius/3.0/``. Other distributions
may use a different directory, e.g. ``/etc/raddb/``.


Setup
-----

First, the ``rlm_rest`` module needs to be enabled::

    cd /etc/freeradius/3.0/mods-enabled
    ln -s ../mods-available/rest .


The authentication type needs to be configured in the ``/etc/freeradius/3.0/users`` file::

    DEFAULT Auth-Type := rest

and the site configuration should invoke the module as follows::

   authenticate {
        Auth-Type rest {
           rest
        }
        digest
        unix
   }

The module itself is then configured via the file ``/etc/freeradius/3.0/mods-enabled/rest``. First, ``connect_uri``
needs to point to your privacyIDEA instance::

    connect_uri = "https://127.0.0.1/"

The ``authenticate`` section needs to be modified as follows::

    authenticate {
        uri = "${..connect_uri}/validate/radiuscheck"
        method = 'post'
        body = 'post'
        data = "user=%{urlquote:%{User-Name}}&pass=%{urlquote:%{User-Password}}"
        force_to = 'plain'
        tls = ${..tls}
    }

Assuming ``clients.conf`` has been edited accordingly, the FreeRADIUS server should already respond
to authentication requests::

   echo "User-Name=user, User-Password=password" | radclient -sx yourRadiusServer \
      auth topsecret


For instructions on how to configure more advanced features of ``rlm_rest`` such as the connection pool or
TLS certificate validation, please consult the documentation in the configuration file.
