# SPDX-FileCopyrightText: (C) 2024 Paul Lettich <paul.lettich@netknights.it>
#
# SPDX-FileCopyrightText: (C) 2018 Friedrich Weber <friedrich.weber@netknights.it>
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
"""
This script can be used to create a self-contained local privacyIDEA
instance that does not require a web server to run. Instead,
authentication requests are validated via the command line.

The ``create`` command launches a wizard that creates a new instance.
The ``configure`` command starts a local development server that can
be used to setup tokens. This server must not be exposed to the network!
The ``check`` command can then be used to authenticate users.
"""

import click
import functools
import json
import os
from pathlib import Path
import shutil
import string
import subprocess  # nosec B404 # only trusted input is used
from tempfile import NamedTemporaryFile

from privacyidea.app import create_app
from privacyidea.lib.security.default import DefaultSecurityModule
from privacyidea.lib.utils import get_version_number

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

# warnings.simplefilter("ignore", category=sqlalchemy.exc.SAWarning)

PI_CFG_TEMPLATE = """import os, logging

INSTANCE_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
PI_ENCFILE = os.path.join(INSTANCE_DIRECTORY, 'encKey')
PI_AUDIT_KEY_PRIVATE = os.path.join(INSTANCE_DIRECTORY, 'private.pem')
PI_AUDIT_KEY_PUBLIC = os.path.join(INSTANCE_DIRECTORY, 'public.pem')
PI_AUDIT_SQL_TRUNCATE = True
PI_LOGFILE = os.path.join(INSTANCE_DIRECTORY, 'privacyidea.log')
PI_LOGLEVEL = logging.INFO
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(INSTANCE_DIRECTORY, 'privacyidea.sqlite')

SECRET_KEY = b'{secret_key}'
PI_PEPPER = '{pi_pepper}'

"""

RSA_KEYSIZE = 2048
PEPPER_CHARSET = string.ascii_letters + string.digits + '_'


def invoke_pi_manage(commandline, pi_cfg):
    """
    Invoke ``pi-manage`` with arguments, setting PRIVACYIDEA_CONFIGFILE TO ``pi_cfg``.

    :param commandline: arguments to pass as a list
    :type commandline: list
    :param pi_cfg: location of the privacyIDEA config file
    :type pi_cfg: str or pathlib.Path
    """
    environment = os.environ.copy()
    environment['PRIVACYIDEA_CONFIGFILE'] = str(pi_cfg)
    subprocess.check_call(['pi-manage'] + commandline, env=environment)  # nosec B603 # only trusted input is used


def instance_option(f):
    """The instance option for all commands"""
    options = [
        click.option('-i', '--instance', default=Path.home() / '.privacyidea',
                     help='Location of the privacyIDEA instance', show_default=True,
                     type=click.Path(file_okay=False, resolve_path=True))
    ]
    return functools.reduce(lambda x, opt: opt(x), options, f)


@click.group(context_settings=CONTEXT_SETTINGS,
             epilog='Check out our docs at https://privacyidea.readthedocs.io/ for more details')
def cli():
    """
\b
             _                    _______  _______
   ___  ____(_)  _____ _______ __/  _/ _ \\/ __/ _ |
  / _ \\/ __/ / |/ / _ `/ __/ // // // // / _// __ |
 / .__/_/ /_/|___/\\_,_/\\__/\\_, /___/____/___/_/ |_|  Standalone
/_/                       /___/

  Management script for creating local privacyIDEA instances."""
    click.echo(r"""
             _                    _______  _______
   ___  ____(_)  _____ _______ __/  _/ _ \/ __/ _ |
  / _ \/ __/ / |/ / _ `/ __/ // // // // / _// __ |
 / .__/_/ /_/|___/\_,_/\__/\_, /___/____/___/_/ |_|  Standalone
/_/                       /___/
{0!s:>51}
    """.format('v{0!s}'.format(get_version_number())))


@click.command()
@instance_option
@click.pass_context
def configure(ctx, instance):
    """Run a local webserver to configure the privacyIDEA instance."""
    instance = Path(instance)
    if instance.exists() and instance.joinpath('pi.cfg').exists():
        app = create_app(config_name="production", config_file=instance.joinpath('pi.cfg'),
                         silent=True)
        app.run()
    else:
        click.secho(f"Instance configuration at '{instance}/pi.cfg' does "
                    f"not exist! Aborting.", fg='red')
        ctx.exit(1)


@click.command()
@instance_option
@click.pass_context
def create(ctx, instance):
    """ Create a new privacyIDEA instance."""
    instance = Path(instance)
    if instance.exists():
        click.secho(f"Instance at '{instance}' already exists! Aborting.", fg='red')
        ctx.exit(1)
    try:
        instance.mkdir()

        # create SECRET_KEY and PI_PEPPER
        secret_key = DefaultSecurityModule.random(24)
        pi_pepper = create_pepper()

        secret_key_hex = ''.join('\\x{:02x}'.format(b) for b in secret_key)
        # create a pi.cfg
        pi_cfg = instance / 'pi.cfg'
        with open(pi_cfg, 'w') as f:
            f.write(PI_CFG_TEMPLATE.format(
                secret_key=secret_key_hex,
                pi_pepper=pi_pepper
            ))

        # create an enckey
        invoke_pi_manage(['create_enckey'], pi_cfg)
        invoke_pi_manage(['create_audit_keys'], pi_cfg)
        invoke_pi_manage(['create_tables'], pi_cfg)

        click.secho('Please enter a password for the new admin `super`.', fg='blue')
        invoke_pi_manage(['admin', 'add', 'super'], pi_cfg)

        # create user resolver
        if click.confirm('Would you like to create a default resolver and realm?', default=True):
            click.echo("""
There are two possibilities to create a resolver:
 1) We can create a table in the privacyIDEA SQLite database to store the users.
    You can add users via the privacyIDEA Web UI.
 2) We can create a resolver that contains the users from /etc/passwd
    """)
            create_sql_resolver = click.prompt('Please choose (default=1): ',
                                               default=1, type=click.Choice(['1', '2']),
                                               show_choices=False, show_default=False)
            if create_sql_resolver == 1:
                invoke_pi_manage(['resolver', 'create_internal', 'defresolver'], pi_cfg)
            else:
                with NamedTemporaryFile(mode='w', delete=False) as f:
                    f.write('{"fileName": "/etc/passwd"}')
                invoke_pi_manage(['resolver', 'create', 'defresolver', 'passwdresolver',
                                  f.name], pi_cfg)
                os.unlink(f.name)
            invoke_pi_manage(['realm', 'create', 'defrealm', 'defresolver'], pi_cfg)

        click.secho('Configuration is complete. You can now configure privacyIDEA in '
                    'the web browser by running', fg='blue')
        click.secho(f"  privacyidea-standalone configure -i '{instance}' ", fg='blue')
    except Exception as _e:
        click.secho(f'Could not finish creation process! Removing '
                    f'instance directory {instance}.', fg='red')
        shutil.rmtree(instance)
        raise


@click.command()
@click.option('-r', '--response', 'show_response', is_flag=True,
              help='Print the JSON response of privacyIDEA to standard output')
@click.option("-u", "--username", prompt=True,
              help="The username to authenticate")
@click.option("-p", "--password", prompt=True, hide_input=True,
              help="The password to authenticate the user")
@instance_option
@click.pass_context
def check(ctx, instance, show_response, username, password):
    """
    Check the given username and password against privacyIDEA.
    This command reads two lines from standard input: The first line is
    the username, the second line is the password (which consists of a
    static part and the OTP).

    This commands exits with return code 0 if the user could be authenticated
    successfully.
    """
    exitcode = -1
    instance = Path(instance)
    if instance.exists() and instance.joinpath('pi.cfg').exists():
        try:
            app = create_app(config_name="production", config_file=instance.joinpath('pi.cfg'),
                             silent=True)
            with app.test_request_context('/validate/check', method='POST',
                                          data={'user': username, 'pass': password}):
                response = app.full_dispatch_request()
                if response.status_code == 200 and response.json['result']['value'] is True:
                    exitcode = 0
                else:
                    exitcode = 1
                if show_response:
                    click.secho(f"Status: {response.status}\n"
                                f"Data:\n{json.dumps(response.json, indent=2)}", fg='blue')
        except Exception as e:
            click.secho(str(e), fg='red')

    else:
        click.secho(f"Instance configuration at '{instance}/pi.cfg' does "
                    f"not exist! Aborting.", fg='red')

    ctx.exit(exitcode)


cli.add_command(configure)
cli.add_command(create)
cli.add_command(check)


def create_pepper(length=24, chunk_size=8, charset=PEPPER_CHARSET):
    """
    create a valid PI_PEPPER value of a given length from urandom,
    choosing characters from a given charset

    :param length: pepper length to generate
    :param chunk_size: number of bytes to read from urandom per iteration
    :param charset: list of valid characters
    :return: a string of the specified length
    :rtype: str
    """
    pepper = ''
    while len(pepper) < length:
        random_bytes = DefaultSecurityModule.random(chunk_size)
        printables = ''.join(chr(b) for b in random_bytes if chr(b) in charset)
        pepper += printables
    return pepper[:length]


if __name__ == '__main__':
    cli()
