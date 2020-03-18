.. _logginghandler:

Logging Handler Module
----------------------

.. index:: Logging Handler, Handler Modules

The logging event handler can be used to log the occurrence of an event to the
python logging facility.
You can log arbitrary events with a configurable log message, loglevel and
logger instance. Several tags are available to customize the log message.

The configuration to handle the log messages can be defined in detail with
the :ref:`advanced_logging`.

Possible Actions
~~~~~~~~~~~~~~~~

logging
.......

Emit a log message to the python logging facility when the specified event gets
triggered (and the conditions match).

**name**

  * *default:* ``pi-eventlogger``

The name of the logger to use when emitting the log message. This can be used
for a fine-grained control of the log messages via :ref:`advanced_logging`.

.. note:: Logger names beginning with ``privacyidea`` will be handled by the
   default privacyIDEA logger and will end up in the privacyIDEA log.

**level**

  * *default:* ``INFO``

The log level for the emitted log message. The following levels are available:

  * ``ERROR``
  * ``WARNING``
  * ``INFO``
  * ``DEBUG``

**message**

  * *default:* ``"event={action} triggered"``

The message to send to the logging facility. This message can be customized
with the following tags:

  * ``{admin}``
        The logged in user.
  * ``{realm}``
        The realm of the logged in user.
  * ``{action}``
        The action which triggered this event.
  * ``{serial}``
        The serial of a token used in this event.
  * ``{url}``
        The URL of the privacyIDEA system.
  * ``{user}``
        The given name of the token owner.
  * ``{surname}``
        The surname of the token owner.
  * ``{givenname}``
        The given name of the token owner.
  * ``{username}``
        The login of the token owner.
  * ``{userrealm}``
        The realm of the token owner.
  * ``{tokentype}``
        The type of the token.
  * ``{time}``
        The current server time (format: HH:MM:SS).
  * ``{date}``
        The current server date (format: YYYY-MM-DD).
  * ``{client_ip}``
        The IP of the client who triggered the event.
  * ``{ua_browser}``
        The user agent of the client, which issued the original request.
  * ``{ua_string}``
        The complete user agent string (including version number) which
        issued the original request.

.. note:: Not all tags are available in every event. It depends on the called
    API-Endpoint and passed parameter which tags exist. If a tag does not exist
    during the event handling, an empty string will be inserted.