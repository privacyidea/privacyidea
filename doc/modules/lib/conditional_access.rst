.. _code_conditional_access:

Conditional Access Module
.........................

.. index:: Conditional Access, Authentication Log

The conditional-access package classifies each authentication request, records the
outcome in the authentication log and feeds it to the conditional-access engine.
See :ref:`authentication_log` for what an entry records and how it is searched.

Authentication event types
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: privacyidea.lib.conditional_access.authentication_event_types
   :members:
   :undoc-members:

Authentication log
~~~~~~~~~~~~~~~~~~~

.. automodule:: privacyidea.lib.conditional_access.authentication_log
   :members:
   :undoc-members:

Conditional access outcome log
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: privacyidea.lib.conditional_access.outcome_log
   :members:
   :undoc-members:

Conditional access engine
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: privacyidea.lib.conditional_access.engine
   :members:
   :undoc-members:

Conditional access policies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: privacyidea.lib.conditional_access.policy
   :members:
   :undoc-members:

Policy conditions
~~~~~~~~~~~~~~~~~~

.. automodule:: privacyidea.lib.conditional_access.conditions
   :members:
   :undoc-members:

Shipped policy templates
~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: privacyidea.lib.conditional_access.policy_template
   :members:
   :undoc-members:

Live lock and block state
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: privacyidea.lib.conditional_access.state
   :members:
   :undoc-members:

Per-request context
~~~~~~~~~~~~~~~~~~~~

.. automodule:: privacyidea.lib.conditional_access.request_context
   :members:
   :undoc-members:
