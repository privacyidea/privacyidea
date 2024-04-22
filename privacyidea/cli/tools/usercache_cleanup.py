# 2024-03-22 Jona-Samuel Höhmann <jona-samuel.hoehmann@netknights.it>
#            Migrate to click
# 2017-04-24 Friedrich Weber <friedrich.weber@netknights.it>
#
# Copyright (c) 2017, Friedrich Weber
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its
# contributors may be used to endorse or promote products derived from this
# software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""
This script deletes expired entries from the user cache.
"""
__version__ = "0.1"

from flask.cli import with_appcontext, ScriptInfo
from privacyidea.lib.usercache import create_filter, get_cache_time
from privacyidea.lib.utils import get_version_number
from privacyidea.models import UserCache, db
from privacyidea.cli import create_silent_app
import click

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


def _get_expired_entries():
    """
    Returns a list of all cache entries that are considered expired.
    """
    filter_condition = create_filter(expired=True)
    return UserCache.query.filter(filter_condition).order_by(UserCache.timestamp.desc()).all()


LIST_FORMAT = '{:<5} {:<10} {:<10} {:<30} {:<10}'


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('-n', "--noaction", is_flag=True, default=False)
@with_appcontext
def delete(noaction=False):
    """
    Delete all cache entries that are considered expired according to the
    UserCacheExpiration configuration setting.
    If the user cache is disabled, no entries are deleted.
    If '--noaction' is passed, expired cache entries are listed, but not
    actually deleted.
    """
    if not get_cache_time():
        click.echo('User cache is disabled, not doing anything.')
    else:
        click.echo('Expired entries:')
        entries = _get_expired_entries()
        if entries:
            click.echo(LIST_FORMAT.format('id', 'username', 'resolver', 'timestamp', 'user id'))
        for entry in entries:
            click.echo(LIST_FORMAT.format(entry.id,
                                          entry.username,
                                          entry.resolver,
                                          entry.timestamp.isoformat(),
                                          entry.user_id))
        click.echo('{} entries'.format(len(entries)))
        if not noaction:
            for entry in entries:
                click.echo('Deleting entry with id={} ...'.format(entry.id))
                entry.delete()
            click.echo('Deleted {} expired entries.'.format(len(entries)))
            db.session.commit()
        else:
            click.echo("'--noaction' was passed, not doing anything.")


def delete_call():
    """Management script for usercache cleanup of privacyIDEA."""
    click.echo(r"""
                 _                    _______  _______
       ___  ____(_)  _____ _______ __/  _/ _ \/ __/ _ |
      / _ \/ __/ / |/ / _ `/ __/ // // // // / _// __ |
     / .__/_/ /_/|___/\_,_/\__/\_, /___/____/___/_/ |_|  Usercache cleanup
    /_/                       /___/
    {0!s:>51}
        """.format('v{0!s}'.format(get_version_number())))

    # Add the ScriptInfo object to create the Flask-App when necessary
    s = ScriptInfo(create_app=create_silent_app)
    delete(obj=s)


if __name__ == '__main__':
    delete_call()
