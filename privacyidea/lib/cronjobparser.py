# -*- coding: utf-8 -*-
import codecs

from pyparsing import White, Word, alphanums, CharsNotIn
from pyparsing import Forward, Group, OneOrMore
from pyparsing import pythonStyleComment
from privacyidea.lib.freeradiusparser import BaseParser


class CronJobParser(BaseParser):
    
    dtime = Word("0123456789-*")
    command = CharsNotIn("{}\n#,")
    username = Word(alphanums)
    key = Word(alphanums)
    value = command
    space = White().suppress()
    comment = Word("#")
    equals = Word("=")
    assignment = Forward()
    assignment << Group(key
                        + equals.suppress()
                        + value)
    entry_block = Forward()
    entry_block << Group(dtime
                         + space.suppress()
                         + dtime
                         + space.suppress()
                         + dtime
                         + space.suppress()
                         + dtime
                         + space.suppress()
                         + dtime
                         + space.suppress()
                         + username
                         + space.suppress()
                         + command
                         )
    cron_file = OneOrMore(entry_block | assignment).ignore(pythonStyleComment)
    
    file_header = """# File parsed and saved by privacyidea.\n\n"""
    
    def __init__(self,
                 infile="/etc/crontab",
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
        
        """
        # reread the file from dist
        if self.file:
            f = codecs.open(self.file, "r", "utf-8")
            self.content = f.read()
            f.close()
        config = self.cron_file.parseString(self.content)
        return config
    
    def format(self, config):
        '''
        :return: The formatted data as it would be written to a file
        '''
        output = ""
        output += self.file_header
        # write the assignments
        assignments = config.get("assignments")
        for assignment in assignments:
            output += "%s=%s\n" % (assignment,
                                   assignments.get(assignment))
        # write the cronjobs
        output += "\n#m\th\tdom\tmon\tdow\tuser\tcommand\n"
        cronjobs = config.get("cronjobs")
        for entry in cronjobs:
            output += "%s\t%s\t%s\t%s\t%s\t%s\t%s" % (entry.get("minute", "*"),
                                                      entry.get("hour", "*"),
                                                      entry.get("dom", "*"),
                                                      entry.get("month", "*"),
                                                      entry.get("dow", "*"),
                                                      entry.get("user"),
                                                      entry.get("command"))
            output += "\n"
        return output
    
    def get_dict(self):
        data = self.get()
        assignments = {}
        cronjobs = []
        for entry in data:
            if len(entry) == 2:
                assignments[entry[0]] = entry[1]
            elif len(entry) == 7:
                cronjobs.append({"minute": entry[0],
                                 "hour": entry[1],
                                 "dom": entry[2],
                                 "month": entry[3],
                                 "dow": entry[4],
                                 "user": entry[5],
                                 "command": entry[6]
                                 })
        
        return {"assignments": assignments,
                "cronjobs": cronjobs}


def main():  # pragma: no cover
    CP = CronJobParser()
    config = CP.get_dict()
    print CP.format(config)
        

if __name__ == '__main__':
    main()