# -*- coding: utf-8 -*-
#
#  privacyIDEA is a fork of LinOTP
#  May 08, 2014 Cornelius Kölbel
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  Copyright (C) 2010 - 2014 LSE Leading Security Experts GmbH
#  License:  AGPLv3
#  contact:  http://www.linotp.org
#            http://www.lsexperts.de
#            linotp@lsexperts.de
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# License as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#  
from logging import Formatter
import string
import logging
import functools
log = logging.getLogger(__name__)


DEFAULT_LOGGING_CONFIG = {
    "version": 1,
    "formatters": {"detail": {"class":
                                  "privacyidea.lib.log.SecureFormatter",
                              "format": "[%(asctime)s][%(process)d]"
                                        "[%(thread)d][%(levelname)s]"
                                        "[%(name)s:%(lineno)d] "
                                        "%(message)s"}
                       },
    "handlers": {"file": {"formatter": "detail",
                          "class":
                              "logging.handlers.RotatingFileHandler",
                          "backupCount": 5,
                          "maxBytes": 10000000,
                          "level": logging.DEBUG,
                          "filename": "privacyidea.log"}
                         },
    "loggers": {"privacyidea": {"handlers": ["file"],
                                "qualname": "privacyidea",
                                "level": logging.INFO}
                }
}

class SecureFormatter(Formatter):

    bad_chars = "\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0b\x0c\x0d\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19"

    def format(self, record):
        try:
            message = super(SecureFormatter, self).format(record)
        except TypeError:
            # In pyhton 2.6 the Formatter does not seem to 
            # be defined as 
            # class Formatter(object)
            # Using it in the super-statement this will raise a TypeError
            message = Formatter.format(self, record)
        secured = False

        s = ""
        for c in message:
            if c in string.printable:
                s += c
            else:
                s += '.'
                secured = True

        if secured:
            s = "!!!Log Entry Secured by SecureFormatter!!! " + s

        return s


class log_with(object):
    """
    Logging decorator that allows you to log with a
    specific logger.
    """
    # Customize these messages
    ENTRY_MESSAGE = u'Entering {0} with arguments {1} and keywords {2}'
    EXIT_MESSAGE = 'Exiting {0} with result {1}'
    
    def __init__(self, logger=None, log_entry=True, log_exit=True):
        self.logger = logger
        self.log_exit = log_exit
        self.log_entry = log_entry

    def __call__(self, func):
        """
        Returns a wrapper that wraps func.
        The wrapper will log the entry and exit points of the function
        with logging.INFO level.

        :param func: The function that is decorated
        :return: function
        """
        # set logger if it was not set earlier
        if not self.logger:
            logging.basicConfig()
            self.logger = logging.getLogger(func.__module__)
            
        @functools.wraps(func)
        def log_wrapper(*args, **kwds):
            try:
                if self.log_entry:
                    self.logger.debug(self.ENTRY_MESSAGE.format(func.__name__, args, kwds))
                else:
                    self.logger.debug(self.ENTRY_MESSAGE.format(func.__name__, "HIDDEN", "HIDDEN"))
            except Exception as exx:
                self.logger.error(exx)
                self.logger.error("Error during logging of function {0}! {1}".format(func.__name__, exx))
                
            f_result = func(*args, **kwds)
            
            try:
                if self.log_exit:
                    self.logger.debug(self.EXIT_MESSAGE.format(func.__name__, f_result))
                else:
                    self.logger.debug(self.EXIT_MESSAGE.format(func.__name__, "HIDDEN"))
            except Exception as exx:
                self.logger.error("Error during logging of function {0}! {1}".format(func.__name__, exx))
            return f_result
        
        return log_wrapper
