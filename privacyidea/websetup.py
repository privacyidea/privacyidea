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

