.. _container_wizard:

Container Creation Wizard
=========================

.. index:: Container Wizard

The container wizard helps the user to create his first container. It can be used for users that are not familiar with
the privacyIDEA webUI or with the token container functionality. The admin has to define all options for the container
creation in the policy. Hence, the user only has to confirm the creation of the container.

Requirements for the container wizard
--------------------------------------

 * The container wizard will only be displayed, if the user has no container assigned, yet.

 * The user must be able to login to the webUI.

 * Activate the container wizard by defining a *webui* policy:
    - All required actions are in the scope *webui* in the group *wizard*.
    - At least the action :ref:`policy_container_wizard_type` must be set. The action defines the container type that
      will be created.
    - Optionally, the container can be created from a template by setting the template name in the action
      :ref:`policy_container_wizard_template`. This will also enroll tokens defined in the template.
      Read more about templates in :ref:`container_templates`.
      Ensure that the selected template is of the correct container type as defined in
      :ref:`policy_container_wizard_type`.
    - Optionally, the registration QR code can be generated during the container creation by enabling the action
      :ref:`policy_container_wizard_registration`. The user can scan the QR code to register the container on his
      smartphone to enable the synchronization between the smartphone and the privacyIDEA server. See
      :ref:`container_synchronization` for more information.
      However, this option is only available for smartphone containers.

If both, the token wizard and the container wizard are enabled, the token wizard will be displayed first. After the
token is enrolled, the user can move on to the container wizard. However, if the token type is supported by the
container type it is recommended to only use the container wizard with a template containing the token.

Customization
-------------

The container wizard only shows required information without further text and instructions. To customize the view, you
can configure html templates that are included on top and at the bottom of each view.


For the creation page, add the following files to add your custom text:

**Old WebUI**::

    static/customize/views/includes/token.containercreate.pre.top.html
    static/customize/views/includes/token.containercreate.pre.bottom.html

**New WebUI**::

    static_new/public/customize/container-create.wizard.pre.top.html
    static_new/public/customize/container-create.wizard.pre.bottom.html

When the container is created and the user needs to do something (e.g. scanning the QR code), you can add your own text
by adding these two files:

**Old WebUI**::

    static/customize/views/includes/token.containercreate.post.top.html
    static/customize/views/includes/token.containercreate.post.bottom.html

**New WebUI**::

    static_new/public/customize/container-create.wizard.post.top.html
    static_new/public/customize/container-create.wizard.post.bottom.html

You can also include the enrollment data in the html files. The available data depends on the configuration you used
for the container creation. However, at least the variable ``containerSerial`` is available. To use the variable, write
``{{ containerSerial }}``.

If the registration was enabled, the following variables are available:

 * ``containerRegistrationQR``: The PNG data URI of the QR code to be used in an `<img>` tag. However, the QR code will
   always be displayed and must not be added manually.
 * ``containerRegistrationURL``: The QR code as URL. The user can open this link on the smartphone to register the
   container.

Creating the container on the basis of a template, but without the registration, for all tokens, the minimum required
information is displayed, e.g. a QR code, the secret, or the otp list.

If no customization files are available, the new WebUI will display a default title and instruction text similar to
the usual container creation page and registration dialog.

.. note:: You can change the directory static/customize to a URL that fits
   your needs the best by defining a variable PI_CUSTOMIZATION in the file
   pi.cfg. This way you can put all modifications in one place apart from the
   original code. See :ref:`pi_customization`.