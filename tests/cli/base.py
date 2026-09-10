# (c) NetKnights GmbH 2024,  https://netknights.it
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-FileCopyrightText: 2024 Paul Lettich <paul.lettich@netknights.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import unittest
from sqlalchemy.orm.session import close_all_sessions

from privacyidea.app import create_app
from privacyidea.models import db
from privacyidea.lib.lifecycle import call_finalizers
from ..base import _reset_database


class CliTestCase(unittest.TestCase):
    app = None
    app_context = None

    @classmethod
    def setUpClass(cls):
        cls.app = create_app(config_name="testing", config_file="", silent=True)
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        # Reuse the schema the way tests/base.py does: building and dropping all
        # 57 tables per class is the single most expensive thing these tests did,
        # and dropping them also denied the next class on this worker a schema to
        # reuse.
        _reset_database()

    def tearDown(self):
        db.session.commit()
        db.session.close()

    @classmethod
    def tearDownClass(cls):
        call_finalizers()
        close_all_sessions()
        db.engine.dispose()
        cls.app_context.pop()
