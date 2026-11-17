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

"""
This module provides the functionality to register export or import functions
for separate parts of the privacyIDEA server configuration.
"""
import logging
import sys
from collections.abc import Callable, Iterable

from privacyidea.lib.error import ConfigAdminError
from privacyidea.lib.log import get_key_names
from privacyidea.models import db

log = logging.getLogger(__name__)

EXPORT_FUNCTIONS = {}
IMPORT_FUNCTIONS = {}


def register_export(name=None):
    """
    This decorator is supposed to decorate a function that exports the
    configuration data from a given module like resolvers, realms, events, ...

    The decorated exporter function needs to return a dictionary which contains
    all the necessary data to (re-)create that module.

    :param name: The name with which the function will be registered.
                 If omitted, the name of the module will be used.
    :type name: str

    ** Usage**:

        .. sourcecode:: python

            @register_export
            def export_events():
                # implement export functionality here
                return dict

"""
    def wrapped(func):
        exp_name = name
        if not exp_name:
            exp_name = func.__module__.split('.')[-1]
        if exp_name in EXPORT_FUNCTIONS:
            print(f'Exporter function with name \'{exp_name!s}\' already exists! '
                  f'Overwriting {EXPORT_FUNCTIONS[exp_name]!s} with {func!s}', file=sys.stderr)
        EXPORT_FUNCTIONS[exp_name] = func
        return func
    return wrapped


def register_import(name=None, prio=99):
    """
    This decorator is supposed to decorate a function that imports the
    configuration data for a given module like resolvers, realms, events, ...

    The decorated importer function takes a dictionary which contains
    the data necessary to (re-)create that module.

    Some modules require that other modules already exists (like realms need
    existing resolvers). To ensure the order of the import, a priority can be
    assigned to the registered importer function (lower comes first).

    :param name: The name with which the function will be registered.
                 If omitted, the name of the module will be used.
    :type name: str
    :param prio: The priority of the importer function, default is 99.
    :type prio: int

    ** Usage**:

        .. sourcecode:: python

            @register_import(prio=10)
            def import_events(dict):
                # implement import functionality here

"""

    def wrapped(func):
        imp_name = name
        if not imp_name:
            imp_name = func.__module__.split('.')[-1]
        if imp_name in IMPORT_FUNCTIONS:
            print(f'Importer function with name \'{imp_name!s}\' already exists! '
                  f'Overwriting {IMPORT_FUNCTIONS[imp_name]!s} with {func!s}', file=sys.stderr)
        IMPORT_FUNCTIONS[imp_name] = {'prio': prio,
                                      'func': func}
        return func
    return wrapped


def get_import_names(data: dict | list, name_key: str = "name") -> list:
    """
    Return the names of the configuration objects in the data an importer gets, for a log message that says which
    objects are imported. The settings of the objects are not part of it, they hold the credentials of the objects
    in plain text.

    :param data: a dict of the objects by their names, or a list of the objects
    :param name_key: the key under which an object in a list holds its name
    :return: the names of the objects
    """
    if isinstance(data, dict):
        return get_key_names(data)
    if isinstance(data, list):
        return [entry.get(name_key) for entry in data if isinstance(entry, dict)]
    return []


def import_entries(entries: Iterable[tuple[str, dict]], import_entry: Callable[[str, dict], int], label: str,
                   error_class: type[Exception] = ConfigAdminError) -> list[str]:
    """
    Import the entries of one part of the configuration independently of each other.

    If an entry can not be imported, the database session is rolled back and the
    remaining entries are still imported. After all entries have been processed,
    an error lists the entries that failed and the entries that were imported.

    :param entries: the name and the data of each entry
    :param import_entry: the function that imports one entry. It is called with
        the name and the data of the entry and returns the database id.
    :param label: what the entries are, in plural, used in the log and in the
        error message (e.g. "SMTP servers")
    :param error_class: the exception that is raised if an entry failed
    :return: the names of the imported entries
    :raises error_class: if at least one entry could not be imported
    """
    imported = []
    failed = {}
    for name, data in entries:
        try:
            rid = import_entry(name, data)
        except Exception as e:
            # Leave the session usable for the next entry
            db.session.rollback()
            log.warning(f'Could not import "{name!s}" of the {label}: {e!s}')
            failed[name] = e
            continue
        imported.append(name)
        log.info(f'Import of "{name!s}" of the {label} finished, id: {rid!s}')

    if failed:
        failure_summary = ', '.join(f'"{n}" ({e!s})' for n, e in failed.items())
        raise error_class(f"Could not import the following {label}: "
                          f"{failure_summary}. Successfully imported: {imported}.")
    return imported
