from collections.abc import Generator

import click
from flask.cli import AppGroup

from privacyidea.lib.container import add_container_info, get_container_generator
from privacyidea.lib.containerclass import TokenContainerClass
from privacyidea.lib.error import PolicyError


def _get_container_list(serial: str = None, ctype: str = None, token_serial: str = None,
                        realm: str = None, template: str = None, description: str = None, assigned: bool = None,
                        resolver: str = None, info: str = None, last_auth_delta: str = None,
                        last_sync_delta: str = None, pagesize: int = 1000, orphaned: bool = None) -> Generator[
    list[TokenContainerClass], None, None]:
    """
    Helper function to get a list of containers based on the provided parameters.
    """

    if info:
        info_key, info_value = info.split("=")
        info = {info_key: info_value}

    container_page = get_container_generator(serial=serial, ctype=ctype,
                                             token_serial=token_serial, realm=realm,
                                             template=template, description=description,
                                             assigned=assigned, resolver=resolver,
                                             info=info, last_auth_delta=last_auth_delta,
                                             last_sync_delta=last_sync_delta, pagesize=pagesize)

    for containers in container_page:
        ret = []
        for container in containers:
            if orphaned is not None:
                try:
                    container_is_orphaned = container.is_orphaned()
                except Exception as error:
                    # Without an answer of the user store the container is neither orphaned nor not orphaned
                    click.secho(f"Can not check whether container {container.serial} is orphaned, the container is "
                                f"skipped: {error}", fg="red", bold=True, err=True)
                    continue
                if container_is_orphaned != orphaned:
                    continue
            ret.append(container)
        yield ret


@click.group('container', invoke_without_command=True, cls=AppGroup)
@click.option('--serial', '-s', help='Serial number of the container.')
@click.option('--type', '-t', 'ctype', help='Type of the container.')
@click.option('--token-serial', '-ts', help='Serial number of the token in the container.')
@click.option('--realm', '-r', help='Realm of the container.')
@click.option('--template', '-T', help='The name of the template the container was created with.')
@click.option('--description', '-d', help='Description of the container.')
@click.option('--assigned', '-a', type=bool, default=None, help='Only show containers that are assigned to a user.')
@click.option('--resolver', '-R', type=str, help='The resolver of the user.')
@click.option('--info', '-i', type=str,
              help='An additional information from the container info table, given as "key=value".')
@click.option('--last-auth-delta', '-l', type=str,
              help='The maximum time difference the last authentication may have to now, e.g. "1y", "14d", "1h" '
                   'The following units are supported: y (years), d (days), h (hours), m (minutes), s (seconds)')
@click.option('--last-sync-delta', '-L', type=str,
              help='The maximum time difference the last synchronization may have to now, e.g. "1y", "14d", "1h" '
                   'The following units are supported: y (years), d (days), h (hours), m (minutes), s (seconds)"')
@click.option('--chunksize', '-c', type=int, default=100,
              help='The number of containers to return per page.')
@click.option('--orphaned', '-o', type=bool, default=None,
              help='Whether the container is orphaned: assigned to users that no longer exist in the user store. '
                   'Can be "True" or "False"')
@click.pass_context
def findcontainer(ctx, serial, ctype, token_serial, realm, template, description,
                  assigned, resolver, info, last_auth_delta, last_sync_delta, chunksize, orphaned):
    """
    Find container.
    """
    ctx.obj = dict()

    ctx.obj['containers'] = _get_container_list(serial=serial, ctype=ctype,
                                                token_serial=token_serial, realm=realm,
                                                template=template, description=description,
                                                assigned=assigned, resolver=resolver,
                                                info=info, last_auth_delta=last_auth_delta,
                                                last_sync_delta=last_sync_delta, pagesize=chunksize, orphaned=orphaned)

    if ctx.invoked_subcommand is None:
        ctx.invoke(list_containers)


@findcontainer.command('list')
@click.option('--key', '-k', type=str, multiple=True, help='The key of the information to display.')
@click.pass_context
def list_containers(ctx, key):
    """
    List containers based on the provided parameters.
    """
    for clist in ctx.obj['containers']:
        for container in clist:
            output = []
            if container:
                container_dict = container.get_as_dict()
                output.append(f"Serial: {container.serial}")
                if not key:
                    key = ['type', 'tokens', 'users', 'realms', 'description']
                for k in key:
                    output.append(f"{k}: {container_dict.get(k, 'N/A')}")
            click.echo(", ".join(output))


@findcontainer.command('delete')
@click.option('--tokens', '-t', 'delete_token', is_flag=True, default=False,
              help='Also delete the tokens in the container.')
@click.pass_context
def delete_containers(ctx, delete_token):
    """
    Delete containers based on the provided parameters.
    """
    for clist in ctx.obj['containers']:
        for container in clist:
            serial = container.serial
            tokens = container.get_tokens()
            for token in tokens:
                if delete_token:
                    token.delete_token()
                else:
                    container.remove_token(token.get_serial())
            container.delete()
            click.echo(f"Deleted container {serial}")


@findcontainer.command('update_info')
@click.argument('key', type=str)
@click.argument('value', type=str)
@click.pass_context
def update_info(ctx, key, value):
    """
    Update information for the containers. A non-existing key is added and the value for an existing key is
    overwritten. All other entries remain unchanged. An entry privacyIDEA maintains itself is skipped.

    KEY is the key of the information to update.
    VALUE is the value of the information to update.
    """
    for clist in ctx.obj['containers']:
        for container in clist:
            try:
                # Refuses the entries privacyIDEA maintains itself, like the endpoints of the API do
                add_container_info(container.serial, key, value)
            except PolicyError as error:
                click.echo(f"Skipped container {container.serial}: {error!s}")
                continue
            click.echo(f"Updated info {key}={value} for container {container.serial}")


@findcontainer.command('delete_info')
@click.argument('key', type=str)
@click.pass_context
def delete_info(ctx, key):
    """
    Delete information for the containers. The information will be removed.

    KEY is the key of the information to delete.
    """
    for clist in ctx.obj['containers']:
        for container in clist:
            try:
                deleted = container.delete_container_info(key=key)
                if deleted.get(key):
                    click.echo(f"Deleted info {key} for container {container.serial}")
                else:
                    click.echo(f"Container {container.serial} has no info {key}")
            except PolicyError as e:
                click.echo(f"Cannot delete info {key} for container {container.serial}: {e}")


@findcontainer.command('set_description')
@click.argument('description', type=str)
@click.pass_context
def set_description(ctx, description):
    """
    Set the description for the containers.

    DESCRIPTION is the description to set.
    """
    for clist in ctx.obj['containers']:
        for container in clist:
            container.description = description
            click.echo(f"Set description '{description}' for container {container.serial}")


@findcontainer.command('set_realm')
@click.argument('realms', type=str)
@click.option('--add', '-a', is_flag=True, default=False, help='The realm(s) will be added to the existing realms.')
@click.pass_context
def set_realm(ctx, realms, add):
    """
    Set the realm(s) for the containers. For multiple realms, separate them with a comma.

    REALM is the realm to set.
    """
    realms_list = [r.strip() for r in realms.split(',')]
    for clist in ctx.obj['containers']:
        for container in clist:
            ret = container.set_realms(realms=realms_list, add=add)
            successful_realms = [realm for realm, success in ret['realms'].items() if success]
            unsuccessful_realms = [realm for realm, success in ret['realms'].items() if not success]
            if unsuccessful_realms:
                click.echo(f"realm: {unsuccessful_realms} could not be set for container {container.serial}")
            if successful_realms:
                click.echo(f"Set realm '{successful_realms}' for container {container.serial}")
