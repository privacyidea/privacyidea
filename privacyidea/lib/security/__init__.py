import logging
log = logging.getLogger(__name__)



class SecurityModule(object):

    def __init__(self, config=None):
        log.error("This is the base class. You should implement this!")
        self.name = "SecurityModule"

    def isReady(self):
        fname = 'isReady'
        log.error("This is the base class. You should implement "
                  "the method : %s " % (fname,))
        raise NotImplementedError("Should have been implemented %s"
                                   % fname)

    def setup_module(self, params):
        fname = 'setup_module'
        log.error("This is the base class. You should implement "
                  "the method : %s " % (fname,))
        raise NotImplementedError("Should have been implemented %s"
                                   % fname)

    ''' base methods '''
    def random(self, len):
        fname = 'random'
        log.error("This is the base class. You should implement "
                  "the method : %s " % (fname,))
        raise NotImplementedError("Should have been implemented %s"
                                   % fname)

    def encrypt(self, value, iv=None):
        fname = 'encrypt'
        log.error("This is the base class. You should implement "
                  "the method : %s " % (fname,))
        raise NotImplementedError("Should have been implemented %s"
                                   % fname)

    def decrypt(self, value, iv=None):
        fname = 'decrypt'
        log.error("This is the base class. You should implement "
                  "the method : %s " % (fname,))
        raise NotImplementedError("Should have been implemented %s"
                                   % fname)


    ''' higer level methods '''
    def encryptPassword(self, cryptPass):
        fname = 'decrypt'
        log.error("This is the base class. You should implement "
                  "the method : %s " % (fname,))
        raise NotImplementedError("Should have been implemented %s"
                                   % fname)

    def encryptPin(self, cryptPin):
        fname = 'decrypt'
        log.error("This is the base class. You should implement "
                  "the method : %s " % (fname,))
        raise NotImplementedError("Should have been implemented %s"
                                   % fname)


    def decryptPassword(self, cryptPass):
        fname = 'decrypt'
        log.error("This is the base class. You should implement "
                  "the method : %s " % (fname,))
        raise NotImplementedError("Should have been implemented %s"
                                   % fname)

    def decryptPin(self, cryptPin):
        fname = 'decrypt'
        log.error("This is the base class. You should implement "
                  "the method : %s " % (fname,))
        raise NotImplementedError("Should have been implemented %s"
                                   % fname)


#eof###########################################################################

