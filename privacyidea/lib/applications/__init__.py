

class MachineApplicationBase(object):

    application_name = "base"
        
    @classmethod
    def get_name(self):
        '''
        returns the identifying name of this application class
        '''
        return self.application_name

