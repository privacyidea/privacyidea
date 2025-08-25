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

The postAddSerialToG decorator is tested in the ValidateAPITestCase.
"""


import logging
from flask import g
import functools
from privacyidea.lib.resolver import get_resolver_type
from privacyidea.lib.riskbase import calculate_risk,get_user_groups

log = logging.getLogger(__name__)


def add_serial_from_response_to_g(wrapped_function):
    """
    This decorator checks for the serial in the response and adds it to the
    flask g object.
    """
    @functools.wraps(wrapped_function)
    def function_wrapper(*args, **kwds):
        response = wrapped_function(*args, **kwds)
        if response.is_json:
            serial = response.json.get("detail", {}).get("serial")
            if serial:
                g.serial = serial
        return response

    return function_wrapper

def add_risk_to_user(request):
    """
    This decorator calculates and attachs the risk score to the user object, if available. It retrieves
    the IP and the service from the headers of the request, X-Forwarded-For and ServiceID respectivelly.
    If the IP is not found in the headers, then the IP of the request is used. For the service, the 
    User-Agent is used instead.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args,**kwargs):
            try:
                user = request.User
                if user:
                    utype = None
                    
                    utype = get_user_groups(user.uid,user.resolver)
                    if len(utype) == 0:
                        utype = None
                        
                    ip: str = request.headers.get("X-Forwarded-For",None)
                    if not ip:
                        log.debug("No IP found in headers. Using the IP of the request...")
                        ip = g.client_ip
                    else:
                        ips = ip.split(",")
                        ip = ips[0]
                    ip = ip.strip()
                        
                    service = request.headers.get("ServiceID",None)
                    if not service:
                        log.debug("No service provided. Using the User-Agent...")
                        service = request.user_agent
                    
                    score = int(calculate_risk(ip,service,utype))
                    user.set_attribute("risk",score)
                else:
                    log.debug("User not available on request. Skipping risk score.")
            except Exception as e:
                log.error(f"Can't calculate the risk score: {e}")
            return func(*args,**kwargs)
        return wrapper
    
    return decorator