# SPDX-FileCopyrightText: (C) 2024 Paul Lettich <paul.lettich@netknights.it>
#
# SPDX-FileCopyrightText: (C) 2017 Cornelius Kölbel <cornelius.koelbel@netknights.it>
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
"""Utility functions for CLI tools"""
import click
from flask.cli import FlaskGroup
import platform
from privacyidea.app import create_app
from privacyidea.lib.utils import get_version_number


# Don't show logging information
def create_silent_app():
    """App factory with silent flag set"""
    app = create_app(config_name="production", silent=True)
    return app


# Don't load plugin commands
class NoPluginsFlaskGroup(FlaskGroup):
    """A FlaskGroup class which does not load commands from plugins"""
    def _load_plugin_commands(self):
        pass


def get_version(ctx, param, value):
    """Show version information"""
    if not value or ctx.resilient_parsing:
        return

    import werkzeug
    from flask import __version__

    message = "Python %(python)s\nFlask %(flask)s\nWerkzeug %(werkzeug)s\nprivacyIDEA %(privacyIDEA)s"
    click.echo(
        message
        % {
            "python": platform.python_version(),
            "flask": __version__,
            "werkzeug": werkzeug.__version__,
            "privacyIDEA": get_version_number(),
        },
        color=ctx.color,
    )
    ctx.exit()
