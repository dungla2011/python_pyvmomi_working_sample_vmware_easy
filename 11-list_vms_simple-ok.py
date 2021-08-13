#!/usr/bin/env python

"""
* *******************************************************
* Copyright (c) VMware, Inc. 2016. All Rights Reserved.
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
__copyright__ = 'Copyright 2017 VMware, Inc. All rights reserved.'
__vcenter_version__ = '6.5+'

import os
import sys
sys.path.append(os.path.realpath(".") + '/venv/Lib/site-packages/')

from pprint import pprint
from vmware.vapi.vsphere.client import create_vsphere_client
from samples.vsphere.common import sample_cli
from samples.vsphere.common import sample_util
from samples.vsphere.common.ssl_helper import get_unverified_session

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



class ListVM(object):
    """
    Demonstrates getting list of VMs present in vCenter
    Sample Prerequisites:
    vCenter/ESX
    """
    def __init__(self):
        #parser = sample_cli.build_arg_parser()
        #args = sample_util.process_cli_args(parser.parse_args())
        #session = get_unverified_session() if args.skipverification else None
        #self.client = create_vsphere_client(server=args.server,
        ##                                    username=args.username,
        #                                    password=args.password,
        #                                    session=session)
        session = get_unverified_session()
        self.client = create_vsphere_client(server=serverDomain,username=username,password=password,session=session)

    def run(self):
        """
        List VMs present in server
        """
        list_of_vms = self.client.vcenter.VM.list()
        print("----------------------------")
        print("List Of VMs")
        print("----------------------------")
        pprint(list_of_vms)
        print("----------------------------")


def main():
    list_vm = ListVM()
    list_vm.run()


if __name__ == '__main__':
    main()
