# -*- coding: utf-8 -*-
import codecs

from pyparsing import Literal, White, Word, alphanums, CharsNotIn
from pyparsing import Forward, Group, Optional, OneOrMore, ZeroOrMore
from pyparsing import pythonStyleComment, Regex


class BaseParser(object):
    
    def get(self):
        """
        return the grouped config
        """
        return
    
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

    def format(self, dict_config):
        '''
        :return: The formatted data as it would be written to a file
        '''
        return
    
    def save(self, dict_config=None, outfile=None):
        if not outfile:
            outfile = self.file
        if dict_config:
            output = self.format(dict_config)
            f = codecs.open(outfile, 'w', 'utf-8')
            for line in output.splitlines():
                f.write(line + "\n")
            f.close()


class ClientConfParser(BaseParser):

    key = Word(alphanums + "_")
    client_key = Word(alphanums + "-_/.:")
    space = White().suppress()
    value = CharsNotIn("{}\n# ")
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
    
    def __init__(self,
                 infile="/etc/freeradius/clients.conf",
                 content=None):
        self.file = None
        if content:
            self.content = content
        else:
            self.file = infile
            self._read()

    def _read(self):
        """
        Reread the contents from the disk
        """
        f = codecs.open(self.file, "r", "utf-8")
        self.content = f.read()
        f.close()
        
    def get(self):
        """
        return the grouped config
        """
        if self.file:
            self._read()
        config = self.client_file.parseString(self.content)
        return config
    
    def format(self, dict_config):
        '''
        :return: The formatted data as it would be written to a file
        '''
        output = ""
        output += self.file_header
        for client, attributes in dict_config.iteritems():
            output += "client %s {\n" % client
            for k, v in attributes.iteritems():
                output += "    %s = %s\n" % (k, v)
            output += "}\n\n"
        return output


class UserConfParser(BaseParser):
    
    key = Word(alphanums + "-")
    username = Word(alphanums + "@_.-/")
    client_key = Word(alphanums + "-_/.:")
    space = White().suppress()
    comma = (",")
    value = CharsNotIn("{}\n#, ")
    comment = ("#")
    # operator = ":="
    operator = Regex(":=|==|=|\+=|!=|>|>=|<|<=|=~|!~|=\*|!\*")
    assignment = Group(space
                       + key
                       + space.suppress()
                       + operator
                       + space.suppress()
                       + value
                       + ZeroOrMore(space).suppress()
                       + ZeroOrMore(comma).suppress())
    user_block = Forward()
    # USERNAME key operator value
    # <tab> key operator value
    user_block << Group(username
                        + space
                        + key
                        + operator
                        + space
                        + value
                        + Group(ZeroOrMore(assignment)))
    
    user_file = OneOrMore(user_block).ignore(pythonStyleComment)
    
    file_header = """# File parsed and saved by privacyidea.\n\n"""
    
    def __init__(self,
                 infile="/etc/freeradius/users",
                 content=None):
        self.file = None
        if content:
            self.content = content
        else:
            self.file = infile
            f = codecs.open(self.file, "r", "utf-8")
            self.content = f.read()
            f.close()
            
    def get(self):
        """
        return the grouped config
        
        something like this:
        [
        ['DEFAULT', 'Framed-Protocol', '==', 'PPP', [['Framed-Protocol', '=', 'PPP'], ['Framed-Compression', '=', 'Van-Jacobson-TCP-IP']]],
        ['DEFAULT', 'Hint', '==', '"CSLIP"', [['Framed-Protocol', '=', 'SLIP'], ['Framed-Compression', '=', 'Van-Jacobson-TCP-IP']]],
        ['DEFAULT', 'Hint', '==', '"SLIP"', [['Framed-Protocol', '=', 'SLIP']]]
        ]
        """
        config = self.user_file.parseString(self.content)
        return config
    
    def format(self, config):
        '''
        :return: The formatted data as it would be written to a file
        '''
        output = ""
        output += self.file_header
        for user in config:
            output += "%s %s %s %s\n" % (user[0], user[1], user[2], user[3])
            if len(user[4]):
                i = 0
                for reply_item in user[4]:
                    i += 1
                    output += "\t%s %s %s" % (reply_item[0],
                                              reply_item[1],
                                              reply_item[2])
                    if i < len(user[4]):
                        output += ","
                    output += "\n"
            output += "\n"
        return output
        

def main():  # pragma: no cover
    CP = ClientConfParser()
    config = CP.get_dict()
    # Here we could mangle with the config...
    CP.save(config, infile="/etc/freeradius/clients.conf.new")
    

if __name__ == '__main__':
    main()