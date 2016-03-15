#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright(c) 2016 Nippon Telegraph and Telephone Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import os
import sys
import unittest

import mock

# FIXEME(masa) Adding python path is temporal hack. After setting up tox
# test tool with virtualenv, throw away it.
sys.path.append((os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import masakari_worker
import masakari_config

class TestRecoveryControllerWorker(unittest.TestCase):
    def setUp(self):
        
        sample_config = os.path.dirname(os.path.abspath(__file__)) +\
            '/masakari-controller-test.conf'
        rc_config = masakari_config.RecoveryControllerConfig(sample_config)
        self.worker = masakari_worker.RecoveryControllerWorker(rc_config)
        
    def tearDown(self):
        pass

    def test_do_node_accident_vm_recovery_with_resized(self):
        self.worker.rc_util_api.do_instance_reset = mock.Mock()
        self.worker.rc_util_api.do_instance_reset.return_value = ('202',
                                                                  'success')
        self.worker.rc_util_api.do_instance_evacuate = mock.Mock()
        self.worker.rc_util_api.do_instance_evacuate.return_value = ('200',
                                                                     'success')
        expected_ret = self.worker.STATUS_NORMAL

        ret = self.worker._do_node_accident_vm_recovery(
            'uuid1', 'resized', 'node1')

        self.assertEqual(expected_ret, ret)

    def test_do_node_accident_vm_recovery_with_active_stopped(self):
        self.worker.rc_util_api.do_instance_evacuate = mock.Mock()
        self.worker.rc_util_api.do_instance_evacuate.return_value = ('200',
                                                                     'success')
        expected_ret = self.worker.STATUS_NORMAL

        ret = self.worker._do_node_accident_vm_recovery(
            'uuid1', 'active', 'node1')
        self.assertEqual(expected_ret, ret)

        ret = self.worker._do_node_accident_vm_recovery(
            'uuid1', 'stopped', 'node1')
        self.assertEqual(expected_ret, ret)

    def test_do_process_accident_vm_recovery_with_stopped(self):
        self.worker.rc_util_api.do_instance_reset = mock.Mock()
        self.worker.rc_util_api.do_instance_reset.return_value = ('202',
                                                                  'success')
        expected_ret = self.worker.STATUS_NORMAL

        ret = self.worker._do_process_accident_vm_recovery(
            'uuid1', 'stopped')
        self.assertEqual(expected_ret, ret)

    def test_do_process_accident_vm_recovery_with_resized(self):
        self.worker.rc_util_api.do_instance_reset = mock.Mock()
        self.worker.rc_util_api.do_instance_reset.return_value = ('202',
                                                                  'success')
        self.worker.rc_util_api.do_instance_stop = mock.Mock()
        self.worker.rc_util_api.do_instance_stop.return_value = ('202',
                                                                 'success')

        response_body = {
            "server": {
                "OS-EXT-STS:vm_state": 'stopped',
                'metadata': {}
                }
            }
        jsoned_body = json.dumps(response_body)

        self.worker.rc_util_api.do_instance_show = mock.Mock()
        self.worker.rc_util_api.do_instance_show.return_value = ('200',
                                                                 jsoned_body)

        self.worker.rc_util_api.do_instance_start = mock.Mock()
        self.worker.rc_util_api.do_instance_start.return_value = ('202',
                                                                 'success')
        expected_ret = self.worker.STATUS_NORMAL

        ret = self.worker._do_process_accident_vm_recovery(
            'uuid1', 'resized')

        self.assertEqual(expected_ret, ret)

    def test_do_process_accident_vm_recovery_with_active(self):
        self.worker.rc_util_api.do_instance_stop = mock.Mock()
        self.worker.rc_util_api.do_instance_stop.return_value = ('202',
                                                                 'success')

        response_body = {
            "server": {
                "OS-EXT-STS:vm_state": 'stopped',
                'metadata': {}
                }
            }
        jsoned_body = json.dumps(response_body)

        self.worker.rc_util_api.do_instance_show = mock.Mock()
        self.worker.rc_util_api.do_instance_show.return_value = ('200',
                                                                 jsoned_body)

        self.worker.rc_util_api.do_instance_start = mock.Mock()
        self.worker.rc_util_api.do_instance_start.return_value = ('202',
                                                                 'success')
        expected_ret = self.worker.STATUS_NORMAL

        ret = self.worker._do_process_accident_vm_recovery(
            'uuid1', 'active')

        self.assertEqual(expected_ret, ret)


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(
        TestRecoveryControllerWorker)
    unittest.TextTestRunner(verbosity=2).run(suite)
