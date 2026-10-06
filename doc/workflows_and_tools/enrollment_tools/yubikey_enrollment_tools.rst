.. _yubikey_enrollment_tools:

YubiKey Enrollment Tools
------------------------

.. index:: Yubikey, Yubico AES mode, Yubikey OATH-HOTP mode

The YubiKey can be used with privacyIDEA in Yubico's own AES mode (*Yubico OTP*),
in the HOTP mode (*OATH-HOTP*) or the seldom used static password mode.

This section describes tools which can be used to initialize and enroll a
YubiKey with privacyIDEA.

If not using the :ref:`yubico_token` mode, the YubiKey has to be initialized/configured
which creates a new secret on the device that has to be imported to privacyIDEA.

There are tools to (mass-)enroll YubiKeys in AES mode (Yubikey token) or HOTP mode (HOTP token).

.. _privacyideaadm_enrollment:

privacyidea CLI tool
~~~~~~~~~~~~~~~~~~~~

.. index:: privacyideaadm, admin tool

For Linux clients, there is the ``privacyidea`` command line
client [#privacyideaadm]_, to initialize the YubiKeys. You can use the mass enrollment, which
eases the process of initializing a whole bunch of tokens.

.. note:: The ``privacyidea`` command line client (privacyideaadm) is no longer
   actively developed; its last change dates from 2023. Its YubiKey functions
   depend on python-yubico, which Yubico archived in 2024.

Run the command like this::

   privacyidea -U https://your.privacyidea.server -a admin token \
   yubikey-mass-enroll --yubimode YUBICO --yubiprefixrandom 6

This command initializes the device and creates a new token with the
AES secret and prefix in privacyIDEA. ``--yubiprefixrandom 6`` gives the token
the 12-character public ID (prefix) that Yubico mode expects; without it the
YubiKey is programmed with an empty prefix. You can enroll YubiKeys
in HOTP mode by using the option ``--yubimode OATH`` which is also the default.
You can choose the slot with ``--yubislot``. For further help call
``privacyidea token yubikey-mass-enroll`` with the ``--help`` option and refer to
the documentation of the tool [#privacyideaadmdocs]_.

You can also use ``yubikey-mass-enroll`` with the option ``--filename`` to
write the token configuration to the specified file, which can be imported
later via the privacyIDEA WebUI at *Token* -> *Import*.
There, select :ref:`import_oath_csv` and the file you just created.

.. _ykpersgui:

YubiKey Personalization GUI
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. index:: Yubikey, Yubikey personalization GUI, Yubikey personalization tool

.. note:: The YubiKey Personalization Tool reached its end of life on
   February 19, 2026 [#ykpers]_. This section describes this end-of-life tool.
   To program the OTP slots of a YubiKey, Yubico provides the YubiKey Manager
   (``ykman``) with the commands ``ykman otp yubiotp`` (Yubico OTP) and
   ``ykman otp hotp`` (OATH-HOTP), see the ykman documentation [#ykman]_.

You can also initialize the YubiKey with the official Yubico personalization GUI
[#ykpers]_ and use the obtained secret to enroll the YubiKey with privacyIDEA.
For both AES (Yubico OTP) and OATH-HOTP mode, there are two possibilities to initialize
the YubiKey with privacyIDEA.

Manual token enrollment
.......................

To initialize a single YubiKey in AES mode (Yubico OTP) use the *Quick* button and
copy the displayed secret labeled with *Secret Key (16 bytes Hex)* to the field *OTP Key*
on the enrollment form in the privacyIDEA WebUI.

.. figure:: images/ykpers-quick-initialize-aes.png
   :width: 500

   *Initialize a Yubikey in AES mode (Yubikey OTP)*

.. figure:: images/enroll_yubikey.png
   :width: 500

   *Enroll a Yubikey AES mode token in privacyIDEA*

In the field *Test Yubikey* touch the YubiKey button. This will determine the
length of the *OTP value* and the field *OTP length* is automatically filled.

.. note::
    The length of the unique passcode for each OTP is 32 characters at the end
    of the OTP value. The remaining characters at the beginning of the OTP value
    form the Public ID of the device. They remain constant for each
    OTP [#ykotp]_.

    privacyIDEA takes care of separating these parts but it needs to know the
    complete length of the OTP value to work correctly.

The process is similar for the HOTP mode. You have to deselect *OATH Token Identifier*.
Copy the displayed secret to the HOTP :ref:`hotp_token_enrollment` form in privacyIDEA.

.. figure:: images/ykpers-quick-initialize-oath-hotp.png
   :width: 500

   *To initialize a single Yubikey in HOTP mode, deselect OATH Token Identifier.*

.. note::
   In the case of HOTP mode privacyIDEA can not necessarily distinguish a YubiKey in
   HOTP mode from a smartphone App in HOTP mode. Using the above mentioned mass-enrollment,
   the token serial number is used to distinguish these tokens.

Mass enrollment
...............

To initialize one or more YubiKeys it is convenient to write the created token secrets to a file
which can be imported in the privacyIDEA WebUI. To do this, activate *Settings* -> *Log configuration output*.
We recommend selecting *Yubico format*, since then privacyIDEA is able to detect the YubiKey mode and
sets the serial accordingly by prepending UBOM or UBAM. PSKC format is also supported upon import.
The *Yubico format* does not record the slot (all serials end in ``_X``) and imports HOTP tokens with the OTP
length 6. If both slots of a YubiKey are programmed in the same mode, or for HOTP with 8 digits, use the *Flexible
format* below.
You may also use the *Flexible format* to set custom token serials upon import with :ref:`import_oath_csv`.

To set a custom serial for Yubikey tokens, set the *Flexible format* to::

   YUBIAES{serial}_{configSlot},{secretKeyTxt},yubikey,44

The last column is the OTP length: 32 characters plus the length of the public ID, i.e. 44 for the default public ID
of 12 characters. Without this column the token is imported with the OTP length 6 and does not authenticate.

For YubiKeys in HOTP mode, set the output format as::

   YUBIHOTP{serial}_{configSlot},{secretKeyTxt},hotp,{hotpDigits}

Upon clicking *Write Configuration* for the first time, you will be prompted to select an output file name and
the generated configuration is written both to the device and to the selected file. In the *Advanced* mode
select *Program Multiple Yubikeys* and *Automatically program Yubikeys when inserted* to program each YubiKey
automatically after you insert it.

.. figure:: images/ykpers-mass-initialize.png
   :width: 500

   *Write Configuration initializes the Yubikey*

During this process the token secrets are automatically
appended to the selected export file. Note again that for HOTP, you have to deselect
*OATH Token Identifier*.

After mass-initialization, the token secrets have to be imported to privacyIDEA according to the
output format (see :ref:`import`).

.. rubric:: Footnotes

.. [#privacyideaadm] https://github.com/privacyidea/privacyideaadm/
.. [#privacyideaadmdocs] https://github.com/privacyidea/privacyideaadm/blob/master/doc/index.rst
.. [#ykpers] https://www.yubico.com/support/download/yubikey-personalization-tools/
.. [#ykman] https://docs.yubico.com/software/yubikey/tools/ykman/OTP_Commands.html
.. [#ykotp] https://developers.yubico.com/OTP/OTPs_Explained.html
