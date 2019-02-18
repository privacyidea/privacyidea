"""
This file contains the tests for the periodic tasks API.

This tests api/periodictask.py
"""
import json
from contextlib import contextmanager
import mock
from dateutil.parser import parse as parse_timestamp

from privacyidea.lib.periodictask import TASK_MODULES
from tests.base import MyApiTestCase


class APIPeriodicTasksTestCase(MyApiTestCase):
    @contextmanager
    def mock_task_module(self):
        """
        Mock a UnitTest task module, use as ``with self.mock_task_module() as module:``
        """
        taskmodule = mock.MagicMock()
        cls = lambda config: taskmodule
        with mock.patch.dict(TASK_MODULES, {"UnitTest": cls}, clear=True):
            yield taskmodule

    def simulate_request(self, *args, **kwargs):
        """
        Run test request, return a tuple (status code, decoded body)
        If 'Authorization' is not given in the request headers, add ``self.at``.
        """
        headers = kwargs.get('headers', {}).copy()
        if 'Authorization' not in headers:
            headers['Authorization'] = self.at
        kwargs['headers'] = headers
        with self.app.test_request_context(*args, **kwargs):
            res = self.app.full_dispatch_request()
            return res.status_code, json.loads(res.data.decode('utf8'))

    def test_01_crud(self):
        # no tasks yet
        status_code, data = self.simulate_request('/periodictask/', method='GET')
        self.assertEqual(status_code, 200)
        self.assertTrue(data['result']['status'])
        self.assertEqual(data['result']['value'], [])

        # need authorization
        status_code, data = self.simulate_request('/periodictask/', method='GET', headers={'Authorization': 'ABC'})
        self.assertEqual(status_code, 401)
        self.assertFalse(data['result']['status'])

        # create task
        with self.mock_task_module():
            task_dict1 = {
                'name': 'some task',
                'nodes': 'pinode1, pinode2',
                'active': False,
                'interval': '0 8 * * *',
                'taskmodule': 'UnitTest',
                'ordering': 5,
                'options': '{"something": 123, "else": true}',
            }
            status_code, data = self.simulate_request('/periodictask/', method='POST', data=task_dict1)
            self.assertEqual(status_code, 200)
            self.assertEqual(data['result']['status'], True)
            ptask_id1 = data['result']['value']

        # some invalid tasks
        invalid_task_dicts = [
            # invalid ordering
            {
                'name': 'some other task',
                'active': False,
                'nodes': 'a, b',
                'interval': '0 8 * * *',
                'taskmodule': 'UnitTest',
                'ordering': '-3',
                'options': '{"something": "123", "else": true}',
            },
            # no nodes
            {
                'name': 'some other task',
                'active': False,
                'interval': '0 8 * * *',
                'taskmodule': 'UnitTest',
                'options': '{"something": "123", "else": true}',
            },
            # empty nodes
            {
                'name': 'some other task',
                'active': False,
                'interval': '0 8 * * *',
                'nodes': '    ',
                'taskmodule': 'UnitTest',
                'options': '{"something": "123", "else": true}',
            },
            # unknown taskmodule
            {
                'name': 'some other task',
                'nodes': 'pinode1, pinode2',
                'active': False,
                'interval': '0 8 * * *',
                'taskmodule': 'Unknown',
                'options': '{"something": "123"}',
            },
            # invalid interval
            {
                'name': 'some other task',
                'nodes': 'pinode1, pinode2',
                'active': False,
                'interval': 'every day',
                'taskmodule': 'UnitTest',
                'options': '{"something": "123"}',
            },
            # invalid options
            {
                'name': 'some task',
                'nodes': 'pinode1, pinode2',
                'active': False,
                'interval': '0 8 * * *',
                'taskmodule': 'UnitTest',
                'options': '[1, 2]',
            }
        ]
        # all result in ERR905
        with self.mock_task_module():
            for invalid_task_dict in invalid_task_dicts:
                status_code, data = self.simulate_request('/periodictask/', method='POST',
                                                          data=invalid_task_dict)
                self.assertEqual(status_code, 400)
                self.assertFalse(data['result']['status'])
                self.assertIn('ERR905', data['result']['error']['message'])

        # create another task
        with self.mock_task_module():
            task_dict2 = {
                'name': 'some other task',
                'nodes': 'pinode1',
                'active': False,
                'interval': '0 8 * * 0',
                'taskmodule': 'UnitTest',
                'ordering': 2,
            }
            status_code, data = self.simulate_request('/periodictask/', method='POST',
                                                      data=task_dict2)

            self.assertEqual(status_code, 200)
            self.assertTrue(data['result']['status'])
            ptask_id2 = data['result']['value']

        # can list the periodic tasks
        status_code, data = self.simulate_request('/periodictask/', method='GET')
        self.assertEqual(status_code, 200)
        self.assertTrue(data['result']['status'])
        self.assertEqual(len(data['result']['value']), 2)
        self.assertEqual([task['name'] for task in data['result']['value']],
                         ['some other task', 'some task'])

        # find first task
        result_dict = data['result']['value'][1]
        self.assertEqual(result_dict['id'], ptask_id1)
        self.assertEqual(result_dict['ordering'], 5)
        self.assertEqual(result_dict['name'], 'some task')
        self.assertEqual(result_dict['active'], False)
        self.assertEqual(result_dict['interval'], '0 8 * * *')
        self.assertEqual(result_dict['nodes'], ['pinode1', 'pinode2'])
        self.assertEqual(result_dict['last_runs'], {})
        last_update = parse_timestamp(result_dict['last_update'])
        self.assertIsNotNone(last_update)
        self.assertEqual(result_dict['options'], {'something': '123', 'else': 'True'})


        # get one
        status_code, data = self.simulate_request('/periodictask/{}'.format(ptask_id1), method='GET')
        self.assertEqual(status_code, 200)
        self.assertEqual(data['result']['value']['id'], ptask_id1)

        # unknown ID
        status_code, data = self.simulate_request('/periodictask/4242', method='GET')
        self.assertEqual(status_code, 404)
        self.assertFalse(data['result']['status'])

        # update existing task
        task_dict1['name'] = 'new name'
        task_dict1['options'] = '{"key": "value"}'
        task_dict1['id'] = ptask_id1
        task_dict1['ordering'] = '2'
        with self.mock_task_module():
            status_code, data = self.simulate_request('/periodictask/', method='POST',
                                                      data=task_dict1)
            self.assertEqual(status_code, 200)
            self.assertTrue(data['result']['status'])
            self.assertEqual(data['result']['value'], ptask_id1)

        # can list the periodic tasks in new order
        status_code, data = self.simulate_request('/periodictask/', method='GET')
        self.assertEqual(status_code, 200)
        self.assertTrue(data['result']['status'])
        self.assertEqual(len(data['result']['value']), 2)
        self.assertEqual([task['name'] for task in data['result']['value']],
                         ['new name', 'some other task'])

        # get updated task
        status_code, data = self.simulate_request('/periodictask/{}'.format(ptask_id1), method='GET')
        self.assertEqual(status_code, 200)
        self.assertEqual(data['result']['value']['id'], ptask_id1)
        self.assertEqual(data['result']['value']['ordering'], 2)
        self.assertEqual(data['result']['value']['name'], 'new name')
        self.assertEqual(data['result']['value']['options'], {'key': 'value'})
        self.assertGreater(parse_timestamp(data['result']['value']['last_update']),
                           last_update)
        last_update = parse_timestamp(data['result']['value']['last_update'])

        # enable
        status_code, data = self.simulate_request('/periodictask/enable/{}'.format(ptask_id1), method='POST')
        self.assertEqual(status_code, 200)

        # get updated task
        status_code, data = self.simulate_request('/periodictask/{}'.format(ptask_id1), method='GET')
        self.assertEqual(status_code, 200)
        self.assertEqual(data['result']['value']['name'], 'new name')
        self.assertEqual(data['result']['value']['active'], True)
        self.assertGreater(parse_timestamp(data['result']['value']['last_update']),
                           last_update)
        last_update = parse_timestamp(data['result']['value']['last_update'])

        # disable
        status_code, data = self.simulate_request('/periodictask/disable/{}'.format(ptask_id1), method='POST')
        self.assertEqual(status_code, 200)

        # get updated task
        status_code, data = self.simulate_request('/periodictask/{}'.format(ptask_id1), method='GET')
        self.assertEqual(status_code, 200)
        self.assertEqual(data['result']['value']['name'], 'new name')
        self.assertEqual(data['result']['value']['active'], False)
        self.assertGreater(parse_timestamp(data['result']['value']['last_update']),
                           last_update)

        # disable again without effect
        status_code, data = self.simulate_request('/periodictask/disable/{}'.format(ptask_id1), method='POST')
        self.assertEqual(status_code, 200)

        # get updated task
        status_code, data = self.simulate_request('/periodictask/{}'.format(ptask_id1), method='GET')
        self.assertEqual(status_code, 200)
        self.assertEqual(data['result']['value']['name'], 'new name')
        self.assertEqual(data['result']['value']['active'], False)

        # delete
        status_code, data = self.simulate_request('/periodictask/{}'.format(ptask_id1), method='DELETE')
        self.assertEqual(status_code, 200)
        self.assertEqual(data['result']['value'], ptask_id1)

        # get updated task impossible now
        status_code, data = self.simulate_request('/periodictask/{}'.format(ptask_id1), method='GET')
        self.assertEqual(status_code, 404)
        self.assertFalse(data['result']['status'], False)

        # only 1 task left
        status_code, data = self.simulate_request('/periodictask/', method='GET')
        self.assertEqual(status_code, 200)
        self.assertTrue(data['result']['status'])
        self.assertEqual(len(data['result']['value']), 1)

        # delete the second task as well
        status_code, data = self.simulate_request('/periodictask/{}'.format(ptask_id2), method='DELETE')
        self.assertEqual(status_code, 200)
        self.assertEqual(data['result']['value'], ptask_id2)

        # no tasks left
        status_code, data = self.simulate_request('/periodictask/', method='GET')
        self.assertEqual(status_code, 200)
        self.assertTrue(data['result']['status'])
        self.assertEqual(data['result']['value'], [])

    def test_02_taskmodules(self):
        with self.mock_task_module() as taskmodule:
            status_code, data = self.simulate_request('/periodictask/taskmodules/', method='GET')
            self.assertEqual(status_code, 200)
            self.assertTrue(data['result']['status'])
            self.assertEqual(data['result']['value'], ['UnitTest'])

            options = {'key1': {'type': 'str', 'desc': 'description'},
                       'key2': {'type': 'str', 'desc': 'other description'}}
            taskmodule.options = options

            status_code, data = self.simulate_request('/periodictask/options/UnitTest', method='GET')
            self.assertEqual(status_code, 200)
            self.assertTrue(data['result']['status'])
            self.assertEqual(data['result']['value'], options)

    def test_03_nodes(self):
        status_code, data = self.simulate_request('/periodictask/nodes/', method='GET')
        self.assertEqual(status_code, 200)
        self.assertTrue(data['result']['status'])
        self.assertEqual(data['result']['value'], ['Node2', 'Node1'])
