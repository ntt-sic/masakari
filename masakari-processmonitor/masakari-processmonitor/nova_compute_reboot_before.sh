#!/bin/bash

# Copyright(c) 2015 Nippon Telegraph and Telephone Corporation
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

# Delete the child process as the required steps to restart of nova_compute process.

KILL_PS_LIST=(`ps -ef | grep nova-compute | grep -v grep | awk '{ print $2; }'`)

for PS_ID in ${KILL_PS_LIST[@]}
do
    sudo kill -9 ${PS_ID}
done
