.. _debug_log:

Debugging and Logging
---------------------

.. index:: Debugging, Logging

You can set ``PI_LOGLEVEL`` to a value 10 (Debug), 20 (Info), 30 (Warngin),
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

   [loggers]
   keys=privacyidea

   [formatters]
   keys=detail

   [formatter_detail]
   class=privacyidea.lib.log.SecureFormatter
   format=[%(asctime)s][%(process)d][%(thread)d][%(levelname)s]\
      [%(name)s:%(lineno)d] %(message)s

   [logger_privacyidea]
   handler=file
   qualname=privacyidea
   level=DEBUG

   [handlers]
   keys=file

   [handler_file]
   # Rollover the logfile at midnight
   class=handlers.TimeRotatingFileHandler
   backupCount=14
   interval=midnight
   formatter=detail
   level=DEBUG
   args=('/var/log/privacyidea/privacyidea.log',)

The file structure follows [#fileconfig]_ and can be used to define additional
handlers like logging errors to email addresses.

.. note:: Thus administrators can get email notification if some severe error
   occurs.

.. rubric:: Footnotes

.. [#fileconfig] https://docs.python.org/2/library/logging.config.html#configuration-file-format
