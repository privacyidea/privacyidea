.. _container:

Container
---------

Starting with version 3.10, privacyIDEA supports token containers. A container represents a physical device (e.g.
smartphone, yubikey) which can contain multiple tokens. The container can be used to store and manage these tokens.
All tokens in a container can be enabled, disabled and deleted at once. For example, that might be helpful if a user
looses the smartphone with several tokens on it. The administrator can then disable all tokens in the container at once.



.. toctree::
   :maxdepth: 1

   container_types.rst
