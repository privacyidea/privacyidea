# -*- coding: utf-8 -*-

""" Test module for a fancy token class """

from privacyidea.lib.tokenclass import TokenClass


class FancyTokenClass(TokenClass):
    def __init__(self, db_token):
        TokenClass.__init__(self, db_token)
        self.set_type("fancy")
        self.mode = ['authenticate']
        self.hKeyRequired = False

    @staticmethod
    def get_class_type():
        return 'fancy'

    @staticmethod
    def get_class_prefix():
        return "PIFA"
