# -*- coding: utf-8 -*-

import logging

log = logging.getLogger(__name__)

EXPORT_FUNCTIONS = {}
IMPORT_FUNCTIONS = {}


def register_export_name(name):
    def wrapped(func):
        # TODO: this doesn't work since the logging configuration is not
        #       initialized during imports
        # log.debug('Registering export function {0!s} with name {1!s}'.format(func, name))
        EXPORT_FUNCTIONS[name] = func
        return func
    return wrapped


def register_import_name(name):
    def wrapped(func):
        # TODO: this doesn't work since the logging configuration is not
        #       initialized during imports
        # log.debug('Registering export function {0!s} with name {1!s}'.format(func, name))
        IMPORT_FUNCTIONS[name] = func
        return func
    return wrapped


def register_export(func):
    name = func.__module__.split('.')[-1]
    EXPORT_FUNCTIONS[name] = func
    return func


def register_import(func):
    name = func.__module__.split('.')[-1]
    IMPORT_FUNCTIONS[name] = func
    return func
