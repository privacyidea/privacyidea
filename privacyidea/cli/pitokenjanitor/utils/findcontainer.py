from typing import Generator

import click
from flask.cli import AppGroup

from privacyidea.lib.container import container_page_generator
from privacyidea.lib.containerclass import TokenContainerClass


def _get_container_list(serial: str = None, ctype: str = None, token_serial: str = None,
                        realm: str = None, template: str = None, description: str = None, assigned: bool = False,
                        resolver: str = None, info: str = None, last_auth_delta: str = None,
                        last_sync_delta: str = None, pagesize: int = 1000) -> Generator[
    list[TokenContainerClass], None, None]:
    """
    Helper function to get a list of containers based on the provided parameters.
    """
    container = container_page_generator(serial=serial, ctype=ctype,
                                         token_serial=token_serial, realm=realm,
                                         template=template, description=description,
                                         assigned=assigned, resolver=resolver,
                                         info=info, last_auth_delta=last_auth_delta,
                                         last_sync_delta=last_sync_delta, pagesize=pagesize)
    return container


@click.group('find_container', invoke_without_command=True, cls=AppGroup)
@click.option('--serial', '-s', help='Serial number of the container.')
@click.option('--type', '-t', 'ctype', help='Type of the container.')
@click.option('--token-serial', '-ts', help='Serial number of the token in the container.')
@click.option('--realm', '-r', help='Realm of the container.')
@click.option('--template', '-T', help='The name of the template the container was created with.')
@click.option('--description', '-d', help='Description of the container.')
@click.option('--assigned', '-a', is_flag=True, help='Only show containers that are assigned to a user.')
@click.option('--resolver', '-R', type=str, help='The resolver of the user.')
@click.option('--info', '-i', type=str,
              help='An additional information from the container info table, given as "key=value".')
@click.option('--last-auth-delta', '-l', type=str,
              help='The maximum time difference the last authentication may have to now, e.g. "1y", "14d", "1h" '
                   'The following units are supported: y (years), d (days), h (hours), m (minutes), s (seconds)')
@click.option('--last-sync-delta', '-L', type=str,
              help='The maximum time difference the last synchronization may have to now, e.g. "1y", "14d", "1h" '
                   'The following units are supported: y (years), d (days), h (hours), m (minutes), s (seconds)"')
@click.option('--chunksize', '-p', type=int, default=100,
              help='The number of containers to return per page.')
@click.pass_context
def findcontainer(ctx, serial, ctype, token_serial, realm, template, description,
                  assigned, resolver, info, last_auth_delta, last_sync_delta, chunksize):
    """
    Find container.
    """
    ctx.obj = dict()

    ctx.obj['containers'] = _get_container_list(serial=serial, ctype=ctype,
                                                token_serial=token_serial, realm=realm,
                                                template=template, description=description,
                                                assigned=assigned, resolver=resolver,
                                                info=info, last_auth_delta=last_auth_delta,
                                                last_sync_delta=last_sync_delta, pagesize=chunksize)

    if ctx.invoked_subcommand is None:
        ctx.invoke(list_containers)


@findcontainer.command('test')
@click.pass_context
def test(ctx):
    try:
        for clist in ctx.obj['containers']:
            for container in clist:
                click.echo(container)
    except Exception as e:
        click.echo(e)


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
                if key:
                    output.append(f"Serial: {container.serial}")
                    for key in ctx.obj['key']:
                        output.append(f"{key}: {container.get(key, 'N/A')}")
                else:
                    output.append(f"Serial: {container.get('serial', 'N/A')}")
                    output.append(f"Type: {container.get('type', 'N/A')}")
                    output.append(f"User: {container.get('user', 'N/A')}")
                    output.append(f"Realm: {container.get('realm', 'N/A')}")
                    output.append(f"Description: {container.get('description', 'N/A')}")
            click.echo(", ".join(output))


@findcontainer.command('delete')
@click.pass_context
def delete_containers(ctx):
    """
    Delete containers based on the provided parameters.
    """
    for clist in ctx.obj['containers']:
        for container in clist:
            serial = container.get('serial')
            container.delete()
            click.echo(f"Deleted token {serial}")


@findcontainer.command('set_info')
@click.argument('key', type=str)
@click.argument('value', type=str)
@click.pass_context
def set_info(ctx, key, value):
    """
    Set information for the containers. The old information will be overwritten.

    KEY is the key of the information to set.
    VALUE is the value of the information to set.
    """
    for clist in ctx.obj['containers']:
        for container in clist:
            container.set_container_info({key: value})
            click.echo(f"Set info {key}={value} for container {container.get('serial')}")


@findcontainer.command('update_info')
@click.argument('key', type=str)
@click.argument('value', type=str)
@click.pass_context
def update_info(ctx, key, value):
    """
    Update information for the containers. The old information will be updated.

    KEY is the key of the information to update.
    VALUE is the value of the information to update.
    """
    for clist in ctx.obj['containers']:
        for container in clist:
            container.update_container_info([{key: value}])
            click.echo(f"Updated info {key}={value} for container {container.get('serial')}")


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
            container.delete_container_info(key=key)
            click.echo(f"Deleted info {key} for container {container.get('serial')}")


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
            click.echo(f"Set description '{description}' for container {container.get('serial')}")


@findcontainer.command('set_realm')
@click.argument('realm', type=str)
@click.option('--add', '-a', is_flag=True, help='The realm will be added to the existing realms.')
@click.pass_context
def set_realm(ctx, realm, add):
    """
    Set the realm for the containers.

    REALM is the realm to set.
    """
    for clist in ctx.obj['containers']:
        for container in clist:
            container.set_realm(realm, add=add)
            click.echo(f"Set realm '{realm}' for container {container.get('serial')}")
