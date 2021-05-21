# -*- coding: utf-8 -*-

#  2021-22-20 Paul Lettich <paul.lettich@netknights.it>
#             Initial creation of import/export functionality
#
# (c) Cornelius Kölbel
# Info: http://www.privacyidea.org
#
# This code is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import sys

EXPORT_FUNCTIONS = {}
IMPORT_FUNCTIONS = {}


def register_export(name=None):
    def wrapped(func):
        exp_name = name
        if not exp_name:
            exp_name = func.__module__.split('.')[-1]
        if exp_name in EXPORT_FUNCTIONS:
            print('Exporter function with name \'{0!s}\' already exists! '
                  'Overwriting {1!s} with {2!s}'.format(exp_name,
                                                        EXPORT_FUNCTIONS[exp_name],
                                                        func), file=sys.stderr)
        EXPORT_FUNCTIONS[exp_name] = func
        return func
    return wrapped


def register_import(name=None, prio=99):
    def wrapped(func):
        imp_name = name
        if not imp_name:
            imp_name = func.__module__.split('.')[-1]
        if imp_name in IMPORT_FUNCTIONS:
            print('Importer function with name \'{0!s}\' already exists! '
                  'Overwriting {1!s} with {2!s}'.format(imp_name,
                                                        IMPORT_FUNCTIONS[imp_name],
                                                        func), file=sys.stderr)
        IMPORT_FUNCTIONS[imp_name] = {'prio': prio,
                                      'func': func}
        return func
    return wrapped
