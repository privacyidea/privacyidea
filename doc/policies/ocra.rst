.. _ocra_policies:

OCRA policies
-------------

.. index:: OCRA policies

The scope *ocra* defines who is allowed to access the OCRA
methods. It controlls the access to the :ref:`ocra_controller`.

The following actions are available in the scope 
*ocra*:

request
~~~~~~~

type: bool

The administrator is allowed to issue OCRA requests *ocra/request*.


status
~~~~~~

type: bool

The administratpr is allowed to check the transaction status.

activationcode
~~~~~~~~~~~~~~

type: bool

The administrator is allowed to create an activation code via
*ocra/getActivationCode*.

calcOTP
~~~~~~~

type: bool

The administrator is allowed to calculate OTP values via
*ocra/calculateOTP*.
