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
"""CLI commands for configuring the privacyIDEA server"""
import copy
import sys
import ast
from functools import partial
import click
from flask import current_app
from flask.cli import AppGroup
import json
import yaml

from privacyidea.lib.authcache import cleanup
from privacyidea.lib.caconnector import (get_caconnector_list,
                                         get_caconnector_class,
                                         get_caconnector_object,
                                         save_caconnector)
from privacyidea.lib.caconnectors.localca import ATTR
from privacyidea.lib.crypto import create_hsm_object
from privacyidea.lib.error import ResourceNotFoundError
from privacyidea.lib.event import EventConfiguration, enable_event, delete_event
from privacyidea.lib.policy import (PolicyClass, enable_policy, delete_policy,
                                    set_policy)
from privacyidea.lib.realm import (get_realms, delete_realm, set_default_realm,
                                   get_default_realm)
from privacyidea.lib.resolver import (save_resolver, get_resolver_list)
from privacyidea.lib.utils import get_version_number
from privacyidea.lib.utils.export import EXPORT_FUNCTIONS, IMPORT_FUNCTIONS
from privacyidea.cli.pimanage.challenge import challenge_cli

config_cli = AppGroup("config", help="Manage the privacyIDEA server configuration")

config_cli.add_command(challenge_cli)

ca_cli = AppGroup("ca", help="Manage Certificate Authorities")


@ca_cli.command("list")
@click.option("-v", "--verbose", is_flag=True,
              help="Additionally output the configuration of the CA connector")
def ca_list(verbose):
    """
    List the Certificate Authorities.
    """
    lst = get_caconnector_list()
    for ca in lst:
        click.echo(f"{ca.get('connectorname')} (type {ca.get('type')})")
        if verbose:
            for (k, v) in ca.get("data").items():
                click.echo(f"\t{k:20}: {v}")


@ca_cli.command("create", short_help="Create a new CA connector.")
@click.argument('name', type=str)
@click.option('-t', '--type', "catype", default="local",
              help='The type of the new CA', show_default=True)
@click.pass_context
def ca_create(ctx, name, catype):
    """
    Create a new CA connector identified by NAME.

    If the type "local" is given, also the directory
    structure, the openssl.cnf and the CA key pair will be created.
    """
    ca = get_caconnector_object(name)
    if ca:
        click.secho(f"A CA connector with the name '{name}' already exists.",
                    fg="red")
        ctx.exit(1)
    click.echo(f"Creating CA connector of type {catype}.")
    ca_class = get_caconnector_class(catype)
    if not ca_class:
        click.secho(f"Unknown CA type {catype}.", fg="red")
        ctx.exit(1)
    ca_params = ca_class.create_ca(name)
    r = save_caconnector(ca_params)
    if r:
        click.secho(f"Saved CA Connector with ID {r}.", fg="green")
        if ca_params["type"] == "local":
            click.secho(f"Warning: Be sure to set the correct access rights "
                        f"to the directory {ca_params[ATTR.WORKING_DIR]}.", fg="yellow")
    else:
        click.secho(f"Error saving CA connector {name}.", fg="red")


@ca_cli.command("create_crl", short_help="Create and publish CRL")
@click.argument("name", type=str)
@click.option("-f", "--force", is_flag=True,
              help="Enforce creation of a new CRL")
def ca_create_crl(name, force):
    """
    Create and publish the CRL for the CA NAME.
    """
    ca_obj = get_caconnector_object(name)
    r = ca_obj.create_crl(check_validity=not force)
    if not r:
        click.secho("The CRL was not created.", fg="yellow")
    else:
        click.echo(f"The CRL {r} was created.")


config_cli.add_command(ca_cli)
hsm_cli = AppGroup("hsm", help="Manage hardware security modules")


@hsm_cli.command("create_keys")
def hsm_create_keys():
    """
    Create new encryption keys on the HSM.
    Be sure to first set up the HSM module, the PKCS11
    module and the slot/password for the given HSM in your pi.cfg.
    Set the variables PI_HSM_MODULE, PI_HSM_MODULE_MODULE, PI_HSM_MODULE_SLOT
    and PI_HSM_MODULE_PASSWORD.
    """
    hsm_object = create_hsm_object(current_app.config)
    r = hsm_object.create_keys()
    click.echo("Please add the following to your pi.cfg:")
    click.echo(f"PI_HSM_MODULE_KEY_LABEL_TOKEN = {r.get('token')!r}")
    click.echo(f"PI_HSM_MODULE_KEY_LABEL_CONFIG = {r.get('config')!r}")
    click.echo(f"PI_HSM_MODULE_KEY_LABEL_VALUE = {r.get('value')!r}")


config_cli.add_command(hsm_cli)
realm_cli = AppGroup("realm", help="Manage realms")


@realm_cli.command("list")
def realm_list():
    """
    list the available realms.
    The '*' denotes the default realm.
    """
    realm_lst = get_realms()
    def_realm = get_default_realm()
    for (name, realm_data) in realm_lst.items():
        if name == def_realm:
            name = f"* {name}"
        resolver_names = [x.get("name") for x in realm_data.get("resolver")]
        click.echo(f"{name:16}: {resolver_names}")


@realm_cli.command("create")
@click.argument("name")
@click.argument("resolvers", nargs=-1)
def realm_create(name, resolvers):
    """
    Create a new realm.
    This command will create a new realm with the given resolvers.

    An existing realm with the same name will be replaced.
    """
    from privacyidea.lib.realm import set_realm
    (added, failed) = set_realm(name, [{'name': res} for res in resolvers])
    if failed:
        click.secho(f"Realm '{name}' created. Following resolvers could not be "
                    f"assigned: {failed}", fg="yellow")
    else:
        click.secho(f"Successfully created realm '{name}' with resolver: {added}.",
                    fg="green")


@realm_cli.command("delete")
@click.argument("realm", type=str)
def realm_delete(realm):
    """
    Delete the given REALM
    """
    try:
        delete_realm(realm)
    except ResourceNotFoundError as e:
        click.secho(f"Could not delete realm '{realm}': {e}", fg="red")
    else:
        click.secho(f"Realm '{realm}' successfully deleted.", fg="green")


@realm_cli.command("set_default")
@click.argument("realm", type=str)
def realm_set_default(realm):
    """
    Set the given REALM as the default realm
    """
    try:
        set_default_realm(realm)
    except ResourceNotFoundError as e:
        click.secho(f"Could not set realm {realm} as default: {e}", fg="red")
    else:
        click.secho(f"Realm {realm} set as default realm.", fg="green")


@realm_cli.command("clear_default")
def realm_clear_default():
    """
    Unset the default realm
    """
    set_default_realm(None)
    click.secho("cleared default realm.", fg="green")


config_cli.add_command(realm_cli)

resolver_cli = AppGroup("resolver", help="Manage user resolver")


@resolver_cli.command("list")
@click.option("-v", "--verbose", is_flag=True,
              help="Additionally output the configuration of the resolvers")
def resolver_list(verbose):
    """
    List the available resolvers and their type.
    """
    reso_list = get_resolver_list()

    if not verbose:
        for (name, resolver) in reso_list.items():
            click.echo(f"{name:16} - ({resolver.get('type')})")
    else:
        for (name, resolver) in reso_list.items():
            click.echo(f"{name:16} - ({resolver.get('type')})")
            click.echo("." * 32)
            data = resolver.get("data", {})
            for (k, v) in data.items():
                if k.lower() in ["bindpw", "password"]:
                    v = "xxxxx"
                click.echo(f"{k:>24}: {v!r}")
            click.echo("\n")


@resolver_cli.command("create")
@click.argument("name", type=str)
@click.argument("rtype", type=str)
@click.argument("conf_file", type=click.File())
def resolver_create(name, rtype, conf_file):
    """
    Create a new resolver with the specified name and type.

    The necessary resolver parameters are read from the file given with FILENAME.
    The file should contain a python dictionary.

    \b
    NAME:     The name of the resolver
    RTYPE:    The type of the resolver (can be ldapresolver, sqlresolver,
              httpresolver, passwdresolver or scimresolver)
    CONF_FILE: The name of the config file with the resolver parameters.

    \b
    Note: it might be more convenient to use the
        pi-manage config import
    command since it simplifies the import of the server configuration.
    """
    contents = conf_file.read()

    params = ast.literal_eval(contents)
    params["resolver"] = name
    params["type"] = rtype
    save_resolver(params)


@resolver_cli.command("create_internal")
@click.argument("name")
@click.pass_context
def resolver_create_internal(ctx, name):
    """
    This creates a new internal, editable sqlresolver. The users will be
    stored in the token database in a table called 'users_<NAME>'. You can then
    add this resolver to a new realm using the command
    'pi-manage config realm add <realm-name> <NAME>'.
    """
    sqluri = current_app.config.get("SQLALCHEMY_DATABASE_URI")
    sqlelements = sqluri.split("/")
    # mysql://user:password@localhost/pi
    # sqlite:////home/cornelius/src/privacyidea/data.sqlite
    sql_driver = sqlelements[0][:-1]
    user_pw_host = sqlelements[2]
    database = "/".join(sqlelements[3:])
    username = ""
    password = ""
    host = ""
    # determine host and user
    hostparts = user_pw_host.split("@")
    if len(hostparts) > 2:
        click.secho(f"Invalid database URI: {sqluri}", fg="red")
        ctx.exit(2)
    elif len(hostparts) == 1:
        host = hostparts[0] or "/"
    elif len(hostparts) == 2:
        host = hostparts[1] or "/"
        # split hostname and password
        userparts = hostparts[0].split(":")
        if len(userparts) == 2:
            username = userparts[0]
            password = userparts[1]
        elif len(userparts) == 1:
            username = userparts[0]
        else:
            click.secho(f"Invalid username and password in database URI: {sqluri}",
                        fg="red")
            ctx.exit(3)
    # now we can create the resolver
    params = {
        'resolver': name,
        'type': "sqlresolver",
        'Server': host,
        'Driver': sql_driver,
        'User': username,
        'Password': password,
        'Database': database,
        'Table': 'users_' + name,
        'Limit': '500',
        'Editable': '1',
        'Map': '{"userid": "id", "username": "username", '
               '"email":"email", "password": "password", '
               '"phone":"phone", "mobile":"mobile", "surname":"surname", '
               '"givenname":"givenname", "description": "description"}'}
    save_resolver(params)

    # Now we create the database table
    from sqlalchemy import create_engine
    from sqlalchemy import Table, MetaData, Column
    from sqlalchemy import Integer, String
    engine = create_engine(sqluri)
    metadata = MetaData()
    Table('users_%s' % name,
          metadata,
          Column('id', Integer, primary_key=True),
          Column('username', String(40), unique=True),
          Column('email', String(80)),
          Column('password', String(255)),
          Column('phone', String(40)),
          Column('mobile', String(40)),
          Column('surname', String(40)),
          Column('givenname', String(40)),
          Column('description', String(255)))
    metadata.create_all(engine)


config_cli.add_command(resolver_cli)

event_cli = AppGroup("event", help="Manage events")


@event_cli.command("list")
def event_list():
    """
    List events
    """
    events = EventConfiguration().events
    click.echo("\n{0:7} {4:4} {1:30}\t{2:20}\t{3}".format("Active", "Name", "Module", "Action", "ID"))
    click.echo(90 * "=")
    for event in events:
        click.echo(f"{event['active']!r:7} {event['id']:<4} {event['name']:30}"
                   f"\t{event['handlermodule']:20}\t{event['action']}")


@event_cli.command("enable")
@click.argument("eid", type=int)
def event_enable(eid):
    """
    Enable event with id EID
    """
    try:
        r = enable_event(eid)
    except ResourceNotFoundError as e:
        click.secho(f"Could not enable event {eid}: {e}", fg="red")
    else:
        click.secho(f"Enabled Event with ID {r}", fg="green")


@event_cli.command("disable")
@click.argument("eid", type=int)
def event_disable(eid):
    """
    Disable event with id EID
    """
    try:
        r = enable_event(eid, enable=False)
    except ResourceNotFoundError as e:
        click.secho(f"Could not disable event {eid}: {e}", fg="red")
    else:
        click.secho(f"Disabled Event with ID {r}", fg="green")


@event_cli.command("delete")
@click.argument("eid", type=int)
def event_delete(eid):
    """
    Delete event with id EID
    """
    try:
        r = delete_event(eid)
    except ResourceNotFoundError as e:
        click.secho(f"Could not delete event with ID {eid}: {e}", fg="red")
    else:
        click.secho(f"Deleted Event with ID {r}", fg="green")


config_cli.add_command(event_cli)

policy_cli = AppGroup("policy", help="Manage policies")


@policy_cli.command("list")
def policy_list():
    """
    list the policies
    """
    pol_cls = PolicyClass()
    policies = pol_cls.list_policies()
    click.echo("Active   Name " + 16 * ' ' + "Scope")
    click.echo(40 * "=")
    for policy in policies:
        click.echo(f"{policy.get('active')!r:8} {policy.get('name'):20} "
                   f"{policy.get('scope')}")


@policy_cli.command("enable")
@click.argument("name", type=str)
def policy_enable(name):
    """
    enable the policy NAME.
    """
    try:
        enable_policy(name)
    except ResourceNotFoundError as e:
        click.secho(f"Could not enable policy {name}: {e}", fg="red")
    else:
        click.secho(f"Successfully enabled policy '{name}'", fg="green")


@policy_cli.command("disable")
@click.argument("name", type=str)
def policy_disable(name):
    """
    disable the policy NAME
    """
    try:
        enable_policy(name, enable=False)
    except ResourceNotFoundError as e:
        click.secho(f"Could not disable policy {name}: {e}", fg="red")
    else:
        click.secho(f"Successfully disabled policy '{name}'", fg="green")


@policy_cli.command("delete")
@click.argument("name", type=str)
def policy_delete(name):
    """
    delete the policy NAME
    """
    try:
        delete_policy(name)
    except ResourceNotFoundError as e:
        click.secho(f"Could not delete policy {name}: {e}", fg="red")
    else:
        click.secho(f"Successfully deleted policy '{name}'", fg="green")


@policy_cli.command("create")
@click.argument("name")
@click.argument("scope")
@click.argument("action")
@click.option("-f", "--file", type=click.File(),
              help="The file to import the policy configuration from.")
def policy_create(name, scope, action, file):
    """
    Create a new policy.

    The file given with the option '-f' must contain a Python dictionary and its
    content takes precedence over the other CLI arguments.
    I.e. if you are specifying a configuration file with '-f',
    the arguments name, scope and action need to be specified, but are ignored.

    \b
    Note: it might be more convenient to use the
        pi-manage config import
    command since it simplifies the import of the server configuration.
    """
    if file:
        try:
            contents = file.read()
            params = ast.literal_eval(contents)
            if params.get("name") and params.get("name") != name:
                print("Found name '{0!s}' in file, will use that instead of "
                      "'{1!s}'.".format(params.get("name"), name))
            else:
                print("name not defined in file, will use the cli value "
                      "{0!s}.".format(name))
                params["name"] = name

            if params.get("scope") and params.get("scope") != scope:
                print("Found scope '{0!s}' in file, will use that instead of "
                      "'{1!s}'.".format(params.get("scope"), scope))
            else:
                print("scope not defined in file, will use the cli value "
                      "{0!s}.".format(scope))
                params["scope"] = scope

            if params.get("action") and params.get("action") != action:
                print("Found action in file: '{0!s}', will use that instead "
                      "of: '{1!s}'.".format(params.get("action"), action))
            else:
                print("action not defined in file, will use the cli value "
                      "{0!s}.".format(action))
                params["action"] = action

            r = set_policy(params.get("name"),
                           scope=params.get("scope"),
                           action=params.get("action"),
                           realm=params.get("realm"),
                           resolver=params.get("resolver"),
                           user=params.get("user"),
                           time=params.get("time"),
                           client=params.get("client"),
                           active=params.get("active", True),
                           adminrealm=params.get("adminrealm"),
                           adminuser=params.get("adminuser"),
                           check_all_resolvers=params.get(
                               "check_all_resolvers", False))
            return r

        except Exception as _e:
            print("Unexpected error: {0!s}".format(sys.exc_info()[1]))

    else:
        r = set_policy(name, scope, action)
        return r


config_cli.add_command(policy_cli)

imp_fmt_dict = {
    'python': ast.literal_eval,
    'json': json.loads,
    'yaml': yaml.safe_load}


@config_cli.command("import")
@click.option('-i', '--input', "infile", type=click.File('r'),
              default=sys.stdin,
              help='The filename to import the data from. Read '
                   'from <stdin> if this argument is not given.')
@click.option('-t', '--types', multiple=True, default=['all'], show_default=True,
              type=click.Choice(['all'] + list(IMPORT_FUNCTIONS.keys()), case_sensitive=False),
              help='The types of configuration to import. By default import all '
                   'available data if a corresponding importer type exists. '
                   'Currently registered importer types are: '
                   '{0!s}'.format(', '.join(['all'] + list(IMPORT_FUNCTIONS.keys()))))
@click.option('-n', '--name', metavar="NAME",
              help='The name of the configuration object to import (default: import all)')
@click.pass_context
def config_import(ctx, infile, types, name):
    """
    Import server configuration using specific or all registered importer types.

    Note: Existing configuration with the same name will be overwritten, other
    existing configuration will be kept as is.
    """
    data = None
    imp_types = IMPORT_FUNCTIONS.keys() if 'all' in types else types

    content = infile.read()

    for fmt in imp_fmt_dict:
        try:
            data = imp_fmt_dict[fmt](content)
            break
        except (SyntaxError, json.decoder.JSONDecodeError, yaml.error.YAMLError) as _e:
            continue
    if not data:
        click.secho("Could not read input format! ", fg="red")
        click.secho(f"Accepted formats are: {', '.join(imp_fmt_dict.keys())}.",
                    fg="yellow")
        ctx.exit(1)

    def minver(s: str) -> str:
        """Get major.minor version number from string."""
        return ".".join(s.split('.')[0:2])

    # Check the version in the import data
    if "privacyIDEA_version" not in data:
        click.secho("Unable to determine version of exported data.", fg="yellow")
        click.secho("Please make sure that the imported configuration "
                    "works as expected.", fg="yellow")

    else:
        if minver(data["privacyIDEA_version"]) != minver(get_version_number()):
            click.secho(f"Version of export ({minver(data['privacyIDEA_version'])}) "
                        f"does not match current privacyIDEA "
                        f"version ({minver(get_version_number())}).", fg="yellow")
            click.secho("Please make sure that the imported configuration "
                        "works as expected.", fg="yellow")

    # we need to go through the importer functions based on priority
    for typ, value in sorted(IMPORT_FUNCTIONS.items(), key=lambda x: x[1]['prio']):
        if typ in imp_types:
            if typ in data:
                click.echo(f"Importing configuration type '{typ}'.")
                try:
                    value['func'](data[typ], name=name)
                except Exception as e:
                    click.secho(f"Could not successfully import data of "
                                f"type {typ}: {e}", fg="red")


# Create the "importer" command as a hidden and deprecated alias for "import"
importer_cmd = copy.copy(config_cli.get_command(None, "import"))
importer_cmd.hidden = True
importer_cmd.deprecated = True
importer_cmd.name = "importer"
importer_cmd.epilog = "This command is deprecated. Please use 'pi-manage config import' instead."
config_cli.add_command(importer_cmd)


exp_fmt_dict = {
    'python': str,
    'json': partial(json.dumps, indent=2),
    'yaml': yaml.safe_dump}


@config_cli.command("export")
@click.option('-o', '--output', type=click.File('w'),
              default=sys.stdout,
              help='The filename to export the data to. Write to '
                   '<stdout> if this argument is not given or is \'-\'.')
@click.option('-f', '--format', "fmt", default='python', show_default=True,
              type=click.Choice(exp_fmt_dict.keys(), case_sensitive=False),
              help='Output format, default is \'python\'')
# TODO: we need to have an eye on the help output, it might get less readable
#  when more exporter functions are added
@click.option('-t', '--types', multiple=True, default=['all'], show_default=True,
              type=click.Choice(['all'] + list(EXPORT_FUNCTIONS.keys()), case_sensitive=False),
              help='The types of configuration to export (can be given multiple '
                   'times). By default, export all available types. Currently '
                   'registered exporter types are: '
                   '{0!s}'.format(', '.join(['all'] + list(EXPORT_FUNCTIONS.keys()))),
              )
@click.option('-n', '--name', metavar="NAME",
              help='The name of the configuration object to export (default: export all)')
def config_export(output, fmt, types, name):
    """
    Export server configuration using specific or all registered exporter types.
    """
    exp_types = EXPORT_FUNCTIONS.keys() if 'all' in types else types

    out = {}
    for typ in exp_types:
        out.update({typ: EXPORT_FUNCTIONS[typ](name=name)})

    if out:
        # Add version information to output
        out["privacyIDEA_version"] = get_version_number()
        res = exp_fmt_dict.get(fmt.lower())(out) + '\n'
        output.write(res)


# Create the "exporter" command as a hidden and deprecated alias for "export"
exporter_cmd = copy.copy(config_cli.get_command(None, "export"))
exporter_cmd.hidden = True
exporter_cmd.deprecated = True
exporter_cmd.name = "exporter"
exporter_cmd.epilog = "This command is deprecated. Please use 'pi-manage config export' instead."
config_cli.add_command(exporter_cmd)

authcache_cli = AppGroup("authcache", help="Manage authentication cache")


@authcache_cli.command("cleanup")
@click.option("-m", "--minutes", default=480, show_default=True, type=int,
              help="Clean up authcache entries older than this number of minutes")
def authcache_cleanup(minutes):
    """
    Remove entries from the authcache.
    Remove all entries where the last_auth entry is older than the given number
    of minutes.
    """
    r = cleanup(minutes)
    click.echo(f"{r} entries deleted from authcache")


config_cli.add_command(authcache_cli)
