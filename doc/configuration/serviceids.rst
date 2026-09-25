.. _serviceids:

Service IDs
-----------

.. index:: Service ID

privacyIDEA uses Service IDs to identify service. The idea is instead of identifying each and every single host by
hostname or IP address, privacyIDEA can e.g. identify all "web servers" or "mail servers".
The administrator can define these Services IDs. privacyIDEA provides the REST API :ref:`rest_serviceid` to do so.

A service ID can then be used to e.g. attach an SSH key to such a service ID instead of attaching the SSH key to
a lot of different IP addresses. See :ref:`application_ssh`

Service IDs are also used with :ref:`application_specific_token`. Such a token is enrolled for one of the defined
service IDs, so a user who enrolls one in the self-service portal needs to read the list as well, which the policy
action :ref:`user_policy_serviceid_list` allows.

Clients communicating with privacyIDEA can then send the a parameter `service_id` in an authentication request
for application specific tokens or in the request that fetches allowed SSH keys.

.. note:: A Service ID is simply an identifier.
   privacyIDEA does not provide means to change the name of the Service ID later.

