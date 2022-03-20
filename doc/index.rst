######################
Welcome to privacyIDEA
######################

privacyIDEA is a modular authentication system.
Using privacyIDEA you can enhance your existing applications like
:ref:`local login <pam_plugin>`,
:ref:`VPN <freeradius>`,
:ref:`remote access <freeradius>`,
:ref:`SSH connections <pam_plugin>`,
access to web sites or
:ref:`web portals <rest_api>`
with a second factor during authentication.
Thus boosting the security of your existing applications.
Originally it was used for OTP authentication devices.
But other "devices" like challenge response and SSH keys are also available.
It runs on Linux and is completely Open Source, licensed under the AGPLv3.

privacyIDEA can read users from many different sources like flat files,
different LDAP services, SQL databases and SCIM services. (see :ref:`realms`)

Authentication devices to provide two factor authentication can be
assigned to those users, either by administrators or by the users themselves.
:ref:`Policies <policies>` define what a user is allowed to do in the web UI and
what an administrator is allowed to do in the management interface.

The system is written in python, uses flask as web framework and an
SQL database as datastore. Thus it can be enrolled quite easily providing
a lean installation. (see :ref:`installation`)

#################
Table of Contents
#################

.. toctree::
   :maxdepth: 1
   :glob:
   :numbered:

   overview/index
   installation/index
   firststeps/index
   webui/index
   configuration/index
   tokens/index
   policies/index
   eventhandler/index
   periodictask/index
   audit/index
   machines/index
   workflows_and_tools/index
   jobqueue/index
   application_plugins/index
   modules/index
   faq/index
   glossary/index


If you are missing any information or descriptions
file an issue at `github <https://github.com/privacyidea/privacyidea/issues>`_ (which would be the preferred way),
drop a note to info(@)privacyidea.org
or go to the `Community Forum <https://community.privacyidea.org>`_.

This will help us a lot to improve documentation to your needs.

Thanks a lot!

##################
Indices and tables
##################

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

