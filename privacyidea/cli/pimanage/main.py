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

import click
from flask.cli import FlaskGroup
from privacyidea.app import create_app
from privacyidea.lib.utils import get_version_number
from .admin import admin_cli
from .audit import audit_cli, rotate_audit as audit_rotate_audit
from .backup import backup_cli
from .pi_setup import (setup_cli, encrypt_enckey, create_enckey, create_tables,
                       create_pgp_keys, create_audit_keys, drop_tables)
from .pi_config import (config_cli, ca_cli, realm_cli, resolver_cli, event_cli,
                        policy_cli, authcache_cli, hsm_cli)
from .api import api_cli

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


# Don't show logging information
def my_create_app():
    app = create_app(config_name="production", silent=True)
    return app


@click.group(cls=FlaskGroup, create_app=my_create_app, context_settings=CONTEXT_SETTINGS,
             epilog='Check out our docs at https://privacyidea.readthedocs.io/ for more details')
def cli():
    """
\b
             _                    _______  _______
   ___  ____(_)  _____ _______ __/  _/ _ \/ __/ _ |
  / _ \/ __/ / |/ / _ `/ __/ // // // // / _// __ |
 / .__/_/ /_/|___/\_,_/\__/\_, /___/____/___/_/ |_|
/_/                       /___/

  Management script for the privacyIDEA application."""
    click.echo(r"""
             _                    _______  _______
   ___  ____(_)  _____ _______ __/  _/ _ \/ __/ _ |
  / _ \/ __/ / |/ / _ `/ __/ // // // // / _// __ |
 / .__/_/ /_/|___/\_,_/\__/\_, /___/____/___/_/ |_|
/_/                       /___/
{0!s:>51}
    """.format('v{0!s}'.format(get_version_number())))


cli.add_command(audit_rotate_audit, "rotate_audit")
cli.add_command(create_enckey)
cli.add_command(encrypt_enckey)
cli.add_command(create_audit_keys)
cli.add_command(create_tables)
cli.add_command(create_pgp_keys)
cli.add_command(create_tables, "createdb")
cli.add_command(drop_tables)
cli.add_command(drop_tables, "dropdb")
cli.add_command(realm_cli)
cli.add_command(resolver_cli)
cli.add_command(policy_cli)
cli.add_command(event_cli)

cli.add_command(admin_cli)
cli.add_command(audit_cli)
cli.add_command(setup_cli)
cli.add_command(config_cli)
cli.add_command(backup_cli)
cli.add_command(api_cli)
cli.add_command(ca_cli)
cli.add_command(authcache_cli)
cli.add_command(hsm_cli)

if __name__ == '__main__':
    cli()
