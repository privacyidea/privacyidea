.. _code_docu:

Code Documentation
==================

The code roughly has three levels: API, LIB and DB.

.. index:: JWT, JSON Web Token

API level
---------
The API level is used to access the system. 
For some calls you need to be authenticated as administrator,
for some calls you can be authenticated as normal user.
These are the ``token`` and the ``audit`` endpoint.
For calls to the ``validate`` API you do not need to be authenticated at all.

At this level ``Authentication`` is performed. In the lower levels there is no
authentication anymore.

The object ``g.logged_in_user`` is used to pass the authenticated user.
The client gets a JSON Web Token to authenticate every request.

API functions are decorated with the decorators ``admin_required`` and
``user_required`` to define access rules.

.. toctree::

   api

LIB level
---------

At the LIB level all library functions are defined. There is no authentication
on this level.
Also there is no flask/Web/request code on this level.

Request information and the ``logged_in_user`` need to be passed to the 
functions as parameters, if they are needed.

If possible, policies are checked with policy decorators.

.. toctree::

   lib
   useridresolvers
   audit
   monitoring
   machineresolvers
   pinhandler


DB level
--------

On the DB level you can simply modify all objects.


.. toctree::

   db
