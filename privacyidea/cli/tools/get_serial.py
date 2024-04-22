# SPDX-FileCopyrightText: (C) 2024 Paul Lettich <paul.lettich@netknights.it>
#
# SPDX-FileCopyrightText: (C) 2016 Cornelius Kölbel <cornelius.koelbel@netknights.it>
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
__doc__ = """
This script searches the OTP value in a given list of tokens.
The searched tokens are determined by tokentype, substring of the serial,
assigned status...

The serial number of the token is returned.

You can call the script like this:

    privacyidea-get-serial byotp --otp <otp> --type <type> --serial <serial>
        --unassigned --assigned --window <window>

"""
__version__ = "0.1"

import click
from flask.cli import with_appcontext, ScriptInfo

from privacyidea.lib.token import get_tokens, get_serial_by_otp
from privacyidea.lib.utils import get_version_number
from privacyidea.cli import create_silent_app

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('-a', '--assigned', is_flag=True,
              help='If set, search only assigned tokens')
@click.option('-u', '--unassigned', is_flag=True,
              help='If set, search only unassigned tokens')
@click.option('-w', '--window', type=int, default=10, show_default=True,
              help="The OTP window for calculating OTP values. Default=10")
@click.option('-s', '--serial', type=str, default="",
              help="A part of the token serial number")
@click.option('-t', '--type', 'tokentype', type=str, default=None,
              help="The tokentype like hotp, totp, ...")
@click.argument('otp')
@with_appcontext
def byotp(otp, tokentype, serial, window, unassigned, assigned):
    """
    This searches the list of the specified tokens for the given OTP value.
    """
    if not assigned and not unassigned:
        assigned = None
    count = get_tokens(tokentype=tokentype, serial_wildcard="*{0!s}*".format(
            serial), assigned=assigned, count=True)
    click.echo("Searching in {0!s} tokens.".format(count))

    tokenobj_list = get_tokens(tokentype=tokentype,
                               serial_wildcard="*{0!s}*".format(serial),
                               assigned=assigned)
    serial = get_serial_by_otp(tokenobj_list, otp=otp, window=window)
    if serial:
        click.echo("Found the token with serial {0!s}".format(serial))
    else:
        click.echo("No token found.")


def byotp_call():
    """Call the actual function with an initialized app"""
    click.echo(r"""
                 _                    _______  _______
       ___  ____(_)  _____ _______ __/  _/ _ \/ __/ _ |
      / _ \/ __/ / |/ / _ `/ __/ // // // // / _// __ |
     / .__/_/ /_/|___/\_,_/\__/\_, /___/____/___/_/ |_|  Get Serial
    /_/                       /___/
    {0!s:>51}
        """.format('v{0!s}'.format(get_version_number())))

    # Add the ScriptInfo object to create the Flask-App when necessary
    s = ScriptInfo(create_app=create_silent_app)
    byotp(obj=s)


if __name__ == '__main__':
    byotp_call()
