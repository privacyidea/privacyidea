# -*- coding: utf-8 -*-
#
#  2015-02-25 Cornelius Kölbel <cornelius@privacyidea.org>
#             Initial writeup
#
#
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# License as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
__doc__ = '''
Machine Resolvers are used to find machines in directories like LDAP, Active
Directory or the /etc/hosts file.

Machines can then be used to assign applications and tokens to those machines.
'''
from .base import BaseMachineResolver

