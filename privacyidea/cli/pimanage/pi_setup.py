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

import sys
import click
from flask.cli import AppGroup

from privacyidea.lib.security.default import DefaultSecurityModule

setup_cli = AppGroup("setup", short_help="privacyIDEA server setup",
                     help="Commands to setup the privacyIDEA server for production")


@setup_cli.command("encrypt_enckey", short_help="Additionally encrypt the encryption key")
@click.argument("encfile", type=click.File("rb"))
@click.option("-o", "--outfile", type=click.File("w"), default=sys.stdout,
              help="The file to which the encrypted encryption key will be "
                   "written to (default: stdout)")
@click.password_option()
def encrypt_enckey(encfile, outfile, password):
    """
    You will be asked for a password and the encryption key in the specified
    file will be encrypted with an AES key derived from your password.

    The encryption key in the file is a 96 bit binary key.

    The password based encrypted encryption key is a hex combination of an IV
    and the encrypted data.

    The result can be piped to a new enckey file.
    """
    # TODO we just print out a string here and assume, the user pipes it into a file.
    #      Maybe we should write the file here so we know what is in there
    # TODO: get the name/path of the encfile from the pi.cfg
    enckey = encfile.read()
    res = DefaultSecurityModule.password_encrypt(enckey, password)
    outfile.write(res)
    outfile.write('\n')


@setup_cli.command("create_enckey")
def create_enckey():
    """Create a key for encrypting the sensitive database entries"""
    pass


@setup_cli.command("create_pgp_keys")
def create_pgp_keys():
    pass


@setup_cli.command("create_audit_keys")
def create_audit_keys():
    pass


@setup_cli.command("create_tables")
def create_tables():
    pass


@setup_cli.command("drop_tables")
def drop_tables():
    pass
