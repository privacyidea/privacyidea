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
from copy import deepcopy
log = logging.getLogger(__name__)


DEFAULT_LOGGING_CONFIG = {
    "version": 1,
    "formatters": {
        "detail": {
            "()": "privacyidea.lib.log.SecureFormatter",
            "format": "[%(asctime)s][%(process)d]"
                      "[%(thread)d][%(levelname)s]"
                      "[%(name)s:%(lineno)d] "
                      "%(message)s"
        }
    },
    "handlers": {
        "file": {
            "formatter": "detail",
            "class": "logging.handlers.RotatingFileHandler",
            "backupCount": 5,
            "maxBytes": 10000000,
            "level": logging.DEBUG,
            "filename": "privacyidea.log"
        }
    },
    "loggers": {"privacyidea": {"handlers": ["file"],
                                "qualname": "privacyidea",
                                "level": logging.INFO}
                }
}


class SecureFormatter(Formatter):

    def format(self, record):
        message = super(SecureFormatter, self).format(record)
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
    ENTRY_MESSAGE = 'Entering {0} with arguments {1} and keywords {2}'
    EXIT_MESSAGE = 'Exiting {0} with result {1}'

    def __init__(self, logger=None, log_entry=True, log_exit=True,
                 hide_args=None, hide_kwargs=None,
                 hide_args_keywords=None):
        """
        Write the parameters and the result of the function to the log.

        :param logger: The logger object.
        :param log_entry: Whether the function parameters should be logged
        :type log_entry: bool
        :param log_exit: Whether the result of the function should be logged
        :type log_exit: bool
        :param hide_args: List of parameters, which should be hidden in the
            log entries. This is a list of parameter indices.
        :type hide_args: list of int
        :param hide_kwargs: list of key word arguments, that should be hidden
            from the log entry.
        :type hide_kwargs: list of keywords
        :param hide_args_keywords: Hide the keywords in positional arguments,
            if the positional argument is a dictionary
        :type hide_args_keywords: dict
        """
        self.logger = logger
        self.log_exit = log_exit
        self.log_entry = log_entry
        self.hide_args = hide_args or []
        self.hide_kwargs = hide_kwargs or []
        self.hide_args_keywords = hide_args_keywords or {}

    def __call__(self, func):
        """
        Returns a wrapper that wraps func.
        The wrapper will log the entry and exit points of the function
        with logging.INFO level.

        :param func: The function that is decorated
        :return: function
        """

        @functools.wraps(func)
        def log_wrapper(*args, **kwds):
            """
            Wrap the function in log entries. The entry of the function and
            the exit of the function is logged using the DEBUG log level.
            If the logger does not log DEBUG messages, this just returns
            the result of ``func(*args, **kwds)`` to improve performance.

            :param args: The positional arguments starting with index
            :type args: tuple
            :param kwds: The keyword arguments
            :type kwds: dict
            :return: The wrapped function
            """
            # Exit early if self.logger disregards DEBUG messages.
            if not self.logger.isEnabledFor(logging.DEBUG):
                return func(*args, **kwds)

            log_args = args
            log_kwds = kwds
            if self.hide_args or self.hide_kwargs or \
                    self.hide_args_keywords:
                try:
                    level = self.logger.getEffectiveLevel()
                    # Check if we should not do the password logging.
                    # I.e. we only do password logging if log_level < 10.
                    if level != 0 and level >= 10:
                        # Hide specific arguments or keyword arguments
                        log_args = list(deepcopy(args))
                        log_kwds = deepcopy(kwds)
                        for arg_index in self.hide_args:
                            log_args[arg_index] = "HIDDEN"
                        for keyword in self.hide_kwargs:
                            log_kwds[keyword] = "HIDDEN"
                        for k, v in self.hide_args_keywords.items():
                            for keyword in v:
                                if keyword in args[k]:
                                    log_args[k][keyword] = "HIDDEN"
                except Exception:
                    # Probably the deepcopy fails, due to special objects in the
                    # args But as we are asked to hide a parameter, we hide
                    # them all!
                    log_args = ()
                    log_kwds = {}
            try:
                if self.log_entry:
                    self.logger.debug(self.ENTRY_MESSAGE.format(
                        func.__name__, log_args, log_kwds))
                else:
                    self.logger.debug(self.ENTRY_MESSAGE.format(
                        func.__name__, "HIDDEN", "HIDDEN"))
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
