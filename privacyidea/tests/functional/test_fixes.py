# -*- coding: utf-8 -*-
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
  Description:  functional tests
                
  Dependencies: -

'''

from privacyidea.tests import TestController, url

import json

import logging
log = logging.getLogger(__name__)


import threading

class DoRequest(threading.Thread):
    ''' the request thread'''

    def __init__ (self, utest, rid=1, uri=None, params=None):
        '''
        initialize all settings of the request thread

        :param utest: method/function to be called
        :param rid: the request id
        :param uri: the request url object
        :param params: additional parmeters
        '''
        threading.Thread.__init__(self)

        self.utest = utest
        self.rid = rid
        self.uri = uri
        self.params = params

        self.response = None

    def run(self):
        ''' start the thread'''
        response = self.utest.app.get(self.uri, params=self.params)
        self.response = response.body
        return

    def status(self):
        '''
        retrieve the request result

        :return: the thread request result
        '''
        res = '"status": true,' in self.response
        return res

    def stat(self):
        '''
        retrieve the complete response
        '''
        return (self.rid, self.response)

class TestFixesController(TestController):
    '''
    test some fixes for closed tickets
    '''
    def setUp(self):
        ''' setup the Test Controller'''
        TestController.setUp(self)
        self.serials = []

    def tearDown(self):
        ''' make the dishes'''
        self.remove_tokens()
        TestController.tearDown(self)
        return

    def remove_tokens(self):
        '''
        remove all tokens, which are in the internal array of serial

        :return: - nothing -
        '''
        for serial in self.serials:
            self.del_token(serial)
        return

    def del_token(self, serial):
        '''
        delet a token identified by his serial number

        :param serial: the token serial
        :return: the response object of admin/remove
        '''
        param = {"serial" : serial }
        response = self.app.get(url(controller='admin', action='remove'),
                                                            params=param)
        return response

    def get_config(self):
        '''
        get the privacyidea config

        :return: the response object of the system/getConfig
        '''
        param = {}
        response = self.app.get(url(controller='system', action='getConfig'),
                                                                params=param)
        return response


    def add_token(self, user, pin=None, serial=None, typ=None, key=None,
                        timeStep=60, timeShift=0, hashlib='sha1', otplen=8):
        '''
        add a token to privacyIDEA

        :param user: user that owns the token
        :param pin: token pin - if none use the user name
        :param serial: give serial number
        :parm typ: token type
        :param key: the secret key
        :param timeStep: the TOTP time step
        :param timeShift: the TOTP time shift
        :param hashlib: the hmac hashlib
        :param otplen: the otp length

        :return: tuple of serial and response
        '''
        if serial is None:
            serial = 's' + user

        if pin is None:
            pin = user

        if typ is None:
            typ = 'totp'

        param = { 'user': user, 'pin':pin, 'serial': serial, 'type':typ,
                 'timeStep':timeStep, 'otplen' : otplen, 'hashlib':hashlib}
        if timeShift != 0:
            param['timeShift'] = timeShift

        if key is not None:
            param['otpkey'] = key

        response = self.app.get(url(controller='admin', action='init'),
                                                                params=param)
        assert '"status": true,' in response

        return (serial, response)


    def test_ticket_425(self):
        '''
        Test #2425: test if setConfig is timing save

        1. run multiple setConfig threads concurrently
        2. verify that only one thread has written his config
        3. verify, that all config entries of this thread are in place

        config entries are of format: key_entryId = val_threadId
             eg. key_101 = val_4 belongs to thread 4 and is entry 101
        '''

        check_results = []
        numthreads = 20
        numkeys = 200

        params = {}
        for tid in range(numthreads):
            param = {}
            for kid in range(numkeys):
                key = 'key_%d' % (kid)
                val = 'val_%d' % (tid)
                param[key] = val
            params[tid] = param

        uri = url(controller='system', action='setConfig')

        for tid in range(numthreads):
            param = params.get(tid)
            current = DoRequest(self, rid=tid, uri=uri, params=param)
            check_results.append(current)
            current.start()

        ## wait till all threads are completed
        for req in check_results:
            req.join()

        ## now check in the config if all keys are there
        config = self.get_config()
        conf = json.loads(config.body)
        conf = conf.get('result').get('value')

        ## check for the keys and the values in the dict
        counter = 0
        valdict = set()
        for cconf in conf:
            if cconf.startswith('key_'):
                valdict.add(conf.get(cconf))
                counter += 1

        assert counter == numkeys
        assert len(valdict) == 1

        return


    def test_ticket_864(self):
        '''
        #2864: admin/tokenrealm with multiple realms
        remarks:
            the problem is independent of sqlite, the reason is that realms are
            treated case insensitive
        1. create a token
        2. add some realms to the token
        3. verify, that the token is part of the realms
        '''

        sqlconnect = self.appconf.get('sqlalchemy.url')
        log.debug('current test against %s' % (sqlconnect))

        self.add_token('root', serial='troot', typ='spass', key='1234')

        param = {'serial':'troot', 'realms':'myDefRealm,myMixRealm'}
        response = self.app.get(url(controller='admin', action='tokenrealm'),
                                                                params=param)
        if '"value": 1' not in response.body:
            assert '"value": 1' in response.body

        param = {}
        ## the admin show returns slices of 10 token and our troot is not in
        ## the first slice :-( - so we now search directly for the token
        param['serial'] = 'troot'
        response = self.app.get(url(controller='admin', action='show'),
                                                            params=param)
        resp = json.loads(response.body)
        tok_data = resp.get('result').get('value').get('data')[0]
        realms = tok_data.get('privacyIDEA.RealmNames')
        t_ser = tok_data.get("privacyIDEA.TokenSerialnumber")

        assert t_ser == 'troot'
        assert 'mydefrealm' in realms
        assert 'mymixrealm' in realms

        self.del_token('troot')

        return

    def test_ticket_2909(self):
        '''
        Test #2909: HSM problems will raise an HSM Exception
               which could trigger an HTTP Error
        '''
        param = {'__HSMEXCEPTION__':'__ON__'}
        response = self.app.get(url(controller='system',
                                action='setupSecurityModule'), params=param)

        param = {'key':'sec', 'value':'mySec', 'type':'password'}
        response = self.app.get(url(controller='system', action='setConfig'),
                                                                params=param)

        assert '707' in response
        assert 'hsm not ready' in response

        res = ''
        try:
            param = {'key':'sec', 'value':'mySec',
                 'type':'password', 'httperror':'503'}
            response = self.app.get(url(controller='system',
                                        action='setConfig'), params=param)
        except Exception as exx:
            log.info(response)
            res = type(exx).__name__

        assert res == 'AppError'

        ## restore default
        param = {'__HSMEXCEPTION__':'__OFF__'}
        response = self.app.get(url(controller='system',
                                action='setupSecurityModule'), params=param)

        return

    def test_ticket_12018(self):
        '''
        #12018: OTPLen of /admin/init is not ignored
        '''
        (serial, response) = self.add_token('root', serial='troot',
                                           typ='hmac', key='1234', otplen=12)
        log.info(response)
        assert serial == 'troot'

        param = {}
        response = self.app.get(url(controller='admin', action='show'),
                                                                params=param)
        #resp = json.loads(response.body)
        assert '"privacyIDEA.OtpLen": 12' in response

        res = self.del_token(serial)
        assert '"status": true,' in res
        assert '"value": 1' in res

        return

#eof###########################################################################

