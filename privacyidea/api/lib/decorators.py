# -*- coding: utf-8 -*-
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
These are the decorators which run before processing the request and may
modify API calls e.g. by changing the flask environment.

The functions of this module are tested in tests/test_api_lib_decorators.py
"""


import logging
from privacyidea.api.lib.utils import getParam
from flask import g
import functools

log = logging.getLogger(__name__)

optional = True
required = False

class APIDecorator(object):
    """
    This is the decorator to either wrap an API function call or act as response-modifier.
    The behavior is given by the argument 'position'. With position = "post" it runs
    after the request and else (position = "pre") wraps the API function itself.

    """
    def __init__(self, function, request, position="pre", options=()):
        """
        :param function: This is the function the is to be called
        :type function: function
        :param request: The original request object, that needs to be passed
        :type request: Request Object
        :param options: Options which are passed to the decorator function
        :type options: dict
        :param position: The behavior of the decorator. With "post", it executes
        after the request. With "pre" (default), the API function itself is wrapped
        by the decorator.
        """
        self.function = function
        self.request = request
        self.position = position
        self.options = options

    def __call__(self, wrapped_function):
        """
        This decorates the given function. The prepolicy decorator is ment
        for API functions on the API level.

        If some error occur the a DecoratorException is raised.

        The decorator function can modify the request data.

        :param wrapped_function: The function, that is decorated.
        :type wrapped_function: API function
        :return: None
        """
        @functools.wraps(wrapped_function)
        def function_wrapper(*args, **kwds):
            if self.position == "pre":
                    self.function(self.request,
                                  options=self.options)
            elif self.position == "post":
                response = wrapped_function(*args, **kwds)
                return self.function(self.request,
                                     response=response,
                                     options=self.options,
                                     *args, **kwds)
            return wrapped_function(*args, **kwds)

        return function_wrapper


def g_add_serial(request, response=None, options=()):
    """
    This is decorator function fetches the token serial and adds it to the flask
    g object.
    With a given response, this decorator checks for the serial in the response.
    If no response is given, the decorator checks first in the request and in the
    request path for the serial. By default the serial is expected at the third
    position of the request path. Set the position of the serial in the URL by
    specifying

    options = {"serial_position": N}

    N defaults to 3.
    """
    if response is None:
        if "serial" not in g or not g.serial:
            # try to get serial from request (also done by before_after.py)
            g.serial = getParam(request.all_data, "serial")
            if not g.serial:
                # try to get serial from request path
                if request.path:
                    if "serial_position" not in options:
                        options = {"serial_position": 3}
                    path_elements = [x for x in request.path.split('/') if x]
                    if len(path_elements) > options["serial_position"] + 1:
                        g.serial = path_elements[options["serial_position"] + 1]
        return True
    elif response.is_json:
        serial = response.json.get("detail", {}).get("serial")
        if serial:
            g.serial = serial
        return response
    else:
        return response