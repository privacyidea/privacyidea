# -*- coding: utf-8 -*-
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
"""
High-level API for matching policies. This module provides a class ``Match``,
which encapsulates a policy matching operation. ``Match`` objects are created
using several classmethods which represent different flavors of matching
operations: For example, there are classmethods for matching policies based
on a user realm, or based on a user object.

In addition, the ``Match`` object performs postprocessing of matching results,
e.g. by extracing action values from the matching policies. Finally, it writes
the matched policies to the audit log (though this can be disabled).

This module is tested in ``test_lib_policymatch.py``.
"""


