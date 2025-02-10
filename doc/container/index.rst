.. _container:

Container
---------

Starting with version 3.10, privacyIDEA supports token containers. A container represents a physical device (e.g.,
smartphones, yubikeys) that can contain multiple tokens. The container can be used to store and manage these tokens.
All tokens in a container can be enabled, disabled, and deleted at once. This might be helpful if a user
loses the smartphone with several tokens on it. The administrator can then disable all tokens in the container at once.

Starting with version 3.11, privacyIDEA supports the synchronization of smartphones with the privacyIDEA
server and supports container templates for a simplified token rollout. Both are explained in more detail in the
following subsections.

.. toctree::
   :maxdepth: 1

   container_types.rst
   synchronization.rst
   templates.rst
