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

import fakes as nova_fakes
import masakari_config
import masakari_util
import masakari_worker

class TestRecoveryControllerWorker(unittest.TestCase):
    def setUp(self):
        
        sample_config = os.path.dirname(os.path.abspath(__file__)) +\
            '/masakari-controller-test.conf'
        rc_config = masakari_config.RecoveryControllerConfig(sample_config)
        with mock.patch('masakari_util.RecoveryControllerUtilApi') as mock_api:
            self.worker = masakari_worker.RecoveryControllerWorker(rc_config)
        
    def tearDown(self):
        pass

    def test_do_node_accident_vm_recovery_with_resized(self):
        self.worker.rc_util_api.do_instance_reset.return_value = None
        self.worker.rc_util_api.do_instance_evacuate.return_value = None

        expected_ret = self.worker.STATUS_NORMAL

        ret = self.worker._do_node_accident_vm_recovery(
            'uuid1', 'resized', 'node1')

        self.assertEqual(expected_ret, ret)
        (self.worker.rc_util_api.do_instance_reset.
         assert_called_with('uuid1', 'error'))

    def test_do_node_accident_vm_recovery_with_active_stopped(self):
        self.worker.rc_util_api.do_instance_evacuate.return_value = None
        expected_ret = self.worker.STATUS_NORMAL

        ret = self.worker._do_node_accident_vm_recovery(
            'uuid1', 'active', 'node1')
        self.assertEqual(expected_ret, ret)
        (self.worker.rc_util_api.do_instance_evacuate.
         assert_called_with('uuid1', 'node1'))

        ret = self.worker._do_node_accident_vm_recovery(
            'uuid2', 'stopped', 'node1')
        self.assertEqual(expected_ret, ret)
        (self.worker.rc_util_api.do_instance_evacuate.
         assert_called_with('uuid2', 'node1'))

    def test_do_process_accident_vm_recovery_with_stopped(self):
        self.worker.rc_util_api.do_instance_reset.return_value = None
        expected_ret = self.worker.STATUS_NORMAL

        ret = self.worker._do_process_accident_vm_recovery(
            'uuid1', 'stopped')
        self.assertEqual(expected_ret, ret)
        (self.worker.rc_util_api.do_instance_reset.
         assert_called_with('uuid1', 'stopped'))


    def test_do_process_accident_vm_recovery_with_resized(self):
        self.worker.rc_util_api.do_instance_reset.return_value = None
        self.worker.rc_util_api.do_instance_stop.return_value = None
        stopped_server = nova_fakes.FakeNovaServer('uuid1', 'stopped', {})
        self.worker.rc_util_api.do_instance_show.return_value = stopped_server
        self.worker.rc_util_api.do_instance_start.return_value = None

        expected_ret = self.worker.STATUS_NORMAL

        ret = self.worker._do_process_accident_vm_recovery(
            'uuid1', 'resized')

        self.assertEqual(expected_ret, ret)
        (self.worker.rc_util_api.do_instance_reset.
         assert_called_with('uuid1', 'active'))
        self.worker.rc_util_api.do_instance_stop.assert_called_with('uuid1')
        self.worker.rc_util_api.do_instance_show.assert_called_with('uuid1')
        self.worker.rc_util_api.do_instance_start.assert_called_with('uuid1')

    def test_do_process_accident_vm_recovery_with_active(self):
        self.worker.rc_util_api.do_instance_stop.return_value = None
        stopped_server = nova_fakes.FakeNovaServer('uuid1', 'stopped', {})
        self.worker.rc_util_api.do_instance_show.return_value = stopped_server
        self.worker.rc_util_api.do_instance_start.return_value = None
        expected_ret = self.worker.STATUS_NORMAL

        ret = self.worker._do_process_accident_vm_recovery(
            'uuid1', 'active')

        self.assertEqual(expected_ret, ret)
        self.worker.rc_util_api.do_instance_stop.assert_called_with('uuid1')
        self.worker.rc_util_api.do_instance_show.assert_called_with('uuid1')
        self.worker.rc_util_api.do_instance_start.assert_called_with('uuid1')


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(
        TestRecoveryControllerWorker)
    unittest.TextTestRunner(verbosity=2).run(suite)
