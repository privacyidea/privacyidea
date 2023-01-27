# -*- coding: utf-8 -*-
"""
This tests the files
  lib/task/simplestats.py
"""
from privacyidea.lib.user import User
from privacyidea.lib.tokenclass import TOKENKIND
from privacyidea.lib.token import init_token
from privacyidea.models import db
from .base import MyTestCase
from privacyidea.lib.monitoringstats import get_values
from flask import current_app

from privacyidea.lib.task.simplestats import SimpleStatsTask

simple_results = {'total_tokens': (1, 2, 3, 4),
                  'hardware_tokens': (0, 1, 2, 2),
                  'software_tokens': (1, 1, 1, 2),
                  'assigned_tokens': (0, 0, 1, 1),
                  'unassigned_hardware_tokens': (0, 1, 1, 1),
                  'user_with_token': (0, 0, 1, 2)
                  }


class TaskSimpleStatsTestCase(MyTestCase):

    serials = ['SE1', 'SE2', 'SE3', 'SE4']
    otpkey = "3132333435363738393031323334353637383930"

    def test_00_read_simplestats_to_monitoringstats(self):
        self.setUp_user_realms()

        # create a simple statistics class
        sst = SimpleStatsTask(current_app.config)
        # and set all parameters to 'true'
        params = {}
        for o in sst.options.keys():
            params[o] = True

        # first we create a software token
        init_token({"type": "totp", "otpkey": self.otpkey, "serial": self.serials[0]})

        sst.do(params)
        db.session.commit()
        for o in sst.options.keys():
            self.assertEqual(simple_results[o][0], get_values(o)[0][1],
                             msg="Current option: {0}".format(o))

        # add a hardware token
        init_token({"type": "totp", "otpkey": self.otpkey, "serial": self.serials[1]},
                   tokenkind=TOKENKIND.HARDWARE)

        sst.do(params)
        db.session.commit()
        for o in sst.options.keys():
            self.assertEqual(simple_results[o][1], get_values(o)[1][1],
                             msg="Current option: {0}".format(o))

        # add a hardware token and assign it to a user
        token = init_token({"type": "totp", "otpkey": self.otpkey, "serial": self.serials[2]},
                           tokenkind=TOKENKIND.HARDWARE,
                           user=User(login="cornelius", realm=self.realm1))
        self.assertEqual("cornelius", token.user.login)
        self.assertTrue(token.is_active())
        self.assertEqual(TOKENKIND.HARDWARE, token.get_tokeninfo('tokenkind'))

        sst.do(params)
        db.session.commit()
        for o in sst.options.keys():
            self.assertEqual(simple_results[o][2], get_values(o)[2][1],
                             msg="Current option: {0}".format(o))

        # add a software token and assign it to a user
        token = init_token({"type": "totp", "otpkey": self.otpkey, "serial": self.serials[3]},
                           user=User(login="selfservice", realm=self.realm1))
        self.assertEqual("selfservice", token.user.login)
        self.assertTrue(token.is_active())
        self.assertEqual(TOKENKIND.SOFTWARE, token.get_tokeninfo('tokenkind'))

        # check if getting only certain stats works
        params['assigned_tokens'] = False
        sst.do(params)
        db.session.commit()
        self.assertEqual(3, len(get_values('assigned_tokens')))
        self.assertEqual(4, len(get_values('user_with_token')))
        for o in sst.options.keys():
            if o != 'assigned_tokens':
                self.assertEqual(simple_results[o][3], get_values(o)[3][1],
                                 msg="Current option: {0}".format(o))
        self.assertEqual(simple_results['assigned_tokens'][3],
                         get_values('assigned_tokens')[2][1])

