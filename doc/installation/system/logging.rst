.. _debug_log:

Debugging and Logging
---------------------

.. index:: Debugging, Logging

You can set ``PI_LOGLEVEL`` to a value 10 (Debug), 20 (Info), 30 (Warning),
40 (Error) or 50 (Critical).
If you experience problems, set ``PI_LOGLEVEL = 10`` restart the web service
and resume the operation. The log file ``privacyidea.log`` should contain
some clues.

You can define the location of the logfile using the key ``PI_LOGFILE``.
Usually it is set to::

   PI_LOGFILE = "/var/log/privacyidea/privacyidea.log"

.. _advanced_logging:

Advanced Logging
~~~~~~~~~~~~~~~~

You can also define a more detailed logging by specifying a
log configuration file. By default the file is ``/etc/privacyidea/logging.cfg``.

You can change the location of the logging configuration file
in :ref:`cfgfile` like this::

   PI_LOGCONFIG = "/path/to/logging.yml"

Since Version 3.3 the logging configuration can be written in YAML [#yaml]_.
Such a YAML based configuration could look like this:

.. code-block:: yaml

    version: 1
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
        # Rollover the logfile at midnight
        class: logging.handlers.RotatingFileHandler
        backupCount: 5
        maxBytes: 1000000
        formatter: detail
        level: INFO
        filename: /var/log/privacyidea/privacyidea.log
      syslog:
        class: logging.handlers.SysLogHandler
        address: ('192.168.1.110', 514)
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

Different handlers can be used to send log messages to log-aggregators like
splunk [#splunk]_ or logstash [#logstash]_.

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
   # Rollover the logfile at midnight
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

   [logger_root]
   level=ERROR
   handlers=file

.. note:: These examples define a mail handler, that will send emails
   to certain email addresses, if an ERROR occurs. All other DEBUG messages will
   be logged to a file.

.. note:: The filename extension is irrelevant in this case

.. rubric:: Footnotes

.. [#yaml] https://yaml.org/
.. [#splunk] https://www.splunk.com/
.. [#logstash] https://www.elastic.co/logstash