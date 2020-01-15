# -*- coding: utf-8 -*-
#
# 2020-01-14 Jean-Pierre Höhmann <jean-pierre.hoehmann@netknights.it>
#
# License:  AGPLv3
# Contact:  https://www.privacyidea.org
#
# Copyright (C) 2020 NetKnights GmbH
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

import logging

__doc__ = """
Business logic for WebAuthn protocol.

This file contains a partial implementation of the server part of the WebAuthn
protocol. It currently uses a library written by Duo Security to do most of the
heavy lifting. The functions in this file that make use of this library will be
gradually rewritten to implement the necessary functionality themselves,
allowing us to remove the external dependency.

This file is tested in tests/test_lib_tokens_webauthn.py
"""

log = logging.getLogger(__name__)