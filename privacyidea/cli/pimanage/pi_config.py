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

from flask.cli import AppGroup

config_cli = AppGroup("config", help="privacyIDEA server configuration")

ca_cli = AppGroup("ca", help="Manage Certificate Authorities")


@ca_cli.command("list")
def list_ca():
    pass


@ca_cli.command("create")
def create_ca():
    pass


@ca_cli.command("create_crl")
def create_crl_ca():
    pass


config_cli.add_command(ca_cli)

realm_cli = AppGroup("realm", help="Manage realms")


@realm_cli.command("list")
def realm_list():
    pass


@realm_cli.command("create")
def realm_create():
    pass


@realm_cli.command("delete")
def realm_delete():
    pass


@realm_cli.command("set_default")
def realm_set_default():
    pass


@realm_cli.command("clear_default")
def realm_clear_default():
    pass


config_cli.add_command(realm_cli)

resolver_cli = AppGroup("resolver", help="Manage user resolver")


@resolver_cli.command("list")
def resolver_list():
    pass


@resolver_cli.command("create")
def resolver_create():
    pass


@resolver_cli.command("create_internal")
def resolver_create_internal():
    pass


config_cli.add_command(resolver_cli)

event_cli = AppGroup("event", help="Manage events")


@event_cli.command("list")
def event_list():
    pass


def event_enable():
    pass


def event_disable():
    pass


def event_delete():
    pass


config_cli.add_command(event_cli)

policy_cli = AppGroup("policy", help="Manage policies")


@policy_cli.command("list")
def policy_list():
    pass


def policy_enable():
    pass


def policy_disable():
    pass


def policy_delete():
    pass


def policy_create():
    pass


config_cli.add_command(policy_cli)


@config_cli.command("import")
def config_import():
    pass


@config_cli.command("export")
def config_export():
    pass
