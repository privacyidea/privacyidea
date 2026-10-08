.. _debug_log:

Debugging and Logging
---------------------

.. index:: Debugging, Logging

You can set ``PI_LOGLEVEL`` to a value 10 (Debug), 20 (Info), 30 (Warning),
40 (Error) or 50 (Critical).
If you experience problems, set ``PI_LOGLEVEL = 10``, restart the web service
and resume the operation. The log file ``privacyidea.log`` should contain
some clues.

You can define the location of the logfile using the key ``PI_LOGFILE``. If it
is not set, the file ``privacyidea.log`` is written to the working directory of
the server process (or of ``pi-manage``). Set it to an absolute path, usually::

   PI_LOGFILE = "/var/log/privacyidea/privacyidea.log"

The *pi.cfg* of the Ubuntu packages sets this path. The Docker image logs to
standard error and ignores ``PI_LOGFILE``.

.. note:: ``PI_LOGLEVEL`` and ``PI_LOGFILE`` only apply when privacyIDEA uses no
   logging configuration file (see :ref:`advanced_logging`). As soon as it loads
   such a file - the file set with ``PI_LOGCONFIG`` or, without that key,
   ``/etc/privacyidea/logging.cfg`` - the levels, handlers and log files are
   taken from that file only, and both keys are ignored. To debug, raise the
   level in that file. If the file exists but cannot be loaded, privacyIDEA
   writes the error to standard error and uses ``PI_LOGLEVEL`` and
   ``PI_LOGFILE``.

.. _advanced_logging:

Advanced Logging
~~~~~~~~~~~~~~~~

In the advanced logging you can use the Python logging configuration to
define in a fine-grained way which information should be logged where.
For more details see `python logging config <https://docs.python.org/3/library/logging.config.html#module-logging.config>`_.


You can also define a more detailed logging by specifying a
log configuration file. By default the file is ``/etc/privacyidea/logging.cfg``.
If this file exists and can be loaded, ``PI_LOGLEVEL`` and ``PI_LOGFILE`` are
ignored.

You can change the location of the logging configuration file
in :ref:`cfgfile` like this::

   PI_LOGCONFIG = "/path/to/logging.yml"

The logging configuration can also be written in YAML [#yaml]_.
Such a YAML based configuration could look like this:

.. code-block:: yaml

    version: 1
    disable_existing_loggers: false
    formatters:
      detail:
        class: privacyidea.lib.log.SecureFormatter
        format: '[%(asctime)s][%(process)d][%(thread)d][%(levelname)s][%(name)s:%(lineno)d] %(message)s'

    handlers:
      mail:
        class: logging.handlers.SMTPHandler
        mailhost: mail.example.com
        fromaddr: privacyidea@example.com
        toaddrs:
        - admin1@example.com
        - admin2@example.com
        subject: PI Error
        formatter: detail
        level: ERROR
      file:
        # Rotate the logfile at 1 MB, keep 5 old files
        class: logging.handlers.RotatingFileHandler
        backupCount: 5
        maxBytes: 1000000
        formatter: detail
        level: INFO
        filename: /var/log/privacyidea/privacyidea.log
      syslog:
        class: logging.handlers.SysLogHandler
        address: ['192.168.1.110', 514]
        formatter: detail
        level: INFO

    loggers:
      # The logger name is the qualname
      privacyidea:
        handlers:
        - file
        - mail
        level: INFO

    root:
      handlers:
      - syslog
      level: WARNING

Set ``disable_existing_loggers: false`` as in this example. Without it, every
logger that already exists when privacyIDEA loads the file, e.g. the SQLAlchemy
loggers, is switched off, unless the file names it or a logger above it (as
``privacyidea`` is above ``privacyidea.lib.token``). A YAML file that configures
only ``root`` would switch off all loggers of privacyIDEA.

Different handlers can be used to send log messages to log-aggregators like
Splunk [#splunk]_ or Logstash [#logstash]_.

The old `python logging config file format <https://docs.python.org/3/library/logging.config
.html#logging-config-fileformat>`_ is also still supported::

   [formatters]
   keys=detail

   [handlers]
   keys=file,mail

   [formatter_detail]
   class=privacyidea.lib.log.SecureFormatter
   format=[%(asctime)s][%(process)d][%(thread)d][%(levelname)s][%(name)s:%(lineno)d] %(message)s

   [handler_mail]
   class=logging.handlers.SMTPHandler
   level=ERROR
   formatter=detail
   args=('mail.example.com', 'privacyidea@example.com', ['admin1@example.com',\
      'admin2@example.com'], 'PI Error')

   [handler_file]
   # Rotate the logfile at 10 MB, keep 14 old files
   class=logging.handlers.RotatingFileHandler
   backupCount=14
   maxBytes=10000000
   formatter=detail
   level=DEBUG
   args=('/var/log/privacyidea/privacyidea.log',)

   [loggers]
   keys=root,privacyidea

   [logger_privacyidea]
   handlers=file,mail
   qualname=privacyidea
   level=DEBUG
   propagate=0

   [logger_root]
   level=ERROR
   handlers=file


.. note:: These examples define a mail handler that sends emails to certain
   email addresses if an ERROR occurs. All other messages are logged to a file:
   DEBUG and higher in the cfg example, INFO and higher in the YAML example.

.. note:: The filename extension is irrelevant in this case

The logging config can also be used to send the log to a syslog server::

    [formatters]
    keys=detail

    [formatter_detail]
    class=privacyidea.lib.log.SecureFormatter
    format=[%(asctime)s][%(process)d][%(thread)d][%(levelname)s][%(name)s:%(lineno)d] %(message)s

    [handlers]
    keys=audit

    [handler_audit]
    class=logging.handlers.SysLogHandler
    args=(('192.168.121.193', handlers.SYSLOG_UDP_PORT), handlers.SysLogHandler.LOG_LOCAL0)
    formatter=detail
    level=INFO
    propagate=0

    [loggers]
    keys=root

    [logger_root]
    level=INFO
    handlers=audit

.. rubric:: Footnotes

.. [#yaml] https://yaml.org/
.. [#splunk] https://www.splunk.com/
.. [#logstash] https://www.elastic.co/logstash
