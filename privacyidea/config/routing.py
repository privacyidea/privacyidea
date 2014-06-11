# -*- coding: utf-8 -*-
#
#  privacyIDEA is a fork of LinOTP
#  May 08, 2014 Cornelius Kölbel
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  Copyright (C) 2010 - 2014 LSE Leading Security Experts GmbH
#  License:  AGPLv3
#  contact:  http://www.linotp.org
#            http://www.lsexperts.de
#            linotp@lsexperts.de
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
'''
This file is part of the privacyidea service
'''

"""Routes configuration

The more specific and detailed routes should be defined first so they
may take precedent over the more generic routes. For more information
refer to the routes manual at http://routes.groovie.org/docs/
"""
from pylons import config
from routes import Mapper

def make_map():
    '''
    Create, configure and return the routes Mapper
    There are the three main controllers:
        /admin
        /validate
        /system
    '''
    routeMap = Mapper(directory=config['pylons.paths']['controllers'],
                 always_scan=config['debug'])
    routeMap.minimization = False

    # The ErrorController route (handles 404/500 error pages); it should
    # likely stay at the top, ensuring it can always be resolved
    routeMap.connect('/error/{action}', controller='error')
    routeMap.connect('/error/{action}/{id}', controller='error')

    # CUSTOM ROUTES HERE
    routeMap.connect('/manage/custom-style.css', controller='manage', action='custom_style')
    routeMap.connect('/selfservice/custom-style.css', controller='selfservice', action='custom_style')

    routeMap.connect('/{controller}/{action}')
    routeMap.connect('/{controller}/{action}/{id}')

    routeMap.connect('/admin', controller='admin', action='show')
    routeMap.connect('/validate', controller='validate', action='check')
    routeMap.connect('/system', controller='system', action='getConfig')

    # the default site will be the self service
    routeMap.connect('/', controller='selfservice', action='index')

    routeMap.connect('/manage/', controller='manage', action='index')

    # the default openid will be the status
    routeMap.connect('/openid/', controller='openid', action='status')
    return routeMap
