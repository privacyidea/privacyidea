.. _logginghandler:

Logging Handler Module
----------------------

.. index:: Logging Handler, Handler Modules

The logging event handler can be used to log the occurrence of an event to the
Python logging facility.
You can log arbitrary events with a configurable log message, loglevel and
logger instance. Several tags are available to customize the log message.

The configuration to handle the log messages can be defined in detail with
the :ref:`advanced_logging`.

Possible Actions
~~~~~~~~~~~~~~~~

logging
.......

Emit a log message to the Python logging facility when the specified event gets
triggered (and the conditions match).

**name**

  * *default:* ``pi-eventlogger``

The name of the logger to use when emitting the log message. This can be used
for a fine-grained control of the log messages via :ref:`advanced_logging`.

.. note:: Logger names ``privacyidea`` or starting with ``privacyidea.`` (with a
   dot) are handled by the privacyIDEA logger and end up in the privacyIDEA log;
   a name like ``privacyidea-events`` is not. With the default logging
   configuration of a package or pip installation, any other name - including
   the default ``pi-eventlogger`` - needs its own logger in the
   :ref:`advanced_logging` configuration; otherwise its INFO and DEBUG messages
   are dropped and only warnings and errors appear on stderr. In the Docker
   image, messages of every logger are written to the container output.

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
        The path of the request that triggered this event, e.g. ``/validate/check``.
  * ``{serial}``
        The serial of the token of this event, taken from the request, the
        response or the audit entry. If none of them names a token (e.g. in the
        pre position of ``/validate/check``, or after a failed authentication),
        the comma-separated serials of all tokens of the user.
  * ``{url}``
        The URL of the privacyIDEA system as set in ``PI_BASE_URL`` (see
        :ref:`cfgfile`); empty if it is not set.
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
  * ``{now}``
        The current server timestamp including the date, the time and the time
        zone. ``{current_time}`` is a deprecated alias for it.
  * ``{client_ip}``
        The IP of the client who triggered the event.
  * ``{ua_browser}``
        The user agent of the client, which issued the original request.
  * ``{ua_string}``
        The complete user agent string (including version number) which
        issued the original request.

.. note:: Not all tags are available in every event. It depends on the called
    API endpoint and the passed parameters which tags exist. If a tag of the list
    above has no value during the event handling, an empty string is inserted. A
    tag name the handler does not know (e.g. a typo, or ``{logged_in_user}`` from
    the webhook handler) and a single brace make the handler fail, and no message
    is logged.

Code
~~~~

.. automodule:: privacyidea.lib.eventhandler.logginghandler
   :members:
   :undoc-members:
