.. _u2f_token_config:

U2F Token Config
................

.. index:: U2F Token

AppId
~~~~~

You need to configure the AppId of the privacyIDEA server. The AppId is
defined in the FIDO specification [#fido]_.

The AppId is the URL of your privacyIDEA and used to find or create the right
key pair on the U2F device. The AppId must correspond to the URL that is
used to call the privacyIDEA server.

.. note:: if you register a U2F device with an AppId
   https://privacyidea.example.com and
   try to authenticate at https://10.0.0.1, the U2F authentication will fail.

.. note:: The AppId must not contain any trailing slashes!

Facets
~~~~~~

If specifying the AppId as the FQDN, you will only be able to authenticate at
the privacyIDEA server itself or at any application in a sub directory on the
privacyIDEA server. This is OK, if you are running a SAML IdP on the same
server.

But if you also want to use the U2F token with other applications, you need
to specify the AppId like this:

   https://privacyidea.example.com/pi-url/ttype/u2f

*pi-url* is the path, if you are running the privacyIDEA instance in a sub
folder.

*/ttype/u2f* is the endpoint that returns a trusted facets list.
Trusted facets are other hosts in the domain *example.com*. You need to
define a policy that contains a list of the other hosts
(:ref:`policy_u2f_facets`).

For more information on AppId and trusted facets see [#fido]_.

For further details and information on how to add U2F to your application you
can see the code documentation at
:ref:`code_u2f_token`.

Workflow
~~~~~~~~

You can use a U2F token on privacyIDEA and other hosts in the same Domain. To
do so you need to do the following steps:

1. Configure the AppId to reflect your privacyIDEA server:

      https://pi.your-network.com/ttype/u2f

   Adding the path */ttype/u2f* is crucial. Otherwise privacyIDEA will not
   return the trusted facets.

2. Define a policy with the list of trusted facets. (see
   :ref:`policy_u2f_facets`). Add the FQDNs of the hosts to the policy:

      saml.your-network.com otherapp.your-network.com vpn.your-network.com

   .. note:: The privacyIDEA plugin for simpleSAMLphp supports U2F with
      privacyIDEA starting with version 2.8.

3. Now register a U2F token on https://pi.your-network.com. Due to the trusted
   facets you will also be able to use this U2F token on the other hosts.

4. Now got to https://saml.your-network.com and you will be able to authenticate
   with the very U2F token without any further registering.



.. rubric:: Footnotes

.. [#fido] https://fidoalliance.org/specs/fido-u2f-v1.0-nfc-bt-amendment-20150514/fido-appid-and-facets.html
