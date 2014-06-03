from logging import Formatter
import string
import logging
import functools
log = logging.getLogger(__name__)

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
    '''Logging decorator that allows you to log with a
    specific logger.
    '''
    # Customize these messages
    ENTRY_MESSAGE = u'Entering {0} with arguments {1} and keywords {2}'
    EXIT_MESSAGE = 'Exiting {0} with result {1}'
    
    def __init__(self, logger=None, log_entry=True, log_exit=True):
        self.logger = logger
        self.log_exit = log_exit
        self.log_entry = log_entry

    def __call__(self, func):
        '''Returns a wrapper that wraps func.
        The wrapper will log the entry and exit points of the function
        with logging.INFO level.
        '''
        # set logger if it was not set earlier
        if not self.logger:
            logging.basicConfig()
            self.logger = logging.getLogger(func.__module__)
            
        @functools.wraps(func)
        def wrapper(*args, **kwds):
            try:
                if self.log_entry:
                    self.logger.debug(self.ENTRY_MESSAGE.format(func.__name__, args, kwds))
                else:
                    self.logger.debug(self.ENTRY_MESSAGE.format(func.__name__, "HIDDEN", "HIDDEN"))
            except Exception as exx:
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
        
        return wrapper
