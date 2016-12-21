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

Advanced Logging
~~~~~~~~~~~~~~~~

You can also define a more detailed logging by specifying a log configuration
file like this::

   PI_LOGCONFIG = "/etc/privacyidea/logging.cfg"

Such a configuration could look like this::

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


The file structure follows [#fileconfig]_ and can be used to define additional
handlers like logging errors to email addresses.

.. note:: In this example a mail handler is defined, that will send emails
   to certain email addresses, if an ERROR occurs.

.. rubric:: Footnotes

.. [#fileconfig] https://docs.python.org/2/library/logging.config.html#configuration-file-format
