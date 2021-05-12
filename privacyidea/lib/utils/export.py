# -*- coding: utf-8 -*-

import logging

log = logging.getLogger(__name__)

EXPORT_FUNCTIONS = {}
IMPORT_FUNCTIONS = {}


def register_export(name=None):
    def wrapped(func):
        # TODO: this doesn't work since the logging configuration is not
        #       initialized during imports
        # log.debug('Registering export function {0!s} with name {1!s}'.format(func, name))
        exp_name = name
        if not exp_name:
            exp_name = func.__module__.split('.')[-1]
        # TODO: check if name already exists in register
        EXPORT_FUNCTIONS[exp_name] = func
        return func
    return wrapped


def register_import(name=None):
    def wrapped(func):
        # TODO: this doesn't work since the logging configuration is not
        #       initialized during imports
        # log.debug('Registering export function {0!s} with name {1!s}'.format(func, name))
        imp_name = name
        if not imp_name:
            imp_name = func.__module__.split('.')[-1]
        # TODO: check if name already exists in register
        IMPORT_FUNCTIONS[imp_name] = func
        return func
    return wrapped
