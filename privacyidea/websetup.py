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
  Description:  - Setup the privacyIDEA application -
                the websetup.py is called for the creating the initial
                data and configuration

  Dependencies: -

'''



from privacyidea.config.environment import load_environment
import privacyidea.lib.base

import logging
LOG = logging.getLogger(__name__)



def setup_app(command, conf, param):
    '''
    setup_app is the hook, which is called, when the application is created

    :param command: - not used -
    :param conf: the application configuration
    :param vars: - not used -

    :return: - nothing -
    '''

    load_environment(conf.global_conf, conf.local_conf)
    unitTest = conf.has_key('unitTest')
    privacyidea.lib.base.setup_app(conf.local_conf, conf.global_conf, unitTest)

###eof#########################################################################

