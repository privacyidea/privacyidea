# -*- coding: utf-8 -*-
import codecs

from pyparsing import Literal, White, Word, alphanums, CharsNotIn
from pyparsing import Forward, Group, Optional, OneOrMore, ZeroOrMore
from pyparsing import pythonStyleComment


class ClientConfParser(object):

    key = Word(alphanums + "_")
    client_key = Word(alphanums + "_/.:")
    space = White().suppress()
    value = CharsNotIn("{}\n#")
    comment = ("#")
    assignment = (key
                  + Optional(space)
                  + Literal("=").suppress()
                  + Optional(space)
                  + value
                  + Optional(space)
                  + Optional("#"))
    client_block = Forward()
    client_block << Group((Literal("client").suppress()
                          + space
                          + client_key)
                          + Literal("{").suppress()
                          + Group(ZeroOrMore(Group(assignment)))
                          + Literal("}").suppress()
                          )
    
    client_file = OneOrMore(client_block).ignore(pythonStyleComment)
    
    file_header = """# File parsed and saved by privacyidea.\n\n"""
    
    def __init__(self, infile="/etc/freeradius/clients.conf"):
        self.file = infile
        f = codecs.open(self.file, "r", "utf-8")
        self.content = f.read()
        f.close()

    def get(self):
        """
        return the grouped config
        """
        config = self.client_file.parseString(self.content)
        return config
    
    def get_dict(self):
        '''
        return the client config as a dictionary.
        '''
        ret = {}
        config = self.get()
        for client in config:
            client_config = {}
            for attribute in client[1]:
                client_config[attribute[0]] = attribute[1]
            ret[client[0]] = client_config
        return ret
    
    def dump(self):
        conf = self.get()
        for client in conf:
            print "%s: %s" % (client[0], client[1])

    def save(self, dict_config=None, outfile=None):
        if not outfile:
            outfile = self.file
        if dict_config:
            f = codecs.open(outfile, 'w', 'utf-8')
            f.write(self.file_header)
            for client, attributes in dict_config.iteritems():
                f.write("client %s {\n" % client)
                for k, v in attributes.iteritems():
                    f.write("    %s = %s\n" % (k, v))
                f.write("}\n\n")
            f.close()


class UserConfParser(object):
    
    def __init__(self, infile="/etc/freeradius/users"):
        self.file = infile
        f = codecs.open(self.file, "r", "utf-8")
        self.content = f.read()
        f.close()
        
        

def main():
    CP = ClientConfParser()
    config = CP.get_dict()
    # Here we could mangle with the config...
    CP.save(config, infile="/etc/freeradius/clients.conf.new")
    

if __name__ == '__main__':
    main()