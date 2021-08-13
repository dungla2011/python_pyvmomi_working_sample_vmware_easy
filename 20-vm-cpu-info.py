#!/usr/bin/env python

"""
* *******************************************************
* Copyright (c) VMware, Inc. 2016-2018. All Rights Reserved.
* SPDX-License-Identifier: MIT
* *******************************************************
*
* DISCLAIMER. THIS PROGRAM IS PROVIDED TO YOU "AS IS" WITHOUT
* WARRANTIES OR CONDITIONS OF ANY KIND, WHETHER ORAL OR WRITTEN,
* EXPRESS OR IMPLIED. THE AUTHOR SPECIFICALLY DISCLAIMS ANY IMPLIED
* WARRANTIES OR CONDITIONS OF MERCHANTABILITY, SATISFACTORY QUALITY,
* NON-INFRINGEMENT AND FITNESS FOR A PARTICULAR PURPOSE.
"""

__author__ = 'VMware, Inc.'
__vcenter_version__ = '6.5+'

import os

import sys
sys.path.append(os.path.realpath(".") + '/venv/Lib/site-packages/')

import requests
import urllib3
from vmware.vapi.vsphere.client import create_vsphere_client

from com.vmware.vcenter.vm.hardware_client import Cpu
from samples.vsphere.common.sample_util import parse_cli_args_vm
from samples.vsphere.common.sample_util import pp
from samples.vsphere.vcenter.setup import testbed

from samples.vsphere.vcenter.helper.vm_helper import get_vm
from samples.vsphere.common.ssl_helper import get_unverified_session



"""
Demonstrates how to configure CPU settings for a VM.

Sample Prerequisites:
The sample needs an existing VM.
"""



from configparser import ConfigParser
config = ConfigParser()
# read user/pw from ini
fileConf = '../vc_info.ini'  # File config store login info, see vc_info.ini.sample
# If file config exists:
if os.path.exists(fileConf):
    config.read(fileConf)

    serverDomain = config.get('config', 'server')
    username = config.get('config', 'username')
    password = config.get('config', 'password')
else:
    serverDomain = "<enter your server domain>"
    username = "<enter user, ex: administrator@vsphere.local>"
    password = "<enter password>"
###############################


vm_name = "2012-test1-2020"

session = requests.session()

session.verify = False

# Disable the secure connection warning for demo purpose.
# This is not recommended in a production environment.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Connect to a vCenter Server using username and password
client = create_vsphere_client(server=serverDomain, username=username,
                                       password=password, session=session)

vm = get_vm(client, vm_name)

if not vm:
    raise Exception('Sample requires an existing vm with name ({}). '
                    'Please create the vm first.'.format(vm_name))
print("Using VM '{}' ({}) for Cpu Sample".format(vm_name, vm))

print('\n# Example: Get current Cpu configuration')

cpu_info = client.vcenter.vm.hardware.Cpu.get(vm)
print('vm.hardware.Cpu.get({}) -> {}'.format(vm, pp(cpu_info)))

