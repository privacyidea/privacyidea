# (c) NetKnights GmbH 2025,  https://netknights.it
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
# SPDX-FileCopyrightText: 2025 Jelina Unger <jelina.unger@netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
import logging

from flask import Response

from privacyidea.lib.resolvers.HTTPResolver import RequestConfig, HTTPResolver

log = logging.getLogger(__name__)

def delete_user_error_handling_no_content(resolver: HTTPResolver, response: Response, config: RequestConfig, user_identifier: str) -> bool:
    """
    Handles the error response from the HTTP Resolver user store when deleting a user.
    Does not raise an exception, as this is handled from the API function.

    :param resolver: The HTTPResolver instance used to handle the request
    :param response: The response object from the HTTP request
    :param config: Configuration for the endpoint containing information about special error handling
    :param user_identifier: The identifier of the user to be deleted
    """
    if response.status_code == 204:
        return True

    # extract error code and messages
    error = resolver.get_error(response)
    if error.error:
        # We do not raise an error here, as it would be caught in the outer function and cause an ambiguous
        # log message. But an error is displayed in the UI anyway.
        success = False
        log.info(f"Failed to delete user {user_identifier}: {error.code} - {error.message}")
    else:
        # Checks for generic HTTP errors and custom error handling
        success = resolver.default_error_handling(response, config)
    return success