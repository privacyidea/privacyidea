# SPDX-FileCopyrightText: (C) 2023 Paul Lettich <paul.lettich@netknights.it>
#
# SPDX-FileCopyrightText: (C) 2014 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# 2024-04-22 Paul Lettich <paul.lettich@netknights.it>
#            Refactor using click
# 2020-11-18 Henning Hollermann <henning.hollermann@netknights.it>
#            Allow import and export of events, resolvers and policies
# 2018-08-07 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#            Allow creation of HSM keys
# 2017-10-08 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#            Allow cleaning up different actions with different
#            retention times.
# 2017-07-12 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#            Add generation of PGP keys
# 2017-02-23 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#            Add CA sub commands
# 2017-01-27 Diogenes S. Jesus
#            Cornelius Kölbel <cornelius.koelbel@netknights.it>
#            Add creation of more detailed policy
# 2016-04-15 Cornelius Kölbel <cornelius@privacyidea.org>
#            Add backup for pymysql driver
# 2016-01-29 Cornelius Kölbel <cornelius@privacyidea.org>
#            Add profiling
# 2015-10-09 Cornelius Kölbel <cornelius@privacyidea.org>
#            Set file permissions
# 2015-09-24 Cornelius Kölbel <cornelius@privacyidea.org>
#            Add validate call
# 2015-06-16 Cornelius Kölbel <cornelius@privacyidea.org>
#            Add creation of JWT token
# 2015-03-27 Cornelius Kölbel, cornelius@privacyidea.org
#            Add sub command for policies
# 2014-12-15 Cornelius Kölbel, info@privacyidea.org
#            Initial creation
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
"""CLI Tool for configuring and managing privacyIDEA"""

import click
from flask.cli import FlaskGroup
from privacyidea.cli import create_silent_app
from privacyidea.lib.utils import get_version_number
from .admin import admin_cli
from .audit import audit_cli, rotate_audit as audit_rotate_audit
from .backup import backup_cli
from .pi_setup import (
    setup_cli,
    encrypt_enckey,
    create_enckey,
    create_tables,
    create_pgp_keys,
    create_audit_keys,
    drop_tables,
)
from .pi_config import (
    config_cli,
    ca_cli,
    realm_cli,
    resolver_cli,
    event_cli,
    policy_cli,
    authcache_cli,
    hsm_cli,
)
from .api import api_cli

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group(
    cls=FlaskGroup,
    create_app=create_silent_app,
    context_settings=CONTEXT_SETTINGS,
    epilog="Check out our docs at https://privacyidea.readthedocs.io/ for more details",
)
def cli():
    """
    \b
                 _                    _______  _______
       ___  ____(_)  _____ _______ __/  _/ _ \\/ __/ _ |
      / _ \\/ __/ / |/ / _ `/ __/ // // // // / _// __ |
     / .__/_/ /_/|___/\\_,_/\\__/\\_, /___/____/___/_/ |_|
    /_/                       /___/

      Management script for the privacyIDEA application."""
    click.echo(
        r"""
             _                    _______  _______
   ___  ____(_)  _____ _______ __/  _/ _ \/ __/ _ |
  / _ \/ __/ / |/ / _ `/ __/ // // // // / _// __ |
 / .__/_/ /_/|___/\_,_/\__/\_, /___/____/___/_/ |_|
/_/                       /___/
{0!s:>51}
    """.format("v{0!s}".format(get_version_number()))
    )


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

if __name__ == "__main__":
    cli()
