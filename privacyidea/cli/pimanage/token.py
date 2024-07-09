# SPDX-FileCopyrightText: (C) 2023 Paul Lettich <paul.lettich@netknights.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Info: https://privacyidea.org
#
# This code is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License
# as published by the Free Software Foundation, either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program. If not, see <http://www.gnu.org/licenses/>.
"""CLI commands for managing tokens"""
import click
from flask.cli import AppGroup
from privacyidea.lib.token import import_token
from privacyidea.lib.importotp import parseOATHcsv


token_cli = AppGroup("token", short_help="Manage tokens in privacyIDEA",
                     help="Commands to manage token in privacyIDEA")


@token_cli.command("import", short_help="Import tokens from a file")
@click.argument("file", type=click.File())
@click.option("-t", "--tokenrealm", multiple=True, default=[],
              help="The realms in which the tokens should be imported (can be "
                   "used multiple times)")
def import_tokens(file, tokenrealm):
    """
    Import Tokens from CSV data in FILE
    """
    contents = file.read()
    tokens = parseOATHcsv(contents)
    i = 0
    for serial in tokens:
        i += 1
        print(u"{0!s}/{1!s} Importing token {2!s}".format(i, len(tokens), serial))

        import_token(serial, tokens[serial], tokenrealms=tokenrealm)
